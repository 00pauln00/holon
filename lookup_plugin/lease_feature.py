from ansible.plugins.lookup import LookupBase
import json
import os
import time
import subprocess
import uuid
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
    #json_data = {}
    with open(outfile, "r+", encoding="utf-8") as json_file:
        json_data = json.load(json_file)

    output_data['outfile_status'] = 0
    output_data['output_data'] = json_data

    return output_data

def set_environment_variables(cluster_params):
    ctl_interface_path = "%s/%s/ctl-interface" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'])
    config_path = "%s/%s/configs" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'])

    if os.path.exists(ctl_interface_path):
        logging.info("file already exist")
    else:
        os.mkdir(niova_lookout_ctl_interface_path)

    #set environment variables
    os.environ['NIOVA_INOTIFY_BASE_PATH'] = ctl_interface_path
    os.environ['NIOVA_LOCAL_CTL_SVC_DIR'] = config_path

    return ctl_interface_path

def lease_operation(cluster_params, operation, client, resource, numOfLeases, getLeaseOutfile, outFileName):
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

    #start leaseApp process
    bin_path = '%s/leaseClient' % binary_dir

    #uuid is added at end to generate unique json file.
    outfilePath = "%s/%s/%s_%s" % (base_dir, raft_uuid, outFileName, uuid.uuid1())
    ctl_interface_path = set_environment_variables(cluster_params)

    if getLeaseOutfile == '':
         process_popen = subprocess.Popen([bin_path, '-o', operation, '-u', client, '-v', resource, '-ru', raft_uuid,
                                            '-n', numOfLeases, '-f', getLeaseOutfile, '-j', outfilePath], stdout = fp, stderr = fp)
    elif getLeaseOutfile != '':
         process_popen = subprocess.Popen([bin_path, '-o', operation, '-ru', raft_uuid,
                                              '-n', numOfLeases, '-f', getLeaseOutfile, '-j', outfilePath], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen, outfilePath

def extracting_dictionary(cluster_params, operation, input_values):
    client = ""
    resource = ""
    numOfLeases = ""
    getLeaseOutfile = ""

    if operation == "GET" or operation == "GET_VALIDATE":

        get_lease, outfile = lease_operation(cluster_params, operation, input_values['client'], input_values['resource'],
                                                            input_values['numOfLeases'], input_values['getLeaseOutfile'],
                                                            input_values['outFileName'])
        output_data = get_the_output(outfile)
        output_data['outfilePath'] = outfile
        return output_data

    if operation == "LOOKUP" or operation == "LOOKUP_VALIDATE":

        lookup_lease, outfile = lease_operation(cluster_params, operation, input_values['client'], input_values['resource'],
                                                             input_values['numOfLeases'], input_values['getLeaseOutfile'],
                                                             input_values['outFileName'])
        output_data = get_the_output(outfile)

        return output_data

    if operation == "REFRESH":

        refresh_lease, outfile = lease_operation(cluster_params, operation, input_values['client'], input_values['resource'],
                                                             input_values['numOfLeases'], input_values['getLeaseOutfile'],
                                                             input_values['outFileName'])
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
