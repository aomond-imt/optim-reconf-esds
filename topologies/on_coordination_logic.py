import json
import os
import time
from multiprocessing import shared_memory

import yaml
from esds.node import Node
from esds.plugins.power_states import PowerStates, PowerStatesComms


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
    if api.node_id == 0:
        s = shared_memory.SharedMemory("shm_cps", create=True, size=5)
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
    tot_uptimes, tot_msg_sent, tot_msg_rcv = 0, 0, 0
    results_dir = api.args["results_dir"]

    # Get node's uptime schedule and initialise variable
    with open(f"uptimes_schedules/{api.args['uptimes_schedule_name']}") as f:
        uptimes_schedules = json.load(f)[api.node_id]  # Node uptime schedule
    retrieved_data = []  # All data retrieved from neighbors
    current_task = tasks_list.pop(0)  # Current task trying to be run

    def c():
        return api.read("clock")

    def is_time_up(deadline):
        return c() >= deadline

    def remaining_time(deadline):
        return max(deadline - c(), 0)

    # Duty-cycle simulation
    for uptime, duration in uptimes_schedules:
        node_cons.set_power(0)
        api.turn_off()
        api.wait(uptime - c())
        api.turn_on()
        node_cons.set_power(idle_conso)
        tot_uptimes += 1
        # Loop until all tasks are done
        while current_task is not None and not is_time_up(uptime + duration):
            name, time_task, dependencies = current_task
            # Resolve dependencies
            while not all(dep in retrieved_data for dep in dependencies) and not is_time_up(uptime + duration):
                # Ask only for not retrieved dependencies
                req_dependencies = [dep for dep in dependencies if dep not in retrieved_data]
                # Request dependencies to all neighbors
                api.sendt("eth0", ("req", req_dependencies), 257, 0, timeout=remaining_time(uptime + duration))
                tot_msg_sent += 1
                # Listen to response and to other neighbors' requests
                code, data = api.receivet("eth0", timeout=min(1, remaining_time(uptime + duration)))
                while data is not None and not is_time_up(uptime + duration):
                    type_data, content_data = data
                    tot_msg_rcv += 1
                    if type_data == "rep" and content_data in dependencies:
                        retrieved_data.append(content_data)
                    if type_data == "req":
                        # Send all available requested dependencies
                        for content in content_data:
                            if content in retrieved_data:
                                api.sendt("eth0", ("rep", content), 257, 0, timeout=remaining_time(uptime + duration))
                                tot_msg_sent += 1
                    code, data = api.receivet("eth0", timeout=min(0.1, remaining_time(uptime + duration)))

            if not is_time_up(uptime + duration) and all(dep in retrieved_data for dep in dependencies):
                # When dependencies are resolved, execute reconf task
                api.log("doing task")
                node_cons.set_power(stress_conso)
                api.wait(time_task)
                node_cons.set_power(idle_conso)
                # Append the task done to the retrieved_data list
                retrieved_data.append(name)
                if len(tasks_list) > 0:
                    current_task = tasks_list.pop(0)
                else:
                    api.log("all tasks done cya nerds")
                    current_task = None
                    s.buf[api.node_id] = 1

        # When all ONs tasks are done, stay in receive mode until the end of reconf
        while not is_time_up(uptime + duration) and any(buf_flag == 0 for buf_flag in s.buf):
            code, data = api.receivet("eth0", timeout=min(1, remaining_time(uptime + duration)))
            # api.log(f"received {data}")
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
            break

    # Report metrics
    node_cons.set_power(0)
    node_cons.report_energy()
    comms_cons.report_energy()
    api.log(f"Tot nb uptimes: {tot_uptimes}")
    api.log(f"Tot msg sent: {tot_msg_sent}")
    api.log(f"Tot msg rcv: {tot_msg_rcv}")
    results_dir_exec = f"{results_dir}"
    os.makedirs(results_dir_exec, exist_ok=True)
    with open(f"{results_dir_exec}/{api.node_id}.yaml", "w") as f:
        yaml.safe_dump({
            "time": c(),
            "node_cons": node_cons.energy,
            "comms_cons": float(comms_cons.get_energy()),
            "tot_uptimes": tot_uptimes,
            "tot_msg_sent": tot_msg_sent,
            "tot_msg_rcv": tot_msg_rcv,
        }, f)

    api.log("terminating")
    s.close()
    if api.node_id == 0:
        s.unlink()
