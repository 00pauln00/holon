from ansible.plugins.lookup import LookupBase
import json
import os, time

import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *
from inotifypath import *
from raftprocess import RaftProcess

'''
niova_raft_process_ops: This function perform operations like start, stop,pause
on the server/client.
	@recipe_conf: Recipe config parameters.
	@cluster_type: raft or pumicedb
	@peer_uuid: Peer UUID
	@operation: operation to perform on the peer.
	@proc_type: Process type (server/client)
'''
def niova_raft_process_ops(recipe_conf, cluster_type, peer_uuid, operation, proc_type):

    raft_uuid = recipe_conf['raft_config']['raft_uuid']
    base_dir =  recipe_conf['raft_config']['base_dir_path']

    if operation != "start":
        pid = int(recipe_conf['raft_process'][peer_uuid]['process_pid'])

    serverproc = RaftProcess(cluster_type, peer_uuid, proc_type)

    if operation == "start":

        ctlsvc_path = "%s/configs" % base_dir
        logging.info("base dir: %s" % base_dir)
        logging.info("ctlsvc_path: %s" % ctlsvc_path)
        logging.info("cluster_type: %s" % cluster_type)

        inotifyobj = InotifyPath(base_dir, True)
        inotifyobj.export_ctlsvc_path(ctlsvc_path)
        serverproc.start_process(raft_uuid, peer_uuid, base_dir)

    elif operation == "pause":
        serverproc.pause_process(pid)
    elif operation == "resume":
        serverproc.resume_process(pid)
    elif operation == "kill":
        serverproc.kill_process(pid)

    json_string = json.dumps(serverproc.__dict__)
    raft_proc_dict = json.loads(json_string)

    '''
    If this is the first process entry in the recipe_conf dictionary.
    '''
    if not "raft_process" in recipe_conf:
        recipe_conf['raft_process'] = {}

    recipe_conf['raft_process'][peer_uuid] = {}
    recipe_conf['raft_process'][peer_uuid] = raft_proc_dict

    genericcmdobj = GenericCmds()
    genericcmdobj.recipe_json_dump(recipe_conf) 
    return serverproc.__dict__

'''
niova_raft_process_get_proc_type: Return the type of the process
looking at the UUID.
'''
def niova_raft_process_get_proc_type(uuid, raft_config):
    '''
    Find out the uuid type by iterating over the raft config
    '''
    proc_type = "server"
    try:
        peer_idx = list(raft_config['peer_uuid_dict'].keys())[list(raft_config['peer_uuid_dict'].values()).index(uuid)]
    except:
        proc_type = "client"

    logging.warning("Type of uuid is: %s" % proc_type)
    return proc_type

'''
Every client and server should use unique client port.
Get the total number of severs and already started clients count to
get the next unused client_port.
'''
def niova_get_unused_client_port(recipe_params, client_dict):
    nservers = int(recipe_params['npeers'])
    start_client_port = int(recipe_params['client_port'])
    nclients = len(client_dict)

    new_client_port = start_client_port + nservers + nclients

    return new_client_port

def niova_client_config_create(client_uuid, config_params, recipe_params, client_uuid_dict):
    base_dir = recipe_params['base_dir']
    raft_uuid = recipe_params['raft_uuid']
    raft_dir = "%s/%s" % (base_dir, raft_uuid)

    '''
    check if config file for client is already created
	'''
    client_conf_path = "%s/%s.raft_client" % (raft_dir, client_uuid)
    if os.path.exists(client_conf_path) :
        # Client config file already present, do nothing
        return False

    genericcmdobj = GenericCmds()
    raftconfobj = RaftConfig(raft_dir, raft_uuid, genericcmdobj)

    '''
    It's important that client_port should be unique across all servers and
    clients. Get the count of number of servers and already started clients.
    And use the next client port for this new client.
    '''
    new_client_port = niova_get_unused_client_port(recipe_params, client_uuid_dict)
    raftconfobj.generate_client_conf(genericcmdobj, client_uuid, "127.0.0.1", new_client_port)


'''
Main function for raftprocess lookup.
'''
class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        recipe_params = kwargs['variables']['raft_param']
        raft_config = kwargs['variables']['raft_conf']
        client_uuid_array = kwargs['variables']['client_uuid_array']
        cluster_type = recipe_params['ctype']
        proc_operation = terms[0]
        uuid = terms[1]

        # Initialize the logger
        log_path = "%s/%s/%s.log" % (recipe_params['base_dir'], recipe_params['raft_uuid'], recipe_params['raft_uuid'])

        logging.basicConfig(filename=log_path, filemode='a', level=logging.DEBUG, format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s')

        logging.warning("Peer uuid passed: %s" % uuid)

        recipe_conf = {}
        raft_json_fpath = "%s/%s/%s.json" % (recipe_params['base_dir'], recipe_params['raft_uuid'], recipe_params['raft_uuid'])
        if os.path.exists(raft_json_fpath):
            with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
                recipe_conf = json.load(json_file)

        '''
        Find out the type of the process (server or client) looking at its UUID
        '''
        proc_type = niova_raft_process_get_proc_type(uuid, raft_config)

        if proc_type == "client" and proc_operation == "start":
            # Prepare the client config if it's already not created.
            logging.warning("Create client config file for uuid: %s" % uuid)
            niova_client_config_create(uuid, raft_config, recipe_params, client_uuid_array)
            # Add Client uuid into global client_uuid_array
            client_uuid_array.append(uuid)
        # Perform the operation on the peer.
        niova_obj_dict = niova_raft_process_ops(recipe_conf, cluster_type, uuid, proc_operation, proc_type)
        if len(terms) == 3:
            logging.info("sleep after the operation")
            sleep_info = terms[2]
            sleep_nsec = int(sleep_info['sleep_after_cmd'])
            time.sleep(sleep_nsec)
