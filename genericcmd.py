import os, subprocess
from datetime import datetime

'''
This class will have wrapper functions for generic system cmds.
'''
class GenericCmds:
    '''
    Method: generate uuid.
    Purpose: Call uuid system command and generate the UUID.
    Parameters:
    '''
    def generate_uuid(self):
        
        p = subprocess.Popen(["uuid"], stdout=subprocess.PIPE)
        (stdout, err) = p.communicate()
        
        #remove the newline
        uuid_bytes = stdout.strip()
        uuid = uuid_bytes.decode('utf-8')

        return uuid

    '''
    Method: copy file from source to destinaton directory
    '''
    def copy_file(self, src_path, dest_path):
        
        try:
            subprocess.Popen(['cp', src_path, dest_path], stdout=subprocess.PIPE)
        except FileNotFoundError:
            print("File not found!")
