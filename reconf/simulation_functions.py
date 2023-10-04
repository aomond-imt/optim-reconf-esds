import os
import json
import yaml
from esds.plugins.power_states import PowerStates, PowerStatesComms


def initialisation(api):
    with open(f"../uptimes_schedules/{api.args['uptimes_schedule_name']}") as f:
        uptimes_schedules = json.load(f)[api.node_id]
    interface_name = "eth0"
    datasize = api.args["datasize"]
    bandwidth = api.args["bandwidth"]
    freq_polling = api.args["freq_polling"]
    nb_msrmt = api.args["nb_msrmt"]
    node_cons = PowerStates(api, 0)
    comms_cons = PowerStatesComms(api)
    comms_conso = api.args["commsConso"]
    comms_cons.set_power(interface_name, 0, comms_conso, comms_conso)
    idle_conso = api.args["idleConso"]
    stress_conso = api.args["stressConso"]
    results_dir = api.args["results_dir"]
    tot_uptimes, tot_msg_sent, tot_msg_rcv = 0, 0, 0
    return uptimes_schedules, interface_name, datasize, bandwidth, freq_polling, node_cons, nb_msrmt, comms_cons, idle_conso, stress_conso, results_dir, tot_uptimes, tot_msg_sent, tot_msg_rcv


def report_metrics(api, c, comms_cons, node_cons, results_dir, name_dir_exec, tot_msg_rcv, tot_msg_sent, tot_uptimes):
    node_cons.set_power(0)
    node_cons.report_energy()
    comms_cons.report_energy()
    api.log(f"Tot nb uptimes: {tot_uptimes}")
    api.log(f"Tot msg sent: {tot_msg_sent}")
    api.log(f"Tot msg rcv: {tot_msg_rcv}")
    results_dir_exec = f"{results_dir}/{name_dir_exec}"
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
