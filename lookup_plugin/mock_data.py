from ansible.plugins.lookup import LookupBase
import os, random
import subprocess
from multiprocessing import Pool
from lookup_plugin.helper import *

class data_generator:
    def __init__(self, cluster_params):
        self.cluster_params = cluster_params
        self.bin_dir =  os.getenv('NIOVA_BIN_PATH')
        self.base_path = f"{cluster_params['base_dir']}/{cluster_params['raft_uuid']}/"
        self.s3_upload_log = f"{self.base_path}/s3Upload"

    def generate_random_values(self, input_values):
        dbi_path = get_dir_path(self.cluster_params, DBI_DIR)

        if dbi_path != None:
            json_data = load_parameters_from_json(f"{dbi_path}/{input_values['chunk']}/DV/dummy_generator.json")
            input_values['chunk'] = str(json_data['TotalChunkSize'])
            input_values["seqStart"] = str(json_data['SeqEnd'] + 1)
            input_values["vdev"] = str(json_data['Vdev'])
            dbicount = str(json_data['TMinDbiFileForForceGC'])
        else:
            input_values["seqStart"] = "0"
            dbicount = "0"

        defaults = {
            'chunk': lambda: str(random.randint(1, 200)),
            'maxPunches': lambda: str(random.randint(1, 50)),
            'maxVblks': lambda: str(random.randint(100, 1000)),
            'punchAmount': lambda: str(random.randint(51, 100)),
            'punchesPer': lambda: "0",
            'maxPunchSize': lambda: str(random.randint(1, 1024)),
            'seed': lambda: str(random.randint(1, 100)),
            'vbAmount': lambda: str(random.randint(1000, 10000)),
            'vblkPer': lambda: str(random.randint(1, 20)),
            'blockSize': lambda: str(random.randint(1, 32)),
            'blockSizeMax': lambda: str(random.randint(1, 32)),
            'startVblk': lambda: "0",
            'strideWidth': lambda: str(random.randint(1, 50)),
            'numOfSet': lambda: str(random.randint(1, 10)),
            'punchwholechunk': lambda: False,
        }

        for key, random_val in defaults.items():
            if key not in input_values:
                input_values[key] = random_val()
    
        return input_values

    def set_vals_from_json(self, input_values):
        dbi_path = get_dir_path(self.cluster_params, DBI_DIR)

        if dbi_path != None:
            entries = os.listdir(dbi_path)
            chunk_no = input_values["chunk"]
            if chunk_no not in entries:
                dbi_path = None
            else:
                json_data = load_parameters_from_json(f"{dbi_path}/{input_values['chunk']}/DV/dummy_generator.json")
                input_values["vdev"] = str(json_data['Vdev'])
                input_values["seqStart"] = str(json_data['SeqEnd'] + 1)
                dbicount = str(json_data['TMinDbiFileForForceGC'])

        return input_values

    def add_params_to_cmd(self, commands, input_values):
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

    def run_dummy_generator(self, command):
        print("command", command)
        try:
            result = subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")

    def generate_data(self, input_values, no_of_chunks, is_random, rm_files):
        bin_path = f'{self.bin_dir}/dummyData'
        s3_config = f'{self.bin_dir}/s3.config.example'
        path = f"{self.base_path}/{DBI_DIR}"

        # Create the new directory
        if not os.path.exists(path):
            # Create the directory path
            try:
                os.makedirs(path, mode=0o777)
            except Exception as e:
                print(f"An error occurred while creating '{path}': {e}")

        dbicount = "0"
        if is_random:
            input_values = self.generate_random_values(input_values)
        else:
            input_values = self.set_vals_from_json(input_values)

        commands = []
        for chunk in range(1, no_of_chunks + 1):
            if no_of_chunks > 1:
                input_values['chunk'] = str(chunk)
            command = [bin_path, "-c", input_values['chunk'], "-mp", input_values['maxPunches'], "-mv", input_values['maxVblks'], 
                       "-p", path, "-pa", input_values['punchAmount'], "-pp", input_values['punchesPer'], "-ps", input_values['maxPunchSize'], 
                       "-seed", input_values['seed'], "-ss", input_values['seqStart'], "-t", input_values['genType'], "-va", input_values['vbAmount'], 
                       "-l", "5", "-vp", input_values['vblkPer'], "-bs", input_values['blockSize'], "-bsm", input_values['blockSizeMax'], 
                       "-vs", input_values['startVblk'], "-s3config", s3_config, "-s3log", self.s3_upload_log, "-dbic", dbicount]
            commands.append(command)

        commands, input_values = self.add_params_to_cmd(commands, input_values)

        if is_random:
            for cmd in commands:
                cmd.extend(['-b', 'paroscale-test'])
                if 'dbiWithPunches' in input_values:
                    cmd.extend(['-e', input_values['dbiWithPunches']])
                if not rm_files:
                    cmd.append('-r=true')

        with Pool(processes = no_of_chunks) as pool:
            results = pool.map(self.run_dummy_generator, commands)

        if is_random:
            return input_values['chunk']

class data_validator:
    def __init__(self, cluster_params):
        self.cluster_params = cluster_params
        self.bin_dir =  os.getenv('NIOVA_BIN_PATH')
        self.base_path = f"{cluster_params['base_dir']}/{cluster_params['raft_uuid']}/"
        self.data_validate_log = f"{self.base_path}/dataValidateResult"

    def validate_data(self, chunk):
        bin_path = f'{self.bin_dir}/dataValidator'
        dbi_path = get_dir_path(self.cluster_params, DBI_DIR)
        s3_config = f'{self.bin_dir}/s3.config.example'
        dv_path = f"{self.base_path}/dv-downloaded-obj"
        
        if dbi_path != None:
            json_data = load_parameters_from_json(f"{dbi_path}/{chunk}/DV/dummy_generator.json")
            vdev = str(json_data['Vdev'])

        modified_path = modify_path(dbi_path)
        process = subprocess.Popen([bin_path, '-d', dv_path, '-c', chunk, '-v', vdev, '-s3config', s3_config, '-b', 'paroscale-test', '-l', self.data_validate_log, '-ll', '2'])

        # Wait for the process to finish and get the exit code
        exit_code = process.wait()

        # Check if the process finished successfully (exit code 0)
        if exit_code == 0:
            f"Process completed successfully."
        else:
            error_message = f"Process failed with exit code {exit_code}."
            raise RuntimeError(error_message)

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        operation = terms[0]
        cluster_params = kwargs['variables']['ClusterParams']

        if operation == "generator":
            input_values = terms[1]
            no_of_chunks = terms[2]
            is_random = terms[3]
            rm_files = terms[4]
            data = data_generator(cluster_params)
            chunk = data.generate_data(input_values, no_of_chunks, is_random, rm_files)
            return chunk
        
        elif operation == "validator":
            chunk = terms[1]
            dv = data_validator(cluster_params)
            dv.validate_data(chunk)