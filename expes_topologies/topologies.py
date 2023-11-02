import numpy as np


def clique(nodes_count, bw):
    B = np.full((nodes_count, nodes_count), bw)
    L = np.full((nodes_count, nodes_count), 0)
    return B, L


def symmetricize(arr1D):
    ID = np.arange(arr1D.size)
    return arr1D[np.abs(ID - ID[:,None])]


def chain(nodes_count, bw):
    if nodes_count < 3:
        node_0 = np.array([bw]*nodes_count)
    else:
        node_0 = np.array([bw, bw] + [0]*(nodes_count-2))
    B = symmetricize(node_0)
    L = np.full((nodes_count, nodes_count), 0)
    return B, L


def ring(nodes_count, bw):
    if nodes_count < 4:
        node_0 = np.array([bw]*nodes_count)
    else:
        node_0 = np.array([bw, bw] + ([0]*(nodes_count-3)) + [bw])
    B = symmetricize(node_0)
    L = np.full((nodes_count, nodes_count), 0)
    return B, L
