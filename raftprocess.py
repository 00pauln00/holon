import signal, subprocess, logging, psutil
import time as time_global
from raftconfig import RaftConfig
from func_timeout import func_timeout, FunctionTimedOut

def check_for_process_status(pid, process_status):
    '''
    To check process status
    '''
    ps = psutil.Process(pid)
    while(1):
        if ps.status() == process_status:
            logging.info(" process status %s (expected %s)"% (ps.status(), process_status))
            break
        time_global.sleep(0.005)

class RaftProcess:

    process_type = ''
    process_uuid = ''
    process_status = ''
    process_popen = {}
    process_idx = 0
    binary_path='/home/pauln/raft-builds/latest/'


    '''
        Constructor:
        Purpose: Initialisation
        Parameter:  @uuid: UUID of server or client for which process object is
                            created.
                    @process_type: Type of the process(server or client)
    '''
    def __init__(self, uuid, process_idx, process_type):
        self.process_uuid = uuid
        self.process_idx = process_idx
        self.process_type = process_type

    '''
        Method: start_process
        Purpose: Start the process of type process_type
        Parameters: @raftconfobj: RaftConf object.
                    @uuid: UUID of the server or client.
    '''

    def Wait_for_process_status(self, process_status):
        '''
        To wait for change in process status.
        Timeout is added to wait for change in process status till the specified time.
        '''
        rc = 0
        try:
            func_timeout(20, check_for_process_status, args=(self.process_popen.pid, process_status))
        except FunctionTimedOut:
                logging.error("Error : timeout occur to change process status to %s" % process_status)
                rc = 1

        if rc == 1:
            exit()

    def start_process(self, raftconfobj, clusterobj):
        logging.warning("Starting process of type: %s with UUID: %s" % (self.process_type,
                                self.process_uuid))

        if self.process_type == 'server':
            server_bin_path = "%s/raft-server" % (self.binary_path)
            with open(clusterobj.log_file_path, "a") as file:
                self.process_popen = subprocess.Popen([server_bin_path, '-r',
                                raftconfobj.raft_uuid, '-u', self.process_uuid], stdout = file, stderr = file)
                file.close()
        else:
            client_bin_path = "%s/raft-client" % (self.binary_path)
            self.process_popen = subprocess.Popen([client_bin_path, '-r',
                                raftconfobj.raft_uuid, '-u', self.process_uuid])

        # Check if child process exited with error
        if self.process_popen.poll() is None:
            logging.warning("Raft process started successfully")
        else:
            logging.error("Raft process failed to start")
            raise subprocess.SubprocessError(self.process_popen.returncode)

        '''
        To check if process is started
        '''
        self.Wait_for_process_status("running")

    '''
        Method: pause_process
        Purpose: pause the process by sending sigstop
        Parameters:
    '''
    def pause_process(self):
        logging.warning("pause the process by sending sigstop")
        try:
            self.process_popen.send_signal(signal.SIGSTOP)
        except subprocess.SubprocessError as e:
            logging.error("Failed to send Stop signal with error: %s" % os.stderror(e.errno))
            return -1

        '''
        To check if process is paused
        '''
        self.Wait_for_process_status("stopped")
        return 0

    '''
        Method: resume_process
        Purpose: resume the process by sending sigcont
        Parameters:
    '''
    def resume_process(self):
        logging.warning("resume the process by sending sigcont")
        try:
            self.process_popen.send_signal(signal.SIGCONT)
        except subprocess.SubprocessError as e:
            logging.error("Failed to send CONT signal with error: %s" % os.stderror(e.errno))
            return -1

        return 0

    '''
        Method: kill_process
        Purpose: kill the process by sending sigterm
        Parameters:
    '''
    def kill_process(self):
        logging.warning("kill the process by sending sigterm")
        try:
            self.process_popen.send_signal(signal.SIGTERM)
        except subprocess.SubprocessError as e:
            logging.error("Failed to send kill signal with error: %s" % os.stderror(e.errno))
            return -1
        return 0
