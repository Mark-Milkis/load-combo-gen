from bigtree import Node, levelorder_iter, shift_nodes, copy_nodes_from_tree_to_tree, find_attr
root = Node("a")
b = Node("b", additive=False, parent=root)
c = Node("c", parent=b)
d = Node("d", parent=b)
e = Node("e", additive=False, parent=root)
f = Node("f", parent=e)
g = Node("g", parent=e)
h = Node("h", parent=e)
i = Node("i", parent=root)
root.show(attr_list=["additive"])

def get_permutations(self):


def get_permutations(tree):
#TODO: Fix double looping within the function

    result = []
    branching_nodes = 0
    for node in levelorder_iter(tree):
        if node.get_attr("additive")==False and len(node.children) > 1:
            # If a non-additive node is found, create a copy of the current tree for each child of the non-additive node
            # then replace the non-additive node with one of the children in each copy
            # Increase count of branching nodes by 1
            branching_nodes += 1
            for child in node.children:
                copy = tree.copy()

                new_child_path = child.path_name.replace(f"{node.name}/", "")
                shift_nodes(copy, [child.path_name, node.path_name], [new_child_path, None])
                copy.root.name = f"{tree.name}-{child.name}"
                result.append(get_permutations(copy))

    if branching_nodes == 0:
        # If no branching nodes are found, return the tree as is
        return tree

    return result

results = get_permutations(root)
for subtree in results:
    subtree.show()