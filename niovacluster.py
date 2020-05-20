class NiovaCluster:

    raftconfobj = {}
    raftuuidobj = {}
    inotifyobj = {} # Could be array
    raftserver = [] # Array
    raftclient = [] # Array
    raftserverprocess = [] # Server process Array
    raftclientprocess = [] # Server process Array
    nserver = 0 # number of server objects created
    nclient = 0 # number of client objects created
    nprocess = 0 # number of processes(server/client) started

    '''
        Method: raft_conf_obj_store
        Purpose: store the raft conf object.
        Parameters:
    '''
    def raft_conf_obj_store(self, raftconf):
        self.raftconfobj = raftconf

    '''
        Method: inotify_obj_store
        Purpose: store the inotify object.
        Parameters:
    '''
    def inotify_obj_store(self, inotify):
        self.inotifyobj = inotify

    '''
        Method: raftserver_obj_store
        Purpose: store the raft server object.
        Parameters:
    '''
    def raftserver_obj_store(self, raftserver):
        self.raftserver.append(raftserver)
        self.nserver += 1

    '''
        Method: raft_client_obj_store
        Purpose: store the raft client object.
        Parameters:
    '''
    def raftclient_obj_store(self, raftclient):
        self.raftclient.append(raftclient)
        self.nclient += 1

    '''
        Method: raft_process_obj_store
        Purpose: store the raft process object.
        Parameters:
    '''
    def raftprocess_obj_store(self, raftprocess):
        if raftprocess.process_type == "server":
            self.raftserverprocess.append(raftprocess)
        else:
            self.raftclientprocess.append(raftprocess)

        self.nprocess += 1
