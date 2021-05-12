from ansible.plugins.lookup import LookupBase
import fcntl
import sys
import json
import termios
import os
import time

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get lookup parameter values[cmd,client_uuid]
        cmd = terms[0]
        uuid = terms[1]
        cluster_params = kwargs['variables']['ClusterParams']
        

        #Open the application log and get pid
        raft_json_fpath = "%s/%s/%s.json" % (cluster_params['base_dir'], cluster_params['raft_uuid'], cluster_params['raft_uuid'])
        if os.path.exists(raft_json_fpath):
            with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
                recipe_conf = json.load(json_file)
                pid = int(recipe_conf['raft_process'][uuid]['process_pid'])
        
        #Get operation and file_name from cmd
        opcode,fname = cmd.split("#")[0],cmd.split("#")[-1] 

        #Send the cmd to application client through proc
        path="/proc/{}/fd/0".format(pid)
        cmd+="\n"
        try:
            with open(path, 'w') as fd:
                for c in cmd:
                    fcntl.ioctl(fd, termios.TIOCSTI, c)
        except:
            #Client is not running
            return {"status":-1,"msg":"Client is not running!"}

        #Wait till output json file created
        counter = 0
        timeout = 2500
        client_json = "%s/%s/%s.json" % (cluster_params['base_dir'],cluster_params['raft_uuid'],fname)
        print(client_json)
        while True:
            if os.path.exists(client_json):
                try:
                    with open(client_json, "r+", encoding="utf-8") as json_file:
                        request = json.load(json_file)
                except:
                    return {"status":-1,"msg":"Invalid json format in output file"}
                break
            else:
                #Wait, fail at max count
                counter += 1
                time.sleep(0.1)
                if counter == timeout:
                    return {"status":-1,"msg":"Timeout checking for output file"}
        
        #Output parsing
        if "Read" in request['Operation']: 
            return {"status":0,"response":request['Data']}
        elif "Write" in request['Operation']:
            return {"status":0,"response":request['Data']}
        else:
            return {"status":0,"response":request['Leader_uuid']}
