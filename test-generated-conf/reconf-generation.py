import esds

import numpy as np

n = 5

bwdth = 8  # bps
B = np.array([[bwdth, bwdth, 0, 0, bwdth], [bwdth, bwdth, bwdth, 0, 0], [0, bwdth, bwdth, bwdth, 0], [0, 0, bwdth, bwdth, bwdth], [bwdth, 0, 0, bwdth, bwdth]])
L = np.full((n,n), 0)

s = esds.Simulator({"eth0": {"bandwidth": B, "latency": L, "is_wired": False}})

args = {
    "arg1": [1,2,3],
    "arg2": [[(2,3), (5,3)], [3,2]]
}
s.create_node("test-node", interfaces=["eth0"], args=args)
s.create_node("test-node", interfaces=["eth0"], args=args)
s.create_node("test-node", interfaces=["eth0"], args=args)
s.create_node("test-node", interfaces=["eth0"], args=args)
s.create_node("test-node", interfaces=["eth0"], args=args)
s.run(interferences=False)
