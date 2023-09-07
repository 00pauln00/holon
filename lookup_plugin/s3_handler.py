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

def get_dir_path(cluster_params, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    baseDir = os.path.join(base_dir, raft_uuid)
    dbi_dir = os.path.join(baseDir, dirName)

    # Get a list of all entries (files and directories) under the 'bin' directory
    entries = os.listdir(dbi_dir)

    # Filter out directories only
    directories = [entry for entry in entries if os.path.isdir(os.path.join(dbi_dir, entry))]

    # Check if there are any directories in the 'dbi_dir'
    if directories:
        # Return the path of the first directory found with a trailing slash
        first_directory = directories[0]
        directory_path = os.path.join(dbi_dir, first_directory, '')  # Add the trailing slash here
        return directory_path
    else:
        return None

def start_pattern_generator(cluster_params, chunkNumber, genType, s3Support, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    dbo = "bin"
    path = generate_directory_path(base_dir, raft_uuid, dirName)
    # Create the new directory
    if not os.path.exists(path):
        # Create the directory path
        try:
            os.makedirs(path)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dbiLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/example' % binary_dir
    print("path", path)
    vdev = ""
    # Generate random values for the dbi pattern generation
    jsonPath = get_dir_path(cluster_params, dirName)
    if jsonPath != None:
        if os.path.exists(jsonPath + "dummy_generator.json"):
            json_data = load_json_contents(jsonPath + "dummy_generator.json")
            chunk = str(json_data['TotalChunkSize'])
            seqStart = str(json_data['SeqEnd'] + 1)
            vdev = str(json_data['BucketName'])
    else:
        chunk = chunkNumber
        seqStart = "0"

    maxPunches = str(random.choice([2 ** i for i in range(6)]))
    maxVblks = str(random.choice([2 ** i for i in range(4)]))
    punchAmount = str(random.choice([2 ** i for i in range(6)]))
    punchesPer = "0"
    maxPuncheSize = str(random.choice([2 ** i for i in range(6)]))
    seed = str(random.randint(1, 100))
    vbAmount = str(random.randint(1, 100))
    vblkPer = str(random.randint(1, 10))
    blockSize = str(random.randint(1, 32))
    blockSizeMax = str(random.randint(1, 32))
    startVblk = "0"
    strideWidth = str(random.randint(1, 50))

    if s3Support == True:
        s3config = '%s/s3.config.example' % binary_dir
        # Prepare path for log file.
        s3LogFile = "%s/%s/s3Upload" % (base_dir, raft_uuid)
        if vdev != "":
            process = subprocess.Popen([bin_path, "-c", chunk, "-dbo", dbo, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                           "-vs", startVblk, "-sw", strideWidth, '-s3config', s3config, '-s3log',
                           s3LogFile, "-vdev", vdev], stdout = fp, stderr = fp)
        else:
            process = subprocess.Popen([bin_path, "-c", chunk, "-dbo", dbo, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                           "-vs", startVblk, "-sw", strideWidth, '-s3config', s3config, '-s3log',
                           s3LogFile], stdout = fp, stderr = fp)
    else:
        if vdev != "":
            process = subprocess.Popen([bin_path, "-c", chunk, "-dbo", dbo, "-mp", maxPunches,
                           "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                           "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                           "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                           "-vs", startVblk, "-sw", strideWidth, "-vdev", vdev], stdout = fp, stderr = fp)
        else:
            process = subprocess.Popen([bin_path, "-c", chunk, "-dbo", dbo, "-mp", maxPunches,
                               "-mv",maxVblks, "-p", path, "-pa", punchAmount, "-pp", punchesPer,
                               "-ps", maxPuncheSize, "-seed",  seed, "-ss", seqStart, "-va", vbAmount,
                               "-vp", vblkPer, "-t", genType, "-bs", blockSize, "-bsm", blockSizeMax,
                               "-vs", startVblk, "-sw", strideWidth], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.wait()
    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
    else:
        error_message = f"Process failed with exit code {exit_code}."
        raise RuntimeError(error_message)

def start_gc_process(cluster_params, s3Support, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    baseDir = os.path.join(base_dir, raft_uuid)
    debugMode = cluster_params['debugMode']
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/gcLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    jsonPath = get_dir_path(cluster_params, dirName)
    # Check if file exist or not
    if os.path.exists(jsonPath + "dummy_generator.json"):
         json_data = load_json_contents(jsonPath + "dummy_generator.json")
         vdev = str(json_data['BucketName'])
         dbo_input_path = str(json_data['DboPath'])
         dbi_input_path = str(json_data['DbiPath'])
    else:
         err_msg = f"dummy_generator.json is not present"
         raise RuntimeError(err_msg)

    bin_path = '%s/gcTester' % binary_dir

    gc_output_path = "%s/%s/GC_OUTPUT/"  % (base_dir, raft_uuid)
    if not os.path.exists(gc_output_path):
        # Create the directory path
        try:
            os.makedirs(gc_output_path)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")

    json_path = jsonPath + "/" + "dummy_generator.json"
    if s3Support == True:
         s3config = '%s/s3.config.example' % binary_dir
         # Prepare path for log file.
         s3LogFile = "%s/%s/s3Download" % (base_dir, raft_uuid)
         downloadPath = "%s/%s/" % (base_dir, raft_uuid)
         jPath = jsonPath + "dummy_generator.json"
         cmd = [bin_path, '-s3config', s3config, '-s3log', s3LogFile, '-j', jPath, '-path', downloadPath, '-o', gc_output_path]
         if debugMode:
              cmd.append('-d')

         process = subprocess.Popen(cmd, stdout = fp, stderr = fp)
    else:
         process = subprocess.Popen([bin_path, '-dbi', dbi_input_path, '-dbo',
                              dbo_input_path, '-o', gc_output_path, "-j", json_path], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.wait()

    # Close the log file
    fp.close()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
    else:
        error_message = f"Process failed with exit code {exit_code}."
        raise RuntimeError(error_message)

def start_data_validate(cluster_params, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dataValidateLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    path = get_dir_path(cluster_params, dirName)
    # Check if file exist or not
    if os.path.exists(path + "dummy_generator.json"):
         json_data = load_json_contents(path + "/" + "dummy_generator.json")
         chunkNumber = str(json_data['TotalChunkSize'])
         vdev = str(json_data['BucketName'])
    else:
         err_msg = f"dummy_generator.json is not present"
         raise RuntimeError(err_msg)

    bin_path = '%s/dataValidator' % binary_dir
    gcOpPath = "%s/%s/GC_OUTPUT/%s/" % (base_dir, raft_uuid, vdev)
    process = subprocess.Popen([bin_path, '-d', path, '-gcd', gcOpPath, '-c', chunkNumber], stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.wait()

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

def copy_DBI_file_generatorNum(cluster_params, dirName):
    jsonPath = get_dir_path(cluster_params, dirName)
    if os.path.exists(jsonPath + "dummy_generator.json"):
         json_data = load_json_contents(jsonPath + "dummy_generator.json")
         dbi_input_path = str(json_data['DbiPath'])
    else:
         err_msg = f"dummy_generator.json is not present"
         raise RuntimeError(err_msg)

    # Get a list of files in the source directory
    file_list = os.listdir(dbi_input_path)

    # Check if there are any files in the directory
    if file_list:
        # Select a random file from the list
        random_file = random.choice(file_list)

        # Split the filename by dots ('.')
        filename_parts = random_file.split(".")

        # Extract the 3rd last element after the dots
        third_last_element = filename_parts[-3]

        # Increment the extracted element by 1
        new_third_last_element = str(int(third_last_element) + 1)

        # Update the filename with the incremented element
        filename_parts[-3] = new_third_last_element
        new_filename = ".".join(filename_parts)

        # Full path for the copied and renamed file
        source_file_path = os.path.join(dbi_input_path, random_file)
        new_file_path = os.path.join(dbi_input_path, new_filename)

        # Copy the file and rename the copy
        shutil.copy(source_file_path, new_file_path)
    else:
        print("No files found in the directory.")

def extracting_dictionary(cluster_params, operation, s3Support, dirName):

    if operation == "start_gc":
       if s3Support == True:
           #input_values['dbiObjPath'] = None
           #input_values['dboObjPath'] = None
           print("s3Support in function: ", s3Support)
           popen = start_gc_process(cluster_params, s3Support, dirName)
       else:
           popen = start_gc_process(cluster_params, s3Support, dirName)

    elif operation == "data_validate":
       popen = start_data_validate(cluster_params, dirName)

    elif operation == "load_contents":
        data = load_json_contents(input_values['path'])
        return data

    elif operation == "delete_file":
        jsonPath = get_dir_path(cluster_params, dirName)
        if os.path.exists(jsonPath + "dummy_generator.json"):
            json_data = load_json_contents(jsonPath + "dummy_generator.json")
            dbi_input_path = str(json_data['DbiPath'])
            dbo_input_path = str(json_data['DboPath'])
        else:
            err_msg = f"dummy_generator.json is not present"
            raise RuntimeError(err_msg)

        delete_dir(dbi_input_path)
        delete_dir(dbo_input_path)

    elif operation == "delete_file_50Precent":
        jsonPath = get_dir_path(cluster_params, dirName)
        if os.path.exists(jsonPath + "dummy_generator.json"):
            json_data = load_json_contents(jsonPath + "dummy_generator.json")
            dbipath = str(json_data['DbiPath'])
        else:
            err_msg = f"dummy_generator.json is not present"
            raise RuntimeError(err_msg)

        file_list = os.listdir(dbipath)
        files_to_delete = len(file_list) // 2

        random.shuffle(file_list)

        for i in range(files_to_delete):
            file_to_delete = os.path.join(dbipath, file_list[i])
            os.remove(file_to_delete)

    elif operation == "copy_dbi_dbo":
        jsonPath = get_dir_path(cluster_params, dirName)
        if os.path.exists(jsonPath + "dummy_generator.json"):
            json_data = load_json_contents(jsonPath + "dummy_generator.json")
            dbipath = str(json_data['DbiPath'])
            dbopath = str(json_data['DboPath'])
            vdev  = str(json_data['BucketName'])
            chunk = str(json_data['TotalChunkSize'])
        else:
            err_msg = f"dummy_generator.json is not present"
            raise RuntimeError(err_msg)


        gcdbi = "%s/%s/GC_OUTPUT/%s/dbi/%s"  % (cluster_params['base_dir'], cluster_params['raft_uuid'], vdev, chunk)
        gcdbo = "%s/%s/GC_OUTPUT/%s/dbo/%s"  % (cluster_params['base_dir'], cluster_params['raft_uuid'], vdev, chunk)
        copy_contents(gcdbi, dbipath)
        copy_contents(gcdbo, dbopath)
        delete_dir(gcdbi)
        delete_dir(gcdbo)

    elif operation == "copy_contents":

        dbiPath = input_values['dbiObjPath']
        dboPath = input_values['dboObjPath']
        destinationdbi = input_values['dbiObjPath']
        destinationdbo = input_values['dboObjPath']
        copy_contents(dbiPath, destinationdbi)
        copy_contents(dboPath, destinationdbo)

    elif operation == "copy_DBI_file_generatorNum":
        copy_DBI_file_generatorNum(cluster_params, dirName)

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        dirName = "dbi-dbo"
        operation = terms[0]
        # Generate a random chunkNumber
        chunkNumber = str(random.randint(1, 200))

        cluster_params = kwargs['variables']['ClusterParams']
        if operation == "generate_pattern":
            input_values = terms[1]
            s3Support = terms[2]
            popen = start_pattern_generator(cluster_params, chunkNumber, input_values['genType'], s3Support, dirName)
        else:
            s3Support = terms[1]
            data = extracting_dictionary(cluster_params, operation, s3Support, dirName)
            return data
