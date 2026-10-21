#!/usr/bin/env python3
"""Optional per-prefix repaint adapter. Observes geometry, never changes it."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time


class ClientWindows:
    def __init__(self):
        self.bounds = {}

    @staticmethod
    def client(window):
        return window.get("app_id") == "battle.net.exe" and window.get("title") == "战网"

    def accept(self, event):
        before = self.bounds.copy()
        if "WindowsChanged" in event:
            self.bounds.clear()
            for window in event["WindowsChanged"]["windows"]:
                self.window(window)
        elif "WindowOpenedOrChanged" in event:
            self.window(event["WindowOpenedOrChanged"]["window"])
        elif "WindowClosed" in event:
            self.bounds.pop(event["WindowClosed"]["id"], None)
        elif "WindowLayoutsChanged" in event:
            for identifier, layout in event["WindowLayoutsChanged"]["changes"]:
                if identifier in self.bounds:
                    self.bounds[identifier] = tuple(layout["window_size"])
        return self.bounds != before

    def window(self, window):
        identifier = window["id"]
        if self.client(window):
            self.bounds[identifier] = tuple(window["layout"]["window_size"])
        else:
            self.bounds.pop(identifier, None)


def state_lock(prefix):
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "utopia"
    digest = hashlib.sha256(os.fsencode(prefix.resolve())).hexdigest()[:16]
    return state / f"battlenet-repaint-{digest}.lock"


def stop(prefix):
    try:
        pid = int(state_lock(prefix).read_text())
        command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        if not any(Path(os.fsdecode(arg)).name == "battlenet-repaint.py" for arg in command if arg):
            return
        index = command.index(b"--prefix")
        if Path(os.fsdecode(command[index + 1])).resolve() == prefix.resolve():
            os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError, IndexError):
        return


def run(prefix, runner, helper, verbose=False):
    prefix = prefix.resolve()
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG="-all")
    for key in ("WINEARCH", "WINEDLLOVERRIDES", "WINELOADER", "WINESERVER"):
        env.pop(key, None)
    lock = state_lock(prefix)
    lock.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with lock.open("a") as held:
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        held.seek(0)
        held.truncate()
        held.write(str(os.getpid()))
        held.flush()
        process = subprocess.Popen(["niri", "msg", "--json", "event-stream"],
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        windows = ClientWindows()
        buffer = b""
        due = None
        idle = time.monotonic()
        try:
            while True:
                now = time.monotonic()
                if not windows.bounds and now - idle > 45:
                    break
                if windows.bounds:
                    idle = now
                if due is not None and now >= due:
                    due = None
                    if windows.bounds:
                        try:
                            result = subprocess.run([str(runner), str(helper), "--once"], env=env,
                                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, timeout=3)
                            if result.returncode not in (0, 1):
                                break
                            if verbose:
                                print("repaint request", result.returncode, flush=True)
                        except (OSError, subprocess.TimeoutExpired):
                            break
                ready, _, _ = select.select([process.stdout], [], [], .1)
                if not ready:
                    if process.poll() is not None:
                        break
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                buffer += chunk
                if len(buffer) > 4 * 1024 * 1024:
                    break
                while b"\n" in buffer:
                    row, buffer = buffer.split(b"\n", 1)
                    try:
                        changed = windows.accept(json.loads(row))
                    except (ValueError, KeyError, TypeError):
                        continue
                    if changed:
                        due = time.monotonic() + .4 if windows.bounds else None
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--runner", type=Path)
    parser.add_argument("--helper", type=Path)
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.stop:
        stop(args.prefix)
    elif args.runner and args.helper and args.prefix.joinpath("system.reg").is_file() and args.runner.is_file() and args.helper.is_file():
        def terminate(*unused):
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, terminate)
        try:
            run(args.prefix, args.runner, args.helper, args.verbose)
        except KeyboardInterrupt:
            pass
