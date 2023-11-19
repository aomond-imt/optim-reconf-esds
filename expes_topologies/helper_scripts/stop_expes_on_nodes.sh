#!/bin/bash

hosts=$(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]')
for host in $hosts; do
  host_split=($(echo "$host" | tr ";" " "))
  host_node=${host_split}[0]
  echo "killing tmux session on host $host_node"
  tmux kill-session -t "$host_node"
  ssh "$host_node" "kill $(ps -aux | pgrep -f esds)"
done
