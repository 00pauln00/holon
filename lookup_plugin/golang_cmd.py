from ansible.plugins.lookup import LookupBase
import fcntl
import sys
import json
import termios
import os
import time

class LookupModule(LookupBase):
    def run(self,terms,**kwargs):
        #Get parameter values
        cmd=terms[0]
        uuid=terms[1]
        cluster_params = kwargs['variables']['ClusterParams']
        print("Debug : ",cmd," ",uuid)
        # open the application log and get pid
        recipe_conf = {}
        raft_json_fpath = "%s/%s/%s.json" % (cluster_params['base_dir'], cluster_params['raft_uuid'], cluster_params['raft_uuid'])
        if os.path.exists(raft_json_fpath):
            with open(raft_json_fpath, "r+", encoding="utf-8") as json_file:
                recipe_conf = json.load(json_file)
        #Get pid
        pid = int(recipe_conf['raft_process'][uuid]['process_pid'])
        #debug 
        
        #check pid is alive
        #send the cmd to application client through proc
        path="/proc/{}/fd/0".format(pid)
        cmd+="\n"
        try:
            with open(path, 'w') as fd:
                for c in cmd:
                    fcntl.ioctl(fd, termios.TIOCSTI, c)
        except:
            return {"Client has crashed"}

        #temp not checking json file for writes
        counter=0 #Timeout for checking output file 
        client_json="%s/%s/client_%s.json" % (cluster_params['base_dir'], cluster_params['raft_uuid'],uuid)
        while True:
            if os.path.exists(client_json):
                try:
                    with open(client_json, "r+", encoding="utf-8") as json_file:
                        request = json.load(json_file)
                except:
                    pass
                break
            else:
                #busy wait
                counter+=1
                time.sleep(1)
                if counter == 5:
                    return "Output file not created"
        
        #Parsing
        if "Read" in request['Operation'] or "Write" in request['Operation']: 
            return request['App_data']
        else:
            return request['Leader_uuid']
