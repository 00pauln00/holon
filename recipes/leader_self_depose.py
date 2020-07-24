from holonrecipe import *
import logging
import psutil

def verify_follower_stat_for_non_running_peers(leader_json, raftconf, nstarted):
    for p in range(raftconf.nservers - 1):
        follower_peer_uuid = leader_json["raft_root_entry"][0]["follower-stats"][p]["peer-uuid"]

        for n in range(nstarted, raftconf.nservers):
            if follower_peer_uuid == raftconf.peer_uuid_arr[n]:
                logging.warning("Checking non-running peers parameter: %s" % follower_peer_uuid)
                last_ack = leader_json["raft_root_entry"][0]["follower-stats"][p]["last-ack"]
                if last_ack != "Thu Jan 01 00:00:00 UTC 1970":
                    logging.error("last_ack is %s not (Thu Jan 01 00:00:00 UTC 1970)" % last_ack)
                    return False
                next_idx = leader_json["raft_root_entry"][0]["follower-stats"][p]["next-idx"]
                if int(next_idx) < 1:
                    logging.error("next idx is not >= 1: %s" % next_idx)
                    return False
                prev_idx_term = leader_json["raft_root_entry"][0]["follower-stats"][p]["prev-idx-term"]
                if int(prev_idx_term) < 1:
                    logging.error("prev_idx_term  is not >= 1: %s" % prev_idx_term)
                    return False

    return True


'''
The unpaused follower becomes leader.
'''
def leader_self_depose_case1(ctlreq_arr, raftconf, resume_peer_uuid, orig_term, nstarted):
    '''
    Create object for generic cmds.
    '''
    genericcmdobj = GenericCmds()

    leader_idx = 0
    for p in range(nstarted):
        if ctlreq_arr[p] == None:
            continue

        raft_json_dict = genericcmdobj.raft_json_load(ctlreq_arr[p])
        leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
        state = raft_json_dict["raft_root_entry"][0]["state"]
        if state == "leader":
            leader_idx = p

        voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
        term = raft_json_dict["raft_root_entry"][0]["term"]
        commit_idx = raft_json_dict["raft_root_entry"][0]["commit-idx"]
        newest_entry_term = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]
        newest_entry_dsize = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"]

        logging.warning("Check for case#1")
        logging.warning("leader_uuid: %s voted_for_uuid: %s resume_peer_uuid: %s" % (leader_uuid, voted_for_uuid, resume_peer_uuid))
        logging.warning("Term: %d orig term: %d" % (term, orig_term[p]))
        logging.warning("newest_entry_term: %d, newest_entry_data_size: %d" % (newest_entry_term, newest_entry_dsize))
        if leader_uuid != resume_peer_uuid or voted_for_uuid != resume_peer_uuid:
            return False

        if term != (orig_term[p] + 1):
            return False

        if newest_entry_dsize != 0:
            return False

    leader_json = genericcmdobj.raft_json_load(ctlreq_arr[leader_idx])
    case_occurred = verify_follower_stat_for_non_running_peers(leader_json, raftconf, nstarted)
    return case_occurred

'''
Unpaused follower started the election, but did not win or did not win immediately.
'''
def leader_self_depose_case2(ctlreq_arr, raftconf, resume_peer_uuid, orig_term, nstarted):
    case2_occurred = False
    '''
    Create object for generic cmds.
    '''
    genericcmdobj = GenericCmds()

    for p in range(nstarted):
        if ctlreq_arr[p] == None:
            continue

        raft_json_dict = genericcmdobj.raft_json_load(ctlreq_arr[p])
        state = raft_json_dict["raft_root_entry"][0]["state"]
        if state == "leader":
            leader_idx = p

        peer_uuid = raft_json_dict["raft_root_entry"][0]["peer-uuid"]
        if peer_uuid != resume_peer_uuid:
            continue

        # Get the values for unpaused follower only
        leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
        voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
        term = raft_json_dict["raft_root_entry"][0]["term"]
        logging.warning("Check case#2")
        logging.warning("leader_uuid: %s voted_for_uuid: %s" % (leader_uuid, voted_for_uuid))
        logging.warning("term: %d, orig term: %d" % (term, orig_term[p]))

        if leader_uuid == resume_peer_uuid or voted_for_uuid == resume_peer_uuid:
            if term >= (orig_term[p] + 2):
                case2_occurred =  True

        break

    if case2_occurred:
        leader_json = genericcmdobj.raft_json_load(ctlreq_arr[leader_idx])
        case2_occurred = verify_follower_stat_for_non_running_peers(leader_json, raftconf, nstarted)
    
    return case2_occurred
 
'''
original leader maintains the leadership after the pause.
'''
def leader_self_depose_case3(ctlreq_arr, orig_leader, orig_term, nstarted):
    '''
    Create object for generic cmds.
    '''
    logging.warning("Checking case#3")
    genericcmdobj = GenericCmds()

    for p in range(nstarted):
        if ctlreq_arr[p] == None:
            continue

        raft_json_dict = genericcmdobj.raft_json_load(ctlreq_arr[p])
        leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]

        voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
        term = raft_json_dict["raft_root_entry"][0]["term"]

        logging.warning("leader uuid: %s orig leader: %s" % (leader_uuid, orig_leader))
        logging.warning("term %d, orig term: %d" % (term, orig_term[p]))
        if leader_uuid != orig_leader:
            return False

        # Original leader remains the leader after unpause
        if term != orig_term[p]:
            return False

    return True


'''
Leader Self depose recipe
'''
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
        orig_state = {}
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
        paused_follower_uuid = {}

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
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output 
        '''
        get_ctl = [None] * npeer_start

        for p in range(npeer_start):
            get_ctl[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p], genericcmdobj,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        orig_follower_last_ack ={}
        fpeer = 0

        for p in range(npeer_start):
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[p])
            peer_uuid[p] = raft_json_dict["raft_root_entry"][0]["peer-uuid"]
            orig_leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            orig_term[p] = raft_json_dict["raft_root_entry"][0]["term"]
            orig_commit_idx[p] = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            orig_newest_entry_term[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]
            orig_newest_entry_dsize[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"]
            orig_newest_entry_crc[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]
            orig_state[p]  = raft_json_dict["raft_root_entry"][0]["state"]

            if orig_state[p] == "leader":
                # Get the follower stat.
                for p in range(raftconfobj.nservers - 1):
                    follower_peer_uuid = raft_json_dict["raft_root_entry"][0]["follower-stats"][p]["peer-uuid"]
                    orig_follower_last_ack[follower_peer_uuid] = raft_json_dict["raft_root_entry"][0]["follower-stats"][p]["last-ack"]
    
        logging.warning("Leader uuid is: %s" % orig_leader_uuid[0])

        '''
        Pausing 1 or more follower for 10  sec.
        Number of followers to pause must be >= (num-running-peers - (N/2)).
        '''
        nfollower_paused = (npeer_start - int(raftconfobj.nservers / 2))
        if nfollower_paused == 1 and npeer_start > 2:
            nfollower_paused = nfollower_paused + 1

        logging.warning("Number of followers to pause %d" % nfollower_paused)
        f = 0
        for p in range(npeer_start):
            if orig_state[p] == "follower":
                logging.warning("Pausing peer uuid: %s" % serverproc[p].process_uuid)
                rc = serverproc[p].pause_process()
                if rc < 0:
                    logging.error("Failed to pause the peer: %s" % serverproc[p].process_uuid)
                    return 1

                '''
                To check if process is paused
                '''
                paused_peer_pid = serverproc[p].process_popen.pid
                ps = psutil.Process(paused_peer_pid)
                if ps.status() != "stopped":
                    logging.error("Process for follower uuid : %s is not paused"% serverproc[p].process_uuid)
                    return 1

                paused_peer_uuid = serverproc[p].process_uuid
                paused_follower_uuid[p] = paused_peer_uuid
                f += 1
                if f >= nfollower_paused:
                    break



        '''
        Read the JSON from leader and compare parameters:
        1. leader::raft_root_entry::follower-stats::last-ack has stopped
        ticking for the paused follower.
        2. leader::raft_root_entry::client-requests == deny-may-be-deposed -
        this means that the leader will not accept any requests from clients
        since it has lost contact with the quorum
        '''
        retry = 0
        while retry < 5:
            rc = 0
            get_ctl[0] = CtlRequest(inotifyobj, "get_all", orig_leader_uuid[0], genericcmdobj,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
            raft_json_dict = genericcmdobj.raft_json_load(get_ctl[0])
            client_req =  raft_json_dict["raft_root_entry"][0]["client-requests"]
            if client_req != "deny-may-be-deposed":
                logging.warning("client req changed to deny-may-be-deposed!")
                break

            logging.warning("client requests is not deny-may-be-deposed yet, retry: %s" % client_req)
            rc = 1
            time_global.sleep(1)
            retry += 1

        if rc == 1:
            logging.error("client req is still not deny-may-depose")
            return 1

        '''
        Iterate over follower stat and for paused followers check the last-ack
        '''
        for p in range(raftconfobj.nservers - 1):
            follower_peer_uuid = raft_json_dict["raft_root_entry"][0]["follower-stats"][p]["peer-uuid"]
            for f in paused_follower_uuid:
                if follower_peer_uuid == paused_follower_uuid[f]:
                    curr_last_ack = raft_json_dict["raft_root_entry"][0]["follower-stats"][p]["last-ack"]
                    '''
                    To check if last-ack for paused peer has stopped ticking.
                    '''
                    #TODO compare time stamp.
                    orig_last_ack = orig_follower_last_ack[follower_peer_uuid]
                    time_string = orig_last_ack.split()
                    time = time_string[3]
                    orig_last_ack_time = datetime.strptime(time, "%H:%M:%S")

                    logging.warning("orig_last_ack : %s" % orig_last_ack_time)

                    time_string = curr_last_ack.split()
                    time = time_string[3]
                    curr_last_ack_time = datetime.strptime(time, "%H:%M:%S")
                    logging.warning("curr last ack: %s" % curr_last_ack_time)

                    time_diff = curr_last_ack_time - orig_last_ack_time
                    time_diff_in_sec = time_diff.total_seconds()
                    logging.warning("time difference is %d" % time_diff_in_sec)
                    # As follower was paused for 10sec, we should not see last-ack difference
                    # more than 2sec
                    if time_diff_in_sec > 5:
                        logging.error("last-ack has not stopped ticking: curr :%s, orig: %s" % (curr_last_ack, orig_last_ack))
                        return 1

        '''
        Resuming the paused peers now
        '''
        logging.warning("Resume the peer one at a time")

        unpause_case1_occurred = False
        unpause_case2_occurred = False
        for p in paused_follower_uuid:

            logging.warning("paused follower_uuid: %s, %d" % (paused_follower_uuid[p], p))
            resume_peer_uuid = paused_follower_uuid[p]
            logging.warning("Resumeing peer uuid: %s" % resume_peer_uuid)
            rc = serverproc[p].resume_process()
            if rc < 0:
                logging.error("Failed to resume process")
                return 1

            # Modify peer entry from paused_follower_uuid dictionary
            paused_follower_uuid[p] = "INVALID_UUID"

            # Sleep for 5sec to allow any new election to happen after unpausing.
            time_global.sleep(5)

            '''
            After resume of peer, check which unpause case observed.
            '''
            for i in range(npeer_start):
                # Dont send cmd to paused peers or non-running peers.
                if paused_follower_uuid.get(i) != None and paused_follower_uuid[i] == peer_uuid_arr[i]:
                    get_ctl[i] = None
                    continue

                get_ctl[i] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[i], genericcmdobj,
                                        inotify_input_base.REGULAR,
                                        self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
            '''
            Check if this is Unpause case 1
            The unpaused follower immediately becomes the leader
            '''
            rc = leader_self_depose_case1(get_ctl, raftconfobj, resume_peer_uuid, orig_term, npeer_start)
            if rc == True:
                logging.warning("Unpause case#1 occurred after pausing peer %s" % resume_peer_uuid)
                if unpause_case1_occurred == True:
                    logging.error("Unpase case#1 should not occur twice")
                    return 1

                # Mark unpause case1 occurred.
                unpause_case1_occurred = True
                continue

            '''
            Unpause Case #2: The unpaused follower started an election cycle but
            did not win or did not win immediately.
            Paused peer started the election
            '''
            rc = leader_self_depose_case2(get_ctl, raftconfobj, resume_peer_uuid, orig_term, npeer_start)
            if rc == True:
                logging.warning("Unpause case#2 occurred after pausing peer %s" % resume_peer_uuid)
                if unpause_case2_occurred == True:
                    logging.error("Unpase case#2 should not occur twice")
                    return 1

                # Mark unpause case1 occurred.
                unpause_case2_occurred = True
                continue

            '''
            Unpause Case #3: The original leader maintains leadership after the unpause. 
            '''
            rc = leader_self_depose_case3(get_ctl, orig_leader_uuid[0], orig_term, npeer_start)
            if rc == True:
                logging.warning("Unpause case#3 occurred after pausing peer %s" % resume_peer_uuid)
                continue

            logging.error("None of the unpause cases occur!")
            return 1

        '''
        Make sure all paused processes are resumed
        '''
    def post_run(self, clusterobj):
        logging.warning("Post run method")
        '''
        Delete all the input and output files this recipe has written.
        '''
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()
