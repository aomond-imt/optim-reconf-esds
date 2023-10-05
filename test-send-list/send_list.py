import time
from multiprocessing import shared_memory

from esds.node import Node
import random


def execute(api: Node):
    schedule = []
    for i in range(750):
        schedule.append(random.uniform(i*3600, (i+1)*3600))
    api.send("eth0", schedule, 3000, 1)
