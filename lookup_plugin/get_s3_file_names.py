from ansible.plugins.lookup import LookupBase

def extract_dbi_filenames(file_paths):
    filenames = []
    exclude_files = {"solutionArray", "dummy_generator.json"}

    for path in file_paths.strip().split("\n"):
        filename = path.split("/")[-1]
        
        if filename not in exclude_files:
            filenames.append(filename)

    return filenames

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        dbi_files_path_str = terms[0]

        file_list = extract_dbi_filenames(dbi_files_path_str)

        return file_list
