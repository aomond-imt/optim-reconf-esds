from esds.node import Node

from expes_topologies.on_coordination_logic import initialise_simulation, is_time_up, is_isolated_uptime, remaining_time, \
    FREQ_POLLING, terminate_simulation, c, execute_reconf_task, is_finished


def execute(api: Node):
    """
    Weaknesses:
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
        current_task,
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

    deps_to_retrieve = []
    deps_retrieved = []
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
            # Append the deps to request
            if current_task is not None and not all(dep in deps_retrieved for dep in current_task[2]):
                for dep in current_task[2]:
                    if dep not in deps_to_retrieve:
                        deps_to_retrieve.append(dep)

            # Execute task if deps are resolved
            if current_task is not None and all(dep in deps_retrieved for dep in current_task[2]):
                new_current_task, tot_reconf_duration = execute_reconf_task(
                    api, idle_conso, current_task[0], node_cons, s, stress_conso, tasks_list, current_task[1],
                    tot_reconf_duration
                )
                deps_retrieved.append(current_task[0])
                current_task = new_current_task
                if current_task is None:
                    local_termination = c(api)

            # Ask for missing deps
            if len(deps_to_retrieve) > 0:
                for dep in deps_to_retrieve:
                    api.sendt("eth0", ("req", dep), 257, 0, timeout=remaining_time(api, uptime_end))

            # Treat incoming msgs
            # if current_task is None and len(deps_to_retrieve) == 0:
            #     timeout = remaining_time(api, uptime_end)
            # else:
            buf = []
            timeout = 0.05
            code, data = api.receivet("eth0", timeout=timeout)
            while data is not None and not is_time_up(api, uptime_end) and not is_finished(s):
                type_msg, dep = data
                if data not in buf:
                    buf.append((type_msg, dep))
                code, data = api.receivet("eth0", timeout=0.05)

            for data in buf:
                type_msg, dep = data
                api.log(f"Treat: {type_msg} {dep}")
                if type_msg == "req":
                    if dep in deps_retrieved:
                        api.sendt("eth0", ("res", dep), 257, 0, timeout=remaining_time(api, uptime_end))
                    elif dep not in deps_to_retrieve:
                        deps_to_retrieve.append(dep)
                if type_msg == "res":
                    # Non-interested nodes do not retrieve dep
                    if dep in deps_to_retrieve and dep not in deps_retrieved:
                        deps_retrieved.append(dep)
                        deps_to_retrieve.remove(dep)
                # code, data = api.receivet("eth0", timeout=0.05)

            if not is_finished(s):
                api.wait(min(0.5, remaining_time(api, uptime_end)))

        tot_uptimes += 1
        tot_uptimes_duration += c(api) - uptime

        if is_finished(s):
            api.log("All nodes finished, terminating")
            break

    terminate_simulation(aggregated_send, api, comms_cons, comms_conso, current_task, node_cons, results_dir, s,
                         tot_msg_rcv, tot_msg_sent, tot_reconf_duration, tot_sleeping_duration, tot_uptimes,
                         tot_uptimes_duration, local_termination)
