from ansible.plugins.lookup import LookupBase
import json
import os
from datetime import datetime
import time
import subprocess
import uuid, random
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def start_generate_dbi(cluster_params, punchAmount, punchesPer, maxPuncheSize, maxPunches,
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

    # Wait for the process to finish and get the exit code
    exit_code = process_popen.wait()

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
        return True
    else:
        print(f"Process failed with exit code {exit_code}.")
        return False

def start_pattern_generator(cluster_params, genType):
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

    # Generate random values for the dbi pattern generation
    chunk = str(random.randint(1, 200))
    maxPunches = str(random.choice([2 ** i for i in range(6)]))
    maxVblks = str(random.choice([2 ** i for i in range(10)]))
    punchAmount = str(random.choice([2 ** i for i in range(10)])) 
    punchesPer = "0"
    maxPuncheSize = str(random.choice([2 ** i for i in range(10)]))
    seed = str(random.randint(1, 100))
    seqStart = "0"
    vbAmount = str(random.randint(1, 10000000))
    vblkPer = str(random.randint(1, 1000))
    blockSize = str(random.randint(1, 32))
    blockSizeMax = str(random.randint(1, 32))
    startVblk = "0"
    strideWidth = str(random.randint(1, 50)) 
    
    process_popen = subprocess.Popen([bin_path, "-c", chunk, "-dbo", dirName, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                           "-vs", startVblk, "-sw", strideWidth], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process_popen.wait()

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
        return True
    else:
        print(f"Process failed with exit code {exit_code}.")
        return False

def start_gc_process(cluster_params, dbi_input_path):
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

    process_popen = subprocess.Popen([bin_path, '-dir', dbi_input_path], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process_popen.wait()

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
        return True
    else:
        print(f"Process failed with exit code {exit_code}.")
        return False

def start_data_validate(cluster_params, path, gcPath):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dataValidateLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    bin_path = '%s/dataValidator' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-d', path, '-gcd', gcPath], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process_popen.wait()

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
        return True
    else:
        print(f"Process failed with exit code {exit_code}.")
        return False

def load_json_contents(path):
    counter = 0
    timeout = 200
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
       popen = start_generate_dbi(cluster_params, input_values['punchAmount'], input_values['punchPer'],
                                  input_values['maxPunchSize'], input_values['maxPunches'], input_values['maxVblks'],
                                  input_values['vblkPer'], input_values['vbAmount'], input_values['seqStart'],
                                  input_values['chunk'], input_values['seed'], input_values['genType'])

    elif operation == "generate_pattern":
       popen = start_pattern_generator(cluster_params, input_values['genType'])
    elif operation == "start_gc":
       popen = start_gc_process(cluster_params, input_values['dbiObjPath'])

    elif operation == "data_validate":
       popen = start_data_validate(cluster_params, input_values['path'], input_values['gcPath'])

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

        data = extracting_dictionary(cluster_params, operation, input_values)
        return data
