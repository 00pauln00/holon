from ansible.plugins.lookup import LookupBase
import json
import os, time

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


def niova_ctlreq_cmd_create(raft_conf, ctlreq_dict):
    wait_for_ofile = True
    cmd = ctlreq_dict['cmd']
    recipe_name = ctlreq_dict['recipe_name']
    peer_idx = ctlreq_dict['peer_id']
    stage = ctlreq_dict['stage']
    peerno = "peer%s" % peer_idx
    input_base = inotify_input_base.REGULAR

    # Get the peer_uuid from the raft json dictionary
    peer_uuid = raft_conf['raft_config']['peer_uuid_dict'][str(peer_idx)]
    base_dir =  raft_conf['raft_config']['base_dir_path']

    genericcmdobj = GenericCmds()
    app_uuid = genericcmdobj.generate_uuid()
        
    inotifyobj = InotifyPath(base_dir, True)

    # For idle_on cmd , input_base would be PRIVATE_INIT.
    if cmd == "idle_on":
        input_base = inotify_input_base.PRIVATE_INIT

    if 'wait_for_ofile' in ctlreq_dict:
        wait_for_ofile = ctlreq_dict['wait_for_ofile']
    # Prepare the ctlreq object
    if wait_for_ofile == False:
        ctlreqobj = CtlRequest(inotifyobj, cmd, peer_uuid, app_uuid,
                        input_base).Apply()
    else:
        ctlreqobj = CtlRequest(inotifyobj, cmd, peer_uuid, app_uuid,
                        input_base).Apply_and_Wait(wait_for_ofile)

    ctlreq_dict_list = []
    ctlreq_dict_list.append(ctlreqobj.__dict__)

    # Add the ctlreq to the raft json directionary
    if not recipe_name in raft_conf:
        raft_conf[recipe_name] = {}
    if not peerno in raft_conf[recipe_name]:
        raft_conf[recipe_name][peerno] = {}
    if not stage in raft_conf[recipe_name][peerno]:
        raft_conf[recipe_name][peerno][stage] = ctlreq_dict_list
    else:
        ctl_list = raft_conf[recipe_name][peerno][stage]
        raft_conf[recipe_name][peerno][stage] = ctl_list + ctlreq_dict_list

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

'''
Load the output json file and lookup raft_keys
from the list and return the list of raft values.
'''
def niova_raft_return_values(ctlreq_dict, raft_key_list):

    raft_values = []
    out_fpath = ctlreq_dict['output_fpath']

    # Read the output file and lookup for the raft key value
    with open(out_fpath, 'r') as json_file:
        raft_dict = json.load(json_file)

    for key in raft_key_list:
        value = dpath.util.values(raft_dict, key)
        if value[0] == "":
            value[0] = "null"
        raft_values.append(str(value[0]))

    return raft_values

'''
Lookup the raft keys in 'recipe:peerid:stage:index' tuple if the ctlreq
for it is already present.
Otherwise fire ctlreq cmd for this tuple and then get the raft keys
for it.
'''
def niova_raft_lookup_create(raft_conf, ctlreq_dict, raft_key_list):

    print(raft_key_list)
    recipe_name = ctlreq_dict['recipe_name']
    peerno = "peer%s" % ctlreq_dict['peer_id']
    stage = ctlreq_dict['stage']

    '''
    If the index inside stage array is give, use it.
    Otherwise use zeroth index.
    '''
    index = 0
    if "index" in ctlreq_dict:
        index = int(ctlreq_dict['index'])

    '''
    If the ctlreq_cmd entry for 'recipe-name:peerid:stage:index' tuple already
    present, simply lookup raft_key(s) in the raft json output file
    '''
    if raft_conf.get(recipe_name, {}).get(peerno, {}).get(stage[index]):
        ctlreq_dict = raft_conf[recipe_name][peerno][stage][index]
        raft_values = niova_raft_return_values(ctlreq_dict, raft_key_list)
    else:
        '''
        But if ctlreq_cmd entry for 'recipe-name:peerid:stage:index' tuple is
        not present that means command was never executed before.
        Execute the ctlreq cmd and then get value for the raft key(s)
        '''
        new_ctlreq_dict = niova_ctlreq_cmd_create(raft_conf, ctlreq_dict)
        raft_values = niova_raft_return_values(new_ctlreq_dict, raft_key_list)

    '''
    TODO: There was issue in adding sleep from ansible after ctlreq_Cmd.
    So for now added the option in the lookup plugin to sleep.
    We should figure out how to do it from ansible playbook itself.
    '''
    if "sleep_after" in ctlreq_dict:
        stime = int(ctlreq_dict['sleep_after'])
        time.sleep(stime)

    print(raft_values)
    return raft_values

def niova_raft_query(ctlreq_dict, raft_key):

    out_fpath = ctlreq_dict['output_fpath']

    # Read the output file and lookup for the raft key value
    with open(out_fpath, 'r') as json_file:
        raft_dict = json.load(json_file)

    value = dpath.util.values(raft_dict, raft_key)

    return value

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
            ctlreq_cmd_dict = terms[2]
            niova_obj_dict = niova_ctlreq_cmd_create(raft_conf, ctlreq_cmd_dict)
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
        elif operation == "lookup_create":
            ctlreq_cmd_dict = terms[2]
            raft_key_list = terms[3]
            niova_obj_dict = niova_raft_lookup_create(raft_conf, ctlreq_cmd_dict, raft_key_list)
        elif operation == "query":
            ctlreq_cmd_dict = terms[2]
            raft_key = terms[3]
            niova_obj_dict = niova_raft_query(ctlreq_cmd_dict, raft_key)
        else:
            print("Invalide option passed: %s" % operation)
            sys.exit()

        return niova_obj_dict
