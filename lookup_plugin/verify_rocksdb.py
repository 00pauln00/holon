#!/usr/bin/env python3
import subprocess
import sys
from ansible.plugins.lookup import LookupBase

def run_cmd(cmd):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
        return output
    except subprocess.CalledProcessError as e:
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
        else:
            print(f"[ERROR] Unknown key_type: {key_type}")
            return []