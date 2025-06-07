import yaml
import csv
import logging
import time
from simulation import Simulation

def setup_logging(enable=False): # Add a parameter to easily switch it on/off
    """Configures or disables logging for the simulation."""
    if enable:
        # To re-enable for debugging, set enable=True
        logging.basicConfig(level=logging.DEBUG, 
                            format='%(message)s')
        print("Logging is ENABLED (DEBUG level).")
    else:
        # This will suppress all messages, even CRITICAL ones.
        # It's the fastest option.
        logging.disable(logging.CRITICAL) 

def main():
    setup_logging(enable=False)  # Disable logging by default
    
    config_file = 'config_generated_style1.yaml'
    
    print(f"Loading massive configuration from: {config_file}")
    with open(config_file, 'r') as f:
        config_data = yaml.safe_load(f)

    all_results = []
    start_time = time.time()

    for i, run_config in enumerate(config_data['simulation_runs']):
        print(f"\n[{i+1}/{len(config_data['simulation_runs'])}] Running simulation: {run_config['run_id']}...")
        sim = Simulation(run_config)
        results = sim.run()
        all_results.append(results)
        print(f"Finished. Goodput: {results['Goodput_Mbps']} Mbps, Avg RTT: {results['Avg_RTT_ms']} ms")

    end_time = time.time()
    print(f"\nAll simulations completed in {end_time - start_time:.2f} seconds.")

    if not all_results:
        print("No results to write.")
        return

    # Write results to CSV
    output_file = 'results_style_1.csv'
    fieldnames = all_results[0].keys()
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()