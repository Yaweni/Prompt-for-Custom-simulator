import numpy as np
import collections

class MetricsCollector:
    def __init__(self, env):
        self.env = env
        self.rtts = []
        self.successful_transactions = 0
        self.goodput_bytes = 0
        self.legit_packets_sent = 0
        
        self.packet_drops = collections.defaultdict(int)
        self.packets_processed = collections.defaultdict(int)
        
        # This dictionary is used to store queue length samples
        self.queue_lengths = collections.defaultdict(list)
        self.node_ids_to_monitor = set()

    def add_node_to_monitor(self, node_id):
        self.node_ids_to_monitor.add(node_id)

    # THIS IS THE MISSING METHOD THAT NEEDS TO BE ADDED BACK
    def record_queue_arrival(self, node_id, queue_len_packets):
        """Records a snapshot of a node's queue length."""
        if node_id in self.node_ids_to_monitor:
            self.queue_lengths[node_id].append(queue_len_packets)

    def record_rtt(self, rtt):
        self.rtts.append(rtt)

    def record_successful_transaction(self, reply_packet):
        self.successful_transactions += 1
        self.goodput_bytes += reply_packet.size_bytes

    def record_legit_packet_sent(self):
        self.legit_packets_sent += 1
        
    def record_packet_drop(self, node_id, packet, reason):
        key = f"drop_{node_id}_{reason}"
        self.packet_drops[key] += 1

    def record_packet_processed(self, node_id):
        self.packets_processed[node_id] += 1

    def _get_queue_stats(self, node_id):
        lengths = self.queue_lengths.get(node_id, [0])
        if not lengths: return 0, 0
        return np.mean(lengths), np.max(lengths)

    def generate_report(self):
        duration_s = self.env.duration_ms / 1000.0
        cfg = self.env.config
        
        goodput_mbps = (self.goodput_bytes * 8) / (duration_s * 1_000_000) if duration_s > 0 else 0
        avg_rtt = np.mean(self.rtts) if self.rtts else -1
        median_rtt = np.median(self.rtts) if self.rtts else -1
        p95_rtt = np.percentile(self.rtts, 95) if self.rtts else -1

        fw_avg_q, fw_max_q = self._get_queue_stats('FW')
        srv_avg_q, srv_max_q = self._get_queue_stats('SRV')
        
        scrubber1_id = self.env.scrubber_ids.get(1)
        scrubber2_id = self.env.scrubber_ids.get(2)
        s1_avg_q, s1_max_q = self._get_queue_stats(scrubber1_id) if scrubber1_id else (0,0)
        s2_avg_q, s2_max_q = self._get_queue_stats(scrubber2_id) if scrubber2_id else (0,0)

        fw_drops_mitigation = self.packet_drops.get('drop_FW_FIREWALL_MITIGATION', 0)
        fw_drops_queue = self.packet_drops.get('drop_FW_QUEUE_OVERFLOW', 0)
        s1_drops_scrub = self.packet_drops.get(f"drop_{scrubber1_id}_SCRUBBER_MITIGATION", 0) if scrubber1_id else 0
        s1_drops_queue = self.packet_drops.get(f"drop_{scrubber1_id}_QUEUE_OVERFLOW", 0) if scrubber1_id else 0
        s2_drops_scrub = self.packet_drops.get(f"drop_{scrubber2_id}_SCRUBBER_MITIGATION", 0) if scrubber2_id else 0
        s2_drops_queue = self.packet_drops.get(f"drop_{scrubber2_id}_QUEUE_OVERFLOW", 0) if scrubber2_id else 0
        server_drops_queue = self.packet_drops.get('drop_SRV_QUEUE_OVERFLOW', 0)
        
        return {
            "Run_ID": cfg['run_id'],
            "Scenario_Type": cfg['scenario_type'],
            "Attack_Style": cfg['attack_traffic']['style'],
            "Attack_PPS": cfg['attack_traffic']['total_attack_pps'],
            "Attack_Style2_Multiplier": cfg['attack_traffic'].get('attack_style2_multiplier', 'N/A'),
            "FW_PPS_Capacity": cfg.get('firewall_centralized', {}).get('processing_capacity_pps', 'N/A'),
            "Scrubber_Choice": cfg.get('distributed_mitigation', {}).get('scrubber1_id', 'N/A'),
            "Goodput_Mbps": f"{goodput_mbps:.2f}",
            "Successful_Transactions": self.successful_transactions,
            "Avg_RTT_ms": f"{avg_rtt:.2f}",
            "P95_RTT_ms": f"{p95_rtt:.2f}",
            "FW_Packets_Processed": self.packets_processed.get('FW', 0),
            "FW_Dropped_Mitigation": fw_drops_mitigation,
            "FW_Dropped_Queue": fw_drops_queue,
            "FW_Avg_Queue_Len": f"{fw_avg_q:.2f}",
            "Scrubber1_ID": scrubber1_id,
            "S1_Packets_Processed": self.packets_processed.get(scrubber1_id, 0),
            "S1_Dropped_Mitigation": s1_drops_scrub,
            "S1_Dropped_Queue": s1_drops_queue,
            "S1_Avg_Queue_Len": f"{s1_avg_q:.2f}",
            "Scrubber2_ID": scrubber2_id,
            "S2_Packets_Processed": self.packets_processed.get(scrubber2_id, 0),
            "S2_Dropped_Mitigation": s2_drops_scrub,
            "S2_Dropped_Queue": s2_drops_queue,
            "S2_Avg_Queue_Len": f"{s2_avg_q:.2f}",
            "Server_Dropped_Queue": server_drops_queue
        }