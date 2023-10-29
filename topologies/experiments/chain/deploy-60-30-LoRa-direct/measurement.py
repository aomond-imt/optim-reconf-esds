import json

from esds.node import Node

import on_coordination_logic


def execute(api: Node):
    # Initialisation
    tasks_list = [
        ("use_install", 15.76, ["provide_install"]),  # Name, time, dependencies
        ("use_config", 5.21, ["provide_config"]),
        ("use_run", 5.82, ["provide_run"]),
    ]
    on_coordination_logic.execute_coordination_tasks(api, tasks_list)
