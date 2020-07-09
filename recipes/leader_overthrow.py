from holonrecipe import *
import logging 

class Recipe(HolonRecipeBase):
    name = "leader_overthrow"
    desc = "Leader Overthrow\n"\
            "Leader overthrow is a way of deposing a functional leader by\n"\
            "causing that leader’s network requests to be ignored.\n"\
            "This recipe is a descendant of Basic Leader Election\n"\
            "1. Disable Msg Recv on all Peers\n"\
            "2. Enable Recv on all Peers from the Leader-to-be\n"\
            "3. Enable Recv from all Peers on the Leader-to-be\n"\
            "4. Finalize recipe with enabling recv on all peers\n"
    parent = "basic_leader_election"
    recipe_ctl_req_obj_list = []

    def print_desc(self):
        print(self.desc)

    def pre_run(self):
        return self.parent

    def run(self, clusterobj):
        logging.warning("================ Run Leader Overthrow ==================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        npeer = int(raftconfobj.nservers / 2) + 1
        peer_uuid_arr = {}

        for p in range(npeer):
            peer_uuid_arr[p] = raftconfobj.get_peer_uuid_for_peerno(p)
       
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
        get_all = [None] * npeer
        idle_off = [None] * npeer
        net_rcv_false = [None] * npeer
        new_uuid = [None] * npeer
        net_rcv_true = [None] * npeer
        orig_raftjsonobj = [None] * npeer
        rcv_false_raftjson = [None] * npeer
        set_leader_raftjson = [None] * npeer
        raftjsonobj = [None] * npeer

        #Verify the parameters
        leader_to_be = -1
        LEADER_ELECTION_TIME_OUT = 300 #5mins
       
        recipe_failed = 0
        '''
        Make sure none of the peer is in idle state
        '''
        for p in range(npeer):
            idle_off[0] = CtlRequest(inotifyobj, "idle_off", peer_uuid_arr[0],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        '''
        Get the parameter of basic leader election
        to compare with New leader-to-be
        '''

        for p in range(npeer):    
            get_all[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
           
            orig_raftjsonobj[p] = RaftJson(get_all[p].output_fpath, raftconfobj)
            if orig_raftjsonobj[p].state == "follower" and leader_to_be == -1:
                logging.warning("New leader-to-be is peer: %d and uuid: %s" % (p, peer_uuid_arr[p]))
                leader_to_be = p

        '''
        Copy the cmd file for Disable the net_recv_enable on all
        peers and verify that net_recv_enable is set to false.
        '''
        logging.warning("Stage 1: Disable message receive on all peers")
        for p in range(npeer): 
            #Copy the cmd file for Disable the net_recv_enable
            net_rcv_false[p] = CtlRequest(inotifyobj, "rcv_false", peer_uuid_arr[p],
                                          app_uuid,
                                          inotify_input_base.REGULAR,
                                          self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        time_global.sleep(3)

        '''
        Verify if net_recv_enable is set to false for all peers.
        '''
        for p in range(npeer):

            #Copy cmdfile to get the JSON output 
            get_all[p].Apply_and_Wait(False)

            rcv_false_raftjson[p] = RaftJson(get_all[p].output_fpath, raftconfobj)
            peer_uuid = peer_uuid_arr[p]
            if rcv_false_raftjson[p].net_rcv_enabled[peer_uuid] != False:
                logging.error("net_rcv_enable is not set to false(%s) for peer %s" % (rcv_false_raftjson[p].net_recv_enable, p))
                recipe_failed = 1
                break

            if rcv_false_raftjson[p].leader_uuid != orig_raftjsonobj[p].leader_uuid:
                logging.error("New leader election happened, original leader: %s, new leader: %s" %
                        (orig_raftjsonobj[p].leader_uuid, rcv_false_raftjson[p].leader_uuid))
                recipe_failed = 1
                break

            if rcv_false_raftjson[p].state != "candidate" and rcv_false_raftjson[p].state != "leader":
                logging.error(f"peer state %s for peer-uuid %s" % (rcv_false_raftjson[p].state, peer_uuid_arr[p]))
                logging.error("peer %s state is not candidate" % p)
                recipe_failed = 1
                break

            if rcv_false_raftjson[p].state == "candidate":
                if rcv_false_raftjson[p].term <= orig_raftjsonobj[p].term:
                    logging.error("term value of previous follower is not increasing")
                    recipe_failed = 1
                    break

                if rcv_false_raftjson[p].client_req != "deny-leader-not-established":
                    logging.error("client_requests is not deny-leader-not-established: %s" % rcv_false_raftjson[p].client_req)
                    recipe_failed = 1
                    break

            elif rcv_false_raftjson[p].state == "leader":
                if rcv_false_raftjson[p].term != orig_raftjsonobj[p].term:
                    logging.error("term value of leader changed: orig %d, new: %d" % (orig_raftjsonobj[p].term, rcv_false_raftjson[p].term))
                    recipe_failed = 1
                    break

                if rcv_false_raftjson[p].client_req != "deny-may-be-deposed":
                    logging.error("client_requests is not deny-may-be-deposed: %s" % rcv_false_raftjson[p].client_req)
                    recipe_failed = 1
                    break

        if recipe_failed:
            logging.error("Stage 1 of leader overthrow failed")
            return recipe_failed

        logging.warning("Stage 1 successful, net_recv_enabled is false on all peers")

        '''
        Copy the cmd for "Enable Recv on all Peers from the Leader-to-be"
        verify the new value by comparing with original values.
        '''
        logging.warning("Stage 2: Enable receive on all Peers from the Leader-to-be")
        for p in range(npeer): 
            #Copy new leader-to-be cmd file. Use first follower as leader-to-be
            CtlRequest(inotifyobj, "set_leader_uuid", peer_uuid_arr[p],
                                  app_uuid,
                                  inotify_input_base.REGULAR,
                                  self.recipe_ctl_req_obj_list).set_leader(peer_uuid_arr[leader_to_be])
        time_global.sleep(3)

        '''
        Verify receive enable to the peer which is to be appointed as leader for
        all peers.
        '''
        logging.warning("Verify receive enable on the peer which is to be appointed as leader")
        for p in range(npeer):

            #Copy ctlrequest cmd file to get JSON output
            get_all[p].Apply_and_Wait(False)

            set_leader_raftjson[p] = RaftJson(get_all[p].output_fpath, raftconfobj)
            '''
            Make sure following item values are consistent and leader-election
            has not happened yet.
            '''
            if set_leader_raftjson[p].leader_uuid != orig_raftjsonobj[p].leader_uuid:
                logging.error("New leader election happened, original leader: %s, new leader: %s" %
                        (orig_raftjsonobj[p].leader_uuid, set_leader_raftjsonj[p].leader_uuid))
                recipe_failed = 1
                break

            if set_leader_raftjson[p].commit_idx != orig_raftjsonobj[p].commit_idx:
                logging.error("commit indx changed. Original: %d, new: %d" % (orig_raftjsonobj[p].commit_idx, set_leader_raftjson[p].commit_idx))
                recipe_failed
                break

            if set_leader_raftjson[p].last_applied != orig_raftjsonobj[p].last_applied:
                logging.error("last-applied changed: original: %d, new: %d" % (orig_raftjsonobj[p].last_applied, set_leader_raftjson[p].last_applied))
                recipe_failed = 1
                break

            if set_leader_raftjson[p].cumu_crc != orig_raftjsonobj[p].cumu_crc:
                logging.error("last-applied-cumulative-crc changed: original: %d, new: %d" % (orig_raftjsonobj[p].cumu_crc, set_leader_raftjson[p].cumu_crc))
                recipe_failed = 1
                break

            if set_leader_raftjson[p].newest_entry_idx != set_leader_raftjson[p].newest_entry_idx:
                logging.error("newest-entry-idx changed. Original: %d, new: %d" % (orig_raftjsonobj[p].newest_entry_idx, set_leader_raftjson[p].newest_entry_idx))
                recipe_failed = 1
                break

            if set_leader_raftjson[p].newest_entry_term != orig_raftjsonobj[p].newest_entry_term:
                logging.error("newest-entry-term changed. Original: %d, new: %d" % (orig_raftjsonobj[p].newest_entry_term, set_leader_raftjson[p].newest_entry_term))
                recipe_failed = 1
                break

            if set_leader_raftjson[p].newest_entry_dsize != orig_raftjsonobj[p].newest_entry_dsize:
                logging.error("newest-entry-data-size changed. Original: %d, new: %d" % (orig_raftjsonobj[p].newest_entry_dsize, set_leader_raftjson[p].newest_entry_dsize))
                recipe_failed = 1
                break

            if set_leader_raftjson[p].newest_entry_crc != orig_raftjsonobj[p].newest_entry_crc:
                logging.error("newest-entry-crc changed. Original: %d, new: %d" % (orig_raftjsonobj[p].newest_entry_crc, set_leader_raftjson[p].newest_entry_crc))
                recipe_failed = 1
                break

            if set_leader_raftjson[p].voted_for_uuid != set_leader_raftjson[p].peer_uuid:
                logging.error("voted_for_uuid is not same as self uuid")
                logging.error("voted_for_uuid: %s, self uuid: %s" % (set_leader_raftjson[p].voted_for_uuid, set_leader_raftjson[p].peer_uuid))
                recipe_failed = 1
                break
            
            if set_leader_raftjson[p].client_req != "deny-leader-not-established":
                logging.error("client_requests is not deny-leader-not-established: %s" % set_leader_raftjson[p].client_req)
                recipe_failed = 1
                break

            if set_leader_raftjson[p].term <= orig_raftjsonobj[p].term:
                    logging.error("term value of previous follower is not increasing")
                    recipe_failed = 1
                    break

            if set_leader_raftjson[p].state != "candidate":
                logging.error("peer state is wrong: %s" % set_leader_raftjson[p].state)
                recipe_failed = 1
                break

        if recipe_failed:
            logging.error("Stage 2 of Leader overthrow failed")
            return recipe_failed

        '''
        Enable the net_rcv on peer UUID-of-leader-to-be.
        The cmd is copied only to UUID-of-leader-to-be.
        check net_rcv_enabled is set to true on UUID-of-leader-to-be.
        '''    
        logging.warning("Stage 3: Enable Recv from all Peers on the Leader-to-be")

        CtlRequest(inotifyobj, "rcv_true", peer_uuid_arr[leader_to_be],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

        logging.warning("New leader election may take time...")

        time_out = 0
        while 1:
            recipe_failed = 0

            get_all[leader_to_be].Apply_and_Wait(False)
            leader_json = RaftJson(get_all[leader_to_be].output_fpath, raftconfobj)
            
            if leader_json.voted_for_uuid != peer_uuid_arr[leader_to_be] or leader_json.leader_uuid != peer_uuid_arr[leader_to_be]:
                time_out = time_out + 10
                if time_out >= LEADER_ELECTION_TIME_OUT:
                    logging.error("Leader election failed")
                    recipe_failed = 1
                    break

                logging.warning("Leader election is not done yet!, retry")
                logging.warning("leader_uuid: %s, voted_for_uuid: %s" % (leader_json.leader_uuid, leader_json.voted_for_uuid))
                continue
            else:
                logging.warning("New leader elected successfuly %s" % leader_json.peer_uuid)
                break

        if recipe_failed:
            logging.error("Failed to elect new leader")
            return recipe_failed

        '''
        Copy get_all cmd to all the peers and make sure everyone selected the new leader
        '''
        for p in range(npeer):

            #Copy ctlrequest cmd file to get JSON output
            get_all[p].Apply_and_Wait(False)
            
            raftjsonobj[p] = RaftJson(get_all[p].output_fpath, raftconfobj)
        
            if raftjsonobj[p].voted_for_uuid != peer_uuid_arr[leader_to_be] or raftjsonobj[p].leader_uuid != peer_uuid_arr[leader_to_be]:
                logging.error("New leader is not elected by peer: %d" % peer_uuid_arr[p])
                recipe_failed = 1
                break

            # commit idx should be pre-state1 value + 1
            if raftjsonobj[p].commit_idx != orig_raftjsonobj[p].commit_idx + 1:
                logging.error("Current commit idx %d != orig commit indx + 1 %d" % (raftjsonobj[p].commit_idx, orig_raftjsonobj[p].commit_idx))
                recipe_failed = 1
                break

            # newest_entry_idx should be Pre-stage1 value + 1
            if raftjsonobj[p].newest_entry_idx != orig_raftjsonobj[p].newest_entry_idx + 1:
                logging.error("Current newest_entry_idx %d != original + 1 %d" % (raftjsonobj[p].newest_entry_idx, orig_raftjsonobj[p].newest_entry_idx))
                recipe_failed = 1
                break

            # Term should be greater than pre-stage1. With multiple failed leader election, its value can
            # increase more than one.
            if raftjsonobj[p].term <= orig_raftjsonobj[p].term:
                logging.error("Current term %d is not greater than original %d" % (raftjsonobj[p].term, orig_raftjsonobj[p].term))
                recipe_failed = 1
                break

        if recipe_failed:
            logging.error("Stage 3 failed")
            return recipe_failed

        logging.warning(f"Stage 3 successful, all peers elected the new leader.")

        '''
        Finalization of recipe: The recipe should restore net_recv_enabled state to true on all peers.
        '''
        for p in range(npeer):
            net_rcv_true[p] = CtlRequest(inotifyobj, "rcv_true", peer_uuid_arr[p],
                                         app_uuid,
                                         inotify_input_base.REGULAR,
                                         self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

            #Copy ctlrequest cmd file to get JSON output
            get_all[p].Apply_and_Wait(False)
            raftjsonobj[p] = RaftJson(get_all[p].output_fpath, raftconfobj)

            peer_uuid = peer_uuid_arr[p]
            if raftjsonobj[p].net_rcv_enabled[peer_uuid] != True:
                logging.error("net_recv_enable is not set to true for peer %s" % peer_uuid_arr[p])
                recipe_failed = 1
                break

        if recipe_failed:
            logging.error("Finalization of recipe failed")
            return recipe_failed

        logging.warning("Recipe finalization successful")
        return 0
 
    def post_run(self, clusterobj):
        logging.warning("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()
