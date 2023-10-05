from multiprocessing import shared_memory

from esds.node import Node


def execute(api: Node):
    code, data = api.receive("eth0")
    api.log(data)

