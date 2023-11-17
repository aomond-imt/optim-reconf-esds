import math
import subprocess, os
import sys
import traceback
from contextlib import redirect_stdout
from multiprocessing import Process, cpu_count, shared_memory
from multiprocessing.pool import Pool

import esds
import numpy as np
import yaml
from icecream import ic

from topologies import clique, chain, ring, star, deploy_tasks_list

env_with_pythonpath = os.environ.copy()
env_with_pythonpath["PYTHONPATH"] = env_with_pythonpath["PYTHONPATH"] + ":" + os.path.dirname(os.path.realpath(__file__))
FREQ_POLLING = 1
LORA_BW = 50_000


tests_topologies = {
    "pull": {
        "solo_on": clique(1, LORA_BW),
        "use_provide": clique(2, LORA_BW),
        "overlaps_sending": clique(3, LORA_BW),
        "actions_overflow": clique(2, LORA_BW),
        "chained_one_provide": chain(3, LORA_BW),
        "chained_three_provides": chain(3, LORA_BW),
        "ring_one_provide": ring(4, LORA_BW),
        "ring_three_aggregators": ring(6, LORA_BW),
        "chained_aggregator_use": chain(5, LORA_BW),
        "concurrent_tasks": clique(4, LORA_BW),
        "deploy_6_star": star(6, LORA_BW)
    },
    "static_pull": {
        "solo_on": clique(1, LORA_BW),
        "standard_comm": clique(2, LORA_BW),
        "overlaps_sending": clique(3, LORA_BW),
        "actions_overflow": clique(2, LORA_BW),
        "chained_one_provide": chain(3, LORA_BW),
        "chained_three_provides": chain(3, LORA_BW),
    },
    "push": {
        "unfinished_reconf": clique(1, LORA_BW),
        "use_provide": clique(2, LORA_BW),
        "concurrent_provide_msgs": clique(4, LORA_BW),
    }
}


def compute_neighborhood(topology):
    node_neighbors = []
    for node_id, other_nodes in enumerate(topology):
        neighbors = []
        for other_node_id in range(len(other_nodes)):
            if node_id != other_node_id:
                if topology[node_id][other_node_id] > 0:
                    neighbors.append(other_node_id)
        node_neighbors.append(neighbors)

    return node_neighbors


def run_simulation(test_name, tasks_list, type_comms):
    B, L = tests_topologies[type_comms][test_name]
    s = esds.Simulator({"eth0": {"bandwidth": B, "latency": L, "is_wired": False}})
    node_neighbors = compute_neighborhood(B)
    nodes_count = len(tasks_list)
    arguments = {
        "stress_conso": 1.358,
        "idle_conso": 1.339,
        "comms_conso": 0.16,
        "bandwidth": 6250,
        "results_dir": f"/tmp/{test_name}",
        "nodes_count": nodes_count,
        "uptimes_schedule_name": f"tests/{type_comms}/{test_name}.json",
        "tasks_list": tasks_list,
        "neighbor_nodes": node_neighbors,
        "s": shared_memory.SharedMemory(f"shm_cps_{test_name}", create=True, size=nodes_count)
    }
    sys.path.append("..")
    for node_num in range(nodes_count):
        s.create_node(f"on_{type_comms}", interfaces=["eth0"], args=arguments)

    s.run(interferences=False)
    arguments["s"].close()
    arguments["s"].unlink()


def verify_results(expected_result, test_name):
    errors = []
    # Check result for each node
    for node_num, expected_node_results in expected_result.items():
        # Load node results
        with open(f"/tmp/{test_name}/{node_num}.yaml") as f:
            result = yaml.safe_load(f)

        # Check exact results
        # for key in ["finished_reconf", "tot_aggregated_send", "tot_reconf_duration"]:
        for key in ["finished_reconf", "tot_reconf_duration"]:
            if round(result[key], 2) != round(expected_node_results[key], 2):
                errors.append(f"Error {key} node {node_num}: expected {expected_node_results[key]} got {result[key]}")

        # Results with approximation tolerance
        # for key in ["global_termination_time", "tot_uptimes_duration", "tot_msg_sent"]:
        for key in ["global_termination_time", "local_termination_time", "tot_uptimes_duration"]:
            delta = abs(result[key] - expected_node_results[key])
            if delta > FREQ_POLLING * 5:
                errors.append(f"Error {key} node {node_num}: expected a delta of minus or equal {FREQ_POLLING * 5}, got {delta} (expected {expected_node_results[key]} got {result[key]}")

    return errors


def run_test(test_name, type_comms):
    with open(f"tests/{type_comms}/{test_name}.yaml") as f:
        test_args = yaml.safe_load(f)

    expected_result = test_args["expected_result"]
    if "deploy" in test_name:
        _, nodes_count, _ = test_name.split("_")
        tasks_list = deploy_tasks_list(int(nodes_count) - 1)
    else:
        tasks_list = test_args["tasks_list"]

    # Launch and log experiment
    os.makedirs(f"/tmp/{test_name}", exist_ok=True)
    with open(f"/tmp/{test_name}/debug.txt", "w") as f:
        with redirect_stdout(f):
            run_simulation(test_name, tasks_list, type_comms)

    errors = verify_results(expected_result, test_name)
    if len(errors) == 0:
        print(f"{test_name}: ok")
    else:
        print(f"{test_name}: errors: \n" + "\n".join(errors))


def main():
    type_comms = "pull"
    all_p = []
    for test_name in tests_topologies[type_comms].keys():
        p = Process(target=run_test, args=(test_name,type_comms))
        p.start()
        all_p.append(p)

    for k in all_p:
        k.join()
    # nb_cores = math.ceil(cpu_count() * 0.5)
    # pool = Pool(nb_cores)
    # for test_name in tests_topologies[type_comms].keys():
    #     exec_esds = pool.apply_async(
    #         run_test,
    #         args=(test_name,type_comms)
    #     )
    #     all_p.append(exec_esds)
    #
    # for running_exec in all_p:
    #     try:
    #         running_exec.get()
    #     except subprocess.CalledProcessError as err:
    #         print("failed :(")
    #         print("------------- Test has a non-zero exit code -------------")
    #         print(err.output, end="")
    #     except Exception as err:
    #         print("failed :(")
    #         traceback.print_exc()


if __name__ == "__main__":
    main()
