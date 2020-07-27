from holonrecipe import *
import logging
from recipe_verify import *

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
        orig_ctlreqobj = [None] * npeer
        rcv_false_ctlreqobj = [None] * npeer
        set_leader_ctlreqobj = [None] * npeer
        new_election_ctlreqobj = [None] * npeer

        #Verify the parameters
        new_leader_idx = -1
        LEADER_ELECTION_TIME_OUT = 300 #5mins
       
        recipe_failed = 0
        '''
        Make sure none of the peer is in idle state
        '''
        for p in range(npeer):
            CtlRequest(inotifyobj, "idle_off", peer_uuid_arr[0],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        '''
        Get the leader uuid and select one of the follower as leader-to-be
        for next leader election.
        '''
        orig_leader_uuid = ""
        for p in range(npeer):
            orig_ctlreqobj[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                        app_uuid,
                                        inotify_input_base.REGULAR,
                                        self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
            if orig_leader_uuid == "":
                orig_leader_uuid = get_raft_json_key_value(orig_ctlreqobj[p], "/raft_root_entry/*/leader-uuid")
            # Select the new leader-to-be from follower peers
            if peer_uuid_arr[p] != orig_leader_uuid and new_leader_idx == -1:
                logging.warning("Peer uuid for new leader is: %s" % peer_uuid_arr[p])
                new_leader_idx = p

        '''
        Copy the cmd file to Disable the net_recv_enable on all
        peers and verify that net_recv_enable is set to false.
        '''
        logging.warning("Stage 1: Disable message receive on all peers")
        for p in range(npeer):
            #Copy the cmd file for Disable the net_recv_enable
            CtlRequest(inotifyobj, "rcv_false", peer_uuid_arr[p],
                        app_uuid,
                        inotify_input_base.REGULAR,
                        self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        time_global.sleep(3)

        #Load the rule table
        with open('rule_table/leader_overthrow.json') as json_file:
            self.stage_rule_table = json.load(json_file)

        '''
        Verify if net_recv_enable is set to false for all peers.
        '''
        for p in range(npeer):

            #Copy cmdfile to get the JSON output 
            rcv_false_ctlreqobj[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                             app_uuid,
                                             inotify_input_base.REGULAR,
                                             self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

            peer_state = get_raft_json_key_value(rcv_false_ctlreqobj[p],
                                                 "/raft_root_entry/*/state")

            if peer_state != "candidate" and peer_state != "leader":
                logging.error("peer %s state is not leader or candidate. It is: %s" % (peer_uuid_arr[p], peer_state))
                recipe_failed = 1
                break

            ctlreq_list = []
            orig_ctlreq_list = []

            ctlreq_list.append(rcv_false_ctlreqobj[p])
            orig_ctlreq_list.append(orig_ctlreqobj[p])

            stage_no = 0
            if peer_state == "leader":
                #leader stage is stage1 and candidate is stage 0
                stage_no = 1

            self.stage_rule_table[stage_no]["ctlreqobj"] = ctlreq_list
            self.stage_rule_table[stage_no]["orig_ctlreqobj"] = orig_ctlreq_list
            recipe_failed = verify_rule_table(self.stage_rule_table[stage_no])
            if recipe_failed:
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
                                  self.recipe_ctl_req_obj_list).set_leader(peer_uuid_arr[new_leader_idx])
        time_global.sleep(3)

        '''
        Verify receive enable to the peer which is to be appointed as leader for
        all peers.
        '''
        logging.warning("Verify receive enable on the peer which is to be appointed as leader")
        for p in range(npeer):

            #Copy ctlrequest cmd file to get JSON output
            set_leader_ctlreqobj[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                             app_uuid,
                                             inotify_input_base.REGULAR,
                                             self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

            ctlreq_list = []
            orig_ctlreq_list = []

            ctlreq_list.append(set_leader_ctlreqobj[p])
            orig_ctlreq_list.append(orig_ctlreqobj[p])
            self.stage_rule_table[2]["ctlreqobj"] = ctlreq_list
            self.stage_rule_table[2]["orig_ctlreqobj"] = orig_ctlreq_list
            recipe_failed = verify_rule_table(self.stage_rule_table[2])
            if recipe_failed:
                break

            '''
            Make sure following item values are consistent and leader-election
            has not happened yet.
            '''

        if recipe_failed:
            logging.error("Stage 2 of Leader overthrow failed")
            return recipe_failed

        '''
        Enable the net_rcv on peer UUID-of-leader-to-be.
        The cmd is copied only to UUID-of-leader-to-be.
        check net_rcv_enabled is set to true on UUID-of-leader-to-be.
        '''    
        logging.warning("Stage 3: Enable Recv from all Peers on the Leader-to-be")

        CtlRequest(inotifyobj, "rcv_true", peer_uuid_arr[new_leader_idx],
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

        logging.warning("New leader election may take time...")

        time_out = 0
        while 1:
            recipe_failed = 0

            new_leader_ctlreqobj = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[new_leader_idx],
                                             app_uuid,
                                             inotify_input_base.REGULAR,
                                             self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
           
            leader_uuid = get_raft_json_key_value(new_leader_ctlreqobj, "/raft_root_entry/*/leader-uuid")
            voted_for_uuid = get_raft_json_key_value(new_leader_ctlreqobj, "/raft_root_entry/*/voted-for-uuid")

            if leader_uuid != peer_uuid_arr[new_leader_idx] or voted_for_uuid != peer_uuid_arr[new_leader_idx]:
                time_out = time_out + 1
                if time_out >= LEADER_ELECTION_TIME_OUT:
                    logging.error("Leader election failed")
                    recipe_failed = 1
                    break

                logging.warning("Leader election is not done yet!, retry after sleep 1sec")
                logging.warning("leader_uuid: %s, voted_for_uuid: %s" % (leader_uuid, voted_for_uuid))
                time_global.sleep(1)
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
            new_election_ctlreqobj[p] = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                             app_uuid,
                                             inotify_input_base.REGULAR,
                                             self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
            
            ctlreq_list = []
            orig_ctlreq_list = []

            ctlreq_list.append(new_election_ctlreqobj[p])
            orig_ctlreq_list.append(orig_ctlreqobj[p])
            self.stage_rule_table[3]["ctlreqobj"] = ctlreq_list
            self.stage_rule_table[3]["orig_ctlreqobj"] = orig_ctlreq_list
            recipe_failed = verify_rule_table(self.stage_rule_table[3])
            if recipe_failed:
                break
        

        if recipe_failed:
            logging.error("Stage 3 failed")
            return recipe_failed

        logging.warning(f"Stage 3 successful, all peers elected the new leader.")

        '''
        Finalization of recipe: The recipe should restore net_recv_enabled state to true on all peers.
        '''
        for p in range(npeer):
            CtlRequest(inotifyobj, "rcv_true", peer_uuid_arr[p],
                                         app_uuid,
                                         inotify_input_base.REGULAR,
                                         self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

            # verify rcv_true is set for all peers
            ctlreqobj = CtlRequest(inotifyobj, "get_all", peer_uuid_arr[p],
                                             app_uuid,
                                             inotify_input_base.REGULAR,
                                             self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
            ctlreq_list = []

            ctlreq_list.append(new_election_ctlreqobj[p])

            self.stage_rule_table[4]["ctlreqobj"] = ctlreq_list
            self.stage_rule_table[4]["orig_ctlreqobj"] = None
            recipe_failed = verify_rule_table(self.stage_rule_table[4])
            if recipe_failed:
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
