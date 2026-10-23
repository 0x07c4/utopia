import importlib.util
from pathlib import Path
from struct import pack_into
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "desktop/gaming/diagnostics/pe-candidate-fingerprint.py"
spec = importlib.util.spec_from_file_location("ime_fingerprint", SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def pe_fixture():
    data = bytearray(0x600)
    data[:2] = b"MZ"
    pack_into("<I", data, 0x3c, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    pack_into("<H", data, 0x86, 1)
    pack_into("<H", data, 0x94, 0xf0)
    pack_into("<H", data, 0x98, 0x20b)
    pack_into("<I", data, 0x98+112, 0x1000)
    pack_into("<IIII", data, 0x98+0xf0+8, 0x400, 0x1000, 0x400, 0x200)
    pack_into("<IIII", data, 0x200+24, 1, 0x1050, 0x1060, 0x1070)
    pack_into("<I", data, 0x250, 0x1100)
    pack_into("<I", data, 0x260, 0x1080)
    pack_into("<H", data, 0x270, 0)
    name = b"ImmSetCandidateWindow\0"
    data[0x280:0x280+len(name)] = name
    data[0x300:0x340] = bytes(range(64))
    return data


def fingerprint(data):
    with patch.object(Path, "read_bytes", return_value=bytes(data)):
        return probe.fingerprint(Path("owned-module.dll"))


class FingerprintTest(unittest.TestCase):
    def test_pe_export_is_resolved_and_fingerprinted(self):
        result = fingerprint(pe_fixture())
        self.assertRegex(result, r"^[0-9a-f]{16}$")
        self.assertEqual(result, fingerprint(pe_fixture()))

    def test_changed_export_code_changes_fingerprint(self):
        original = pe_fixture()
        modified = pe_fixture()
        modified[0x300] ^= 1
        self.assertNotEqual(fingerprint(original), fingerprint(modified))

    def test_unrelated_bytes_do_not_change_target_fingerprint(self):
        original = pe_fixture()
        modified = pe_fixture()
        modified[0x500] ^= 1
        self.assertEqual(fingerprint(original), fingerprint(modified))

    def test_later_export_region_change_is_detected(self):
        original = pe_fixture()
        modified = pe_fixture()
        modified[0x300+200] ^= 1
        self.assertNotEqual(fingerprint(original), fingerprint(modified))

    def test_missing_export_is_rejected(self):
        data = pe_fixture()
        data[0x280] = ord("X")
        with self.assertRaisesRegex(ValueError, "Export not found"):
            fingerprint(data)

    def test_invalid_function_rva_is_rejected(self):
        data = pe_fixture()
        pack_into("<I", data, 0x250, 0xffff0000)
        with self.assertRaisesRegex(ValueError, "RVA outside sections"):
            fingerprint(data)
        data = pe_fixture()
        with self.assertRaisesRegex(ValueError, "Export code is truncated"):
            fingerprint(data[:0x320])
