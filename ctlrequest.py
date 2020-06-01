import os
import subprocess
from basicio import BasicIO
from genericcmd import GenericCmds

def ctl_req_create_cmdfile_and_copy(ctlreqobj):
    basicioobj = BasicIO()
    genericcmdobj = GenericCmds()

    o_base = os.path.basename(ctlreqobj.output_fpath)
    i_base = os.path.basename(ctlreqobj.input_fpath)
    cmd_str = "%s\nOUTFILE /%s\n" % (ctlreqobj.ctl_cmd_dict[ctlreqobj.cmd], o_base)

    # Before copying the cmdfile, remove the output file if it already exits.
    if os.path.exists(ctlreqobj.output_fpath):
        genericcmdobj.remove_file(ctlreqobj.output_fpath)

    # Write the cmd to tmpfile.
    tmp_file = "/tmp/%s" % i_base

    fd = basicioobj.open_file(tmp_file)
    basicioobj.write_file(fd, cmd_str)
    basicioobj.close_file(fd)

    genericcmdobj.move_file(tmp_file, ctlreqobj.input_fpath)


class CtlRequest:
    ctl_cmd_dict = {'idle_on':'APPLY ignore_timer_events@true\nWHERE /raft_net_info/ignore_timer_events',
        'idle_off':'APPLY ignore_timer_events@false\nWHERE /raft_net_info/ignore_timer_events',
        'get_all':'GET /.*/.*/.*/.*',
        'current_time':'GET /system_info/current_time',
        'get_term':'GET /raft_root_entry/term'
        }

    input_fpath = ""
    output_fpath = ""
    cmd = ""

    def __init__(self, inotifyobj, cmd, peer_uuid, app_uuid):

        self.cmd = cmd

        if cmd == "idle_on":
            self.input_fpath = inotifyobj.prepare_init_path(cmd, app_uuid)
        else:
            self.input_fpath = inotifyobj.prepare_input_output_path(peer_uuid,
                                                                    cmd, True,
                                                                    app_uuid)
            
        self.output_fpath = inotifyobj.prepare_input_output_path(peer_uuid,
                                                                cmd, False,
                                                                app_uuid)
        # Copy the cmd file into input directory
        ctl_req_create_cmdfile_and_copy(self)

    def delete_files(self):
        genericcmdobj = GenericCmds()

        print(f"Destroying ctl obj")
        if os.path.exists(self.input_fpath):
            print(f"Removing file: %s" % self.input_fpath)
            genericcmdobj.remove_file(self.input_fpath)

        if os.path.exists(self.output_fpath):
            print(f"Removing file: %s" % self.output_fpath)
            genericcmdobj.remove_file(self.output_fpath)

