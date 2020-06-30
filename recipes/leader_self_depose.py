from holonrecipe import *
import logging
import psutil

class Recipe(HolonRecipeBase):
    name = "leader_self_depose"
    desc = "Leader Self-Depose\n"\
            "Purpose: To observe the leader reporting that it has lost contact with its followers.\n"
    parent = "basic_leader_election"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    
    def print_desc(self):
        print(self.desc)

    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        logging.warning("================ Run Leader-Self Depose ======================\n")

        peer_uuid = {}
        term = {}
        orig_term = {}
        commit_idx = {}
        orig_commit_idx = {}
        newest_entry_term = {}
        orig_newest_entry_term = {}
        newest_entry_dsize = {}
        orig_newest_entry_dsize = {}
        newest_entry_crc = {}
        orig_newest_entry_crc = {}
        leader_uuid = {}
        orig_leader_uuid = {}
        voted_for_uuid = {}
        prev_idx_term ={}

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj
        serverproc = clusterobj.raftserverprocess
        
        '''
        Number of peers to be started for basic leader election
        '''
        
        npeer_start = int(raftconfobj.nservers / 2) + 1
        peer_uuid_arr = {}

        logging.warning("Number of peers needed for leader election: %d" % npeer_start)

        for p in range(npeer_start):
            peer_uuid_arr[p] = raftconfobj.get_peer_uuid_for_peerno(p)

        '''
        Create object for generic cmds.
        '''
        genericcmdobj = GenericCmds()

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output 
        '''
        get_ctl = [None] * npeer_start

        for p in range(npeer_start):
            get_ctl[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply()

        follower ={}
        fpeer = 0

        for p in range(npeer_start):
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[p].output_fpath)
            peer_uuid[p] = raft_json_dict["raft_root_entry"][0]["peer-uuid"]
            orig_leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            orig_term[p] = raft_json_dict["raft_root_entry"][0]["term"]
            orig_commit_idx[p] = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            orig_newest_entry_term[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]
            orig_newest_entry_dsize[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"]
            orig_newest_entry_crc[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]
            
            state  = raft_json_dict["raft_root_entry"][0]["state"]
    
            if state == "follower":
                follower[fpeer] = peer_uuid[p]
                fpeer = fpeer + 1
        
        logging.warning("Leader uuid is: %s" % orig_leader_uuid[0])
        '''
        Pausing 1st follower for 10  sec
        '''
        logging.warning("Pausing follower uuid: %s" % follower[0])
        for p in range(npeer_start):
            if serverproc[p].process_uuid == follower[0]:
                proc_pause_id = p
                paused_peer_uuid = follower[0]
                break

        rc = serverproc[proc_pause_id].pause_process()
        if rc < 0:
            logging.error("Failed to pause the peer: %s" % serverproc[proc_pause_id].process_uuid)
            return 1

        logging.warning("Pausing follower for 10secs")
        time_global.sleep(10)

        '''
        To check if process is paused
        '''
        paused_peer_pid = serverproc[proc_pause_id].process_popen.pid
        ps = psutil.Process(paused_peer_pid)
        if ps.status() != "stopped":
            logging.error("Process for follower uuid : %s is not paused"% follower[0])
            return 1

        '''
        Read the JSON from leader and compare parameters:
        1. leader::raft_root_entry::follower-stats::last-ack has stopped
        ticking for the paused follower.
        2. leader::raft_root_entry::client-requests == deny-may-be-deposed -
        this means that the leader will not accept any requests from clients
        since it has lost contact with the quorum
        '''
        get_ctl[0] = CtlRequest(inotifyobj, "get_all", orig_leader_uuid[0],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply()

        raft_json_dict = genericcmdobj.raft_json_load(get_ctl[0].output_fpath)
        client_req =  raft_json_dict["raft_root_entry"][0]["client-requests"]
        last_ack = raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["last-ack"]
        if client_req != "deny-may-be-deposed":
            logging.error("client requests is not deny-may-be-deposed: %s" % client_req)
            return 1

        '''
        To check if last-ack for paused peer has stopped ticking.
        '''
        if last_ack != "Thu Jan 01 00:00:00 UTC 1970":
             logging.error("last-ack is not stopped ticking: %s" % last_ack)
             return 1

        '''
        Resuming the peer now
        '''
        logging.warning("Resume the peer ")

        rc = serverproc[proc_pause_id].resume_process()
        if rc < 0:
            logging.error("Failed to resume process")
            return 1

        '''
        To check if process is resumed
        '''
        paused_peer_pid = serverproc[proc_pause_id].process_popen.pid
        ps = psutil.Process(paused_peer_pid)
        if ps.status() != "running":
            logging.error("Process for follower uuid : %s is not running"% follower[0])
            return 1

        for i in range(npeer_start):
            get_ctl[i] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[i],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply()
        for i in range(npeer_start):
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[i].output_fpath)
            peer_uuid[p] = raft_json_dict["raft_root_entry"][0]["peer-uuid"]
            leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            voted_for_uuid[p] = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
            term[p] = raft_json_dict["raft_root_entry"][0]["term"]
            commit_idx[p] = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            newest_entry_term[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]
            newest_entry_dsize[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"]
            newest_entry_crc[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]
            
        '''
        Unpause Case #1:   The unpaused follower immediately becomes the leader
        '''
        if paused_peer_uuid == leader_uuid[0] and term[0] == orig_term[0] + 1:
            logging.warning("Unpaused Case 1: Paused peer uuid became Leader: %s" % paused_peer_uuid)
            if term[p] != orig_term[p] + 1:
                logging.error("Current term (%d) is not orig term(%d) + 1" % (term[p], orig_term[p]))
                return 1
            if newest_entry_term[p] != term[p]:
                logging.error("Newest entry term (%d) is not same as term(%d)" % (newest_entry_term[p], term[p]))
                return 1
            if orig_newest_entry_crc[p] != newest_entry_crc[p]:
                logging.error("Current newest entry crc (%d) is not orig_newest_entry_crc(%d)" % (newest_entry_crc[p], orig_newest_entry_crc[p]))
                return 1

        '''
        Unpause Case #2: The unpaused follower started an election cycle but
        did not win or did not win immediately.
        Paused peer started the election
        '''
        if voted_for_uuid[proc_pause_id] == peer_uuid[proc_pause_id]:
            logging.warning("Unpaused Case 2: Unpaused follower started the election.")
            if term[p] != orig_term[p] + 1:
                logging.error("Current term (%d) is not orig term(%d) + 1" % (term[p], orig_term[p]))
                return 1
            if orig_newest_entry_crc[p] != newest_entry_crc[p]:
                logging.error("Current newest entry crc (%d) is not orig_newest_entry_crc(%d)" % (newest_entry_crc[p], orig_newest_entry_crc[p]))
                return 1
            if (newest_entry_term[p] >2) != True:
                logging.error("Newest entry term is not greater than 2")
                return 1

            '''
            Printing information from follower-stats for non-running peers
            '''
            if peer_uuid[p] != peer_uuid_arr[i]:
                last_ack = raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["last-ack"]
                next_idx =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["next-idx"]
                prev_idx_term =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["prev_idx_term"]

                logging.warning("last ack: {}".format(last_ack))
                logging.warning("next_idx: {}".format(next_idx))
                logging.warning("prev_idx_term : {}".format(prev_idx_term))

        '''
        Unpause Case #3: The original leader maintains leadership after the unpause. 
        '''
        if orig_leader_uuid[0] == leader_uuid[0]:
            logging.warning("Unpaused Case 3: Original leader maintains leadership after the pause")
            # Term, commit-idx, newest-entry-term and newest-entry-crc remains same as original values
            if term[p] != orig_term[p]:
                logging.error("Current term %d is not same as orig term %d" % (term[p], orig_term[p]))
                return 1
            if commit_idx[p] != orig_commit_idx[p]:
                logging.error("Current commit-idx %d is not same as orig commit-idx %d" % (commit_idx[p], orig_commit_idx[p]))
                return 1
            if newest_entry_term[p] != orig_newest_entry_term[p]:
                logging.error("Current newest-entry-term %d is not same as orig newest-entry-term %d" % (commit_idx[p], orig_commit_idx[p]))
                return 1
            if newest_entry_crc[p] != orig_newest_entry_crc[p]:
                logging.error("Current newest-entry-crc %d is not same as orig newest-entry-crc %d" % (commit_idx[p], orig_commit_idx[p]))
                return 1

            '''
            Printing information from follower-stats for non-running peers
            '''
        for i in peer_uuid_arr:
            state  = raft_json_dict["raft_root_entry"][0]["state"]
            if state == "leader":
                if peer_uuid[p] != peer_uuid_arr[i]:
                    last_ack = raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["last-ack"]
                    next_idx =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["next-idx"]
                    prev_idx_term =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["prev_idx_term"]

                    logging.warning("last ack: {}".format(last_ack))
                    logging.warning("next_idx: {}".format(next_idx))
                    logging.warning("prev_idx_term : {}".format(prev_idx_term))

        '''
        Pausing more than 1 follower :
        The number of followers to pause must be >= (num-running-peers - (N/2)
        so that quorum may not be made by the remaining running peers.
        '''
        logging.warning("Pausing more than 1 follower:")
        no_of_peers_to_be_paused = (npeer_start - int(raftconfobj.nservers / 2))
        for i in range(no_of_peers_to_be_paused):
             if serverproc[p].process_uuid == follower[i]:
                proc_pause_id = p
                paused_peer_uuid = follower[i]
             rc = serverproc[proc_pause_id].pause_process()
             if rc < 0:
                 logging.error("Failed to pause the peer: %s" % serverproc[proc_pause_id].process_uuid)
                 return 1

             logging.warning("Pausing follower for 10secs")
             time_global.sleep(10)
             '''
             To check if process is paused
             '''
             paused_peer_pid = serverproc[proc_pause_id].process_popen.pid
             ps = psutil.Process(paused_peer_pid)
             if ps.status() != "stopped":
                 logging.error("Process for follower uuid : %s is not paused"% paused_peer_uuid)
                 return 1

        '''
        Read the JSON from leader and compare parameters:
        1. leader::raft_root_entry::follower-stats::last-ack has stopped
        ticking for the paused follower.
        2. leader::raft_root_entry::client-requests == deny-may-be-deposed -
        this means that the leader will not accept any requests from clients
        since it has lost contact with the quorum
        '''
        get_ctl[0] = CtlRequest(inotifyobj, "get_all", orig_leader_uuid[0],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply()



        raft_json_dict = genericcmdobj.raft_json_load(get_ctl[0].output_fpath)
        client_req =  raft_json_dict["raft_root_entry"][0]["client-requests"]
        last_ack = raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["last-ack"]
        if client_req != "deny-may-be-deposed":
            logging.error("client requests is not deny-may-be-deposed: %s" % client_req)
            return 1

        '''
        To check if last-ack for paused peer has stopped ticking.
        '''
        if last_ack != "Thu Jan 01 00:00:00 UTC 1970":
             logging.error("last-ack is not stopped ticking: %s" % last_ack)
             return 1

        '''
        Resuming the followers in series
        '''
        for i in range(no_of_peers_to_be_paused):
             rc = serverproc[proc_pause_id].resume_process()
             if rc < 0:
                 logging.error("Failed to pause the peer: %s" % serverproc[proc_pause_id].process_uuid)
                 return 1

             '''
             To check if process is resumed
             '''
             paused_peer_pid = serverproc[proc_pause_id].process_popen.pid
             ps = psutil.Process(paused_peer_pid)
             if ps.status() != "running":
                 logging.error("Process for follower uuid : %s is not running"% paused_peer_uuid)
                 return 1

        for i in range(npeer_start):
            get_ctl[i] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[i],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply()


        for i in range(npeer_start):
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[i].output_fpath)
            peer_uuid[p] = raft_json_dict["raft_root_entry"][0]["peer-uuid"]
            leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            voted_for_uuid[p] = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
            term[p] = raft_json_dict["raft_root_entry"][0]["term"]
            commit_idx[p] = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            newest_entry_term[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]
            newest_entry_dsize[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"]
            newest_entry_crc[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]

        '''
        Unpause Case #1:   The unpaused follower immediately becomes the leader
        '''
        if paused_peer_uuid == leader_uuid[0] and term[0] == orig_term[0] + 1:
            logging.warning("Unpaused Case 1: Paused peer uuid became Leader: %s" % paused_peer_uuid)
            if term[p] != orig_term[p] + 1:
                logging.error("Current term (%d) is not orig term(%d) + 1" % (term[p], orig_term[p]))
                return 1
            if newest_entry_term[p] != term[p]:
                logging.error("Newest entry term (%d) is not same as term(%d)" % (newest_entry_term[p], term[p]))
                return 1
            if orig_newest_entry_crc[p] != newest_entry_crc[p]:
                logging.error("Current newest entry crc (%d) is not orig_newest_entry_crc(%d)" % (newest_entry_crc[p], orig_newest_entry_crc[p]))
                return 1
        '''
        Unpause Case #2: The unpaused follower started an election cycle but
        did not win or did not win immediately.
        Paused peer started the election
        '''
        if voted_for_uuid[proc_pause_id] == peer_uuid[proc_pause_id]:
            logging.warning("Unpaused Case 2: Unpaused follower started the election.")
            if term[p] != orig_term[p] + 1:
                logging.error("Current term (%d) is not orig term(%d) + 1" % (term[p], orig_term[p]))
                return 1
            if orig_newest_entry_crc[p] != newest_entry_crc[p]:
                logging.error("Current newest entry crc (%d) is not orig_newest_entry_crc(%d)" % (newest_entry_crc[p], orig_newest_entry_crc[p]))
                return 1
            if (newest_entry_term[p] >2) != True:
                logging.error("Newest entry term is not greater than 2")
                return 1

            '''
            Printing information from follower-stats for non-running peers
            '''
            if peer_uuid[p] != peer_uuid_arr[i]:
                last_ack = raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["last-ack"]
                next_idx =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["next-idx"]
                prev_idx_term =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["prev_idx_term"]

                logging.warning("last ack: {}".format(last_ack))
                logging.warning("next_idx: {}".format(next_idx))
                logging.warning("prev_idx_term : {}".format(prev_idx_term))
        '''
        Unpause Case #3: The original leader maintains leadership after the unpause.
        '''
        if orig_leader_uuid[0] == leader_uuid[0]:
            logging.warning("Unpaused Case 3: Original leader maintains leadership after the pause")
            # Term, commit-idx, newest-entry-term and newest-entry-crc remains same as original values
            if term[p] != orig_term[p]:
                logging.error("Current term %d is not same as orig term %d" % (term[p], orig_term[p]))
                return 1
            if commit_idx[p] != orig_commit_idx[p]:
                logging.error("Current commit-idx %d is not same as orig commit-idx %d" % (commit_idx[p], orig_commit_idx[p]))
                return 1
            if newest_entry_term[p] != orig_newest_entry_term[p]:
                logging.error("Current newest-entry-term %d is not same as orig newest-entry-term %d" % (commit_idx[p], orig_commit_idx[p]))
                return 1
            if newest_entry_crc[p] != orig_newest_entry_crc[p]:
                logging.error("Current newest-entry-crc %d is not same as orig newest-entry-crc %d" % (commit_idx[p], orig_commit_idx[p]))
                return 1

            '''
            Printing information from follower-stats for non-running peers
            '''
        for i in peer_uuid_arr:
            state  = raft_json_dict["raft_root_entry"][0]["state"]
            if state == "leader":
                if peer_uuid[p] != peer_uuid_arr[i]:
                    last_ack = raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["last-ack"]
                    next_idx =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["next-idx"]
                    prev_idx_term =  raft_json_dict["raft_root_entry"][0]["follower-stats"][0]["prev_idx_term"]

                    logging.warning("last ack: {}".format(last_ack))
                    logging.warning("next_idx: {}".format(next_idx))
                    logging.warning("prev_idx_term : {}".format(prev_idx_term))

    def post_run(self, clusterobj):
        logging.warning("Post run method")
        '''
        Delete all the input and output files this recipe has written.
        '''
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()
