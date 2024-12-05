from ansible.plugins.lookup import LookupBase
import os
import subprocess
import logging
import re
import psutil
import signal
from lookup_plugin.helper import *

class garbage_collection:
    def __init__(self, cluster_params):
        self.cluster_params = cluster_params
        self.s3_support = cluster_params['s3Support']
        self.app_name = cluster_params['app_type']
        self.binary_dir = os.getenv('NIOVA_BIN_PATH')
        self.base_path = os.path.join(cluster_params['base_dir'], cluster_params['raft_uuid'])
        self.gc_log = os.path.join(self.base_path, "gc_logs")
        self.s3_log_path = os.path.join(self.base_path, "s3_log")
        self.download_path = os.path.join(self.base_path, "gc-download")
        self.s3config = os.path.join(self.binary_dir, "s3.config.example")
        os.makedirs(self.download_path, exist_ok=True)

    def start_gc_service(self, dry_run, del_dbo, partition, force_gc, total_chunks):
        try:
            if partition:
                download_path = os.path.join(self.base_path, "gc", "gc_download")
            else:
                download_path = self.download_path

            bin_path = os.path.normpath(os.path.join(self.binary_dir, "GCService"))
            cmd = [
                bin_path, '-path', download_path, '-s3config', self.s3config, 
                '-s3log', self.s3_log_path, '-t', '120', '-l', '4', '-p', '7500', 
                '-b', 'paroscale-test', '-mp', str(total_chunks)
            ]
            if dry_run:
                cmd.append('-dr')
            if del_dbo:
                cmd.append('-dd')
            if force_gc:
                cmd.append('-f')

            with open(self.gc_log, "a+") as fp:
                process_popen = subprocess.Popen(cmd, stdout=fp, stderr=fp)
                if process_popen.poll() is None:
                    logging.info("gcService process started successfully")
                else:
                    logging.error("gcService failed to start")
                    raise subprocess.SubprocessError(process_popen.returncode)

                # Update and save recipe config
                recipe_conf = load_recipe_op_config(self.cluster_params)
                pid = process_popen.pid
                ps = psutil.Process(pid)
                recipe_conf['gcService_process'] = {
                    'process_pid': pid,
                    'process_type': "gcService",
                    'process_app_type': self.app_name,
                    'process_status': ps.status()
                }
                genericcmdobj = GenericCmds()
                genericcmdobj.recipe_json_dump(recipe_conf)
                os.fsync(fp)

        except Exception as e:
            logging.error(f"Error starting gcService process: {e}")
            raise 

    def pause_gc_service(self, pid):
        try:
            pid = int(pid)  # Convert string pid to integer
        except ValueError:
            logging.error(f"pause_gc_service: Invalid PID format: {pid}")
            return -1

        try:
            process_obj = psutil.Process(pid)
        except psutil.NoSuchProcess:
            logging.error(f"pause_gc_service: Process with PID {pid} not found")
            return -1

        logging.info(f"Pausing gc service {pid} by sending SIGSTOP")
        try:
            process_obj.send_signal(signal.SIGSTOP)
            return 0
        except Exception as e:  # Catch unexpected errors
            logging.error(f"pause_gc_service: Error pausing process: {e}")
            return -1

    def resume_gc_service(self, pid):
        try:
            pid = int(pid)  # Convert string pid to integer
        except ValueError:
            logging.error(f"resume_gc_service: Invalid PID format: {pid}")
            return -1

        try:
            process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            logging.error(f"resume_gc_service: Process with PID {pid} not found")
            return -1

        logging.info(f"Resuming gc service {pid} by sending SIGCONT")

        try:
            process.send_signal(signal.SIGCONT)
            return 0
        except Exception as e:  # Catch unexpected errors
            logging.error(f"resume_gc_service: Unexpected error: {e}")
            return -1

    def start_gc_tester(self, debug_mode, chunk, crcCheck=None):
        try:
            bin_path = os.path.join(self.binary_dir, "gcTester")
            path = get_dir_path(self.cluster_params, DBI_DIR)
            matches = re.findall(r'[\w-]{36}', path)
            vdev = matches[-1] if matches else None
            modified_path = modify_path(path)

            if self.s3_support == "true":
                cmd = [
                    bin_path, '-c', chunk, '-v', vdev, '-s3config', self.s3config, 
                    '-path', self.download_path, '-s3log', self.s3_log_path, '-b', 'paroscale-test'
                ]
            else:
                cmd = [bin_path, '-i', modified_path, '-v', vdev, '-c', chunk]

            if debug_mode:
                cmd.append('-d')
            if crcCheck:
                cmd.append('-ec=true')

            with open(self.gc_log, "a+") as fp:
                process = subprocess.Popen(cmd, stdout=fp, stderr=fp)
                exit_code = process.wait()
                return exit_code

        except Exception as e:
            logging.error(f"Error starting GC process: {e}")
            raise

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        operation = terms[0]
        cluster_params = kwargs['variables']['ClusterParams']
        gc = garbage_collection(cluster_params)
        
        if operation == "tester":
            if len(terms) >= 3:
               debug = terms[1]
               chunk = terms[2]
               crc_check = terms[3] if len(terms) > 3 else None
               popen = gc.start_gc_tester(dirName, debug, chunk, crc_check)
               return popen
            else:
               raise ValueError("not enough arguments provided to start gc tester")

        elif operation == "service":
            dry_run = terms[1]
            del_dbo = terms[2]
            partition = terms[3]
            total_chunks = terms[4]
            force_gc = terms[5]
            gc.start_gc_service(dry_run, del_dbo, partition, force_gc, total_chunks)

        elif operation == "pause":
            pid = terms[1]
            gc.pause_gc_service(pid)

        elif operation == "resume":
            pid = terms[1]
            gc.resume_gc_service(pid)      