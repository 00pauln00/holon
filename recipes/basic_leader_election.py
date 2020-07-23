from holonrecipe import *
import logging
from recipe_verify import *
import json

class Recipe(HolonRecipeBase):
    name = "basic_leader_election"
    desc = "Basic leader election\n"\
            "1. Start number_of_peers/2 + 1 servers for basic leader election\n"\
            "2. Copy the command file and get the JSON output from all running peers\n"\
            "3. Compare values to make sure leader election happened successfully\n"
    parent = "term_catch_up"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    stage_rule_table = {}

    def print_desc(self):
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
            serverproc[p].start_process(raftconfobj, clusterobj)
            # append the serverproc into recipe process object list
            self.recipe_proc_obj_list.append(serverproc[p])

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
            get_ctl[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        '''
        Make sure we wait for leader election to complete.
        Check leader election completion in a loop
        '''
        #Load te rule table
        with open('rule_table/basic_leader_election.json') as json_file:
            self.stage_rule_table = json.load(json_file)

        for itr in range(5):
            election_in_progress = 0
            for p in range(npeer_start):
                logging.warning("Copy the cmd file into input directory of server. peer %d" % p)
                get_ctl[p].Apply_and_Wait(False)
                time_global.sleep(4)
                '''
                Add get_ctl object into stage0_rule_table to perform the rule checks
                on it.
                '''
                get_all_ctl = []
                get_all_ctl.append(get_ctl[p])

                # Now access stage0_rule_table
                self.stage_rule_table[0]["ctlreqobj"] = get_all_ctl
                self.stage_rule_table[0]["orig_ctlreqobj"] = None

                recipe_failed = verify_rule_table(self.stage_rule_table[0])
                if recipe_failed:
                    election_in_progress = 1
                    logging.warning("Leader election failed")
                    get_ctl[p].Apply_and_Wait(False)
                    break

            if election_in_progress == 0:
                logging.warning("Leader election successful")
                break

        for p in range(npeer_start):
            logging.warning("Copy the cmd file into input directory of server. peer %d" % p)
            get_ctl[p].Apply_and_Wait(False)
            time_global.sleep(4)
            '''
            Add get_ctl object into stage1_rule_table to perform the rule checks
            on it.
            '''
            compare_value = []
            compare_value.append(get_ctl[p])
           
            # Now access stage1_rule_table
            self.stage_rule_table[1]["ctlreqobj"] = compare_value
            self.stage_rule_table[1]["orig_ctlreqobj"] = None

            recipe_failed = verify_rule_table(self.stage_rule_table[1])
            if recipe_failed:
                break

        if recipe_failed:
            logging.error("Basic Leader Election recipe failed")
        else:
            logging.warning("Basic Leader Election recipe Successful")
        return recipe_failed
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
