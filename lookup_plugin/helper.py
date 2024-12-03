import json
import os  
import shutil
import random
from ansible.plugins.lookup import LookupBase

DBI_DIR = "dbi-dbo"
GEN_NUM = 1
MARKER_VDEV = 0
MARKER_CHUNK = 1
MARKER_TYPE = 4

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
    print(f"Copying {file_list} to {destination_path}")
    # If a single file is passed, wrap it in a list
    if isinstance(file_list, str):
        file_list = [file_list]
    os.makedirs(destination_path, exist_ok=True)

    for file_name in file_list:

        if not os.path.isdir(file_name):
            # cleaning if any additional quotes are present
            src = file_name.strip("'")
            shutil.copy2(src, destination_path)

def get_dir_path(cluster_params, dir_name, seed=None):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    base_directory = os.path.join(base_dir, raft_uuid, dir_name, seed) if seed else os.path.join(base_dir, raft_uuid, dir_name)

    # Get a list of all directories under the specified path
    directories = [entry for entry in os.listdir(base_directory) if os.path.isdir(os.path.join(base_directory, entry))]

    if directories:
        # Sort directories based on creation time (most recent first)
        directories.sort(key=lambda d: os.path.getctime(os.path.join(base_directory, d)), reverse=True)
        # Return the path of the most recently created directory with a trailing slash
        return os.path.join(base_directory, directories[0], '')
    return None

def list_files_from_dir(dir_path):
    return [os.path.abspath(os.path.join(dir_path, file)) for file in os.listdir(dir_path)]   

def get_marker_by_type(vdev, chunk, mList, mType):
    for line in (mList.splitlines()):
        parts = line.split(".")
        if vdev in parts[MARKER_VDEV] and chunk in parts[MARKER_CHUNK] and mType in parts[MARKER_TYPE]:
            return parts[2]
    return None   

def inc_dbi_gen_num(cluster_params, chunk):
    dbi_Path = get_dir_path(cluster_params, DBI_DIR)
    dummy_config = get_dummy_gen_config_path(dbi_Path, chunk)
    dummy_json_data = load_parameters_from_json(dummy_config)
    dbi_input_path = str(dummy_json_data['DbiPath'])
    files_list = list_files_from_dir(dbi_input_path)    # List files from dbipath
    
    if files_list:
        random_file = random.choice(files_list)  # Select a random file from the list
        filename_parts = random_file.split(".")
        genration_num = filename_parts[GEN_NUM]  # Extract the generation number
        # Increment the extracted element by 1, Decrement as the number is inversed
        inc_gen_num = str(hex(int(genration_num, 16) - 1)[2:])
        filename_parts[GEN_NUM] = inc_gen_num  # Update the filename with the incremented element
        new_filename = ".".join(filename_parts)
        source_file_path = os.path.join(dbi_input_path, random_file)
        new_file_path = os.path.join(dbi_input_path, new_filename)
        return source_file_path, new_file_path
    else:
        print("No files found in the directory.")

def get_last_file_from_dir(dir_path):
    file_list = list_files_from_dir(dir_path) # Get a list of files in the source directory
    if len(file_list) > 1:
        # Sort the file list by modification time (oldest to newest)
        file_list.sort(key=lambda x: os.path.getmtime(os.path.join(dir_path, x)))
        # Remove directories from list
        file_list = [f for f in file_list if not os.path.isdir(os.path.join(dir_path, f))]
        return file_list[-1]  # return the last file in the sorted list
    return None

def corrupt_last_file(cluster_params, chunk):
    dbi_path = get_dir_path(cluster_params, DBI_DIR)
    dummy_config = load_parameters_from_json(get_dummy_gen_config_path(dbi_path, chunk))
    dbi_input_path = str(dummy_config['DbiPath'])
    dbi_list = list_files_from_dir(dbi_input_path)
    copy_files(dbi_list, f"{cluster_params['base_dir']}/{cluster_params['raft_uuid']}/orig-dbi")
    orig_file_path = get_last_file_from_dir(f"{cluster_params['base_dir']}/{cluster_params['raft_uuid']}/orig-dbi")
    corrupt_file_path = get_last_file_from_dir(dbi_input_path)
    if not corrupt_file_path:
        print("No files found in the directory.")
        return None
    with open(corrupt_file_path, "rb") as f:
        data = bytearray(f.read())
    if len(data) < 16: # Ensure the file is at least 16 bytes long
        print("File is too small to modify the first 16 bytes")
        return None
    new_entry = bytearray(16)  # Create a new 16-byte entry with Type set to 1 and the rest set to zero
    new_entry[0] = 0x01  # Set Type to 1
    data[:16] = new_entry # Copy the new entry to the first 16 bytes of the data
    with open(corrupt_file_path, "wb") as f: # Write the modified data back to the original file
        f.write(data)

    return [corrupt_file_path, orig_file_path]

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        operation = terms[0]
        cluster_params = kwargs['variables']['ClusterParams']
        
        if operation == "clone_dbi_set":
            chunk = terms[1]
            clone_dbi_files(cluster_params, chunk)
            
        elif operation == "corrupt_last_file":
            chunk = terms[1]
            return corrupt_last_file(cluster_params, chunk)

        elif operation == "inc_dbi_gen_num":
            chunk = terms[1]
            return inc_dbi_gen_num(cluster_params, chunk)

        elif operation == "copy_file":
            source_file = terms[1]
            dest_file = terms[2]
            copy_files(source_file, dest_file)
    
        else:
            raise ValueError(f"Unsupported operation: {operation}")
