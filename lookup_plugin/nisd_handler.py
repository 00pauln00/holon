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
import logging

def initialize_logger(log_file):

    #now we will Create and configure logger
    logging.basicConfig(filename=log_file,
                                        format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s',
                                        filemode='a+')

    #Let us Create an object
    logger=logging.getLogger()

    #Now we are going to Set the threshold of logger to DEBUG
    logger.setLevel(logging.DEBUG)

    return logger

def start_niova_block_ctl_process(cluster_params, nisd_uuid, input_values):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    genericcmdobj = GenericCmds()
    nisd_uuid = genericcmdobj.generate_uuid()

    # Prepare path for log file.
    log_file = "%s/%s/niovablockctl_%s_log.txt" % (base_dir, raft_uuid, nisd_uuid)

    # Initialize the logger
    logger = initialize_logger(log_file)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "a+")

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    #format and run the niova-block-ctl
    bin_path = '%s/niova-block-ctl' % binary_dir

    nisd_dict = { nisd_uuid : 0 }

    nisd_dict[nisd_uuid] = 0

     #writing the information of lookout uuids dict into raft_uuid.json
    recipe_conf = load_recipe_op_config(cluster_params)

    if not "lookout_uuid_dict" in recipe_conf:
        recipe_conf['lookout_uuid_dict'] = {}

    if input_values['lookout_uuid'] != "":
        if not "nisd_uuid_dict" in recipe_conf['lookout_uuid_dict'][input_values['lookout_uuid']]:
            recipe_conf['lookout_uuid_dict'][input_values['lookout_uuid']]['nisd_uuid_dict'] = {}

        recipe_conf['lookout_uuid_dict'][input_values['lookout_uuid']]['nisd_uuid_dict'].update(nisd_dict)
    else:
        if not "nisd_uuid_dict" in recipe_conf:
            recipe_conf['nisd_uuid_dict'] = {}
        recipe_conf['nisd_uuid_dict'].update(nisd_dict)

    genericcmdobj.recipe_json_dump(recipe_conf)

    nisdPath = prepare_nisd_device_path(nisd_uuid)

    logger.debug("nisd-uuid: %s", nisd_uuid)

    # Start niova-block-ctl process
    test_device_path = create_nisd_device_and_uuid(nisd_uuid, input_values['nisd_dev_size'])

    process_popen = subprocess.Popen([bin_path, '-n', input_values['alt_name'], '-d', nisdPath, '-i', '-u', nisd_uuid,
                                       '-Z', input_values['nisd_dev_size']], stdout = fp, stderr = fp)

    logger.info("niova-block-ctl args: %s", process_popen.args)
    #Check if niova-block-ctl process exited with error
    if process_popen.poll() is None:
        logger.info("niova-block-ctl process started successfully")
    else:
        logger.error("niova-block-ctl process failed to start")
        raise subprocess.SubprocessError(process_popen.returncode)

    # Sync the log file so all the logs from niova-block-ctl gets written to log file.
    os.fsync(fp)

    return nisd_uuid

def start_nisd_process(cluster_params, input_values, nisdPath):
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    app_name = cluster_params['app_type']
    raft_uuid = cluster_params['raft_uuid']

    # Prepare seperate path for nisd log file.
    log_path = "%s/%s/nisd_%s_log.txt" % (base_dir, raft_uuid, input_values['nisd_uuid'])

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_path, "a+")

    genericcmdobj = GenericCmds()
    #writing the information of lookout uuids dict into raft_uuid.json
    recipe_conf = load_recipe_op_config(cluster_params)

    nisd_uuid = input_values['nisd_uuid']
    uport = input_values['uport']

    if input_values['lookout_uuid'] != "":
        if nisd_uuid in recipe_conf['lookout_uuid_dict'][input_values['lookout_uuid']]['nisd_uuid_dict']:
            recipe_conf['lookout_uuid_dict'][input_values['lookout_uuid']]['nisd_uuid_dict'].update({ nisd_uuid : uport })
    else:
        if input_values['nisd_uuid'] in recipe_conf['nisd_uuid_dict'].keys():
            recipe_conf['nisd_uuid_dict'][nisd_uuid] = uport

    fp.write("starting nisd process\n")
    fp.write("nisd-uuid: "+nisd_uuid+"\n")

    #start nisd process
    bin_path = '%s/nisd' % binary_dir
    process_popen = subprocess.Popen([bin_path, '-u', nisd_uuid, '-p', uport, '-d', nisdPath],
                                      stdout = fp, stderr = fp)

    fp.write("nisd args: "+str(process_popen.args)+"\n")
    #Check if nisd process exited with error
    if process_popen.poll() is None:
        fp.write("NISD process started successfully")
    else:
        fp.write("NISD process failed to start")
        raise subprocess.SubprocessError(process_popen.returncode)

    # writing the information of lookout and nisd into raft_uuid.json file
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

    genericcmdobj.recipe_json_dump(recipe_conf)

    # Sync the log file so all the logs from nisd gets written to log file.
    os.fsync(fp)

    return process_popen

def prepare_nisd_device_path(nisd_uuid):
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    nisdPath = "%s/%s.device" % (binary_dir, nisd_uuid)
    return nisdPath

def create_nisd_device_and_uuid(nisd_uuid, nisd_dev_size):
    nisdpath_device = prepare_nisd_device_path(nisd_uuid)

    # truncate the device to a specified size
    file = open(nisdpath_device, 'w')
    file.truncate(int(nisd_dev_size))
    file.close()

    return nisdpath_device

def controlplane_environment_variables(cluster_params,lookout_uuid):
    niova_lookout_ctl_interface_path = "%s/%s/niova_lookout/%s" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'], lookout_uuid)

    if os.path.exists(niova_lookout_ctl_interface_path):
        logging.info("file already exist")
    else:
        os.mkdir(niova_lookout_ctl_interface_path)
    #set environment variables
    os.environ['NIOVA_INOTIFY_BASE_PATH'] = niova_lookout_ctl_interface_path
    os.environ['NIOVA_LOCAL_CTL_SVC_DIR'] = niova_lookout_ctl_interface_path

    return niova_lookout_ctl_interface_path

def start_niova_block_test_with_inputFile(cluster_params, input_values):
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    f = open("niova_block_test_inputs.txt")
    next(f)

    input_dict = {}
    i = 0
    j = 0

    nisd_uuid_to_write = input_values['nisd_uuid_to_write']
    if not 'niova-block-test-input' in input_dict:
         input_dict['niova-block-test-input'] = {}

    input_dict['niova-block-test-input'][nisd_uuid_to_write[5:]] = {}
    input_dict['niova-block-test-input'][nisd_uuid_to_write[5:]]['write-input'] = {}
    input_dict['niova-block-test-input'][nisd_uuid_to_write[5:]]['read-input'] = {}

    for line in f:
      # parse input, assign values to variables
        currentline = line.split(",")

        operation_type = currentline[0]
        read_operation_ratio_percentage = currentline[1]
        random_seed =  currentline[2]
        request_size_in_bytes =  currentline[3]
        queue_depth =  currentline[4]
        num_ops =  currentline[5]
        integrity_check =  currentline[6]
        sequential_writes =  currentline[7]
        blocking_process = currentline[8]
        sleep = int(currentline[9])

        vdev = input_values['vdev']
        client_uuid = input_values['client_uuid']

        info = {'vdev-uuid': vdev, 'read-operation-ratio-percentage' : read_operation_ratio_percentage, 'num-ops': num_ops, 'req-size-bytes': request_size_in_bytes}
        info['vdev-uuid'] = vdev
        info['read-operation-ratio-percentage'] = read_operation_ratio_percentage
        info['num-ops'] = num_ops
        info['req-size-bytes'] = request_size_in_bytes

        if operation_type == "write":
            i += 1
            input_cnt = "input" + str(i)
            input_dict['niova-block-test-input'][nisd_uuid_to_write[5:]]['write-input'][input_cnt] = {}
            input_dict['niova-block-test-input'][nisd_uuid_to_write[5:]]['write-input'][input_cnt] = info
        else:
            j += 1
            input_cnt = "input" + str(j)
            input_dict['niova-block-test-input'][nisd_uuid_to_write[5:]]['read-input'][input_cnt] = {}
            input_dict['niova-block-test-input'][nisd_uuid_to_write[5:]]['read-input'][input_cnt] = info

        if operation_type == 'write':
            # prepare path for log file.
            log_path = "%s/%s/niova-block-test_%s_%s.log" % (base_dir, raft_uuid, operation_type, nisd_uuid_to_write[5:])
        else:
            # Prepare path for log file.
            log_path = "%s/%s/niova-block-test_%s_%s.log" % (base_dir, raft_uuid, operation_type, nisd_uuid_to_write[5:])

        # Initialize the logger
        logger = initialize_logger(log_path)

        # Open the log file to pass the fp to subprocess.Popen
        fp = open(log_path, "a+")

        #start niova block test process
        bin_path = '%s/niova-block-test' % binary_dir

        logger.debug("Do write/read operation on nisd by starting niova-block-test")
        logger.debug("nisd-uuid: %s", nisd_uuid_to_write[5:])
        logger.debug("vdev-uuid: %s", vdev)
        logger.debug("client-uuid: %s", client_uuid)

        if sequential_writes == True and integrity_check == False and blocking_process == False:
            ps = subprocess.Popen([bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                       '-u', client_uuid, '-Z', request_size_in_bytes,
                                       '-q', queue_depth, '-N', num_ops, '-I', '-Q'], stdout=fp, stderr=fp)

        elif integrity_check == True and sequential_writes == False and blocking_process == False:
            ps = subprocess.Popen([bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                       '-a', random_seed, '-u', client_uuid, '-Z', request_size_in_bytes,
                                       '-q', queue_depth, '-N', num_ops, '-I'], stdout=fp, stderr=fp)

        elif blocking_process == True and sequential_writes == False and integrity_check == False:
            ps = subprocess.Popen([bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                       '-u', client_uuid, '-Z', request_size_in_bytes,
                                       '-q', queue_depth, '-N', num_ops, '-I', '-Q'], stdout=fp, stderr=fp)

        else:
            ps = subprocess.Popen([bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                       '-a', random_seed, '-u', client_uuid, '-Z', request_size_in_bytes,
                                       '-q', queue_depth, '-N', num_ops], stdout=fp, stderr=fp)

        out, err = ps.communicate()
        logger.info("niova-block-test: %s", ps.args)
        logger.info("return code: %d", ps.returncode)
        info['returncode'] = ps.returncode
        # Sync the log file so all the logs from niova-block-test gets written to log file.
        os.fsync(fp)
        time.sleep(sleep)

    f.close()
    return input_dict

def start_niova_block_test(cluster_params, input_values):
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    #get input parameters
    nisd_uuid_to_write = input_values['nisd_uuid_to_write']
    vdev = input_values['vdev']
    read_operation_ratio_percentage = input_values['read_operation_ratio_percentage']
    random_seed = input_values['random_seed']
    client_uuid = input_values['client_uuid']
    request_size_in_bytes = input_values['request_size_in_bytes']
    queue_depth = input_values['queue_depth']
    num_ops = input_values['num_ops']
    integrity_check = input_values['integrity_check']
    sequential_writes = input_values['sequential_writes']
    blocking_process = input_values['blocking_process']

    if read_operation_ratio_percentage == '0':
        # prepare path for log file.
        log_path = "%s/%s/niova-block-test_write_%s.log" % (base_dir, raft_uuid, nisd_uuid_to_write[5:])
    else:
        # Prepare path for log file.
        log_path = "%s/%s/niova-block-test_read_%s.log" % (base_dir, raft_uuid, nisd_uuid_to_write[5:])

    # Initialize the logger
    logger = initialize_logger(log_path)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_path, "a+")

    #start niova block test process
    bin_path = '%s/niova-block-test' % binary_dir

    logger.debug("Do write/read operation on nisd by starting niova-block-test")
    logger.debug("nisd-uuid: %s", nisd_uuid_to_write[5:])
    logger.debug("vdev-uuid: %s", vdev)
    logger.debug("client-uuid: %s", client_uuid)
    file_size_in_bytes = "8589934592"
    
    if sequential_writes == True and integrity_check == False and blocking_process == False:
        ps = subprocess.run((bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops, '-I', '-Q', '-z', file_size_in_bytes), stdout=fp, stderr=fp)

    elif integrity_check == True and sequential_writes == False and blocking_process == False:
        ps = subprocess.run((bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-a', random_seed, '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops, '-I', '-z', file_size_in_bytes), stdout=fp, stderr=fp)

    elif blocking_process == True and sequential_writes == False and integrity_check == False:
        proc = subprocess.Popen([bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops, '-I', '-Q', '-z', file_size_in_bytes], stdout=fp, stderr=fp)

        poll = proc.poll()  # returns the exit code or None if the process is still running
        logger.info("niova-block-test args: %s", proc.args)
        logger.info("return code: %s", proc.returncode)
        return proc.returncode

    else:
        ps = subprocess.run((bin_path, '-d', '-c', nisd_uuid_to_write, '-v', vdev, '-r', read_operation_ratio_percentage,
                                   '-a', random_seed, '-u', client_uuid, '-Z', request_size_in_bytes,
                                   '-q', queue_depth, '-N', num_ops, '-z', file_size_in_bytes), stdout=fp, stderr=fp)

    logger.info("niova-block-test args: %s", ps.args)
    logger.info("return code: %d", ps.returncode)
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
        nisd_uuid = ""

        cluster_params = kwargs['variables']['ClusterParams']

        if process_type == "niova-block-ctl":

               controlplane_environment_variables(cluster_params, input_values['lookout_uuid'])
               niova_block_ctl_process = start_niova_block_ctl_process(cluster_params, nisd_uuid, input_values)

               return niova_block_ctl_process

        elif process_type == "nisd":

               controlplane_environment_variables(cluster_params, input_values['lookout_uuid'])
               #start nisd process
               nisdPath = prepare_nisd_device_path(input_values['nisd_uuid'])
               nisd_process = start_nisd_process(cluster_params, input_values, nisdPath)

               return nisd_process

        elif process_type == "niova-block-test":

               NiovaBlocktest_input_file = cluster_params['niovaBlockTest_input_file_path']

               if cluster_params['niovaBlockTest_input_file_path'] == True:
                    # Take niova-block-test input parameters from input file and start process
                    niova_block_test_process = start_niova_block_test_with_inputFile(cluster_params, input_values)
               else:
                    # Start niova-block-test
                    niova_block_test_process = start_niova_block_test(cluster_params, input_values)

               return niova_block_test_process

