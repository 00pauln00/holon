from ansible.plugins.lookup import LookupBase
import fcntl
import sys
import json
import termios
import os
import shutil, os
import time
import subprocess

def start_subprocess(cluster_params, database_type, size_of_key, 
                        key_prefix, seed_random_generator, size_of_value,
                        no_of_operations, precent_put_get, no_of_concurrent_req):
    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    bin_path = '%s/lkvt' % binary_dir

    # Prepare path for log file.
    log_file = "%s/%s/%s_LKVT_log.txt" % (base_dir, raft_uuid, app_name)

    # Open the log file to pass the fd to subprocess.Popen
    fp = open(log_file, "w")
    logfile = "%s/%s/lkvtclientlogfile.log" % (base_dir, raft_uuid)

    # Prepare config file path for niovakv_client
    config_path = "%s/niovakv.config" % binary_dir

    if precent_put_get == "1":
        outfilePath = "%s/%s/lkvt_Put_outfile" % (base_dir, raft_uuid)
    elif precent_put_get == "0":
        outfilePath = "%s/%s/lkvt_Get_outfile" % (base_dir, raft_uuid)
    else : 
         outfilePath = "%s/%s/lkvt_outfile" % (base_dir, raft_uuid)

    process_popen = subprocess.Popen([bin_path, '-d', database_type, '-ks', size_of_key,
                                         '-kp', key_prefix, '-s', seed_random_generator,
                                         '-vs', size_of_value, '-n', no_of_operations, 
                                         '-pp', precent_put_get, '-c', no_of_concurrent_req,
                                         '-jp', outfilePath ,'-cp', config_path ], 
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
        database_type = str(terms[0])
        size_of_key = str(terms[1])
        key_prefix = terms[2]
        seed_random_generator = str(terms[3])
        size_of_value  = str(terms[4])
        no_of_operations = str(terms[5])
        precent_put_get = str(terms[6])
        no_of_concurrent_req = str(terms[7])
        cluster_params = kwargs['variables']['ClusterParams']

        # Start the niovakv_client and perform the specified operation e.g write/read/getLeader.
        process,outfile = start_subprocess(cluster_params, database_type, size_of_key, key_prefix,
                                             seed_random_generator, size_of_value,
                                              no_of_operations, precent_put_get, no_of_concurrent_req)

        output_data = get_the_output(outfile)

        return output_data