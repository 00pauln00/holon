from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe03"
    desc = "Term catchup."
    parent = "recipe02"
    
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
        Create Json object for reading the JSON output and returning term value.
        '''
        jsonobj = RaftJson()

        '''
        To start the peer1, create objects for raftserver and raftprocess.
        '''
        raftserverobj1 = RaftServer(raftconfobj, 1)
        peer1_uuid = raftconfobj.get_peer_uuid_for_peerno(1)
        serverproc1 = RaftProcess(peer1_uuid, 1, "server")

        print(f"Starting peer 1 with UUID: %s\n" % peer1_uuid)
        serverproc1.start_process(raftconfobj)

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
        ctlreqobj = CtlRequest()

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output to check term value. 
        '''
        cmd_file_path = "/tmp/ctl_get_term.%s" % app_uuid 
        outfilename = "/get_term_output.%s" % (app_uuid)
        ctlreqobj.ctl_req_get_term_cmd_create(cmd_file_path, outfilename)

        #Prepare the output file path for peer 0 and peer 1
        p0_get_term_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer0_uuid,
                                    outfilename)

        p1_get_term_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer1_uuid,
                                    outfilename)

        # Get the term valur for Peer0 before pausing it.
        inotifyobj.copy_cmd_file(genericcmdobj, peer0_uuid, cmd_file_path)
        time_global.sleep(1)
        peer0_term = jsonobj.json_parse_and_return_term_value(p0_get_term_out)

        '''
        Run the loop to copy the command file for getting the term value
        and verifying in each iteration, term value increases.
        '''
        print(f"Pause and resume peer0 in loop and check if its term catches up with peer1")
        pause_time = 3
        # TODO Iteration value should be specified by user. 
        for i in range(5):

            print(f"Pausing Peer0 for %d sec" % pause_time)
            serverproc0.pause_process()
            '''
            Copy the cmd file into Peer 1's input directory.
            And read the output JSON to get the term value.
            '''
            inotifyobj.copy_cmd_file(genericcmdobj, peer1_uuid, cmd_file_path)
            time_global.sleep(1)
            peer1_term = jsonobj.json_parse_and_return_term_value(p1_get_term_out)
            print(f"Term value for peer1: %d" % peer1_term)

            # TODO pasue duration should be user defined
            time_global.sleep(pause_time)

            '''
            Resume Peer0 and again copy cmd file to get it's current term value.
            '''
            serverproc0.resume_process()

            inotifyobj.copy_cmd_file(genericcmdobj, peer0_uuid, cmd_file_path)
            time_global.sleep(1)
            peer0_term = jsonobj.json_parse_and_return_term_value(p0_get_term_out)
            print(f"Term value of peer0 after resume is: %d" % peer0_term)

            '''
            Peer0 term should have catched up with peer1 term i.e Peer0 term value should
            be greater than or equal to peer1's term value.
            '''
            if peer0_term < peer1_term:
                print(f"Term Catch up failed, peer0 term: %d and peer1 term: %d" % (peer0_term, peer1_term))
                sys.exit(1)


        print("Recipe03 Successful, Raft Peer 0 term is catching up with peer 1 term!!\n")
        # Store the raftserver1 object into clusterobj
        clusterobj.raftserver_obj_store(raftserverobj1, 1)
        # Store server1 process object
        clusterobj.raftprocess_obj_store(serverproc1, 1)
        

    def post_run(self, clusterobj):
        print("Post run method")
        print("kill server process 1")
        serverproc = clusterobj.raftserverprocess[1]
        serverproc.kill_process()
