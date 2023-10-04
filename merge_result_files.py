import json
import os
from pathlib import Path

import yaml

results_dir = "/tmp"
expe_name = "deploy-60s-direct"
results_dir_to_merge = f"{results_dir}/{expe_name}"
merged_results = {}
print("Merging files...")
for file_name in os.listdir(results_dir_to_merge):
    node_num = int(Path(file_name).stem)
    file_path = f"{results_dir_to_merge}/{file_name}"
    with open(file_path) as f:
        merged_results[node_num] = yaml.safe_load(f)
    os.remove(file_path)

os.rmdir(results_dir_to_merge)
target_file_name = f"./{expe_name}.yaml"
print(f"Dump results at {target_file_name}")
with open(target_file_name, "w") as f:
    yaml.safe_dump(merged_results, f)
