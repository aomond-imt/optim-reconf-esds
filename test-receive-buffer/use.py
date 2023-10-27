from multiprocessing import shared_memory

from esds.node import Node


def execute(api: Node):
    api.turn_on()
    api.wait(20)
    api.turn_off()
    api.turn_on()
    code, data = api.receivet("eth0", timeout=1)
    api.log(f"{code}: {data}")
    code, data = api.receivet("eth0", timeout=1)
    api.log(f"{code}: {data}")
    code, data = api.receivet("eth0", timeout=1)
    api.log(f"{code}: {data}")
    api.turn_off()
