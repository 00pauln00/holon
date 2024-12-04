from ansible.plugins.lookup import LookupBase
import os, random
import subprocess
import logging
import psutil
import time
from genericcmd import GenericCmds
from lookup_plugin.helper import *


class Minio:
    def __init__(self, cluster_params, minio_path):
        self.cluster_params = cluster_params
        self.minio_path = minio_path
        self.base_path = f"{cluster_params['base_dir']}/{cluster_params['raft_uuid']}/"
        self.s3_server_log = f"{self.base_path}/s3_server.log"

    def start(self):
        s3Support = self.cluster_params['s3Support']
        if s3Support:
            create_dir(self.minio_path)
            command = f"minio server {self.minio_path} --console-address ':2000' --address ':2090'"
            with open(self.s3_server_log, "w") as fp:
                process_popen = subprocess.Popen(command, shell=True, stdout=fp, stderr=fp)

            if process_popen.poll() is None:
                logging.info("MinIO server started successfully in the background.")
            else:
                logging.info("MinIO server failed to start")
                raise subprocess.SubprocessError(process_popen.returncode)

            time.sleep(2)
            self._update_recipe_conf(process_popen)

    def stop(self):
        try:
            subprocess.run(["pkill", "minio"], check=True)
            logging.info("MinIO server stopped successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to stop MinIO server: {e}")

    def _update_recipe_conf(self, process_popen):
        genericcmdobj = GenericCmds()
        recipe_conf = load_recipe_op_config(self.cluster_params)

        if not "s3_process" in recipe_conf:
            recipe_conf['s3_process'] = {}

        minio_process = None
        for child in psutil.Process(process_popen.pid).children(recursive=True):
            if "minio" in child.name().lower():
                minio_process = child
                break

        if minio_process:
            minio_pid = minio_process.pid
            minio_status = minio_process.status()
            logging.info(f"MinIO server PID: {minio_pid}, Status: {minio_status}")
            recipe_conf['s3_process']['process_pid'] = minio_pid
            recipe_conf['s3_process']['process_status'] = minio_status
            genericcmdobj.recipe_json_dump(recipe_conf)


class s3_operations:
    def __init__(self, cluster_params):
        self.cluster_params = cluster_params
        self.bin_dir =  os.getenv('NIOVA_BIN_PATH')
        self.base_path = f"{cluster_params['base_dir']}/{cluster_params['raft_uuid']}/"
        self.s3_operations_log = f"{self.base_path}/s3_operation"

    def delete_dbi_set_s3(self, chunk):
        dir_path = get_dir_path(self.cluster_params, DBI_DIR)
        # TODO change the dbi dir and file name
        # the changes need to be made at the dummy generator side as the values are 
        # hardcoded at the dummy generator
        destination_dir = "dbiSetFiles"
        dbi_list_path = os.path.join(dir_path, "dbisetFname.txt")
        dbi_list = read_file_list(dbi_list_path)
        rand_dbi_path = random.choice(dbi_list)
        rand_dbi = os.path.basename(rand_dbi_path)
        dbi_prefix = rand_dbi.split('.')[0]
        # Create a list to store files with the same prefix
        dbi_set_files = [file for file in dbi_list if file.startswith(dbi_prefix)]
        with open(dbi_list_path, 'w') as file:
            for item in dbi_set_files:
                file.write(item + ", ")
        # Delete file locally
        os.remove(rand_dbi_path)
        process = self.perform_operations("delete", chunk, rand_dbi)

    def perform_operations(self, operation, chunk, path):
        if chunk != "" and path != "":
            dbi_path = get_dir_path(self.cluster_params, DBI_DIR)
            json_data = load_parameters_from_json(f"{dbi_path}/{chunk}/DV/dummy_generator.json")
            vdev = str(json_data['Vdev'])
        else: 
            vdev = ""
        bin_path = f'{self.bin_dir}/s3Operation'
        s3_config = f'{self.bin_dir}/s3.config.example'
        log_path = f'{self.s3_operations_log}_{operation}'
        cmd = [
            bin_path, '-b', 'paroscale-test', '-o', operation,
            '-v', vdev, '-c', chunk, '-s3config', s3_config, '-l', log_path, '-p', path
        ]
        print("cmd: ", cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process

    def get_markers(self, chunk, vdev):
        def process_and_get_markers(vdev, chunk):
            process = self.perform_operations("list", chunk, "m")
            exit_code = process.wait()

            if exit_code != 0:
                raise RuntimeError(f"Process failed with exit code {exit_code}.")

            stdout, _ = process.communicate()
            gc_seq = get_marker_by_type(vdev, chunk, stdout, "gc")
            nisd_seq = get_marker_by_type(vdev, chunk, stdout, "nisd")
            print("gc_seq:", gc_seq, "nisd_seq:", nisd_seq)
            return [gc_seq, nisd_seq]

        dbi_path = get_dir_path(self.cluster_params, DBI_DIR)
        if dbi_path:
            json_path = f"{dbi_path}/{chunk}/DV/dummy_generator.json"
            json_data = load_parameters_from_json(json_path)
            vdev = str(json_data.get('Vdev', vdev))  # Use the vdev from JSON if available
            return process_and_get_markers(vdev, chunk)

        if vdev:
            return process_and_get_markers(vdev, chunk)

        print("Invalid path or directory not found.")
        return False


class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        operation = terms[0]
        cluster_params = kwargs['variables']['ClusterParams']
        
        if operation == "start_minio":
            minio_path = terms[1]
            minio = Minio(cluster_params, minio_path)
            minio.start()

        elif operation == "stop_minio":
            minio = Minio(cluster_params, "")
            minio.stop()
        
        elif operation == "operation":
            operation = terms[1]
            chunk = terms[2]
            path = terms[3]
            s3 = s3_operations(cluster_params)
            process = s3.perform_operations(operation, chunk, path)
            return process
        
        elif operation == "delete_set_file":
            s3 = s3_operations(cluster_params)
            chunk = terms[1]
            s3.delete_dbi_set_s3(chunk)

        elif operation == "get_markers":
            chunk = terms[1]
            vdev = terms[2] if len(terms) > 2 else ""
            s3 = s3_operations(cluster_params)
            marker_seq = s3.get_markers(chunk, vdev)
            return marker_seq

        else:
            raise ValueError(f"Unsupported operation: {operation}")
