#!/usr/bin/env python3
import subprocess
import sys

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error running ldb command: {cmd}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

def verify_keys(db_path, cf, last_written_key):
    # Scan the given CF
    cmd = ["ldb", f"--db={db_path}", f"--column_family={cf}", "scan"]
    output = run_cmd(cmd)

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

def verify_last_applied(db_path, expected_index):
    # Read last_applied
    cmd = ["ldb", f"--db={db_path}", "get", "a1_hdr.last_applied", "--value_hex"]
    last_applied_hex = run_cmd(cmd)

    print(f"[DEBUG] Raw last_applied output: {repr(last_applied_hex)}")

    if last_applied_hex.startswith("0x") or last_applied_hex.startswith("0X"):
        last_applied_hex = last_applied_hex[2:]

    if len(last_applied_hex) < 16:
        print(f"INVALID_LAST_APPLIED_HEX: {last_applied_hex}")
        sys.exit(3)

    first_8_bytes = last_applied_hex[:16]
    last_applied_index = int.from_bytes(bytes.fromhex(first_8_bytes), "little")

    print(f"[DEBUG] Parsed last_applied_index={last_applied_index}")

    if last_applied_index != expected_index:
        print(f"LAST_APPLIED_MISMATCH last_applied_index={last_applied_index} expected={expected_index}")
        sys.exit(2)
    else:
        print(f"LAST_APPLIED_OK last_applied_index={last_applied_index}")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: verify_persistence.py <mode> <db_path> [cf] [last_written_key]")
        print("Modes: keys | last_applied")
        sys.exit(1)

    mode = sys.argv[1]
    db_path = sys.argv[2]

    if mode == "keys":
        if len(sys.argv) != 5:
            print("Usage for keys mode: verify_persistence.py keys <db_path> <cf> <last_written_key>")
            sys.exit(1)
        cf = sys.argv[3]
        last_written_key = int(sys.argv[4])
        verify_keys(db_path, cf, last_written_key)

    elif mode == "last_applied":
        if len(sys.argv) != 4:
            print("Usage for last_applied mode: verify_persistence.py last_applied <db_path> <expected_index>")
            sys.exit(1)
        expected_index = int(sys.argv[3])
        verify_last_applied(db_path, expected_index)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)