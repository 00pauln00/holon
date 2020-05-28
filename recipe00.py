from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe00"
    desc = "Bootup recipe"
    parent = ""
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    
    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        '''
        Purpose of this recipe is:
        1. To verify the idleness of the process.
        2. Verify process can be activated by exiting the idleness.
        3. Once process is active, verify it's timestamp progresses.
        '''
        print(f"===========Run Recip00=======================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()
        print(f"Application UUID generated: %s" % app_uuid)

        peerno = 0
        '''
        Create Process object for first server
        '''
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(peerno)

        '''
        - Create ctlrequest object to create command for CTL request
        - Before starting the server, copy the APPLY init command into init directory,
          so that server will not go into start loop and will remain idle.
        '''
        init_ctl = CtlRequest(inotifyobj, "idle_on", peer_uuid, app_uuid)

        # Create Init cmd idleness file
        init_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)
 
        # append the init_ctl object into recipe's ctl_req list.
        self.recipe_ctl_req_obj_list.append(init_ctl)
        
        print(f"Starting peer %d with uuid: %s" % (peerno, peer_uuid))
        serverproc = RaftProcess(peer_uuid, peerno, "server")

        #Start the server process
        serverproc.start_process(raftconfobj)

        # append the serverproc into recipe process object list
        self.recipe_proc_obj_list.append(serverproc)

        # sleep for 2 sec
        time_global.sleep(2)

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JASON output to check the idleness
        '''
        get_all_ctl = CtlRequest(inotifyobj, "get_all", peer_uuid, app_uuid)

        get_all_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)

        # append the get_all_ctl object into recipe's ctl_req list.
        self.recipe_ctl_req_obj_list.append(get_all_ctl)

        # Sleep before reading the output file.
        time_global.sleep(1)

        '''
        Verify the JSON out for idleness.
        '''

        raft_json_dict = genericcmdobj.raft_json_load(get_all_ctl.output_fpath)
        # Leader UUID should be null
        leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
        if leader_uuid != "":
            print(f"Error: Leader uuid is set: %s" % leader_uuid)
            exit()

        commit_idx = raft_json_dict["raft_root_entry"][0]["commit-idx"]
        if commit_idx != -1:
            print(f"commit-idx is not -1: %s" % commit_idx)
            exit()
        
        last_applied = raft_json_dict["raft_root_entry"][0]["last-applied"]
        if last_applied != -1:
            print(f"last-applied is not -1: %s" % {last_applied})
            exit()

        last_applied_cumulative_crc = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]
        if last_applied_cumulative_crc != 0:
            print(f"last-applied-cumulative-crc is not zero: %s" % last_applied_cumulative_crc)
            exit()


        '''
        Activate the server by exiting the idlenss
        Create cmdfile to exit idleness and copy it into input directory
        of the server.
        '''
        idle_off_ctl = CtlRequest(inotifyobj, "idle_off", peer_uuid, app_uuid)

        idle_off_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)

        # append the idle_off_ctl object into recipe's ctl_req list.
        self.recipe_ctl_req_obj_list.append(idle_off_ctl)

        # sleep for 2sec
        time_global.sleep(2)

        print(f"Exited Idleness and starting the server loop\n")

        # Once server the started, verify that the timestamp progresses
        curr_time_ctl = CtlRequest(inotifyobj, "current_time", peer_uuid, app_uuid)

        # append the curr_time_ctl object into recipe's ctl_req list.
        self.recipe_ctl_req_obj_list.append(curr_time_ctl)

        # TODO the iteration shouldn't be hardcoded
        timestamp_arr = []
        for i in range(4):
            # Copy the cmd file into input directory of server.
            print(f"Copy cmd file to get current_system_time for iteration: %d" % i)
            curr_time_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)

            # Read the output file and get the time
            time_global.sleep(1)
            raft_json_dict = genericcmdobj.raft_json_load(curr_time_ctl.output_fpath)
            curr_time_string = raft_json_dict["system_info"]["current_time"]
            time_string = curr_time_string.split()
            time = time_string[3]

            print(f"Time is: %s" % time)
            timestamp_arr.append(time)

        '''
        Compare the timestamp stored in the timestamp_arr and verify time
        is progressing.
        '''
        print(f"Compare the timestamp and it should be progressing.")
        for i in range(3):
            time1 = timestamp_arr[i]
            time2 = timestamp_arr[i+1]
            prev_time = datetime.strptime(time1,"%H:%M:%S")
            curr_time = datetime.strptime(time2,"%H:%M:%S")
            if prev_time >= curr_time:
                print("Error: Time is not updating")
                exit()

        print("Recip00 Successful, Time progressing!!")

        # Store server process object
        clusterobj.raftprocess_obj_store(serverproc, peerno)

    def post_run(self, clusterobj):
        print("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()

        for proc_obj in self.recipe_proc_obj_list:
            print("kill server process: %d" % proc_obj.process_idx)
            proc_obj.kill_process()
