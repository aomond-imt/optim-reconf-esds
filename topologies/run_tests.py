import subprocess, os

import yaml

env_with_pythonpath = os.environ.copy()
env_with_pythonpath["PYTHONPATH"] = env_with_pythonpath["PYTHONPATH"] + ":" + os.path.dirname(os.path.realpath(__file__))
FREQ_POLLING = 1


for test_dir in os.listdir("tests"):
    print(test_dir)
    current_test_dir = f"tests/{test_dir}"

    # Launch and log experiment
    os.makedirs(f"/tmp/{current_test_dir}", exist_ok=True)
    with open(f"/tmp/{current_test_dir}/debug.txt", "w") as f:
        out = subprocess.run(["esds", "run", f"{current_test_dir}/plateform.yaml"], stdout=f, encoding="utf-8", env=env_with_pythonpath)

    # Load experiment expected metric results
    with open(f"{current_test_dir}/expected_result.yaml") as f:
        expected_result = yaml.safe_load(f)

    # Check result for each node
    for node_num, expected_node_results in expected_result.items():
        # Load node results
        with open(f"/tmp/{current_test_dir}/uptime_schedules.json/{node_num}.yaml") as f:
            result = yaml.safe_load(f)

        # Check exact results
        print(f"Assertions node {node_num}")
        p = True
        for key in ["finished_reconf", "tot_aggregated_send", "tot_reconf_duration"]:
            if round(result[key], 2) != round(expected_node_results[key], 2):
                print(f"Error {key}: expected {expected_node_results[key]} got {result[key]}")
                p = False

        # Results with approximation tolerance
        for key in ["time", "tot_uptimes_duration", "tot_msg_sent"]:
            delta = abs(result[key] - expected_node_results[key])
            if delta > FREQ_POLLING * 2:
                print(f"Error {key}: expected a delta of minus or equal {FREQ_POLLING*2}, got {delta} (expected {expected_node_results[key]} got {result[key]}")
                p = False

        if p:
            print("Passed")

