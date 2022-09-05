from ansible.plugins.lookup import LookupBase
import fcntl, psutil, uuid
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

def start_ncpc(cluster_params, Key, Value, Operation,
                                     OutfileName, IP_addr, Port, NumWrites, seqNo):
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

    outfilePath = "%s/%s/%s_%s" % (base_dir, raft_uuid, OutfileName, uuid.uuid1())

    if Operation == "read":
        if seqNo != "" and NumWrites != "":
            process_popen = subprocess.Popen([bin_path, '-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-j', outfilePath,
                                             '-k', Key, '-n', NumWrites, '-S', seqNo], stdout = fp, stderr = fp)
        elif NumWrites != "":
            process_popen = subprocess.Popen([bin_path, '-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-j', outfilePath,
                                             '-k', Key, '-n', NumWrites], stdout = fp, stderr = fp)
        else:
            process_popen = subprocess.Popen([bin_path, '-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-j', outfilePath,
                                             '-k', Key], stdout = fp, stderr = fp)

    elif Operation == "write":
        if NumWrites == "":
            process_popen = subprocess.Popen([bin_path, '-k', Key, '-v', Value,'-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-j', outfilePath,
                                             '-a' , IP_addr, '-p', Port],
                                             stdout = fp, stderr = fp)
        else:
            process_popen = subprocess.Popen([bin_path, '-k', Key, '-v', Value,'-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-j', outfilePath,
                                             '-a' , IP_addr, '-p', Port, '-n', NumWrites],
                                             stdout = fp, stderr = fp)
    else:
        process_popen = subprocess.Popen([bin_path, '-k', Key,
                                             '-v', Value, '-c', ConfigPath,
                                             '-l', logfile, '-o', Operation, '-j', outfilePath],
                                             stdout = fp, stderr = fp)

    # Sync the log file so all the logs from ncpc gets written to log file.
    os.fsync(fp)
    return process_popen, outfilePath

def extracting_dictionary(cluster_params, input_values):
    Key = ""
    Value = ""
    IP_addr = ""
    Port = ""
    NumWrites = ""
    seqNo = ""

    if input_values['Operation'] == "write" and input_values['NoofWrites'] == "":
        # Start the ncpc_client and perform the specified operation e.g write/read/config.
        process,outfile = start_ncpc(cluster_params, input_values['Key'], input_values['Value'],
                                           input_values['Operation'], input_values['OutfileName'],
                                           input_values['IP_addr'], input_values['Port'], NumWrites, seqNo)
        if input_values['wait_for_outfile']:
            output_data = get_the_output(outfile)
            return output_data
        else:
            return outfile

    elif input_values['Operation'] == "write" and input_values['NoofWrites'] != "":
        # Start the ncpc_client and perform the specified operation e.g write/read/config.
        process,outfile = start_ncpc(cluster_params, Key, Value,
                                           input_values['Operation'], input_values['OutfileName'],
                                           IP_addr, Port, input_values['NoofWrites'], seqNo)
        if input_values['wait_for_outfile']:
            output_data = get_the_output(outfile)
            return output_data
        else:
            return outfile

    elif input_values['Operation'] == "read" and input_values['NoofWrites'] == "":
        # Start the ncpc_client and perform the specified operation e.g write/read/config.
        process,outfile = start_ncpc(cluster_params, input_values['Key'], Value,
                                           input_values['Operation'], input_values['OutfileName'],
                                           IP_addr, Port, NumWrites, seqNo)
        if input_values['wait_for_outfile']:
            output_data = get_the_output(outfile)
            return output_data
        else:
            return outfile

    elif input_values['Operation'] == "read" and input_values['NoofWrites'] != "":
        # Start the ncpc_client and perform the specified operation e.g write/read/config.
        process,outfile = start_ncpc(cluster_params, input_values['Key'], Value,
                                           input_values['Operation'], input_values['OutfileName'],
                                           IP_addr, Port, input_values['NoofWrites'], input_values['seqNo'])
        if input_values['wait_for_outfile']:
            output_data = get_the_output(outfile)
            return output_data
        else:
            return outfile

    elif input_values['Operation'] == "membership":
        # Start the ncpc_client and perform the specified operation e.g write/read/config.
        process,outfile = start_ncpc(cluster_params, Key, Value,
                                           input_values['Operation'], input_values['OutfileName'],
                                           IP_addr, Port, NumWrites, seqNo)
        output_data = get_the_output(outfile)
        return {"membership":output_data}

    elif input_values['Operation'] == "NISDGossip":
        # Start the ncpc_client and perform the specified operation e.g write/read/config.
        process,outfile = start_ncpc(cluster_params, Key, Value,
                                           input_values['Operation'], input_values['OutfileName'],
                                           IP_addr, Port, NumWrites, seqNo)
        output_data = get_the_output(outfile)
        return {"NISDGossip":output_data}

    elif input_values['Operation'] == "config":
        # Start the ncpc_client and perform the specified operation e.g write/read/config.
        process,outfile = start_ncpc(cluster_params, Key, Value,
                                           input_values['Operation'], input_values['OutfileName'],
                                           IP_addr, Port, NumWrites, seqNo)
        output_data = get_the_output(outfile)
        return {"config":output_data}

def get_the_output(outfilePath):
    outfile = outfilePath + '.json'
    counter = 0
    timeout = 160

    # Wait till the output json file gets created.
    while True:
        if not os.path.exists(outfile):
            counter += 1
            time.sleep(1)
            if counter == timeout:
                return {"status":-1,"msg":"Timeout checking for output file"}
        else:
            break

    output_data = {}
    with open(outfile, "r+", encoding="utf-8") as json_file:
        output_data = json.load(json_file)
    return output_data

def set_environment_variables(cluster_params,lookout_uuid):
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

def start_niova_lookout_process(cluster_params, aport, hport, rport, uport):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    app_name = cluster_params['app_type']

    genericcmdobj = GenericCmds()
    lookout_uuid = genericcmdobj.generate_uuid()
    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    ctl_interface_path = set_environment_variables(cluster_params, lookout_uuid)

    # Prepare path for log file.
    log_file = "%s/%s/%s_niova-lookout_%s_log.txt" % (base_dir, raft_uuid, app_name, lookout_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")
    gossipNodes = "%s/%s/gossipNodes" % (base_dir, raft_uuid)

    #start niova block test process
    bin_path = '%s/nisdLookout' % binary_dir

    ports = { 'aport' : 0, 'hport' : 0, 'rport' : 0 ,'uport' : 0}

    ports['aport'] = aport
    ports['hport'] = hport
    ports['rport'] = rport
    ports['uport'] = uport

    #writing the information of lookout uuids dict into raft_uuid.json
    recipe_conf = load_recipe_op_config(cluster_params)

    if not "lookout_uuid_dict" in recipe_conf:
        recipe_conf['lookout_uuid_dict'] = {}

    recipe_conf['lookout_uuid_dict'][lookout_uuid] = {}
    recipe_conf['lookout_uuid_dict'][lookout_uuid] = ports

    genericcmdobj.recipe_json_dump(recipe_conf)

    logging.info("starting niova-lookout process")
    process_popen = subprocess.Popen([bin_path, '-dir', str(ctl_interface_path), '-c', gossipNodes, '-n', lookout_uuid,
                                            '-p', aport, '-port', hport, '-r', rport, '-u', uport], stdout = fp, stderr = fp)

    #Check if niova-lookout process exited with error
    if process_popen.poll() is None:
        logging.info("niova-lookout process started successfully")
    else:
        logging.info("niova-lookout failed to start")
        raise subprocess.SubprocessError(process_popen.returncode)

    #writing the information of lookout uuid in raft_process into raft_uuid.json
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

    return lookout_uuid

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

        cluster_params = kwargs['variables']['ClusterParams']
        
        if process_type == "ncpc":
            
            data = extracting_dictionary(cluster_params, input_values)
            
            return data

        elif process_type == "niova-lookout":

            niova_lookout_path = "%s/%s/niova_lookout" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'])
            if os.path.exists(niova_lookout_path):
                print("file already exist")
            else:
                os.mkdir(niova_lookout_path)

            niova_lookout_process = start_niova_lookout_process(cluster_params, input_values['aport'], input_values['hport'],
                                                                 input_values['rport'], input_values['uport'])
            return niova_lookout_process
