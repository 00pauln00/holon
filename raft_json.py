import os, sys, json, logging, time

class RaftJson:

    leader_uuid = ''
    voted_for_uuid = ''
    peer_uuid = ''
    commit_idx = 0
    last_aplied = ''
    term = 0
    state = ''
    cumu_crc = 0
    newest_entry_idx = 0
    newest_entry_term = 0
    newest_entry_dsize = 0
    newest_entry_crc = 0
    current_time_string = '' 
    self_uuid = ''
    net_rcv_enabled = {}
    client_req = ''
    ignore_timer = False
  
    def __init__(self, outfile, raftconfigobj):

        self.outfile = outfile
 
        #Sleep for 1 sec if file has not got created yet.
        while os.path.exists(outfile) == False:
            time.sleep(1)

        with open(outfile, "r") as f:
            raft_json_dict = json.load(f)
  
            #Extract the JSON Parameters
            self.leader_uuid = raft_json_dict["raft_root_entry"][0]["leader-uuid"]
   
            self.voted_for_uuid = raft_json_dict["raft_root_entry"][0]["voted-for-uuid"]

            self.peer_uuid = raft_json_dict["raft_root_entry"][0]["peer-uuid"]
    
            self.state = raft_json_dict["raft_root_entry"][0]["state"]
  
            self.term = raft_json_dict["raft_root_entry"][0]["term"]
   
            self.commit_idx = raft_json_dict["raft_root_entry"][0]["commit-idx"]

            self.last_applied = raft_json_dict["raft_root_entry"][0]["last-applied"]

            self.cumu_crc = raft_json_dict["raft_root_entry"][0]["last-applied-cumulative-crc"]

            self.newest_entry_idx = raft_json_dict["raft_root_entry"][0]["newest-entry-idx"]

            self.newest_entry_term = raft_json_dict["raft_root_entry"][0]["newest-entry-term"]

            self.newest_entry_dsize = raft_json_dict["raft_root_entry"][0]["newest-entry-data-size"] 

            self.newest_entry_crc = raft_json_dict["raft_root_entry"][0]["newest-entry-crc"]

            self.current_time_string = raft_json_dict["system_info"]["current_time"]

            self.client_req = raft_json_dict["raft_root_entry"][0]["client-requests"]

            self.self_uuid = raft_json_dict["raft_root_entry"][0]["peer-uuid"]

            #self.net_rcv_enable = raft_json_dict["ctl_svc_nodes"][1]["net_recv_enabled"]

            self.ignore_timer = raft_json_dict["raft_net_info"]["ignore_timer_events"]
            for p in range(raftconfigobj.nservers + 1):
                server_type = raft_json_dict["ctl_svc_nodes"][p]["type"]
                if server_type == "raft-server":
                    self.net_rcv_enabled[self.peer_uuid] = raft_json_dict["ctl_svc_nodes"][p]["net_recv_enabled"]
