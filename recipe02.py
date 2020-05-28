from holonrecipe import *

class Recipe(HolonRecipeBase):
    name = "Recipe02"
    desc = "Raft server term value increments."
    parent = "recipe01"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    
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

        peerno = 0
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(peerno)

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JSON output to check term value. 
        '''
        get_term_ctl = CtlRequest(inotifyobj, "get_term", peer_uuid, app_uuid)

        # append the curr_time_ctl object into recipe's ctl_req list.
        self.recipe_ctl_req_obj_list.append(get_term_ctl)

        '''
        Run the loop to copy the command file for getting the term value
        and verifying in each iteration, term value increases.
        '''
        prev_term = 0
        # TODO Iteration value should be specified by user. 
        print(f"Copy cmd file to get and verify term value\n")
        for i in range(10):
            # Copy the cmd file into input directory of server.
            get_term_ctl.ctl_req_create_cmdfile_and_copy(genericcmdobj)
            
            time_global.sleep(1)
            # Send the output value for reading the term value.
            raft_json_dict = genericcmdobj.raft_json_load(get_term_ctl.output_fpath)
            term = raft_json_dict["raft_root_entry"][0]["term"]

            print(f"Term value returned is: %d" % term)
            if term <= prev_term:
                print(f"Error: Raft server term value is not increasing")
                sys.exit(1)

            # Sleep for 2second to allow term to get incremented.
            time_global.sleep(2)

        print(f"Recipe02 Successful, Raft Peer 0's term value increasing!!\n")

    def post_run(self, clusterobj):
        print("Post run method for recipe02")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()
