from esds.node import Node

from expes_topologies.on_coordination_logic import initialise_simulation, is_time_up, is_isolated_uptime, remaining_time, \
    FREQ_POLLING, terminate_simulation, c, is_finished


def execute(api: Node):
    """
    Note:
    - Do not consume messages when executing tasks. Message can accumulate leading
      to mass responses after task is complete
    :param api:
    :return:
    """
    (
        aggregated_send,
        all_uptimes_schedules,
        comms_cons,
        comms_conso,
        current_concurrent_tasks,
        idle_conso,
        node_cons,
        nodes_count,
        results_dir,
        retrieved_data,
        s,
        stress_conso,
        tasks_list,
        tot_msg_rcv,
        tot_msg_sent,
        tot_reconf_duration,
        tot_sleeping_duration,
        tot_uptimes,
        tot_uptimes_duration,
        uptimes_schedule
    ) = initialise_simulation(api)

    deps_to_retrieve = set()
    for _, _, task_dep in current_concurrent_tasks:
        deps_to_retrieve.add(task_dep)

    deps_retrieved = {None}
    local_termination = 0

    # Duty-cycle simulation
    for uptime, duration in uptimes_schedule:
        # Sleeping period
        node_cons.set_power(0)
        api.turn_off()
        sleeping_duration = uptime - c(api)
        api.wait(sleeping_duration)
        tot_sleeping_duration += sleeping_duration

        # Uptime period
        api.turn_on()
        node_cons.set_power(idle_conso)
        uptime_end = uptime + duration

        # Coordination loop
        while not is_time_up(api, uptime_end) and not is_finished(s):
            if current_concurrent_tasks is not None:
                tasks_to_do = []
                for task in current_concurrent_tasks:
                    _, _, task_dep = task
                    if task_dep in deps_retrieved:
                        tasks_to_do.append(task)

                if len(tasks_to_do) > 0:
                    # Execute tasks
                    max_task_time = max(task_time for _, task_time, _ in tasks_to_do)
                    api.log(f"Executing concurrent tasks {tasks_to_do}")
                    node_cons.set_power(stress_conso)
                    api.wait(max_task_time)
                    tot_reconf_duration += max_task_time
                    node_cons.set_power(idle_conso)
                    for task_name, _, _ in tasks_to_do:
                        deps_retrieved.add(task_name)

                for task in tasks_to_do:
                    current_concurrent_tasks.remove(task)

                if len(current_concurrent_tasks) == 0:
                    current_concurrent_tasks = tasks_list.pop(0) if len(tasks_list) > 0 else None
                    s.buf[api.node_id] = current_concurrent_tasks is None
                    if current_concurrent_tasks is not None:
                        for _, _, task_dep in current_concurrent_tasks:
                            deps_to_retrieve.add(task_dep)

                    # Save metrics
                    if current_concurrent_tasks is None:
                        local_termination = c(api)
                        api.log("All tasks done")
                    else:
                        api.log(f"New concurrent tasks: {current_concurrent_tasks}")
                        api.log(f"deps_to_retrieve: {deps_to_retrieve}")


            # Ask for missing deps
            if len(deps_to_retrieve) > 0:
                api.sendt("eth0", ("req", deps_to_retrieve), 257, 0, timeout=remaining_time(api, uptime_end))

            # Receive msgs and put them in buffer (do not put duplicates in buf)
            buf = []
            timeout = 0.01
            code, data = api.receivet("eth0", timeout=timeout)
            while data is not None and not is_time_up(api, uptime_end) and not is_finished(s):
                api.log(f"Log: received {data}")
                if data not in buf:
                    buf.append(data)
                code, data = api.receivet("eth0", timeout=timeout)

            # Treat each received msg
            for data in buf:
                type_msg, deps = data
                if type_msg == "req":
                    deps_to_send = deps_retrieved.intersection(deps)
                    if len(deps_to_send) > 0:
                        api.log(f"Sending deps: {deps_to_send}")
                        api.sendt("eth0", ("res", deps_to_send), 257, 0, timeout=remaining_time(api, uptime_end))
                    deps_to_retrieve.update(deps.difference(deps_retrieved))
                if type_msg == "res":
                    for dep in deps:
                        if dep in deps_to_retrieve:
                            api.log(f"Retrieved deps: {dep}")
                            deps_retrieved.add(dep)
                            deps_to_retrieve.remove(dep)

            if not is_finished(s):
                api.wait(min(1, remaining_time(api, uptime_end)))

        tot_uptimes += 1
        tot_uptimes_duration += c(api) - uptime

        if is_finished(s):
            api.log("All nodes finished, terminating")
            break

    terminate_simulation(aggregated_send, api, comms_cons, comms_conso, current_concurrent_tasks, node_cons, results_dir, s,
                         tot_msg_rcv, tot_msg_sent, tot_reconf_duration, tot_sleeping_duration, tot_uptimes,
                         tot_uptimes_duration, local_termination)
