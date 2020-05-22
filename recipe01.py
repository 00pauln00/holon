from holonrecipe import *

class Recipe(HolonRecipeBase):

    name = "Recipe01"
    desc = "PAUSE and RESUME the process"
    parent = "recipe00"

    def pre_run(self):
        return self.parent

    def run(self, clusterobj):
        '''
        Recipe01 purpose is to pasue and resume processes without exiting
        unexpectedly. It assumes peer 0  was started by Recip00.
        '''
        print(f"Run Recipe : Recipe01")

        serverproc = clusterobj.raftserverprocess[0]
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        '''
        Create the object for ctlrequest.
        '''
        ctlreqobj = CtlRequest()

        '''
        Create Json parsing object
        '''
        jsonparseobj = RaftJson()

        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(0)
        print("Pause and resume the peer: %s" % peer_uuid)

        # Pause and Resume server for n iterations.
        # TODO iteration count should not be hardcoded.
        for i in range(5):
            # pause the process
            print(f"pausing the process for 2sec")
            serverproc.pause_process()
            time_global.sleep(2)
            serverproc.resume_process()

        '''
        After resuming the server process, copy cmd file and
        verify server is still progessing and shows timestamp
        progressing.
        '''
        cmd_file_path = "/tmp/curr_time_recip01.%s" % os.getpid()
        print(f"Cmd file path: %s" % cmd_file_path)
        outfile = "/curr_time_output.%s" % os.getpid()

        # Create the cmdfile.
        ctlreqobj.ctl_req_get_current_time_cmd_create(cmd_file_path, outfile)
        out_file_path = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer_uuid,
                                    outfile)

        prev_time_string = "00:00:00"
        prev_time = datetime.strptime(prev_time_string,"%H:%M:%S")
        for i in range(4):
            print("Copy the cmd file into input directory of server. Itr %d" % i)
            inotifyobj.copy_cmd_file(peer_uuid, cmd_file_path)
            # Read the output file and get the time
            time_global.sleep(1)
            time_string = jsonparseobj.json_parse_and_return_curr_time(out_file_path)
            print(f"Time return by parse func: %s" % time_string)
            curr_time = datetime.strptime(time_string,"%H:%M:%S")
            if prev_time >= curr_time:
                print("Error: Time is not updating from Recip01")
                exit()


    def post_run(self, clusterobj):
        print("Post run method: ")

