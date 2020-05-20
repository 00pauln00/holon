from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe00"
    desc = "Bootup recipe"
    parent = ""
    
    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):

        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj
        
        print(f"Run Recip00")

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
        raftserverobj = RaftServer(raftconfobj, 0)

        '''
        Create Process object for first server
        '''
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(0)

        print(f"Starting peer with uuid: %s" % peer_uuid)
        serverproc = RaftProcess(peer_uuid, "server")

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
        inotifyobj.copy_cmd_file(peer_uuid, cmd_file_path)

        # Sleep before reading the output file.
        time_global.sleep(1)

        #Read the output file and verify the idleness of the server.
        get_all_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                            peer_uuid,
                                            outfilename)

        '''
        Create Jason parsing object to parse the JASON output.
        '''
        jasonparseobj = RaftJasonParse()

        # Verify the idleness of the server
        jasonparseobj.jason_parse_and_verify_server_idleness(get_all_out)

        '''
        Start one client. Generate UUID and config file for it.
        '''
        # TODO check how to pass client port and ip_address dynamically.
        raftconfobj.generate_client_conf("127.0.0.1", 14001)

        # Create RaftClient object for client 0
        raftclientobj = RaftClient(raftconfobj, 0)
        client_uuid = raftconfobj.get_client_uuid_for_clientno(0)

        # Create RaftProcess object for client 0
        clientproc = RaftProcess(client_uuid, "client")

        print(f"Starting client process with UUID: %s" % client_uuid)
        clientproc.start_process(raftconfobj)

        # Sleep for 2sec
        time_global.sleep(2)

        # Copy the cmd file into input directory of the started client.
        print(f"Copy init cmd file to client's input directory")
        inotifyobj.copy_cmd_file(client_uuid, cmd_file_path)

        # Sleep before reading the output file.
        time_global.sleep(1)

        #Read the output file and verify the idleness of the server.
        get_all_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    client_uuid,
                                    outfilename)

        print(f"Verify the JASON output of the client")
        # Parse the output and verify client idleness
        jasonparseobj.jason_parse_and_verify_client_idleness(get_all_out)

        '''
        Start the server and client by exiting the idlenss
        Create cmdfile to exit idleness and copy it into input directory
        of server and client.
        '''
        idleness_file_path = "/tmp/exit_idleness.%s" % app_uuid 
        ctlreqobj.ctl_req_init_idleness_create(idleness_file_path, "false")

        # Copy it in to input directory of server
        inotifyobj.copy_cmd_file(peer_uuid, idleness_file_path)

        # Copy it in to input directory of client
        inotifyobj.copy_cmd_file(client_uuid, idleness_file_path)

        # sleep for 2sec
        time_global.sleep(2)

        print(f"Exited Idleness and starting the server and client loops")

        # Once server and client started, check the timestamp progresses
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
            inotifyobj.copy_cmd_file(peer_uuid, curr_time_path)
            # Read the output file and get the time
            time_global.sleep(1)
            time = jasonparseobj.jason_parse_and_return_curr_time(curr_time_out)
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
        clusterobj.raftserver_obj_store(raftserverobj)
        # Store the raftclient object
        clusterobj.raftclient_obj_store(raftclientobj)
        # Store server process object
        clusterobj.raftprocess_obj_store(serverproc)
        # Store client process object
        clusterobj.raftprocess_obj_store(clientproc)

    def post_run(self, clusterobj):
        print("Post run method")
        #if kill_proc:
        serverproc = clusterobj.raftserverprocess[0]
        clientproc = clusterobj.raftclientprocess[0]
        print("kill server and client processes")
        serverproc.kill_process()
        clientproc.kill_process()

