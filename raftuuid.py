import os
import subprocess

class RaftUUID:

    raft_uuid = ''

    '''
        Method: generate_raft_uuid
        Purpose: generate UUID usinf /usr/bin/uuid
        Parameters:
    '''
    def generate_raft_uuid(self):
        p = subprocess.Popen(["/usr/bin/uuid"], stdout=subprocess.PIPE)
        (stdout, err) = p.communicate()
        raft_uuid_bytes=stdout.strip()
        raft_uuid = raft_uuid_bytes.decode('utf-8')
        self.raft_uuid = raft_uuid


    '''
        Method: write_raft_uuid_to_raft_conf
        Purpose: write raft uuid to raft conf
        Parameters:
    '''
    def write_raft_uuid_to_raft_conf(self, raft_conf):
        raft_conf_path = "%s/%s.raft" % (raft_conf.server_config_path, self.raft_uuid)
        print(raft_conf_path)

        f = open(raft_conf_path, "w+")
        f.write("RAFT %s\n" % (self.raft_uuid))
        f.close()
