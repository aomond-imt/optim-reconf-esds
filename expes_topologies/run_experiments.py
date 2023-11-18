import math
import os
import sys
import traceback
from contextlib import redirect_stdout
from multiprocessing import cpu_count, shared_memory
from multiprocessing.pool import Pool
import time
from os.path import exists

import esds
import yaml
from execo_engine import ParamSweeper, sweep
from icecream import ic

import shared_methods
from topologies import clique, chain, ring, star, deploy_tasks_list

network_topologies = {
    "clique": clique,
    "chain": chain,
    "ring": ring,
    "star": star
}

coord_name_tasks_lists = {
    "deploy": deploy_tasks_list
}


def run_simulation(parameters, test_expe):
    try:
        # Setup parameters
        coordination_name, nodes_count, network_topology = parameters["use_case"].split("-")
        nodes_count = int(nodes_count)
        B, L = network_topologies[network_topology](nodes_count, parameters["bandwidth"])
        smltr = esds.Simulator({"eth0": {"bandwidth": B, "latency": L, "is_wired": False}})
        root_results_dir = f"{os.environ['HOME']}/results-reconfiguration-esds/topologies/{['paper', 'tests'][test_expe]}"
        expe_results_dir = f"{root_results_dir}/{parameters['use_case']}-{parameters['uptime_duration']}/{parameters['id_run']}"
        t = int(time.time()*1000)

        current_dir_name = os.path.dirname(os.path.abspath(__file__))
        if not test_expe:
            uptimes_schedule_name = f"{current_dir_name}/uptimes_schedules/{parameters['id_run']}-{parameters['uptime_duration']}.json"
        else:
            uptimes_schedule_name = f"{current_dir_name}/expe_tests/{parameters['use_case']}.json"
            if not exists(uptimes_schedule_name):
                print(f"No test found for {parameters['use_case']}")

        node_arguments = {
            "stress_conso": parameters["stress_conso"],
            "idle_conso": parameters["idle_conso"],
            "comms_conso": parameters["comms_conso"],
            "bandwidth": parameters["bandwidth"],
            "results_dir": expe_results_dir,
            "nodes_count": nodes_count,
            "uptimes_schedule_name": uptimes_schedule_name,
            "tasks_list": coord_name_tasks_lists[coordination_name](nodes_count - 1),
            "s": shared_memory.SharedMemory(f"shm_cps_{parameters['id_run']}-{parameters['uptime_duration']}-{t}", create=True, size=nodes_count)
        }
        sys.path.append("..")
        os.makedirs(expe_results_dir, exist_ok=True)
        os.makedirs(f"/tmp/{parameters['use_case']}/{parameters['id_run']}-{parameters['uptime_duration']}", exist_ok=True)

        # Setup and launch simulation
        for node_num in range(nodes_count):
            smltr.create_node("on_pull", interfaces=["eth0"], args=node_arguments)
        with open(f"/tmp/{parameters['use_case']}/{parameters['id_run']}-{parameters['uptime_duration']}/debug.txt", "w") as f:
            with redirect_stdout(f):
                smltr.run(interferences=False)
        node_arguments["s"].close()
        node_arguments["s"].unlink()

        # If test, verification
        if test_expe:
            with open(f"{current_dir_name}/expe_tests/{parameters['use_case']}.yaml") as f:
                expected_results = yaml.safe_load(f)["expected_result"]
            shared_methods.verify_results(expected_results, expe_results_dir)

        print(f"{parameters['use_case']}: done")

        # Go to next parameter
        sweeper.done(parameters)
    except Exception as exc:
        traceback.print_exc()
        sweeper.skip(parameters)


def main(test_expe):
    if test_expe:
        print("Testing")
    else:
        print("Simulation start")

    nb_cores = math.ceil(cpu_count() * 0.5)
    parameters = sweeper.get_next()
    with Pool(nb_cores) as pool:
        l = []
        while parameters is not None:
            print(f"registering {parameters}")
            e = pool.apply_async(run_simulation, args=(parameters, test_expe))
            parameters = sweeper.get_next()
            l.append(e)
        pool.close()
        pool.join()


if __name__ == "__main__":
    test_expe = True
    parameter_list = {
        "use_case": ["deploy-6-star"],
        "stress_conso": [1.358],
        "idle_conso": [1.339],
        "comms_conso": [0.16],
        "bandwidth": [50_000],
        "id_run": [0, 1, 2, 3, 4, 5],
        "uptime_duration": [60]
    }
    sweeps = sweep(parameter_list)

    # Initialise sweeper in global scope to be copied on all processes
    sweeper = ParamSweeper(
        persistence_dir=os.path.join(os.environ['HOME'], "optim-esds-sweeper"), sweeps=sweeps, save_sweeps=True
    )
    main(test_expe)
