from ansible.plugins.lookup import LookupBase
import json
import os
from datetime import datetime
import time
import subprocess
import uuid
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def start_generate_dbi(cluster_params, operation, punchPer, maxPunchSize,
                                maxEntries, entries, seqStart, chunkNum, seed):

    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    dirName = "dbi-dbo"
    # Get current date and time
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Create new directory name with timestamp
    new_directory_name = f'{dirName}_{timestamp}'

    print("new_directory_name: ", new_directory_name)
    path = "%s/%s/%s/" % (base_dir, raft_uuid, new_directory_name)
    # Create the new directory
    os.mkdir(path)

    #print("new_directory_name: ", new_directory_name)
    print("path: ", path)
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dbiLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/example' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-pp', punchPer, '-ps', maxPunchSize, '-me', maxEntries, '-e', entries,
                                            '-ss', seqStart, '-c', chunkNum, '-seed', seed, '-p', path, '-dbo', "bin"], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen

def start_gc_process(cluster_params, operation, dbi_input_path, path):
    #TODO Modify parameters as per implementation
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/gcLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/gc' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-inputPath', dbi_input_path, '-p', path], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen


def start_gc_validate(cluster_params, operation, solutionArrFile, gc_dbi_list, dbi_generator_json):
    #TODO Modify parameters as per implementation
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/gcValidtaeLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/gc_validate' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-sa', solutionArrFile, 'gcInput', gc_dbi_list, '-jpath', dbi_generator_json], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen

def extracting_dictionary(cluster_params, operation, input_values):

    print("input_values: :", input_values)

    if operation == "generate_dbi":
       popen = start_generate_dbi(cluster_params, operation, input_values['punchPer'], input_values['maxPunchSize'],
                                         input_values['maxEntries'], input_values['entries'],
                                         input_values['seqStart'], input_values['chunkNum'], input_values['seed'])
    elif operation == "start_gc":
       popen = start_gc_process(cluster_params, operation, input_values['dbiObjPath'], input_values['Path'])

    elif operation == "gc_validate":
       popen = start_gc_validate(cluster_params, operation, input_values['solutionArrFile'], input_values['gcDBIs'], input_values['dbiGeneratorPath'])

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        operation = terms[0]
        input_values = terms[1]

        cluster_params = kwargs['variables']['ClusterParams']

        if cluster_params['app_type'] == "gcvalidation":
            extracting_dictionary(cluster_params, operation, input_values)

