from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "basic_leader_election"
    desc = "Basic leader election\n"\
            "1. Start number_of_peers/2 + 1 servers for basic leader election\n"\
            "2. Copy the command file and get the JSON output from all running peers\n"\
            "3. Compare values to make sure leader election happened successfully\n"
    parent = "term_catch_up"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    
    def dry_run(self):
        print(self.desc)

    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        '''
        Purpose of this recipe is:
        Invoke and observe a successful leader election with the minimum
        number of peers per the specified configuration.
        '''
        print(f"================ Run Basic Leader election ======================\n")

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
        Make sure we wait for leader election to complete.
        Check leader election completion in a loop
        '''
        leader_uuid = {}
        term_values = {}
        commit_idx = {}
        last_applied = {}
        cumu_crc = {}
        newest_entry_term = {}
        newest_entry_crc = {}

        for itr in range(100):
            election_in_progress = 0
            for p in range(npeer_start):
                raft_json_dict = genericcmdobj.raft_json_load(get_ctl[p].output_fpath)
                leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
                if leader_uuid[p] == "":
                    time_global.sleep(1)
                    election_in_progress = 1
                    ctl_req_create_cmdfile_and_copy(get_ctl[p])
                    break

            if election_in_progress == 0:
                print("Leader election successful")
                break

        
        recipe_failed = 0
        for p in range(npeer_start):
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[p].output_fpath)
            leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]

            term_values[p] = raft_json_dict["raft_root_entry"][0]["term"]

            commit_idx[p] = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            if commit_idx[p] != 0:
                print("Error: Commit idx is not 0 for peer %s" % p)
                recipe_failed = 1
                break

            last_applied[p] = raft_json_dict["raft_root_entry"][0]["last-applied"]
            if last_applied[p] != 0:
                print("Error: Last applied is not 0 for peer %s" % p)
                recipe_failed = 1
                break

            cumu_crc[p] = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]

            newest_entry_term[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]

            newest_entry_crc[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]

            # Term should be same as newest_entry_term
            if term_values[p] != newest_entry_term[p]:
                print("Error, term %d is not same as newest-entry-term %d" % (term_values[p], newest_entry_term[p]))
                recipe_failed = 1
                break

            # last-applied-cumulative-crc should be same as newest-entry-crc
            if cumu_crc[p] != newest_entry_crc[p]:
                print("Error: last-applied-cumulative-crc %d is not same as newest-entry-crc : %d" % (cumu_crc[p], newest_entry_crc[p]))
                recipe_failed = 1
                break

        # Make sure leader-uuid is same on all three peers.
        if not (leader_uuid[0] == leader_uuid[1] and leader_uuid[0] == leader_uuid[2]):
            print("Error Leader uuid is not same of all peers")
            recipe_failed = 1
        elif not (term_values[0] == term_values[1] and term_values[0] == term_values[2]):
            print("Error: Term values are not same for all peers")
            recipe_failed = 1

        if recipe_failed:
            print("Basic Leader election Faileed")
        else:
            print("Basic leader election Successful, Leader election successful!!\n")

        # Store the raftserver2 object into clusterobj
        clusterobj.raftserver_obj_store(raftserverobj2, peerno)
        # Store server2 process object
        clusterobj.raftprocess_obj_store(serverproc2, peerno)
        

    def post_run(self, clusterobj):
        print("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()

        for proc_obj in self.recipe_proc_obj_list:
            print("kill server process: %d" % proc_obj.process_idx)
            proc_obj.kill_process()
