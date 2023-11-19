import math
import os
import shutil
import sys
import traceback
from contextlib import redirect_stdout
from multiprocessing import cpu_count, shared_memory, Process
import time
from os.path import exists

import esds
import yaml
from execo_engine import ParamSweeper, sweep

import shared_methods
from topologies import clique, chain, ring, star, grid, deploy_tasks_list_agg_0, deploy_tasks_list_agg_middle, deploy_tasks_list_grid_fav

topology_sizes = {
    "clique": {"small": 6, "medium": 16, "large": 31},
    "chain": {"small": 6, "medium": 16, "large": 31},
    "ring": {"small": 6, "medium": 16, "large": 31},
    "star": {"small": 6, "medium": 16, "large": 31},
    "grid": {"small": 9, "medium": 16, "large": 25}
}

tasks_list_tplgy = {
    "deploy-star-fav": (deploy_tasks_list_agg_0, star),
    "deploy-star-nonfav": (deploy_tasks_list_agg_middle, star),
    "deploy-ring-fav": (deploy_tasks_list_agg_0, ring),
    "deploy-chain-fav": (deploy_tasks_list_agg_middle, chain),
    "deploy-chain-nonfav": (deploy_tasks_list_agg_0, chain),
    "deploy-clique-fav": (deploy_tasks_list_agg_0, clique),
    "deploy-grid-fav": (deploy_tasks_list_grid_fav, grid),
    "deploy-grid-nonfav": (deploy_tasks_list_agg_0, grid),
}


def run_simulation(test_expe):
    print("Starting simulation")
    parameters = sweeper.get_next()
    while parameters is not None:
        print(f"Doing param {parameters}")
        root_results_dir = f"{os.environ['HOME']}/results-reconfiguration-esds/topologies/{['paper', 'tests'][test_expe]}"
        results_dir = f"{parameters['use_case']}-{parameters['topology_size']}-{parameters['uptime_duration']}/{parameters['id_run']}"
        expe_results_dir = f"{root_results_dir}/{results_dir}"
        tmp_results_dir = f"/tmp/{results_dir}"
        os.makedirs(expe_results_dir, exist_ok=True)
        os.makedirs(tmp_results_dir, exist_ok=True)
        debug_file_path = f"{tmp_results_dir}/debug.txt"

        try:
            # Setup parameters
            coordination_name, network_topology, _ = parameters["use_case"].split("-")
            nodes_count = topology_sizes[network_topology][parameters["topology_size"]]
            tasks_list, tplgy = tasks_list_tplgy[parameters["use_case"]]
            B, L = tplgy(nodes_count, parameters["bandwidth"])
            smltr = esds.Simulator({"eth0": {"bandwidth": B, "latency": L, "is_wired": False}})
            t = int(time.time()*1000)

            current_dir_name = os.path.dirname(os.path.abspath(__file__))
            if not test_expe:
                uptimes_schedule_name = f"{current_dir_name}/uptimes_schedules/{parameters['id_run']}-{parameters['uptime_duration']}.json"
            else:
                uptimes_schedule_name = f"{current_dir_name}/expe_tests/{parameters['use_case']}-{nodes_count}.json"
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
                "tasks_list": tasks_list(nodes_count - 1),
                "s": shared_memory.SharedMemory(f"shm_cps_{parameters['id_run']}-{parameters['uptime_duration']}-{t}", create=True, size=nodes_count)
            }
            sys.path.append("..")

            # Setup and launch simulation
            for node_num in range(nodes_count):
                smltr.create_node("on_pull", interfaces=["eth0"], args=node_arguments)
            with open(debug_file_path, "w") as f:
                with redirect_stdout(f):
                    smltr.run(interferences=False)
            node_arguments["s"].close()
            try:
                node_arguments["s"].unlink()
            except FileNotFoundError as e:
                traceback.print_exc()

            # If test, verification
            if test_expe:
                with open(f"{current_dir_name}/expe_tests/{parameters['use_case']}-{nodes_count}.yaml") as f:
                    expected_results = yaml.safe_load(f)["expected_result"]
                shared_methods.verify_results(expected_results, expe_results_dir)
            print(f"{results_dir}: done")

            # Go to next parameter
            sweeper.done(parameters)
        except Exception as exc:
            traceback.print_exc()
            sweeper.skip(parameters)
        finally:
            if exists(debug_file_path):
                shutil.copy(debug_file_path, expe_results_dir)
                os.remove(debug_file_path)
            parameters = sweeper.get_next()


if __name__ == "__main__":
    test_expe = False
    parameter_list = {
        "use_case": [
            "deploy-star-fav",
            "deploy-star-nonfav",
            "deploy-ring-fav",
            "deploy-chain-fav",
            "deploy-chain-nonfav",
            "deploy-clique-fav",
            "deploy-grid-nonfav",
            "deploy-grid-fav",
        ],
        "topology_size": ["small", "medium", "large"],
        "stress_conso": [2.697],
        "idle_conso": [1.339],
        "comms_conso": [0.16],
        "bandwidth": [50_000],
        "id_run": [0],
        "uptime_duration": [60]
    }
    sweeps = sweep(parameter_list)

    # Initialise sweeper in global scope to be copied on all processes
    sweeper = ParamSweeper(
        persistence_dir=os.path.join(os.environ['HOME'], "optim-esds-sweeper"+"-test"*test_expe), sweeps=sweeps, save_sweeps=True
    )

    if test_expe:
        print("Testing")
    else:
        print("Simulation start")

    nb_cores = math.ceil(cpu_count() * 0.5)
    print("Creating processes")
    processes = []
    for _ in range(nb_cores):
        print("got here")
        p = Process(target=run_simulation, args=(test_expe,))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
