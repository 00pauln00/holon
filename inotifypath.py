import os
import subprocess
class InotifyPath:
  inotify_path = ''
  inotify_init_path = ''
  inotify_is_base_path = ''
    '''
    Constructor:
    Purpose: Initialisation
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
    Parameters:
  '''
  def export_init_path(self, init_path):
      self.inotify_init_path = init_path
      os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'] = init_path
      print("INOTIFY_INIT_PATH:", os.environ['NIOVA_CTL_INTERFACE_INIT_PATH'])


  '''
    Method: copy_cmd_file
    Purpose: Copy {cmd_file} to input dir
    Parameters:
  '''
  def copy_cmd_file(self, peer_uuid, cmd_file):
    print(f"Copy {cmd_file} to input dir")
    input_dir = "%s/%s/input" % (self.inotify_path, peer_uuid)
    print("input directory path:%s"%(input_dir))
    subprocess.Popen(['cp', cmd_file, input_dir],stdout=subprocess.PIPE)
