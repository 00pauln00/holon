from ansible.plugins.lookup import LookupBase
import json
import os
from datetime import datetime
import time
import subprocess
import uuid
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def start_generate_dbi(cluster_params, operation, punchAmount, punchesPer, maxPuncheSize, maxPunches,
                            maxVblks, vblkPer, vbAmount, seqStart, chunk, seed, genType):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    dirName = "dbi-dbo"
    # Get current date and time
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Create new directory name with timestamp
    new_directory_name = f'{dirName}_{timestamp}'

    path = "%s/%s/%s/" % (base_dir, raft_uuid, new_directory_name)
    # Create the new directory
    os.mkdir(path)

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dbiLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/example' % binary_dir

    process_popen = subprocess.Popen([bin_path, "-c", chunk, "-dbo", dirName, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen

def start_pattern_generator(cluster_params, operation, punchAmount, punchesPer, maxPuncheSize, maxPunches,
                            maxVblks, vblkPer, vbAmount, seqStart, chunk, seed, genType, blockSize, blockSizeMax,
                            startVblk, vblkDump, strideWidth):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    dirName = "dbi-dbo"
    # Get current date and time
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Create new directory name with timestamp
    new_directory_name = f'{dirName}_{timestamp}'

    path = "%s/%s/%s/" % (base_dir, raft_uuid, new_directory_name)
    # Create the new directory
    os.mkdir(path)

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dbiLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/example' % binary_dir

    process_popen = subprocess.Popen([bin_path, "-c", chunk, "-dbo", dirName, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                           "-vs", startVblk, "-d", vblkDump, "-sw", strideWidth], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen

def start_gc_process(cluster_params, operation, dbi_input_path):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/gcLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/gcTester' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-d', dbi_input_path], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen


def start_data_validate(cluster_params, operation, path):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dataValidateLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    bin_path = '%s/dataValidator' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-d', path], stdout = fp, stderr = fp)

    os.fsync(fp)

    return process_popen

def load_json_contents(path):
    counter = 0
    timeout = 100
    # Wait till the output json file gets created.
    while True:
        if not os.path.exists(path):
            counter += 1
            time.sleep(1)
            if counter == timeout:
                return {'outfile_status':-1}
        else:
            break

    json_data = {}
    with open(path, "r+", encoding="utf-8") as json_file:
        json_data = json.load(json_file)

    return json_data

def extracting_dictionary(cluster_params, operation, input_values):

    if operation == "generate_dbi":
       popen = start_generate_dbi(cluster_params, operation, input_values['punchAmount'], input_values['punchPer'],
                                  input_values['maxPunchSize'], input_values['maxPunches'], input_values['maxVblks'],
                                  input_values['vblkPer'], input_values['vbAmount'], input_values['seqStart'],
                                  input_values['chunk'], input_values['seed'], input_values['genType'])

    elif operation == "generate_pattern":
       popen = start_pattern_generator(cluster_params, operation, input_values['punchAmount'], input_values['punchPer'],
                                  input_values['maxPunchSize'], input_values['maxPunches'], input_values['maxVblks'],
                                  input_values['vblkPer'], input_values['vbAmount'], input_values['seqStart'],
                                  input_values['chunk'], input_values['seed'], input_values['genType'], input_values['blockSize'],
                                  input_values['blockSizeMax'], input_values['startVblk'], input_values['vblkDump'],
                                  input_values['strideWidth'])
    elif operation == "start_gc":
       popen = start_gc_process(cluster_params, operation, input_values['dbiObjPath'])

    elif operation == "data_validate":
       popen = start_data_validate(cluster_params, operation, input_values['path'])

    elif operation == "load_contents":
        print("path from recipe", input_values['path'])
        data = load_json_contents(input_values['path'])

        return data


class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        operation = terms[0]
        input_values = terms[1]

        cluster_params = kwargs['variables']['ClusterParams']

        if cluster_params['app_type'] == "gcvalidation":
            data = extracting_dictionary(cluster_params, operation, input_values)
            return data
