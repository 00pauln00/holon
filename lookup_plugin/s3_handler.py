from ansible.plugins.lookup import LookupBase
import json
import os, random, psutil
from datetime import datetime
import time
import subprocess
import uuid, random
import shutil
from genericcmd import *
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def load_recipe_op_config(cluster_params):
    recipe_conf = {}
    raft_json_fpath = "%s/%s/%s.json" % (cluster_params['base_dir'],
                                         cluster_params['raft_uuid'],
                                         cluster_params['raft_uuid'])
    if os.path.exists(raft_json_fpath):
        with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
            recipe_conf = json.load(json_file)

    return recipe_conf

def start_minio_server(cluster_params, dirName):
    s3Support = cluster_params['s3Support']
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for log file.
    s3_server = "%s/%s/s3Server.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(s3_server, "w")

    if s3Support:
        # Check if the directory exists, and if not, create it.
        if not os.path.exists(os.path.expanduser(f'~/{dirName}')):
            os.makedirs(os.path.expanduser(f'~/{dirName}'))

        command = f"minio server ~/{dirName} --console-address ':9090' --address ':9000'"

        process_popen = subprocess.Popen(command, shell=True, stdout=fp, stderr=fp)

        # Check if MinIO process started successfully
        if process_popen.poll() is None:
            logging.info("MinIO server started successfully in the background.")
        else:
            logging.info("MinIO server failed to start")
            raise subprocess.SubprocessError(process_popen.returncode)

        # Wait for a short time to ensure the MinIO process has started.
        time.sleep(2)
        genericcmdobj = GenericCmds()
        recipe_conf = load_recipe_op_config(cluster_params)

        if not "s3_process" in recipe_conf:
            recipe_conf['s3_process'] = {}

        # Find the MinIO server process using psutil
        minio_process = None
        for child in psutil.Process(process_popen.pid).children(recursive=True):
            if "minio" in child.name().lower():
                minio_process = child
                break

        if minio_process:
            minio_pid = minio_process.pid
            minio_status = minio_process.status()
            logging.info(f"MinIO server PID: {minio_pid}, Status: {minio_status}")
            recipe_conf['s3_process']['process_pid'] = minio_pid
            recipe_conf['s3_process']['process_status'] = minio_status
            genericcmdobj.recipe_json_dump(recipe_conf)
        else:
            logging.info("MinIO server process not found")

    return process_popen

def get_dir_path(cluster_params, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    baseDir = os.path.join(base_dir, raft_uuid)
    dbi_dir = os.path.join(baseDir, dirName)

    # Get a list of all entries (files and directories) under the 'dbi-dbo' directory
    entries = os.listdir(dbi_dir)

    # Filter out directories only
    directories = [entry for entry in entries if os.path.isdir(os.path.join(dbi_dir, entry))]

    # Check if there are any directories in the
    if directories:
        # Return the path of the first directory found with a trailing slash
        first_directory = directories[0]
        directory_path = os.path.join(dbi_dir, first_directory, '')  # Add the trailing slash here
        return directory_path
    else:
        return None

def start_pattern_generator(cluster_params, chunkNumber, genType, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']

    dbo = "bin"
    path = "%s/%s/%s/" % (base_dir, raft_uuid, dirName)
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
    vdev = ""
    # Generate random values for the dbi pattern generation
    jsonPath = get_dir_path(cluster_params, dirName)
    if jsonPath != None:
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

    if s3Support == "true":
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

def start_gc_process(cluster_params, dirName, debugMode):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']
    baseDir = os.path.join(base_dir, raft_uuid)
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/gcLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    path = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(path + "dummy_generator.json")
    vdev = str(json_data['BucketName'])
    dbo_input_path = str(json_data['DboPath'])
    dbi_input_path = str(json_data['DbiPath'])

    bin_path = '%s/gcTester' % binary_dir
    json_path = path + "dummy_generator.json"
    solnArry = path
    cmd = []
    if s3Support == "true":
         s3config = '%s/s3.config.example' % binary_dir
         # Prepare path for log file.
         s3LogFile = "%s/%s/s3Download" % (base_dir, raft_uuid)
         downloadPath = "%s/%s/" % (base_dir, raft_uuid)
         cmd = [bin_path, '-s3config', s3config, '-s3log', s3LogFile, '-j', json_path, '-v', solnArry, '-path', downloadPath]
    else:
        cmd = [bin_path, '-i', path, '-j', json_path, '-v', solnArry]

    if debugMode:
        cmd.append('-d')

    process = subprocess.Popen(cmd, stdout = fp, stderr = fp)

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
    dbiLogFile = "%s/%s/dataValidate.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    path = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(path + "/" + "dummy_generator.json")
    chunkNumber = str(json_data['TotalChunkSize'])
    vdev = str(json_data['BucketName'])

    logFile = "%s/%s/dataValidateResult" % (base_dir, raft_uuid)
    bin_path = '%s/dataValidator' % binary_dir
    process = subprocess.Popen([bin_path, '-d', path, '-c', chunkNumber, '-l', logFile], stdout = fp, stderr = fp)

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

def get_DBiFileNames(cluster_params, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    path = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(jsonPath + "dummy_generator.json")
    dbi_input_path = str(json_data['DbiPath'])

    # Initialize a list to store file names
    file_names = []

    # Iterate over the files in the directory
    for filename in os.listdir(dbi_input_path):
        if os.path.isfile(os.path.join(dbi_input_path, filename)):
            file_names.append(filename)

    # Create a JSON file and write the list of file names to it
    json_filename = 'DBIFileNames.json'
    path = "%s/%s/%s" % (base_dir, raft_uuid, json_filename)
    with open(path, 'w') as json_file:
        json.dump(file_names, json_file)

def copy_DBI_file_generatorNum(cluster_params, dirName):
    jsonPath = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(jsonPath + "dummy_generator.json")
    dbi_input_path = str(json_data['DbiPath'])

    # Get a list of files in the source directory
    file_list = os.listdir(dbi_input_path)

    # Check if there are any files in the directory
    if file_list:
        # Select a random file from the list
        random_file = random.choice(file_list)
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

def deleteFiles(cluster_params, dirName):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    json_filename = 'DBIFileNames.json'
    path = "%s/%s/%s" % (base_dir, raft_uuid, json_filename)

    jsonPath = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(jsonPath + "dummy_generator.json")
    dbi_input_path = str(json_data['DbiPath'])

    # Read the JSON file to get the list of file names
    json_filename = 'DBIFileNames.json'
    path = "%s/%s/%s" % (base_dir, raft_uuid, json_filename)
    with open(path, 'r') as json_file:
        file_names = json.load(json_file)

    # Calculate how many files you want to delete (half of the total)
    total_files = len(file_names)
    files_to_delete = total_files // 2

    for i in range(files_to_delete):
        file_to_delete = os.path.join(dbi_input_path, file_names[i])
        try:
            os.remove(file_to_delete)
        except Exception as e:
            print(f"Error deleting {file_to_delete}: {str(e)}")

def extracting_dictionary(cluster_params, operation, dirName):
    if operation == "data_validate":
       popen = start_data_validate(cluster_params, dirName)

    elif operation == "load_contents":
        data = load_json_contents(input_values['path'])
        return data

    elif operation == "copy_DBI_file_generatorNum":
        copy_DBI_file_generatorNum(cluster_params, dirName)

    elif operation == "get_DBI_fileNames":
        get_DBiFileNames(cluster_params, dirName)

    elif operation == "delete_DBI_files":
        deleteFiles(cluster_params, dirName)

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        dirName = "dbi-dbo"
        s3Dir = ""
        port = ""
        operation = terms[0]

        # Generate a random chunkNumber
        chunkNumber = str(random.randint(1, 200))
        cluster_params = kwargs['variables']['ClusterParams']

        if operation == "generate_pattern":
            input_values = terms[1]
            popen = start_pattern_generator(cluster_params, chunkNumber, input_values['genType'], dirName)

        elif operation == "start_s3":
            s3Dir = terms[1]
            process = start_minio_server(cluster_params, s3Dir)

        elif operation == "start_gc":
            debugMode = terms[1]
            popen = start_gc_process(cluster_params, dirName, debugMode)

        else:
            data = extracting_dictionary(cluster_params, operation, dirName)
            return data
