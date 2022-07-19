from ansible.plugins.lookup import LookupBase
import fcntl
import sys
import json
import termios
import os
import shutil, os
import time
import subprocess

def start_subprocess(cluster_params, Operation, Key, Value, OutfileName,
                     NumRequest, MultiKey, Sequential):
    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    bin_path = '%s/nkvc' % binary_dir

    # Prepare path for log file.
    log_file = "%s/%s/%s_log.txt" % (base_dir, raft_uuid, app_name)

    # Open the log file to pass the fd to subprocess.Popen
    fp = open(log_file, "w")
    logfile = "%s/%s/niovakvclientlogfile.log" % (base_dir, raft_uuid)

    # Prepare config file path for niovakv_client
    config_path = "%s/%s/niovakv.config" % (base_dir, raft_uuid)

    outfilePath = "%s/%s/%s" % (base_dir, raft_uuid, OutfileName)

    if MultiKey == False:
        if Operation == "write":
            process_popen = subprocess.Popen([bin_path,'-c', config_path,
                                             '-l', logfile, '-o', Operation, '-k', Key,
                                             '-v', Value, '-r', outfilePath , '-n', NumRequest ],
                                             stdout = fp, stderr = fp)
        elif Operation == "read":
            process_popen = subprocess.Popen([bin_path,'-c', config_path, '-o', Operation,
                                              '-l', logfile, '-k', Key, '-v', Value,
                                              '-r', outfilePath, '-n', NumRequest],
                                              stdout = fp, stderr = fp)

        elif Operation == "leader":         # operation for get leader
            process_popen = subprocess.Popen([bin_path,'-c', config_path, '-o', Operation,
                                              '-r', outfilePath],
                                              stdout = fp, stderr = fp)
        elif Operation == "membership":
            process_popen = subprocess.Popen([bin_path,'-c', config_path, '-o', Operation,
                                              '-r', outfilePath],
                                              stdout = fp, stderr = fp)
        else:
           logging.error("Invalid Operation passed to start niovakv_client: %s", Operation)
           os.fsync(fp)
           exit(1)

    elif (( MultiKey == True ) and ( Sequential == True )):

        logfile = "%s/%s/niovakvclientlogfile_multi_sequential.log" % (base_dir, raft_uuid)
        outfilePath = "%s/%s/%s" % (base_dir, raft_uuid, OutfileName)
        process_popen = subprocess.Popen([bin_path,'-c', config_path, '-l' , logfile,
                                          '-s', "y", '-n', NumRequest, '-k', Key,
                                          '-v', Value, '-r', outfilePath],
                                          stdout = fp, stderr = fp)
    else:
        logfile = "%s/%s/niovakvclientlogfile_multi_concurrent.log" % (base_dir, raft_uuid)
        outfilePath = "%s/%s/%s" % (base_dir, raft_uuid , OutfileName)
        process_popen = subprocess.Popen([bin_path,'-c', config_path, '-l', logfile,
                                          '-n', NumRequest, '-k', Key, '-v', Value,
                                          '-r' , outfilePath],
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
        Operation = terms[0]
        Key = terms[1]
        Value = terms[2]
        OutfileName = terms[3]
        NumRequest = str(terms[4])
        MultiKey = terms[5]
        Sequential = terms[6]
        cluster_params = kwargs['variables']['ClusterParams']

        # Start the niovakv_client and perform the specified operation e.g write/read/getLeader.
        process,outfile = start_subprocess(cluster_params, Operation, Key,
                                           Value, OutfileName, NumRequest,
                                           MultiKey, Sequential)
        output_data = get_the_output(outfile)


        if Operation == "write":
            return {"write":output_data['write']}
        elif Operation == "read":
            return {"read":output_data['read']}
        elif Operation == "getLeader":
            return {"getLeader":output_data['getLeader']}
        elif Operation == "membership":
            return {"membership":output_data}
        else:
            return output_data
            

        return output_data
