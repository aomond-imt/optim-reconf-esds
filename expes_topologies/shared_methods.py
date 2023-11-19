import copy
import json
import os
import time
from multiprocessing import shared_memory
from pathlib import Path

import yaml
from esds.plugins.power_states import PowerStates, PowerStatesComms

FREQ_POLLING = 1


def is_isolated_uptime(node_num, hour_num, uptime_schedules, nodes_count):
    """
    TODO: check if an overlap can happen between current hour and previous hour
    Optimization method for simulation
    :return: True if an uptime never overlap during this hour
    """
    uptime_start, uptime_duration = uptime_schedules[node_num][hour_num]
    uptime_end = uptime_start + uptime_duration
    # print(f"-- node {node_num}, {hour_num} round, {uptime_start}s/{uptime_end}s --")
    for n_node_num, node_schedule in enumerate(uptime_schedules[:nodes_count]):
        if n_node_num != node_num:
            n_uptime_start, n_uptime_duration = node_schedule[hour_num]
            n_uptime_end = n_uptime_start + n_uptime_duration
            res = min(uptime_end, n_uptime_end) - max(uptime_start, n_uptime_start)
            # print(f"With node {n_node_num}: {n_uptime_start}s/{n_uptime_end}s, res: {res} {res > 0}")
            if res > 0:
                return False

    return True


def c(api):
    return api.read("clock")


def is_time_up(api, deadline):
    return c(api) + 0.0001 >= deadline  # Add epsilon to compensate float operations inaccuracy


def remaining_time(api, deadline):
    return max(deadline - c(api), 0)


def is_finished(s):
    return all(buf_flag == 1 for buf_flag in s.buf)


def terminate_simulation(aggregated_send, api, comms_cons, comms_conso, current_task, node_cons, results_dir, s,
                         tot_msg_rcv, tot_msg_sent, tot_reconf_duration, tot_sleeping_duration, tot_uptimes,
                         tot_uptimes_duration, local_termination):
    # Terminate
    api.log("Terminating")
    api.turn_off()

    # Report metrics
    node_cons.set_power(0)
    node_cons.report_energy()
    comms_cons.report_energy()
    api.log(f"Tot nb uptimes: {tot_uptimes}")
    api.log(f"Tot msg sent: {tot_msg_sent}")
    api.log(f"Tot msg rcv: {tot_msg_rcv}")
    api.log(f"Tot aggregated send: {aggregated_send}")
    os.makedirs(results_dir, exist_ok=True)
    with open(f"{results_dir}/{api.node_id}.yaml", "w") as f:
        yaml.safe_dump({
            "finished_reconf": current_task is None,
            "global_termination_time": c(api),
            "local_termination_time": local_termination,
            "node_cons": node_cons.energy,
            "comms_cons": float(comms_cons.get_energy() + aggregated_send * (257 / 6250) * comms_conso),
            "tot_uptimes": tot_uptimes,
            "tot_msg_sent": tot_msg_sent,
            "tot_msg_rcv": tot_msg_rcv,
            "tot_aggregated_send": aggregated_send,
            "tot_uptimes_duration": tot_uptimes_duration,
            "tot_reconf_duration": tot_reconf_duration,
            "tot_sleeping_duration": tot_sleeping_duration,
        }, f)
    api.log("terminating")


def initialise_simulation(api):
    # Setup termination condition
    s = api.args["s"]

    # Energy calibration
    interface_name = "eth0"
    idle_conso = api.args["idle_conso"]
    stress_conso = api.args["stress_conso"]
    comms_conso = api.args["comms_conso"]
    node_cons = PowerStates(api, 0)
    comms_cons = PowerStatesComms(api)
    comms_cons.set_power(interface_name, 0, comms_conso, comms_conso)

    # Metrics
    tot_uptimes, tot_msg_sent, tot_msg_rcv, tot_uptimes_duration, tot_reconf_duration, tot_sleeping_duration = 0, 0, 0, 0, 0, 0
    aggregated_send = 0  # Count the number of send computed but not simulated

    # Uptime schedule and variable initialisation
    uptimes_schedule_name = api.args['uptimes_schedule_name']
    with open(uptimes_schedule_name) as f:
        all_uptimes_schedules = json.load(f)  # Get all uptimes schedules for simulation optimization
    uptimes_schedule = all_uptimes_schedules[api.node_id]  # Node uptime schedule
    retrieved_data = []  # All data retrieved from neighbors
    tasks_list = copy.deepcopy(api.args["tasks_list"][api.node_id])
    current_concurrent_tasks = tasks_list.pop(0)  # Current task trying to be run
    results_dir = api.args["results_dir"]
    nodes_count = api.args["nodes_count"]

    api.log("Parameters:")
    api.log(f"idle_conso: {idle_conso}")
    api.log(f"stress_conso: {stress_conso}")
    api.log(f"comms_conso: {comms_conso}")
    api.log(f"uptimes_schedule_name: {uptimes_schedule_name}")
    api.log(f"tasks_list: {tasks_list}")
    api.log(f"results_dir: {results_dir}")
    api.log(f"nodes_count: {nodes_count}")

    return aggregated_send, all_uptimes_schedules, comms_cons, comms_conso, current_concurrent_tasks, idle_conso, node_cons, nodes_count, results_dir, retrieved_data, s, stress_conso, tasks_list, tot_msg_rcv, tot_msg_sent, tot_reconf_duration, tot_sleeping_duration, tot_uptimes, tot_uptimes_duration, uptimes_schedule


def verify_results(expected_result, test_dir):
    errors = []
    # Check result for each node
    for node_num, expected_node_results in expected_result.items():
        # Load node results
        with open(f"{test_dir}/{node_num}.yaml") as f:
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
