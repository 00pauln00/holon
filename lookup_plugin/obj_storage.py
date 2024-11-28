from ansible.plugins.lookup import LookupBase
import os
import subprocess
import logging
import psutil
import time
from genericcmd import GenericCmds
import helper

DBI_DIR = "dbi-dbo"

class Minio:
    def __init__(self, cluster_params, minio_path):
        self.cluster_params = cluster_params
        self.minio_path = minio_path
        self.base_path = f"{cluster_params['base_dir']/cluster_params['raft_uuid']/"
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
        self.base_path = f"{cluster_params['base_dir']/cluster_params['raft_uuid']/"
        self.s3_operations_log = f"{self.base_path}/s3_operations.log"


    def perform_operations(self, operation, chunk, path):
        dbi_path = get_dir_path(self.cluster_params, DBI_DIR)
        json_data = load_json_contents(f"{dbi_path}/{chunk}/DV/dummy_generator.json")
        vdev = str(json_data['Vdev'])
        bin_path = f'{self.bin_dir}/s3Operation'
        s3_config = f'{self.bin_dir}/s3.config.example'
        
        cmd = [
            bin_path, '-bucketName', 'paroscale-test', '-operation', operation,
            '-v', vdev, '-c', chunk, '-s3config', s3_config, '-l', self.s3_operations_log, '-p', path
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process



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

        elif operation == "s3_operation":
            operation = terms[1]
            chunk = terms[2]
            path = terms[3]
            s3 = s3_operations(cluster_params)
            process = s3.perform_operations(operation, chunk, path)
            return process

        else:
            raise ValueError(f"Unsupported operation: {operation}")
