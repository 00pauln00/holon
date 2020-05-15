class NiovaCluster:

    raftconfobj = {}
    raftuuidobj = {}
    inotifyobj = {} # Could be array
    raftserver = [] # Array
    raftclient = [] # Array
    raftprocess = [] # Array
    nserver = 0 # number of server objects created
    nclient = 0 # number of client objects created
    nprocess = 0 # number of processes(server/client) started

    '''
        Method: assign_raft_conf_obj
        Purpose: store the raft conf object.
        Parameters:
    '''
    def assign_raft_conf_obj(self, raftconf):
        self.raftconfobj = raftconf

    '''
        Method: assign_raft_uuid_obj
        Purpose: store the raft uuid object.
        Parameters:
    '''
    def assign_raft_uuid_obj(self, raftuuid):
        self.raftuuidobj = raftuuid

    '''
        Method: assign_inotify_obj
        Purpose: store the inotify object.
        Parameters:
    '''
    def assign_inotify_obj(self, inotify):
        self.inotifyobj = inotify

    '''
        Method: assign_raftserver_obj
        Purpose: store the raft server object.
        Parameters:
    '''
    def assign_raftserver_obj(self, raftserver):
        self.raftserver.append(raftserver)
        self.nserver += 1

    '''
        Method: assign_raft_client_obj
        Purpose: store the raft client object.
        Parameters:
    '''
    def assign_raftclient_obj(self, raftclient):
        print("Value of nclient")
        print(self.nclient)
        self.raftclient.append(raftclient)
        self.nclient += 1

    '''
        Method: assign_raft_process_obj
        Purpose: store the raft process object.
        Parameters:
    '''
    def assign_raftprocess_obj(self, raftprocess):
        self.raftprocess.append(raftprocess)
        self.nprocess += 1
