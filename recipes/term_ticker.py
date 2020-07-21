from holonrecipe import *
from recipe_verify import *
import json

class Recipe(HolonRecipeBase):
    name = "term_ticker"
    desc = "Term Ticker Recipe\n"\
            "1. Verify term increases in each iteration.\n"\
            "2. Restart the server process and make sure term value persists\n"\
            "across reboot.\n"
    parent = "basic_process_ctl"
    recipe_proc_obj_list = []
    recipe_ctl_req_obj_list = []
    stage_rule_table = {}

    def print_desc(self):
        print(self.desc)

    def pre_run(self):
        return self.parent

    def run(self, clusterobj):
        logging.warning("=================Run Term Ticker recipe ====================\n")

        '''
        Extract the objects to be used from clusterobj.
        '''
        inotifyobj = clusterobj.inotifyobj
        raftconfobj = clusterobj.raftconfobj
        serverproc0 = clusterobj.raftserverprocess[0]

        # Create object for generic cmds.
        genericcmdobj = GenericCmds()

        peerno = 0
        peer_uuid = raftconfobj.get_peer_uuid_for_peerno(peerno)

        '''
        Run the loop to copy the command file for getting the term value
        and verifying in each iteration, term value increases.
        '''
        app_uuid = {}
        get_all_ctlreqobj = {}
        recipe_failed = 0

        # TODO Iteration value should be specified by user. 
        itr = 10
        logging.warning("Copy cmd file to get and verify term value\n")
        for i in range(itr):
            '''
            Generate UUID for the application to be used in the outfilename.
            '''
            app_uuid[i] = genericcmdobj.generate_uuid()

            '''
            Creating cmd file to get all the JSON output from the server.
            Will verify parameters from server JSON output to check term value.
            '''
            get_all_ctlreqobj[i] = CtlRequest(inotifyobj, "get_all", peer_uuid, app_uuid[i],
                                              inotify_input_base.REGULAR,
                                              self.recipe_ctl_req_obj_list).Apply_and_Wait(False)

            # sleep to allow term to get incremented
            time_global.sleep(3)

        #Load te rule table
        with open('rule_table/term_ticker.json') as json_file:
            self.stage_rule_table = json.load(json_file)

        for i in range(9):
            logging.warning("Copy the cmd file into input directory of server. Itr %d" % i)  
            '''
            Add get_all_ctl object into stage2_rule_table to perform the rule checks
            on it.
            '''
            get_all_ctl = []
            orig_get_all = []

            get_all_ctl.append(get_all_ctlreqobj[i+1])
            orig_get_all.append(get_all_ctlreqobj[i])
 
            # Now access stage2_rule_table
            self.stage_rule_table[0]["ctlreqobj"] = get_all_ctl
            self.stage_rule_table[0]["orig_ctlreqobj"] = orig_get_all

            recipe_failed = verify_rule_table(self.stage_rule_table[0])
            if recipe_failed:
                break

            #TODO verify total_writes - Term = 2

        if recipe_failed:
            logging.error("Term ticker recipe failed")
            return recipe_failed

        '''
        After reboot, server should have term value > previously strored term + 1 or 2. 
        I.e term value should persist across reboots.
        '''
        after_reboot_ctl = []
        before_reboot_ctl = []

        # Kill the server
        serverproc0.kill_process()

        # Restart the server
        serverproc0.start_process(raftconfobj, clusterobj)

        time_global.sleep(2)

        app_uuid = genericcmdobj.generate_uuid()
        after_reboot_ctlreq = CtlRequest(inotifyobj, "get_all", peer_uuid, app_uuid,
                                              inotify_input_base.REGULAR,
                                              self.recipe_ctl_req_obj_list).Apply_and_Wait(False)
        

        # Add the newly taken ctlreq object after reboot ctl list.
        after_reboot_ctl.append(after_reboot_ctlreq)

        # Use the last iteration ctlreqobj as before restart parameter.
        before_reboot_ctl.append(get_all_ctlreqobj[itr - 1])

        # Now access stage2_rule_table
        self.stage_rule_table[1]["ctlreqobj"] = after_reboot_ctl
        self.stage_rule_table[1]["orig_ctlreqobj"] = before_reboot_ctl
        
        recipe_failed = verify_rule_table(self.stage_rule_table[1])
        
        if recipe_failed:
            logging.error("Term Ticker Recipe Failed")
        else:
            logging.warning("Term ticker Recipe Successful, Raft Peer 0's term value increasing!!\n")

        return recipe_failed

    def post_run(self, clusterobj):
        logging.warning("Post run method")
        # Delete all the input and output files this recipe has written.
        for ctl_obj in self.recipe_ctl_req_obj_list:
            ctl_obj.delete_files()
