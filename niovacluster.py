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
        Method: Constructor
        Purpose: Create object and initialize the raaftnpeers.
    '''
    def __init__(self, npeers):
        self.raftnpeers = npeers
        '''
        Preallocate the list for servers as per the number of peers in the
        cluster
        '''
        self.raftserver = [None] * npeers
        self.raftserverprocess = [None] * npeers

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
        Purpose: store the raft server object at the peerno index
        Parameters:
    '''
    def raftserver_obj_store(self, raftserver, peerno):
        self.raftserver[peerno] = raftserver
        self.nserver += 1

    '''
        Method: raft_client_obj_store
        Purpose: store the raft client object at the clientno index.
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
    def raftprocess_obj_store(self, raftprocess, index):
        if raftprocess.process_type == "server":
            self.raftserverprocess[index] = raftprocess
        else:
            self.raftclientprocess.append(raftprocess)

        self.nprocess += 1
