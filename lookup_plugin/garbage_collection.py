from ansible.plugins.lookup import LookupBase
import os
import subprocess
import logging
import re
import psutil
import signal
from lookup_plugin.helper import *

class gc_service:
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

    def start_service(self, input_params):
        try:
            download_path = os.path.join(self.base_path, "gc", "gc_download") if input_params.get("partition") else self.download_path
            bin_path = os.path.normpath(os.path.join(self.binary_dir, "GCService"))
            cmd = [
                bin_path, '-path', download_path, '-s3config', self.s3config, 
                '-s3log', self.s3_log_path, '-t', '120', '-l', '4', '-p', '7500', 
                '-b', 'paroscale-test', '-mp', str(input_params.get("total_chunks"))
            ]
            if input_params.get("dry_run"): cmd.append('-dr')
            if input_params.get("del_dbo"): cmd.append('-dd')
            if input_params.get("force_gc"): cmd.append('-f')

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

    def pause_service(self, pid):
        try:
            process_obj = psutil.Process(int(pid))
            logging.info(f"Pausing gc service {pid} by sending SIGSTOP")
            process_obj.send_signal(signal.SIGSTOP)
            return 0
        except (ValueError, psutil.NoSuchProcess) as e:
            logging.error(f"pause_gc_service: {e}")
            return -1

    def resume_service(self, pid):
        try:
            process = psutil.Process(int(pid))
            logging.info(f"Resuming gc service {pid} by sending SIGCONT")
            process.send_signal(signal.SIGCONT)
            return 0
        except (ValueError, psutil.NoSuchProcess) as e:
            logging.error(f"resume_gc_service: {e}")
            return -1

class gc_tester:
    def __init__(self, cluster_params):
        self.cluster_params = cluster_params
        self.binary_dir = os.getenv('NIOVA_BIN_PATH')
        self.base_path = os.path.join(cluster_params['base_dir'], cluster_params['raft_uuid'])
        self.download_path = os.path.join(self.base_path, "gc-download")
        self.s3_log_path = os.path.join(self.base_path, "s3_log")
        self.gc_log = os.path.join(self.base_path, "gc_logs")
        self.s3config = os.path.join(self.binary_dir, "s3.config.example")
        os.makedirs(self.download_path, exist_ok=True)

    def start_tester(self, input_params):
        try:
            bin_path = os.path.join(self.binary_dir, "gcTester")
            path = get_dir_path(self.cluster_params, DBI_DIR)
            vdev = re.findall(r'[\w-]{36}', path)[-1] if re.findall(r'[\w-]{36}', path) else None
            modified_path = modify_path(path)

            cmd = [bin_path, '-c', input_params.get("chunk"), '-v', vdev, '-s3config', self.s3config, 
                   '-path', self.download_path, '-s3log', self.s3_log_path, '-b', 'paroscale-test'] if self.cluster_params['s3Support'] == "true" else \
                  [bin_path, '-i', modified_path, '-v', vdev, '-c', input_params.get("chunk")]

            if input_params.get("debug_mode"): cmd.append('-d')
            if input_params.get("crc_check"): cmd.append('-ec=true')

            with open(self.gc_log, "a+") as fp:
                process = subprocess.Popen(cmd, stdout=fp, stderr=fp)
                return process.wait()

        except Exception as e:
            logging.error(f"Error starting GC process: {e}")
            raise

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        cmd = terms[0]
        cluster_params = kwargs['variables']['ClusterParams']
        
        if cmd == "single_exec":
            sub_cmd = terms[1]
            input_params = terms[2]
            gc = gc_tester(cluster_params)
            if sub_cmd == "start":  
                popen = gc.start_tester(input_params)
                return popen
            else:
                raise ValueError("invalid sub command")

        elif cmd == "daemon":
            sub_cmd = terms[1]
            input_params = terms[2]
            gc = gc_service(cluster_params)
            if sub_cmd == "start":
                gc.start_service(input_params)

            elif sub_cmd == "pause":
                gc.pause_service(input_params.get("pid"))

            elif cmd == "resume":
                pid = terms[2]
                gc.resume_service(input_params.get("pid"))   
            else:
                raise ValueError("invalid sub command")   
        else:
            raise ValueError("invalid command")  