#!/usr/bin/env python3
import subprocess
import sys
import hashlib
import time
from datetime import datetime
from pathlib import Path
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

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

def files_identical(file1, file2):
        """Compare two files quickly (binary)."""
        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            return f1.read() == f2.read()

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

def verify_consistency(base_dir):
        base_path = Path(base_dir)
        config_dir = base_path / "configs"
        cf = "PMDBTS_CF"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = {
            "timestamp": ts,
            "base_dir": str(base_path),
            "config_dir": str(config_dir),
            "stores": [],
            "hash_files": {},
            "identical": True,
            "elapsed_seconds": 0,
            "messages": [],
        }

        result["messages"].append(f":mag: Reading store paths from peer files in {config_dir}")

        # === Extract store paths ===
        stores = []
        store_names = []

        for peer_file in config_dir.glob("*.peer"):
            try:
                with peer_file.open() as f:
                    for line in f:
                        if line.strip().startswith("STORE"):
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                store_path = Path(parts[1])
                                store_dir = store_path.parent.name
                                peer_id = store_path.stem
                                name = f"{store_dir}_{peer_id}"
                                db_path = str(store_path / "db")
                                stores.append(db_path)
                                store_names.append(name)
            except Exception as e:
                result["messages"].append(f":warning: Could not read {peer_file}: {e}")

        if not stores:
            raise AnsibleError(f":x: No store paths found in {config_dir}")

        result["messages"].append(f":white_check_mark: Found {len(stores)} stores")
        for name, store in zip(store_names, stores):
            result["messages"].append(f"  {name}: {store}")
            result["stores"].append({"name": name, "path": store})

        # === Compute hashes ===
        start_time = time.time()
        hash_files = []

        for name, store in zip(store_names, stores):
            result["messages"].append(f":package: Scanning {name} ...")
            store_path = Path(store)
            if not store_path.exists():
                result["messages"].append(f":warning: Store path {store} not found, skipping")
                continue

            hash_file = store_path / f"hash_{ts}.sha256"
            try:
                ldb_proc = subprocess.Popen(
                    ["ldb", f"--db={store}", f"--column_family={cf}", "scan", "--hex"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                sha_proc = subprocess.Popen(
                    ["sha256sum"],
                    stdin=ldb_proc.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = sha_proc.communicate()
                if sha_proc.returncode != 0:
                    raise RuntimeError(f"sha256sum failed: {stderr.decode()}")

                hash_str = stdout.decode().strip()
                result["messages"].append(f":key: Hash for {name}: {hash_str}")  # show hash value

                with hash_file.open("w") as f:
                    f.write(hash_str + "\n")
                hash_files.append((name, str(hash_file)))
                result["hash_files"][name] = str(hash_file)

            except FileNotFoundError:
                raise AnsibleError(":x: 'ldb' command not found in PATH.")
            except Exception as e:
                result["messages"].append(f":x: Failed to hash {store}: {e}")

        # === Compare hashes pairwise ===
        identical = True
        for i in range(len(hash_files)):
            for j in range(i + 1, len(hash_files)):
                name_i, file_i = hash_files[i]
                name_j, file_j = hash_files[j]
                if not files_identical(file_i, file_j):
                    result["messages"].append(f":x: {name_i} and {name_j} differ!")
                    identical = False

        result["identical"] = identical
        if identical:
            result["messages"].append(":white_check_mark: All stores are identical")

        end_time = time.time()
        result["elapsed_seconds"] = int(end_time - start_time)
        result["messages"].append(f":stopwatch: Verification completed in {result['elapsed_seconds']} seconds")

        return result

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        key_type = terms[0]    
        cluster_params = kwargs['variables']['ClusterParams']

        base_dir = cluster_params['base_dir']
        raft_uuid = cluster_params['raft_uuid']
        config_dir = "{}/{}".format(base_dir, raft_uuid)

        if key_type == "verify_consistency":
            result = verify_consistency(config_dir)
            return [result]

        else:
            node = terms[1]
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