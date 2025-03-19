from ansible.plugins.lookup import LookupBase

def twos_complement_to_decimal(hex_str):
    num = int(hex_str, 16)
    bit_length = len(hex_str) * 4

    return -(num - (1 << bit_length)) - 1 if num & (1 << (bit_length - 1)) else num

def ones_complement_to_decimal(hex_str):
    return int(hex_str, 16)

def extract_dbi_filenames(file_paths):
    if not file_paths:
        return []

    exclude_files = {"solutionArray", "dummy_generator.json"}

    return [
        path.split("/")[-1]
        for path in file_paths.strip().split("\n")
        if path.split("/")[-1] not in exclude_files
    ]

def get_dbi_sets_seq(dbi_file_list):
    if not dbi_file_list:
        return []

    return list({file.split(".")[0] for file in dbi_file_list})

def has_stale_set(file_paths):
    dbi_file_list = extract_dbi_filenames(file_paths)

    set_list = get_dbi_sets_seq(dbi_file_list)
    
    prev_start_seq = ones_complement_to_decimal(set_list[0].split("_")[1])

    for index in range(1, len(set_list)):
        curr_start_seq = ones_complement_to_decimal(set_list[index].split("_")[1])
        curr_end_seq = twos_complement_to_decimal(set_list[index].split("_")[0])
        
        # This condition checks if the current sequence occurs before the previous sequence.
        # - `curr_end_seq < prev_start_seq`: Ensures the current sequence ends before the previous one starts.
        # - `curr_start_seq < prev_start_seq`: Ensures the current sequence starts before the previous one.
        # If either of these conditions is true, it indicates that the current sequence does not overlap 
        # or is positioned entirely before the previous sequence.
        if not (curr_end_seq < prev_start_seq or curr_start_seq < prev_start_seq):
            return ['true']
            
        prev_start_seq = curr_start_seq    
        
    return ['false']

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        dbi_files_path_str = terms[0]
        
        return has_stale_set(dbi_files_path_str)
