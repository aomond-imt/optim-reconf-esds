from esds.node import Node


def execute(api: Node):
    api.turn_on()
    api.sendt("eth0", f"zoeifj_{api.node_id}", 1, 0, timeout=1)
    c, d = api.receivet("eth0", timeout=1)
    c, d = api.receivet("eth0", timeout=1)
    c, d = api.receivet("eth0", timeout=1)
    c, d = api.receivet("eth0", timeout=1)
    c, d = api.receivet("eth0", timeout=1)
    c, d = api.receivet("eth0", timeout=1)
    while d is not None:
        api.log(d)
        c, d = api.receivet("eth0", timeout=1)
    api.turn_off()
