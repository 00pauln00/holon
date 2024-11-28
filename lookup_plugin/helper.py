import json
import os  

def load_parameters_from_json(filename):
    with open(filename, 'r') as json_file:
        params = json.load(json_file)
    return params

def create_file(file_name: str, content: str):
    with open(file_name, 'w') as file:
        file.write(content)

def delete_file(file_name: str):
    if os.path.exists(file_name):
        os.remove(file_name)

def load_recipe_op_config(cluster_params):
    recipe_conf = {}
    raft_json_fpath = "%s/%s/%s.json" % (cluster_params['base_dir'],
                                         cluster_params['raft_uuid'],
                                         cluster_params['raft_uuid'])
    if os.path.exists(raft_json_fpath):
        with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
            recipe_conf = json.load(json_file)

    return recipe_conf

def create_dir(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, mode=0o777)