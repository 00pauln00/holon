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
        net_rcv_false = [None] * npeer
        new_uuid = [None] * npeer
        net_rcv_true = [None] * npeer

        #Verify the parameters
        original_leader_uuid = {}
        original_state = {}
        original_term = {}
        original_commit_idx = {}
        original_last_applied = {}
        original_cumu_crc = {}
        original_newest_entry_idx = {}
        original_newest_entry_term = {}
        original_newest_entry_dsize = {}
        original_newest_entry_crc = {}
        leader_to_be = -1
        LEADER_ELECTION_TIME_OUT = 300 #5mins
       
        '''
        Get the parameter of basic leader election
        to compare with New leader-to-be
        '''
        recipe_failed = 0
        for p in range(npeer):
            get_all[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply()
         
            raft_json_dict = genericcmdobj.raft_json_load(get_all[p].output_fpath)
            peer_uuid = raft_json_dict["raft_root_entry"][0]["peer-uuid"]
            if peer_uuid != peer_uuid_arr[p]:
                logging.error("Peer uuid %s is different, expected: %s" % (peer_uuid, peer_uuid_arr[p]))
            logging.warning(f"peer-uuid for peer: %d is: %s" % (p, peer_uuid))

            original_leader_uuid[p] = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            logging.warning(f"Original Leader UUID is: %s" % original_leader_uuid[p])

            if p > 0 and original_leader_uuid[p] != original_leader_uuid[p - 1]:
                logging.error("leader for peer %s is different than peer %s") % (peer_uuid, peer_uuid_arr[p - 1])
                recipe_failed = 1
                break

            voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
            if voted_for_uuid != original_leader_uuid[p]:
                logging.error("voted-for-uuid %s is not same as leader %s" % (voted_for_uuid, original_leader_uuid[p]))
                recipe_failed = 1
                break

            original_state[p] = raft_json_dict["raft_root_entry"][0]["state"]
            logging.warning(f"State is: %s" % original_state[p])

            if original_state[p] == "follower" and leader_to_be == -1:
                logging.warning("peer: %d is leader_to_be" % p)
                leader_to_be = p

            original_commit_idx[p] = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            logging.warning(f"Original commit-idx: %d" % original_commit_idx[p])
            
            original_last_applied[p] = raft_json_dict["raft_root_entry"][0]["last-applied"]
            logging.warning(f"Original last-applied: %d" % original_last_applied[p])

            original_cumu_crc[p] = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]
            logging.warning(f"Original last-applied-cumulative-crc: %d" % original_cumu_crc[p])
            
            original_newest_entry_idx[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-idx"]
            logging.warning(f"Original newest_entry_idx: %d" % original_newest_entry_idx[p])

            original_newest_entry_term[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]
            logging.warning(f"Original newest_entry_term: %d" % original_newest_entry_term[p])

            original_newest_entry_dsize[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"]
            logging.warning(f"Original newest_entry_data_size: %d" % original_newest_entry_dsize[p])

            original_newest_entry_crc[p] = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]
            logging.warning(f"Original newest_entry_crc: %d" % original_newest_entry_crc[p])

            original_term[p] = raft_json_dict["raft_root_entry"][0]["term"]
            logging.warning(f"Original Term: %s" % original_term[p])
        
        '''
        Copy the cmd file for Disable the net_recv_enable on all
        peers and verify that net_recv_enable is set to false.
        '''
        logging.warning("Stage 1:")
        logging.warning("Disable message receive on all peers")
        for p in range(npeer): 
            #Copy the cmd file for Disable the net_recv_enable
            net_rcv_false[p] = CtlRequest(inotifyobj, "rcv_false", peer_uuid_arr[p],
                                          app_uuid,
                                          inotify_input_base.REGULAR,
                                          self.recipe_ctl_req_obj_list).Apply()
        
        time_global.sleep(5)

        '''
        Verify if net_recv_enable is set to false for all peers.
        '''
        for p in range(npeer):

            #Copy cmdfile to get the JSON output 
            ctl_req_create_cmdfile_and_copy(get_all[p])

            time_global.sleep(5)

            raft_json_dict = genericcmdobj.raft_json_load(get_all[p].output_fpath)
            net_recv_enable = raft_json_dict["ctl_svc_nodes"][1]["net_recv_enabled"]
            if net_recv_enable != False:
                logging.error("net_rcv_enable is not set to false(%s) for peer %s" % (net_recv_enable, p))
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
        logging.warning("Stage 2:")
        logging.warning("Enable receive on all Peers from the Leader-to-be")
        for p in range(npeer): 
            #Copy new leader-to-be cmd file. Use first follower as leader-to-be
            CtlRequest(inotifyobj, "set_leader_uuid", peer_uuid_arr[p],
                                  app_uuid,
                                  inotify_input_base.REGULAR,
                                  self.recipe_ctl_req_obj_list).set_leader(peer_uuid_arr[leader_to_be])

        time_global.sleep(5)

        '''
        Verify receive enable to the peer which is to be appointed as leader for
        all peers.
        '''
        logging.warning("Verify receive enable to the peer which is to be appointed as leader")
        for p in range(npeer):

            #Copy ctlrequest cmd file to get JSON output
            ctl_req_create_cmdfile_and_copy(get_all[p])
            time_global.sleep(2)

            raft_json_dict = genericcmdobj.raft_json_load(get_all[p].output_fpath)

            '''
            Make sure following item values are consistent and leader-election
            has not happened yet.
            '''
            self_uuid = raft_json_dict["raft_root_entry"][0]["peer-uuid"]

            leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            if leader_uuid != original_leader_uuid[p]:
                logging.error("New leader election happened, original leader: %s, new leader: %s" %
                        (original_leader[p], leader_uuid))
                recipe_failed = 1
                break

            commit_idx = raft_json_dict["raft_root_entry"][0]["commit-idx"] 
            if commit_idx != original_commit_idx[p]:
                logging.error("commit indx changed. Original: %d, new: %d" % (original_commit_idx[p], commit_idx))
                recipe_failed
                break

            last_applied = raft_json_dict["raft_root_entry"][0]["last-applied"] 
            if last_applied != original_last_applied[p]:
                logging.error("last-applied changed: original: %d, new: %d" % (original_last_applied[p], last_applied))
                recipe_failed = 1
                break

            last_app_cumu_crc = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]
            if last_app_cumu_crc != original_cumu_crc[p]:
                logging.error("last-applied-cumulative-crc changed: original: %d, new: %d" % (original_cumu_crc[p], last_app_cumu_crc))
                recipe_failed = 1
                break

            newest_entry_idx = raft_json_dict["raft_root_entry"][0]["newest-entry-idx"]
            if newest_entry_idx != original_newest_entry_idx[p]:
                logging.error("newest-entry-idx changed. Original: %d, new: %d" % (original_newest_entry_idx[p], newest_entry_idx))
                recipe_failed = 1
                break

            newest_entry_term = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]
            if newest_entry_term != original_newest_entry_term[p]:
                logging.error("newest-entry-term changed. Original: %d, new: %d" % (original_newest_entry_term[p], newest_entry_term))
                recipe_failed = 1
                break

            newest_entry_dsize = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"]
            if newest_entry_dsize != original_newest_entry_dsize[p]:
                logging.error("newest-entry-data-size changed. Original: %d, new: %d" % (original_newest_entry_dsize[p], newest_entry_dsize))
                recipe_failed = 1
                break

            newest_entry_crc = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]
            if newest_entry_crc != original_newest_entry_crc[p]:
                logging.error("newest-entry-crc changed. Original: %d, new: %d" % (original_newest_entry_crc[p], newest_entry_crc))
                recipe_failed = 1
                break

            voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
            if self_uuid != voted_for_uuid:
                logging.error("voted_for_uuid is not same as self uuid")
                logging.error("voted_for_uuid: %s, self uuid: %s" % (voted_for_uuid, self_uuid))
                recipe_failed = 1
                break

            client_req = raft_json_dict["raft_root_entry"][0]["client-requests"]
            term = raft_json_dict["raft_root_entry"][0]["term"]

            state = raft_json_dict["raft_root_entry"][0]["state"]
            if state != "leader" or state != "candidate":
                logging.error("peer state is wrong: %s" % state)
                recipe_failed = 1
                break

            if state == "candidate":
                if term <= original_term[p]:
                    logging.error("term value of previous follower is not increasing")
                    recipe_failed = 1
                    break

                if client_req != "deny-leader-not-established":
                    logging.error("client_requests is not deny-leader-not-established: %s" % client_req)
                    recipe_failed = 1
                    break

            elif state == "leader":
                if term != original_term[p]:
                    logging.error("term value of leader changed: orig %d, new: %d" % (original_term[p], term))
                    recipe_failed = 1
                    break

                if client_req != "deny-may-be-deposed":
                    logging.error("client_requests is not deny-may-be-deposed: %s" % client_req)
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
        logging.warning("Stage 3:")
        logging.warning("Enable Recv from all Peers on the Leader-to-be")

        CtlRequest(inotifyobj, "rcv_true", peer_uuid_arr[leader_to_be],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply()
        time_global.sleep(5)

        logging.warning("New leader election may take time")

        time_out = 0
        while 1:
            recipe_failed = 0

            ctl_req_create_cmdfile_and_copy(get_all[leader_to_be])
            time_global.sleep(5)

            raft_json_dict = genericcmdobj.raft_json_load(get_all[leader_to_be].output_fpath)

            voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
            leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            if voted_for_uuid != peer_uuid_arr[leader_to_be] or leader_uuid != peer_uuid_arr[leader_to_be]:
                time_out = time_out + 10
                if time_out >= LEADER_ELECTION_TIME_OUT:
                    logging.error("Leader election failed")
                    recipe_failed = 1
                    break
                logging.warning("Leader election is not done yet!, retry")
                logging.warning("leader_uuid: %s, voted_for_uuid: %s" % (leader_uuid, voted_for_uuid))
                continue
            else:
                logging.warning("New leader elected successfuly %s" % leader_uuid)
                break

        if recipe_failed:
            logging.error("Failed to elect new leader")
            return recipe_failed

        '''
        Copy get_all cmd to all the peers and make sure everyone selected the new leader
        '''
        for p in range(npeer):

            #Copy ctlrequest cmd file to get JSON output
            ctl_req_create_cmdfile_and_copy(get_all[p])
            time_global.sleep(2)

            raft_json_dict = genericcmdobj.raft_json_load(get_all[p].output_fpath)
            voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]
            leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
            if voted_for_uuid != peer_uuid_arr[leader_to_be] or leader_uuid != peer_uuid_arr[leader_to_be]:
                logging.error("New leader is not elected by peer: %d" % peer_uuid_arr[p])
                recipe_failed = 1
                break

            # commit idx should be pre-state1 value + 1
            commit_idx = raft_json_dict["raft_root_entry"][0]["commit-idx"]
            if commit_idx != original_commit_idx[p] + 1:
                logging.error("Current commit idx(%d) != orig commit indx + 1(%d)" % (commit_idx, original_commit_idx[p]))
                recipe_failed = 1
                break

            # newest_entry_idx should be Pre-stage1 value + 1
            newest_entry_idx = raft_json_dict["raft_root_entry"][0]["newest-entry-idx"]
            if newest_entry_idx != original_newest_entry_idx[p] + 1:
                logging.error("Current newest_entry_idx (%) != original + 1 (%d)" % (newest_entry_idx, original_newest_entry_idx[p]))
                recipe_failed = 1
                break

            # Term should be greater than pre-stage1. With multiple failed leader election, its value can
            # increase more than one.
            term = raft_json_dict["raft_root_entry"][0]["term"]
            if term > original_term[p]:
                logging.error("Current term (%) is not greater than original (%d)" % (term, original_term[p]))
                recipe_failed = 1
                break

        if recipe_failed:
            logging.error("Stage 3 failed")
            return recipe_failed

        logging.warning(f"Stage 3 successful" % leader_uuid)

        '''
        Finalization of recipe: The recipe should restore net_recv_enabled state to true on all peers.
        '''
        for p in range(npeer):
            net_rcv_true[p] = CtlRequest(inotifyobj, "rcv_true", peer_uuid_arr[follower_to_be_leaer],
                                         app_uuid,
                                         inotify_input_base.REGULAR,
                                         self.recipe_ctl_req_obj_list).Apply()
            time_global.sleep(2)

            #Copy ctlrequest cmd file to get JSON output
            ctl_req_create_cmdfile_and_copy(get_all[p])

            raft_json_dict = genericcmdobj.raft_json_load(get_all[p].output_fpath)
            net_recv_enable = raft_json_dict["ctl_svc_nodes"][0]["net_recv_enabled"]
            if net_recv_enable != True:
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
