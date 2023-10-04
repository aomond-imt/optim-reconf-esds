import yaml

with open("deploy-60s-direct.yaml") as f:
    standard = yaml.safe_load(f)
with open("deploy-60s-direct-termination_k.yaml") as f:
    termination_k = yaml.safe_load(f)

standard_res = {
    "node_cons": sum(res_node["node_cons"] for res_node in standard.values()),
    "comms_cons": sum(res_node["comms_cons"] for res_node in standard.values()),
    "time": max(res_node["time"] for res_node in standard.values())
}

termination_k_res = {
    "node_cons": sum(res_node["node_cons"] for res_node in termination_k.values()),
    "comms_cons": sum(res_node["comms_cons"] for res_node in termination_k.values()),
    "time": max(res_node["time"] for res_node in termination_k.values())
}

print(standard_res)
print(termination_k_res)
