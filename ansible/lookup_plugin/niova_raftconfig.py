from ansible.plugins.lookup import LookupBase
import json
import os, time

import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *

def niova_raft_conf_create(cluster_params):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']

    npeers = int(cluster_params['npeers'])
    port = int(cluster_params['srv_port'])
    client_port = int(cluster_params['client_port'])

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
                                       port, client_port)

    json_string = json.dumps(raftconfobj.__dict__)
    raft_conf_dict = json.loads(json_string)
    recipe_conf = { "raft_config" : raft_conf_dict }

    genericcmdobj.recipe_json_dump(recipe_conf) 
    return raftconfobj.__dict__

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        cluster_params = kwargs['variables']['ClusterParams']

        '''
        Create server and raft config files
        '''
        raftconfobj_dict = niova_raft_conf_create(cluster_params)

        return raftconfobj_dict
