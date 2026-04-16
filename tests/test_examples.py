import importlib

import Main


def _reload_examples():
    import examples

    return importlib.reload(examples)


def test_examples_do_not_modify_global_tree():
    examples = _reload_examples()
    assert Main.tree == []
    assert isinstance(examples.EXAMPLE_TREES, dict)


def test_examples_are_distinct_and_populated():
    examples = _reload_examples()
    trees = examples.EXAMPLE_TREES

    assert set(trees.keys()) == {"Dhom", "Ahom", "Cone"}
    assert trees["Dhom"] is not trees["Ahom"]
    assert trees["Dhom"] is not trees["Cone"]
    assert trees["Ahom"] is not trees["Cone"]

    for name, tree in trees.items():
        assert len(tree) > 0, f"{name} is empty"
        for node in tree:
            if node.parent is None:
                assert isinstance(node, Main.Framework), f"{name} has a non-framework root node"

        framework_nodes = [
            node for node in tree
            if isinstance(node, Main.Framework) and not isinstance(node, (Main.Assertibility, Main.Unassertibility))
        ]
        assert framework_nodes, f"{name} has no framework nodes"


def test_examples_shortcuts_match_registry():
    examples = _reload_examples()
    assert examples.example_tree_1 == examples.EXAMPLE_TREES["Dhom"]
    assert examples.example_tree_2 == examples.EXAMPLE_TREES["Ahom"]
    assert examples.example_tree_3 == examples.EXAMPLE_TREES["Cone"]
