from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe04"
    desc = "Basic leader election"
    parent = "recipe03"
    
    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        '''
        Purpose of this recipe is:
        Invoke and observe a successful leader election with the minimum
        number of peers per the specified configuration.
        '''
        print(f"================ Run Recip04 ======================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj

        '''
        Create Json object for reading the JSON output and returning term value.
        '''
        jsonobj = RaftJson()

        # Number of peers to be started for Recipe04
        npeer_start = 3
        peerno = 2
        peer_uuid_arr = [None] * npeer_start

        for p in range(npeer_start):
            peer_uuid_arr[p] = raftconfobj.get_peer_uuid_for_peerno(p)

        '''
        To start the peer2, create objects for raftserver and raftprocess.
        '''
        print(f"Starting peer %d with UUID: %s" % (peerno, peer_uuid_arr[peerno]))
        raftserverobj2 = RaftServer(raftconfobj, peerno)
        serverproc2 = RaftProcess(peer_uuid_arr[peerno], peerno, "server")

        serverproc2.start_process(raftconfobj)
        time_global.sleep(2)
        '''
        After starting peer2, minimum number of servers for leader election
        have reached.
        '''

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()

        '''
        Generate UUID for the application to be used in the outfilename.
        '''
        app_uuid = genericcmdobj.generate_uuid()

        '''
        - Create ctlrequest object to create command for CTL request
        - Before starting the server, copy the APPLY init command into init directory,
          so that server will not go into start loop and will remain idle.
        '''
        ctlreqobj = CtlRequest()

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output to check term value. 
        '''
        cmd_file_path = "/tmp/get_all.%s" % app_uuid 
        outfilename = "/get_all.%s" % (app_uuid)
        ctlreqobj.ctl_req_get_all_cmd_create(cmd_file_path, outfilename)

        '''
        Prepare the output file path for peer0,1 and 2 using it's UUID.
        '''
        p0_get_all_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer_uuid_arr[0],
                                    outfilename)

        p1_get_all_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer_uuid_arr[1],
                                    outfilename)

        p2_get_all_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer_uuid_arr[2],
                                    outfilename)
        '''
        Copy the get all command file into input directories of peer0,
        peer1 and peer2. And verify all peers elected the same leader.
        '''

        for p in range(npeer_start):
            inotifyobj.copy_cmd_file(genericcmdobj, peer_uuid_arr[p], cmd_file_path)

        time_global.sleep(3)

        '''
        Get the leader UUID from all the 3 servers.
        '''
        peer0_leader_uuid = jsonobj.json_parse_and_return_leader_uuid(p0_get_all_out)
        print(f"Leader uuid of peer0 is: %s" % peer0_leader_uuid)
        peer1_leader_uuid = jsonobj.json_parse_and_return_leader_uuid(p1_get_all_out)
        print(f"Leader uuid of peer1 is: %s" % peer1_leader_uuid)
        peer2_leader_uuid = jsonobj.json_parse_and_return_leader_uuid(p2_get_all_out)
        print(f"Leader uuid of peer2 is: %s" % peer2_leader_uuid)

        if peer0_leader_uuid != peer1_leader_uuid:
            print(f"Error: Peer0 leader(%s) does not match with peer1 leader(%s)" %
                                peer0_leader_uuid, peer1_leader_uuid)
            exit()
        elif peer0_leader_uuid != peer2_leader_uuid:
            print(f"Error: Peer0 leader(%s) does not match with peer2 leader(%s)" %
                                peer0_leader_uuid, peer2_leader_uuid)
            exit()
                
        print("Recipe04 Successful, Leader election successful!!\n")

        # Store the raftserver2 object into clusterobj
        clusterobj.raftserver_obj_store(raftserverobj2, peerno)
        # Store server2 process object
        clusterobj.raftprocess_obj_store(serverproc2, peerno)
        

    def post_run(self, clusterobj):
        print("Post run method")
        print("kill server process 2")
        serverproc = clusterobj.raftserverprocess[2]
        serverproc.kill_process()
