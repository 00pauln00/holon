import os
import signal
class RaftProcess:

    process_type = ''
    process = {}
    
    '''
        Constructor:
        Purpose: Initialisation
    '''
    def __init__(self, process_type, process):
        self.process_type = process_type
        self.process = process
    
    '''
        Method: pause_process
        Purpose: pause the process by sending sigstop
        Parameters:
    '''
    def pause_process(self):
        print(f"pause the process by sending sigstop")
        self.process.send_signal(signal.SIGSTOP)
    '''
        Method: resume_process
        Purpose: resume the process by sending sigcont
        Parameters:
    '''
    def resume_process(self):
        print(f"resume the process by sending sigcont")
        self.process.send_signal(signal.SIGCONT)
    '''
        Method: kill_process
        Purpose: kill the process by sending sigterm
        Parameters:
    '''
    def kill_process(self):
        print(f"kill the process by sending sigterm")
        self.process.send_signal(signal.SIGTERM)
