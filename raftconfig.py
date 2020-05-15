import os

class RaftConfig:

    server_config_path = ''

    '''
        Constructor:
        Purpose: Initialisation
    '''
    def __init__(self, server_config_path):
        self.server_config_path = server_config_path

    '''
        Method: export_path
        Purpose: export ctl svc dir
        Parameters:
    '''
    def export_path(self):
        CTL_SVC_DIR = os.environ['NIOVA_LOCAL_CTL_SVC_DIR'] = self.server_config_path

        print(f"CTL_SVC_DIR:", CTL_SVC_DIR)

