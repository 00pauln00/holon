import os
import subprocess

class RaftClient:

    client_uuid = ''
    raft_uuid = ''
    ip_address = ''
    client_port = ''
    client_proc_obj = {}

    '''
        Method: generate_client_uuid
        Purpose: generate UUID using /usr/bin/uuid
        Parameters:
    '''
    def generate_client_uuid(self):
        p1 = subprocess.Popen(["/usr/bin/uuid"], stdout=subprocess.PIPE)
        (stdout, err) = p1.communicate()
        client_uuid_bytes = stdout.strip()
        client_uuid = client_uuid_bytes.decode('utf-8')
        self.client_uuid = client_uuid

    '''
        Method: assign_client_params
        Purpose: assign client parameters
        Parameters:
    '''
    def assign_client_params(self, raft_uuid_obj, ip_address, client_port):
        self.raft_uuid = raft_uuid_obj.raft_uuid
        self.ip_address = ip_address
        self.client_port = client_port

    '''
        Method: prepare_client_conf
        Purpose: prepare the client config file
        Parameters:
    '''
    def prepare_client_conf(self, server_config_obj):
        client_conf_path = "%s/%s.raft_client" % (server_config_obj.server_config_path, self.client_uuid)
        print(client_conf_path)
        f1 = open(client_conf_path, "w+")
        f1.write("RAFT              %s\n" % (self.raft_uuid))
        f1.write("IPADDR            %s\n" % (self.ip_address))
        f1.write("CLIENT_PORT       %s\n" % (self.client_port))
        f1.close()
    '''
        Method: start_client
        Purpose: write raft uuid to client conf
        Parameters:
    '''
    def start_client(self, raft_uuid):
        print(f"start client")
        client_proc_obj = subprocess.Popen(['/home/pauln/raft-builds/latest/raft-client', '-r', raft_uuid.raft_uuid, '-u', self.client_uuid])
        self.client_proc_obj = client_proc_obj

