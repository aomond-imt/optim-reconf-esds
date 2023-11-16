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


def star(nodes_count, bw):
    all_arrays = [np.array([bw]*nodes_count)]
    for dep_num in range(1, nodes_count):
        dep_t = [bw, *[0]*(nodes_count-1)]
        dep_t[dep_num] = bw
        all_arrays.append(np.array(dep_t))
    L = np.full((nodes_count, nodes_count), 0)
    B = np.asarray(all_arrays)
    return B, L


def deploy_tasks_list():
    return [
        [["t_sa", 1.03, []], [f"t_sc", 19.39, [f"t_di_{dep_num}" for dep_num in range(30)]], [f"t_sr", 10.51, [f"t_dr_{dep_num}" for dep_num in range(30)]]],
        *[[[f"t_di_{dep_num}", dep_times[0], []], [f"t_dr_{dep_num}", dep_times[1], []]] for dep_num, dep_times in enumerate(
            [(4.99, 16.69), (1.25, 1.52), (5.26, 2.29), (9.82, 2.41), (5.68, 1.40), (7.92, 3.8), (3.66, 2.8), (1.34, 9.21), (2.31, 1.46), (12.53, 12.82),
             (3.21, 1.81), (1.33, 2.62), (1.99, 3.88), (1.88, 22.04), (3.67, 7.29), (2.98, 1.09), (4.39, 3.01), (5.76, 8.07), (5.95, 2.97), (2.56, 1.99),
             (1.4, 4.37), (3.71, 2.1), (3.43, 3.86), (3.61, 5.8), (2.34, 4.46), (2.3, 3.93), (15.47, 3.52), (9.04, 6.97), (3.4, 1.05), (1.33, 3.0)]
        )]
    ]
