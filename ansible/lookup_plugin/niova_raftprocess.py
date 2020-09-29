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
	@peer_idx: Peer index.
	@process_type: server or client.
	@operation: operation to perform on the peer.
'''
def niova_raft_process_ops(recipe_conf, cluster_type, peer_idx, process_type, operation):

    raft_uuid = recipe_conf['raft_config']['raft_uuid']
    peer_uuid = recipe_conf['raft_config']['peer_uuid_dict'][str(peer_idx)]
    base_dir =  recipe_conf['raft_config']['base_dir_path']

    if operation != "start":
        pid = int(recipe_conf['raft_process'][str(peer_idx)]['process_pid'])

    serverproc = RaftProcess(cluster_type, peer_uuid, peer_idx, process_type)

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

    recipe_conf['raft_process'][str(peer_idx)] = {}
    recipe_conf['raft_process'][str(peer_idx)] = raft_proc_dict

    genericcmdobj = GenericCmds()
    genericcmdobj.recipe_json_dump(recipe_conf) 
    return serverproc.__dict__

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        recipe_params = kwargs['variables']['raft_param']
        cluster_type = recipe_params['ctype']
        proc_operation = terms[0]
        proc_type = terms[1]
        peer_id = terms[2]

        # Initialize the logger
        log_path = "%s/%s/%s.log" % (recipe_params['base_dir'], recipe_params['raft_uuid'], recipe_params['raft_uuid'])

        logging.basicConfig(filename=log_path, filemode='a', level=logging.DEBUG, format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s')


        recipe_conf = {}
        raft_json_fpath = "%s/%s/%s.json" % (recipe_params['base_dir'], recipe_params['raft_uuid'], recipe_params['raft_uuid'])
        if os.path.exists(raft_json_fpath):
            with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
                recipe_conf = json.load(json_file)

        # Perform the operation on the peer.
        niova_obj_dict = niova_raft_process_ops(recipe_conf, cluster_type, peer_id, proc_type, proc_operation)
        if len(terms) == 4:
            logging.info("sleep after the operation")
            sleep_info = terms[3]
            sleep_nsec = int(sleep_info['sleep_after_cmd'])
            time.sleep(sleep_nsec)
