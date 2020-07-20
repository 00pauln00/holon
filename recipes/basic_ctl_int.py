from holonrecipe import *
from recipe_verify import *
import logging
import json

class Recipe(HolonRecipeBase):
    name = "basic_ctl_int"
    desc = "Basic Control interface recipe\n"\
            "1. To verify the idleness of the process.\n"\
            "2. Verify process can be activated by exiting the idleness.\n"\
            "3. Once process is active, verify it's timestamp progresses.\n"
    parent = ""
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    stage_rule_table = {}

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

        get_all_ctl = []

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
                              inotify_input_base.PRIVATE_INIT,
                              self.recipe_ctl_req_obj_list).Apply()
        '''
        Create Process object for first server
        '''
        logging.warning("Starting peer %d with uuid: %s" % (peerno, peer_uuid))
        serverproc = RaftProcess(peer_uuid, peerno, "server")

        #Start the server process
        serverproc.start_process(raftconfobj, clusterobj)


        # append the serverproc into recipe process object list
        self.recipe_proc_obj_list.append(serverproc)

        '''
        Creating cmd file to get all the JSON output from the server.
        Will verify parameters from server JASON output to check the idleness
        '''
        ctlobj = CtlRequest(inotifyobj, "get_all", peer_uuid, app_uuid,
                            inotify_input_base.REGULAR,
                            self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

        '''
        Add get_all_ctl object into stage1_rule_table to perform the rule checks
        on it.
        '''
        get_all_ctl.append(ctlobj)

        #Load te rule table
        with open('rule_table/basic_ctl_int.json') as json_file:
            self.stage_rule_table = json.load(json_file)

        self.stage_rule_table[0]["ctlreqobj"] = get_all_ctl
        self.stage_rule_table[0]["orig_ctlreqobj"] = None

        recipe_failed = verify_rule_table(self.stage_rule_table[0])
        if recipe_failed:
            logging.error("Basic control interface recipe Failed")
            return recipe_failed

        '''
        Activate the server by exiting the idleness
        Create cmdfile to exit idleness and copy it into input directory
        of the server.
        '''
        idle_off_ctl = CtlRequest(inotifyobj, "idle_off", peer_uuid, app_uuid,
                                  inotify_input_base.REGULAR,
                                  self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

        logging.warning("Exited Idleness and starting the server loop\n")

        # TODO the iteration shouldn't be hardcoded
        app_uuid = {}
        curr_time_ctlreqobj = {}
        for i in range(4):

            '''
            Generate UUID for the application to be used in the outfilename.
            '''
            app_uuid[i] = genericcmdobj.generate_uuid()

            # Once server is started, verify that the timestamp progresses
            curr_time_ctlreqobj[i] = CtlRequest(inotifyobj, "current_time", peer_uuid, app_uuid[i],
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

            time_global.sleep(1)

        '''
        Compare the timestamp and verify time
        is progressing.
        '''
        recipe_failed = 0
        logging.warning("Compare the timestamp and it should be progressing.")
        for i in range(3):
            '''
            Add curr_time_ctl object into stage2_rule_table to perform the rule checks
            on it.
            '''
            curr_time_ctl = []
            orig_time_ctl = []

            curr_time_ctl.append(curr_time_ctlreqobj[i+1])
            orig_time_ctl.append(curr_time_ctlreqobj[i])

            # Now access stage2_rule_table
            self.stage_rule_table[1]["ctlreqobj"] = curr_time_ctl
            self.stage_rule_table[1]["orig_ctlreqobj"] = orig_time_ctl

            recipe_failed = verify_rule_table(self.stage_rule_table[1])

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
