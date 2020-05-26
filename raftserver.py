# -*- coding: utf-8 -*-
"""
Created on Wed May 13 12:59:31 2020

@author:
"""

import subprocess
from raftconfig import RaftConfig

class RaftServer:
    peer_uuid = ''
    peer_index = 0
    ip_address = ''
    port = ''
    client_port = ''
    raft_db_path = ''

    '''
    Constructor:
    Purpose: Initialisation
    Parameters: @raftconfobj:RaftConf object to get the raft_uuid.
                @peer_index: Peer index.
    '''
    def __init__(self, raftconfobj, peer_index):
        self.peer_index = peer_index
        print(f"Peer index is: %d" % peer_index)
        print(f"Length of the array: %d" % len(raftconfobj.peer_uuid_arr))
        self.peer_uuid = raftconfobj.peer_uuid_arr[peer_index]

    '''
    Method: get peer uuid.
    Purpose: Get the peer UUID for this object
    Parameters:
    '''
    def get_peer_uuid(self):
        return self.peer_uuid
