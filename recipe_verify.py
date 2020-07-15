import dpath.util
import json
from ctlrequest import *
import logging

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

def verify_rule_table(recipe_stage_rule_table):
    logging.warning("Calling verify_rule_table")

    ctlreqobj = recipe_stage_rule_table['ctlreqobj']
    with open(ctlreqobj.output_fpath, 'r') as string:
        raft_dct = json.load(string)
    string.close()

    logging.debug("Opening the JSON file: %s" % ctlreqobj.output_fpath)

    '''
    Iterate the rule table and compare the values aginst the JSON file
    '''
    for k, v in recipe_stage_rule_table.items():
        logging.warning("Verifying rule: %s", k)
        if type(v) is dict:
            fs = dpath.util.values(raft_dct, v['key1'])
            if v['key2'] != "null":
                # TODO key2 handling is yet to be done.
                fs1 = dpath.util.values(raft_dct, v['key2'])

            if v['expected_value'] != "null":
                curr_val = fs[0]
                expected_val = v['expected_value']

                if v['data_type'] == "int":
                    curr_val = int(curr_val)
                    expected_val = int(expected_val)
                elif v['data_type'] == "bool":
                    curr_val = bool(curr_val)
                    expected_val = bool(expected_val)
                
                if not ops[v['operator']](curr_val, expected_val):
                    logging.error("key1: (%s:%s) not matched expected_value: %s" % (v['key1'], curr_val, expected_val))
                    return 1
                else:
                    logging.info("key1 (%s:%s) matched with expected value: %s" % (v['key1'], curr_val, expected_val))

    return 0
