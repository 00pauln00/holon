from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe04"
    desc = "Basic leader election"
    parent = "recipe03"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    
    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        '''
        Purpose of this recipe is:
        Invoke and observe a successful leader election with the minimum
        number of peers per the specified configuration.
        '''
        print(f"================ Run Recip04 ======================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        # Number of peers to be started for Recipe04
        npeer_start = 3
        peerno = 2
        peer_uuid_arr = [None] * npeer_start

        for p in range(npeer_start):
            peer_uuid_arr[p] = raftconfobj.get_peer_uuid_for_peerno(p)

        '''
        To start the peer2, create objects for raftserver and raftprocess.
        '''
        print(f"Starting peer %d with UUID: %s" % (peerno, peer_uuid_arr[peerno]))
        raftserverobj2 = RaftServer(raftconfobj, peerno)
        serverproc2 = RaftProcess(peer_uuid_arr[peerno], peerno, "server")

        serverproc2.start_process(raftconfobj)
        # append the serverproc into recipe process object list
        self.recipe_proc_obj_list.append(serverproc2)

        time_global.sleep(2)
        '''
        After starting peer2, minimum number of servers for leader election
        have reached.
        '''

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output to check term value. 
        '''
        get_ctl = [None] * npeer_start

        for p in range(npeer_start):
            get_ctl[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p], app_uuid)
            self.recipe_ctl_req_obj_list.append(get_ctl[p])


        '''
        Copy the get all command file into input directories of peer0,
        peer1 and peer2. And verify all peers elected the same leader.
        '''

        for p in range(npeer_start):
            get_ctl[p].ctl_req_create_cmdfile_and_copy(genericcmdobj)

        time_global.sleep(5)

        '''
        Get the leader UUID from all the 3 servers.
        '''
        leader_uuid = [None] * npeer_start

        for p in range(npeer_start):
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[p].output_fpath)
            leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["term"]
            print(f"Leader uuid of peer%d is: %s" % (p, leader_uuid[p]))


        if leader_uuid[0] != leader_uuid[1]:
            print(f"Error: Peer0 leader(%s) does not match with peer1 leader(%s)" %
                                leader_uuid[0], leader_uuid[1])
            exit()
        elif leader_uuid[0] != leader_uuid[2]:
            print(f"Error: Peer0 leader(%s) does not match with peer2 leader(%s)" %
                                leader_uuid[0], leader_uuid[2])
            exit()
                
        print("Recipe04 Successful, Leader election successful!!\n")

        # Store the raftserver2 object into clusterobj
        clusterobj.raftserver_obj_store(raftserverobj2, peerno)
        # Store server2 process object
        clusterobj.raftprocess_obj_store(serverproc2, peerno)
        

    def post_run(self, clusterobj):
        print("Post run method for recipe04")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()

        for proc_obj in self.recipe_proc_obj_list:
            print("kill server process: %d" % proc_obj.process_idx)
            proc_obj.kill_process()
