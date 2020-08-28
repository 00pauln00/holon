from ansible.plugins.lookup import LookupBase
import json
import os

import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *
from inotifypath import *
from raftprocess import RaftProcess
from ctlrequest import *
from recipe_verify import *

def niova_write_to_recipe_json(raft_conf):
    raft_json_fpath = "%s/%s.json" % (raft_conf['raft_config']['base_dir_path'], raft_conf['raft_config']['raft_uuid'])

    with open(raft_json_fpath, "w+", encoding="utf-8") as json_file:
        json.dump(raft_conf, json_file, indent = 4)


def niova_ctlreq_cmd_create(raft_conf, peer_idx, ctlreq_dict):
    cmd = ctlreq_dict['cmd']
    wait_for_ofile = ctlreq_dict['wait_for_ofile']
    recipe_name = ctlreq_dict['recipe_name']
    stage = ctlreq_dict['stage']
    src = ctlreq_dict['src']

    # Get the peer_uuid from the raft json dictionary
    peer_uuid = raft_conf['raft_config']['peer_uuid_dict'][str(peer_idx)]
    base_dir =  raft_conf['raft_config']['base_dir_path']

    genericcmdobj = GenericCmds()
    app_uuid = genericcmdobj.generate_uuid()
        
    inotifyobj = InotifyPath(base_dir, True)

    # Prepare the ctlreq object
    if cmd == "idle_on":
        ctlreqobj = CtlRequest(inotifyobj, cmd, peer_uuid, app_uuid,
                        inotify_input_base.PRIVATE_INIT).Apply()
    else:
        ctlreqobj = CtlRequest(inotifyobj, cmd, peer_uuid, app_uuid,
                        inotify_input_base.REGULAR).Apply_and_Wait(wait_for_ofile)

    ctlreq_dict_list = []
    ctlreq_dict_list.append(ctlreqobj.__dict__)

    # Add the ctlreq to the raft json directionary
    if not recipe_name in raft_conf:
        raft_conf[recipe_name] = {}
    if not stage in raft_conf[recipe_name]:
        raft_conf[recipe_name][stage] = {}
    if not src in raft_conf[recipe_name][stage]:
        raft_conf[recipe_name][stage][src] = ctlreq_dict_list
    else:
        ctl_list = raft_conf[recipe_name][stage][src]
        raft_conf[recipe_name][stage][src] = ctl_list + ctlreq_dict_list

    niova_write_to_recipe_json(raft_conf)
    return ctlreqobj.__dict__

def niova_raft_conf_create(recipe_params, conf_params):
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

    raftconfobj = RaftConfig(raft_dir, raft_uuid, genericcmdobj)
    raftconfobj.generate_raft_conf(genericcmdobj, npeers, "127.0.0.1",
                                       port, client_port)

    json_string = json.dumps(raftconfobj.__dict__)
    raft_conf_dict = json.loads(json_string)
    raft_conf_dict = { "raft_config" : raft_conf_dict }

    niova_write_to_recipe_json(raft_conf_dict)
    return raftconfobj.__dict__

def niova_raft_process_ops(raft_conf, peer_idx, operation):

    raft_uuid = raft_conf['raft_config']['raft_uuid']
    peer_uuid = raft_conf['raft_config']['peer_uuid_dict'][str(peer_idx)]
    base_dir =  raft_conf['raft_config']['base_dir_path']

    process_type ="server"
    binary_path='/home/pauln/raft-builds/latest/'

    serverproc = RaftProcess(peer_uuid, peer_idx, process_type)
    if operation == "start":
        ctlsvc_path = "%s/configs" % base_dir
        inotifyobj = InotifyPath(base_dir, True)
        inotifyobj.export_ctlsvc_path(ctlsvc_path)
        #Creating raftprocess object
        #Staring the server
        serverproc.start_process(raft_uuid, peer_uuid)

        #Converting the process object into dictionary
    elif operation == "pause":
        pid = int(raft_conf['raft_process'][str(peer_idx)]['process_pid'])
        serverproc.pause_process(pid)
    elif operation == "resume":
        pid = int(raft_conf['raft_process'][str(peer_idx)]['process_pid'])
        serverproc.resume_process(pid)
    elif operation == "kill":
        pid = int(raft_conf['raft_process'][str(peer_idx)]['process_pid'])
        serverproc.kill_process(pid)

    json_string = json.dumps(serverproc.__dict__)
    raft_proc_dict = json.loads(json_string)

    if not "raft_process" in raft_conf:
        raft_conf['raft_process'] = {}

    raft_conf['raft_process'][str(peer_idx)] = {}
    raft_conf['raft_process'][str(peer_idx)] = raft_proc_dict

    niova_write_to_recipe_json(raft_conf)
    return serverproc.__dict__

def ctlreq_rule_table_compare(rule_table, orig_ctlreq, ctlreq):
    rule_table['ctlreq_dict'] = ctlreq
    rule_table['orig_ctlreq_dict'] = orig_ctlreq
    recipe_failed = verify_rule_table(rule_table)
    if recipe_failed:
        logging.error("Basic control interface recipe Failed")
        return recipe_failed

    return recipe_failed

def niova_raft_recipe_verify(raft_conf, compare_sources, rule_table):
    src1 = compare_sources['src1']
    src1_split = src1.split('/')
    recipe_name = src1_split[0]
    src1_stage_name = src1_split[1]
    src1_tag = src1_split[2]

    src2 = None
    if 'src2' in compare_sources:
        src2 = compare_sources['src2']
        src2_split = src1.split('/')
        src2_stage_name = src2_split[1]
        src2_tag = src2_split[2]
        
    if src2 == None:
        src1_array_size = len(raft_conf[recipe_name][src1_stage_name]['src1'])

        if src1_array_size == 1:
            ctlreq_dict = raft_conf[recipe_name][src1_stage_name]['src1'][0]
            orig_ctlreq_dict = None
            rc = ctlreq_rule_table_compare(rule_table, orig_ctlreq_dict, ctlreq_dict)
            if rc:
                result = {}
                result[recipe_name] = rc
                return result

        for i in range(src1_array_size - 1):
            orig_ctlreq_dict = raft_conf[recipe_name][src1_stage_name]['src1'][i]
            ctlreq_dict = raft_conf[recipe_name][src1_stage_name]['src1'][i+1]

            rc = ctlreq_rule_table_compare(rule_table, orig_ctlreq_dict, ctlreq_dict)
            if rc:
                break
    else:
        orig_ctlreq_dict = raft_conf[recipe_name][src1_stage_name]['src1'][0]
        ctlreq_dict = raft_conf[recipe_name][src2_stage_name]['src2'][0]
        rc = ctlreq_rule_table_compare(rule_table, orig_ctlreq_dict, ctlreq_dict)

    result = {}
    result[recipe_name] = rc

    return result

def niova_raft_lookup_key(raft_conf, peer_idx, ctlreq_dict):

    recipe_name = ctlreq_dict['recipe_name']
    stage = ctlreq_dict['stage']
    src = ctlreq_dict['src']
    index = len(raft_conf[recipe_name][stage][src]) - 1
    raft_key = ctlreq_dict['raft_key']

    output_fpath = raft_conf[recipe_name][stage][src][index]['output_fpath']

    # Read the output file and lookup for the raft key value
    with open(output_fpath, 'r') as json_file:
        raft_dict = json.load(json_file)

    value = dpath.util.values(raft_dict, raft_key)

    result = {}
    result['raft_key'] = value[0]

    return result

def niova_raft_query(ctlreq_dict, raft_key):

    out_fpath = ctlreq_dict['output_fpath']

    print(out_fpath)
    # Read the output file and lookup for the raft key value
    with open(out_fpath, 'r') as json_file:
        raft_dict = json.load(json_file)

    
    value = dpath.util.values(raft_dict, raft_key)

    print(value)
    result = {}
    result['raft_key'] = value[0]

    return result

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        operation = terms[0]
        recipe_params = terms[1]

        raft_json_fpath = "%s/%s/%s.json" % (recipe_params['base_dir'], recipe_params['raft_uuid'], recipe_params['raft_uuid'])

        raft_conf = {}
        if os.path.exists(raft_json_fpath):
            with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
                raft_conf = json.load(json_file)

        if operation == "ctlrequest":
            peer_idx = terms[2]
            ctlreq_cmd_dict = terms[3]
            niova_obj_dict = niova_ctlreq_cmd_create(raft_conf, peer_idx, ctlreq_cmd_dict)
        elif operation == "raftconfigure":
            config_params_dict = terms[2]
            niova_obj_dict = niova_raft_conf_create(recipe_params, config_params_dict)
        elif operation == "raftprocess":
            peer_idx = terms[2]
            proc_operation = terms[3]
            niova_obj_dict = niova_raft_process_ops(raft_conf, peer_idx, proc_operation)
        elif operation == "recipe_verify":
            compare_src = terms[2]
            rule_table = terms[3]
            niova_obj_dict = niova_raft_recipe_verify(raft_conf, compare_src, rule_table)
        elif operation == "lookup_from_json":
            peer_idx = terms[2]
            ctlreq_cmd_dict = terms[3]
            niova_obj_dict = niova_raft_lookup_key(raft_conf, peer_idx, ctlreq_cmd_dict)
        elif operation == "query":
            ctlreq_cmd_dict = terms[2]
            raft_key = terms[3]
            niova_obj_dict = niova_raft_query(ctlreq_cmd_dict, raft_key)

        return niova_obj_dict

