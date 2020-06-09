import os, logging
import subprocess
from genericcmd import GenericCmds

class InotifyPath:
    base_dir_path = ''
    inotify_path = ''
    inotify_init_path = ''
    inotify_is_base_path = ''
    '''
    Constructor:
    Purpose: Initialisation
    Parameters: @inotify_path: INOTIFY directory path.
                @inotify_is_base_path: Is this NIOVA_INOTIFY_BASE_PATH
                path? (True/False)
    '''
    def __init__(self, base_dir_path, inotify_is_base_path):
        self.inotify_path = "%s/inotify" % base_dir_path
        self.inotify_shared_init_path = "%s/init" % base_dir_path
        self.inotify_is_base_path = inotify_is_base_path

        # Create inotify and init directories
        genericcmdobj = GenericCmds()
        genericcmdobj.make_dir(self.inotify_path)
        genericcmdobj.make_dir(self.inotify_shared_init_path)

        # export the inotify path
        if inotify_is_base_path:
            os.environ['NIOVA_INOTIFY_BASE_PATH'] = self.inotify_path
            logging.warning("exporting NIOVA_INOTIFY_BASE_PATH=%s",
                            os.environ['NIOVA_INOTIFY_BASE_PATH'])
        else:
            os.environ['NIOVA_INOTIFY_PATH'] = self.inotify_path
            logging.warning("exporting NIOVA_INOTIFY_PATH=%s",
                            os.environ['NIOVA_INOTIFY_PATH'])


    '''
    Method: init path initialization
    Purpose: export init path
    Parameters: @init_path: Init directory path
    '''
    def export_init_path(self, peer_uuid, shared_path):

        genericcmdobj = GenericCmds()

        '''
        if shared_path is true, use the shared init path.
        else use the init directory path inside inotify/peer_uuid/init
        '''
        if shared_path:
            init_path = self.inotify_shared_init_path
        else:
            init_path = "%s/%s/init" % (self.inotify_path, peer_uuid)

        os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'] = init_path
        logging.warning("exporting NIOVA_CTL_INTERFACE_INIT_PATH=%s",
                        os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'])


    '''
    method: prepare input/output path.
    purpose: Prepare the absolute path for input/output files for specific
    peer_uuid and app_uuid
    '''
    def prepare_input_output_path(self, peer_uuid, base_fname, input_dir, app_uuid):
        dir_name = "output"
        if input_dir:
            dir_name = "input"

        fpath = "%s/%s/%s/%s.%s" % (self.inotify_path, peer_uuid, dir_name, base_fname,
                                    app_uuid)
        return fpath;

    '''
    method: prepare init cmd path.
    purpose: Prepare the absolute path for init command file.
    '''
    def prepare_init_path(self, peer_uuid, base_fname, app_uuid, shared_init):
        if shared_init:
            # The init file should get created inside shared init directory
            fpath = "%s/%s.%s" % (self.inotify_shared_init_path, base_fname, app_uuid)
        else:
            fpath = "%s/%s/init/%s.%s" % (self.inotify_path, peer_uuid, base_fname, app_uuid)
        return fpath
