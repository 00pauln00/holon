import json
import os  
import shutil
import random
from ansible.plugins.lookup import LookupBase

DBI_DIR = "dbi-dbo"
GEN_NUM = 1
Marker_vdev = 0
Marker_chunk = 1
Marker_type = 4

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

def clone_dbi_files(cluster_params, chunk):
    dir_path = get_dir_path(cluster_params, DBI_DIR)
    destination_dir = "dbiSetFiles"
    dbi_list_path = os.path.join(dir_path, "dbisetFname.txt")
    file_list = read_file_list(dbi_list_path)
    
    create_dir(os.path.join(dir_path, destination_dir))
    copy_files(file_list, os.path.join(dir_path, destination_dir))

# generates the dummy generator config path
def get_dummy_gen_config_path(data_dir, chunk):
    return os.path.join(data_dir, str(chunk), "DV", "dummy_generator.json")

def read_file_list(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read().rstrip(', ').split(', ')
    except FileNotFoundError:
        print(f"The file '{file_path}' was not found.")
        return []

def copy_files(file_list, destination_path):
    # If a single file is passed, wrap it in a list
    if isinstance(file_list, str):
        file_list = [file_list]

    for file_name in file_list:
        shutil.copy2(file_name, destination_path)

def get_dir_path(cluster_params, dirName, seed=None):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    baseDir = os.path.join(base_dir, raft_uuid)

    if seed is not None:
        dbi_dir = os.path.join(baseDir, dirName, seed)
    else:
        dbi_dir = os.path.join(baseDir, dirName)

    # Get a list of all entries (files and directories) under the 'dbi-dbo' directory
    entries = os.listdir(dbi_dir)

    # Filter out directories only
    directories = [entry for entry in entries if os.path.isdir(os.path.join(dbi_dir, entry))]

    if directories:
        # Sort directories based on creation time (most recent first)
        directories.sort(key=lambda d: os.path.getctime(os.path.join(dbi_dir, d)), reverse=True)
        # Return the path of the most recently created directory with a trailing slash
        most_recent_directory = directories[0]
        if len(directories) > 1:
            most_recent_directory = directories[1]
        directory_path = os.path.join(dbi_dir, most_recent_directory, '')  # Add the trailing slash here
        return directory_path
    else:
        return None

def list_files_from_dir(dir_path):
    return os.listdir(dir_path)    

def check_if_mType_present(vdev, chunk, mList, mType):
    for line in (mList.splitlines()):
        parts = line.split(".")
        if vdev in parts[Marker_vdev] and chunk in parts[Marker_chunk] and mType in parts[Marker_type]:
            return parts[2]
    return None   

def copy_DBI_file_generatorNum(cluster_params, dirName, chunk):
    jsonPath = get_dir_path(cluster_params, dirName)
    jsonfile = get_dummy_gen_config_path(jsonPath, chunk)
    json_data = load_parameters_from_json(jsonfile)
    dbi_input_path = str(json_data['DbiPath'])
    # List files from dbipath
    files_list = list_files_from_dir(dbi_input_path)
    
    if files_list:
        # Select a random file from the list
        random_file = random.choice(files_list)
        filename_parts = random_file.split(".")
        # Extract the generation number
        genration_num = filename_parts[GEN_NUM]
        # Increment the extracted element by 1
        # Decrement as the number is inversed
        new_genration_num = str(int(genration_num, 16) - 1)
        # Update the filename with the incremented element
        filename_parts[GEN_NUM] = new_genration_num
        new_filename = ".".join(filename_parts)
        source_file_path = os.path.join(dbi_input_path, random_file)
        new_file_path = os.path.join(dbi_input_path, new_filename)
        print(f"Copying {source_file_path} to {new_file_path}") 
        # Copy the file and rename the copy
        copy_files(source_file_path, new_file_path)
    else:
        print("No files found in the directory.")
     


class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        operation = terms[0]
        cluster_params = kwargs['variables']['ClusterParams']
        
        if operation == "clone_dbi_set":
            chunk = terms[1]
            clone_dbi_files(cluster_params, chunk)
        if operation == "copy_DBI_file_generatorNum":
            chunk = terms[1]
            copy_DBI_file_generatorNum(cluster_params, DBI_DIR, chunk)
    
        else:
            raise ValueError(f"Unsupported operation: {operation}")
