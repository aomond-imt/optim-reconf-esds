import json

from esds.plugins.power_states import PowerStates, PowerStatesComms


def initialisation(api):
    with open("uptimes_schedules/uptimes-dao-60-sec.json") as f:
        uptimes_schedules = json.load(f)[api.node_id]
    interface_name = "eth0"
    datasize = api.args["datasize"]
    bandwidth = api.args["bandwidth"]
    freq_polling = api.args["freq_polling"]
    node_cons = PowerStates(api, 0)
    sending_cons = PowerStatesComms(api)
    comms_conso = api.args["commsConso"]
    sending_cons.set_power(interface_name, 0, comms_conso, comms_conso)
    idle_conso = api.args["idleConso"]
    tot_uptimes, tot_msg_sent, tot_msg_rcv = 0, 0, 0
    return uptimes_schedules, interface_name, datasize, bandwidth, freq_polling, node_cons, sending_cons, idle_conso, tot_uptimes, tot_msg_sent, tot_msg_rcv
