import struct

class DBI_vblk_entry:
    def __init__(self, dve_type, dve_crc, dve_number, dve_dbo_off, dve_dbo_len):
        self.dve_type = dve_type
        self.dve_crc = dve_crc
        self.dve_number = dve_number
        self.dve_dbo_off = dve_dbo_off
        self.dve_dbo_len = dve_dbo_len

class DBIEntryVal:
    def __init__(self, vblk, seq, vblk_num):
        self.vblk = vblk
        self.seq = seq
        self.vblk_num = vblk_num

def start_dbi_gen(s3_params):
    #TODO Start DBI gen process
    out_dir = s3_params['out_dir']
    outfile_path = "%s/" % out_dir  #TODO Add outfile name as DBO name

    binary_dir = os.getenv('S3_BIN_PATH')
    bin_path = '%s/example' % binary_dir

    log_file = "%s/s3_log.log" % out_dir
    fp = open(log_file, "w")

    process_popen = subprocess.Popen([], stdout = fp, stderr = fp)

    os.fsync(fp)
    return process_popen,

def start_gc(dbi_list):
    #TODO Start GC process

def start_validate(dbi_list):
    #TODO Start GC validation process

def read_dbi(file_path):
    #NOTE For different DBI Entries, the structs will have different alignments
    entries = []
    with open(file_path, "rb") as file:
        while True:
            fe = file.read(struct.calcsize("<I"))
            if not fe:
                break
            t = struct.unpack_from("<I", fe)
            if t[0] == 1:
                dbi_pattern = "4IQI"
                entry_data = file.read(struct.calcsize(dbi_pattern))
                if not entry_data:
                    break
                vblk_type, vblk_crc, vblk_number, vblk_dbo_off, vblk_dbo_len, seq, vblk_num = struct.unpack(dbi_pattern, entry_data)
                vblk_entry = DBI_vblk_entry(vblk_type, vblk_crc, vblk_number, vblk_dbo_off, vblk_dbo_len)
                entry = DBIEntryVal(vblk_entry, seq, vblk_num)
                entries.append(entry)
            elif t[0] == 0:
                #TODO Add code for unpacking dbi punch entry
    return entries

def cmp_and_verify_dbi(dbi_list1, dbi_list2):
    #NOTE If the comparison for dbi1 and dbi2 has to be unordered, then we have to use 'sets'



def extract_and_run_dbi_gen(s3_params, input_values):
    nDBIs = ""
    c_ow_percent = ""
    p_ow_percent = ""
    punch_ow_percent = ""
    
    #TODO Start dbi gen process with proper params
    process, outfile = start_dbi_gen()

def extract_and_run_gc(s3_params, input_values):

    dbi_list = read_dbi(file_path)
    #TODO Start GC process with proper params
    process, outfile = start_gc(dbi_list)

def extract_and_run_validaiton():

    dbi_list = read_dbi(file_path)
    #TODO Start validation process with proper params
    process, outfile = start_validate(dbi_list)

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        #Get lookup params
        process_type = terms[0]
        input_values = terms[1]

        s3_params = kwargs['variables']['s3Params']

        if process_type == "dbi_gen":
            data = extract_and_run_dbi_gen(s3_params, input_values)

            return data

        if process_type == "gc_validation":
            data = extract_and_validate(s3_params, input_values)

            return data

        elif process_type == "gc":
            data = extract_and_run_gc(s3_params, input_values)

            return data
