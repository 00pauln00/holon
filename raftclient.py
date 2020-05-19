import os
import subprocess
from raftconfig import RaftConfig

class RaftClient:

    raft_uuid = ''
    client_uuid = ''
    client_no = 0 # Client number e.g 0/1/2

    '''
    Constructor:
    Purpose: Initialisation
    Parameters: @raft_conf_obj: RaftConfig Object to get raft_uuid.
                @client_no: Client index.
    '''
    def __init__(self, raft_conf_obj, client_no):
        self.raft_uuid = raft_conf_obj.raft_uuid
        self.client_uuid = raft_conf_obj.client_uuid_arr[client_no]
        self.client_no = client_no

    '''
    Method: Get Client UUID
    Purpose: Get the client UUID for this object
    Parameters:
    '''
    def get_client_uuid(self):
        print(f"Client UUID is: %s" % (self.client_uuid))
        return self.client_uuid
