import heapq
import logging
from components import *
from metrics import MetricsCollector

class TopologyBuilder:
    # ... (init is fine) ...
    def __init__(self, env, config):
        self.env = env
        self.config = config
        self.nodes = {}

    def build(self):
        # ... (this method is fine) ...
        scenario = self.config['scenario_type']
        if scenario == "NoMitigation":
            self._build_no_mitigation()
        elif scenario == "Centralized":
            self._build_centralized()
        elif scenario == "Distributed":
            self._build_distributed()
        else:
            raise ValueError(f"Unknown scenario type: {scenario}")
        
        self._add_attackers()
        return self.nodes

    def _add_node(self, node):
        self.nodes[node.id] = node
        self.env.metrics.add_node_to_monitor(node.id)

    def _link(self, n1_id, n2_id, bw_bps, prop_delay_ms):
        n1 = self.nodes[n1_id]
        n2 = self.nodes[n2_id]
        n1.add_link(n2, bw_bps, prop_delay_ms)
        n2.add_link(n1, bw_bps, prop_delay_ms)
        logging.info(f"Linking {n1_id} <-> {n2_id} at {bw_bps/1e9:.2f} Gbps")

    # NEW: Helper for adding routes
    def _route(self, from_id, to_id, via_id):
        self.nodes[from_id].add_route(to_id, via_id)
        logging.info(f"Routing from {from_id} to {to_id} via {via_id}")

    # UPDATED: Now includes routing
    def _build_no_mitigation(self):
        lc = self.config['legitimate_traffic']
        sc = self.config['server_config']
        links = self.config['network_links']

        # Create nodes
        client = LegitimateClientNode(self.env, 'CLIENT', 'SRV', lc['request_interval_ms'], lc['request_size_bytes'], lc['reply_size_bytes'])
        switch = SwitchNode(self.env, 'SW', 1_000_000)
        server = ServerNode(self.env, 'SRV', lc['server_processing_delay_ms'], sc['queue_max_bytes'])
        
        self._add_node(client)
        self._add_node(switch)
        self._add_node(server)

        # Create links
        self._link('CLIENT', 'SW', links['default_bandwidth_bps'], links['default_propagation_delay_ms'])
        self._link('SW', 'SRV', sc['link_to_switch_bw_bps'], links['default_propagation_delay_ms'])

        # Create routes
        self._route('CLIENT', 'SRV', 'SW') # To get to SRV, client must go via SW
        self._route('SW', 'SRV', 'SRV')     # SW is directly connected to SRV
        self._route('SRV', 'CLIENT', 'SW') # To get back to CLIENT, server must go via SW
        self._route('SW', 'CLIENT', 'CLIENT') # SW is directly connected to CLIENT
    
    # UPDATED: Now includes routing
    def _build_centralized(self):
        lc = self.config['legitimate_traffic']
        fc = self.config['firewall_centralized']
        sc = self.config['server_config']
        links = self.config['network_links']

        # Create nodes
        client = LegitimateClientNode(self.env, 'CLIENT', 'SRV', lc['request_interval_ms'], lc['request_size_bytes'], lc['reply_size_bytes'])
        firewall = FirewallNode(self.env, 'FW', fc['queue_max_bytes'], fc['processing_capacity_pps'])
        server = ServerNode(self.env, 'SRV', lc['server_processing_delay_ms'], sc['queue_max_bytes'])

        self._add_node(client)
        self._add_node(firewall)
        self._add_node(server)

        # Create links
        self._link('CLIENT', 'FW', fc['interface_speed_bps'], links['default_propagation_delay_ms'])
        self._link('FW', 'SRV', fc['interface_speed_bps'], links['default_propagation_delay_ms'])

        # Create routes
        self._route('CLIENT', 'SRV', 'FW')
        self._route('FW', 'SRV', 'SRV')
        self._route('SRV', 'CLIENT', 'FW')
        self._route('FW', 'CLIENT', 'CLIENT')

    # UPDATED: Now includes routing
    

    
    def _build_distributed(self):
        lc = self.config['legitimate_traffic']
        fc = self.config['firewall_centralized']
        dc = self.config['distributed_mitigation']
        sc = self.config['server_config']
        links = self.config['network_links']

        # 1. Identify the three ingress/egress points
        scrubber1_id = dc['scrubber1_id']
        scrubber2_id = dc['scrubber2_id']
        balanced_hops = ['FW', scrubber1_id, scrubber2_id]
        self.env.scrubber_ids = {1: scrubber1_id, 2: scrubber2_id}

        # 2. Create nodes (Client is now a standard LegitimateClientNode)
        client = LegitimateClientNode(self.env, 'CLIENT', 'SRV', lc['request_interval_ms'],
                                    lc['request_size_bytes'], lc['reply_size_bytes'])
        firewall = FirewallNode(self.env, 'FW', fc['queue_max_bytes'], fc['processing_capacity_pps'])
        sw5 = SwitchNode(self.env, 'SW5', 2_000_000)
        server = ServerNode(self.env, 'SRV', lc['server_processing_delay_ms'], sc['queue_max_bytes'])
        self._add_node(client); self._add_node(firewall); self._add_node(sw5); self._add_node(server)
        
        for sw_id, sw_config in dc['scrubber_configs'].items():
            is_scrubber = sw_id in [scrubber1_id, scrubber2_id]
            
            # THE MODIFICATION IS HERE:
            # Get BOTH custom delay values from the config for this switch type
            base_delay = sw_config.get('processing_delay_ms')
            scrub_delay = sw_config.get('scrubber_processing_delay_ms')
            
            # Pass BOTH custom delays to the SwitchNode constructor
            sw = SwitchNode(self.env, sw_id, sw_config['queue_max_bytes'], 
                            is_scrubber=is_scrubber, 
                            processing_delay_ms=base_delay,
                            scrubber_processing_delay_ms=scrub_delay)
            self._add_node(sw)

        # 3. Link nodes
        # Link client to its three egress points
        self._link('CLIENT', 'FW', fc['interface_speed_bps'], links['default_propagation_delay_ms'])
        self._link('CLIENT', scrubber1_id, dc['scrubber_configs'][scrubber1_id]['bandwidth_bps'], links['default_propagation_delay_ms'])
        self._link('CLIENT', scrubber2_id, dc['scrubber_configs'][scrubber2_id]['bandwidth_bps'], links['default_propagation_delay_ms'])
        # Link all ingress points to the aggregator SW5
        for hop_id in balanced_hops:
            self._link(hop_id, 'SW5', self.nodes[hop_id].links['CLIENT'].bandwidth_bps, links['default_propagation_delay_ms'])
        # Link aggregator to server
        self._link('SW5', 'SRV', sc['link_to_switch_bw_bps'], links['default_propagation_delay_ms'])

        # 4. Create SYMMETRIC, LOAD-BALANCED routes
        # -- FORWARD PATH (Client -> Server) --
        # For each balanced hop, add a route from the client to the server via that hop
        for hop_id in balanced_hops:
            self._route('CLIENT', 'SRV', hop_id)
            self._route(hop_id, 'SRV', 'SW5') # From any ingress, go to SW5
        self._route('SW5', 'SRV', 'SRV') # From SW5, go to Server

        # -- RETURN PATH (Server -> Client) --
        # From server, go to SW5
        self._route('SRV', 'CLIENT', 'SW5')
        # From SW5, round-robin back through the balanced hops
        for hop_id in balanced_hops:
            self._route('SW5', 'CLIENT', hop_id)
            self._route(hop_id, 'CLIENT', 'CLIENT') # From ingress, go to Client
    
    # UPDATED: Needs to add routes for attackers
    def _add_attackers(self):
        ac = self.config['attack_traffic']
        if not ac.get('present', False):
            return
        
        num_attackers = ac['num_total_attackers']
        if num_attackers == 0: return

        pps_per_attacker = ac['total_attack_pps'] / num_attackers
        
        targets = self._get_attack_targets()
        
        for i in range(num_attackers):
            attacker_id = f'ATTACKER_{i}'
            target_node_id = targets[i % len(targets)]
            attacker = AttackNode(self.env, attacker_id, 'SRV', pps_per_attacker, 
                                ac['attack_packet_size_bytes'], ac['style'])
            self._add_node(attacker)
            
            # Link attacker to its first hop target
            self._link(attacker_id, target_node_id, 10_000_000_000, 0.01)
            # Add route for the attacker
            self._route(attacker_id, 'SRV', target_node_id)


    def _get_attack_targets(self):
    # ... (this method is fine as is)
        scenario = self.config['scenario_type']
        if scenario == 'NoMitigation':
            return ['SW']
        elif scenario == 'Centralized':
            return ['FW']
        elif scenario == 'Distributed':
            dc = self.config['distributed_mitigation']
            return ['FW', dc['scrubber1_id'], dc['scrubber2_id']]
        return []

class Simulation:
    def __init__(self, config):
        self.config = config
        self.now = 0.0
        self.duration_ms = config['duration_seconds'] * 1000
        self.events = []
        self.event_counter = 0
        self.metrics = MetricsCollector(self)
        self.scrubber_ids = {} # Populated by topology builder

        builder = TopologyBuilder(self, config)
        self.nodes = builder.build()
        Packet._id_counter = 0 # Reset for determinism

    def schedule_event(self, delay_ms, callback, event_type, **kwargs):
        event_time = self.now + delay_ms
        if event_time < self.duration_ms:
            # Tie-break with a unique counter
            heapq.heappush(self.events, (event_time, self.event_counter, callback, event_type, kwargs))
            self.event_counter += 1

    def run(self):
        logging.info(f"--- Starting Simulation: {self.config['run_id']} ---")
        
        # Initial events
        self.nodes['CLIENT'].start()
        for node_id, node in self.nodes.items():
            if isinstance(node, AttackNode):
                node.start()

        # Main event loop
        while self.events:
            event_time, _, callback, event_type, kwargs = heapq.heappop(self.events)
            
            if event_time >= self.duration_ms:
                break
                
            self.now = event_time
            logging.debug(f"Executing event {event_type} at {self.now:.4f} with {kwargs}")
            callback(**kwargs)

        logging.info(f"--- Simulation Finished at {self.now:.4f} ms ---")
        return self.metrics.generate_report()