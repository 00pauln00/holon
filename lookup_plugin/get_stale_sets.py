from ansible.plugins.lookup import LookupBase

def twos_complement_to_decimal(hex_str):
    """Convert a two's complement hex string to a signed integer."""
    num = int(hex_str, 16)
    bit_length = len(hex_str) * 4

    return num - (1 << bit_length) if num & (1 << (bit_length - 1)) else num

def ones_complement_to_decimal(hex_str):
    """Convert a one's complement hexadecimal string to a signed integer."""
    return -int(hex_str, 16)

def extract_dbi_filenames(file_paths):
    """Extract filenames from a newline-separated string of file paths."""
    if not file_paths:
        return []

    exclude_files = {"solutionArray", "dummy_generator.json"}

    return [
        path.split("/")[-1]
        for path in file_paths.strip().split("\n")
        if path.split("/")[-1] not in exclude_files
    ]

def get_dbi_sets_seq(dbi_file_list):
    """Extract unique set names from a list of DBI filenames."""
    if not dbi_file_list:
        return []

    return list({file.split(".")[0] for file in dbi_file_list})

def validate_stale_set(file_paths):
    dbi_file_list = extract_dbi_filenames(file_paths)

    rev_set_list = get_dbi_sets_seq(dbi_file_list)[::-1]

    decimal_seq = set()

    for index, hex_seq in enumerate(rev_set_list):
        if index % 2 == 0:  # If index is even, apply two's complement conversion
            decimal_seq.add(twos_complement_to_decimal(hex_seq))
        else:  # If index is odd, apply one's complement conversion
            decimal_seq.add(ones_complement_to_decimal(hex_seq))

    return decimal_seq  # Return fixed value as per original logic

class LookupModule(LookupBase):
    """Ansible lookup plugin to validate DBI sets."""

    def run(self, terms, **kwargs):  # Accept **kwargs to handle unexpected arguments
        """Run the lookup plugin."""
        dbi_files_path_str = terms[0]
        return validate_stale_set(dbi_files_path_str)
