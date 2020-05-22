import os
import subprocess
class CtlRequest:

    '''
    Method: ctl_req_init_idleness_cmd_create
    Purpose: Create idleness command file
    Parameters: @file_path
                @idleness: Idleness true or false
    '''
    def ctl_req_init_idleness_create(self, file_path, idleness):
        # Prepare the idleness cmd.
        with open(file_path, 'w+') as f:
            f.write('APPLY ignore_timer_events@%s\n' % idleness)
            f.write('WHERE /raft_net_info/ignore_timer_events\n')
            f.write('OUTFILE /err.out\n')

    '''
    Method: ctl_req_get_all_cmd_create
    Purpose: Create ctl request command to get all JSON output.
    Parameters: @cmd_file_path
    '''
    def ctl_req_get_all_cmd_create(self, cmd_file_path, outfilename):
        with open(cmd_file_path, "w+") as f:
            f.write("GET /.*/.*/.*/.*\n")
            f.write("OUTFILE %s\n" % (outfilename))

    '''
    Method: ctl_req_get_current_time_cmd_create
    Purpose: Create ctl request command to get the current time.
    Parameters: @cmd_file_path
    '''
    def ctl_req_get_current_time_cmd_create(self, cmd_file_path, outfilename):
        with open(cmd_file_path, "w+") as f:
            f.write("GET /system_info/current_time\n")
            f.write("OUTFILE %s\n" % (outfilename))

    '''
    Method: ctl_req_get_term_cmd_create
    Purpose: Create ctl request command to get the term value.
    Parameters: @cmd_file_path
    '''
    def ctl_req_get_term_cmd_create(self, cmd_file_path, outfilename):
        with open(cmd_file_path, "w+") as f:
            f.write("GET /raft_root_entry/term\n")
            f.write("OUTFILE %s\n" % (outfilename))
