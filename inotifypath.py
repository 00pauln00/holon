import os, logging
import subprocess

class InotifyPath:
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
    def __init__(self, inotify_path, inotify_is_base_path):
        self.inotify_path = inotify_path
        self.inotify_is_base_path = inotify_is_base_path
        if inotify_is_base_path:
            os.environ['NIOVA_INOTIFY_BASE_PATH'] = inotify_path
            logging.warning("exporting NIOVA_INOTIFY_BASE_PATH=%s", os.environ['NIOVA_INOTIFY_BASE_PATH'])
        else:
            os.environ['NIOVA_INOTIFY_PATH'] = inotify_path
            logging.warning("exporting NIOVA_INOTIFY_PATH=%s", os.environ['NIOVA_INOTIFY_PATH'])


    '''
    Method: init path initialization
    Purpose: export init path
    Parameters: @init_path: Init directory path
    '''
    def export_init_path(self, init_path):
        self.inotify_init_path = init_path
        os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'] = init_path
        logging.warning("exporting NIOVA_CTL_INTERFACE_INIT_PATH=%s", os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'])


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
    def prepare_init_path(self, base_fname, app_uuid):
        fpath = "%s/%s.%s" % (self.inotify_init_path, base_fname, app_uuid)
        return fpath
