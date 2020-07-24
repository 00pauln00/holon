import dpath.util
import json
from ctlrequest import *
import logging
from datetime import datetime

'''
recipe_verify is the class for verifying recipe stages generically.
@key1 : Compare the value of the key with expected value.
@key2 : Compare the value of primary key with value of secondary key.
@expected_value : Value of primary key should be compared against expected_value.
@data_type : data_type of the value of key. e.g integer, string, time.
@operator : comparison operator to apply.
'''

ops = {
       '==': lambda x,y: x == y,
       '>=': lambda x,y: x >= y,
       '<=': lambda x,y: x <= y,
       '<': lambda x,y: x < y,
       '>': lambda x,y: x > y,
       '!=': lambda x,y: x != y
      }

def ctlreq_json_to_dict(ctlreqobj):
    if ctlreqobj == None:
        return None

    dct = []
    for obj in ctlreqobj:
        with open(obj.output_fpath, 'r') as string:
            dct.append(json.load(string))
        string.close()

    return dct

def convert_to_data_type(value, data_type):
    conv_value = value

    if data_type == "int":
        conv_value = int(value)
    elif data_type == "bool":
        conv_value = bool(value)

    if data_type == "time":
        time_string = value.split()
        time = time_string[3]
        conv_value = datetime.strptime(time, "%H:%M:%S")
    
    return conv_value


def compare_values(key_value_tuple, operator):
    val1 = key_value_tuple[1]
    val2 = key_value_tuple[3]
    rc = 0 
    if not ops[operator](val1, val2):
        logging.error("key1:val1 : (%s:%s), key2:val2: (%s:%s), operator: %s failed" % (key_value_tuple[0], val1, key_value_tuple[2], val2, operator))
        rc = 1
    else:
        logging.warning("key1:val1 : (%s:%s), key2:val2: (%s:%s), operator: %s passed!" % (key_value_tuple[0], val1, key_value_tuple[2], val2, operator))

    return rc


def rule_table_key_to_value(dictionary, rule_key, data_type):
    if dictionary == None or rule_key == "null":
        return None

    key_value = dpath.util.values(dictionary, rule_key)
    conv_value = convert_to_data_type(key_value[0], data_type)
    return conv_value

def verify_rule_table(recipe_stage_rule_table):
    logging.warning("Calling verify_rule_table")

    ctlreqobj = recipe_stage_rule_table['ctlreqobj']
    curr_dict = ctlreq_json_to_dict(ctlreqobj)

    orig_ctlreqobj = recipe_stage_rule_table['orig_ctlreqobj']
    orig_dict = ctlreq_json_to_dict(orig_ctlreqobj)

    '''
    Iterate the rule table and compare the values aginst the JSON file
    '''
    for k, v in recipe_stage_rule_table.items():
        logging.warning("Verifying rule: %s", k)
        key1_val = key2_val = expected_val = None
        if type(v) is dict:

            if orig_dict == None:
                # All the comparisons are done on ctlreqobj(s)
                for dct in curr_dict:
                    '''
                    If key1 and key2 both are present, comparison would be
                    done against them.
                    '''

                    key1_val = rule_table_key_to_value(dct, v['key1'], v['data_type'])
                    key2_val = rule_table_key_to_value(dct, v['key2'], v['data_type'])

                    if key2_val != None:
                        key_value_tuple = (v['key1'], key1_val, v['key2'], key2_val)
                        rc = compare_values(key_value_tuple, v['operator'])
                    else:
                        expected_val = v['expected_value']
                        expected_val = convert_to_data_type(expected_val, v['data_type'])
                        key_value_tuple = (v['key1'], key1_val, None, expected_val)
                        rc = compare_values(key_value_tuple, v['operator'])

                    if rc == 1:
                        return 1
            else:
                '''
                when original and current ctlreq list are passed, key1 from 
                one file is compared with key1 from another file.
                '''

                for odct in orig_dict:
                    for cdct in curr_dict:
                        orig_key_val = rule_table_key_to_value(odct, v['key1'], v['data_type'])
                        curr_key_val = rule_table_key_to_value(cdct, v['key1'], v['data_type'])

                        key_value_tuple = (v['key1'], orig_key_val, v['key1'], curr_key_val)
                        rc = compare_values(key_value_tuple, v['operator'])
                        
                        if rc == 1:
                            return 1
       
    return 0

def get_raft_json_key_value(ctlreqobj, key):
    with open(ctlreqobj.output_fpath, 'r') as json_file:
        dic = json.load(json_file)

    value = dpath.util.values(dic, key)
    return value[0]
