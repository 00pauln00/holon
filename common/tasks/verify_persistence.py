#!/usr/bin/env python3
import subprocess
import sys

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: verify_key_persistence.py <db_path> <cf> <last_written_key>")
        sys.exit(1)

    db_path = sys.argv[1]
    cf = sys.argv[2]
    last_written_key = int(sys.argv[3])

    # Scan the given CF
    cmd = ["ldb", f"--db={db_path}", f"--column_family={cf}", "scan"]
    output = subprocess.check_output(cmd).decode("utf-8", errors="replace")

    keys = []
    for line in output.splitlines():
        if "=>" in line:
            parts = line.split("=>")
            key = parts[0].strip()
            try:
                keys.append(int(key))
            except ValueError:
                continue

    if not keys:
        print("NO_KEYS_FOUND")
        sys.exit(1)

    max_key = max(keys)

    if max_key <= last_written_key:
        print(f"KEY_OK max_key={max_key} last_written_key={last_written_key}")
        sys.exit(0)
    else:
        print(f"KEY_TOO_HIGH max_key={max_key} last_written_key={last_written_key}")
        sys.exit(2)
