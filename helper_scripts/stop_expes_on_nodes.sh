#!/bin/bash

#set -e

## declare an array variable
declare -a hosts=($(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]'))

#declare -a hosts=(
#  "gros-21"
#  "gros-22"
#  "gros-23"
#  "gros-24"
#  "gros-25"
#)

# get length of an array
hosts_length=${#hosts[@]}

# use for loop to read all values and indexes
for (( i=0; i<${hosts_length}; i++ ));
do
  echo "killing tmux session on host ${hosts[$i]}"
  ssh ${hosts[$i]} "tmux kill-session -t $i"
  ssh ${hosts[$i]} "kill $(ps -aux | pgrep -f esds)"
done
