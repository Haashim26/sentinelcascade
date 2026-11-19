PART C: Experiment analysis (owner: Irfan Ahmed)

`analyze.py` compares the staged engine with the baseline using the engine's events and the simulator's `scenarios.csv`.

    pip install pandas matplotlib requests
    python analyze.py --scenarios scenarios.csv --events events.csv
    python analyze.py --scenarios scenarios.csv --events-url https://<engine>.onrender.com/events?limit=5000

Outputs `results.csv`, `per_scenario.csv`, `false_alarms.png`, `time_to_alert.png`.
This folder holds a sample run on 40 simulated scenarios (seed 7).
