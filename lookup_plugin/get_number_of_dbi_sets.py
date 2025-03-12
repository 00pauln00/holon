from ansible.plugins.lookup import LookupBase
import re

def count_unique_sets(file_list):
    unique_sets = set()
    
    for file in file_list:
        set_name = file.split(".")[0]
        unique_sets.add(set_name)
    
    return len(unique_sets)


def extract_dbi_filenames(file_paths):
    filenames = []
    for path in file_paths.strip().split("\n"):
        filename = path.split("/")[-1]
        if filename != "solutionArray":
            filenames.append(filename)
    return filenames

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        dbi_files_path_str = terms[0]

        file_list = extract_dbi_filenames(dbi_files_path_str)
        total_sets = count_unique_sets(file_list)

        return [total_sets]
