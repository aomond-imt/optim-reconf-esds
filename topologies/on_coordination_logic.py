import json
from multiprocessing import shared_memory

from esds.node import Node


def execute_coordination_tasks(api: Node, tasks_list):
    with open(f"uptimes_schedules/{api.args['uptimes_schedule_name']}") as f:
        uptimes_schedules = json.load(f)[api.node_id]  # Node uptime schedule
    retrieved_data = []  # All data retrieved from neighbors
    current_task = tasks_list.pop(0)  # Current task trying to be run

    # Setup termination condition
    if api.node_id == 0:
        s = shared_memory.SharedMemory("shm_cps", create=True, size=5)
    else:
        s = shared_memory.SharedMemory("shm_cps")

    def c():
        return api.read("clock")

    def is_time_up(deadline):
        return c() >= deadline

    def remaining_time(deadline):
        return max(deadline - c(), 0)

    # Duty-cycle simulation
    for uptime, duration in uptimes_schedules:
        api.log("sleeping")
        api.wait(uptime - c())
        api.log("done")
        # Loop until all tasks are done
        while current_task is not None and not is_time_up(uptime + duration):
            name, time, dependencies = current_task
            api.log("starting task")
            # Resolve dependencies
            while not all(dep in retrieved_data for dep in dependencies) and not is_time_up(uptime + duration):
                # Ask only for not retrieved dependencies
                req_dependencies = [dep for dep in dependencies if dep not in retrieved_data]
                # Request dependencies to all neighbors
                api.sendt("eth0", ("req", req_dependencies), 257, 0, timeout=remaining_time(uptime + duration))
                # Listen to response and to other neighbors' requests
                code, data = api.receivet("eth0", timeout=min(1, remaining_time(uptime + duration)))
                # api.log(f"received {data}")
                while data is not None and not is_time_up(uptime + duration):
                    type_data, content_data = data
                    if type_data == "rep" and content_data in dependencies:
                        retrieved_data.append(content_data)
                    if type_data == "req":
                        # Send all available requested dependencies
                        for content in content_data:
                            if content in retrieved_data:
                                api.sendt("eth0", ("rep", content), 257, 0, timeout=remaining_time(uptime + duration))
                    code, data = api.receivet("eth0", timeout=min(0.1, remaining_time(uptime + duration)))

            if not is_time_up(uptime + duration) and all(dep in retrieved_data for dep in dependencies):
                # When dependencies are resolved, execute reconf task
                api.log("doing task")
                api.wait(time)
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
            api.log(f"received {data}")
            if data is not None:
                type_data, content_data = data
                if type_data == "req":
                    # Send all available requested dependencies
                    for content in content_data:
                        if content in retrieved_data:
                            api.sendt("eth0", ("rep", content), 257, 0, timeout=remaining_time(uptime + duration))

    api.log("terminating")
    s.close()
    if api.node_id == 0:
        s.unlink()
