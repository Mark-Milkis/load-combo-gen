from bigtree import Node, find_name, find_names, find_attrs, shift_nodes, preorder_iter, levelorder_iter

# Each resulting load combination shall be a dictionary with the following structure:
# {
#     "name": str,
#     "load_cases": dict: {case_name: load_factor}
# }
# A new load combination will be created each time the load groups branch off into sub-groups.
# For example, if the Dead Load group has one sub-group and the Live Load group has three sub-groups,
# then three load combinations will be created for LRFD2. The name of each combination will be the name of the
# base load combination, "LRFD2", followed by the name of the sub-group. The load factors will be inherited from the parent group
# if they are not explicitly defined in the load_factors dictionary.


# Iterate through the load_groups dictionary and determine the parent/child relationships between load groups.
# Leaf nodes are load cases while parent nodes are load groups. Create classes to represent these relationships.
# the classes should have attributes for the name of the group, the parent group, and the children groups. As well as an attribute for the load factor for each load combination.
# The class should have a method for retrieving the dictionary of load combinations and load factors. In case a load factor is not explicitly defined, it should inherit the load factor from the parent group.
# The class should contain a boolean type attribute which dictates if the children nodes should be additive or exclusive in load combinations.

def get_promoted_path(self, levels = 1, separator = "/"):
    
    # Get promoted path by breaking up the node path into a list and removing the pre-last n item

    #Check that the levels is positive and less than the depth of the node
    if levels < 0 or levels >= self.depth:
        raise ValueError("Levels must be positive and less than the depth of the node")

    path = self.path_name.split(separator)
    path = path[:-levels-1]
    path.append(self.name)
    promoted_path = separator.join(path)
    return promoted_path

Node.get_promoted_path = get_promoted_path

class LoadItem(Node):
    def __init__(self, name, additive=None):
        super().__init__(name)
        if additive is not None:
            self.set_attrs({"additive": additive})

    def set_load_factor(self, load_factor):

        if self.check_root_is_combination_set():
            self.set_attrs({"load_factor": load_factor})
        else:
            raise ValueError("Cannot set load factor if not part of LoadCombinationSet")
        
    def get_load_factor(self):
        load_factor = self.get_attr("load_factor")
        if load_factor is not None:
            return load_factor
        elif self.parent is not None and isinstance(self.parent, LoadItem):
            return self.parent.get_load_factor()
        else:
            return None
        
    def check_root_is_combination_set(self):
        """
        Check if the root is an instance of LoadCombinationSet.

        Returns:
            bool: True if the root is an instance of LoadCombinationSet, False otherwise.
        """
        if isinstance(self.root, LoadCombinationSet):
            return True
        else:
            return False

    def check_chid_load_factors(self):
        # Check if any of the children have load factors defined
        for child in self.children:
            if isinstance(child, LoadItem):
                if child.get_load_factor() is not None:
                    return True
        return False

    def is_additive(self):
        return self.get_attr("additive")

    @classmethod
    def create_tree(cls, load_groups):
        load_group_hierarchy = cls("Root")
        for group_name, group_data in load_groups.items():
            if isinstance(group_data, dict):
                group = cls(group_name, additive=False)
                load_group_hierarchy.append(group)
                for subgroup_name, subgroup_data in group_data.items():
                    subgroup_extended_name = f"{group_name}_{subgroup_name}"
                    subgroup = cls(subgroup_extended_name, additive=True)
                    group.append(subgroup)
                    for item_name in subgroup_data:
                        item = cls(item_name)
                        subgroup.append(item)
            else:
                group = cls(group_name, additive=True)
                load_group_hierarchy.append(group)
                for item_name in group_data:
                    item = cls(item_name)
                    group.append(item)

        # Go through the hierarchy and determine child/parent relationships by checking if the
        # name of the group matches the name of a leaf item
        for group in load_group_hierarchy.children:
            matching_nodes = find_names(load_group_hierarchy, group.name)
            for node in matching_nodes:
                if node.is_leaf:
                    shift_nodes(
                        load_group_hierarchy,
                        [group.path_name],
                        [node.path_name],
                        overriding=True,
                    )
        return load_group_hierarchy


class LoadCombinationSet(Node):
    def __init__(self, name):
        super().__init__(name)

    @classmethod
    def create_tree(cls, load_group_tree, load_factors, clean_tree=True):
        """
        Create a new tree structure that contains the load combinations and load factors.

        Args:
            cls (class): The class used to create the load combination tree.
            load_group_tree (Tree): The original load group tree.
            load_factors (dict): A dictionary containing the load factors for each load combination.
            clean_tree (bool, optional): Flag indicating whether to clean the tree after assigning load factors.
                Defaults to True.

        Returns:
            dict: A dictionary containing the load combination sets, where the keys are the load combination names
            and the values are the corresponding load combination trees.
        """
        load_combination_sets = {}

        for load_combination_name, load_combination_data in load_factors.items():
            load_combination_tree = cls(load_combination_name)

            # clone the load_group_tree into the load_combination_tree under the load_combination node
            load_combination_tree.extend(load_group_tree.copy())

            for group_name, group_data in load_combination_data.items():
                if isinstance(group_data, dict):
                    for subgroup_name, subgroup_data in group_data.items():
                        subgroup_extended_name = f"{group_name}_{subgroup_name}"
                        subgroup: LoadItem = find_name(
                            load_combination_tree, subgroup_extended_name
                        )
                        subgroup.set_load_factor(subgroup_data)
                else:
                    group: LoadItem = find_name(load_combination_tree, group_name)
                    group.set_load_factor(group_data)

            if clean_tree:
                load_combination_tree.clean_tree()

            load_combination_sets[load_combination_name] = load_combination_tree
        return load_combination_sets

    def clean_tree(self):
        """
        Removes all nodes that do not have a load factor assigned.

        This method iterates over the tree in a preorder traversal and removes any nodes that are instances of `LoadItem`
        and do not have a child load factor assigned and do not have a load factor assigned themselves.

        Args:
            None

        Returns:
            None
        """
        for node in preorder_iter(self):
            if isinstance(node, LoadItem):
                if (
                    node.check_chid_load_factors() is False
                    and node.get_load_factor() is None
                ):
                    shift_nodes(self, [node.path_name], [None], delete_children=True)

    def expand_nonadditive_nodes(self):
        """
        Expand non-additive nodes into separate load combinations.

        This method iterates over the tree in a levelorder_iter traversal and expands any non-additive nodes into separate
        load combinations. The method creates a new load combination for each child of the non-additive node and
        replaces the non-additive node with the child in the new load combination.
        """
        #TODO: Fix the issue with nested branching nodes
        if find_attrs(self, "additive", False) == ():
            self.show(attr_list=["additive", "load_factor"])
            # return self

        for node in levelorder_iter(self):
            if isinstance(node, LoadItem):
                if node.get_attr("additive") is False and len(node.children) > 1:
                    for child in node.children:
                        # Create a copy of the current tree for each child of the non-additive node
                        copy = self.copy()
                        # Get the path of the promoted child node
                        new_child_path = child.get_promoted_path(levels=1)
                        #Promote the child node to the parent level and remove the 
                        shift_nodes(copy, [child.path_name, node.path_name], [new_child_path, None])
                        # Rename the root node of the copy by appending the selected child node name
                        copy.root.name = f"{self.name}-{child.name}"
                        # Recursively expand non-additive nodes in the copy
                        copy.expand_nonadditive_nodes()
     
        

if __name__ == "__main__":
    # Load groups are a collections of load cases or other load groups organized by sub-groups
    # Load factors can be assigned to the entire load group or to individual sub-groups
    # Each sub-group is considered exclusive
    # Load items within the sub-group are considered additive
    # Load items can be load cases or other load groups

    # The following example defines two load groups: Dead and Live
    # The Dead group only has DL and SDL load cases which should be applied simultaneously with the same load factor
    # The Live group has three sub-groups: Perm, Construction, and Pattern
    # These should be applied one at a time with their respective load factors
    # All items in lists should be applied simultaneously with the same load factor
    # while items in dictionaries should be applied one at a time with their respective load factors

    # The load factors are defined in a dictionary where the key is the load combination name
    # Each load combination contains a dictionary of load factors
    # The load factors can be assigned to the entire load group or to individual sub-groups by passing another dictionary

    load_groups = {
        # Create a load group for all dead loads
        "Dead": ["DL", "SDL"],
        "Live": {
            "Perm": ["LL"],
            "Construction": ["LL_Construction"],
            "Pattern": ["LL_Pattern"],
        },
        "Wind": {
            "North": ["WL_Frame_North", "WL_Cladding_North"],
            "West": ["WL_Frame_West", "WL_Cladding_West"],
        },
        "Seismic": {"North": ["EQ_North"], "West": ["EQ_West"]},
        "Lateral": {
            "Wind": ["Wind"],  # References the Wind load group
            "Seismic": ["Seismic"],  # References the Seismic load group
        },
    }

    load_factors = {
        "LRFD1": {"Dead": 1.4},
        "LRFD2": {
            "Dead": 1.2,
            "Live": {"Perm": 1.6, "Construction": 1.0, "Pattern": 1.6},
        },
        "LRFD4": {
            "Dead": 1.2,
            "Live": {"Perm": 1.0, "Pattern": 1.0},
            "Wind": 1.0,
        },
        "Lateral-Envelope": {"Lateral": {"Wind": 1.0, "Seismic": 1.0}},
    }

    load_group_tree = LoadItem.create_tree(load_groups)

    load_combination_sets = LoadCombinationSet.create_tree(
        load_group_tree, load_factors, clean_tree=True
    )

    for load_combination_name, load_combination_tree in load_combination_sets.items():
        # print(f"Load Combination: {load_combination_name}")
        # load_combination_tree.show(attr_list=["additive", "load_factor"])
        load_combination_tree.expand_nonadditive_nodes()
