from ansible.plugins.lookup import LookupBase
import os, random
import subprocess
import logging
import psutil
import time
from genericcmd import GenericCmds
from lookup_plugin.helper import *

GET_VDEV = "get_vdev_from_dummy_generator.json"

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

    def delete_dbi_set_s3(self, input_param):
        dir_path = get_dir_path(self.cluster_params, DBI_DIR)
        dbi_list_path = os.path.join(dir_path, DBI_SET_LIST)
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
        input_param['path'] = rand_dbi
        input_param['vdev'] = GET_VDEV
        process = self.perform_operations("delete", input_param)

    def get_dbi_list(self, input_param):
        input_param['path'] = "GET_VDEV"
        input_param['vdev'] = GET_VDEV
        stdout = self.perform_operations("list", input_param)
        return stdout

    def delete_half_dbis(self, input_param):
        # Split the output into lines
        list_output = input_param['output']
        lines = list_output.splitlines()

        # Get half of the lines
        half_lines = lines[:len(lines) // 2]
        dbi_path = os.path.join(self.base_path, "gc-download")
        # Print half of the lines
        for file in half_lines:
           if os.path.basename(file) == "solutionArray":
               continue 
           obj = os.path.join(dbi_path, file)
           file_paths = [obj+".i", obj+".o"]
           for f in file_paths:
               os.remove(f)
           input_param['path'] = file
           input_param['vdev'] = GET_VDEV 
           process = self.perform_operations("delete", input_param) 
        

    def perform_operations(self, operation, input_param):
        vdev = input_param.get('vdev')
        if vdev == GET_VDEV:
            dbi_path = get_dir_path(self.cluster_params, DBI_DIR)
            json_data = load_parameters_from_json(f"{dbi_path}/{input_param['chunk']}/DV/dummy_generator.json")
            vdev = str(json_data['Vdev'])
        elif vdev == None:
            vdev = ""
        bin_path = f'{self.bin_dir}/s3Operation'
        s3_config = f'{self.bin_dir}/s3.config.example'
        log_path = f'{self.s3_operations_log}_{operation}'
        outputfile = f'{self.base_path}/stdout.txt'
        if input_param['path'] == "GET_VDEV":
            input_param['path'] = f"{vdev}/{input_param['chunk']}"
        cmd = [
            bin_path, '-b', 'paroscale-test', '-o', operation,
            '-v', vdev, '-c', input_param['chunk'], '-s3config', s3_config, '-l', log_path, '-p', input_param['path']
        ]
        with open(outputfile, "w") as outfile:
            process = subprocess.Popen(cmd, stdout=outfile, stderr=subprocess.PIPE, text=True)
            # Wait for process to complete if necessary
            process.wait()
  
        # Read the output file
        with open(outputfile, "r") as outfile:
            process_stdout = outfile.read()
            return process_stdout

    def get_markers(self, input_param):
        def process_and_get_markers(input_param):
            input_param['path'] = "m"
            stdout = self.perform_operations("list", input_param)

            gc_seq = get_marker_by_type(input_param['vdev'], input_param['chunk'], stdout, "gc")
            nisd_seq = get_marker_by_type(input_param['vdev'], input_param['chunk'], stdout, "nisd")
            print("gc_seq:", gc_seq, "nisd_seq:", nisd_seq)
            return [gc_seq, nisd_seq]
        
        if input_param.get('vdev') != None:
            return process_and_get_markers(input_param)
        else:
            dbi_path = get_dir_path(self.cluster_params, DBI_DIR)
            if dbi_path:
                json_path = f"{dbi_path}/{input_param['chunk']}/DV/dummy_generator.json"
                json_data = load_parameters_from_json(json_path)
                input_param['vdev'] = str(json_data.get('Vdev', input_param.get('vdev', 'default_value')))  # Use the vdev from JSON if available
                return process_and_get_markers(input_param)

            print("Invalid path or directory not found.")
            return False


class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        command = terms[0]
        cluster_params = kwargs['variables']['ClusterParams']
        
        if command == "minio":
            sub_cmd  = terms[1]
            if sub_cmd == "start":
                minio_path = terms[2]
                minio = Minio(cluster_params, minio_path)
                minio.start()

            elif sub_cmd == "stop":
                minio = Minio(cluster_params, "")
                minio.stop()
        
        elif command == "operation":
            operation = terms[1]
            input_param = terms[2]
            s3 = s3_operations(cluster_params)
            if operation == "create_bucket":
                input_param['path'] = ""
                process = s3.perform_operations(operation, input_param)
            else: 
                input_param['vdev'] = GET_VDEV
                process = s3.perform_operations(operation, input_param)
            return process
        
        elif command == "delete_set_file":
            input_param = terms[1]
            s3 = s3_operations(cluster_params)
            s3.delete_dbi_set_s3(input_param)

        elif command == "get_markers":
            input_param = terms[1]
            s3 = s3_operations(cluster_params)
            marker_seq = s3.get_markers(input_param)
            return marker_seq

        elif command == "get_list":
            input_param = terms[1]
            s3 = s3_operations(cluster_params)
            list_op = s3.get_dbi_list(input_param)
            return list_op

        elif command == "delete_half_files":
            input_param = terms[1]
            s3 = s3_operations(cluster_params)
            s3.delete_half_dbis( input_param )

        else:
            raise ValueError(f"Unsupported operation: {command}")
