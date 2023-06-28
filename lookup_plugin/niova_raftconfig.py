from ansible.plugins.lookup import LookupBase
import json
import os, time

import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *

def niova_server_conf_create(cluster_params):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    npeers = int(cluster_params['npeers'])
    port = int(cluster_params['srv_port'])
    client_port = int(cluster_params['client_port'])
    file_counter = int(cluster_params['file_counter'])

    # Log file would be created inside the base directory only
    log_path = "%s/%s/%s.log" % (base_dir, raft_uuid, raft_uuid)

    '''
    Prepare the raft directory path to create raft config and
    server configs.
    '''
    raft_dir = "%s/%s" % (base_dir, raft_uuid)

    genericcmdobj = GenericCmds()
    raftconfobj = RaftConfig(raft_dir, raft_uuid, genericcmdobj)
    logging.basicConfig(filename=log_path, filemode='w', level=logging.DEBUG, format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s')

    raftconfobj.generate_raft_conf(genericcmdobj, npeers, "127.0.0.1",
                                       port, client_port, file_counter)

    json_string = json.dumps(raftconfobj.__dict__)
    raft_conf_dict = json.loads(json_string)
    recipe_conf = { "raft_config" : raft_conf_dict }

    genericcmdobj.recipe_json_dump(recipe_conf) 
    return raftconfobj.__dict__

def niova_client_conf_create(cluster_params):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    npeers = int(cluster_params['npeers'])
    nclients = int(cluster_params['nclients'])
    raft_dir = "%s/%s" % (base_dir, raft_uuid)

    # Start using client_port for clients after server's client_port range.
    start_client_port = int(cluster_params['client_port']) + npeers

    # Load the recipe JSON file
    json_path = "%s/%s/%s.json" % (base_dir, raft_uuid, raft_uuid)
    recipe_conf = {}
    if os.path.exists(json_path):
        with open(json_path, "r+", encoding="utf-8") as json_file:
            recipe_conf = json.load(json_file)

    genericcmdobj = GenericCmds()
    raftconfobj = RaftConfig(raft_dir, raft_uuid, genericcmdobj)

    recipe_conf['client_uuid_array'] = []
    for cli in range(nclients):
        # Create client UUID.
        client_uuid = genericcmdobj.generate_uuid()
        client_port = start_client_port + cli
        raftconfobj.generate_client_conf(genericcmdobj, client_uuid, "127.0.0.1", client_port)
        # Add the entry of this new client uuid into the client_uuid_array
        recipe_conf['client_uuid_array'].append(client_uuid)

    genericcmdobj.recipe_json_dump(recipe_conf)
    return recipe_conf['client_uuid_array']

def controlplane_gossipNodes_create(cluster_params, peer_uuids, entriesInFile):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    port = int(cluster_params['srv_port'])
    raft_dir = "%s/%s" % (base_dir, raft_uuid)
    genericcmdobj = GenericCmds()
    raftconfobj = RaftConfig(raft_dir, raft_uuid, genericcmdobj)
    raftconfobj.generate_controlplane_gossipNodes(cluster_params, "127.0.0.1", port, peer_uuids, entriesInFile)
    return 0

def niovakv_conf_create(cluster_params):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    port = int(cluster_params['srv_port'])
    npeers = cluster_params['npeers']
    raft_dir = "%s/%s" % (base_dir, raft_uuid)
    
    genericcmdobj = GenericCmds()
    raftconfobj = RaftConfig(raft_dir, raft_uuid, genericcmdobj)
    file_counter = 1

    raftconfobj.generate_niovakv_conf(npeers, file_counter, "127.0.0.1", port)
    return 0

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        cluster_params = kwargs['variables']['ClusterParams']
        config_type = terms[0]
    
        if config_type == "server":
            '''
            Create server and raft config files
            '''
            raftconfobj_dict = niova_server_conf_create(cluster_params)

        elif config_type == "niovakv":
            '''
            Create niovakv config file
            '''
            raftconfobj_dict = niovakv_conf_create(cluster_params)

        elif config_type == "controlplane" or config_type == "standalone":
            '''
            Create controlPlane config file
            '''

            peer_uuids = kwargs['variables']['ClusterInfo']['peer_uuid_dict']

            #Create gossipNodes file using peer-uuids
            raftconfobj_dict = controlplane_gossipNodes_create(cluster_params, peer_uuids, terms[1])

            return 0
        
        else:
            '''
            Create client config files
            '''
            raftconfobj_dict = niova_client_conf_create(cluster_params)
            
        return raftconfobj_dict
