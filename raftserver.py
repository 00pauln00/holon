# -*- coding: utf-8 -*-
"""
Created on Wed May 13 12:59:31 2020

@author: Admin
"""
import os
import subprocess
from raft_uuid import RaftUUID
from raftconfig import RaftConfig
class RaftServer:

    peer_uuid = ''
    ip_address = ''
    port = ''
    client_port = ''
    raft_db_path = ''
    process_obj = {}

    '''
        Method: generate_peer_uuid
        Purpose: generate UUID usinf /usr/bin/uuid
        Parameters:
    '''
    def generate_peer_uuid(self):
        p = subprocess.Popen(["/usr/bin/uuid"], stdout=subprocess.PIPE)
        (stdout, err) = p.communicate()
        peer_uuid_bytes=stdout.strip()
        peer_uuid= peer_uuid_bytes.decode('utf-8')
        #print(peer_uuid)
        self.peer_uuid = peer_uuid
        return self.peer_uuid

    '''
        Method: assign_peer_params
        Purpose: assign peer parameters
        Parameters:
    '''
    def assign_peer_params(self, ip_address, port, client_port, raft_db_path):
        self.ip_address = ip_address
        #print(self.ip_address)
        self.port = port
        #print(self.port)
        self.client_port = client_port
        #print(self.client_port)
        self.raft_db_path = raft_db_path
        #print(self.raft_db_path)

    '''
        Method: write_peer_uuid_to_raft_conf
        Purpose: write peer uuid to raft conf
        Parameters:
    '''
    def write_peer_uuid_to_raft_conf(self, raft_conf, raft_uuid):
        #print(f"write peer uuid to raft conf: {raft_conf}")
        raft_conf_path = "%s/%s.raft" % (raft_conf.server_config_path, raft_uuid.raft_uuid)
        with open(raft_conf_path, 'a',encoding = 'utf-8') as f2:
                f2.write("PEER %s\n"%(self.peer_uuid))


    '''
        Method: prepare_peer_conf
        Purpose: prepare peer config inside the ctl dir
        Parameters:
    '''
    def prepare_peer_conf(self, raft_conf,raft_uuid):
        print(f"prepare peer config inside the ctl dir")
        peer_config_path="%s/%s.peer"%(raft_conf.server_config_path,self.peer_uuid)
        #print(peer_config_path)
        store_path="/home/vkapare/tmp/%s.raftdb"%(self.peer_uuid)
        with open(peer_config_path, 'w',encoding = 'utf-8') as f2:
                 f2.write("RAFT      %s\n"%(raft_uuid.raft_uuid))
                 f2.write("IPADDR   %s\n"%(self.ip_address))
                 f2.write("PORT      %s\n"%(self.port))
                 f2.write("CLIENT_PORT   %s\n"%(self.client_port))
                 f2.write("STORE      %s\n"%(store_path))
                 
    '''
        Method: start_server
        Purpose: start server
        Parameters:
    '''
    def start_server(self, raft_uuid):
        print(f"start server")
        server_obj = subprocess.Popen(['/home/pauln/raft-builds/latest/raft-server', '-r', raft_uuid.raft_uuid, '-u', self.peer_uuid])
        self.process_obj = server_obj
