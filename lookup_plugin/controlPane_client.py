from ansible.plugins.lookup import LookupBase
import fcntl
import sys
import json
import termios
import os
import shutil, os
import time
import subprocess

def start_subprocess(cluster_params, IPAddress, Key, Value,
                         ConfigPath, logfile, Operation, OutfileName ):
    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    bin_path = '%s/niovakv_client' % binary_dir

    # Prepare path for log file.
    log_file = "%s/%s/%s_log.txt" % (base_dir, raft_uuid, app_name)

    # Open the log file to pass the fd to subprocess.Popen
    fp = open(log_file, "w")
    logfile = "%s/%s/niovakvclientlogfile.log" % (base_dir, raft_uuid)

    # Prepare config file path for niovakv_client
    config_path = "%s/niovakv.config" % binary_dir

    outfilePath = "%s/%s/%s" % (base_dir, raft_uuid, OutfileName)

    process_popen = subprocess.Popen([bin_path, '-k', Key,
                                             '-v', Value,'-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, outfilePath],
                                             stdout = fp, stderr = fp)

    # Sync the log file so all the logs from niovakv client gets written to log file.
    os.fsync(fp)
    return process_popen, outfilePath

def get_the_output(outfilePath):
    outfile = outfilePath+'.json'
    counter = 0
    timeout = 120

    # Wait till the output json file gets created.
    while True:
        if not os.path.exists(outfile):
            counter += 1
            time.sleep(0.1)
            if counter == timeout:
                return {"status":-1,"msg":"Timeout checking for output file"}
        else:
            break

    output_data = {}
    with open(outfile, "r+", encoding="utf-8") as json_file:
        output_data = json.load(json_file)

    return output_data

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        IPAddress = terms[0]
        Key = terms[1]
        Value = terms[2]
        ConfigPath = terms[3]
        Operation = terms[4] 
        OutfileName = terms[5]
        cluster_params = kwargs['variables']['ClusterParams']

        # Start the niovakv_client and perform the specified operation e.g write/read/getLeader.
        process,outfile = start_subprocess(cluster_params, IPAddress, Key,
                                           Value, ConfigPath, Operation , OutfileName)

        output_data = get_the_output(outfile)


        if Operation == "write":
            return {"write":output_data['write']}
        elif Operation == "read":
            return {"read":output_data['read']}
        elif Operation == "config":
            return {"config":output_data['config']}
        else:
            return output_data
            

        return output_data
