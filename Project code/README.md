# DDoS Mitigation Strategy Simulator

This project implements a discrete-event network simulation in Python to compare the performance of centralized versus distributed DDoS mitigation strategies.

## Project Structure

- `main.py`: The main entry point for the simulation.
- `simulation.py`: Contains the core simulation engine and topology builder.
- `components.py`: Defines the network components (Nodes, Packets, Links, etc.).
- `metrics.py`: Handles the collection and reporting of simulation metrics.
- `config.yaml`: The configuration file where all simulation scenarios and their parameters are defined.
- `results.csv`: The output file containing the metrics from each simulation run.
- `requirements.txt`: Python package dependencies.

## How to Run

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Scenarios:**
    Open `config.yaml` to view, modify, or add new simulation runs. The file is pre-configured with several scenarios as required by the project prompt.

3.  **Run the Simulation:**
    ```bash
    python main.py
    ```

4.  **Check the Results:**
    Once the simulation is complete, a file named `results.csv` will be generated in the same directory. This file contains a detailed breakdown of the performance metrics for each configured run.

## Interpreting the Output

The `results.csv` file contains a row for each simulation run defined in `config.yaml`. The columns include:

-   Run parameters (scenario type, attack style, etc.).
-   Key performance indicators like Goodput (Mbps), Average/Median/P95 RTT (ms), and Successful Transaction Count.
-   Operational metrics like packet drop counts and average/max queue lengths at the server, firewall, and scrubbers.

This data can be used to analyze how different mitigation strategies perform under various attack types and intensities.