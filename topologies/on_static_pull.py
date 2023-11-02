from esds.node import Node

from topologies.on_coordination_logic import initialise_simulation, is_time_up, is_isolated_uptime, remaining_time, \
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

        # Loop until all tasks are done
        while current_task is not None and not is_time_up(api, uptime_end):
            name, time_task, dependencies = current_task

            # Resolve dependencies and catch incoming requests
            if not is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules, nodes_count):
                while not all(dep in retrieved_data for dep in dependencies) and not is_time_up(api, uptime_end):
                    # Ask only for not retrieved dependencies
                    req_dependencies = [dep for dep in dependencies if dep not in retrieved_data]
                    # Request dependencies to all neighbors
                    api.sendt("eth0", ("req", req_dependencies), 257, 0, timeout=remaining_time(api, uptime_end))
                    if remaining_time(api, uptime_end) >= 257 / 6250:  # TODO: theoretical verification, use sendt code to check (when its working)
                        tot_msg_sent += 1
                    # Listen to response and to other neighbors' requests
                    code, data = api.receivet("eth0", timeout=min(0.05, remaining_time(api, uptime_end)))
                    while data is not None and not is_time_up(api, uptime_end):
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
                                    api.sendt("eth0", ("rep", content), 257, 0, timeout=remaining_time(api, uptime_end))
                                    if remaining_time(api, uptime_end) >= 257 / 6250:  # TODO: theoretical verification, use sendt code to check (when its working)
                                        tot_msg_sent += 1
                        code, data = api.receivet("eth0", timeout=min(0.05, remaining_time(api, uptime_end)))
                    api.wait(min(FREQ_POLLING, remaining_time(api, uptime_end)))

            # When dependencies are resolved, execute reconf task
            if not is_time_up(api, uptime_end) and all(dep in retrieved_data for dep in dependencies):
                current_task, tot_reconf_duration = execute_reconf_task(api, idle_conso, name, node_cons,
                                                                        s, stress_conso, tasks_list,
                                                                        time_task, tot_reconf_duration)
                # Append the task done to the retrieved_data list
                retrieved_data.append(name)

            # If isolated uptime, simulate the sending of the node during the remaining uptime (if dependencies need to be solved)
            if is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules, nodes_count) and not all(
                    dep in retrieved_data for dep in dependencies):
                remaining_t = remaining_time(api, uptime_end)
                api.wait(remaining_t)
                th_aggregated_send = remaining_t / ((257 / 6250) + 0.05 + FREQ_POLLING)
                aggregated_send += int(th_aggregated_send)

                # Check if sending an additional message doesn't cross the deadline, and add it if it's the case
                if int(th_aggregated_send) - th_aggregated_send <= 257 / 6250:
                    aggregated_send += 1

                api.log(f"Isolated uptime, simulating {th_aggregated_send} sends")

        # Receive and respond to requests until the end of reconf
        if current_task is None and not is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules,
                                                           nodes_count):
            api.log("Entering receive mode")
            while not is_time_up(api, uptime_end) and any(buf_flag == 0 for buf_flag in s.buf):
                code, data = api.receivet("eth0", timeout=min(1, remaining_time(api, uptime_end)))
                if data is not None:
                    type_data, content_data = data
                    tot_msg_rcv += 1
                    if type_data == "req":
                        # Send all available requested dependencies
                        for content in content_data:
                            if content in retrieved_data:
                                api.sendt("eth0", ("rep", content), 257, 0, timeout=remaining_time(api, uptime_end))
                                if remaining_time(api,
                                                  uptime_end) >= 257 / 6250:  # TODO: theoretical verification, use sendt code to check (when its working)
                                    tot_msg_sent += 1

        # Check for termination condition
        if is_finished(s):
            api.log("All nodes finished, terminating")
            tot_uptimes += 1
            tot_uptimes_duration += c(api) - uptime
            break

        # Receive period for simulation duration optimization
        if is_isolated_uptime(api.node_id, tot_uptimes, all_uptimes_schedules, nodes_count):
            remaining_t = remaining_time(api, uptime_end)
            api.log(f"Isolated uptime, simulating {remaining_t} receive mode time (no energy cost)")
            api.wait(remaining_t)

        tot_uptimes += 1
        tot_uptimes_duration += c(api) - uptime

    terminate_simulation(aggregated_send, api, comms_cons, comms_conso, current_task, node_cons, results_dir, s,
                         tot_msg_rcv, tot_msg_sent, tot_reconf_duration, tot_sleeping_duration, tot_uptimes,
                         tot_uptimes_duration, 0)
