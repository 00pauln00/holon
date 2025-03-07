from ansible.plugins.lookup import LookupBase
import re

def extract_dbi_filenames(file_paths):
    filenames = []
    for path in file_paths.strip().split("\n"):
        filename = path.split("/")[-1]
        if filename != "dummy_generator.json":
            filenames.append(filename)
    return filenames

def empty_dbi_file_count(filenames):
    count = 0
    for filename in filenames:
        # Extract the last component from the filename
        components = filename.split(".")
        if len(components) >= 1:
            last_component = components[-1]
            if last_component == "0":
                count += 1
    return count

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        dbi_files_path_str = terms[0]
        
        dbi_file_names = extract_dbi_filenames(dbi_files_path_str)
        total_empty_dbis = empty_dbi_file_count(dbi_file_names)
        
        return [total_empty_dbis]
