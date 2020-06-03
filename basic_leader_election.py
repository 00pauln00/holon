from holonrecipe import *
import logging

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
        logging.warning("================ Run Basic Leader election ======================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        # Number of peers to be started for Recipe04
        npeer_start = int(raftconfobj.nservers / 2) + 1
        peer_uuid_arr = {}

        logging.warning("Number of peers needed for leader election: %d" % npeer_start)

        for p in range(npeer_start):
            peer_uuid_arr[p] = raftconfobj.get_peer_uuid_for_peerno(p)

        '''
        peer0 and peer1 is already started by the previous recipes.
        So start from peer2 till npeer_start for basic leader election
        '''
        serverproc = {}
        for p in range(2, npeer_start):
            logging.warning("Starting peer %d with UUID: %s" % (p, peer_uuid_arr[p]))
            serverproc[p] = RaftProcess(peer_uuid_arr[p], p, "server")
            serverproc[p].start_process(raftconfobj)
            # append the serverproc into recipe process object list
            self.recipe_proc_obj_list.append(serverproc[p])

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
                logging.warning("Leader election successful")
                break

        
        recipe_failed = 0
        for p in range(npeer_start):
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[p].output_fpath)
            leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]

            term_values[p] = raft_json_dict["raft_root_entry"][0]["term"]

            commit_idx[p] = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            if commit_idx[p] != 0:
                logging.error("Commit idx is not 0 for peer %s" % p)
                recipe_failed = 1
                break

            last_applied[p] = raft_json_dict["raft_root_entry"][0]["last-applied"]
            if last_applied[p] != 0:
                logging.error("Last applied is not 0 for peer %s" % p)
                recipe_failed = 1
                break

            cumu_crc[p] = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]

            newest_entry_term[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]

            newest_entry_crc[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]

            # Term should be same as newest_entry_term
            if term_values[p] != newest_entry_term[p]:
                loggin.error("term %d is not same as newest-entry-term %d" % (term_values[p], newest_entry_term[p]))
                recipe_failed = 1
                break

            # last-applied-cumulative-crc should be same as newest-entry-crc
            if cumu_crc[p] != newest_entry_crc[p]:
                logging.error("last-applied-cumulative-crc %d is not same as newest-entry-crc : %d" % (cumu_crc[p], newest_entry_crc[p]))
                recipe_failed = 1
                break

        if recipe_failed:
            logging.error("Basic leader election recipe failed")
            return recipe_failed
        # Make sure leader-uuid is same on all three peers.
        elif not (leader_uuid[0] == leader_uuid[1] and leader_uuid[0] == leader_uuid[2]):
            logging.error("Leader uuid is not same of all peers")
            recipe_failed = 1
        elif not (term_values[0] == term_values[1] and term_values[0] == term_values[2]):
            logging.error("Term values are not same for all peers")
            recipe_failed = 1

        if recipe_failed:
            logging.error("Basic Leader election recipe Failed")
        else:
            logging.warning("Basic leader election Successful, Leader election successful!!\n")

        # Store server2 process object
        for p in range(2, npeer_start):
            clusterobj.raftprocess_obj_store(serverproc[p], p)

        return recipe_failed
        

    def post_run(self, clusterobj):
        logging.warning("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()

        for proc_obj in self.recipe_proc_obj_list:
            logging.warning("kill server process: %d" % proc_obj.process_idx)
            proc_obj.kill_process()
