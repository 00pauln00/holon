from ansible.plugins.lookup import LookupBase
import json
import os, time

import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *

def niova_raft_conf_create(recipe_params, conf_params, log_path):
    base_dir = recipe_params['base_dir']
    raft_uuid = recipe_params['raft_uuid']

    npeers = int(conf_params['npeers'])
    port = int(conf_params['port'])
    client_port = int(conf_params['client_port'])

    '''
    Prepare the raft directory path to create raft config and
    server configs.
    '''
    raft_dir = "%s/%s" % (base_dir, raft_uuid)

    genericcmdobj = GenericCmds()
    raftconfobj = RaftConfig(raft_dir, raft_uuid, genericcmdobj, log_path)
    raftconfobj.generate_raft_conf(genericcmdobj, npeers, "127.0.0.1",
                                       port, client_port)

    json_string = json.dumps(raftconfobj.__dict__)
    raft_conf_dict = json.loads(json_string)
    recipe_conf = { "raft_config" : raft_conf_dict }

    genericcmdobj.recipe_json_dump(recipe_conf) 
    return raftconfobj.__dict__

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        recipe_params = kwargs['variables']['raft_param']

        config_params_dict = terms[0]
        log_path = terms[1]
        '''
        Create server and raft config files
        '''
        raftconfobj_dict = niova_raft_conf_create(recipe_params, config_params_dict, log_path)

        return raftconfobj_dict
