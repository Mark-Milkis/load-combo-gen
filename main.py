from bigtree import (
    Node,
    find_name,
    find_names,
    find_attrs,
    shift_nodes,
    preorder_iter,
)
import pandas as pd
import yaml

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


def get_promoted_path(self, levels=1, separator="/"):

    # Get promoted path by breaking up the node path into a list and removing the pre-last n item

    # Check that the levels is positive and less than the depth of the node
    if levels < 0 or levels >= self.depth:
        raise ValueError("Levels must be positive and less than the depth of the node")

    path = self.path_name.split(separator)
    path = path[: -levels - 1]
    path.append(self.name)
    promoted_path = separator.join(path)
    return promoted_path


# Add the get_promoted_path method to the existing Node class
Node.get_promoted_path = get_promoted_path


class LoadItem(Node):
    def __init__(self, name, additive=None):
        super().__init__(name)
        if additive is not None:
            self.set_attrs({"additive": additive})

    def set_load_factor(self, load_factor):
        """
        Sets the load factor for the LoadCombinationSet.

        Args:
            load_factor (float): The load factor to be set.

        Raises:
            ValueError: If the LoadCombinationSet is not initialized.

        """
        if self.check_root_is_combination_set():
            self.set_attrs({"load_factor": load_factor})
        else:
            raise ValueError("Cannot set load factor if not part of LoadCombinationSet")

    def get_load_factor(self):
            """
            Retrieves the load factor of the current LoadItem.

            If the load factor is explicitly set for the current LoadItem, it is returned.
            If the load factor is not set for the current LoadItem, but the parent LoadItem exists and is an instance of LoadItem class,
            the load factor is retrieved from the parent LoadItem recursively.
            If neither the current LoadItem nor its parent has a load factor set, None is returned.

            Returns:
                The load factor of the current LoadItem, or None if not set.
            """
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
        """
        Check if any of the children have load factors defined.

        Returns:
            bool: True if any child has load factors defined, False otherwise.
        """
        for child in self.children:
            if isinstance(child, LoadItem):
                if child.get_load_factor() is not None:
                    return True
        return False

    def is_additive(self):
        return self.get_attr("additive")

    @classmethod
    def create_tree(cls, load_groups):
        """
        Creates a tree hierarchy based on the provided load groups.

        Args:
            load_groups (dict): A dictionary containing the load groups.

        Returns:
            LoadItem: The root node of the created tree hierarchy.
        """
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
    def create_tree_sets(
        cls, load_group_tree, load_factors, clean_tree=True, expand_tree=False
    ):
        """
        Create a new tree structure that contains the load combinations and load factors.

        Args:
            cls (class): The class used to create the load combination tree.
            load_group_tree (Tree): The original load group tree.
            load_factors (dict): A dictionary containing the load factors for each load combination.
            clean_tree (bool, optional): Flag indicating whether to clean the tree after assigning load factors.
                Defaults to True.
            expand_tree (bool, optional): Flag indicating whether to expand the tree after assigning load factors.

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
                    if group is not None:
                        group.set_load_factor(group_data)

            if clean_tree:
                load_combination_tree.clean_tree()

            tree_dict = {load_combination_name: load_combination_tree}

            if expand_tree:
                tree_dict = load_combination_tree.expand_nonadditive_nodes()

            load_combination_sets.update(tree_dict)
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
        Recursively expands non-additive nodes in the tree.

        Returns:
            dict: A dictionary containing the load combination sets.
        """
        load_combination_sets = {}
        branching_nodes = find_attrs(self, "additive", False)
        if branching_nodes == ():
            load_combination_sets[self.root.name] = self
            self.root.set_attrs({"expanded": True})
        else:
            node = branching_nodes[0]
            if len(node.children) > 1:
                for child in node.children:
                    partially_expanded_tree = self.copy()
                    new_child_path = child.get_promoted_path(levels=1)
                    shift_nodes(
                        partially_expanded_tree,
                        [child.path_name, node.path_name],
                        [new_child_path, None],
                    )
                    partially_expanded_tree.root.name = f"{self.name}-{child.name}"
                    fully_expanded_tree = (
                        partially_expanded_tree.expand_nonadditive_nodes()
                    )
                    load_combination_sets.update(fully_expanded_tree)

        return load_combination_sets

    def to_dict(self):
        """
        Converts the tree to a dictionary representation.

        Raises:
            ValueError: If the tree has not been expanded.

        Returns:
            dict: A dictionary representation of the tree.
        """

        # Check if the tree has been expanded
        if self.get_attr("expanded") is None:
            raise ValueError("Tree must be expanded before converting to dictionary")

        load_case_dict = {}
        for load_case in self.leaves:
            load_case_dict[load_case.name] = load_case.get_load_factor()

        combination_dict = {"name": self.name, "load_cases": load_case_dict}
        return combination_dict

    def to_dataframe(self, df_exist=None):
        """
        Converts the load combination tree to a pandas DataFrame.

        Args:
            df_exist (pandas.DataFrame, optional): An existing DataFrame to concatenate the converted data to.

        Returns:
            pandas.DataFrame: The converted DataFrame.

        Raises:
            ValueError: If the tree has not been expanded before converting to a DataFrame.
        """

        # Check if the tree has been expanded
        if self.get_attr("expanded") is None:
            raise ValueError("Tree must be expanded before converting to dataframe")

        data = []
        for load_case in self.leaves:
            data.append(
                {
                    "Load Combination": self.name,
                    "Load Case": load_case.name,
                    "Load Factor": load_case.get_load_factor(),
                }
            )
        df = pd.DataFrame(data)

        if df_exist is not None:
            df = pd.concat([df_exist, df], ignore_index=True)

        return df

    @classmethod
    def set_to_csv(cls, load_combination_sets, file_path="load_combinations.csv"):
        """
        Convert the given load combination sets to a CSV file.

        Args:
            load_combination_sets (dict): A dictionary containing load combination names as keys and load combination trees as values.
            file_path (str, optional): The file path to save the CSV file. Defaults to "load_combinations.csv".
        """
        df = None
        for (
            load_combination_name,
            load_combination_tree,
        ) in load_combination_sets.items():
            df = load_combination_tree.to_dataframe(df)
        df.to_csv(file_path, index=False)


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

    # Load the load_groups from the YAML file
    load_groups_filepath = "load_groups.yml"
    with open(load_groups_filepath, "r") as file:
        load_groups = yaml.safe_load(file)

    # Load the load_factors from the YAML file
    load_factors_filepath = "load_factors.yml"
    with open(load_factors_filepath, "r") as file:
        load_factors = yaml.safe_load(file)

    print(
        f"Using load groups from {load_groups_filepath} and load factors from {load_factors_filepath}"
    )

    load_group_tree = LoadItem.create_tree(load_groups)

    load_combination_sets = LoadCombinationSet.create_tree_sets(
        load_group_tree, load_factors, clean_tree=True, expand_tree=True
    )

    # Show the number of combinations created
    print(f"Number of combinations created: {len(load_combination_sets)}")

    csv_file_path = "load_combinations.csv"
    LoadCombinationSet.set_to_csv(load_combination_sets, csv_file_path)
    print(f"Load combinations saved to {csv_file_path}")

    print("Done")
