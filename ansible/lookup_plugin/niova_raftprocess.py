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

def niova_raft_process_get_proc_type(uuid, raft_config):
	'''
	Find out the uuid type by iterating over the raft config
	'''
	proc_type = "server"
	logging.warning("Find the type of uuid: %s" % uuid)
	try:
		peer_idx = list(raft_config['peer_uuid_dict'].keys())[list(raft_config['peer_uuid_dict'].values()).index(uuid)]
	except:
		proc_type = "client"

	return proc_type
	
class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        recipe_params = kwargs['variables']['raft_param']
        raft_config = kwargs['variables']['raft_conf']
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

        proc_type = niova_raft_process_get_proc_type(uuid, raft_config)

        # Perform the operation on the peer.
        niova_obj_dict = niova_raft_process_ops(recipe_conf, cluster_type, uuid, proc_operation, proc_type)
        if len(terms) == 3:
            logging.info("sleep after the operation")
            sleep_info = terms[2]
            sleep_nsec = int(sleep_info['sleep_after_cmd'])
            time.sleep(sleep_nsec)
