import os

import pandas as pd
import yaml

results_dir = f"{os.environ['HOME']}/results-reconfiguration-esds/topologies/paper"
esds_results = []
for expe_dir in os.listdir(results_dir):
    abs_expe_dir = f"{results_dir}/{expe_dir}"
    print(expe_dir)
    coord_name, net_tplgy, srv_tplgy, size, upt_duration = expe_dir.split("-")
    for id_run in os.listdir(abs_expe_dir):
        try:
            abs_id_run_dir = f"{abs_expe_dir}/{id_run}"
            with open(f"{abs_id_run_dir}/0.yaml") as f:
                res = yaml.safe_load(f)
            esds_results.append(
                (coord_name, net_tplgy, srv_tplgy, size, upt_duration, id_run, res)
            )
        except FileNotFoundError as e:
            continue

d = pd.DataFrame(
    esds_results,
    columns=("coord_name", "net_tplgy", "srv_tplgy", "size", "upt_duration", "id_run", "res")
)

print()
