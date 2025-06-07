# --- COPY AND PASTE THIS ENTIRE METHOD INTO FirewallNode in components.py ---

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