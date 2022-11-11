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
    def __init__(self, base_dir_path, raft_uuid, genericcmdobj):
        self.raft_uuid = raft_uuid
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
    def generate_raft_conf(self, genericcmdobj, nservers, ip_address, port, client_port, file_counter):

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
        
        self.file_counter = 0

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
    def generate_client_conf(self, genericcmdobj, client_uuid, ip_address, client_port):
        
        basicioobj = BasicIO()

        '''
        Prepare client config information and right it to client config file.
        client config file name format would be <CLIENT_UUID>.raft_client.
        '''
        client_conf_path = "%s/%s.raft_client" % (self.server_config_path, client_uuid)
        cl_fd = basicioobj.open_file(client_conf_path)
        #client_buff = "RAFT              %s\nIPADDR            %s\nCLIENT_PORT       %s\n" % (self.raft_uuid, ip_address, client_port)
        client_buff = "RAFT              %s\nIPADDR            %s\n" % (self.raft_uuid, ip_address)
        # Write the config file
        basicioobj.write_file(cl_fd, client_buff)
        # close the file
        basicioobj.close_file(cl_fd)
        # Store the client UUID
        self.client_uuid_arr.append(client_uuid)



    '''
        Method: generate_niovakv_conf
        Purpose: Create niovakv config for niovakv
        Parameters: @nclients: no of clients
                    @file_counter: file counter
                    @ip_address: IP address for the client.
                    @port: port number.
    '''
    def generate_niovakv_conf(self, nclients, file_counter, ip_address, port):

        basicioobj = BasicIO()

        '''
        Prepare niovakv config information and right it to niovakv config file.
        niovakv config file name format would be niovakv.config.
        '''
        niovakv_conf_path = "%s/niovakv.config" % (self.base_dir_path)
        nk_fd = basicioobj.open_file(niovakv_conf_path)
        port += 30
        for i in range(nclients):
            niovakv_buff = "Node%d %s %d %d %d\n" % (file_counter, ip_address, port, port+1, port+2)
            # Write the config file
            basicioobj.write_file(nk_fd, niovakv_buff)
            file_counter += 1
            port += 3
        
        # close the file
        basicioobj.close_file(nk_fd)

    '''
        Method: generate_controlplane_gossipNodes
        Purpose: Create controlplane gossipNodes for controlplane
        Parameters: .
    '''
    def generate_controlplane_gossipNodes(self, cluster_params, ip_address, port, peeruuids):

        basicioobj = BasicIO()

        '''
        Prepare gossipNodes information and write it to gossipNodes file.
        Checks if prometheus_support is set and writes prometheus port info
        to targets.json file.
        gossipNodes file name format would be gossipNodes.
        '''
        gossip_path = self.base_dir_path + '/' + "gossipNodes"
        gossip_fd = basicioobj.open_file(gossip_path)

        if int(cluster_params['prometheus_support']) == 0:
            for peer in peeruuids.values():
                gossip_data = "%s " % ip_address
                basicioobj.write_file(gossip_fd, gossip_data)
            startRange = port
            endRange = int(port) + 1000
            Totalrange = str(startRange) + " " + str(endRange)
            basicioobj.write_file(gossip_fd, '\n' + Totalrange)
        else:
            prom_targets_path = os.environ['PROMETHEUS_PATH'] + '/' + "targets.json"
            prom_targets_fd = basicioobj.open_file(prom_targets_path)
            target_data = []
            for peer in peeruuids.values():
                gossip_data = "%s %s %d %d %d\n" % ( peer, ip_address, port, port+1, port+2 )
                basicioobj.write_file(gossip_fd, gossip_data)
                target_data.append({
                    "targets":[ "localhost:" + str(port + 2) ],
                    })
                port=port+3

            # Write targets to targets.json
            basicioobj.write_file(prom_targets_fd, json.dumps(target_data))
            basicioobj.close_file(prom_targets_fd)
        # close the file
        basicioobj.close_file(gossip_fd)

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

