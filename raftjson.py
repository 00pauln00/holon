import os, json, sys

class RaftJson:

    def json_parse_and_verify_server_idleness(self, server_outfile):

        with open(server_outfile, "r") as read_file:
            data = json.load(read_file)
             # Verify "leader-uuid" : ""
            leader_uuid = data["raft_root_entry"][0]["leader-uuid"]
            if leader_uuid != "":
                print(f"Error: Leader uuid is set: {leader_uuid}")
                exit()

            server_state = data["raft_root_entry"][0]["state"]
            if server_state != "follower" and server_state != "candidate":
                print(f"Error: Peer state is not follower: %s" % server_state)
                exit()

            commit_idx = data["raft_root_entry"][0]["commit-idx"]
            if commit_idx != -1:
                print(f"commit-idx is not -1: {commit_idx}")
                exit()

            last_applied = data["raft_root_entry"][0]["last-applied"]
            if last_applied != -1:
                print(f"last-applied is not -1: {last_applied}")
                exit()

            last_applied_cumulative_crc = data["raft_root_entry"][0]["last-applied-cumulative-crc"]
            if last_applied_cumulative_crc != 0:
                print(f"last-applied-cumulative-crc is not zero: ${last_applied_cumulative_crc}")
                exit()

        print(f"Idleness of server is successful!!")


    def json_parse_and_verify_client_idleness(self, client_outfile):
        print(f"Verify clientout JSON file: %s" % client_outfile)
        with open(client_outfile, "r") as read_file:
            data = json.load(read_file)
             # Verify "leader-uuid" : ""
            initialized = data["raft_client_app"]["initialized"]
            if initialized != False:
                print(f"Error: Client initialized even with idleness init command: %s" % initialized)
                exit()

            committed_seqno = data["raft_client_app"]["committed-seqno"]
            if committed_seqno != 0:
                print(f"Error: Committted seqno is not zero: %s" % committed_seqno)
                exit()

            committed_xor_sum = data["raft_client_app"]["committed-xor-sum"]
            if committed_xor_sum != 0:
                print(f"Error: committed-xor-sum is not zero: %s" % committed_xor_sum)
                exit()

            pending_seqno = data["raft_client_app"]["pending-seqno"]
            if pending_seqno != -1:
                print(f"Error: pending-seqno is not -1: %s" % pending_seqno)
                exit()

            pending_value = data["raft_client_app"]["pending-value"]
            if pending_value != -1:
                print(f"Error: pending-value is not -1: %s" % pending_value)
                exit()

            pending_msg_id = data["raft_client_app"]["pending-msg-id"]
            if pending_msg_id != 0:
                print(f"Error: pending-msg-id is not 0: %s" % pending_msg_id)
                exit()

            last_retried_seqno = data["raft_client_app"]["last-retried-seqno"]
            if last_retried_seqno != 0:
                print(f"Error: last-retried-seqno is not 0: %s" % last_retried_seqno)
                exit()

            num_write_retries = data["raft_client_app"]["num-write-retries"]
            if num_write_retries != 0:
                print(f"Error: num-write-retries is not 0: %s" % num_write_retries)
                exit()

            last_validated_seqno = data["raft_client_app"]["last-validated-seqno"]
            if last_validated_seqno != 0:
                print(f"Error: last-validated-seqno is not 0: %s" % last_validated_seqno)
                exit()

            last_validated_xor_sum = data["raft_client_app"]["last-validated-xor-sum"]
            if last_validated_xor_sum != 0:
                print(f"Error: last-validated-xor-sum is not 0: %s" % last_validated_xor_sum)
                exit()

            leader_alive_cnt = data["raft_client_app"]["leader-alive-cnt"]
            if leader_alive_cnt != 0:
                print(f"Error: leader-alive-cnt is not 0: %s" % leader_alive_cnt)
                exit()

            print("Idleness of client is successful!!")

    def json_parse_and_return_curr_time(self, outfile):
        with open(outfile) as f:
            data = json.load(f)
            curr_time_string = data["system_info"]["current_time"]
            time_string = curr_time_string.split()
            return time_string[3]

