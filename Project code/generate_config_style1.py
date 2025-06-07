import yaml
import numpy as np

# --- Simulation Parameters to Sweep for Volumetric Attacks ---
# These PPS levels are chosen to stress the BANDWIDTH of the scrubbers.
# The 'GoodQueue' scrubber has a 10 Mbps link in the template.
# 512 bytes/packet * 8 bits/byte = 4096 bits/packet.
# 10,000,000 bps / 4096 bits/packet = ~2441 pps saturation point per scrubber.
# Total attack PPS is split 3 ways, so saturation starts around 3 * 2441 = ~7300 pps.
ATTACK_PPS_LEVELS = [ 60000,180000,250000,350000] 
FIREWALL_CAPACITY_LEVELS = [8000, 12000] # Less critical here, but good to vary.

# --- Base Template for a STYLE 1 run ---
# Note: attack_style2_multiplier is not present here.
RUN_TEMPLATE = """
  - run_id: "{run_id}"
    duration_seconds: 10
    scenario_type: "Distributed"
    legitimate_traffic: {{request_interval_ms: 50, request_size_bytes: 1024, reply_size_bytes: 4096, server_processing_delay_ms: 10}}
    attack_traffic:
      present: True
      style: "ATTACK_STYLE_1"
      num_total_attackers: 30
      attack_packet_size_bytes: 512
      total_attack_pps: {attack_pps}
    network_links: {{default_bandwidth_bps: 100_000_000, default_propagation_delay_ms: 0.01}}
    firewall_centralized:
      queue_max_bytes: 10_000_000
      interface_speed_bps: 100_000_00
      processing_capacity_pps: {firewall_pps}
    server_config: {{queue_max_bytes: 5_000_000, link_to_switch_bw_bps: 100_000_000}}
    distributed_mitigation:
      scrubber1_id: "{scrubber1_id}"
      scrubber2_id: "{scrubber2_id}"
      scrubber_configs:
        SW1: {{type: "WidePipe", bandwidth_bps: 100_000_00, queue_max_bytes: 1_000_000, processing_delay_ms: 0.0002, scrubber_processing_delay_ms: 0.001}}
        SW2: {{type: "WidePipe", bandwidth_bps: 100_000_00, queue_max_bytes: 1_000_000, processing_delay_ms: 0.0002, scrubber_processing_delay_ms: 0.001}}
        SW3: {{type: "GoodQueue", bandwidth_bps: 10_000_00, queue_max_bytes: 10_000_000, processing_delay_ms: 0.0002, scrubber_processing_delay_ms: 0.001}}
        SW4: {{type: "GoodQueue", bandwidth_bps: 10_000_00, queue_max_bytes: 10_000_000, processing_delay_ms: 0.0002, scrubber_processing_delay_ms: 0.001}}
"""

def generate_config():
    """Generates a massive YAML configuration file for STYLE 1 simulations."""
    all_runs = []
    
    for pps in ATTACK_PPS_LEVELS:
        for fw_pps in FIREWALL_CAPACITY_LEVELS:
            # 1. Generate the "Adequate" scenario (WidePipe scrubbers for volumetric)
            run_id_adequate = f"Style1-WideP_pps-{pps}_fw-{fw_pps}"
            run_yaml_adequate = RUN_TEMPLATE.format(
                run_id=run_id_adequate,
                attack_pps=pps,
                firewall_pps=fw_pps,
                scrubber1_id="SW1",
                scrubber2_id="SW2"
            )
            all_runs.append(yaml.safe_load(run_yaml_adequate)[0])

            # 2. Generate the "Inadequate" scenario (GoodQueue scrubbers for volumetric)
            run_id_inadequate = f"Style1-GoodQ_pps-{pps}_fw-{fw_pps}"
            run_yaml_inadequate = RUN_TEMPLATE.format(
                run_id=run_id_inadequate,
                attack_pps=pps,
                firewall_pps=fw_pps,
                scrubber1_id="SW3",
                scrubber2_id="SW4"
            )
            all_runs.append(yaml.safe_load(run_yaml_inadequate)[0])

    final_config = {'simulation_runs': all_runs}
    
    with open('config_generated_style1.yaml', 'w') as f:
        yaml.dump(final_config, f, sort_keys=False, width=120)
        
    print(f"Successfully generated config_generated_style1.yaml with {len(all_runs)} runs.")

if __name__ == "__main__":
    generate_config()