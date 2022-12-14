from ansible.plugins.lookup import LookupBase
import os
import time
import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *
from inotifypath import *

def create_gdb_file(app_name, peer_uuid, ptype, binary_dir, gdb_cmd):
    gdb_file = ""
    cmd = ""
    if app_name == "pumicedb":
         if ptype == "server":
             gdb_file = '%s/debug_server_%s.gdb' % (binary_dir, peer_uuid)
             cmd = "--command=%s" % gdb_file
         else:
             gdb_file = '%s/debug_client_%s.gdb' % (binary_dir, peer_uuid)
             cmd = "--command=%s" % gdb_file
    else:
         gdb_file = '%s/nblock_test_%s.gdb' % (binary_dir, peer_uuid)
         cmd = "--command=%s" % gdb_file

    # Open the file in append & read mode ('a+')
    with open(gdb_file, "a+") as file_object:
        # Move read cursor to the start of file.
        file_object.seek(0)
        # If file is not empty then append '\n'
        data = file_object.read(100)
        if len(data) > 0 :
            file_object.write("\n")
        # Append text at the end of file
        file_object.write("\n" + gdb_cmd + "\n")

    return cmd

def run_gdb_script(bin_path, base_dir, cmd, raft_uuid, peer_uuid, ptype, app_name, binary_dir):

    log_file = "%s/gdb_logfile_%s.log" % (base_dir, peer_uuid)
    # Open the log file to pass the fp to subprocess.Popen
    fp = open(log_file, "w")

    if app_name == "pumicedb":
        if ptype == "server":
            bin_path = '%s/pumice-reference-server' % binary_dir
            process_popen = subprocess.Popen(['gdb', '--batch', cmd, '--args', bin_path, '-r',
                                                  raft_uuid, '-u', peer_uuid, '-a'],
                                                  stdout = fp, stderr = fp)
        else:
            bin_path = '%s/pumice-reference-client' % binary_dir
            process_popen = subprocess.Popen(['gdb', '--batch', cmd, '--args', bin_path, '-r',
                                                  raft_uuid, '-u', peer_uuid, '-a'],
                                                  stdout = fp, stderr = fp)

    # Sync the log file so all the logs from gdb gets written to log file.
    os.fsync(fp)

    return process_popen

def set_environment_variables(cluster_params, lookout_uuid):
    niova_lookout_ctl_interface_path = "%s/%s/niova_lookout/%s" % (cluster_params['base_dir'],
                                                           cluster_params['raft_uuid'], lookout_uuid)

    if os.path.exists(niova_lookout_ctl_interface_path):
        print("file already exist")
    else:
        os.mkdir(niova_lookout_ctl_interface_path)

    #set environment variables
    os.environ['NIOVA_INOTIFY_BASE_PATH'] = niova_lookout_ctl_interface_path
    os.environ['NIOVA_LOCAL_CTL_SVC_DIR'] = niova_lookout_ctl_interface_path

def start_niova_block_test(cluster_params, peer_uuid, cmd, nisd_uuid_to_write, vdev, read_operation_ratio_percentage,
                                random_seed, client_uuid, request_size_in_bytes, queue_depth, num_ops):

    # Prepare path for executables.
    binary_dir = os.getenv('NIOVA_BIN_PATH')

    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    gdb_log_file = "%s/%s/gdb_logfile_nblock_test_%s.log" % (base_dir, raft_uuid, peer_uuid)

    # Open the log file to pass the fp to subprocess.Popen
    fp = open(gdb_log_file, "w")

    #start niova block test process
    bin_path = '%s/niova-block-test' % binary_dir
    process_popen = subprocess.Popen(['gdb', '--batch', cmd, '--args', bin_path, '-d', '-c', nisd_uuid_to_write, '-v',vdev, '-r', read_operation_ratio_percentage,
                                               '-a', random_seed, '-u', client_uuid, '-Z', request_size_in_bytes,
                                               '-q', queue_depth, '-N', num_ops, '-I'],
                                                     stdout = fp, stderr = fp)

    logging.warning("starting niova-block-test to write to nisd device")
    # Sync the log file so all the logs from niova-block-test gets written to log file.
    os.fsync(fp)

    return process_popen

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values[cmd]
        ptype = terms[0]
        gdb_cmd = terms[1]
        peer_uuid = terms[2]

        cluster_params = kwargs['variables']['ClusterParams']

        #export NIOVA_THREAD_COUNT
        os.environ['NIOVA_THREAD_COUNT'] = cluster_params['nthreads']

        cluster_info = kwargs['variables']['ClusterInfo']

        raft_uuid = cluster_info['raft_uuid']
        base_dir =  cluster_info['base_dir_path']
        app_name = cluster_params['app_type']

        if (len(terms) == 4):
            app_name = "controlplane"
        else:
            app_name = "pumicedb"

        bin_path = ""
        binary_dir = os.getenv('NIOVA_BIN_PATH')

        if app_name == "pumicedb":
            ctlsvc_path = cluster_info['server_config_path']
            get_process_type = "pmdb"
            lookout_uuid = ""
            inotifyobj = InotifyPath(base_dir, True, get_process_type, lookout_uuid)
            inotifyobj.export_ctlsvc_path(ctlsvc_path)

            cmd = create_gdb_file(app_name, peer_uuid, ptype, binary_dir, gdb_cmd)
            if ptype == "server":
                process_popen = run_gdb_script(bin_path, base_dir, cmd, raft_uuid, peer_uuid, ptype, app_name, binary_dir)

            else:
                process_popen = run_gdb_script(bin_path, base_dir, cmd, raft_uuid, peer_uuid, ptype, app_name, binary_dir)

        elif app_name == "controlplane":
             input_values = terms[3]

             cmd = create_gdb_file(app_name, peer_uuid, ptype, binary_dir, gdb_cmd)
             set_environment_variables(cluster_params, input_values['lookout_uuid'])

             # Start niova-block-test
             process_popen = start_niova_block_test(cluster_params, peer_uuid, cmd, input_values['uuid_to_write'], input_values['vdev'],
                                                                          input_values['read_operation_ratio_percentage'], input_values['random_seed'],
                                                                          input_values['client_uuid'], input_values['request_size_in_bytes'],
                                                                          input_values['queue_depth'], input_values['num_ops'])

        return process_popen
