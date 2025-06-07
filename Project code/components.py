import collections
import logging

class Packet:
    """Represents a network packet."""
    _id_counter = 0
    def __init__(self, source_id, dest_id, size_bytes, type,
                 send_timestamp=0, original_request_id=None):
        self.id = Packet._id_counter
        Packet._id_counter += 1
        self.source_id = source_id
        self.destination_id = dest_id
        self.size_bytes = size_bytes
        self.type = type
        self.send_timestamp = send_timestamp
        # For replies to calculate RTT
        self.original_request_id = original_request_id if original_request_id is not None else self.id

    def __repr__(self):
        return (f"Packet(id={self.id}, type={self.type}, size={self.size_bytes}, "
                f"src={self.source_id}, dst={self.destination_id})")

class Queue:
    """A FIFO queue for a network node with a maximum size in bytes."""
    def __init__(self, max_size_bytes=float('inf')):
        self.queue = collections.deque()
        self.max_size_bytes = max_size_bytes
        self._current_size_bytes = 0

    def enqueue(self, packet):
        if self.is_full(packet):
            return False
        self.queue.append(packet)
        self._current_size_bytes += packet.size_bytes
        return True

    def dequeue(self):
        if not self.queue:
            return None
        packet = self.queue.popleft()
        self._current_size_bytes -= packet.size_bytes
        return packet

    def is_full(self, packet):
        return self.current_size_bytes + packet.size_bytes > self.max_size_bytes

    @property
    def current_size_bytes(self):
        return self._current_size_bytes
    
    @property
    def current_size_packets(self):
        return len(self.queue)
    
    def __len__(self):
        return len(self.queue)

class Link:
    """Represents a network link connecting two nodes."""
    def __init__(self, source, destination, bandwidth_bps, propagation_delay_ms):
        self.source = source
        self.destination = destination
        self.bandwidth_bps = bandwidth_bps
        self.propagation_delay_ms = propagation_delay_ms

    def get_transmission_delay_ms(self, packet):
        return (packet.size_bytes * 8) / self.bandwidth_bps * 1000

class Node:
    """Base class for all network devices."""
    def __init__(self, env, node_id, queue_max_bytes=float('inf')):
        self.env = env
        self.id = node_id
        self.queue = Queue(queue_max_bytes)
        self.links = {}
        # NEW: Routing table now supports multiple next hops for a destination
        self.routing_table = collections.defaultdict(list)
        # NEW: Tracks the index for the next round-robin choice per destination
        self.route_rr_index = collections.defaultdict(int)
        self.is_processing = False
        self.processing_delay_ms = 0.001

    def add_link(self, destination_node, bandwidth_bps, propagation_delay_ms):
        link = Link(self, destination_node, bandwidth_bps, propagation_delay_ms)
        self.links[destination_node.id] = link

    # NEW: Method to add a route
    def add_route(self, destination_id, next_hop_id):
        """Adds a potential next hop for a given final destination."""
        self.routing_table[destination_id].append(next_hop_id)

    def receive_packet(self, packet):
        logging.debug(f"[{self.env.now:.4f}] Node {self.id} received {packet}")
        if self.queue.enqueue(packet):
            self.env.metrics.record_queue_arrival(self.id, self.queue.current_size_packets)
            if not self.is_processing:
                self._schedule_next_processing()
        else:
            logging.warning(f"[{self.env.now:.4f}] Node {self.id} queue full. Dropping {packet}.")
            self.env.metrics.record_packet_drop(self.id, packet, "QUEUE_OVERFLOW")
    
    def _schedule_next_processing(self):
        # ... (this method is unchanged)
        if len(self.queue) > 0 and not self.is_processing:
            self.is_processing = True
            self.env.schedule_event(0, self._start_processing_packet, "PROCESS")

    def _start_processing_packet(self):
        # ... (this method is unchanged)
        packet = self.queue.dequeue()
        if not packet:
            self.is_processing = False
            return
        
        self.env.metrics.record_packet_processed(self.id)
        logging.debug(f"[{self.env.now:.4f}] Node {self.id} started processing {packet}")
        self.env.schedule_event(self.processing_delay_ms, self._finish_processing_packet, "PROCESS_END", packet=packet)

    def _finish_processing_packet(self, packet):
        logging.debug(f"[{self.env.now:.4f}] Node {self.id} finished processing {packet}. Forwarding...")
        self._forward_packet(packet)
        self.is_processing = False
        self._schedule_next_processing()

    # UPDATED: Forwarding logic now uses the routing table
    def _forward_packet(self, packet):
        final_dest_id = packet.destination_id
        
        possible_hops = self.routing_table.get(final_dest_id)
        
        next_hop_id = None
        if not possible_hops:
            # Fallback for directly connected nodes without explicit routes
            if final_dest_id in self.links:
                next_hop_id = final_dest_id
            else:
                logging.error(f"[{self.env.now:.4f}] Node {self.id} has no route to {final_dest_id} for {packet}")
                return
        else:
            # Perform round-robin load balancing
            index = self.route_rr_index[final_dest_id]
            next_hop_id = possible_hops[index]
            # Increment and wrap the index for the next packet to this destination
            self.route_rr_index[final_dest_id] = (index + 1) % len(possible_hops)
        
        if next_hop_id in self.links:
            link = self.links[next_hop_id]
            transmission_delay = link.get_transmission_delay_ms(packet)
            total_delay = transmission_delay + link.propagation_delay_ms
            
            logging.debug(f"[{self.env.now:.4f}] Node {self.id} sending {packet} to next hop {next_hop_id}. TxDelay: {transmission_delay:.4f}, PropDelay: {link.propagation_delay_ms:.4f}")
            self.env.schedule_event(total_delay, link.destination.receive_packet, "RECEIVE", packet=packet)
        else:
            logging.error(f"[{self.env.now:.4f}] Node {self.id} has route to {final_dest_id} via {next_hop_id}, but no such link exists!")


class LegitimateClientNode(Node):
    """
    A simple client that generates legitimate traffic. It now relies on the
    base Node's powerful routing and load-balancing capabilities.
    """
    def __init__(self, env, node_id, server_id, request_interval_ms,
                 request_size_bytes, reply_size_bytes):
        super().__init__(env, node_id)
        self.server_id = server_id
        self.request_interval_ms = request_interval_ms
        self.request_size_bytes = request_size_bytes
        self.reply_size_bytes = reply_size_bytes
        self.pending_requests = {}
    
    def start(self):
        self.env.schedule_event(0.0001, self._send_request, "SEND_REQUEST")

    def _send_request(self):
        """Generates a request and sends it using the base Node's forwarding logic."""
        if self.env.now < self.env.duration_ms:
            packet = Packet(self.id, self.server_id, self.request_size_bytes, 'LEGITIMATE_REQUEST', self.env.now)
            self.pending_requests[packet.id] = self.env.now
            logging.info(f"[{self.env.now:.4f}] Client {self.id} sending new request {packet.id}")
            self.env.metrics.record_legit_packet_sent()
            
            # THE CRITICAL FIX:
            # Call the base class's _forward_packet, which now handles round-robin.
            self._forward_packet(packet)
            
            # Schedule the next request
            self.env.schedule_event(self.request_interval_ms, self._send_request, "SEND_REQUEST")

    def receive_packet(self, packet):
        """Handles incoming reply packets to calculate RTT."""
        if packet.type == 'LEGITIMATE_REPLY':
            if packet.original_request_id in self.pending_requests:
                send_time = self.pending_requests.pop(packet.original_request_id)
                rtt = self.env.now - send_time
                self.env.metrics.record_rtt(rtt)
                self.env.metrics.record_successful_transaction(packet)
                logging.info(f"[{self.env.now:.4f}] Client {self.id} received reply for {packet.original_request_id}. RTT: {rtt:.4f} ms")
            else:
                logging.warning(f"[{self.env.now:.4f}] Client {self.id} received reply for unknown request {packet.original_request_id}")
        else:
            # If it receives something else, let the base class handle it (though it shouldn't happen)
            super().receive_packet(packet)

class ServerNode(Node):
    def __init__(self, env, node_id, processing_delay_ms, queue_max_bytes):
        super().__init__(env, node_id, queue_max_bytes)
        self.server_processing_delay_ms = processing_delay_ms

    def _start_processing_packet(self):
        packet = self.queue.dequeue()
        if not packet:
            self.is_processing = False
            return
        
        self.is_processing = True
        logging.debug(f"[{self.env.now:.4f}] Server {self.id} started processing {packet}")
        
        if packet.type == 'LEGITIMATE_REQUEST':
            self.env.schedule_event(self.server_processing_delay_ms, self._finish_processing_packet, "PROCESS_END", packet=packet)
        else: # Drop attack traffic that reaches the server
            logging.warning(f"[{self.env.now:.4f}] Server {self.id} received and dropped attack packet {packet}.")
            self.env.metrics.record_packet_drop(self.id, packet, "AT_SERVER")
            self.is_processing = False
            self._schedule_next_processing()
            
    def _finish_processing_packet(self, packet):
        # Create and send a reply
        reply_packet = Packet(
            self.id, packet.source_id,
            # This assumes the client passed its reply size expectation. A bit of a cheat.
            # A better model would have this configured on the server.
            # Using the client's config for simplicity.
            self.env.config['legitimate_traffic']['reply_size_bytes'], 
            'LEGITIMATE_REPLY',
            send_timestamp=self.env.now,
            original_request_id=packet.id
        )
        self._forward_packet(reply_packet)
        self.is_processing = False
        self._schedule_next_processing()

class AttackNode(Node):
    def __init__(self, env, node_id, target_id, pps, packet_size, attack_style):
        super().__init__(env, node_id)
        self.target_id = target_id
        self.interval_ms = 1000.0 / pps if pps > 0 else float('inf')
        self.packet_size = packet_size
        self.attack_style = attack_style
    
    def start(self):
        """Schedules the first attack packet event."""
        self.env.schedule_event(0.0001, self._send_attack_packet, "SEND_ATTACK")
    
    def _send_attack_packet(self):
        if self.env.now < self.env.duration_ms:
            packet = Packet(self.id, self.target_id, self.packet_size, self.attack_style, self.env.now)
            logging.debug(f"[{self.env.now:.4f}] Attacker {self.id} sending {packet}")
            self._forward_packet(packet)
            self.env.schedule_event(self.interval_ms, self._send_attack_packet, "SEND_ATTACK")


class FirewallNode(Node):
    def __init__(self, env, node_id, queue_max_bytes, processing_capacity_pps):
        super().__init__(env, node_id, queue_max_bytes)
        self.processing_delay_per_packet_ms = 1000.0 / processing_capacity_pps
        self.bot_detection_accuracy = 1.0 # As per spec
    

    def _start_processing_packet(self):
        packet = self.queue.dequeue()
        if not packet:
            self.is_processing = False
            return
            
        self.is_processing = True
        
        # Use the new, generic packet processing counter
        self.env.metrics.record_packet_processed(self.id)
        
        processing_time = self.processing_delay_per_packet_ms
        is_attack = False

        if packet.type == 'ATTACK_STYLE_1':
            processing_time += 0.01
            is_attack = True
        elif packet.type == 'ATTACK_STYLE_2':
            processing_time += 0.5
            is_attack = True
        
        logging.debug(f"[{self.env.now:.4f}] Firewall {self.id} started processing {packet}, needs {processing_time:.4f} ms")
        
        if is_attack:
            self.env.schedule_event(processing_time, self._drop_attack_packet, "FW_DROP", packet=packet)
        else:
            self.env.schedule_event(processing_time, self._finish_processing_packet, "FW_FORWARD", packet=packet)


    def _drop_attack_packet(self, packet):
        logging.debug(f"[{self.env.now:.4f}] Firewall {self.id} dropped attack packet {packet.id}")
        self.env.metrics.record_packet_drop(self.id, packet, "FIREWALL_MITIGATION")
        self.is_processing = False
        self._schedule_next_processing()


class SwitchNode(Node):
    # UPDATE THE CONSTRUCTOR to accept both custom delays
    def __init__(self, env, node_id, queue_max_bytes, is_scrubber=False, 
                 processing_delay_ms=None, scrubber_processing_delay_ms=None):
        super().__init__(env, node_id, queue_max_bytes)
        
        # Set base processing delay for forwarding legitimate traffic
        if processing_delay_ms is not None:
            self.processing_delay_ms = processing_delay_ms
        
        self.is_scrubber = is_scrubber
        
        # Set the specific delay for scrubbing attack packets
        # Default to 0.005 if not provided, for backward compatibility
        self.scrubber_processing_delay_ms = scrubber_processing_delay_ms if scrubber_processing_delay_ms is not None else 0.005
        
    # The rest of the SwitchNode class is unchanged. The logic inside _start_processing_packet
    # will automatically use these new self.* variables.
    def _start_processing_packet(self):
        packet = self.queue.dequeue()
        if not packet:
            self.is_processing = False
            return

        self.is_processing = True
        self.env.metrics.record_packet_processed(self.id)
        is_attack = packet.type in ['ATTACK_STYLE_1', 'ATTACK_STYLE_2']

        if self.is_scrubber and is_attack:
            processing_time = self.scrubber_processing_delay_ms
            if packet.type == 'ATTACK_STYLE_2':
                # Get the multiplier from the config, defaulting to 1 if not present
                multiplier = self.env.config['attack_traffic'].get('attack_style2_multiplier', 1)
                processing_time *= multiplier
            
            logging.debug(f"[{self.env.now:.4f}] Scrubber {self.id} (fast drop) processing {packet} in {processing_time:.4f} ms")
            self.env.metrics.record_packet_drop(self.id, packet, "SCRUBBER_MITIGATION")
            self.env.schedule_event(processing_time, self._finish_scrubber_drop, "SCRUB_DROP")
        else:
            processing_time = self.processing_delay_ms
            logging.debug(f"[{self.env.now:.4f}] Switch {self.id} forwarding {packet} in {processing_time:.4f} ms")
            self.env.schedule_event(processing_time, self._finish_processing_packet, "SWITCH_FORWARD", packet=packet)
    
    def _finish_scrubber_drop(self):
        self.is_processing = False
        self._schedule_next_processing()

