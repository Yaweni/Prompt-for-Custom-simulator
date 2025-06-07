# DDoS Mitigation Strategy Simulation Project

## Project Goal
Develop a discrete-event network simulation in Python to compare the performance (primarily legitimate traffic throughput/goodput and RTT) of centralized vs. distributed DDoS mitigation strategies under various attack scenarios.

## Core Requirements
1.  **Discrete-Event Simulation Engine:**
    *   Manage simulation time.
    *   Handle events in a priority queue (e.g., packet arrival, processing start/end, transmission start/end).
2.  **Network Components (as Python classes):**
    *   `Packet`: Attributes for `id`, `source_id`, `destination_id`, `size_bytes`, `type` ('LEGITIMATE_REQUEST', 'LEGITIMATE_REPLY', 'ATTACK_STYLE_1', 'ATTACK_STYLE_2'), `send_timestamp`, `processing_difficulty_factor` (derived from type).
    *   `Node`: Base class for all network devices.
        *   `Queue`: FIFO queue for incoming packets. Attribute: `max_size_bytes`. Methods: `enqueue`, `dequeue`, `is_full`, `current_size_bytes`.
        *   `processing_delay_ms`: Base processing delay.
    *   `ServerNode(Node)`: Represents the victim server.
        *   `server_processing_delay_ms`: Fixed delay to process a legitimate request before sending a reply.
    *   `LegitimateClientNode(Node)`: Generates legitimate traffic.
    *   `AttackNode(Node)`: Generates attack traffic.
    *   `FirewallNode(Node)`: Centralized mitigation point.
        *   `processing_capacity_pps` (Packets Per Second it can process).
        *   `connection_to_server_link_bandwidth_bps`
        *   `bot_detection_accuracy = 1.0` (100% accurate).
        *   `process_packet(packet)`:
            *   If `packet.type` is 'ATTACK_STYLE_1': Incurs `0.01 ms` specific processing delay. Then drops.
            *   If `packet.type` is 'ATTACK_STYLE_2': Incurs `0.5 ms` specific processing delay. Then drops.
            *   If legitimate, forwards after base processing delay.
    *   `SwitchNode(Node)`: Represents network switches. For scrubbers, they will have specific behaviors.
        *   `is_scrubber`: Boolean.
        *   `scrubber_processing_delay_ms = 0.005 ms` (if `is_scrubber`).
        *   If `is_scrubber`, its primary action is to receive and drop attack packets with this minimal delay.
    *   `Link`: Connects nodes. Attributes: `bandwidth_bps`, `propagation_delay_ms` (can be minimal/zero for simplicity within a datacenter/POP, or a small fixed value).
3.  **Traffic Generation:**
    *   **Legitimate Traffic:**
        *   `LegitimateClientNode` continuously sends 'LEGITIMATE_REQUEST' packets (configurable `size_s1`) to the `ServerNode` at a configurable `legit_request_interval_ms`.
        *   `ServerNode` responds with 'LEGITIMATE_REPLY' packets (configurable `size_s2`) after `server_processing_delay_ms`.
    *   **Attack Traffic:**
        *   Configurable `num_total_attackers`.
        *   Configurable `total_attack_pps` (aggregate packets per second from all attackers). Each attacker sends `total_attack_pps / num_total_attackers` PPS.
        *   Attackers generate packets of `ATTACK_STYLE_1` or `ATTACK_STYLE_2` (configurable per simulation run). Packet size for attack traffic should also be configurable.
4.  **Network Topologies & Scenarios:**

    *   **Scenario 1: No Mitigation (Baseline)**
        *   Topology: `LegitimateClientNode` -> `Switch` -> `ServerNode`.
        *   `AttackNode(s)` -> `Switch` -> `ServerNode`. (All traffic converges on the switch leading to the server).
        *   The `Switch` here is a simple pass-through with its own queue and link capacities.
        *   Focus: Measure RTT and goodput degradation due to attack traffic overwhelming server/link resources.

    *   **Scenario 2: Centralized Mitigation**
        *   Topology:
            *   `LegitimateClientNode` -> `FirewallNode` -> `ServerNode`.
            *   `AttackNode(s)` (all of them) -> `FirewallNode`.
        *   Fixed Network Link Attributes (Bandwidth, Propagation Delay - provide specific values).
        *   Fixed Firewall Capacity: `firewall_queue_max_bytes`, `firewall_interface_speed_bps` (for links connecting to it), `firewall_processing_capacity_pps`.
        *   Firewall identifies and drops bot traffic per its processing rules.
        *   Focus: Measure RTT, goodput, firewall queue length, firewall drop rates.

    *   **Scenario 3: Distributed Mitigation**
        *   Topology:
            *   `LegitimateClientNode` -> `FirewallNode` -> `Switch5` -> `ServerNode`.
            *   `FirewallNode` is connected to `Switch1`, `Switch2`, `Switch3`, `Switch4`.
            *   `Switch1`, `Switch2`, `Switch3`, `Switch4` all connect to `Switch5`.
            *   `Switch5` connects to `ServerNode`.
            *   **Scrubber Configuration (Fixed per experiment run, defined in YAML):**
                *   Two of the four switches (`Switch1`-`Switch4`) will be designated as active scrubbers.
                *   The other two will act as normal transit switches (or can be omitted from paths if not used as scrubbers in a specific run).
                *   `Switch5` is never a scrubber.
            *   **Bot Connectivity for Distributed Scenario:**
                *   Assume `num_total_attackers` is divisible by 3.
                *   `1/3` of `AttackNode(s)` connect directly to `ScrubberSwitchA` (one of the chosen scrubbers).
                *   `1/3` of `AttackNode(s)` connect directly to `ScrubberSwitchB` (the other chosen scrubber).
                *   `1/3` of `AttackNode(s)` connect directly to `FirewallNode`.
                *   *(The "direct connection" can be modeled as these attacker nodes having their first hop be the designated scrubber/firewall. The intermediate conceptual switch allowing this has infinite capacity/zero delay for simplicity).*
            *   **Firewall Offloading Logic (Simplified by direct bot connection):**
                *   The firewall handles the 1/3 of attack traffic sent directly to it.
                *   The scrubbers handle the 2/3 of attack traffic sent directly to them.
            *   **Switch Characteristics (Fixed):**
                *   `Switch1` (Wide Pipe Scrubber Candidate): High `bandwidth_bps`, Small `queue_max_bytes`.
                *   `Switch2` (Wide Pipe Scrubber Candidate): High `bandwidth_bps`, Small `queue_max_bytes`.
                *   `Switch3` (Good Queue Scrubber Candidate): Small `bandwidth_bps`, Large `queue_max_bytes`.
                *   `Switch4` (Good Queue Scrubber Candidate): Small `bandwidth_bps`, Large `queue_max_bytes`.
                *   *(Provide specific values for "High/Small" bandwidth and "Large/Small" queue).*
            *   **Experiments:**
                1.  Volumetric Attack (`ATTACK_STYLE_1`) vs. "Adequate" Distributed Setup (Firewall + `Switch1` & `Switch2` as scrubbers).
                2.  Volumetric Attack (`ATTACK_STYLE_1`) vs. "Inadequate" Distributed Setup (Firewall + `Switch3` & `Switch4` as scrubbers).
                3.  High Processing Attack (`ATTACK_STYLE_2`) vs. "Adequate" Distributed Setup (Firewall + `Switch3` & `Switch4` as scrubbers – assuming their larger queues help absorb bursts even if the attack isn't volumetric, or that "good queue" also implies better ability to handle packets needing more state/time before the simple drop). *Re-evaluate if this "good queue" logic for `ATTACK_STYLE_2` makes sense for simple drop scrubbers, or if the benefit is mainly for the firewall itself.* The primary benefit of scrubbers here is offloading *any* identified attack traffic.
                4.  High Processing Attack (`ATTACK_STYLE_2`) vs. "Inadequate" Distributed Setup (Firewall + `Switch1` & `Switch2` as scrubbers).
        *   Focus: Measure RTT, goodput, load and drops at firewall and active scrubbers.

5.  **Metrics Collection & Output:**
    *   **Goodput:** Total bytes of *successfully received 'LEGITIMATE_REPLY' packets by `LegitimateClientNode`* / simulation duration.
    *   **RTT:** Round Trip Time for each legitimate request-reply pair. Calculate average, median, 95th percentile RTT.
    *   **Successful Transactions:** Count of legitimate requests that received a reply.
    *   Queue lengths (average, max) at Firewall, Server, and active Scrubber nodes.
    *   Packet drop counts (total, by type if possible) at Firewall, Server, and active Scrubber nodes.
    *   Output all simulation run parameters and collected metrics to a CSV file. Each row represents one simulation run.
    *   **CSV Columns (example, refine as needed):**
        `Run_ID, Timestamp_Start, Scenario_Type (NoMitigation/Centralized/Distributed), Attack_Style (None/Style1/Style2), Total_Attack_PPS, Num_Total_Attackers, Legit_Request_Interval_ms, Server_Processing_Delay_ms, Centralized_Firewall_Queue_Bytes, Centralized_Firewall_Processing_PPS, Distributed_Scrubber1_Type (None/WidePipe/GoodQueue), Distributed_Scrubber1_Bandwidth_bps, Distributed_Scrubber1_Queue_Bytes, Distributed_Scrubber2_Type (None/WidePipe/GoodQueue), Distributed_Scrubber2_Bandwidth_bps, Distributed_Scrubber2_Queue_Bytes, Legitimate_Packets_Sent, Legitimate_Packets_Received_By_Client, Successful_Transactions_Count, Avg_RTT_ms, Median_RTT_ms, P95_RTT_ms, Goodput_Mbps, Firewall_Total_Packets_Processed, Firewall_Attack_Packets_Dropped, Firewall_Avg_Queue_Length_Packets, Firewall_Max_Queue_Length_Packets, Scrubber1_Attack_Packets_Dropped (if applicable), Scrubber1_Avg_Queue_Length_Packets, Scrubber1_Max_Queue_Length_Packets, Scrubber2_Attack_Packets_Dropped (if applicable), Scrubber2_Avg_Queue_Length_Packets, Scrubber2_Max_Queue_Length_Packets, Server_Packets_Dropped_Queue_Overflow`

6.  **Configuration:**
    *   Use a YAML file to define simulation parameters for each run or batch of runs.
    *   Provide a template YAML file.

## Implementation Details & Considerations:
*   Use standard Python libraries (e.g., `heapq` for priority queue, `collections.deque` for node queues).
*   Structure code into logical modules (e.g., `components.py`, `simulation.py`, `traffic_gen.py`, `metrics.py`).
*   Ensure the simulation is deterministic for given parameters (use a fixed random seed if any randomness is introduced, though for now, traffic generation can be deterministic).
*   Logging: Implement logging (Python's `logging` module) for different verbosity levels (DEBUG, INFO, WARNING) to help trace simulation events.
*   Error Handling: Basic error handling for invalid configurations.

## YAML Configuration File Template (`config_template.yaml`):

```yaml
simulation_runs:
  - run_id: "centralized_style1_low_intensity"
    duration_seconds: 60
    scenario_type: "Centralized" # Centralized, Distributed, NoMitigation
    
    legitimate_traffic:
      request_interval_ms: 100 # Time between start of new requests
      request_size_bytes: 1024
      reply_size_bytes: 4096
      server_processing_delay_ms: 5

    attack_traffic:
      present: True
      style: "ATTACK_STYLE_1" # None, ATTACK_STYLE_1, ATTACK_STYLE_2
      num_total_attackers: 10
      total_attack_pps: 1000 # Aggregate PPS from all attackers
      attack_packet_size_bytes: 512

    network_links: # Define parameters for all links if they vary, or use global defaults
      default_bandwidth_bps: 1_000_000_000 # 1 Gbps
      default_propagation_delay_ms: 0.1 # Minimal delay

    firewall_centralized: # Used in Centralized and Distributed scenarios
      queue_max_bytes: 1_000_000 # 1 MB
      interface_speed_bps: 1_000_000_000 # 1 Gbps (link speed to/from firewall)
      processing_capacity_pps: 50000 # Max packets firewall can process

    # --- Distributed Scenario Specific ---
    distributed_mitigation: # Only fill if scenario_type is "Distributed"
      # Bots are split 1/3 to Firewall, 1/3 to Scrubber1, 1/3 to Scrubber2
      scrubber1_type: "WidePipe" # WidePipe, GoodQueue, None
      scrubber2_type: "WidePipe" # WidePipe, GoodQueue, None
      
      # Define characteristics for each potential scrubber type
      # These are fixed definitions for the switch types
      scrubber_configs:
        WidePipe:
          bandwidth_bps: 2_000_000_000 # 2 Gbps
          queue_max_bytes: 100_000    # 100 KB (small queue)
          # is_scrubber: True, scrubber_processing_delay_ms: 0.005 ms (implicit)
        GoodQueue:
          bandwidth_bps: 500_000_000 # 0.5 Gbps (small pipe)
          queue_max_bytes: 2_000_000   # 2 MB (good queue)
          # is_scrubber: True, scrubber_processing_delay_ms: 0.005 ms (implicit)
    
    # --- No Mitigation Scenario Specific ---
    # (If scenario_type is NoMitigation, firewall and distributed sections are ignored)
    # Define capacities for the single switch and server links if different from default

  # --- Add more runs below ---
  # - run_id: "distributed_style1_high_intensity_good_scrubbers"
  #   ...