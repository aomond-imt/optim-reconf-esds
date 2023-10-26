import json
import os

from esds.node import Node

import on_coordination_logic


def execute(api: Node):
    # Initialisation
    tasks_list = [
        ("provide_install", 15, []),  # Name, time, dependencies
    ]
    on_coordination_logic.execute_coordination_tasks(api, tasks_list)
