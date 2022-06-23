from ansible.plugins.lookup import LookupBase
import fcntl, psutil
import sys
import json
import termios
import os
import time
import shutil
import subprocess
from genericcmd import *
from func_timeout import func_timeout, FunctionTimedOut
import time as time_global

def start_niova_block_ctl_process(cluster_params, nisdPath, nisd_uuid):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for log file.
    log_file = "%s/%s/niovablockctl_%s_log.txt" % (base_dir, raft_uuid, nisd_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    #format and run the niova-block-ctl
    bin_path = '%s/niova-block-ctl' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-d', nisdPath, '-i', '-u', nisd_uuid],
                                   stdout = fp, stderr = fp)

    #Check if niova-block-ctl process exited with error
    if process_popen.poll() is None:
        logging.info("niova-block-ctl process started successfully")
    else:
        logging.info("niova-block-ctl process failed to start")
        raise subprocess.SubprocessError(process_popen.returncode)

    # Sync the log file so all the logs from niova-block-ctl gets written to log file.
    os.fsync(fp)

    return process_popen

def start_nisd_process(cluster_params, nisd_uuid, uport, nisdPath):
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare seperate path for nisd log file.
    log_file = "%s/%s/nisd_%s_log.txt" % (base_dir, raft_uuid, nisd_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")

    #start nisd process
    bin_path = '%s/nisd' % binary_dir
    process_popen = subprocess.Popen([bin_path, '-u', nisd_uuid, '-p', uport, '-d', nisdPath],
                                      stdout = fp, stderr = fp)
    logging.info("starting nisd process")

    #Check if nisd process exited with error
    if process_popen.poll() is None:
        logging.info("NISD process started successfully")
    else:
        logging.info("NISD process failed to start")
        raise subprocess.SubprocessError(process_popen.returncode)

    # writing the information of lookout and nisd into raft_uuid.json file
    recipe_conf = load_recipe_op_config(cluster_params)
    pid = process_popen.pid
    ps = psutil.Process(pid)

    if not "raft_process" in recipe_conf:
        recipe_conf['raft_process'] = {}

    recipe_conf['raft_process'][nisd_uuid] = {}

    recipe_conf['raft_process'][nisd_uuid]['process_raft_uuid'] = nisd_uuid
    recipe_conf['raft_process'][nisd_uuid]['img_file_name'] = nisdPath
    recipe_conf['raft_process'][nisd_uuid]['process_pid'] = pid
    recipe_conf['raft_process'][nisd_uuid]['process_uuid'] = nisd_uuid
    recipe_conf['raft_process'][nisd_uuid]['process_type'] = "nisd"
    recipe_conf['raft_process'][nisd_uuid]['process_app_type'] = app_name
    recipe_conf['raft_process'][nisd_uuid]['process_status'] = ps.status()

    genericcmdobj = GenericCmds()
    genericcmdobj.recipe_json_dump(recipe_conf)

    # Sync the log file so all the logs from nisd gets written to log file.
    os.fsync(fp)

    return process_popen

def prepare_nisd_device_path(nisd_uuid):
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    nisdPath = "%s/test_nisd_%s.device" % (binary_dir, nisd_uuid)
    return nisdPath

def create_nisd_device_and_uuid(nisd_uuid, nisd_dev_size):
    nisdpath_device = prepare_nisd_device_path(nisd_uuid)

    # truncate the device to a specified size
    file = open(nisdpath_device, 'w')
    file.truncate(int(nisd_dev_size))
    file.close()

    return nisdpath_device

def set_environment_variables(cluster_params):
    ctl_interface_path = "%s/%s/nisd-interface" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'])

    if os.path.exists(ctl_interface_path):
        logging.info("file already exist")
    else:
        os.mkdir(ctl_interface_path)


    #set environment variables
    os.environ['NIOVA_INOTIFY_BASE_PATH'] = ctl_interface_path
    os.environ['NIOVA_LOCAL_CTL_SVC_DIR'] = ctl_interface_path

    return ctl_interface_path

def start_niova_block_test(cluster_params, nisd_uuid_to_write, vdev, read_operation_ratio_percentage,
                                random_seed, client_uuid, request_size_in_bytes, queue_depth, num_ops,
                                integrity_check, sequential_writes, blocking_process):
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for log file.
    log_file = "%s/%s/niova-block-test_%s_log.txt" % (base_dir, raft_uuid, nisd_uuid_to_write[5:])

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")

    #start niova block test process
    bin_path = '%s/niova-block-test' % binary_dir

    logging.info("Do write/read operation on nisd by starting niova-block-test")

    if sequential_writes == True and integrity_check == False and blocking_process == False:
        ps = subprocess.run((bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops, '-I', '-Q'), stdout=fp, stderr=fp)

    elif integrity_check == True and sequential_writes == False and blocking_process == False:
        ps = subprocess.run((bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-a', random_seed, '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops, '-I'), stdout=fp, stderr=fp)

    elif blocking_process == True and sequential_writes == False and integrity_check == False:
        ps = subprocess.Popen([bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops, '-I', '-Q'], stdout=fp, stderr=fp)

    else:
        ps = subprocess.run((bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-a', random_seed, '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops), stdout=fp, stderr=fp)

    logging.info("return code: ", ps.returncode)
    # Sync the log file so all the logs from niova-block-test gets written to log file.
    os.fsync(fp)

    return ps.returncode

def load_recipe_op_config(cluster_params):
    recipe_conf = {}
    raft_json_fpath = "%s/%s/%s.json" % (cluster_params['base_dir'],
                                         cluster_params['raft_uuid'],
                                         cluster_params['raft_uuid'])
    if os.path.exists(raft_json_fpath):
        with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
            recipe_conf = json.load(json_file)

    return recipe_conf

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        process_type = terms[0]
        input_values = terms[1]
        Key = ""
        Value = ""
        IP_addr = ""
        Port = ""

        cluster_params = kwargs['variables']['ClusterParams']

        if process_type == "niova-block-ctl":

                set_environment_variables(cluster_params)

                # Start niova-block-ctl process
                test_device_path = create_nisd_device_and_uuid(input_values['nisd_uuid'],
                                                                input_values['nisd_dev_size'])
                niova_block_ctl_process = start_niova_block_ctl_process(cluster_params, test_device_path,
                                                                               input_values['nisd_uuid'])

                return niova_block_ctl_process

        elif process_type == "nisd":

                set_environment_variables(cluster_params)

                #start nisd process
                nisdPath = prepare_nisd_device_path(input_values['nisd_uuid'])
                nisd_process = start_nisd_process(cluster_params,  input_values['nisd_uuid'], input_values['uport'], nisdPath)

                return nisd_process

        elif process_type == "niova-block-test":

                set_environment_variables(cluster_params)

                # Start niova-block-test
                niova_block_test_process = start_niova_block_test(cluster_params, input_values['uuid_to_write'], input_values['vdev'],
                                                                  input_values['read_operation_ratio_percentage'], input_values['random_seed'],
                                                                  input_values['client_uuid'], input_values['request_size_in_bytes'],
                                                                  input_values['queue_depth'], input_values['num_ops'], input_values['integrity_check'],
                                                                  input_values['sequential_writes'], input_values['blocking_process'])
                return niova_block_test_process
