import subprocess, os
import sys
from contextlib import redirect_stdout
from multiprocessing import Process

import esds
import numpy as np
import yaml

env_with_pythonpath = os.environ.copy()
env_with_pythonpath["PYTHONPATH"] = env_with_pythonpath["PYTHONPATH"] + ":" + os.path.dirname(os.path.realpath(__file__))
FREQ_POLLING = 1


def clique(nodes_count):
    B = np.full((nodes_count, nodes_count), 50000)
    L = np.full((nodes_count, nodes_count), 0)
    return B, L


def chain(nodes_count):
    bw = 50_000
    B = np.array([
        [bw, bw, 0],
        [bw, bw, bw],
        [0, bw, bw],
    ])
    L = np.full((3, 3), 0)
    return B, L


topologies = {
    "solo_on": clique(1),
    "standard_comm": clique(2),
    "overlaps_sending": clique(3),
    "actions_overflow": clique(2),
    "chained_one_provide": chain(3),
    "chained_three_provides": chain(3),
}


def run_simulation(test_name, tasks_list):
    #B = np.array([[bwdth, bwdth, 0, 0, bwdth], [bwdth, bwdth, bwdth, 0, 0], [0, bwdth, bwdth, bwdth, 0], [0, 0, bwdth, bwdth, bwdth], [bwdth, 0, 0, bwdth, bwdth]])

    B, L = topologies[test_name]
    s = esds.Simulator({"eth0": {"bandwidth": B, "latency": L, "is_wired": False}})
    nodes_count = len(tasks_list.keys())
    arguments = {
        "stress_conso": 1.358,
        "idle_conso": 1.339,
        "comms_conso": 0.16,
        "bandwidth": 6250,
        "results_dir": f"/tmp/{test_name}",
        "nodes_count": nodes_count,
        "uptimes_schedule_name": f"tests/{test_name}.json",
        "tasks_list": tasks_list
    }
    sys.path.append("..")
    for node_num in range(nodes_count):
        s.create_node("on_coordination_logic", interfaces=["eth0"], args=arguments)

    s.run(interferences=False)


def run_test(test_name):
    with open(f"tests/{test_name}.yaml") as f:
        test_args = yaml.safe_load(f)

    tasks_list, expected_result = test_args["tasks_list"], test_args["expected_result"]

    # Launch and log experiment
    os.makedirs(f"/tmp/{test_name}", exist_ok=True)
    with open(f"/tmp/{test_name}/debug.txt", "w") as f:
        with redirect_stdout(f):
            run_simulation(test_name, tasks_list)
        # out = subprocess.run(["esds", "run", f"{current_test_dir}/plateform.yaml"], stdout=f, encoding="utf-8", env=env_with_pythonpath)

    errors = verify_results(expected_result, test_name)
    if len(errors) == 0:
        print(f"{test_name}: ok")
    else:
        print(f"{test_name}: errors: \n" + "\n".join(errors))


def main():
    # for test in ['chained_one_provide', 'solo_on', 'overlaps_sending', 'actions_overflow', 'chained_three_provides', 'standard_comm']:
    all_p = []
    for test_name in topologies.keys():
        p = Process(target=run_test, args=(test_name,))
        p.start()
        all_p.append(p)

    for k in all_p:
        k.join()


def verify_results(expected_result, test_name):
    errors = []
    # Check result for each node
    for node_num, expected_node_results in expected_result.items():
        # Load node results
        with open(f"/tmp/{test_name}/{node_num}.yaml") as f:
            result = yaml.safe_load(f)

        # Check exact results
        for key in ["finished_reconf", "tot_aggregated_send", "tot_reconf_duration"]:
            if round(result[key], 2) != round(expected_node_results[key], 2):
                errors.append(f"Error {key} node {node_num}: expected {expected_node_results[key]} got {result[key]}")

        # Results with approximation tolerance
        for key in ["time", "tot_uptimes_duration", "tot_msg_sent"]:
            delta = abs(result[key] - expected_node_results[key])
            if delta > FREQ_POLLING * 2:
                errors.append(f"Error {key} node {node_num}: expected a delta of minus or equal {FREQ_POLLING * 2}, got {delta} (expected {expected_node_results[key]} got {result[key]}")

    return errors


if __name__ == "__main__":
    main()
