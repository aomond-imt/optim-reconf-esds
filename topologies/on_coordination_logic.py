import json
import math
import os
import time
from multiprocessing import shared_memory

import yaml
from esds.node import Node
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


def execute_coordination_tasks(api: Node, tasks_list):
    """
    Weaknesses:
    - Do not consume messages when executing tasks. Message can accumulate leading
      to mass responses after task is complete
    :param api:
    :param tasks_list:
    :return:
    """
    # Setup termination condition
    nodes_count = api.args["nodes_count"]
    if api.node_id == 0:
        s = shared_memory.SharedMemory("shm_cps", create=True, size=nodes_count)
    else:
        time.sleep(0.5)
        s = shared_memory.SharedMemory("shm_cps")

    # Setup energy calibration
    interface_name = "eth0"
    idle_conso = api.args["idle_conso"]
    stress_conso = api.args["stress_conso"]
    comms_conso = api.args["comms_conso"]
    node_cons = PowerStates(api, 0)
    comms_cons = PowerStatesComms(api)
    comms_cons.set_power(interface_name, 0, comms_conso, comms_conso)

    # Setup metrics
    tot_uptimes, tot_msg_sent, tot_msg_rcv, tot_uptimes_duration, tot_reconf_duration, tot_sleeping_duration = 0, 0, 0, 0, 0, 0
    results_dir = api.args["results_dir"]

    # Get node's uptime schedule and initialise variable
    uptimes_schedule_name = api.args['uptimes_schedule_name']
    with open(uptimes_schedule_name) as f:
        all_uptimes_schedules = json.load(f)  # Get all uptimes schedules for simulation optimization
    uptimes_schedules = all_uptimes_schedules[api.node_id]  # Node uptime schedule
    retrieved_data = []  # All data retrieved from neighbors
    current_task = tasks_list.pop(0)  # Current task trying to be run
    aggregated_send = 0  # Count the number of send computed but not simulated

    def c():
        return api.read("clock")

    def is_time_up(deadline):
        return c() + 0.0001 >= deadline  # Add epsilon to compensate float operations inaccuracy

    def remaining_time(deadline):
        return max(deadline - c(), 0)

    # Duty-cycle simulation
    for uptime, duration in uptimes_schedules:
        # Sleeping period
        node_cons.set_power(0)
        api.turn_off()
        sleeping_duration = uptime - c()
        api.wait(sleeping_duration)
        tot_sleeping_duration += sleeping_duration

        # Uptime period
        api.turn_on()
        node_cons.set_power(idle_conso)

        # Loop until all tasks are done
        while current_task is not None and not is_time_up(uptime + duration):
            name, time_task, dependencies = current_task

            # Resolve dependencies and catch incoming requests
            if not is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules, nodes_count):
                while not all(dep in retrieved_data for dep in dependencies) and not is_time_up(uptime + duration):
                    # Ask only for not retrieved dependencies
                    req_dependencies = [dep for dep in dependencies if dep not in retrieved_data]
                    # Request dependencies to all neighbors
                    api.sendt("eth0", ("req", req_dependencies), 257, 0, timeout=remaining_time(uptime + duration))
                    tot_msg_sent += 1
                    # Listen to response and to other neighbors' requests
                    code, data = api.receivet("eth0", timeout=min(0.05, remaining_time(uptime + duration)))
                    while data is not None and not is_time_up(uptime + duration):
                        type_data, content_data = data
                        tot_msg_rcv += 1
                        if type_data == "rep" and content_data in dependencies:
                            api.log(f"Appending {content_data}")
                            retrieved_data.append(content_data)
                        if type_data == "req":
                            # Catch incoming dependencies requests and respond if possible
                            for content in content_data:
                                if content in retrieved_data:
                                    api.log(f"Sending {content}")
                                    api.sendt("eth0", ("rep", content), 257, 0, timeout=remaining_time(uptime + duration))
                                    tot_msg_sent += 1
                        code, data = api.receivet("eth0", timeout=min(0.1, remaining_time(uptime + duration)))
                    api.wait(FREQ_POLLING)

            # When dependencies are resolved, execute reconf task
            if not is_time_up(uptime + duration) and all(dep in retrieved_data for dep in dependencies):
                api.log(f"Executing task {name}")
                node_cons.set_power(stress_conso)
                api.wait(time_task)
                tot_reconf_duration += time_task
                node_cons.set_power(idle_conso)
                # Append the task done to the retrieved_data list
                retrieved_data.append(name)
                if len(tasks_list) > 0:
                    api.log("Getting next task")
                    current_task = tasks_list.pop(0)
                else:
                    api.log("All tasks done")
                    current_task = None
                    s.buf[api.node_id] = 1

            # If isolated uptime, simulate the sending of the node during the remaining uptime
            if is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules, nodes_count):
                remaining_t = remaining_time(uptime + duration)
                api.wait(remaining_t)
                th_aggregated_send = remaining_t/((257/6250) + 0.05 + FREQ_POLLING)
                aggregated_send += int(th_aggregated_send)

                # Check if sending an additional message doesn't cross the deadline, and add it if it's the case
                if int(th_aggregated_send) - th_aggregated_send <= 257/6250:
                    aggregated_send += 1

                api.log(f"Isolated uptime, simulating {th_aggregated_send} sends")

        # When all ONs tasks are done, stay in receive mode until the end of reconf
        if not is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules, nodes_count):
            api.log("Entering receive mode")
            while not is_time_up(uptime + duration) and any(buf_flag == 0 for buf_flag in s.buf):
                code, data = api.receivet("eth0", timeout=min(1, remaining_time(uptime + duration)))
                if data is not None:
                    type_data, content_data = data
                    tot_msg_rcv += 1
                    if type_data == "req":
                        # Send all available requested dependencies
                        for content in content_data:
                            if content in retrieved_data:
                                api.sendt("eth0", ("rep", content), 257, 0, timeout=remaining_time(uptime + duration))
                                tot_msg_sent += 1

        if all(buf_flag == 1 for buf_flag in s.buf):
            api.log("All nodes finished, terminating")
            tot_uptimes += 1
            tot_uptimes_duration += c() - uptime
            break

        if is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules, nodes_count):
            remaining_t = remaining_time(uptime + duration)
            api.log(f"Isolated uptime, simulating {remaining_t} receive mode time")
            api.wait(remaining_t)

        tot_uptimes += 1
        tot_uptimes_duration += c() - uptime

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
    results_dir_exec = f"{results_dir}/{uptimes_schedule_name}"
    os.makedirs(results_dir_exec, exist_ok=True)
    with open(f"{results_dir_exec}/{api.node_id}.yaml", "w") as f:
        yaml.safe_dump({
            "finished_reconf": current_task is None,
            "time": c(),
            "node_cons": node_cons.energy,
            "comms_cons": float(comms_cons.get_energy() + aggregated_send * comms_conso),
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
