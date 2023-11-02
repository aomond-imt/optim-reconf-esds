import numpy as np


def clique(nodes_count, bw):
    B = np.full((nodes_count, nodes_count), bw)
    L = np.full((nodes_count, nodes_count), 0)
    return B, L


def chain_3(nodes_count, bw):
    B = np.array([
        [bw, bw, 0],
        [bw, bw, bw],
        [0, bw, bw],
    ])
    L = np.full((3, 3), 0)
    return B, L


def chain_5(nodes_count, bw):
    B = np.array([
        [bw, bw, 0, 0, 0],
        [bw, bw, bw, 0, 0],
        [0, bw, bw, bw, 0],
        [0, 0, bw, bw, bw],
        [0, 0, 0, bw, bw],
    ])
    L = np.full((5, 5), 0)
    return B, L


def ring_4(nodes_count, bw):
    B = np.array([
        [bw, bw, 0, bw],
        [bw, bw, bw, 0],
        [0, bw, bw, bw],
        [bw, 0, bw, bw],
    ])
    L = np.full((4, 4), 0)
    return B, L


def ring_6(nodes_count, bw):
    B = np.array([
        [bw, bw, 0, 0, 0, bw],
        [bw, bw, bw, 0, 0, 0],
        [0, bw, bw, bw, 0, 0],
        [0, 0, bw, bw, bw, 0],
        [0, 0, 0, bw, bw, bw],
        [bw, 0, 0, 0, bw, bw],
    ])
    L = np.full((6, 6), 0)
    return B, L
