import time
from multiprocessing import shared_memory

from esds.node import Node


def execute(api: Node):
    api.turn_off()
    s = shared_memory.SharedMemory("shm_a", create=True, size=30)

    api.wait(5)
    s.buf[0] = 1
    while not all(s.buf[i] == 1 for i in range(3)):
        api.wait(1)

    s.close()
    s.unlink()
