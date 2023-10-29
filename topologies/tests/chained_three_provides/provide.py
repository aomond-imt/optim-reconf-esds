from esds.node import Node

import on_coordination_logic


def execute(api: Node):
    # Initialisation
    tasks_list = [
        ("provide_install", 23.5, []),  # Name, time, dependencies
        ("provide_config", 5.3, []),
        ("provide_run", 2.1, []),
    ]
    on_coordination_logic.execute_coordination_tasks(api, tasks_list)
