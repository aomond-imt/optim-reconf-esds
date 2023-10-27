import json
import os

from esds.node import Node

import on_coordination_logic


def execute(api: Node):
    # Initialisation
    tasks_list = [
        ("use_install", 3.12, ["provide_install"]),  # Name, time, dependencies
    ]
    on_coordination_logic.execute_coordination_tasks(api, tasks_list)
