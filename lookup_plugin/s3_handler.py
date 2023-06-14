def start_dbi_gen():
    #TODO Start DBI gen process

def start_gc():
    #TODO Start GC process

def start_validate():
    #TODO Start GC validation process

def extract_and_run_dbi_gen(s3_params, input_values):
    nDBIs = ""
    c_ow_percent = ""
    p_ow_percent = ""
    punch_ow_percent = ""
    
    #TODO Start dbi gen process with proper params
    process, outfile = start_dbi_gen()

def extract_and_run_gc(s3_params, input_values):

    #TODO Start GC process with proper params
    process, outfile = start_gc()

def extract_and_run_validaiton():

    #TODO Start validation process with proper params
    process, outfile = start_validate()

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
