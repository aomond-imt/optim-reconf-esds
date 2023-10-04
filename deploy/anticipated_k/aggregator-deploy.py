import os
from multiprocessing import shared_memory

from esds.node import Node

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

import simulation_functions

duration = 60


def coordination(api, remaining, bandwidth, c, datasize, end_uptime, freq_polling, interface_name, coord_name, tot_msg_rcv, tot_msg_sent):
    while len(remaining) > 0 and c() < end_uptime:
        # for msrmt_id in remaining:
        if c() + datasize * 3 / bandwidth >= end_uptime:
            break
        # api.send(interface_name, api.node_id, datasize, msrmt_id)
        api.send(interface_name, (api.node_id, coord_name), datasize, 1)
        tot_msg_sent += 1
        # TODO: why need *2
        code, data = api.receivet(interface_name, timeout=min(datasize * 2 / bandwidth, end_uptime - c()))
        tot_msg_rcv += 1
        if data is not None:
            msrmt_id_res, _ = data
            if msrmt_id_res is not None:
                api.log(f"Removing {msrmt_id_res}")
                remaining.remove(msrmt_id_res)
                if len(remaining) == 0:
                    api.log(f"{coord_name} clear")

        api.wait(min(freq_polling, end_uptime - c()))
    return tot_msg_rcv, tot_msg_sent


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

    remaining_install = [msrmt_id for msrmt_id in range(1, nb_msrmt + 1)]
    remaining_run = [msrmt_id for msrmt_id in range(1, nb_msrmt + 1)]
    s = shared_memory.SharedMemory("shm_cps", create=True, size=32)

    def c():
        return api.read("clock")

    actions_duration = {
        "install": 10,
        "run": 10
    }
    actions_done = {
        "install": False,
        "run": False
    }
    api.turn_off()
    for uptime, d in uptimes_schedules:
        api.wait(uptime - c())
        api.turn_on()
        tot_uptimes += 1
        node_cons.set_power(idle_conso)
        end_uptime = uptime + d
        tot_msg_rcv, tot_msg_sent = coordination(api, remaining_install, bandwidth, c, datasize, end_uptime, freq_polling, interface_name, "install", tot_msg_rcv, tot_msg_sent)
        execute_action(actions_done, actions_duration, api, node_cons, idle_conso, remaining_install, stress_conso, "install")
        tot_msg_rcv, tot_msg_sent = coordination(api, remaining_run, bandwidth, c, datasize, end_uptime, freq_polling, interface_name, "run", tot_msg_rcv, tot_msg_sent)
        execute_action(actions_done, actions_duration, api, node_cons, idle_conso, remaining_run, stress_conso, "run")
        api.turn_off()
        node_cons.set_power(0)
        if len(remaining_install) == 0 and len(remaining_run) == 0:
            s.buf[0] = 1
            break

    simulation_functions.report_metrics(api, c, comms_cons, node_cons, results_dir, "deploy-60s-direct", tot_msg_rcv, tot_msg_sent, tot_uptimes)
    s.close()
    s.unlink()


def execute_action(actions_done, actions_duration, api, node_cons, idle_conso, remaining, stress_conso, coord_name):
    if len(remaining) == 0 and not actions_done[coord_name]:
        api.log(f"Execute {coord_name}")
        node_cons.set_power(stress_conso)
        api.wait(actions_duration[coord_name])
        actions_done[coord_name] = True
        node_cons.set_power(idle_conso)
