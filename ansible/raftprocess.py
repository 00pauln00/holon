import signal, subprocess, logging, psutil
import time as time_global
from raftconfig import RaftConfig
import shutil, os
from genericcmd import GenericCmds
from func_timeout import func_timeout, FunctionTimedOut

def check_for_process_status(pid, process_status):
    '''
    To check process status
    '''
    ps = psutil.Process(pid)
    while(1):
        if ps.status() == process_status:
            break

        time_global.sleep(0.005)
        logging.info(" process status %s (expected %s)"% (ps.status(), process_status))

class RaftProcess:

    process_type = ''
    process_uuid = ''
    process_status = ''
    process_popen = {}
    process_idx = 0
    process_cluster_type = 'raft'
    binary_path='/home/pauln/raft-builds/latest/raft-server'
    process_pid = 0

    '''
        Constructor:
        Purpose: Initialisation
        Parameter:  @cluster_type: Cluster is raft cluster or pumiceDB cluster.
					@uuid: UUID of server or client for which process object is
                            created.
                    @process_type: Type of the process(server or client)
    '''
    def __init__(self, cluster_type, uuid, process_idx, process_type):
        self.process_cluster_type = cluster_type
        self.process_uuid = uuid
        self.process_idx = process_idx
        self.process_type = process_type
        self.process_pid = 0

    '''
        Method: start_process
        Purpose: Start the process of type process_type
        Parameters: @raftconfobj: RaftConf object.
                    @uuid: UUID of the server or client.
    '''

    def Wait_for_process_status(self, process_status, pid):
        '''
        To wait for change in process status.
        Timeout is added to wait for change in process status till the specified time.
        '''
        rc = 0
        try:
            func_timeout(20, check_for_process_status, args=(pid, process_status))
        except FunctionTimedOut:
                logging.error("Error : timeout occur to change process status to %s" % process_status)
                rc = 1

        if rc == 1:
            exit()

    def start_process(self, raft_uuid, peer_uuid, base_dir):

        if self.process_cluster_type == "pumicedb":
            if self.process_type == "server":
                bin_path = '/home/pauln/raft-builds/latest/pumicedb-server-test'
            else:
                bin_path = '/home/pauln/raft-builds/latest/pumicedb-client-test'
        else:
            if self.process_type == "server":
                bin_path = '/home/pauln/raft-builds/latest/raft-server'
            else:
                bin_path = '/home/pauln/raft-builds/latest/raft-client'


        '''
        We want to append the output of raft-server log into the recipe log
        adding information about for which peerid the process has started.
        So first get the raft-server init log into temp file, add the prefix
        and then write it to recipe log.
        '''
        temp_file = "%s/raft_log_%s.txt" % (base_dir, peer_uuid)

        fp = open(temp_file, "w")
        process_popen = subprocess.Popen([bin_path, '-r',
                                    raft_uuid, '-u', peer_uuid],  stdout = fp, stderr = fp)
        fp.close()

        output_label = "raft-%s.%s" % (self.process_type, self.process_idx)
        self.process_pid = process_popen.pid
    
        #To check if process is started
        
        self.Wait_for_process_status("running", self.process_pid)



        #Check if child process exited with error
        if process_popen.poll() is None:
            logging.info("Raft process started successfully")
        else:
            logging.info("Raft process failed to start")
            raise subprocess.SubprocessError(self.process_popen.returncode)

        # Wait till the raft-server output gets written to the temp file
        while(1):
            fsize = os.path.getsize(temp_file)
            if fsize != 0:
                break

        with open(temp_file, "r") as fp:
            Lines = fp.readlines()

        #Print <process_type.peer_index> at the start of raft log messages
        for line in Lines:
            logging.warning("<{}>:{}".format(output_label, line.strip()))

        # Delete the temp file
        shutil.os.remove(temp_file)

    '''
        Method: pause_process
        Purpose: pause the process by sending sigstop
        Parameters:
    '''
    def pause_process(self, pid):
        self.process_pid = pid
        process_obj = psutil.Process(pid)
        logging.info("pause the process by sending sigstop")
        try:
            process_obj.send_signal(signal.SIGSTOP)
        except subprocess.SubprocessError as e:
            logging.error("Failed to send Stop signal with error: %s" % os.stderror(e.errno))
            return -1

        '''
        To check if process is paused
        '''
        self.Wait_for_process_status("stopped", pid)
        return 0

    '''
        Method: resume_process
        Purpose: resume the process by sending sigcont
        Parameters:
    '''
    def resume_process(self, pid):
        self.process_pid = pid
        process_obj = psutil.Process(pid)
        logging.info("resume the process by sending sigcont")
        try:
            process_obj.send_signal(signal.SIGCONT)
        except subprocess.SubprocessError as e:
            logging.error("Failed to send CONT signal with error: %s" % os.stderror(e.errno))
            return -1

        return 0

    '''
        Method: kill_process
        Purpose: kill the process by sending sigterm
        Parameters:
    '''
    def kill_process(self, pid):
        self.process_pid = pid
        process_obj = psutil.Process(pid)
        logging.info("kill the process by sending sigterm")
        try:
            process_obj.send_signal(signal.SIGTERM)
        except subprocess.SubprocessError as e:
            logging.error("Failed to send kill signal with error: %s" % os.stderror(e.errno))
            return -1
        return 0
