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
def niova_raft_process_ops(peer_uuid, operation, proc_type, recipe_conf,
                           cluster_params):

    raft_uuid = recipe_conf['raft_config']['raft_uuid']
    base_dir =  recipe_conf['raft_config']['base_dir_path']
    app_type = cluster_params['app_type']
    coalesced_wr = cluster_params['coal_wr']
    node_name = ""

    if operation != "start":
        pid = int(recipe_conf['raft_process'][peer_uuid]['process_pid'])

    serverproc = RaftProcess(cluster_params['ctype'], raft_uuid,
                             peer_uuid, proc_type, app_type)

    if (proc_type == "client" and app_type == "niovakv") or (proc_type == "client" and app_type == "controlplane"):
        '''
         Find out the Node name for the niovakv_server which starts pmdbclient
         Get the clientuuid index and use the index to find the name from node
         config file.
        '''
        client_uuid_array = recipe_conf['client_uuid_array']
        index = client_uuid_array.index(peer_uuid)
       
        if app_type == "niovakv":
            # Read the config file.
            binary_dir = os.getenv('NIOVA_BIN_PATH')
            config_path = "%s/niovakv.config" % binary_dir
            with open(config_path) as f:
                lines = f.read().splitlines()

            node_line = lines[index]
            node_name = node_line.split()[0]

            logging.info("Node Name for starting niovakv_server is: %s", node_name)
            if not "serf_nodes" in recipe_conf:
                recipe_conf['serf_nodes'] = {}

            recipe_conf['serf_nodes'][peer_uuid] = node_name

    if operation == "start":

        ctlsvc_path = "%s/configs" % base_dir
        if cluster_params['app_type'] == "controlplane" and proc_type == "client":
            logging.warning("app_type controlplane and proxy server getting started")
            ctlsvc_path = "%s/cpp_configs_%s" % (base_dir, peer_uuid)
            if not os.path.exists(ctlsvc_path):
                logging.warning("Creating config directory: %s", ctlsvc_path)
                os.makedirs(ctlsvc_path)
        else:
            ctlsvc_path = "%s/configs" % base_dir

        logging.warning("base dir: %s" % base_dir)
        logging.warning("ctlsvc_path: %s" % ctlsvc_path)
        logging.warning("cluster_type: %s" % cluster_params['ctype'])
        logging.warning("coalesced_wr: %s" % cluster_params['coal_wr'])

        inotifyobj = InotifyPath(base_dir, True)
        inotifyobj.export_ctlsvc_path(ctlsvc_path)
        serverproc.start_process(base_dir, node_name, coalesced_wr)

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
        peer_idx = list(raft_config['raft_config']['peer_uuid_dict'].keys())[list(raft_config['raft_config']['peer_uuid_dict'].values()).index(uuid)]
    except:
        proc_type = "client"

    logging.warning("Type of uuid is: %s" % proc_type)
    return proc_type

'''
Every client and server should use unique client port.
Get the total number of severs and already started clients count to
get the next unused client_port.
'''
def niova_get_unused_client_port(cluster_params, client_dict):
    nservers = int(cluster_params['npeers'])
    start_client_port = int(cluster_params['client_port'])
    nclients = len(client_dict)

    new_client_port = start_client_port + nservers + nclients

    return new_client_port

def niova_client_config_create(client_uuid, recipe_conf_dict, cluster_params):

    # If this is the first client config, declare the client_array.
    if not 'client_uuid_array' in recipe_conf_dict:
        recipe_conf_dict['client_uuid_array'] = []
    elif client_uuid in recipe_conf_dict['client_uuid_array']:
        # If client_uuid already has config, don't do anything
        return

    logging.warning("Create client config file for uuid: %s" % client_uuid)
    client_uuid_array = recipe_conf_dict['client_uuid_array']

    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
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
    #new_client_port = niova_get_unused_client_port(cluster_params, client_uuid_array)
    #raftconfobj.generate_client_conf(genericcmdobj, client_uuid, "127.0.0.1", new_client_port)

    # Add the entry of this new client uuid into the client_uuid_array
    recipe_conf_dict['client_uuid_array'].append(client_uuid)


def initialize_logger(cluster_params):
    log_path = "%s/%s/%s.log" % (cluster_params['base_dir'],
                                 cluster_params['raft_uuid'],
                                 cluster_params['raft_uuid'])

    logging.basicConfig(filename=log_path, filemode='a',
                        level=logging.DEBUG,
                        format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s')


def load_recipe_op_config(cluster_params):
    recipe_conf = {}
    raft_json_fpath = "%s/%s/%s.json" % (cluster_params['base_dir'],
                                         cluster_params['raft_uuid'],
                                         cluster_params['raft_uuid'])
    if os.path.exists(raft_json_fpath):
        with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
            recipe_conf = json.load(json_file)

    return recipe_conf

'''
Main function for raftprocess lookup.
'''
class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        cluster_params = kwargs['variables']['ClusterParams']
        
        cluster_type = cluster_params['ctype']
        proc_operation = terms[0]
        uuid = terms[1]

        sleep_after_op = False

        if len(terms) == 3:
            # User asked to sleep after operation completion.
            sleep_after_op = True
            sinfo = terms[2]

        # Initialize the logger
        initialize_logger(cluster_params)

        logging.warning("Peer uuid passed: %s" % uuid)

        # Load the recipe_operation config
        recipe_conf = load_recipe_op_config(cluster_params)

        '''
        Find out the type of the process (server or client) looking at its UUID
        '''
        proc_type = niova_raft_process_get_proc_type(uuid, recipe_conf)

        if proc_type == "client" and proc_operation == "start":

            # Prepare the client config if it's already not created.
            niova_client_config_create(uuid, recipe_conf, cluster_params)

        # Perform the operation on the peer.
        niova_obj_dict = niova_raft_process_ops(uuid, proc_operation,
                                                proc_type, recipe_conf,
                                                cluster_params)
        if sleep_after_op == True:
            logging.info("sleep after the operation")
            sleep_info = sinfo
            sleep_nsec = int(sleep_info['sleep_after_cmd'])
            time.sleep(sleep_nsec)
