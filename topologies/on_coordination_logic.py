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
                         tot_uptimes_duration):
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
            "time": c(api),
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
    s.close()
    if api.node_id == 0:
        s.unlink()


def initialise_simulation(api):
    # Setup termination condition
    nodes_count = api.args["nodes_count"]
    expe_name = Path(api.args["results_dir"]).stem
    if api.node_id == 0:
        s = shared_memory.SharedMemory(f"shm_cps_{expe_name}", create=True, size=nodes_count)
    else:
        time.sleep(0.5)
        s = shared_memory.SharedMemory(f"shm_cps_{expe_name}")

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
    tasks_list = api.args["tasks_list"][api.node_id]
    current_task = tasks_list.pop(0)  # Current task trying to be run
    results_dir = api.args["results_dir"]

    return aggregated_send, all_uptimes_schedules, comms_cons, comms_conso, current_task, idle_conso, node_cons, nodes_count, results_dir, retrieved_data, s, stress_conso, tasks_list, tot_msg_rcv, tot_msg_sent, tot_reconf_duration, tot_sleeping_duration, tot_uptimes, tot_uptimes_duration, uptimes_schedule


def execute_reconf_task(api, idle_conso, name, node_cons, s, stress_conso, tasks_list,
                        time_task, tot_reconf_duration):
    api.log(f"Executing task {name}")
    node_cons.set_power(stress_conso)
    api.wait(time_task)
    tot_reconf_duration += time_task
    node_cons.set_power(idle_conso)
    if len(tasks_list) > 0:
        api.log("Getting next task")
        current_task = tasks_list.pop(0)
    else:
        api.log("All tasks done")
        current_task = None
        s.buf[api.node_id] = 1
    return current_task, tot_reconf_duration
