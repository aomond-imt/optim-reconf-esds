import math
import os
import sys
import traceback
from contextlib import redirect_stdout
from multiprocessing import cpu_count, shared_memory
from multiprocessing.pool import Pool
import time

import esds
from esds.node import Node
from execo_engine import ParamSweeper, sweep

from topologies import clique, chain, ring, star

network_topologies = {
    "clique": clique,
    "chain": chain,
    "ring": ring,
    "star": star
}


use_cases_tasks_lists = {
    "default-chain": {
        "deploy": {
            5: [
                [["provide_install_0", 20.51, []]],
                [["use_install", 11.12, ["provide_install_0", "provide_install_2", "provide_install_3", "provide_install_4"]]],
                [["provide_install_2", 6.24, []]],
                [["provide_install_3", 4.52, []]],
                [["provide_install_4", 13.13, []]],
            ]
        }
    },
    "default-star": {
        "deploy": {
            6: [
                [["t_sa", 1.03, []], [f"t_sc", 7.20, [f"t_di_{dep_num}" for dep_num in range(5)]], [f"t_sr", 10.51, [f"t_dr_{dep_num}" for dep_num in range(5)]]],
                *[[[f"t_di_{dep_num}", dep_times[0], []], [f"t_dr_{dep_num}", dep_times[1], []]] for dep_num, dep_times in enumerate(
                    [(4.99, 16.69), (1.25, 1.52), (5.26, 2.29), (9.82, 2.41), (5.68, 1.40)]
                )]
            ]
        }
    }
}


def run_simulation(parameters, root_results_dir):
    try:
        coordination_name, network_topology, nodes_count, services_topology = parameters["use_case"].split("-")
        nodes_count = int(nodes_count)
        B, L = network_topologies[network_topology](nodes_count, parameters["bandwidth"])
        Node.available_node_id = 0  # TODO: notify Loic about it
        smltr = esds.Simulator({"eth0": {"bandwidth": B, "latency": L, "is_wired": False}})
        expe_results_dir = f"{root_results_dir}/{parameters['use_case']}-{parameters['uptime_duration']}/{parameters['id_run']}"
        t = int(time.time()*1000)
        node_arguments = {
            "stress_conso": parameters["stress_conso"],
            "idle_conso": parameters["idle_conso"],
            "comms_conso": parameters["comms_conso"],
            "bandwidth": parameters["bandwidth"],
            "results_dir": expe_results_dir,
            "nodes_count": nodes_count,
            # "uptimes_schedule_name": f"tests/pull/chained_aggregator_use.json",
            # "id_run": f"tests/pull/chained_aggregator_use.json",
            "uptimes_schedule_name": f"uptimes_schedules/{parameters['id_run']}-{parameters['uptime_duration']}.json",
            "tasks_list": use_cases_tasks_lists[f"{services_topology}-{network_topology}"][coordination_name][nodes_count],
            "s": shared_memory.SharedMemory(f"shm_cps_{parameters['id_run']}-{parameters['uptime_duration']}-{t}", create=True, size=nodes_count)
        }
        sys.path.append("..")
        os.makedirs(expe_results_dir, exist_ok=True)
        for node_num in range(nodes_count):
            smltr.create_node("on_pull", interfaces=["eth0"], args=node_arguments)
        os.makedirs(f"/tmp/{parameters['use_case']}/{parameters['id_run']}-{parameters['uptime_duration']}", exist_ok=True)
        with open(f"/tmp/{parameters['use_case']}/{parameters['id_run']}-{parameters['uptime_duration']}/debug.txt", "w") as f:
            with redirect_stdout(f):
                smltr.run(interferences=False)
        print(f"{parameters['use_case']}: done")
        node_arguments["s"].close()
        node_arguments["s"].unlink()
        sweeper.done(parameters)
    except Exception as exc:
        traceback.print_exc()
        sweeper.skip(parameters)


def main(root_results_dir):
    nb_cores = math.ceil(cpu_count() * 0.5)
    # nb_cores = 1
    parameters = sweeper.get_next()
    with Pool(nb_cores) as pool:
        l = []
        while parameters is not None:
            print(f"registering {parameters}")
            e = pool.apply_async(run_simulation, args=(parameters, root_results_dir))
            parameters = sweeper.get_next()
            l.append(e)
        pool.close()
        pool.join()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root_results_dir = sys.argv[1]
    else:
        root_results_dir = f"{os.environ['HOME']}/results-reconfiguration-esds/topologies/tests"
    parameter_list = {
        "use_case": ["deploy-star-6-default"],
        "stress_conso": [1.358],
        "idle_conso": [1.339],
        "comms_conso": [0.16],
        "bandwidth": [6250],
        "id_run": [0, 1, 2, 3, 4, 5],
        "uptime_duration": [60, 120, 180]
    }
    sweeps = sweep(parameter_list)

    # Initialise sweeper in global scope to be copied on all processes
    sweeper = ParamSweeper(
        persistence_dir=os.path.join(root_results_dir, "sweeper"), sweeps=sweeps, save_sweeps=True
    )
    main(root_results_dir)
