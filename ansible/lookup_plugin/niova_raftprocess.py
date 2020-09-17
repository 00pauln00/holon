from ansible.plugins.lookup import LookupBase
import json
import os, time

import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *
from inotifypath import *
from raftprocess import RaftProcess

def niova_raft_process_ops(recipe_conf, peer_idx, operation):

    raft_uuid = recipe_conf['raft_config']['raft_uuid']
    peer_uuid = recipe_conf['raft_config']['peer_uuid_dict'][str(peer_idx)]
    base_dir =  recipe_conf['raft_config']['base_dir_path']
    log_path = recipe_conf['raft_config']['log_path']

    if operation != "start":
        pid = int(recipe_conf['raft_process'][str(peer_idx)]['process_pid'])

    process_type ="server"
    binary_path='/home/pauln/raft-builds/latest/'
    log_path = recipe_conf['raft_config']['log_path']
    serverproc = RaftProcess(peer_uuid, peer_idx, process_type, log_path)
    logging.basicConfig(filename=log_path, filemode='a', level=logging.DEBUG, format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s')

    if operation == "start":

        ctlsvc_path = "%s/configs" % base_dir
        logging.info("base dir: %s" % base_dir)
        logging.info("ctlsvc_path: %s" % ctlsvc_path)

        inotifyobj = InotifyPath(base_dir, True, log_path)
        inotifyobj.export_ctlsvc_path(ctlsvc_path)
        serverproc.start_process(raft_uuid, peer_uuid)

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
        proc_operation = terms[0]
        peer_id = terms[1]

        recipe_conf = {}
        raft_json_fpath = "%s/%s/%s.json" % (recipe_params['base_dir'], recipe_params['raft_uuid'], recipe_params['raft_uuid'])
        if os.path.exists(raft_json_fpath):
            with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
                recipe_conf = json.load(json_file)

        niova_obj_dict = niova_raft_process_ops(recipe_conf, peer_id, proc_operation)
        if len(terms) == 3:
            logging.info("sleep after the operation")
            sleep_time = int(terms[2])
            time.sleep(sleep_time)
