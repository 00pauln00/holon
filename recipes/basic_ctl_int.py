from holonrecipe import *
import logging

class Recipe(HolonRecipeBase):
    name = "basic_ctl_int"
    desc = "Basic Control interface recipe\n"\
            "1. To verify the idleness of the process.\n"\
            "2. Verify process can be activated by exiting the idleness.\n"\
            "3. Once process is active, verify it's timestamp progresses.\n"
    parent = ""
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []

    def print_desc(self):
        print(self.desc)

    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        logging.warning("===========Run Basic Control Interface=======================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()
        '''
        This recipe starts peer0
        '''
        peerno = 0
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(peerno)

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()
        logging.warning("Application UUID generated: %s" % app_uuid)

        '''
        - Create ctlrequest object to create command for CTL request
        - Before starting the server, copy the APPLY init command into init directory,
          so that server will not go into start loop and will remain idle.
        '''
        init_ctl = CtlRequest(inotifyobj, "idle_on", peer_uuid, app_uuid,
                              False, self.recipe_ctl_req_obj_list).Apply()

        '''
        Create Process object for first server
        '''
        logging.warning("Starting peer %d with uuid: %s" % (peerno, peer_uuid))
        serverproc = RaftProcess(peer_uuid, peerno, "server")

        #Start the server process
        serverproc.start_process(raftconfobj, clusterobj)

        # sleep for 2 sec
        time_global.sleep(2)

        # append the serverproc into recipe process object list
        self.recipe_proc_obj_list.append(serverproc)

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JASON output to check the idleness
        '''
        get_all_ctl = CtlRequest(inotifyobj, "get_all", peer_uuid, app_uuid,
                                 False, self.recipe_ctl_req_obj_list).Apply()

        # Sleep before reading the output file.
        time_global.sleep(1)

        '''
        Verify the JSON out for idleness.
        '''

        raft_json_dict = genericcmdobj.raft_json_load(get_all_ctl.output_fpath)
        # Leader UUID should be null
        recipe_failed = 0
        leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
        if leader_uuid != "":
            logging.error("Error: Leader uuid is set: %s" % leader_uuid)
            recipe_failed = 1

        commit_idx = raft_json_dict["raft_root_entry"][0]["commit-idx"]
        if commit_idx != -1:
            logging.error("commit-idx is not -1: %s" % commit_idx)
            recipe_failed = 1
        
        last_applied = raft_json_dict["raft_root_entry"][0]["last-applied"]
        if last_applied != -1:
            logging.error("last-applied is not -1: %s" % {last_applied})
            recipe_failed = 1

        last_applied_cumulative_crc = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]
        if last_applied_cumulative_crc != 0:
            logging.error("last-applied-cumulative-crc is not zero: %s" % last_applied_cumulative_crc)
            recipe_failed = 1

        ignore_timer_events = raft_json_dict["raft_net_info"]["ignore_timer_events"]
        if ignore_timer_events != True:
            logging.error("ignore_timer_evernts should be true %s" % ignore_timer_events)
            recipe_failed = 1

        if recipe_failed:
            logging.error("Basic control interface recipe Failed")
            return recipe_failed

        '''
        Activate the server by exiting the idleness
        Create cmdfile to exit idleness and copy it into input directory
        of the server.
        '''
        idle_off_ctl = CtlRequest(inotifyobj, "idle_off", peer_uuid, app_uuid,
                                  False, self.recipe_ctl_req_obj_list).Apply()

        # sleep for 2sec
        time_global.sleep(2)

        logging.warning("Exited Idleness and starting the server loop\n")

        # Once server the started, verify that the timestamp progresses
        curr_time_ctl = CtlRequest(inotifyobj, "current_time", peer_uuid, app_uuid,
                                    False, self.recipe_ctl_req_obj_list).Apply()

        # TODO the iteration shouldn't be hardcoded
        timestamp_dict = {}
        for i in range(4):

            # Read the output file and get the time
            raft_json_dict = genericcmdobj.raft_json_load(curr_time_ctl.output_fpath)
            curr_time_string = raft_json_dict["system_info"]["current_time"]
            time_string = curr_time_string.split()
            time = time_string[3]

            logging.warning("Time is: %s" % time)
            timestamp_dict[i] = time
            time_global.sleep(3)
            # Copy the cmd file into input directory of server.
            logging.warning("Copy cmd file to get current_system_time for iteration: %d" % i)
            ctl_req_create_cmdfile_and_copy(curr_time_ctl)

        '''
        Compare the timestamp stored in the timestamp_arr and verify time
        is progressing.
        '''
        recipe_failed = 0
        logging.warning("Compare the timestamp and it should be progressing.")
        for i in range(3):
            time1 = timestamp_dict[i]
            time2 = timestamp_dict[i+1]
            prev_time = datetime.strptime(time1,"%H:%M:%S")
            curr_time = datetime.strptime(time2,"%H:%M:%S")
            if prev_time >= curr_time:
                logging.error("Error: Time is not updating")
                recipe_failed = 1
                break

        if recipe_failed:
            logging.error("Basic control interface recipe failed")
        else:
            logging.warning("Basic control interface Recipe Successful, Time progressing!!")

        # Store server process object
        clusterobj.raftprocess_obj_store(serverproc, peerno)

        return recipe_failed

    def post_run(self, clusterobj):
        logging.warning("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()

        for proc_obj in self.recipe_proc_obj_list:
            logging.warning("kill server process: %d" % proc_obj.process_idx)
            proc_obj.kill_process()
