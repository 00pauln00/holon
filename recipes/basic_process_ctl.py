from holonrecipe import *
import logging

class Recipe(HolonRecipeBase):

    name = "basic_process_ctl"
    desc = "Basic Process control recipe\n"\
            "1. Pause and resume the server in a loop.\n"\
            "2. Make sure current time does not progress for the server during pause\n"\
            "and resume cycle.\n"\
            "3. Resume the process and verify time stamp progresses normally.\n"
    parent = "basic_ctl_int"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []

    def print_desc(self):
        print(self.desc)

    def pre_run(self):
        return self.parent

    def run(self, clusterobj):
        logging.warning(f"=============Run Recipe : Basic process control ====================")

        serverproc = clusterobj.raftserverprocess[0]
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()

        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(0)
        logging.warning("Pause and resume the peer: %s\n" % peer_uuid)

        '''
        Copy cmd file. 
        '''
        curr_time_ctl = CtlRequest(inotifyobj, "current_time", peer_uuid,
                                    app_uuid,
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        '''
        Pause and Resume server for n iterations. After pausing the server,
        copy the cmd file into input directory. As process is paused, output
        file should not get generated.
        '''
        # TODO iteration count should not be hardcoded.
        recipe_failed = 0
        for i in range(5):
            # pause the process
            serverproc.pause_process()
            logging.warning("pausing the process for 5secs and then resume")
            time_global.sleep(5)
            curr_time_ctl.Apply_and_Wait(True)
            # Only check if output file got created.
            if os.path.exists(curr_time_ctl.output_fpath):
                logging.error("Error: Output file gets created even when paused")
                recipe_failed = 1
                break

            serverproc.resume_process()

        if recipe_failed:
            logging.error("Basic process control recipe failed")
            return recipe_failed

        logging.warning("After resuming process, check process current time proceeds\n")

        '''
        After resuming the server process, copy cmd file and
        verify server is still progessing and shows timestamp
        progressing.
        '''

        prev_time_string = "00:00:00"
        prev_time = datetime.strptime(prev_time_string,"%H:%M:%S")
        recipe_failed = 0
        for i in range(4):
            logging.warning("Copy the cmd file into input directory of server. Itr %d" % i)
            curr_time_ctl.Apply_and_Wait(False)
            # Read the output file and get the time
            raft_json_dict = genericcmdobj.raft_json_load(curr_time_ctl.output_fpath)
            curr_time_string = raft_json_dict["system_info"]["current_time"]
            time_string = curr_time_string.split()
            time = time_string[3]
            time_global.sleep(1)

            logging.warning("Current Time is: %s" % time)
            curr_time = datetime.strptime(time,"%H:%M:%S")
            if prev_time >= curr_time:
                logging.error("Error: Time is not updating from Basic process control recipe")
                recipe_failed = 1
                break

        if recipe_failed:
            logging.error("basic process control recipe failed")
        else:
            logging.error("Basic process control recipe: Successful, Pause/Resume does not terminate processes")

        return recipe_failed

    def post_run(self, clusterobj):
        logging.warning("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()
