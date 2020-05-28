import signal, subprocess
from raftconfig import RaftConfig
class RaftProcess:

    process_type = ''
    process_uuid = ''
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
    def start_process(self, raftconfobj):
        print(f"Starting process of type: %s with UUID: %s" % (self.process_type,
                                self.process_uuid))

        if self.process_type == 'server':
            server_bin_path = "%s/raft-server" % (self.binary_path)
            self.process_popen = subprocess.Popen([server_bin_path, '-r',
                                raftconfobj.raft_uuid, '-u', self.process_uuid])
        else:
            client_bin_path = "%s/raft-client" % (self.binary_path)
            self.process_popen = subprocess.Popen([client_bin_path, '-r',
                                raftconfobj.raft_uuid, '-u', self.process_uuid])

        # Check if child process exited with error
        if self.process_popen.poll() is None:
            print(f"Raft process started successfully")
        else:
            print(f"Error: Raft process failed to start")
            raise subprocess.SubprocessError(self.process_popen.returncode)

    '''
        Method: pause_process
        Purpose: pause the process by sending sigstop
        Parameters:
    '''
    def pause_process(self):
        print("pause the process by sending sigstop")
        try:
            self.process_popen.send_signal(signal.SIGSTOP)
        except subprocess.SubprocessError as e:
            print(f"Failed to send Stop signal with error: %s" % os.stderror(e.errno))
            sys.exit()


    '''
        Method: resume_process
        Purpose: resume the process by sending sigcont
        Parameters:
    '''
    def resume_process(self):
        print("resume the process by sending sigcont")
        try:
            self.process_popen.send_signal(signal.SIGCONT)
        except subprocess.SubprocessError as e:
            print(f"Failed to send CONT signal with error: %s" % os.stderror(e.errno))
            sys.exit()

    '''
        Method: kill_process
        Purpose: kill the process by sending sigterm
        Parameters:
    '''
    def kill_process(self):
        print("kill the process by sending sigterm")
        try:
            self.process_popen.send_signal(signal.SIGTERM)
        except subprocess.SubprocessError as e:
            print(f"Failed to send kill signal with error: %s" % os.stderror(e.errno))
            sys.exit()
