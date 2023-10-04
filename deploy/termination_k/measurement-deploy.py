import os

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
        sending_cons,
        idle_conso,
        tot_uptimes,
        tot_msg_sent,
        tot_msg_rcv
    ) = simulation_functions.initialisation(api)

    aggregator_ack = False

    def c():
        return api.read("clock")

    api.turn_off()
    for uptime, d in uptimes_schedules:
        api.wait(uptime - c())
        api.turn_on()
        tot_uptimes += 1
        node_cons.set_power(idle_conso)
        end_uptime = uptime + d
        while not aggregator_ack and c() < end_uptime:
            code, data = api.receivet(interface_name, timeout=end_uptime - c())
            tot_msg_rcv += 1
            if data == aggregator_id:
                api.log("Sending ack to aggregator")
                api.send(interface_name, api.node_id, datasize, aggregator_id)
                tot_msg_sent += 1
                aggregator_ack = True
        api.turn_off()
        node_cons.set_power(0)
        if aggregator_ack:
            break

    node_cons.report_energy()
    api.log(f"Tot nb uptimes: {tot_uptimes}")
    api.log(f"Tot msg sent: {tot_msg_sent}")
    api.log(f"Tot msg rcv: {tot_msg_rcv}")
    return
