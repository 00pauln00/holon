from ansible.plugins.lookup import LookupBase
import json
import os, random
from datetime import datetime
import time
import subprocess
import uuid, random
import shutil
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def generate_directory_path(base_dir, raft_uuid, dirName):
    new_directory_name = dirName

    path = "%s/%s/%s/" % (base_dir, raft_uuid, new_directory_name)
    return path

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

def start_pattern_generator(cluster_params, chunkNumber, genType, s3Support):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    dirName = "bin"
    path = generate_directory_path(base_dir, raft_uuid, dirName)
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

    # Generate random values for the dbi pattern generation
    if os.path.exists(path + "dummy_generator.json"):
         json_data = load_json_contents(path + "dummy_generator.json")
         chunk = str(json_data['TotalChunkSize'])
    else:
        chunk = chunkNumber
    maxPunches = str(random.choice([2 ** i for i in range(2)]))
    maxVblks = str(random.choice([2 ** i for i in range(3)]))
    punchAmount = str(random.choice([2 ** i for i in range(2)]))
    punchesPer = "0"
    maxPuncheSize = str(random.choice([2 ** i for i in range(2)]))
    seed = str(random.randint(1, 100))
    if os.path.exists(path+"dummy_generator.json"):
        json_data = load_json_contents(path + "dummy_generator.json")
        seqStart = str(json_data['SeqStart'] + json_data['TotalVBLKs'])
    else:
        seqStart = "0"
    vbAmount = str(random.randint(1, 1000))
    vblkPer = str(random.randint(1, 10))
    blockSize = str(random.randint(1, 32))
    blockSizeMax = str(random.randint(1, 32))
    startVblk = "0"
    strideWidth = str(random.randint(1, 50))

    if s3Support == True:
        s3config = '%s/s3.config.example' % binary_dir
        # Prepare path for log file.
        s3LogFile = "%s/%s/s3Upload" % (base_dir, raft_uuid)

        process = subprocess.run([bin_path, "-c", chunk, "-dbo", dirName, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                           "-vs", startVblk, "-sw", strideWidth, '-s3config', s3config, '-s3log',
                           s3LogFile, '-bn', chunk], stdout = fp, stderr = fp)
    else:
        process = subprocess.run([bin_path, "-c", chunk, "-dbo", dirName, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                           "-vs", startVblk, "-sw", strideWidth], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.returncode

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
    else:
        error_message = f"Process failed with exit code {exit_code}."
        raise RuntimeError(error_message)

def start_gc_process(cluster_params, chunkNumber, dbi_input_path, dbo_input_path, s3Support):
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

    if s3Support == True:
         s3config = '%s/s3.config.example' % binary_dir
         # Prepare path for log file.
         s3LogFile = "%s/%s/s3Download" % (base_dir, raft_uuid)
         downloadPath = "%s/%s/" % (base_dir, raft_uuid)
         path = generate_directory_path(base_dir, raft_uuid, "bin")
         # Generate random values for the dbi pattern generation
         if os.path.exists(path + "dummy_generator.json"):
              json_data = load_json_contents(path + "dummy_generator.json")
              chunkNumber = str(json_data['TotalChunkSize'])
         else:
             print("dummy_generator.json is not present")
         process = subprocess.run([bin_path, '-s3config', s3config, '-s3log',
                              s3LogFile, '-bn', chunkNumber, '-path', downloadPath], stdout = fp, stderr = fp)
    else:
         process = subprocess.run([bin_path, '-dbi', dbi_input_path, '-dbo',
                              dbo_input_path, '-o', gc_output_path], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.returncode

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
    else:
        error_message = f"Process failed with exit code {exit_code}."
        raise RuntimeError(error_message)

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

    process = subprocess.run([bin_path, '-d', path, '-gcd', gcPath], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.returncode

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
    else:
        error_message = f"Process failed with exit code {exit_code}."
        raise RuntimeError(error_message)

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

def extracting_dictionary(cluster_params, operation, chunkNumber, input_values, s3Support):

    if operation == "generate_pattern":
       popen = start_pattern_generator(cluster_params, chunkNumber, input_values['genType'], s3Support)

    elif operation == "start_gc":
       if s3Support == True:
           input_values['dbiObjPath'] = None
           input_values['dboObjPath'] = None
           popen = start_gc_process(cluster_params, chunkNumber, input_values['dbiObjPath'], input_values['dboObjPath'], s3Support)
       else:
           popen = start_gc_process(cluster_params, chunkNumber, input_values['dbiObjPath'], input_values['dboObjPath'], s3Support)

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

    elif operation == "delete_file_50Precent":
        dbipath = input_values['path'] + "/dbi"
        file_list = os.listdir(dbipath)
        files_to_delete = len(file_list) // 2

        random.shuffle(file_list)

        for i in range(files_to_delete):
            file_to_delete = os.path.join(directory_path, file_list[i])
            os.remove(file_to_delete)

    elif operation == "copy_dbi_dbo":
        gcdbi = "%s/%s/GC_OUTPUT/dbi"  % (cluster_params['base_dir'], cluster_params['raft_uuid'])
        gcdbo = "%s/%s/GC_OUTPUT/dbo"  % (cluster_params['base_dir'], cluster_params['raft_uuid'])

        dbiPath = input_values['dbiObjPath']
        dboPath = input_values['dboObjPath']
        copy_contents(gcdbi, dbiPath)
        copy_contents(gcdbo, dboPath)

    elif operation == "copy_contents":
        dbiPath = input_values['dbiObjPath']
        dboPath = input_values['dboObjPath']
        destinationdbi = input_values['dbiObjPath']
        destinationdbo = input_values['dboObjPath']
        copy_contents(dbiPath, destinationdbi)
        copy_contents(dboPath, destinationdbo)

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        operation = terms[0]
        input_values = terms[1]
        s3Support = terms[2]

        # Generate a random chunkNumber
        chunkNumber = str(random.randint(1, 200))

        cluster_params = kwargs['variables']['ClusterParams']

        data = extracting_dictionary(cluster_params, operation, chunkNumber, input_values, s3Support)

        return data
