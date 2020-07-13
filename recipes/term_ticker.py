from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "term_ticker"
    desc = "Term Ticker Recipe\n"\
            "1. Verify term increases in each iteration.\n"\
            "2. Restart the server process and make sure term value persists\n"\
            "across reboot.\n"
    parent = "basic_process_ctl"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []

    def print_desc(self):
        print(self.desc)

    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        logging.warning("=================Run Term Ticker recipe ====================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj
        serverproc0 = clusterobj.raftserverprocess[0]
        

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()
        logging.warning("Application UUID generated: %s" % app_uuid)

        peerno = 0
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(peerno)

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output to check term value. 
        '''
        get_all_ctl = CtlRequest(inotifyobj, "get_all", peer_uuid, app_uuid,
                                 inotify_input_base.REGULAR,
                                 self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        '''
        Run the loop to copy the command file for getting the term value
        and verifying in each iteration, term value increases.
        '''
        prev_term = 0
        recipe_failed = 0
        # TODO Iteration value should be specified by user. 
        logging.warning("Copy cmd file to get and verify term value\n")
        for i in range(10):
            # Copy the cmd file into input directory of server.
            get_all_ctl.Apply_and_Wait(False)
            # Send the output value for reading the term value.
            raft_json_dict = genericcmdobj.raft_json_load(get_all_ctl.output_fpath)
            term = raft_json_dict["raft_root_entry"][0]["term"]

            logging.warning("Term value returned is: %d" % term)
            if term <= prev_term:
                logging.error("Raft server term value is not increasing")
                recipe_failed = 1
                break

            # Verify voted-for-uuid should be same as self uuid
            voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
            if voted_for_uuid != peer_uuid:
                logging.error("voted-for-uuid %s is not same as self uuid %s" % (voted_for_uuid, peer_uuid))
                recipe_failed = 1
                break

            leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            if leader_uuid != "":
                logging.error("Error: Leader UUID is not Null: %s" % leader_uuid)
                recipe_failed = 1
                break

            state = raft_json_dict["raft_root_entry"][0]["state"]
            if state != "candidate":
                logging.error("State(%s) is not candiate" % state)
                recipe_failed = 1
                break

            follower_reason = raft_json_dict["raft_root_entry"][0]["follower-reason"]
            if follower_reason != "none":
                logging.error("Follower reason is not none (%s)" % follower_reason)
                recipe_failed = 1
                break

            cli_req = raft_json_dict["raft_root_entry"][0]["client-requests"]
            if cli_req != "deny-leader-not-established":
                logging.error("client-requests is not deny-leader-not-established (%s)" % cli_req)
                recipe_failed = 1
                break

            commit_idx = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            if commit_idx != -1:
                logging.error("commit-idx is not -1 (%s)" % commit_idx)
                recipe_failed = 1
                break

            last_applied = raft_json_dict["raft_root_entry"][0]["last-applied"]
            if last_applied != -1:
                logging.error("Last applied is not -1 (%s)" % last_applied)
                recipe_failed = 1
                break

            cumu_crc = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]
            if cumu_crc != 0:
                logging.error("last-applied-cumulative-crc is not 0 (%s)" % cumu_crc)
                recipe_failed = 1
                break

            #TODO verify total_writes - Term = 2
            # Sleep for 2second to allow term to get incremented.
            time_global.sleep(2)

        if recipe_failed:
            logging.error("Term ticker recipe failed")
            return recipe_failed

        '''
        Store the current term and restart the server. After reboot, server should have
        term value > previously strored term + 1 or 2. I.e term value should persist
        across reboots.
        '''
            
        before_restart_term = term
        logging.warning("Term value before Restart of the server is %s" % before_restart_term)

        # Kill the server
        serverproc0.kill_process()

        # Restart the server
        serverproc0.start_process(raftconfobj, clusterobj)

        # Copy the cmd file and verify term value is greater than before_restart_term
        get_all_ctl.Apply_and_Wait(False)
        # Send the output value for reading the term value.
        raft_json_dict = genericcmdobj.raft_json_load(get_all_ctl.output_fpath)
        curr_term = raft_json_dict["raft_root_entry"][0]["term"]

        logging.warning("After restart, term value is: %s" % curr_term)

        if curr_term <= before_restart_term:
            logging.error("curr_term %s <= before_restart_term %s" % (curr_term, before_restart_term))
            recipe_failed = 1

        if recipe_failed:
            logging.error("Term Ticker Recipe Failed")
        else:
            logging.warning("Term ticker Recipe Successful, Raft Peer 0's term value increasing!!\n")

        return recipe_failed

    def post_run(self, clusterobj):
        logging.warning("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()
