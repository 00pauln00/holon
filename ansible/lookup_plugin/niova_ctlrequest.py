from ansible.plugins.lookup import LookupBase
import json
import os, time
import dpath.util
import subprocess
from genericcmd import *
from basicio import *
from raftconfig import *
from inotifypath import *
from ctlrequest import *

def niova_write_to_recipe_json(raft_conf):
    raft_json_fpath = "%s/%s.json" % (raft_conf['raft_config']['base_dir_path'], raft_conf['raft_config']['raft_uuid'])

    with open(raft_json_fpath, "w+", encoding="utf-8") as json_file:
        json.dump(raft_conf, json_file, indent = 4)


def niova_ctlreq_cmd_create(recipe_conf, ctlreq_dict):
    wait_for_ofile = True
    cmd = ctlreq_dict['cmd']
    recipe_name = ctlreq_dict['recipe_name']
    peer_idx = ctlreq_dict['peer_id']
    stage = ctlreq_dict['stage']
    peerno = "peer%s" % peer_idx
    input_base = inotify_input_base.REGULAR

    # Get the peer_uuid from the raft json dictionary
    peer_uuid = recipe_conf['raft_config']['peer_uuid_dict'][str(peer_idx)]
    base_dir =  recipe_conf['raft_config']['base_dir_path']

    genericcmdobj = GenericCmds()
    app_uuid = genericcmdobj.generate_uuid()
        
    inotifyobj = InotifyPath(base_dir, True)

    # For idle_on cmd , input_base would be PRIVATE_INIT.
    if cmd == "idle_on":
        input_base = inotify_input_base.PRIVATE_INIT

    if 'wait_for_ofile' in ctlreq_dict:
        wait_for_ofile = ctlreq_dict['wait_for_ofile']

    if cmd == "set_leader_uuid":
       ctlreqobj = CtlRequest(inotifyobj, cmd, peer_uuid, app_uuid,
                    input_base).set_leader(ctlreq_dict['set_leader_uuid'])
    else:
        # Prepare the ctlreq object
        if wait_for_ofile == False:
            ctlreqobj = CtlRequest(inotifyobj, cmd, peer_uuid, app_uuid,
                            input_base).Apply()
        else:
            ctlreqobj = CtlRequest(inotifyobj, cmd, peer_uuid, app_uuid,
                            input_base).Apply_and_Wait(False)

    ctlreq_dict_list = []
    ctlreq_dict_list.append(ctlreqobj.__dict__)

    # Add the ctlreq to the raft json directionary
    if not recipe_name in recipe_conf:
        recipe_conf[recipe_name] = {}
    if not peerno in recipe_conf[recipe_name]:
        recipe_conf[recipe_name][peerno] = {}
    if not stage in recipe_conf[recipe_name][peerno]:
        recipe_conf[recipe_name][peerno][stage] = ctlreq_dict_list
    else:
        ctl_list = recipe_conf[recipe_name][peerno][stage]
        recipe_conf[recipe_name][peerno][stage] = ctl_list + ctlreq_dict_list

    genericcmdobj.recipe_json_dump(recipe_conf)
    return ctlreqobj.__dict__

def niova_raft_lookup_values(ctlreq_dict, raft_key_list):

    raft_values_dict = {}
    out_fpath = ctlreq_dict['output_fpath']

    # Read the output file and lookup for the raft key value
    with open(out_fpath, 'r') as json_file:
        raft_dict = json.load(json_file)

    '''
    Lookup each key from the raft_key_list.
    The output would be stored in another dictionary with key as
    last two keys from the complete key path.
    '''
    for key in raft_key_list:
        print(key)
        value = dpath.util.values(raft_dict, key)
        if value[0] == "":
            value[0] = "null"
        output_key = "/%s/%s" % (os.path.basename(os.path.dirname(key)), os.path.basename(key))
        raft_values_dict[output_key] = value[0]

    return raft_values_dict

def niova_raft_lookup_ctlreq(recipe_conf, ctlreq_cmd_dict, raft_keys):

    ctlreq_obj_dict = niova_ctlreq_cmd_create(recipe_conf, ctlreq_cmd_dict)
    raft_values = niova_raft_lookup_values(ctlreq_obj_dict, raft_keys)

    print(raft_values)
    return raft_values

def niova_set_leader(recipe_conf, ctlreq_dict):

    ctlreq_obj_dict = niova_ctlreq_cmd_create(recipe_conf, ctlreq_dict)
    return ctlreq_obj_dict

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        '''
        Get the playbook variables
        '''
        ctlreq_cmd_dict = {}
        recipe_params = kwargs['variables']['raft_param']
        ctlreq_cmd_dict['recipe_name'] = kwargs['variables']['recipe_name']
        ctlreq_cmd_dict['stage'] = kwargs['variables']['stage']

        operation = terms[0]
        ctlreq_cmd_dict['cmd'] = terms[1]
        ctlreq_cmd_dict['peer_id'] = terms[2]

        raft_json_fpath = "%s/%s/%s.json" % (recipe_params['base_dir'], recipe_params['raft_uuid'], recipe_params['raft_uuid'])

        recipe_conf = {}
        if os.path.exists(raft_json_fpath):
            with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
                recipe_conf = json.load(json_file)

        if operation == "create_cmd":
            ctlreq_cmd_dict['wait_for_ofile'] = terms[3]
            result = niova_ctlreq_cmd_create(recipe_conf, ctlreq_cmd_dict)
        elif operation == "set_leader":
            ctlreq_cmd_dict['set_leader_uuid'] = terms[3]
            result = niova_set_leader(recipe_conf, ctlreq_cmd_dict)
        else:
            raft_key = terms[3]
            '''
            If this lookup is gonna run for number of iterations.
            '''
            iter_info = None
            if len(terms) == 5:
                iter_info = terms[4]

            result = []
            iter_cnt = 1
            sleep_sec = 0
            if iter_info != None:
                iter_cnt = int(iter_info['iter'])
                sleep_sec = int(iter_info['sleep_after_cmd'])

            for i in range(iter_cnt):
                values = niova_raft_lookup_ctlreq(recipe_conf, ctlreq_cmd_dict, raft_key)
                time.sleep(sleep_sec)
                result.append(values)

            '''
            If only one element in present in the result array, return only first element
            rather than returning array of array even for single element.
            '''
            if iter_cnt == 1:
                return result[0]
            else:
                return result

            return result

