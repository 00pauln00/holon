#!/usr/bin/env python3
import subprocess
import sys
from ansible.plugins.lookup import LookupBase

def  get_kv(db_path, cf, key):
    # Scan the given CF
    cmd = ["ldb", f"--db={db_path}", f"--column_family={cf}", "scan"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        if not output.strip():
            # If stdout is empty, try stderr
            output = result.stderr
    except subprocess.CalledProcessError as e:
        pass
    
    kv = {}
    for line in output.splitlines():
        if "==>" in line:
            parts = line.split("==>")
            kv[parts[0].strip()] = parts[1].strip()
    
    print(f"[DEBUG] Found keys: {kv}")

    return kv.get(key, None)


class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        node = terms[0]
        cf = terms[1]
        key = terms[2]
        cluster_params = kwargs['variables']['ClusterParams']
        
        base_dir = cluster_params['base_dir']
        raft_uuid = cluster_params['raft_uuid']
        db_path = "{}/{}/raftdb/{}.raftdb/db".format(base_dir, raft_uuid, node)

        val = get_kv(db_path, cf, key).split(" ")

        if val is None:
            return []
        return val
