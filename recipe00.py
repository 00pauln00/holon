from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe00"
    desc = "Bootup recipe"
    parent = ""
    
    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        '''
        Purpose of this recipe is:
        1. To verify the idleness of the process.
        2. Verify process can be activated by exiting the idleness.
        3. Once process is active, verify it's timestamp progresses.
        '''
        print(f"Run Recip00")

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

        '''
        - Create ctlrequest object to create command for CTL request
        - Before starting the server, copy the APPLY init command into init directory,
          so that server will not go into start loop and will remain idle.
        '''
        print(f"Create ctl request object")
        ctlreqobj = CtlRequest()

        # Create Init cmd idleness file
        init_file_path = "/tmp/init_idleness.%s" % app_uuid
        ctlreqobj.ctl_req_init_idleness_create(init_file_path, "true")
        
        print(f"Copy the init cmd into init dir: %s" % init_file_path)
        genericcmdobj.copy_file(init_file_path, inotifyobj.inotify_init_path)
    
        '''
        Create RaftServer object for first server.
        '''
        peerno = 0
        raftserverobj = RaftServer(raftconfobj, peerno)

        '''
        Create Process object for first server
        '''
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(peerno)

        print(f"Starting peer %d with uuid: %s" % (peerno, peer_uuid))
        serverproc = RaftProcess(peer_uuid, peerno, "server")

        #Start the server process
        serverproc.start_process(raftconfobj)

        # sleep for 2 sec
        time_global.sleep(2)

        '''
        Creating cmd file to get all the JASON output from the server.
        Will verify parameters from server JASON output to check the idleness
        '''
        cmd_file_path = "/tmp/ctl_get_all.%s" % app_uuid 
        outfilename = "/get_all_output.%s" % (app_uuid)
        ctlreqobj.ctl_req_get_all_cmd_create(cmd_file_path, outfilename)

        print(f"Copy command file into server's input directory %s" % cmd_file_path)
        inotifyobj.copy_cmd_file(genericcmdobj , peer_uuid, cmd_file_path)

        # Sleep before reading the output file.
        time_global.sleep(1)

        #Read the output file and verify the idleness of the server.
        get_all_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                            peer_uuid,
                                            outfilename)

        '''
        Create Jason parsing object to parse the JASON output.
        '''
        jsonobj = RaftJson()

        # Verify the idleness of the server
        jsonobj.json_parse_and_verify_server_idleness(get_all_out)

        '''
        Activate the server by exiting the idlenss
        Create cmdfile to exit idleness and copy it into input directory
        of the server.
        '''
        idleness_file_path = "/tmp/exit_idleness.%s" % app_uuid 
        ctlreqobj.ctl_req_init_idleness_create(idleness_file_path, "false")

        # Copy it in to input directory of server
        inotifyobj.copy_cmd_file(genericcmdobj , peer_uuid, idleness_file_path)

        # sleep for 2sec
        time_global.sleep(2)

        print(f"Exited Idleness and starting the server loop")

        # Once server the started, verify that the timestamp progresses
        curr_time_path = "/tmp/current_time.%s" % app_uuid 
        print(f"curr_time_path: %s" % curr_time_path)
        outfilename = "/curr_time_output.%s" % (app_uuid)
        ctlreqobj.ctl_req_get_current_time_cmd_create(curr_time_path, outfilename)

        curr_time_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer_uuid,
                                    outfilename)

        # TODO the iteration shouldn't be hardcoded
        timestamp_arr = []
        for i in range(4):
            # Copy the cmd file into input directory of server.
            print(f"Copy cmd file to get current_system_time for iteration: %d" % i)
            inotifyobj.copy_cmd_file(genericcmdobj , peer_uuid, curr_time_path)
            # Read the output file and get the time
            time_global.sleep(1)
            time = jsonobj.json_parse_and_return_curr_time(curr_time_out)
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

        print("Time progressing!!")

        # Store the raftserver object into clusterobj
        clusterobj.raftserver_obj_store(raftserverobj, peerno)
        # Store server process object
        clusterobj.raftprocess_obj_store(serverproc, peerno)

    def post_run(self, clusterobj):
        print("Post run method")
        #if kill_proc:
        serverproc = clusterobj.raftserverprocess[0]
        print("kill server processes")
        serverproc.kill_process()
