# Original Utopia diagnostic: read an owned PE file, never execute or modify it.
# This FNV-1a fingerprint distinguishes local builds; it is not authentication.
from pathlib import Path
from struct import unpack_from


def fingerprint(path):
    data = path.read_bytes()
    pe = unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe+4] != b'PE\0\0':
        raise ValueError('Not a PE image')
    count = unpack_from('<H', data, pe+6)[0]
    optional = pe + 24
    size = unpack_from('<H', data, pe+20)[0]
    if unpack_from('<H', data, optional)[0] != 0x20b:
        raise ValueError('Expected PE32+')
    sections = [unpack_from('<IIII', data, optional+size+i*40+8) for i in range(count)]

    def offset(rva):
        for virtual_size, virtual_address, raw_size, raw_offset in sections:
            if virtual_address <= rva < virtual_address+max(virtual_size, raw_size):
                return raw_offset+rva-virtual_address
        raise ValueError('RVA outside sections')

    exports = offset(unpack_from('<I', data, optional+112)[0])
    names = unpack_from('<I', data, exports+24)[0]
    functions = offset(unpack_from('<I', data, exports+28)[0])
    name_table = offset(unpack_from('<I', data, exports+32)[0])
    ordinals = offset(unpack_from('<I', data, exports+36)[0])
    for i in range(names):
        start = offset(unpack_from('<I', data, name_table+4*i)[0])
        name = data[start:data.index(b'\0', start)]
        if name == b'ImmSetCandidateWindow':
            ordinal = unpack_from('<H', data, ordinals+2*i)[0]
            code = offset(unpack_from('<I', data, functions+4*ordinal)[0])
            code_bytes = data[code:code+64]
            if len(code_bytes) != 64:
                raise ValueError('Export code is truncated')
            value = 0xcbf29ce484222325
            for byte in code_bytes:
                value = ((value ^ byte) * 0x100000001b3) & 0xffffffffffffffff
            return f'{value:016x}'
    raise ValueError('Export not found')


if __name__ == '__main__':
    import sys
    for arg in sys.argv[1:]:
        path = Path(arg)
        print(path.name, fingerprint(path))
