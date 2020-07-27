import os, subprocess, json, time, logging, socket, errno, shutil
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
        p = subprocess.run(['cp', src_path, dest_path], stdout=subprocess.PIPE)

        if p.returncode != 0:
            logging.error("Copy file %s to %s failed with error: %d" % (src_path, dest_path, p.returncode))

        return p.returncode

    '''
    Method: Move file from source to destinaton directory
    '''
    def move_file(self, src_path, dest_path):
        
        try:
            shutil.move(src_path, dest_path)
        except shutil.Error:
            raise logging.error("Move file %s to %s failed with error: %s" % (src_path, dest_path, shutil.Error))
            return shutil.Error

    def remove_file(self, fpath):
        rc = 0
        try:
            rc = os.remove(fpath)
        except OSError as e:
            logging.error("File %s remove failed with error: %s" % (fpath, os.strerror(e.errno)))
            
        return rc

    '''
    method raft_json_load: Lead the JSON file
    '''
    def raft_json_load(self, ctlreqobj):
        fpath = ctlreqobj.get_latest_version_ofile()
        '''
        Sleep for 1 sec if file has not got created yet.
        '''
        while os.path.exists(fpath) == False:
            time.sleep(1)

        with open(fpath) as f:
            data = json.load(f)

        return data

    def make_dir(self, dirpath):
        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

    '''
    method port_check: Check the Port is already in use or not
    '''
    def port_check(self, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            s.bind(("127.0.0.1", port))
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
               print(f"Port %d is already in use" % port)
               exit()
        s.close()

