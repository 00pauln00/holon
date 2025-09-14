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
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        if not output.strip():
            # If stdout is empty, try stderr
            output = result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running ldb command: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

    # Debug: print the raw output
    print(f"[DEBUG] Raw ldb output: {repr(output)}")
    
    keys = []
    for line in output.splitlines():
        if "==>" in line:
            parts = line.split("==>")
            key = parts[0].strip()
            try:
                keys.append(int(key))
            except ValueError:
                continue
    
    print(f"[DEBUG] Found keys: {keys}")

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
