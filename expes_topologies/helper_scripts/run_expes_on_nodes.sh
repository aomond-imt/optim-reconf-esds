#!/bin/bash

hosts=$(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]')
for host in $hosts; do
  echo "starting on host $host"
  tmux kill-session -t "$host"
  tmux new-session -d -s "$host" "ssh $host; so; python3 run_experiments.py"
done
