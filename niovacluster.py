class NiovaCluster:

    raftnpeers = 0 # Number of servers in the cluster
    raftconfobj = {} #Raftcong object
    inotifyobj = {} # Could be array
    raftserver = {} # dictionary to store peer:raftserverobj 
    raftclient = {} # dictionary to store peer:raftclientobj
    raftserverprocess = {} # dictionary to store peer:serverprocessobj
    raftclientprocess = {} # dictionary to store peer:clientprocessobj

    '''
        Method: Constructor
        Purpose: Create object and initialize the raaftnpeers.
    '''
    def __init__(self, npeers):
        self.raftnpeers = npeers

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

    '''
        Method: raft_client_obj_store
        Purpose: store the raft client object at the clientno index.
        Parameters:
    '''
    def raftclient_obj_store(self, raftclient, clientno):
        self.raftclient[clientno] = raftclient

    '''
        Method: raft_process_obj_store
        Purpose: store the raft process object.
        Parameters:
    '''
    def raftprocess_obj_store(self, raftprocess, index):
        if raftprocess.process_type == "server":
            self.raftserverprocess[index] = raftprocess
        else:
            self.raftclientprocess[index] = raftprocess
