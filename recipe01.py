from holonrecipe import *

class Recipe(HolonRecipeBase):

    name = "Recipe01"
    desc = "PAUSE and RESUME the process"
    parent = "recipe00"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []

    def pre_run(self):
        return self.parent

    def run(self, clusterobj):
        '''
        Recipe01 purpose is to pasue and resume processes without exiting
        unexpectedly. It assumes peer 0  was started by Recip00.
        '''
        print(f"=============Run Recipe : Recipe01====================")

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
        print("Pause and resume the peer: %s\n" % peer_uuid)

        # Pause and Resume server for n iterations.
        # TODO iteration count should not be hardcoded.
        for i in range(5):
            # pause the process
            serverproc.pause_process()
            time_global.sleep(2)
            print(f"pausing the process for 2sec and then resume")
            serverproc.resume_process()

        print(f"After resuming process, check process current time proceeds\n")

        '''
        After resuming the server process, copy cmd file and
        verify server is still progessing and shows timestamp
        progressing.
        '''
        curr_time_ctl = CtlRequest(inotifyobj, "current_time", peer_uuid, app_uuid)

        # append the curr_time_ctl object into recipe's ctl_req list.
        self.recipe_ctl_req_obj_list.append(curr_time_ctl)

        prev_time_string = "00:00:00"
        prev_time = datetime.strptime(prev_time_string,"%H:%M:%S")
        for i in range(4):
            print("Copy the cmd file into input directory of server. Itr %d" % i)
            curr_time_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)

            # Read the output file and get the time
            raft_json_dict = genericcmdobj.raft_json_load(curr_time_ctl.output_fpath)
            curr_time_string = raft_json_dict["system_info"]["current_time"]
            time_string = curr_time_string.split()
            time = time_string[3]
            time_global.sleep(1)

            print(f"Time is: %s" % time)
            curr_time = datetime.strptime(time,"%H:%M:%S")
            if prev_time >= curr_time:
                print("Error: Time is not updating from Recip01")
                exit()

    print(f"Recipe01: Successful, Pause/Resume does not terminate processes")

    def post_run(self, clusterobj):
        print("Post run method for recipe01")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()

