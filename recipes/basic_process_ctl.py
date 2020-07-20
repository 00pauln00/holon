from holonrecipe import *
import logging
from recipe_verify import *
import json

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

        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(0)
        logging.warning("Pause and resume the peer: %s\n" % peer_uuid)

        '''
        Pause and Resume server for n iterations. After pausing the server,
        copy the cmd file into input directory. As process is paused, output
        file should not get generated.
        '''
        # TODO iteration count should not be hardcoded.
        recipe_failed = 0
        curr_time_ctlreqobj = {}
        app_uuid = {}
        for i in range(5):
            # pause the process
            serverproc.pause_process()
            logging.warning("pausing the process for 5secs and then resume")
            time_global.sleep(5)

            '''
            Generate UUID for the application to be used in the outfilename.
            '''
            app_uuid[i] = genericcmdobj.generate_uuid()

            curr_time_ctlreqobj[i] = CtlRequest(inotifyobj, "current_time", peer_uuid, app_uuid[i],
                                    inotify_input_base.REGULAR,
                                    self.recipe_ctl_req_obj_list).Apply_and_Wait(True)

            time_global.sleep(1)
            # Only check if output file got created.
            if os.path.exists(curr_time_ctlreqobj[i].output_fpath):
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

        #Load the rule table
        with open('rule_table/basic_process_ctl.json') as json_file:
            self.stage_rule_table = json.load(json_file)

        recipe_failed = 0
        for i in range(4):
            logging.warning("Copy the cmd file into input directory of server. Itr %d" % i)

            curr_time_ctlreqobj[i].Apply_and_Wait(False)
            time_global.sleep(1)
            '''
            Add curr_time_ctl object into stage1_rule_table to perform the rule checks
            on it.
            '''
            curr_time_ctl = []
            orig_time_ctl = []

            curr_time_ctl.append(curr_time_ctlreqobj[i])
            orig_time_ctl.append(curr_time_ctlreqobj[i+1])
 

            self.stage_rule_table["ctlreqobj"] = curr_time_ctl
            self.stage_rule_table["orig_ctlreqobj"] = orig_time_ctl

            recipe_failed = verify_rule_table(self.stage_rule_table)

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
