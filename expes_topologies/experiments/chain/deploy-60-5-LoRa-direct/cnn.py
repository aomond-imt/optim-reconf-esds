import json

from esds.node import Node

import on_coordination_logic


def execute(api: Node):
    # Initialisation
    tasks_list = [
        ("provide_install", 23.31, []),  # Name, time, dependencies
        ("provide_config", 4.36, []),
        ("provide_run", 2.12, []),
    ]
    on_coordination_logic.execute_coordination_tasks(api, tasks_list)
