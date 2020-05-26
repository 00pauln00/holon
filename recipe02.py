from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe02"
    desc = "Raft server term value increments."
    parent = "recipe01"
    
    def pre_run(self):
        return self.parent
    
    def run(self, clusterobj):
        '''
        Purpose of this recipe is:
        1. To verify the Term value increases in each iteration for the
        raft server.
        '''
        print(f"=================Run Recip02====================\n")

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
        ctlreqobj = CtlRequest()

        peerno = 0
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(peerno)

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output to check term value. 
        '''
        cmd_file_path = "/tmp/ctl_get_term.%s" % app_uuid 
        outfilename = "/get_term_output.%s" % (app_uuid)
        ctlreqobj.ctl_req_get_term_cmd_create(cmd_file_path, outfilename)
        #Prepare the output file path
        get_term_out = "%s/%s/output/%s" % (inotifyobj.inotify_path,
                                    peer_uuid,
                                    outfilename)

        '''
        Create Json object for reading the JSON output and returning term value.
        '''
        jsonobj = RaftJson()

        '''
        Run the loop to copy the command file for getting the term value
        and verifying in each iteration, term value increases.
        '''
        prev_term = 0
        # TODO Iteration value should be specified by user. 
        print(f"Copy cmd file to get and verify term value\n")
        for i in range(10):
            # Copy the cmd file into input directory of server.
            inotifyobj.copy_cmd_file(genericcmdobj, peer_uuid, cmd_file_path)

            time_global.sleep(1)
            # Send the output value for reading the term value.
            term = jsonobj.json_parse_and_return_term_value(get_term_out)
            print(f"Term value returned is: %d" % term)
            if term <= prev_term:
                print(f"Error: Raft server term value is not increasing")
                sys.exit(1)

            # Sleep for 2second to allow term to get incremented.
            time_global.sleep(2)

        print(f"Recipe02 Successful, Raft Peer 0's term value increasing!!\n")

    def post_run(self, clusterobj):
        print("Post run method")
