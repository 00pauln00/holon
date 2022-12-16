from ansible.plugins.lookup import LookupBase
import json
import os
import time
import subprocess
from genericcmd import *
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def get_the_output(outfilePath):
    outfile = outfilePath + '.json'
    counter = 0
    timeout = 100

    # Wait till the output json file gets created.
    while True:
        if not os.path.exists(outfile):
            counter += 1
            time.sleep(1)
            if counter == timeout:
                return {'outfile_status':-1}
        else:
            break

    output_data = {}
    json_data = {}
    with open(outfile, "r+", encoding="utf-8") as json_file:
        output_data = json.load(json_file)
    json_data['outfile_status'] = 0
    json_data['output_data'] = output_data

    return json_data

def lease_operation(cluster_params, operation):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    app_name = cluster_params['app_type']

    genericcmdobj = GenericCmds()
    
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    log_file = "%s/%s/%s_log.txt" % (base_dir, raft_uuid, operation)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")
    
    #start niova block test process
    bin_path = '%s/leaseApp' % binary_dir
        
    if operation = "get_lease":
        process_popen = subprocess.Popen([bin_path, '-u', client, '-v', resource, '-ru', raft_uuid], stdout = fp, stderr = fp)
    
    elif operation = "lookup_lease":
        process_popen = subprocess.Popen([bin_path,'-v', resource, '-ru', raft_uuid], stdout = fp, stderr = fp)
    
    else:
        process_popen = subprocess.Popen([bin_path, '-u', client, '-v', resource, '-ru', raft_uuid], stdout = fp, stderr = fp)

    os.fsync(fp)

def extracting_dictionary(cluster_params, operation, input_values):
    client = ""
    resource = ""

    if operation = "get_lease":

        get_lease = lease_operation(operation, input_values['client'], input_values['resource'])
        output_data = get_the_output(outfile)

        return output_data

    if operation = "lookup_lease":
            
        lookup_lease = lease_operation(operation, input_values['resource'])
        output_data = get_the_output(outfile)
            
        return output_data

    if operation = "refresh_lease":
            
        refresh_lease = lease_operation(operation, input_values['resource'])
        output_data = get_the_output(outfile)
            
        return output_data


class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        operation = terms[0]
        input_values = terms[1]

        cluster_params = kwargs['variables']['ClusterParams']

        data = extracting_dictionary(cluster_params, operation, input_values)

        return data
