import os, logging
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
    if fd == None:
        return -1

    rc = basicioobj.write_file(fd, cmd_str)
    if rc == -1:
        return rc

    rc = basicioobj.close_file(fd)
    if rc == -1:
        return rc

    # Create input_fpath directory if does not exist already.
    if not os.path.exists(os.path.dirname(ctlreqobj.input_fpath)):
        genericcmdobj.make_dir(os.path.dirname(ctlreqobj.input_fpath))

    rc = genericcmdobj.move_file(tmp_file, ctlreqobj.input_fpath)
    if rc == -1:
        return rc

    return rc


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
    error = 0

    def __init__(self, inotifyobj, cmd, peer_uuid, app_uuid, shared_init,
                 ctlreq_list):

        self.cmd = cmd

        if cmd == "idle_on":
            self.input_fpath = inotifyobj.prepare_init_path(peer_uuid, cmd,
                                                            app_uuid,
                                                            shared_init)
            # export the init path
            inotifyobj.export_init_path(peer_uuid, shared_init)

        else:
            self.input_fpath = inotifyobj.prepare_input_output_path(peer_uuid,
                                                                    cmd, True,
                                                                    app_uuid)

        self.output_fpath = inotifyobj.prepare_input_output_path(peer_uuid,
                                                                 cmd, False,
                                                                 app_uuid)
        # Add the ctlreqobj on the recipe list.
        ctlreq_list.append(self)

        # Copy the cmd file into input directory
        #ctl_req_create_cmdfile_and_copy(self)

    def Apply(self):
        logging.warning("APPLY cmd=%s ipath=%s", self.cmd, self.input_fpath)
        '''
        Store the return code inside object only so the caller can check for
        the error later.
        '''
        self.error = ctl_req_create_cmdfile_and_copy(self)
        return self

    def Error(self):
        return self.error

    def delete_files(self):
        genericcmdobj = GenericCmds()

        logging.warning("Destroying ctl obj")
        if os.path.exists(self.input_fpath):
            logging.warning("Removing file: %s" % self.input_fpath)
            genericcmdobj.remove_file(self.input_fpath)

        if os.path.exists(self.output_fpath):
            logging.warning("Removing file: %s" % self.output_fpath)
            genericcmdobj.remove_file(self.output_fpath)

