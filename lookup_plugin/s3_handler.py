from ansible.plugins.lookup import LookupBase
import json
import os
from datetime import datetime
import time
import subprocess
import uuid, random
import shutil
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def start_generate_dbi(cluster_params, punchAmount, punchesPer, maxPuncheSize, maxPunches,
                            maxVblks, vblkPer, vbAmount, seqStart, chunk, seed, genType):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    dirName = "bin"
    # Create new directory name with timestamp
    new_directory_name = f'{dirName}'

    path = "%s/%s/%s/" % (base_dir, raft_uuid, new_directory_name)
    # Create the new directory
    if not os.path.exists(path):
        # Create the directory path
        try:
            os.makedirs(path)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")
    else:
        print(f"Directory '{path}' already exists.")

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

    dirName = "bin"
    # Create new directory name with timestamp
    new_directory_name = f'{dirName}'

    path = "%s/%s/%s/" % (base_dir, raft_uuid, new_directory_name)
    # Create the new directory
    if not os.path.exists(path):
        # Create the directory path
        try:
            os.makedirs(path)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")
    else:
        print(f"Directory '{path}' already exists.")

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dbiLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")
    if os.path.exists(path+"dummy_generator.json"):
        with open(path+"dummy_generator.json", "r+", encoding="utf-8") as json_file:
            json_data = json.load(json_file)
            print(json_data)

    #Get dummyDBI example
    bin_path = '%s/example' % binary_dir
    
    # Generate random values for the dbi pattern generation
    chunk = str(random.randint(1, 200))
    maxPunches = str(random.choice([2 ** i for i in range(4)]))
    maxVblks = str(random.choice([2 ** i for i in range(6)]))
    punchAmount = str(random.choice([2 ** i for i in range(4)])) 
    punchesPer = "0"
    maxPuncheSize = str(random.choice([2 ** i for i in range(4)]))
    seed = str(random.randint(1, 100))
    if os.path.exists(path+"dummy_generator.json"):
        with open(path+"dummy_generator.json", "r+", encoding="utf-8") as json_file:
            json_data = json.load(json_file)
            print(json_data['SeqStart'] + json_data['TotalVBLKs'])
            seqStart = str(json_data['SeqStart'] + json_data['TotalVBLKs'] - 1)
    else:
        seqStart = str(random.randint(1, 200))
    vbAmount = str(random.randint(1, 1000000))
    vblkPer = str(random.randint(1, 100))
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

def start_gc_process(cluster_params, dbi_input_path, dbo_input_path):
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
    gc_output_path = "%s/%s/GC_OUTPUT/"  % (base_dir, raft_uuid)
    if not os.path.exists(gc_output_path):
        # Create the directory path
        try:
            os.makedirs(gc_output_path)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")
    else:
        print(f"Directory '{gc_output_path}' already exists.")

    process_popen = subprocess.Popen([bin_path, '-dbi', dbi_input_path, '-dbo',
                        dbo_input_path, '-o', gc_output_path], stdout = fp, stderr = fp)

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

def start_data_validate(cluster_params, path):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dataValidateLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    bin_path = '%s/dataValidator' % binary_dir
    gcPath = "%s/%s/GC_OUTPUT"  % (base_dir, raft_uuid)

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

def delete_dir(path):
    try:
        shutil.rmtree(path)
        print(f"Directory '{path}' deleted successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

def copy_contents(source, destination):
    try:
        # List all items in the source directory
        items = os.listdir(source)
        # Iterate through each item and copy files to the destination
        for item in items:
            source_item = os.path.join(source, item)
            destination_item = os.path.join(destination, item)

            if os.path.isfile(source_item):
                shutil.copy(source_item, destination_item)  # Copy files

        print("Files copied successfully.")
    except Exception as e:
        print("An error occurred:", e)

def extracting_dictionary(cluster_params, operation, input_values):

    if operation == "generate_dbi":
       popen = start_generate_dbi(cluster_params, input_values['punchAmount'], input_values['punchPer'],
                                  input_values['maxPunchSize'], input_values['maxPunches'], input_values['maxVblks'],
                                  input_values['vblkPer'], input_values['vbAmount'], input_values['seqStart'],
                                  input_values['chunk'], input_values['seed'], input_values['genType'])

    elif operation == "generate_pattern":
       popen = start_pattern_generator(cluster_params, input_values['genType'])
    
    elif operation == "start_gc":
       popen = start_gc_process(cluster_params, input_values['dbiObjPath'], input_values['dboObjPath'])

    elif operation == "data_validate":
       popen = start_data_validate(cluster_params, input_values['path'])

    elif operation == "load_contents":
        data = load_json_contents(input_values['path'])
        return data
    
    elif operation == "delete_file":
        dbopath = input_values['path'] + "/dbo"
        dbipath = input_values['path'] + "/dbi"

        delete_dir(dbopath)
        delete_dir(dbipath)
    
    elif operation == "copy_dbi_dbo":
        gcdbi = "%s/%s/GC_OUTPUT/dbi"  % (cluster_params['base_dir'], cluster_params['raft_uuid'])
        gcdbo = "%s/%s/GC_OUTPUT/dbo"  % (cluster_params['base_dir'], cluster_params['raft_uuid'])

        dbiPath = input_values['dbiObjPath']
        dboPath = input_values['dboObjPath']
        copy_contents(gcdbi, dbiPath)
        copy_contents(gcdbo, dboPath)

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        operation = terms[0]
        input_values = terms[1]

        cluster_params = kwargs['variables']['ClusterParams']

        data = extracting_dictionary(cluster_params, operation, input_values)
    
        return data
