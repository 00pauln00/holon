from ansible.plugins.lookup import LookupBase
import json
import os, random, psutil
from datetime import datetime
import time
import subprocess ,re
import uuid, random
import shutil
import glob
from genericcmd import *
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

Marker_vdev = 0
Marker_chunk = 1
Marker_seq = 2
Marker_type = 3

def load_parameters_from_json(filename):
    # Load parameters from a JSON file
    with open(filename, 'r') as json_file:
        params = json.load(json_file)
    return params

def multiple_iteration_params(cluster_params, dirName, input_values):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']

    path = "%s/%s/%s/" % (base_dir, raft_uuid, dirName)
    # Create the new directory
    if not os.path.exists(path):
        # Create the directory path
        try:
            os.makedirs(path, mode=0o777)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dbiLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/dummyData' % binary_dir
    jsonPath = get_dir_path(cluster_params, dirName)
    if jsonPath != None:
        newPath = jsonPath + "/" + input_values["chunk"] + "/DV"
        json_data = load_json_contents(newPath + "/dummy_generator.json")
        input_values["vdev"] = str(json_data['Vdev'])
        input_values["seqStart"] = str(json_data['SeqEnd'] + 1)

    # Initialize the command list with common arguments
    cmd = [
        bin_path, "-c", input_values['chunk'], "-mp", input_values['maxPunches'], "-mv", input_values['maxVblks'], "-p", path,
        "-pa", input_values['punchAmount'], "-pp", input_values['punchesPer'], "-ps", input_values['maxPunchSize'], "-seed", input_values['seed'],
        "-ss", input_values['seqStart'], "-t", input_values['genType'], '-va', input_values['vbAmount'], '-vp', input_values['vblkPer'],
        "-vdev", input_values["vdev"], "-bs", input_values['blockSize'], "-bsm", input_values['blockSizeMax'], "-vs", input_values['startVblk']
    ]
    # Add the S3-specific options if s3Support is "true"
    if s3Support == "true":
        s3configPath = '%s/s3.config.example' % binary_dir
        s3LogFile = "%s/%s/s3Upload" % (base_dir, raft_uuid)
        cmd.extend(['-s3config', s3configPath, '-s3log', s3LogFile])

    if input_values["punchwholechunk"] == "=true":
        cmd.extend(["-pc", input_values["punchwholechunk"]])
    if input_values["strideWidth"] != "":
        cmd.extend(["-sw", input_values["strideWidth"]])
    if input_values["overlapSeq"] != "" and input_values["numOfSet"] != "":
        cmd.extend(["-se", input_values["overlapSeq"], "-ts", input_values["numOfSet"]])

    print("cmd: ", cmd)
    # Launch the subprocess with the constructed command
    process = subprocess.Popen(cmd, stdout=fp, stderr=fp)
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

    return process

def delete_contents_of_paths(paths):
    """
    Deletes all contents of the specified directories if they exist.

    Parameters:
    paths (list): A list of directory paths to delete contents from.
    """
    for path in paths:
        # Check if the directory exists
        if os.path.exists(path):
            # List all contents
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    # Check if it is a file or directory and delete accordingly
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove file or symbolic link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove directory
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')

def prepare_command_from_parameters(cluster_params, jsonParams, dirName, operation, params_type):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    dbiPath = "%s/%s/%s/" % (base_dir, raft_uuid, dirName)
    #Create the new directory
    if not os.path.exists(dbiPath):
        # Create the directory path
        try:
            os.makedirs(dbiPath, mode=0o777)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")

    processes = []

    for params in jsonParams:
       path = dbiPath + params["seed"]
       #Create the new directory
       if not os.path.exists(path):
          # Create the directory path
          try:
             os.makedirs(path, mode=0o777)
          except Exception as e:
             print(f"An error occurred while creating '{path}': {e}")

       cmd = []
       # Prepare path for log file.
       dbiLogFile = "%s/%s/dbiLog_%s.log" % (base_dir, raft_uuid, params["seed"])
       gcLogFile = "%s/%s/gcLog_%s.log" % (base_dir, raft_uuid, params["seed"])
       data_validator_log = "%s/%s/dataValidatorResult_%s" % (base_dir, raft_uuid, params["seed"])
       s3configPath = '%s/s3.config.example' % binary_dir
       gcDownloadPath = "%s/%s/gc-downloaded-obj" % (base_dir, raft_uuid)
       dvDownloadPath = "%s/%s/dv-downloaded-obj/" % (base_dir, raft_uuid)
       if operation == "run_example":
          bin_path = '%s/dummyData' % binary_dir
          jsonPath = get_dir_path(cluster_params, dirName, params["seed"])
          if jsonPath != None:
               newPath = jsonPath + "/" + params["chunk"] + "/DV"
               json_data = load_json_contents(newPath + "/dummy_generator.json")
               params["seqStart"] = str(json_data['SeqEnd'] + 1)
               params["vdev"] = str(json_data['Vdev'])
          else:
               params["seqStart"] = "0"
               params["vdev"] = ""

          if s3Support == "true":
               s3UploadLogFile = "%s/%s/s3Upload" % (base_dir, raft_uuid)
               cmd.extend([bin_path, "-c", params["chunk"], "-mp", params["maxPunches"],
                   "-mv", params["maxVblks"], "-p", path, "-pa", params["punchAmount"],
                   "-pp", params["punchesPer"], "-ps", params["maxPunchSize"], "-seed", params["seed"],
                   "-ss", params["seqStart"], "-va", params["vbAmount"], "-vp", params["vblkPer"],
                   "-t", params["genType"], "-bs", params["blockSize"], "-bsm", params["blockSizeMax"],
                   "-vs", params["startVblk"], "-vdev", params["vdev"], "-s3config", s3configPath,
                   "-s3log", s3UploadLogFile, '-b=paroscale-test'])
          else:
               cmd.extend([bin_path, "-c", params["chunk"], "-mp", params["maxPunches"],
                   "-mv", params["maxVblks"], "-p", path, "-pa", params["punchAmount"],
                   "-pp", params["punchesPer"], "-ps", params["maxPunchSize"], "-seed", params["seed"],
                   "-ss", params["seqStart"], "-va", params["vbAmount"], "-vp", params["vblkPer"],
                   "-t", params["genType"], "-bs", params["blockSize"], "-bsm", params["blockSizeMax"],
                   "-vs", params["startVblk"], "-vdev", params["vdev"]])
          if params["strideWidth"] != "":
                cmd.extend(["-sw", params["strideWidth"]])
          if params["overlapSeq"] != "" and params["numOfSet"] != "":
                cmd.extend(["-se", params["overlapSeq"], "-ts", params["numOfSet"]])

       elif operation == "run_gc":
          bin_path = '%s/gcTester' % binary_dir
          get_path = get_dir_path(cluster_params, dirName, params["seed"])
          json_data = load_json_contents(get_path + "/" + params["chunk"] + "/DV" + "/dummy_generator.json")
          modified_path = modify_path(get_path, params["seed"])
          vdev = str(json_data['Vdev'])
          if s3Support == "true":
               s3DownloadLogFile = "%s/%s/s3Download_%s" % (base_dir, raft_uuid, params["seed"])
               cmd.extend([bin_path, '-v', vdev, '-c', params["chunk"], "-s3config", s3configPath,
                       "-s3log", s3DownloadLogFile, "-path", gcDownloadPath, '-b=paroscale-test'])
          else:
              cmd.extend([bin_path, "-i", modified_path, '-v', vdev, '-c', params["chunk"]])
          if params["debugMode"]:
              cmd.append('-d')

       elif operation == "run_data_validator":
          bin_path = '%s/dataValidator' % binary_dir
          get_path = get_dir_path(cluster_params, dirName, params["seed"])
          json_data = load_json_contents(get_path + "/" + params["chunk"] + "/DV" + "/dummy_generator.json")
          modified_path = modify_path(get_path, params["seed"])
          vdev = str(json_data['Vdev'])
          if s3Support == "true":
                cmd.extend([bin_path, '-s', modified_path, '-d', dvDownloadPath, '-c', params['chunk'], '-v', vdev,
                    '-b=paroscale-test', '-s3config', s3configPath, '-l', data_validator_log, '-ll', '4'])
          else:
             cmd.extend([bin_path, '-s', modified_path, '-d', modified_path, '-c', params['chunk'],
                    '-v', vdev, '-l', data_validator_log])
       fp = open(dbiLogFile if operation == "run_example" else gcLogFile, "a+")
       process = subprocess.Popen(cmd, stdout=fp, stderr=fp)
       # Wait for the process to finish and get the exit code
       exit_code = process.wait()

       # close the log file
       fp.close()

       # Check if the process finished successfully (exit code 0)
       if exit_code == 0:
          print("Process completed successfully.")
       else:
          error_message = f"Process failed with exit code {exit_code}."
          raise RuntimeError(error_message)

       # Call the function to delete contents
       delete_contents_of_paths([gcDownloadPath, dvDownloadPath])

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
        if not os.path.exists(os.path.expanduser(f'/local/{dirName}')):
            os.makedirs(os.path.expanduser(f'/local/{dirName}'), mode=0o777)

        command = f"minio server /local/{dirName} --console-address ':2000' --address ':2090'"

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

def get_dir_path(cluster_params, dirName, seed=None):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    baseDir = os.path.join(base_dir, raft_uuid)
    #dbi_dir = os.path.join(baseDir, dirName, seed)

    if seed is not None:
        dbi_dir = os.path.join(baseDir, dirName, seed)
    else:
        dbi_dir = os.path.join(baseDir, dirName)

    # Get a list of all entries (files and directories) under the 'dbi-dbo' directory
    entries = os.listdir(dbi_dir)

    # Filter out directories only
    directories = [entry for entry in entries if os.path.isdir(os.path.join(dbi_dir, entry))]

    if directories:
        # Sort directories based on creation time (most recent first)
        directories.sort(key=lambda d: os.path.getctime(os.path.join(dbi_dir, d)), reverse=True)
        # Return the path of the most recently created directory with a trailing slash
        most_recent_directory = directories[0]
        if len(directories) > 1:
            most_recent_directory = directories[1]
        directory_path = os.path.join(dbi_dir, most_recent_directory, '')  # Add the trailing slash here
        return directory_path
    else:
        return None

def start_pattern_generator(cluster_params, genType, dirName, input_values, removeFiles=True):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']
    path = "%s/%s/%s/" % (base_dir, raft_uuid, dirName)
    # Create the new directory
    if not os.path.exists(path):
        # Create the directory path
        try:
            os.makedirs(path, mode=0o777)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    dbiLogFile = "%s/%s/dbiLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(dbiLogFile, "a+")

    #Get dummyDBI example
    bin_path = '%s/dummyData' % binary_dir
    vdev = ""

    chunkNum = ""
    if input_values['chunkNumber'] == "-1":
        # Generate a random chunkNumber
        chunkNum = str(random.randint(1, 200))

    # Generate random values for the dbi pattern generation
    jsonPath = get_dir_path(cluster_params, dirName)
    if jsonPath != None:
        newPath = jsonPath + "/" + input_values['chunkNumber'] + "/DV"
        json_data = load_json_contents(newPath + "/dummy_generator.json")
        chunk = str(json_data['TotalChunkSize'])
        seqStart = str(json_data['SeqEnd'] + 1)
        vdev = str(json_data['Vdev'])
    else:
        chunk = chunkNum
        seqStart = "0"

    maxPunches = str(random.randint(1, 50))
    maxVblks = str(random.randint(100, 1000))
    punchAmount = str(random.randint(51, 100))
    punchesPer = "0"
    maxPuncheSize = str(random.randint(1, 1024))
    seed = str(random.randint(1, 100))
    vbAmount =  str(random.randint(1000, 10000))
    vblkPer = str(random.randint(1, 20))
    blockSize = str(random.randint(1, 32))
    blockSizeMax = str(random.randint(1, 32))
    startVblk = "0"
    strideWidth = str(random.randint(1, 50))
    numOfSet = str(random.randint(1, 10))

    # Initialize the command list with common arguments
    cmd = [
        bin_path, "-c", chunk, "-mp", maxPunches, "-mv", maxVblks, "-p", path,
        "-pa", punchAmount, "-pp", punchesPer, "-ps", maxPuncheSize, "-seed", seed,
        "-ss", seqStart, "-t", genType, "-b", "paroscale-test",
        "-bs", blockSize, "-bsm", blockSizeMax, "-vs", startVblk, "-sw", strideWidth
    ]
    # Add the -se and -ts option if overlapSeq is provided
    if 'overlapSeq' not in input_values:
        cmd.extend(['-va', str(vbAmount), '-vp', str(vblkPer)])
    else:
        cmd.extend(['-va', input_values['vbAmount'], '-vp', input_values['vblkPer'],
                    '-se', input_values['overlapSeq'], '-ts', str(numOfSet)])

    # Add the -vdev option if vdev is provided
    if vdev:
       cmd.extend(['-vdev', vdev])

    if 'dbiWithPunches' in input_values:
       cmd.extend(['-va', input_values['vbAmount'], '-vp', input_values['vblkPer'],
                        '-e', input_values['dbiWithPunches']])
    # Add the S3-specific options if s3Support is "true"
    if s3Support == "true":
         s3config = '%s/s3.config.example' % binary_dir
         s3LogFile = "%s/%s/s3Upload" % (base_dir, raft_uuid)
         cmd.extend(['-s3config', s3config, '-s3log', s3LogFile])
         if not removeFiles:
              cmd.append('-r=true')

    print("cmd: ", cmd)

    # Launch the subprocess with the constructed command
    process = subprocess.Popen(cmd, stdout=fp, stderr=fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.wait()
    # Close the log file
    fp.close()
    print(" Command to run dummygenerator ", cmd)
    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        print("Process completed successfully.")
    else:
        error_message = f"Process failed with exit code {exit_code}."
        raise RuntimeError(error_message)

    return chunk

def start_gc_process(cluster_params, dirName, debugMode, chunk, crcCheck=None):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']
    baseDir = os.path.join(base_dir, raft_uuid)
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    gcLogFile = "%s/%s/gcLog.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(gcLogFile, "a+")

    path = get_dir_path(cluster_params, dirName)
    bin_path = '%s/gcTester' % binary_dir
    matches = re.findall(r'[\w-]{36}', path)
    vdev_uuid = matches[-1] if matches else None
    modified_path = modify_path(path)
    cmd = []
    if s3Support == "true":
         s3config = '%s/s3.config.example' % binary_dir
         # Prepare path for log file.
         s3LogFile = "%s/%s/s3Download" % (base_dir, raft_uuid)
         downloadPath = "%s/%s/gc-downloaded-obj" % (base_dir, raft_uuid)
         cmd = [bin_path, '-c', chunk, '-v', vdev_uuid, '-s3config', s3config, '-path', downloadPath, '-s3log', s3LogFile, '-b', 'paroscale-test']
    else:
        cmd = [bin_path, '-i', modified_path, '-v', vdev_uuid, '-c', chunk]

    if debugMode:
        cmd.append('-d')

    if crcCheck:
        cmd.append('-ec=true')
    process = subprocess.Popen(cmd, stdout = fp, stderr = fp)

    # Wait for the process to finish and get the exit code
    exit_code = process.wait()
    # Close the log file
    fp.close()

    return exit_code

def start_gcService_process(cluster_params, dirName, dryRun, delDBO):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']
    app_name = cluster_params['app_type']

    baseDir = os.path.join(base_dir, raft_uuid)
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    gcLogFile = "%s/%s/gcS3Log.log" % (base_dir, raft_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(gcLogFile, "a+")

    path = get_dir_path(cluster_params, dirName)
    bin_path = '%s/GCService' % binary_dir
    matches = re.findall(r'[\w-]{36}', path)
    vdev_uuid = matches[-1] if matches else None

    cmd = []
    s3config = '%s/s3.config.example' % binary_dir
    # Prepare path for log file.
    s3LogFile = "%s/%s/s3Download" % (base_dir, raft_uuid)
    downloadPath = "%s/%s/gc-downloaded-obj" % (base_dir, raft_uuid)
    cmd = [bin_path, '-path', downloadPath, '-s3config', s3config, '-s3log', s3LogFile, '-t', '120',
              '-l', '4', '-p', '7500', '-b', 'paroscale-test']

    if dryRun:
        cmd.append('-dr')

    if delDBO:
        cmd.append('-dd')
    print("GCservice Command ", cmd)
    process_popen = subprocess.Popen(cmd, stdout = fp, stderr = fp)

    #Check if gcService process exited with error
    if process_popen.poll() is None:
        logging.info("gcService process started successfully")
    else:
        logging.info("gcService failed to start")
        raise subprocess.SubprocessError(process_popen.returncode)

    if downloadPath != None:
        print("downloadPath exist ", downloadPath)
    else:
        print("download path doesn't exist")
    #writing the information of lookout uuids dict into raft_uuid.json
    recipe_conf = load_recipe_op_config(cluster_params)

    #writing the information of lookout uuid in gcService_process into raft_uuid.json
    pid = process_popen.pid
    ps = psutil.Process(pid)

    if not "gcService_process" in recipe_conf:
        recipe_conf['gcService_process'] = {}

    recipe_conf['gcService_process']['process_pid'] = pid
    recipe_conf['gcService_process']['process_type'] = "gcService"
    recipe_conf['gcService_process']['process_app_type'] = app_name
    recipe_conf['gcService_process']['process_status'] = ps.status()

    genericcmdobj = GenericCmds()
    genericcmdobj.recipe_json_dump(recipe_conf)

    os.fsync(fp)

def modify_path(path, seed=None):
    # Split the path into parts
    parts = path.split('/')

    # Remove the first element if it's empty due to a leading slash
    if parts[0] == '':
        parts.pop(0)

    # Remove the last element if it's empty due to a trailing slash
    if parts[-1] == '':
        parts.pop()

    # Find the index of 'dbi-dbo' in the list
    try:
        dbi_dbo_index = parts.index('dbi-dbo')
    except ValueError:
        # If 'dbi-dbo' is not found, return the original path
        return path

    # Ensure there's at least one directory after 'dbi-dbo' to check
    if dbi_dbo_index < len(parts) - 1:
        # Get the directory name after 'dbi-dbo'
        next_directory = parts[dbi_dbo_index + 1]

        # Check if the next directory is seed
        if next_directory == seed:
            # Remove the directory that comes after seed
            parts.pop(dbi_dbo_index + 2)
        else:
            # Remove the directory that comes after 'dbi-dbo'
            parts.pop(dbi_dbo_index + 1)

    # Rejoin the remaining parts
    new_path = '/' + '/'.join(parts)

    return new_path

def start_data_validate(cluster_params, dirName, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    # Prepare path for log file.
    logFile = "%s/%s/dataValidateResult" % (base_dir, raft_uuid)
    jsonPath = get_dir_path(cluster_params, dirName)

    newPath = jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json"
    json_data = load_json_contents(newPath)
    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])

    path = get_dir_path(cluster_params, dirName)
    downloadPath = "%s/%s/gc-downloaded-obj" % (base_dir, raft_uuid)
    bin_path = '%s/dataValidator' % binary_dir
    if path != None:
        newPath = path + "/" + chunk + "/DV"
        json_data = load_json_contents(newPath + "/dummy_generator.json")
        vdev = str(json_data['Vdev'])

    modified_path = modify_path(path)

    if s3Support == "true":
        dvPath = "%s/%s/dv-downloaded-obj" % (base_dir, raft_uuid)
        s3config = '%s/s3.config.example' % binary_dir
        process = subprocess.Popen([bin_path, '-s', modified_path, '-d', dvPath, '-c', chunk, '-v', vdev, '-s3config', s3config, '-b', 'paroscale-test', '-l', logFile, '-ll', '4'])
    else:
        process = subprocess.Popen([bin_path, '-s', modified_path, '-d', modified_path, '-c', chunk, '-v', vdev, '-l', logFile, '-ll', '4'])

    # Wait for the process to finish and get the exit code
    exit_code = process.wait()

    # Check if the process finished successfully (exit code 0)
    if exit_code == 0:
        f"Process completed successfully."
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

def copy_file_to_backup(cluster_params, dirName, operation, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    newPath = jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json"
    json_data = load_json_contents(newPath)

    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])
    logFile = "%s/%s/s3operation" % (base_dir, raft_uuid)
    path = get_dir_path(cluster_params, dirName)
    # Get a list of files in the source directory
    file_list = os.listdir(dbi_input_path)
    last_file = ""
    if len(file_list) > 1:
        # Sort the file list by modification time (oldest to newest)
        file_list.sort(key=lambda x: os.path.getmtime(os.path.join(dbi_input_path, x)))
        # Get the last file in the sorted list
        last_file = file_list[-1]
    # Construct the source file path
    source_file_path = os.path.join(dbi_input_path, last_file)
    backup_dir = os.path.join(base_dir, raft_uuid, 'orig-dbi')
    dest_file_path = os.path.join(backup_dir, last_file)
    s3config = '%s/s3.config.example' % binary_dir
    bin_path = '%s/s3Operation' % binary_dir
    if operation == "upload":
            # Check if the destination directory exists, and create if not
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, mode=0o777)
            # Copy the file to the destination directory
            shutil.copy(source_file_path, dest_file_path)
            # Read the binary file
            with open(source_file_path, "rb") as f:
                data = bytearray(f.read())

	    # Ensure the file is at least 16 bytes long
            if len(data) < 16:
                print("File is too small to modify the first 16 bytes")
                return

	    # Create a new 16-byte entry with Type set to 1 and the rest set to zero
            new_entry = bytearray(16)
            new_entry[0] = 0x01  # Set Type to 1

	    # Copy the new entry to the first 16 bytes of the data
            data[:16] = new_entry

	    # Write the modified data back to the original file
            with open(source_file_path, "wb") as f:
               f.write(data)

            process = subprocess.Popen([bin_path, '-bucketName', 'paroscale-test', '-operation', operation, '-s3config', s3config, '-filepath', source_file_path, '-l', logFile])

    elif operation == "delete":

            process = subprocess.Popen([bin_path, '-bucketName', 'paroscale-test', '-operation', operation, '-s3config', s3config, '-f', last_file, '-v', vdev, '-c', chunk, '-filepath', source_file_path, '-l', logFile])

            delete_dir = os.path.join(base_dir, raft_uuid, 'gc-downloaded-obj')
            if os.path.exists(delete_dir):
                shutil.rmtree(delete_dir)

def uploadAndDeleteCorruptedFile(cluster_params, dirName, operation, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    newPath = jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json"
    json_data = load_json_contents(newPath)

    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])
    logFile = "%s/%s/s3operation" % (base_dir, raft_uuid)

    # Get a list of files in the source directory
    file_list = os.listdir(dbi_input_path)

    last_file = ""
    if len(file_list) > 1:
        # Sort the file list by modification time (oldest to newest)
        file_list.sort(key=lambda x: os.path.getmtime(os.path.join(dbi_input_path, x)))
        # Get the last file in the sorted list
        last_file = file_list[-1]

    # Construct the source file path
    source_file_path = os.path.join(dbi_input_path, last_file)
    # Get the size of the file
    fileSize = os.path.getsize(source_file_path)
    # Split the file name using '.' as the delimiter
    parts = last_file.split('.')
    numOfEntries = parts[4]
    # Calculate the size of each entry
    entry_size = int(fileSize) // int(numOfEntries)
    # Construct the destination directory path
    dest_dir = os.path.join(base_dir, raft_uuid, 'origDBIFile')
    dest_file_path = os.path.join(dest_dir, last_file)
    s3config = '%s/s3.config.example' % binary_dir
    bin_path = '%s/s3Operation' % binary_dir
    if operation == "upload":
            # Check if the destination directory exists, and create if not
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, mode=0o777)
            # Copy the file to the destination directory
            shutil.copy(source_file_path, dest_file_path)
            # Modify the last file by adding "0000" at the end
            with open(source_file_path, 'r+b') as f:
                 # Seek to the position where the last entry starts
                 f.seek(fileSize - entry_size)
                 # Write zeroes to the remaining part of the file
                 f.write(b'\x00' * entry_size)

            process = subprocess.Popen([bin_path, '-bucketName', 'paroscale-test', '-operation', operation, '-s3config', s3config, '-filepath', source_file_path, '-l', logFile])

    elif operation == "delete":

            process = subprocess.Popen([bin_path, '-bucketName', 'paroscale-test', '-operation', operation, '-v', vdev, '-c', chunk, '-s3config', s3config, '-filepath', source_file_path, '-l', logFile])

def PushOrigFileToS3(cluster_params, dirName, operation, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    json_data = load_json_contents(jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json")
    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])
    logFile = "%s/%s/s3operation" % (base_dir, raft_uuid)

    # Construct the destination directory path
    dest_dir = os.path.join(base_dir, raft_uuid, 'orig-dbi')

    # Get a list of files in the source directory
    file_list = os.listdir(dest_dir)
    if len(file_list) >= 1:
        # Sort the file list by modification time (oldest to newest)
        file_list.sort(key=lambda x: os.path.getmtime(os.path.join(dest_dir, x)))

        # Get the last file in the sorted list
        last_file = file_list[0]

        # Construct the source file path
        source_file_path = os.path.join(dest_dir, last_file)
        # Construct the destination directory path
        dest_file_path = os.path.join(dbi_input_path, last_file)
        # Copy the file to the destination directory
        shutil.copy(source_file_path, dest_file_path)
        s3config = '%s/s3.config.example' % binary_dir
        bin_path = '%s/s3Operation' % binary_dir
        process = subprocess.Popen([bin_path, '-bucketName', 'paroscale-test', '-operation', operation, '-s3config', s3config, '-filepath', dest_file_path, '-l', logFile])

def uploadOrigFile(cluster_params, dirName, operation, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    json_data = load_json_contents(jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json")
    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])
    logFile = "%s/%s/s3operation" % (base_dir, raft_uuid)

    # Get a list of files in the source directory
    file_list = os.listdir(dbi_input_path)

    if len(file_list) > 1:
        # Sort the file list by modification time (oldest to newest)
        file_list.sort(key=lambda x: os.path.getmtime(os.path.join(dbi_input_path, x)))

        # Get the last file in the sorted list
        last_file = file_list[-1]

        # Construct the source file path
        source_file_path = os.path.join(dbi_input_path, last_file)
        # Construct the destination directory path
        dest_dir = os.path.join(base_dir, raft_uuid, 'origDBIFile')
        dest_file_path = os.path.join(dest_dir, last_file)
        # Copy the file to the destination directory
        shutil.copy(dest_file_path, source_file_path)
        s3config = '%s/s3.config.example' % binary_dir
        bin_path = '%s/s3Operation' % binary_dir
        process = subprocess.Popen([bin_path, '-bucketName', 'paroscale-test', '-operation', operation, '-s3config', s3config, '-filepath', source_file_path, '-l', logFile])

def perform_s3_operation(cluster_params, dirName, operation, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    json_data = load_json_contents(jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json")
    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])
    logFile = "%s/%s/s3operation" % (base_dir, raft_uuid)

    # Get a list of files in the source directory
    file_list = os.listdir(dbi_input_path)

    if len(file_list) > 1:
        # Sort the file list by modification time (oldest to newest)
        file_list.sort(key=lambda x: os.path.getmtime(os.path.join(dbi_input_path, x)))

        # Get the last file in the sorted list
        last_file = file_list[-2]
        file_path = dbi_input_path + "/" + last_file

        s3config = '%s/s3.config.example' % binary_dir
        bin_path = '%s/s3Operation' % binary_dir
        process = subprocess.Popen([bin_path, '-bucketName', 'paroscale-test', '-operation', operation, '-s3config', s3config, '-filepath', file_path, '-l', logFile])

def get_DBiFileNames(cluster_params, dirName, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json")
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

def search_files_by_string(directory, search_string):
        filename=search_string + ".dbo"
        file_part = filename.split(".")
        old_uuid = file_part[0]
        new_uuid = str(uuid.uuid4())  # Generate a new UUID as a string
        file_part[0] = new_uuid

        # Create the new filename by joining the parts with '.'
        newfile = ".".join(file_part)

        # Create the full paths for the source and destination files
        source_path = os.path.join(directory, filename)
        destination_path = os.path.join(directory, newfile)

        # Copy the file with the new filename
        shutil.copyfile(source_path, destination_path)

        return new_uuid

def copy_DBI_file_generatorNum(cluster_params, dirName, chunk):
    jsonPath = get_dir_path(cluster_params, dirName)
    path = jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json"
    json_data = load_json_contents(path)
    dbi_input_path = str(json_data['DbiPath'])
    dbo_input_path = str(json_data['DboPath'])
    # Get a list of files in the source directory
    file_list = os.listdir(dbi_input_path)

    # Check if there are any files in the directory
    if file_list:
        # Select a random file from the list
        random_file = random.choice(file_list)
        filename_parts = random_file.split(".")
        # Extract the generation number
        genration_num = filename_parts[1]
        uuid = filename_parts[4]
        # create dbo file with new uuid
        result = search_files_by_string(dbo_input_path, uuid)

        # Increment the extracted element by 1
        # Decrement as the number is inversed
        new_genration_num = str(int(genration_num, 16) - 1)

        # Update the filename with the incremented element
        filename_parts[1] = new_genration_num
        filename_parts[4] = result
        new_filename = ".".join(filename_parts)
        # Full path for the copied and renamed file
        source_file_path = os.path.join(dbi_input_path, random_file)
        new_file_path = os.path.join(dbi_input_path, new_filename)

        # Copy the file and rename the copy
        shutil.copy(source_file_path, new_file_path)
    else:
        print("No files found in the directory.")

def deleteFiles(cluster_params, dirName, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    json_filename = 'DBIFileNames.json'

    jsonPath = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json")
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

def deleteSetFiles(cluster_params, dirName, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    json_data = load_json_contents(jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json")
    dbi_input_path = str(json_data['DbiPath'])

    destination_path = jsonPath + "dbisetFname.txt"
    with open(destination_path, 'r') as file:
        # Read the contents of the file
        file_contents = file.read()
    file_list = file_contents.rstrip(', ').split(', ')

    filename = random.choice(file_list)
    os.remove(filename)

    prefix = filename.split('.')[0]

    # Create a list to store files with the same prefix
    files_with_same_prefix = [file for file in file_list if file.startswith(prefix)]
    with open(destination_path, 'w') as file:
        for item in files_with_same_prefix:
            file.write(item + ", ")

def deleteSetFileS3(cluster_params, dirName, operation, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    json_path = jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json"
    json_data = load_json_contents(json_path)
    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])
    logFile = "%s/%s/s3operation" % (base_dir, raft_uuid)

    filenames = []
    destination_path = os.path.join(jsonPath, "dbisetFname.txt")
    with open(destination_path, 'r') as file:
        # Read the contents of the file
        file_contents = file.read()

    file_list = file_contents.rstrip(', ').split(', ')
    filename = random.choice(file_list)
    file_path = filename
    fname = os.path.basename(filename)
    prefix = filename.split('.')[0]

    # Create a list to store files with the same prefix
    files_with_same_prefix = [file for file in file_list if file.startswith(prefix)]
    with open(destination_path, 'w') as file:
        for item in files_with_same_prefix:
            file.write(item + ", ")

    s3config = '%s/s3.config.example' % binary_dir
    bin_path = '%s/s3Operation' % binary_dir
    os.remove(file_path)
    process = subprocess.Popen([bin_path, '-bucketName', "paroscale-test", '-operation', operation, '-v', vdev, '-c', chunk, '-s3config', s3config, '-f', fname, '-l', logFile])

def copyDBIset_NewDir(cluster_params, dirName, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    json_path = jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json"
    json_data = load_json_contents(json_path)
    dbi_input_path = str(json_data['DbiPath'])
    vdev = str(json_data['Vdev'])

    newDir = "dbiSetFiles"
    print("jsonPath:", jsonPath)
    file_path = os.path.join(jsonPath, "dbisetFname.txt")
    file_contents = ""
    try:
        with open(file_path, 'r') as file:
            # Read the contents of the file
            file_contents = file.read()
    except FileNotFoundError:
        print(f"The file '{file_path}' was not found.")

    file_list = file_contents.rstrip(', ').split(', ')
    for fileNames in file_list:
        source_path = fileNames
        destination_path = jsonPath + newDir
        if not os.path.exists(destination_path):
            os.makedirs(destination_path, mode=0o777)
        shutil.copy2(source_path, destination_path)

def copyDBIFile_changeSeqNum(cluster_params, dirName, chunk):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    jsonPath = get_dir_path(cluster_params, dirName)
    json_path = jsonPath + "/" + str(chunk) + "/DV/" + "dummy_generator.json"
    json_data = load_json_contents(json_path)
    dbi_input_path = str(json_data['DbiPath'])
    dbo_input_path = str(json_data['DboPath'])

    # Check if the path is a directory
    if not os.path.isdir(dbi_input_path):
        print(f"{dbi_input_path} is not a valid directory path.")
        return

    # Get the list of files in the directory
    files = [f for f in os.listdir(dbi_input_path) if os.path.isfile(os.path.join(dbi_input_path, f))]

    # Check if there are any files in the directory
    if not files:
        print(f"No files found in {dbi_input_path}.")
        return

    # Get the last file from the list
    last_file = files[-1]

    filename_parts = last_file.split(".")
    old_seq_num = filename_parts[0]
    end_seq = old_seq_num.split("_")

    # Extract the 3rd last element after the dots
    Num_of_entries = filename_parts[-2]
    uuid_str = filename_parts[4]

    # create dbo file with new uuid
    result = search_files_by_string(dbo_input_path, uuid_str)
    new_uuid = str(uuid.uuid4())  # Generate a new UUID

    # Full path for the copied and renamed file
    old_DBO_file_path = os.path.join(dbo_input_path, f"{result}.dbo")
    new_DBO_file_path = os.path.join(dbo_input_path, f"{new_uuid}.dbo")

    # Copy the contents of old_DBO_file_path to new_DBO_file_path
    with open(old_DBO_file_path, 'rb') as old_file:
        content = old_file.read()
        with open(new_DBO_file_path, 'wb') as new_file:
            new_file.write(content)

    # Increment the extracted element by 1
    new_firstSeqNum = str(int(end_seq[1]) + 1)
    new_endSeqNum = str(int(end_seq[1]) + int(Num_of_entries))
    joined_seq = "_".join([new_firstSeqNum, new_endSeqNum])

    filename_parts[0] = joined_seq
    filename_parts[2] = str(new_uuid)
    new_filename = ".".join(filename_parts)

    # Full path for the copied and renamed file
    source_file_path = os.path.join(dbi_input_path, last_file)
    new_file_path = os.path.join(dbi_input_path, new_filename)

    # Copy the file and rename the copy
    shutil.copy(source_file_path, new_file_path)

def extracting_dictionary(cluster_params, operation, dirName):
    if operation == "load_contents":
        data = load_json_contents(input_values['path'])
        return data

def check_if_mType_Present(vdev, chunk, mList, mType):
    for line in (mList.splitlines()):
        parts = line.split(".")
        if vdev in parts[Marker_vdev] and chunk in parts[Marker_chunk] and mType in parts[Marker_type]:
            return parts[2]
    return None

def GetSeqOfMarker(cluster_params, dirName, chunk, value):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    s3Support = cluster_params['s3Support']
    jsonPath = get_dir_path(cluster_params, dirName)
    logFile = "%s/%s/s3operation" % (base_dir, raft_uuid)
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    bin_path = '%s/s3Operation' % binary_dir
    s3config = '%s/s3.config.example' % binary_dir
    if jsonPath is not None:
        newPath = os.path.join(jsonPath, chunk, "DV")
        json_data = load_json_contents(os.path.join(newPath, "dummy_generator.json"))
        vdev = str(json_data['Vdev'])
        for i in range(30):
            cmd = [bin_path, '-bucketName', "paroscale-test", '-operation', "list", '-v', vdev, '-c', chunk, '-s3config', s3config, '-p', "m", '-l', logFile]
            print("command To list Marker Files ", cmd)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            process.wait()
            # Read the output and error
            stdout, stderr = process.communicate()
            print("List output : ", stdout)
            if stdout:
                print(" stdout in if Loop  ", stdout)
                break
            else:
                print(" stdout in else Loop  ", stdout)
                time.sleep(1)
        print("Going to get Sequence ") 
        # Check if any file is found
        GcSeq = check_if_mType_Present(vdev, chunk, stdout, "gc")
        NisdSeq = check_if_mType_Present(vdev, chunk, stdout, "nisd")
        MSeq = []
        match value:
            case 'gc':
                MSeq.extend([GcSeq, None])
                print(" Marker For gc : ",MSeq)
                return MSeq
            case 'nisd':
                MSeq.extend([None, NisdSeq])
                print(" Marker For nisd : ",MSeq)
                return MSeq
            case 'Both':
                MSeq.extend([GcSeq, NisdSeq])
                print(" Marker For Both : ",MSeq)
                return MSeq
    else:
        print("Invalid path or directory not found.")
        return None

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
            popen = start_pattern_generator(cluster_params, input_values['genType'], dirName, input_values, removeFiles=False)
            return popen

        elif operation == "start_s3":
            s3Dir = terms[1]
            process = start_minio_server(cluster_params, s3Dir)

        elif operation == "start_gc":
            # Assume terms is a list with relevant arguments
            if len(terms) >= 3:
               debugMode = terms[1]
               chunk = terms[2]
               # Check if crcCheck is provided
               crcCheck = terms[3] if len(terms) > 3 else None
               popen = start_gc_process(cluster_params, dirName, debugMode, chunk, crcCheck)
               return popen
            else:
               raise ValueError("Not enough arguments provided for start_gc operation")

        elif operation == "start_gcService":
            dryRun = terms[1]
            delDBO = terms[2]
            start_gcService_process(cluster_params, dirName, dryRun, delDBO)

        elif operation == "data_validate":
            Chunk = terms[1]
            popen = start_data_validate(cluster_params, dirName, Chunk)

        elif operation == "get_DBI_fileNames":
            Chunk = terms[1]
            get_DBiFileNames(cluster_params, dirName, Chunk)

        elif operation == "delete_DBI_files":
            Chunk = terms[1]
            deleteFiles(cluster_params, dirName, Chunk)

        elif operation == "deleteSetFileS3":
            operation = terms[1]
            chunk = terms[2]
            popen = deleteSetFileS3(cluster_params, dirName, operation, chunk)

        elif operation == "performS3Operation":
            s3Operation = terms[1]
            chunk = terms[2]
            if s3Operation == "delete" or s3Operation == "upload":
                perform_s3_operation(cluster_params, dirName, s3Operation, chunk)

        elif operation == "corruptedFileOps":
            s3Operation = terms[1]
            chunk = terms[2]
            uploadAndDeleteCorruptedFile(cluster_params, dirName, s3Operation, chunk)

        elif operation == "uploadOrigFile":
            s3Operation = terms[1]
            chunk = terms[2]
            uploadOrigFile(cluster_params, dirName, s3Operation, chunk)

        elif operation == "performCorruptedFileOps":
            s3Operation = terms[1]
            chunk = terms[2]
            copy_file_to_backup(cluster_params, dirName, s3Operation, chunk)

        elif operation == "pushOrigFileToS3":
            s3Operation = terms[1]
            chunk = terms[2]
            PushOrigFileToS3(cluster_params, dirName, s3Operation, chunk)

        elif operation == "copyDBIset":
            chunk = terms[1]
            copyDBIset_NewDir(cluster_params, dirName, chunk)

        elif operation == "deleteSetFiles":
            chunk = terms[1]
            deleteSetFiles(cluster_params, dirName, chunk)

        elif operation == "copy_DBI_file_generatorNum":
            chunk = terms[1]
            copy_DBI_file_generatorNum(cluster_params, dirName, chunk)

        elif operation == "copyDBIFile_changeSeqNum":
            chunk = terms[1]
            copyDBIFile_changeSeqNum(cluster_params, dirName, chunk)

        elif operation == "multiple_iteration_params" or operation == "example_params":
            input_values = terms[1]
            popen = multiple_iteration_params(cluster_params, dirName, input_values)

            return popen

        elif operation == "GetSeqOfMarker":
            chunk = terms[2]
            value = terms[1]
            MarkerSeq = GetSeqOfMarker(cluster_params, dirName, chunk, value)

            return MarkerSeq

        elif operation == "json_params":
            params_type = terms[1]
            load_params = load_parameters_from_json("seed.json")
            if params_type == "single_iteration":
               single_itr_seq = ['run_example', 'run_gc', 'run_data_validator']
               for params in load_params["single_iteration"]:
                  for i in single_itr_seq:
                     prepare_command_from_parameters(cluster_params, [params], dirName, i, params_type)
        else:
            data = extracting_dictionary(cluster_params, operation, dirName)
            return data
