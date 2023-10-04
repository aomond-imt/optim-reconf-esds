import os
from multiprocessing import shared_memory

from esds.node import Node

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

import simulation_functions

duration = 60
aggregator_id = 0


def execute(api: Node):
    (
        uptimes_schedules,
        interface_name,
        datasize,
        bandwidth,
        freq_polling,
        node_cons,
        nb_msrmt,
        comms_cons,
        idle_conso,
        stress_conso,
        results_dir,
        tot_uptimes,
        tot_msg_sent,
        tot_msg_rcv
    ) = simulation_functions.initialisation(api)

    aggregator_acks = {
        "install": False,
        "run": False,
    }
    s = shared_memory.SharedMemory("shm_cps")

    def c():
        return api.read("clock")

    actions_done = False
    actions_duration = 20  # install + run
    api.turn_off()
    for uptime, d in uptimes_schedules:
        api.wait(uptime - c())
        if all(s.buf[i] == 1 for i in range(nb_msrmt + 1)):
            break
        api.turn_on()
        tot_uptimes += 1
        if not actions_done:
            api.log(f"Execute install and run")
            node_cons.set_power(stress_conso)
            api.wait(actions_duration)
            actions_done = True
        node_cons.set_power(idle_conso)
        end_uptime = uptime + d
        while not all(aggregator_acks.values()) and c() < end_uptime:
            code, data = api.receivet(interface_name, timeout=end_uptime - c())
            tot_msg_rcv += 1
            if data is not None:
                sender_id, coord_name = data
                if sender_id == aggregator_id and not aggregator_acks[coord_name]:
                    api.log("Sending ack to aggregator")
                    api.send(interface_name, api.node_id, datasize, aggregator_id)
                    tot_msg_sent += 1
                    aggregator_acks[coord_name] = True
        if c() < end_uptime:
            api.wait(end_uptime - c())
        api.turn_off()
        node_cons.set_power(0)
        if all(aggregator_acks.values()):
            s.buf[api.node_id] = 1

    simulation_functions.report_metrics(api, c, comms_cons, node_cons, results_dir, tot_msg_rcv, tot_msg_sent, tot_uptimes)
    s.close()
