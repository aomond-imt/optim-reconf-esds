#!/bin/bash

hosts=$(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]')
for host in $hosts; do
  host_split=($(echo "$host" | tr "." " "))
  host_node=${host_split[0]}
  echo "starting on host $host_node"
  tmux kill-session -t "$host_node"
  tmux new-session -d -s "$host_node" "ssh $host_node 'cd ~/optim-reconf-esds; source venv/bin/activate; cd expes_topologies; export PYTHONPATH=$PYTHONPATH:$(pwd); python3 run_experiments.py; sleep infinity'"
done
