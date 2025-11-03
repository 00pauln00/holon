import os
import subprocess
import hashlib
import time
from datetime import datetime
from pathlib import Path

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        if not terms:
            raise AnsibleError("Usage: lookup('verify_database', <base_directory>)")

        base_dir = Path(terms[0])
        config_dir = base_dir / "configs"
        cf = kwargs.get("cf", "PMDBTS_CF")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = {
            "timestamp": ts,
            "base_dir": str(base_dir),
            "config_dir": str(config_dir),
            "stores": [],
            "hash_files": {},
            "identical": True,
            "elapsed_seconds": 0,
            "messages": [],
        }

        result["messages"].append(f":mag: Reading store paths from peer files in {config_dir}")

        # === Extract store paths from peer files ===
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

        # === Start verification ===
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
                # Run ldb command
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
                with hash_file.open("w") as f:
                    f.write(hash_str + "\n")
                hash_files.append((name, str(hash_file)))
                result["hash_files"][name] = str(hash_file)
            except FileNotFoundError:
                raise AnsibleError(":x: 'ldb' command not found in PATH.")
            except Exception as e:
                result["messages"].append(f":x: Failed to hash {store}: {e}")

        # === Compare all stores pairwise ===
        identical = True
        for i in range(len(hash_files)):
            for j in range(i + 1, len(hash_files)):
                name_i, file_i = hash_files[i]
                name_j, file_j = hash_files[j]
                if not self.files_identical(file_i, file_j):
                    result["messages"].append(f":x: {name_i} and {name_j} differ!")
                    identical = False

        result["identical"] = identical
        if identical:
            result["messages"].append(":white_check_mark: All stores are identical")

        end_time = time.time()
        result["elapsed_seconds"] = int(end_time - start_time)

        result["messages"].append(f":stopwatch: Verification completed in {result['elapsed_seconds']} seconds")

        return [result]


    def files_identical(self, file1, file2):
        """Compare two files quickly (binary)."""
        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            return f1.read() == f2.read()