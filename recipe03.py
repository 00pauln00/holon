from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe03"
    desc = "Term catchup."
    parent = "recipe02"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    
    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        '''
        Purpose of this recipe is:
        Show that when a number of servers less than or equal to
        (num-raft-peers-in-config / 2) are running that the term values of all
        servers quickly converge to the highest value.
        '''
        print(f"============== Run Recip03 ====================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        serverproc0 = clusterobj.raftserverprocess[0]
        raftconfobj = clusterobj.raftconfobj

        # Peer0 was started be previous recipe, simply get its UUID.
        peer0_uuid = raftconfobj.get_peer_uuid_for_peerno(0)

        '''
        To start the peer1, create objects for raftprocess.
        '''
        peer1_uuid = raftconfobj.get_peer_uuid_for_peerno(1)
        serverproc1 = RaftProcess(peer1_uuid, 1, "server")

        print(f"Starting peer 1 with UUID: %s\n" % peer1_uuid)
        serverproc1.start_process(raftconfobj)

        # append the serverproc into recipe process object list
        self.recipe_proc_obj_list.append(serverproc1)

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()
        print(f"Application UUID generated: %s" % app_uuid)

        '''
        - Create ctlrequest object to create command for CTL request
        '''
        p0_term_ctl = CtlRequest(inotifyobj, "get_term", peer0_uuid, app_uuid)
        p1_term_ctl = CtlRequest(inotifyobj, "get_term", peer1_uuid, app_uuid)

        # append the idle_off_ctl object into recipe's ctl_req list.
        self.recipe_ctl_req_obj_list.append(p0_term_ctl)
        self.recipe_ctl_req_obj_list.append(p1_term_ctl)

        # Get the term valur for Peer0 before pausing it.
        p0_term_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)
        
        time_global.sleep(1)
        raft_json_dict = genericcmdobj.raft_json_load(p0_term_ctl.output_fpath)
        peer0_term = raft_json_dict["raft_root_entry"][0]["term"]
        
        print(f"Term value of peer0 before pausing it: %s" % peer0_term)
        '''
        Run the loop to copy the command file for getting the term value
        and verifying in each iteration, term value increases.
        '''
        print(f"Pause and resume peer0 in loop and check if its term catches up with peer1")
        pause_time = 3
        # TODO Iteration value should be specified by user. 
        for i in range(5):

            serverproc0.pause_process()

            # TODO pasue duration should be user defined
            time_global.sleep(pause_time)

            '''
            Copy the cmd file into Peer 1's input directory.
            And read the output JSON to get the term value.
            '''
            p1_term_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)
            time_global.sleep(1)

            raft_json_dict = genericcmdobj.raft_json_load(p1_term_ctl.output_fpath)
            peer1_term = raft_json_dict["raft_root_entry"][0]["term"]

            print(f"Term value for peer1: %d" % peer1_term)

            '''
            Resume Peer0 and again copy cmd file to get it's current term value.
            '''
            serverproc0.resume_process()

            time_global.sleep(1)
            p0_term_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)

            raft_json_dict = genericcmdobj.raft_json_load(p0_term_ctl.output_fpath)
            peer0_term = raft_json_dict["raft_root_entry"][0]["term"]

            print(f"Term value of peer0 after resume is: %d" % peer0_term)

            '''
            Peer0 term should have catched up with peer1 term i.e Peer0 term value should
            be greater than or equal to peer1's term value or different between term 
            should not be greater than pause_time.
            '''
            if peer0_term < peer1_term and ((peer1_term - peer0_term) > pause_time):
                print(f"Term Catch up failed, peer0 term: %d and peer1 term: %d" % (peer0_term, peer1_term))
                sys.exit(1)


        print("Recipe03 Successful, Raft Peer 0 term is catching up with peer 1 term!!\n")
        # Store server1 process object
        clusterobj.raftprocess_obj_store(serverproc1, 1)
        

    def post_run(self, clusterobj):
        print("Post run method for recipe03")
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()

        for proc_obj in self.recipe_proc_obj_list:
            print("kill server process: %d" % proc_obj.process_idx)
            proc_obj.kill_process()
