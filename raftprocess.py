import signal
import subprocess
from raftconfig import RaftConfig
class RaftProcess:

    process_type = ''
    process_uuid = ''
    process = {}
    binary_path='/home/pauln/raft-builds/latest/'


    '''
        Constructor:
        Purpose: Initialisation
        Parameter:  @uuid: UUID of server or client for which process object is
                            created.
                    @process_type: Type of the process(server or client)
    '''
    def __init__(self, uuid, process_type):
        self.process_uuid = uuid
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
            self.process = subprocess.Popen([server_bin_path, '-r',
                                raftconfobj.raft_uuid, '-u', self.process_uuid])
        else:
            client_bin_path = "%s/raft-client" % (self.binary_path)
            self.process = subprocess.Popen([client_bin_path, '-r',
                                raftconfobj.raft_uuid, '-u', self.process_uuid])


    '''
        Method: pause_process
        Purpose: pause the process by sending sigstop
        Parameters:
    '''
    def pause_process(self):
        print("pause the process by sending sigstop")
        self.process.send_signal(signal.SIGSTOP)

    '''
        Method: resume_process
        Purpose: resume the process by sending sigcont
        Parameters:
    '''
    def resume_process(self):
        print("resume the process by sending sigcont")
        self.process.send_signal(signal.SIGCONT)

    '''
        Method: kill_process
        Purpose: kill the process by sending sigterm
        Parameters:
    '''
    def kill_process(self):
        print("kill the process by sending sigterm")
        self.process.send_signal(signal.SIGTERM)
