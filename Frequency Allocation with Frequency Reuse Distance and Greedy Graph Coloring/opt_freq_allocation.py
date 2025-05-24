import math
import random

# -----------------------------
# Frequency definitions and reuse distances
# -----------------------------
frequencies = {
    '3G': [700, 715, 730, 755, 780, 805, 830],
    '4G': [1800, 1815, 1850, 1870, 1900, 1930]
}
# Minimum separation (meters) for co-channel reuse by tech
distance_threshold = {
    '3G': 5000.0,
    '4G': 3000.0
}

class Node:
    def __init__(self, node_id, x, y, node_type):
        self.id = node_id
        self.x = x
        self.y = y
        self.node_type = node_type
        self.frequency = None
    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)
    def __repr__(self):
        return f"Node({self.id}, {self.node_type}, x={self.x:.1f}, y={self.y:.1f}, freq={self.frequency})"

# -----------------------------
# Build interference graph based only on technology & threshold
# -----------------------------
def build_interference_graph(nodes):
    graph = {node: [] for node in nodes}
    for i, n1 in enumerate(nodes):
        for n2 in nodes[i+1:]:
            if n1.node_type == n2.node_type:
                d = n1.distance_to(n2)
                if d < distance_threshold[n1.node_type]:
                    graph[n1].append(n2)
                    graph[n2].append(n1)
    return graph

# -----------------------------
# Greedy coloring + record candidate distances
# -----------------------------
def greedy_graph_coloring(nodes, graph):
    assignment_info = {}
    for node in nodes:
        used = {nbr.frequency for nbr in graph[node] if nbr.frequency is not None}
        candidates = [f for f in frequencies[node.node_type] if f not in used]
        candidate_min_d = {}
        for freq in candidates:
            co_nodes = [n for n in nodes if n.node_type == node.node_type and n.frequency == freq]
            if co_nodes:
                min_d = min(node.distance_to(n) for n in co_nodes)
            else:
                min_d = float('inf')
            candidate_min_d[freq] = min_d
        # choose frequency maximizing min_d
        if candidate_min_d:
            best_freq = max(candidate_min_d, key=lambda f: candidate_min_d[f])
            node.frequency = best_freq
        else:
            node.frequency = None
            best_freq = None
        assignment_info[node] = {
            'candidates': candidate_min_d,
            'assigned': best_freq
        }
    return assignment_info

# -----------------------------
# Simulation with explanations
# -----------------------------
if __name__ == '__main__':
    random.seed(42)
    nodes = []
    # Create 15 3G and 15 4G nodes randomly in 20km×20km area
    for i in range(15):
        x, y = random.uniform(0, 20000), random.uniform(0, 20000)
        nodes.append(Node(f'3G-{i+1}', x, y, '3G'))
    for i in range(15):
        x, y = random.uniform(0, 20000), random.uniform(0, 20000)
        nodes.append(Node(f'4G-{i+1}', x, y, '4G'))

    graph = build_interference_graph(nodes)
    assignment_info = greedy_graph_coloring(nodes, graph)

    # Print detailed results
    print("Frequency assignment with interference details:\n")
    for node in nodes:
        info = assignment_info[node]
        print(f"Node {node.id} ({node.node_type}): Assigned {info['assigned']} MHz")
        # Distances to all same-technology nodes
        print("  Distances to same-tech nodes:")
        for other in nodes:
            if other is not node and other.node_type == node.node_type:
                print(f"    {other.id}: {node.distance_to(other):.1f} m")
        # Distances to co-channel nodes
        print("  Distances to co-channel nodes:")
        co_channel = [n for n in nodes if n is not node and n.frequency == node.frequency]
        if co_channel:
            for other in co_channel:
                print(f"    {other.id}: {node.distance_to(other):.1f} m")
        else:
            print("    None")
        # Candidate frequency distances
        cands = info['candidates']
        print("  Candidate freq -> min dist to existing co-channel:")
        for f, d in cands.items():
            label = "(chosen)" if f == info['assigned'] else ""
            dist_str = f"{d:.1f} m" if d != float('inf') else "∞"
            print(f"    {f} MHz: {dist_str} {label}")
        # Explanation
        chosen = info['assigned']
        if chosen:
            max_d = cands[chosen]
            print(f"  Explanation: chose {chosen} MHz because its minimum co-channel distance {max_d if max_d!=float('inf') else '∞'} m is the largest among candidates, minimizing interference.\n")
        else:
            print("  Explanation: no available frequencies due to neighbor usage.\n")
