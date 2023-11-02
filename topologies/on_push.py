from esds import rcode
from esds.node import Node

from topologies.on_coordination_logic import initialise_simulation, is_time_up, is_isolated_uptime, remaining_time, \
    FREQ_POLLING, terminate_simulation, c, is_finished, execute_reconf_task


def are_all_data_shared(data_to_share, neighbor_nodes):
    for receiver_ids in data_to_share.values():
        for n_id in neighbor_nodes:
            if n_id not in receiver_ids:
                return False
    return True


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

    # Variables used for pushing
    neighbor_nodes = api.args["neighbor_nodes"]
    data_to_share = {}  # Dict of {data_name: receiver_ids}

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

        while not is_time_up(api, uptime_end) and not is_finished(s):
            if not are_all_data_shared(data_to_share, neighbor_nodes):
                # api.log(str(("ping", api.node_id)))
                code = api.sendt("eth0", ("ping", (api.node_id, data_to_share.keys())), 87, 0, timeout=remaining_time(api, uptime_end))
                if code == rcode.RCode.SUCCESS:
                    tot_msg_sent += 1
            if current_task is not None and all(dep in data_to_share.keys() for dep in current_task[2]):
                new_current_task, tot_reconf_duration = execute_reconf_task(api, idle_conso, current_task[0], node_cons,
                                                                            s, stress_conso, tasks_list,
                                                                            current_task[1], tot_reconf_duration)
                data_to_share[current_task[0]] = []
                current_task = new_current_task
            timeout = min(1, remaining_time(api, uptime_end)) if len(data_to_share) > 0 else remaining_time(api, uptime_end)
            code, data = api.receivet("eth0", timeout=timeout)
            while data is not None and not is_time_up(api, uptime_end):
                type_data, content_data = data
                # api.log(f"received {str((code,data))}")
                tot_msg_rcv += 1
                if type_data == "ping":
                    id_sender, data_shared = content_data
                    if any(d not in data_to_share.keys() for d in data_shared):
                        # api.log(str(("ping_ack", (api.node_id, id_sender))))
                        code = api.sendt("eth0", ("ping_ack", (api.node_id, id_sender)), 87, 0, timeout=remaining_time(api, uptime_end))
                        if code == rcode.RCode.SUCCESS:
                            tot_msg_sent += 1
                if type_data == "ping_ack":
                    id_sender, id_original_sender = content_data
                    if id_original_sender == api.node_id:
                        for data_name, receiver_ids in data_to_share.items():
                            if id_sender not in receiver_ids:
                                # api.log(str(("data", (data_name, api.node_id))))
                                code = api.sendt("eth0", ("data", (data_name, api.node_id)), 257, 0, timeout=remaining_time(api, uptime_end))
                                if code == rcode.RCode.SUCCESS:
                                    tot_msg_sent += 1
                if type_data == "data":
                    data_name, id_sender = content_data
                    if data_name not in data_to_share.keys():
                        data_to_share[data_name] = [id_sender]
                        # api.log(str(("data_ack", (data_name, api.node_id))))
                        code = api.sendt("eth0", ("data_ack", (data_name, api.node_id)), 87, 0, timeout=remaining_time(api, uptime_end))
                        if code == rcode.RCode.SUCCESS:
                            tot_msg_sent += 1
                if type_data == "data_ack":
                    data_name, id_sender = content_data
                    if id_sender not in data_to_share[data_name]:
                        data_to_share[data_name].append(id_sender)
                code, data = api.receivet("eth0", timeout=0.01)
                # if data is None:
                    # api.log("No more data to process")

        tot_uptimes_duration += c(api) - uptime

        if is_finished(s):
            api.log("All nodes finished, terminating")
            break

        tot_uptimes += 1

    terminate_simulation(aggregated_send, api, comms_cons, comms_conso, current_task, node_cons, results_dir, s,
                         tot_msg_rcv, tot_msg_sent, tot_reconf_duration, tot_sleeping_duration, tot_uptimes,
                         tot_uptimes_duration, 0)
