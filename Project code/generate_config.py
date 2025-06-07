import yaml
import numpy as np

# --- Simulation Parameters to Sweep ---
ATTACK_PPS_LEVELS = [5000, 15000, 30000]
FIREWALL_CAPACITY_LEVELS = [8000, 20000, 40000]
MULTIPLIER_LEVELS = np.arange(10, 151, 10) # 10, 20, 30, ... 150

# --- Base Template for a single run ---
# Using f-strings to easily insert values
RUN_TEMPLATE = """
  - run_id: "{run_id}"
    duration_seconds: 10
    scenario_type: "Distributed"
    legitimate_traffic: {{request_interval_ms: 200, request_size_bytes: 1024, reply_size_bytes: 4096, server_processing_delay_ms: 10}}
    attack_traffic:
      present: True
      style: "ATTACK_STYLE_2"
      num_total_attackers: 30
      attack_packet_size_bytes: 1024
      total_attack_pps: {attack_pps}
      attack_style2_multiplier: {multiplier}
    network_links: {{default_bandwidth_bps: 100_000_000, default_propagation_delay_ms: 0.01}}
    firewall_centralized:
      queue_max_bytes: 10_000_000
      interface_speed_bps: 100_000_000
      processing_capacity_pps: {firewall_pps}
    server_config: {{queue_max_bytes: 5_000_000, link_to_switch_bw_bps: 100_000_000}}
    distributed_mitigation:
      scrubber1_id: "{scrubber1_id}"
      scrubber2_id: "{scrubber2_id}"
      scrubber_configs:
        SW1: {{type: "WidePipe", bandwidth_bps: 100_000_000, queue_max_bytes: 1_000_000, processing_delay_ms: 0.001, scrubber_processing_delay_ms: 0.05}}
        SW2: {{type: "WidePipe", bandwidth_bps: 100_000_000, queue_max_bytes: 1_000_000, processing_delay_ms: 0.001, scrubber_processing_delay_ms: 0.05}}
        SW3: {{type: "GoodQueue", bandwidth_bps: 10_000_000, queue_max_bytes: 20_000_000, processing_delay_ms: 0.0002, scrubber_processing_delay_ms: 0.001}}
        SW4: {{type: "GoodQueue", bandwidth_bps: 10_000_000, queue_max_bytes: 20_000_000, processing_delay_ms: 0.0002, scrubber_processing_delay_ms: 0.001}}
"""

def generate_config():
    """Generates a massive YAML configuration file for the simulation."""
    all_runs = []
    
    # --- Main loop to generate the 810 core runs ---
    for pps in ATTACK_PPS_LEVELS:
        for fw_pps in FIREWALL_CAPACITY_LEVELS:
            for mult in MULTIPLIER_LEVELS:
                # 1. Generate the "Adequate" scenario (GoodQueue scrubbers)
                run_id_adequate = f"Dist-GoodQ_pps-{pps}_fw-{fw_pps}_mult-{mult}"
                run_yaml_adequate = RUN_TEMPLATE.format(
                    run_id=run_id_adequate,
                    attack_pps=pps,
                    firewall_pps=fw_pps,
                    multiplier=mult,
                    scrubber1_id="SW3",
                    scrubber2_id="SW4"
                )
                all_runs.append(yaml.safe_load(run_yaml_adequate)[0])

                # 2. Generate the "Inadequate" scenario (WidePipe scrubbers)
                run_id_inadequate = f"Dist-WideP_pps-{pps}_fw-{fw_pps}_mult-{mult}"
                run_yaml_inadequate = RUN_TEMPLATE.format(
                    run_id=run_id_inadequate,
                    attack_pps=pps,
                    firewall_pps=fw_pps,
                    multiplier=mult,
                    scrubber1_id="SW1",
                    scrubber2_id="SW2"
                )
                all_runs.append(yaml.safe_load(run_yaml_inadequate)[0])
                
    # --- Add a few Centralized baselines for comparison ---
    # (You can add more of these if needed)
    for pps in ATTACK_PPS_LEVELS:
         for fw_pps in FIREWALL_CAPACITY_LEVELS:
            run_id = f"Centralized_pps-{pps}_fw-{fw_pps}"
            centralized_run = f"""
  - run_id: "{run_id}"
    duration_seconds: 10
    scenario_type: "Centralized"
    legitimate_traffic: {{request_interval_ms: 200, request_size_bytes: 1024, reply_size_bytes: 4096, server_processing_delay_ms: 10}}
    attack_traffic: {{present: True, style: "ATTACK_STYLE_2", num_total_attackers: 30, attack_packet_size_bytes: 1024, total_attack_pps: {pps}}}
    network_links: {{default_bandwidth_bps: 100_000_000, default_propagation_delay_ms: 0.01}}
    firewall_centralized: {{queue_max_bytes: 10_000_000, interface_speed_bps: 100_000_000, processing_capacity_pps: {fw_pps}}}
    server_config: {{queue_max_bytes: 5_000_000, link_to_switch_bw_bps: 100_000_000}}
"""
            all_runs.append(yaml.safe_load(centralized_run)[0])


    final_config = {'simulation_runs': all_runs}
    
    with open('config_generated.yaml', 'w') as f:
        yaml.dump(final_config, f, sort_keys=False, width=120)
        
    print(f"Successfully generated config_generated.yaml with {len(all_runs)} runs.")

if __name__ == "__main__":
    generate_config()