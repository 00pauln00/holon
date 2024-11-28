from ansible.plugins.lookup import LookupBase
import json
from multiprocessing import Pool
import os, random
from lookup_plugin.s3_handler import get_dir_path
import subprocess

def generate_random_values(cluster_params, dir_name, input_values):
    json_path = get_dir_path(cluster_params, dir_name)

    if json_path != None:
        new_path = json_path + "/" + input_values['chunk'] + "/DV"
        json_data = load_json_contents(new_path + "/dummy_generator.json")
        input_values['chunk'] = str(json_data['TotalChunkSize'])
        input_values["seqStart"] = str(json_data['SeqEnd'] + 1)
        input_values["vdev"] = str(json_data['Vdev'])
        dbicount = str(json_data['TMinDbiFileForForceGC'])
    else:
        input_values["seqStart"] = "0"
        dbicount = "0"

    if input_values['chunk'] == "-1":
        # Generate a random chunkNumber
        input_values['chunk'] = str(random.randint(1, 200))

    if 'maxPunches' not in input_values:
        input_values['maxPunches'] = str(random.randint(1, 50))
    if 'maxVblks' not in input_values:
        input_values['maxVblks'] = str(random.randint(100, 1000))
    if 'punchAmount' not in input_values:
        input_values['punchAmount'] = str(random.randint(51, 100))
    if 'punchesPer' not in input_values:
        input_values['punchesPer'] = "0"
    if 'maxPunchSize' not in input_values:
        input_values['maxPunchSize'] = str(random.randint(1, 1024))
    if 'seed' not in input_values:
        input_values['seed'] = str(random.randint(1, 100))
    if 'vbAmount' not in input_values: 
        input_values['vbAmount'] =  str(random.randint(1000, 10000))
    if 'vblkPer' not in input_values:
        input_values['vblkPer'] = str(random.randint(1, 20))
    if 'blockSize' not in input_values:
        input_values['blockSize'] = str(random.randint(1, 32))
    if 'blockSizeMax' not in input_values:
        input_values['blockSizeMax'] = str(random.randint(1, 32))
    if 'startVblk' not in input_values:
        input_values['startVblk'] = "0"
    if 'strideWidth' not in input_values:
        input_values['strideWidth'] = str(random.randint(1, 50))
    if 'numOfSet' not in input_values:
        input_values['numOfSet'] = str(random.randint(1, 10))
    if 'punchwholechunk' not in input_values:
        input_values['punchwholechunk'] = False   
    
    return input_values

def set_vals_from_json(cluster_params, dir_name, input_values):
    json_path = get_dir_path(cluster_params, dir_name)

    if json_path != None:
        entries = os.listdir(json_path)
        chunk_no = input_values["chunk"]
        if chunk_no not in entries:
            json_path = None
        else:
            new_path = json_path + "/" + input_values["chunk"] + "/DV"
            json_data = load_json_contents(new_path + "/dummy_generator.json")
            input_values["vdev"] = str(json_data['Vdev'])
            input_values["seqStart"] = str(json_data['SeqEnd'] + 1)
            dbicount = str(json_data['TMinDbiFileForForceGC'])

    return input_values

def add_params_to_cmd(commands, input_values):
    for cmd in commands:
        if input_values["punchwholechunk"] == "=true":
            cmd.extend(["-pc", input_values["punchwholechunk"]])
        if 'strideWidth' in input_values:
            cmd.extend(["-sw", input_values["strideWidth"]])
        if 'overlapSeq' in input_values and 'numOfSet' in input_values:
            cmd.extend(["-se", input_values["overlapSeq"], "-ts", input_values["numOfSet"]])
        if 'vdev' in input_values:
            cmd.extend(['-vdev', input_values['vdev']])

    return commands, input_values

def run_dummy_generator(command):
    print("command", command)
    try:
        result = subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def generate_data(cluster_params, dir_name, input_values, no_of_chunks, is_random, rm_files):
    base_dir = cluster_params['base_dir']
    raft_uuid = cluster_params['raft_uuid']
    binary_dir = os.getenv('NIOVA_BIN_PATH')
    bin_path = '%s/dummyData' % binary_dir
    path = "%s/%s/%s/" % (base_dir, raft_uuid, dir_name)
    s3_config_path = '%s/s3.config.example' % binary_dir
    s3_log_file = "%s/%s/s3Upload" % (base_dir, raft_uuid)

    # Create the new directory
    if not os.path.exists(path):
        # Create the directory path
        try:
            os.makedirs(path, mode=0o777)
        except Exception as e:
            print(f"An error occurred while creating '{path}': {e}")

    dbicount = "0"
    if is_random:
        input_values = generate_random_values(cluster_params, dir_name, input_values)
    else:
        input_values = set_vals_from_json(cluster_params, dir_name, input_values)

    commands = []
    for chunk in range(1, no_of_chunks + 1):
        if no_of_chunks > 1:
            input_values['chunk'] = str(chunk)
        command = [bin_path, "-c", input_values['chunk'], "-mp", input_values['maxPunches'], "-mv", input_values['maxVblks'], 
                   "-p", path, "-pa", input_values['punchAmount'], "-pp", input_values['punchesPer'], "-ps", input_values['maxPunchSize'], 
                   "-seed", input_values['seed'], "-ss", input_values['seqStart'], "-t", input_values['genType'], "-va", input_values['vbAmount'], 
                   "-l", "5", "-vp", input_values['vblkPer'], "-bs", input_values['blockSize'], "-bsm", input_values['blockSizeMax'], 
                   "-vs", input_values['startVblk'], "-s3config", s3_config_path, "-s3log", s3_log_file, "-dbic", dbicount]
        commands.append(command)


    commands, input_values = add_params_to_cmd(commands, input_values)

    if is_random:
        for cmd in commands:
            cmd.extend(['-b', 'paroscale-test'])
            if 'dbiWithPunches' in input_values:
                cmd.extend(['-e', input_values['dbiWithPunches']])
            if not rm_files:
                cmd.append('-r=true')

    with Pool(processes = no_of_chunks) as pool:
        results = pool.map(run_dummy_generator, commands)

    if is_random:
        return input_values['chunk']

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values
        dir_name = "dbi-dbo"
        cluster_params = kwargs['variables']['ClusterParams']
        operation = terms[0]

        if operation == "generator":
            input_values = terms[1]
            no_of_chunks = terms[2]
            is_random = terms[3]
            rm_files = terms[4]
            chunk = generate_data(cluster_params, dir_name, input_values, no_of_chunks, is_random, rm_files)
            return chunk