#!/usr/bin/env python3
import subprocess
import sys
from ansible.plugins.lookup import LookupBase

def run_cmd(cmd):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        try:
            output = result.stdout.decode('utf-8', errors='replace').strip()
        except UnicodeDecodeError:
            output = result.stdout.decode('latin-1', errors='replace').strip()

        if not output:
            try:
                output = result.stderr.decode('utf-8', errors='replace').strip()
            except UnicodeDecodeError:
                output = result.stderr.decode('latin-1', errors='replace').strip()

        return output
    except subprocess.CalledProcessError as e:
        stdout = e.stdout.decode('utf-8', errors='replace') if e.stdout else ''
        stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
        print(f"Error running command: {cmd}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return ""

def  get_last_written_key(db_path, cf):
    # Scan the given CF
    cmd = ["ldb", f"--db={db_path}", f"--column_family={cf}", "scan"]
    output = run_cmd(cmd)
    
    keys = []
    for line in output.splitlines():
        if "==>" in line:
            key = line.split("==>")[0].strip()
            try:
                keys.append(int(key))
            except ValueError:
                continue

    print(f"[DEBUG] Found numeric keys: {keys}")

    if not keys:
        return None
    return max(keys)

def get_last_applied_index(db_path):
    # Get the last applied index hexadecimal value
    cmd = ["ldb", f"--db={db_path}", "get", "a1_hdr.last_applied", "--value_hex"]
    last_applied_hex = run_cmd(cmd)

    if last_applied_hex.startswith(("0x", "0X")):
        last_applied_hex = last_applied_hex[2:]

    if len(last_applied_hex) < 16:
        print(f"INVALID_LAST_APPLIED_HEX: {last_applied_hex}")
        sys.exit(3)

    first_8_bytes = last_applied_hex[:16]
    last_applied_index = int.from_bytes(bytes.fromhex(first_8_bytes), "little")

    print(f"[DEBUG] Parsed last_applied_index={last_applied_index}")
    return last_applied_index

def get_counter_value(db_path, cf):
    """
    Return the value of the static 'counter' key used by the counter app.
    This verifies RYOW behavior after multiple writes.
    """

    counter_key = "counter"
    cmd = ["ldb", f"--db={db_path}", f"--column_family={cf}", "get", "counter", "--value_hex"]
    output = run_cmd(cmd)

    if output.startswith(("0x", "0X")):
        output = output[2:]

    if len(output) < 16:
        print(f"INVALID_LAST_APPLIED_HEX: {output}")
        sys.exit(3)

    first_8_bytes = output[:16]
    counter_value = int.from_bytes(bytes.fromhex(first_8_bytes), "little")

    print(f"[DEBUG] Counter key value for {counter_key}: {counter_value}")
    return counter_value

def  get_key_value(db_path, cf, key):
    # Scan the given CF
    cmd = ["ldb", f"--db={db_path}", f"--column_family={cf}", "get", key]
    output = run_cmd(cmd)

    key_value = output.split()

    print(f"[DEBUG] Key value for {key}: {key_value}")

    return key_value

def  get_all_keys(db_path, cf):
    # Scan the given CF
    cmd = ["ldb", f"--db={db_path}", f"--column_family={cf}", "scan", "--value_hex"]
    output = run_cmd(cmd)
    kv_pairs = []
    for line in output.splitlines():
        if "==>" in line:
            parts = line.split("==>")
            key = parts[0].strip()
            value = parts[1].strip()
            kv_pairs.append((key, value))

    print(f"[DEBUG] Found {len(kv_pairs)} key-value pairs.")

    if not kv_pairs:
        return None
    return kv_pairs

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        node = terms[0]
        key_type = terms[1]    # last_written_key or last_applied_index
        cluster_params = kwargs['variables']['ClusterParams']
        
        base_dir = cluster_params['base_dir']
        raft_uuid = cluster_params['raft_uuid']
        db_path = "{}/{}/raftdb/{}.raftdb/db".format(base_dir, raft_uuid, node)

        if key_type == "last_written":
            cf = terms[2]
            if not cf:
                print("[ERROR] column family must be provided for 'last_key'")
                return []
            last_key = get_last_written_key(db_path, cf)
            if last_key is None:
                return []
            return [last_key]

        elif key_type == "last_applied":
            last_applied_index = get_last_applied_index(db_path)
            if last_applied_index is None:
                return []
            return [last_applied_index]

        elif key_type == "counter_key":
            cf = terms[2] if len(terms) > 2 else "PMDBTS_CF"
            counter_val = get_counter_value(db_path, cf)
            if counter_val is None:
                return []
            return [counter_val]

        elif key_type == "lookup_key":
            cf = terms[2] 
            key = terms[3]
            if not cf:
                print("[ERROR] column family must be provided for 'lookup_key'")
                return []
            if not key:
                print("[ERROR] key must be provided for 'lookup_key'")
                return []
            key_value = get_key_value(db_path, cf, key)
            if key_value is None:
                return []
            return [key_value]

        elif key_type == "all_keys":
            cf = terms[2]
            if not cf:
                print("[ERROR] column family must be provided for 'lookup_key'")
                return []
            keys = get_all_keys(db_path, cf)
            if keys is None:
                return []
            return [keys]

        else:
            print(f"[ERROR] Unknown key_type: {key_type}")
            return []