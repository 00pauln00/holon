import os
import subprocess
from basicio import BasicIO

class RaftConfig:

    server_config_path = ''
    raft_uuid = ''
    peer_uuid_arr = [] # Peer UUID array
    client_uuid_arr = [] # Client UUID array
    nservers = 0

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
        print(f"exporting NIOVA_LOCAL_CTL_SVC_DIR=", CTL_SVC_DIR)


    '''
        Method: generate_raft_conf
        Purpose: Create Raft-Conf file for RAFT UUID and PEER UUID
        Parameter: @nservers: Number of servers in the cluster.
                    @ip_address: IP address for the server.
                    @port: Start port number in the range.
                    @client_pport: Start client port in the range.
                    @raft_db_path: Directory path to store the raftdb files
                    for all servers.
                
    '''
    def generate_raft_conf(self, nservers, ip_address, port, client_port, raft_db_path):

        basicioobj = BasicIO()
        # Generate RAFT UUID and store it in raftconf object
        p = subprocess.Popen(["uuid"], stdout=subprocess.PIPE)
        (stdout, err) = p.communicate()
        raft_uuid_bytes=stdout.strip()
        raft_uuid = raft_uuid_bytes.decode('utf-8')
        self.raft_uuid = raft_uuid
        
        # Write RAFT UUID to raft-conf file
        raft_conf_path = "%s/%s.raft" % (self.server_config_path, self.raft_uuid)
        print(f"Raft config file path: %s" % raft_conf_path)
        # open file:
        raft_fd = basicioobj.open_file(raft_conf_path)
        # write to the file.
        basicioobj.write_file(raft_fd, "RAFT %s\n" % (self.raft_uuid))

        self.nservers = nservers

        # Generate PEER UUID and Write it into raft-conf file
        for i in range(nservers):
            p1 = subprocess.Popen(["uuid"], stdout=subprocess.PIPE)
            (stdout, err) = p1.communicate()
            peer_uuid_bytes=stdout.strip()
            peer_uuid = peer_uuid_bytes.decode('utf-8')
            
            basicioobj.write_file(raft_fd, "PEER %s\n" % peer_uuid)

            #Prepare peer-conf file.
            peer_config_path = "%s/%s.peer" % (self.server_config_path, peer_uuid)
            print(f"Generating config file for peer at %s " % peer_config_path)
            store_path = "%s/%s.raftdb" % (raft_db_path, peer_uuid)
            conf_buff = "RAFT         %s\nIPADDR       %s\nPORT         %s\nCLIENT_PORT  %s\nSTORE        %s\n" % (self.raft_uuid, ip_address, port, client_port, store_path)

            #open the server config file
            conf_fd = basicioobj.open_file(peer_config_path)
            # Write the config buffer into the file.
            basicioobj.write_file(conf_fd, conf_buff)
            # CLose the file
            basicioobj.close_file(conf_fd)

            port += 1
            client_port +=1

            #Append peer uuid into an array
            self.peer_uuid_arr.append(peer_uuid)

        # Close the raft conf file.
        basicioobj.close_file(raft_fd)

    '''
        Method: get_peer_uuid_for_peerno
        Purpose: Get the peer uuid for the peerno from peer_uuid_array
    '''
    def get_peer_uuid_for_peerno(self, peerno):
        return self.peer_uuid_arr[peerno]


            
    '''
        Method: generate_client_conf
        Purpose: Create client-conf file for Client UUID
        Parameters: @ip_address: IP address for the client.
                    @client_port: Client port number.
    '''
    def generate_client_conf(self, ip_address, client_port):
        
        basicioobj = BasicIO()
        #Generate Client UUID
        p2 = subprocess.Popen(["uuid"], stdout=subprocess.PIPE)
        (stdout, err) = p2.communicate()
        client_uuid_bytes = stdout.strip()
        client_uuid = client_uuid_bytes.decode('utf-8')

        # Append the client uuid into an array
        self.client_uuid_arr.append(client_uuid)
        
        #Prepare Client config file
        client_conf_path = "%s/%s.raft_client" % (self.server_config_path, client_uuid)
        print(client_conf_path)
        cl_fd = basicioobj.open_file(client_conf_path)
        client_buff = "RAFT              %s\nIPADDR            %s\nCLIENT_PORT       %s\n" % (self.raft_uuid, ip_address, client_port)
        # Write the config file
        basicioobj.write_file(cl_fd, client_buff)
        # close the file
        basicioobj.close_file(cl_fd)

    '''
        Method: get_client_uuid_for_clientno
        Purpose: Get the client uuid for the client number from client_uuid_array
    '''
    def get_client_uuid_for_clientno(self, clientno):
        return self.client_uuid_arr[clientno]
