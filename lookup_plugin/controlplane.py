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

def start_ncpc_process(cluster_params, Key, Value, Operation,
                                     OutfileName, IP_addr, Port):
    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    bin_path = '%s/ncpc' % binary_dir

    # Prepare path for log file.
    log_file = "%s/%s/%s_ncpc_log.txt" % (base_dir, raft_uuid, app_name)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")
    logfile = "%s/%s/ncpclogfile.log" % (base_dir, raft_uuid)

    # Prepare config file path for ncpc
    ConfigPath = "%s/%s/gossipNodes" % (base_dir, raft_uuid)

    outfilePath = "%s/%s/%s" % (base_dir, raft_uuid, OutfileName)
    
    if Value == "" :
        process_popen = subprocess.Popen([bin_path, '-k', Key, '-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-r', outfilePath,
                                             '-a' , IP_addr, '-p', Port],
                                             stdout = fp, stderr = fp)
    else:
        process_popen = subprocess.Popen([bin_path, '-k', Key,
                                             '-v', Value, '-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-r', outfilePath],
                                             stdout = fp, stderr = fp)

    # Sync the log file so all the logs from ncpc gets written to log file.
    os.fsync(fp)
    return process_popen, outfilePath

def get_the_output(outfilePath):
    outfile = outfilePath+'.json'
    counter = 0
    timeout = 120

    # Wait till the output json file gets created.
    while True:
        if not os.path.exists(outfile):
            counter += 1
            time.sleep(0.1)
            if counter == timeout:
                return {"status":-1,"msg":"Timeout checking for output file"}
        else:
            break

    output_data = {}
    with open(outfile, "r+", encoding="utf-8") as json_file:
        output_data = json.load(json_file)

    return output_data

def start_niova_block_ctl_process(cluster_params, nisdPath, nisd_uuid):
    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for log file.
    log_file = "%s/%s/%s_niovablockctl_%s_log.txt" % (base_dir, raft_uuid, app_name, nisd_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    #format and run the niova-block-ctl
    bin_path = '%s/niova-block-ctl' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-d', nisdPath, '-i', nisd_uuid],
                                   stdout = fp, stderr = fp)
    
    logging.warning("niova-block-ctl process is started to format the device")
    process_pid = process_popen.pid
    process_status = ''

    rc = 0
    try:
        func_timeout(60, check_for_process_status, args=(process_pid, process_status))
    except FunctionTimedOut:
        logging.error("Error : timeout occur to change process status to %s" % process_status)
        rc = 1

    # Sync the log file so all the logs from niova-block-ctl gets written to log file.
    os.fsync(fp)

    return process_popen


def check_for_process_status(pid, process_status):
    process_status = "zombie"
    ps = psutil.Process(pid)
    itr = 0
    while(1):
        if ps.status() == process_status:
           break
        time_global.sleep(0.025)
        #After every 50 iterations, print process status.
        if itr == 50:
            logging.warning("process status %s (expected %s)"% (ps.status(), process_status))
            itr = 0
        itr += 1

def start_nisd_process(cluster_params, nisd_uuid, nisdPath):
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare seperate path for nisd log file.
    log_file = "%s/%s/%s_nisd_%s_log.txt" % (base_dir, raft_uuid, app_name, nisd_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")

    #start nisd process
    bin_path = '%s/nisd' % binary_dir
    process_popen = subprocess.Popen([bin_path, '-u', nisd_uuid, '-d', nisdPath],
            stdout = fp, stderr = fp)
    logging.warning("starting nisd process")
    
    # writing the information of lookout and nisd into raft_uuid.json file 
    recipe_conf = load_recipe_op_config(cluster_params)
    pid = process_popen.pid
    ps = psutil.Process(pid)

    if not "raft_process" in recipe_conf:
        recipe_conf['raft_process'] = {}

    recipe_conf['raft_process'][nisd_uuid] = {}

    recipe_conf['raft_process'][nisd_uuid]['process_raft_uuid'] = nisd_uuid
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


def prepare_nisd_device_path(cluster_params, nisd_uuid):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    #prepare the nisd device path
    device_path = "%s/%s" % (cluster_params['base_dir'], cluster_params['raft_uuid'])
    nisd_file_name = "test_nisd_%s.device" % nisd_uuid

    nisdPath = os.path.join(device_path, nisd_file_name)

    return nisdPath

def create_nisd_device_and_uuid(cluster_params, nisd_uuid, nisd_dev_size):
    nisdpath_device = prepare_nisd_device_path(cluster_params, nisd_uuid)

    # truncate the device to a specified size
    file = open(nisdpath_device, 'w')
    file.truncate(int(nisd_dev_size))
    file.close()

    return nisdpath_device

def set_environment_variables(cluster_params,lookout_uuid):
    niova_lookout_ctl_interface_path = "%s/%s/niova_lookout/%s" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'], lookout_uuid)

    if os.path.exists(niova_lookout_ctl_interface_path):
        print("file already exist")
    else:
        os.mkdir(niova_lookout_ctl_interface_path)

    #set environment variables
    os.environ['NIOVA_INOTIFY_BASE_PATH'] = niova_lookout_ctl_interface_path
    os.environ['NIOVA_LOCAL_CTL_SVC_DIR'] = niova_lookout_ctl_interface_path

    return niova_lookout_ctl_interface_path

def start_niova_lookout_process(cluster_params, lookout_uuid, aport, hport, rport, uport):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    app_name = cluster_params['app_type']

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    ctl_interface_path = set_environment_variables(cluster_params, lookout_uuid)

    # Prepare path for log file.
    log_file = "%s/%s/%s_niova-lookout_%s_log.txt" % (base_dir, raft_uuid, app_name, lookout_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")
    gossipNodes = "%s/%s/gossipNodes" % (base_dir, raft_uuid)

    #start niova block test process
    bin_path = '%s/lookout' % binary_dir

    process_popen = subprocess.Popen([bin_path, '-dir', str(ctl_interface_path), '-c', gossipNodes, '-n', lookout_uuid,
                                            '-p', aport, '-port', hport, '-r', rport, '-u', uport], stdout = fp, stderr = fp)

    logging.warning("starting niova-lookout process")

    #writing the information of nisd into raft_uuid.json
    recipe_conf = load_recipe_op_config(cluster_params)
    pid = process_popen.pid
    ps = psutil.Process(pid)

    if not "raft_process" in recipe_conf:
        recipe_conf['raft_process'] = {}

    recipe_conf['raft_process'][lookout_uuid] = {}

    recipe_conf['raft_process'][lookout_uuid]['process_raft_uuid'] = lookout_uuid
    recipe_conf['raft_process'][lookout_uuid]['process_pid'] = pid
    recipe_conf['raft_process'][lookout_uuid]['process_uuid'] = lookout_uuid
    recipe_conf['raft_process'][lookout_uuid]['process_type'] = "lookout"
    recipe_conf['raft_process'][lookout_uuid]['process_app_type'] = app_name
    recipe_conf['raft_process'][lookout_uuid]['process_status'] = ps.status()

    genericcmdobj = GenericCmds()
    genericcmdobj.recipe_json_dump(recipe_conf)

    # Sync the log file so all the logs from niova-block-test gets written to log file.
    os.fsync(fp)

    return process_popen

def start_niova_block_test(cluster_params, nisd_uuid_to_write, read_operation_ratio_percentage,
                                num_ops, vdev, request_size_in_bytes, queue_depth, file_size):
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare path for log file.
    log_file = "%s/%s/%s_niova-block-test_%s_log.txt" % (base_dir, raft_uuid, app_name, nisd_uuid_to_write)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")

    #start niova block test process
    bin_path = '%s/niova-block-test' % binary_dir
    process_popen = subprocess.Popen([bin_path, '-c', nisd_uuid_to_write, '-r' , read_operation_ratio_percentage,
                                               '-N', num_ops, '-v',vdev,'-Z', request_size_in_bytes,
                                               '-q', queue_depth, '-z', file_size],
                                                     stdout = fp, stderr = fp)
    
    logging.warning("starting niova-block-test to write to nisd device")
    # Sync the log file so all the logs from niova-block-test gets written to log file.
    os.fsync(fp)

    return process_popen

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

        if process_type == "ncpc":
            
            if input_values['Operation'] == "write":
                # Start the ncpc_client and perform the specified operation e.g write/read/config.
                process,outfile = start_ncpc_process(cluster_params, input_values['Key'], input_values['Value'],
                                                   input_values['Operation'], input_values['OutfileName'],
                                                   input_values['IP_addr'], input_values['Port'])

                output_data = get_the_output(outfile)
            elif input_values['Operation'] == "read":
                # Start the ncpc_client and perform the specified operation e.g write/read/config.
                process,outfile = start_ncpc_process(cluster_params, input_values['Key'], Value,
                                                   input_values['Operation'], input_values['OutfileName'],
                                                   IP_addr, Port)
                output_data = get_the_output(outfile)
            else:
                # Start the ncpc_client and perform the specified operation e.g write/read/config.
                process,outfile = start_ncpc_process(cluster_params, Key, Value,
                                                   input_values['Operation'], input_values['OutfileName'],
                                                   IP_addr, Port)
                output_data = get_the_output(outfile)


            return output_data

        else:
            if process_type == "niova-block-ctl":

                lookout_uuid = input_values['lookout_uuid'] 
                set_environment_variables(cluster_params, input_values['lookout_uuid'])
                
                # Start niova-block-ctl process
                test_device_path = create_nisd_device_and_uuid(cluster_params, input_values['nisd_uuid'],
                                                                input_values['nisd_dev_size'])

                niova_block_ctl_process = start_niova_block_ctl_process(cluster_params, test_device_path,
                                                                               input_values['nisd_uuid'])

                return niova_block_ctl_process

            elif process_type == "nisd":

                set_environment_variables(cluster_params, input_values['lookout_uuid'])
                
                #start nisd process
                nisdPath = prepare_nisd_device_path(cluster_params, input_values['nisd_uuid'])
                nisd_process = start_nisd_process(cluster_params,  input_values['nisd_uuid'], nisdPath)

                return nisd_process

            elif process_type == "niova-block-test":

                set_environment_variables(cluster_params, input_values['lookout_uuid'])
                
                # Start niova-block-test
                niova_block_test_process = start_niova_block_test(cluster_params, input_values['uuid_to_write'],
                                                                  input_values['read_operation_ratio_percentage'],
                                                                  input_values['num_ops'],input_values['vdev'],
                                                                  input_values['request_size_in_bytes'],input_values['queue_depth'],
                                                                  input_values['file_size'])
                return niova_block_test_process

            elif process_type == "niova-lookout"  :
                
                niova_lookout_path = "%s/%s/niova_lookout" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'])

                if os.path.exists(niova_lookout_path):
                    print("file already exist")
                else:
                    os.mkdir(niova_lookout_path)

                niova_lookout_process = start_niova_lookout_process(cluster_params, input_values['lookout_uuid'],
                                                                      input_values['aport'], input_values['hport'],
                                                                      input_values['rport'], input_values['uport'])
                return niova_lookout_process
