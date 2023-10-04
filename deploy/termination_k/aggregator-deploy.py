import os
from multiprocessing import shared_memory

from esds.node import Node

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

import simulation_functions

duration = 60


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

    nb_msrmt = 2
    remaining = [msrmt_id for msrmt_id in range(1, nb_msrmt + 1)]

    def c():
        return api.read("clock")

    api.turn_off()
    for uptime, d in uptimes_schedules:
        api.wait(uptime - c())
        api.turn_on()
        tot_uptimes += 1
        node_cons.set_power(idle_conso)
        end_uptime = uptime + d
        while len(remaining) > 0 and c() < end_uptime:
            for msrmt_id in remaining:
                if c() + datasize*3/bandwidth >= end_uptime:
                    break
                api.send(interface_name, api.node_id, datasize, msrmt_id)
                tot_msg_sent += 1
                # TODO: why need *2
                code, msrmt_id_res = api.receivet(interface_name, timeout=min(datasize*2/bandwidth, end_uptime - c()))
                tot_msg_rcv += 1
                if msrmt_id_res is not None:
                    api.log(f"Removing {msrmt_id_res}")
                    remaining.remove(msrmt_id_res)

            api.wait(min(freq_polling, end_uptime - c()))
        api.turn_off()
        node_cons.set_power(0)
        if len(remaining) == 0:
            break

    node_cons.report_energy()
    api.log(f"Tot nb uptimes: {tot_uptimes}")
    api.log(f"Tot msg sent: {tot_msg_sent}")
    api.log(f"Tot msg rcv: {tot_msg_rcv}")
    return
