import os
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
          print("INOTIFY_PATH:", os.environ['NIOVA_INOTIFY_BASE_PATH'])
      else:
          os.environ['NIOVA_INOTIFY_PATH'] = inotify_path
          print("INOTIFY_PATH:", os.environ['NIOVA_INOTIFY_PATH'])


  '''
    Method: init path initialization
    Purpose: export init path
    Parameters: @init_path: Init directory path
  '''
  def export_init_path(self, init_path):
      self.inotify_init_path = init_path
      os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'] = init_path
      print("INOTIFY_INIT_PATH:", os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'])


  '''
    Method: copy_cmd_file
    Purpose: Copy {cmd_file} to input dir
    Parameters: @peer_uuid: Peer UUID to copy the command file into it's input
                directory.
                @cmd_file_path: Path of the command file to copy.
  '''
  def copy_cmd_file(self,genericcmdobj, peer_uuid, cmd_file_path):
    input_dir = "%s/%s/input" % (self.inotify_path, peer_uuid)
    try:
        genericcmdobj.copy_file(cmd_file_path , input_dir)
    except FileNotFoundError:
        print("File not found!")      
