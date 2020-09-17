import os, logging, json
import subprocess
from basicio import BasicIO
from genericcmd import GenericCmds
from pathlib import Path

class RaftConfig:

    base_dir_path = ''
    server_config_path = ''
    raft_uuid = ''
    peer_uuid_dict = {} # Peer UUID dictionary
    client_uuid_arr = [] # Client UUID array
    nservers = 0

    '''
        Constructor:
        Purpose: Initialisation
    '''
    def __init__(self, base_dir_path, raft_uuid, genericcmdobj, log_path):
        self.raft_uuid = raft_uuid
        self.log_path = log_path
        logging.basicConfig(filename=log_path, filemode='w', level=logging.DEBUG, format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s')
        '''
        All the configs will  be inside test_root/raft_uuid/configs
        '''
        raft_conf_path = "%s/configs" % base_dir_path
        genericcmdobj.make_dir(raft_conf_path)

        self.base_dir_path = base_dir_path
        self.server_config_path = raft_conf_path

    '''
        Method: export_path
        Purpose: export ctl svc dir
        Parameters:
    '''
    def export_path(self):
        CTL_SVC_DIR = os.environ['NIOVA_LOCAL_CTL_SVC_DIR'] = self.server_config_path
        logging.warning("exporting NIOVA_LOCAL_CTL_SVC_DIR=%s", self.server_config_path)


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
    def generate_raft_conf(self, genericcmdobj, nservers, ip_address, port, client_port):

        basicioobj = BasicIO()
        genericcmdobj = GenericCmds()

        '''
        Generate RAFT_UUID directory inside server_conf_path to make sure
        conf files for this instance gets created inside unique directory.
        '''

        # export the server config path
        self.export_path()

        '''
        Prepare raft config file. Its format would be:
        //
        RAFT <RAFT_UUID>
        PEER <PEER0_UUID>
        PEER <PEER1_UUID>
        .
        .
        //
        Raft config file name format would be <RAFT_UUID>.raft
        '''
        raft_conf_path = "%s/%s.raft" % (self.server_config_path, self.raft_uuid)
        logging.warning("Raft config file path: %s" % raft_conf_path)
        # open file:
        raft_fd = basicioobj.open_file(raft_conf_path)
        # write to the file.
        basicioobj.write_file(raft_fd, "RAFT %s\n" % (self.raft_uuid))

        self.nservers = nservers

        '''
        Create directory to store raftdb files.
        The path would be test_root/raft_uuid/raftdb
        '''
        raft_db_path = "%s/raftdb" % self.base_dir_path
        genericcmdobj.make_dir(raft_db_path)

        '''
        Prepare config file each peer in the cluster. Peer config file name
        format would be <PEER_UUID>.peer
        '''
        self.peer_uuid_dict = {}
        for i in range(nservers):
            peer_uuid = genericcmdobj.generate_uuid()
            
            basicioobj.write_file(raft_fd, "PEER %s\n" % peer_uuid)

            peer_config_path = "%s/%s.peer" % (self.server_config_path, peer_uuid)
            logging.warning("Generating config file for peer at %s " % peer_config_path)
            store_path = "%s/%s.raftdb" % (raft_db_path, peer_uuid)
            conf_buff = "RAFT         %s\nIPADDR       %s\nPORT         %s\nCLIENT_PORT  %s\nSTORE        %s\n" % (self.raft_uuid, ip_address, port, client_port, store_path)

            '''
            Write the config information into peer config file.
            '''
            conf_fd = basicioobj.open_file(peer_config_path)
            basicioobj.write_file(conf_fd, conf_buff)
            basicioobj.close_file(conf_fd)

            port += 1
            client_port +=1

            '''
            Maintain peer uuid array for all the peers in the cluster.
            '''
            self.peer_uuid_dict[i] = peer_uuid

        basicioobj.close_file(raft_fd)

        json_string = json.dumps(self.__dict__)
        logging.info(json_string)

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
    def generate_client_conf(self, genericcmdobj, ip_address, client_port):
        
        basicioobj = BasicIO()

        '''
        Generate new UUID for the client.
        '''
        client_uuid = genericcmdobj.generate_uuid()

        '''
        Prepare client config information and right it to client config file.
        client config file name format would be <CLIENT_UUID>.raft_client.
        '''
        client_conf_path = "%s/%s.raft_client" % (self.server_config_path, client_uuid)
        cl_fd = basicioobj.open_file(client_conf_path)
        client_buff = "RAFT              %s\nIPADDR            %s\nCLIENT_PORT       %s\n" % (self.raft_uuid, ip_address, client_port)
        # Write the config file
        basicioobj.write_file(cl_fd, client_buff)
        # close the file
        basicioobj.close_file(cl_fd)
        # Append the client uuid into an array
        self.client_uuid_arr.append(client_uuid)

    '''
        Method: get_client_uuid_for_clientno
        Purpose: Get the client uuid for the client number from client_uuid_array
    '''
    def get_client_uuid_for_clientno(self, clientno):
        return self.client_uuid_arr[clientno]

    '''
        Method: delete_config_file
        Purpose: It will remove the all config files
    '''
    def delete_config_file(self):
        for f in Path(self.server_config_path).glob('*'):
            try:
                f.unlink()
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))

