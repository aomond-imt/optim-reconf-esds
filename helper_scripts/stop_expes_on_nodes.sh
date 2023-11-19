#!/bin/bash

hosts=$(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]')
for host in $hosts; do
  echo "killing tmux session on host $host"
  tmux kill-session -t "$host"
  ssh "$host" "kill $(ps -aux | pgrep -f esds)"
done
