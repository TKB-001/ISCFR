import importlib

import Main
import render


def _reload_examples():
    import examples

    return importlib.reload(examples)


def test_render_dhom_output():
    examples = _reload_examples()
    expected = "\n".join(
        [
            "\u0393_x(B)",
            "\u0393_x(D)",
            "\u0393_B(s)",
            "\u0393_B(A#D)",
            "\u0393_s(A)",
        ]
    )
    assert render.render(examples.EXAMPLE_TREES["Dhom"]) == expected


def test_render_ahom_output():
    examples = _reload_examples()
    expected = "\n".join(
        [
            "\u0393_x(B)",
            "\u0393_x(D)",
            "\u0393_B(s)",
            "\u0393_B(D#A)",
            "\u0393_s(A)",
        ]
    )
    assert render.render(examples.EXAMPLE_TREES["Ahom"]) == expected


def test_render_cone_output():
    examples = _reload_examples()
    rendered = render.render(examples.EXAMPLE_TREES["Cone"])
    lines = rendered.splitlines()
    assert len(lines) == 7
    assert "\u0393_d(N)" in lines
    assert "\u22a2_h(\u0393_j(x))" in lines
    assert "\u22a2_i(\u0393_j(x))" in lines
    assert "\u22a2_d(\u0393_j(x))" in lines
    assert "\u0393_d(j)" in lines
    assert "\u0393_i(N)" in lines
    assert "\u0393_h(\u0393_i(N)#\u0393_d(j))" in lines


def test_render_complex_nested_relations_uses_all_relation_children_objects():
    framework = Main.add_framework(None, "F")
    statement = Main.add_assertibility(framework, "stmt")

    outer = Main.add_relation(statement, "r0")
    left = Main.add_relation(outer, "r1")
    right = Main.add_relation(outer, "r2")
    inner = Main.add_relation(left, "r3")

    a = Main.add_obj(left, "A")
    b = Main.add_obj(inner, "B")
    c = Main.add_obj(inner, "C")
    d = Main.add_obj(right, "D")
    e = Main.add_obj(right, "E")

    Main.set_relation_children(inner, b, c)
    Main.set_relation_children(left, a, inner)
    Main.set_relation_children(right, d, e)
    Main.set_relation_children(outer, left, right)
    Main.set_assertibility_child(statement, outer)
    Main.set_framework_children(framework, [statement])

    rendered = render.render(Main.tree)
    assert rendered == "\u0393_F((A#(B#C))#(D#E))"
    for name in ("A", "B", "C", "D", "E"):
        assert name in rendered


def test_render_newline_object_as_assertibility_child():
    framework = Main.add_framework(None, "F")
    statement = Main.add_assertibility(framework, "stmt")
    newline = Main.add_newline(statement)

    Main.set_assertibility_child(statement, newline)
    Main.set_framework_children(framework, [statement])

    rendered = render.render(Main.tree)
    assert rendered == ""


def test_render_newline_object_in_relation():
    framework = Main.add_framework(None, "F")
    statement = Main.add_assertibility(framework, "stmt")
    relation = Main.add_relation(statement, "r")
    left = Main.add_obj(relation, "A")
    newline = Main.add_newline(relation)

    Main.set_relation_children(relation, left, newline)
    Main.set_assertibility_child(statement, relation)
    Main.set_framework_children(framework, [statement])

    rendered = render.render(Main.tree)
    assert rendered == "\u0393_F(A#\n)"


def test_render_blank_line_between_framework_sections():
    f1 = Main.add_framework(None, "F1")
    s1 = Main.add_assertibility(f1, "s1")
    o1 = Main.add_obj(s1, "A")
    Main.set_assertibility_child(s1, o1)
    Main.set_framework_children(f1, [s1])

    sep = Main.add_framework(None, "SEP")
    sep_stmt = Main.add_assertibility(sep, "sep_stmt")
    sep_nl = Main.add_newline(sep_stmt)
    Main.set_assertibility_child(sep_stmt, sep_nl)
    Main.set_framework_children(sep, [sep_stmt])

    f2 = Main.add_framework(None, "F2")
    s2 = Main.add_assertibility(f2, "s2")
    o2 = Main.add_obj(s2, "B")
    Main.set_assertibility_child(s2, o2)
    Main.set_framework_children(f2, [s2])

    rendered = render.render(Main.tree)
    assert rendered == "\u0393_F1(A)\n\n\u0393_F2(B)"
