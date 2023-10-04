from multiprocessing import shared_memory

from esds.node import Node


def execute(api: Node):
    api.turn_off()
    s = shared_memory.SharedMemory("shm_a")
    if api.node_id == 1:
        api.wait(40)
        s.buf[1] = 1
    if api.node_id == 2:
        api.wait(20)
        s.buf[2] = 1

    while not all(s.buf[i] == 1 for i in range(3)):
        api.wait(1)
    s.close()

