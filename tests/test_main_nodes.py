import pytest

import Main


def test_obj_requires_assert_parent():
    root = Main.Framework(None, "Root")
    with pytest.raises(ValueError):
        Main.Obj(None, "orphan")
    with pytest.raises(ValueError):
        Main.Obj(root, "bad_parent")

    assert_parent = Main.Assertibility(root, "A")
    obj = Main.Obj(assert_parent, "valid")
    assert obj.parent is assert_parent

def test_newline_requires_assert_or_relation_parent():
    root = Main.Framework(None, "Root")
    with pytest.raises(ValueError):
        Main.Newline(None)
    with pytest.raises(ValueError):
        Main.Newline(root)

    assert_parent = Main.Assertibility(root, "A")
    newline = Main.Newline(assert_parent)
    assert newline.parent is assert_parent


def test_relation_parent_rules():
    root = Main.Framework(None, "Root")
    with pytest.raises(ValueError):
        Main.Relation(None, "rel")
    with pytest.raises(ValueError):
        Main.Relation(root, "rel")

    assert_parent = Main.Assertibility(root, "A")
    rel = Main.Relation(assert_parent, "rel")
    nested = Main.Relation(rel, "nested")
    assert rel.parent is assert_parent
    assert nested.parent is rel


def test_set_relation_children_sets_parents():
    root = Main.Framework(None, "Root")
    assert_parent = Main.Assertibility(root, "A")
    rel = Main.Relation(assert_parent, "rel")
    left = Main.Obj(assert_parent, "L")
    right = Main.Obj(assert_parent, "R")

    Main.set_relation_children(rel, left, right)
    assert rel.left is left
    assert rel.right is right
    assert left.parent is rel
    assert right.parent is rel


def test_set_relation_children_requires_both():
    root = Main.Framework(None, "Root")
    assert_parent = Main.Assertibility(root, "A")
    rel = Main.Relation(assert_parent, "rel")
    left = Main.Obj(assert_parent, "L")
    with pytest.raises(ValueError):
        Main.set_relation_children(rel, left, None)


def test_set_assertibility_child_sets_parent():
    root = Main.Framework(None, "Root")
    assert_parent = Main.Assertibility(root, "A")
    rel = Main.Relation(assert_parent, "rel")

    Main.set_assertibility_child(assert_parent, rel)
    assert assert_parent.child is rel
    assert rel.parent is assert_parent


def test_set_assertibility_child_requires_child():
    root = Main.Framework(None, "Root")
    assert_parent = Main.Assertibility(root, "A")
    with pytest.raises(ValueError):
        Main.set_assertibility_child(assert_parent, None)


def test_unassertibility_requires_framework_or_relation_parent():
    root = Main.Framework(None, "Root")
    with pytest.raises(ValueError):
        Main.Unassertibility(None, "U")

    assert_parent = Main.Assertibility(root, "A")
    unassert = Main.Unassertibility(assert_parent, "U")
    assert unassert.parent is assert_parent


def test_set_unassertibility_child_requires_assertibility_child():
    root = Main.Framework(None, "Root")
    unassert = Main.Unassertibility(root, "U")
    valid = Main.Assertibility(unassert, "A")
    Main.set_unassertibility_child(unassert, valid)
    assert unassert.child is valid
    assert valid.parent is unassert

    with pytest.raises(TypeError):
        Main.set_unassertibility_child(unassert, Main.Obj(valid, "x"))


def test_set_framework_children_requires_assertibility():
    root = Main.Framework(None, "Root")
    framework = Main.Framework(root, "F")
    bad_child = Main.Relation(Main.Assertibility(framework, "A"), "rel")
    with pytest.raises(TypeError):
        Main.set_framework_children(framework, [bad_child])


def test_set_framework_children_copies_list_and_sets_parents():
    root = Main.Framework(None, "Root")
    framework = Main.Framework(root, "F")
    child = Main.Assertibility(framework, "A")
    children = [child]

    Main.set_framework_children(framework, children)
    assert framework.children == children
    assert framework.children is not children
    assert child.parent is framework


def test_set_framework_children_accepts_unassertibility():
    root = Main.Framework(None, "Root")
    framework = Main.Framework(root, "F")
    child = Main.Unassertibility(framework, "U")

    Main.set_framework_children(framework, [child])
    assert framework.children == [child]
    assert child.parent is framework


def test_set_framework_children_requires_non_empty():
    root = Main.Framework(None, "Root")
    framework = Main.Framework(root, "F")
    with pytest.raises(ValueError):
        Main.set_framework_children(framework, [])


def test_add_framework_child_appends_after_init():
    root = Main.Framework(None, "Root")
    framework = Main.Framework(root, "F")
    child1 = Main.Assertibility(framework, "A1")
    Main.set_framework_children(framework, [child1])

    child2 = Main.Assertibility(framework, "A2")
    Main.add_framework_child(framework, child2)
    assert framework.children == [child1, child2]


def test_add_framework_child_requires_children_list():
    root = Main.Framework(None, "Root")
    framework = Main.Framework(root, "F")
    child = Main.Assertibility(framework, "A")
    with pytest.raises(AttributeError):
        Main.add_framework_child(framework, child)


def test_add_helpers_register_in_tree():
    root = Main.Framework(None, "Root")
    framework = Main.add_framework(root, "F")
    assertion = Main.add_assertibility(framework, "A")
    relation = Main.add_relation(assertion, "rel")
    obj = Main.add_obj(assertion, "obj")
    newline = Main.add_newline(assertion)

    assert framework in Main.tree
    assert assertion in Main.tree
    assert relation in Main.tree
    assert obj in Main.tree
    assert newline in Main.tree
    assert len(Main.tree) == 5
