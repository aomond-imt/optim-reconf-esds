import time
from multiprocessing import shared_memory

from esds.node import Node


def execute(api: Node):
    api.turn_on()
    api.send("eth0", "test1", 257, 0)
    api.send("eth0", "test2", 257, 0)
    api.send("eth0", "test3", 257, 0)
    api.turn_off()
