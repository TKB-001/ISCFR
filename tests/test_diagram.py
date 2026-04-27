import importlib
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import Main
import render


def _parse_svg(svg):
    return ET.fromstring(svg)


def _framework_geometry(svg):
    root = _parse_svg(svg)
    geometry = {}
    for elem in root.iter():
        if not elem.tag.endswith("circle"):
            continue
        name = elem.attrib.get("data-framework")
        if not name:
            continue
        geometry[name] = (
            float(elem.attrib["cx"]),
            float(elem.attrib["cy"]),
            float(elem.attrib["r"]),
        )
    return geometry


def _object_positions(svg):
    root = _parse_svg(svg)
    points = {}
    for elem in root.iter():
        if not elem.tag.endswith("text"):
            continue
        name = elem.attrib.get("data-object")
        if not name:
            continue
        points[name] = (
            float(elem.attrib["x"]),
            float(elem.attrib["y"]),
            elem.attrib.get("data-hosts", ""),
        )
    return points


def _relation_edges(svg):
    root = _parse_svg(svg)
    edges = []
    for elem in root.iter():
        if not elem.tag.endswith("line"):
            continue
        label = elem.attrib.get("data-relation")
        if not label:
            continue
        edges.append(
            (
                label,
                elem.attrib.get("data-source"),
                elem.attrib.get("data-target"),
            )
        )
    return edges


def _relation_segments(svg):
    root = _parse_svg(svg)
    segments = []
    for elem in root.iter():
        if not elem.tag.endswith("line"):
            continue
        label = elem.attrib.get("data-relation")
        if not label:
            continue
        segments.append(
            {
                "label": label,
                "source": elem.attrib.get("data-source"),
                "target": elem.attrib.get("data-target"),
                "x1": float(elem.attrib["x1"]),
                "y1": float(elem.attrib["y1"]),
                "x2": float(elem.attrib["x2"]),
                "y2": float(elem.attrib["y2"]),
            }
        )
    return segments


def _svg_size(svg):
    root = _parse_svg(svg)
    return float(root.attrib["width"]), float(root.attrib["height"])


def _text_attributes(svg, attr_name):
    root = _parse_svg(svg)
    attributes = {}
    for elem in root.iter():
        if not elem.tag.endswith("text"):
            continue
        key = elem.attrib.get(attr_name)
        if not key:
            continue
        attributes[key] = elem.attrib
    return attributes


def _circle_inside(inner, outer, tolerance=1e-6):
    ix, iy, ir = inner
    ox, oy, oradius = outer
    return math.hypot(ix - ox, iy - oy) + ir <= oradius + tolerance


def _point_inside(point, circle, tolerance=1e-6):
    px, py = point
    cx, cy, radius = circle
    return math.hypot(px - cx, py - cy) <= radius + tolerance


def _reload_examples():
    import examples

    return importlib.reload(examples)


def test_hom_set_frameworks_are_nested_recursively():
    examples = _reload_examples()
    svg = render.render_diagram(examples.EXAMPLE_TREES["Dhom"])
    frameworks = _framework_geometry(svg)

    assert {"x", "B", "s"} <= set(frameworks.keys())
    assert _circle_inside(frameworks["B"], frameworks["x"])
    assert _circle_inside(frameworks["s"], frameworks["B"])


def test_hom_set_relation_direction_changes_between_ahom_and_dhom():
    examples = _reload_examples()

    dhom_svg = render.render_diagram(examples.EXAMPLE_TREES["Dhom"])
    ahom_svg = render.render_diagram(examples.EXAMPLE_TREES["Ahom"])

    dhom_edges = set(_relation_edges(dhom_svg))
    ahom_edges = set(_relation_edges(ahom_svg))

    assert ("r", "D", "B") in dhom_edges
    assert ("r", "B", "A") in dhom_edges
    assert ("r", "A", "B") in ahom_edges
    assert ("r", "B", "D") in ahom_edges


def test_arrow_to_framework_lands_on_target_framework_not_nested_child():
    examples = _reload_examples()
    svg = render.render_diagram(examples.EXAMPLE_TREES["Dhom"])
    frameworks = _framework_geometry(svg)
    segments = _relation_segments(svg)

    target_segment = next(
        segment for segment in segments
        if segment["label"] == "r" and segment["source"] == "D" and segment["target"] == "B"
    )

    endpoint = (target_segment["x2"], target_segment["y2"])
    b_circle = frameworks["B"]
    s_circle = frameworks["s"]

    assert _point_inside(endpoint, b_circle, tolerance=1.5)
    assert not _point_inside(endpoint, s_circle, tolerance=1e-6)


def test_arrow_from_framework_starts_in_framework_body_not_nested_child():
    examples = _reload_examples()
    svg = render.render_diagram(examples.EXAMPLE_TREES["Ahom"])
    frameworks = _framework_geometry(svg)
    segments = _relation_segments(svg)

    source_segment = next(
        segment for segment in segments
        if segment["label"] == "r" and segment["source"] == "B" and segment["target"] == "D"
    )

    startpoint = (source_segment["x1"], source_segment["y1"])
    b_circle = frameworks["B"]
    s_circle = frameworks["s"]

    assert _point_inside(startpoint, b_circle, tolerance=1.5)
    assert not _point_inside(startpoint, s_circle, tolerance=1e-6)


def test_framework_relation_endpoints_avoid_nested_frameworks_across_examples():
    examples = _reload_examples()

    for tree in (
        examples.EXAMPLE_TREES["Dhom"],
        examples.EXAMPLE_TREES["Ahom"],
        examples.limits,
    ):
        svg = render.render_diagram(tree)
        frameworks = _framework_geometry(svg)
        segments = _relation_segments(svg)
        nested_frameworks = {
            framework_name: [
                other_name
                for other_name, other_circle in frameworks.items()
                if other_name != framework_name and _circle_inside(other_circle, framework_circle)
            ]
            for framework_name, framework_circle in frameworks.items()
        }

        for segment in segments:
            for endpoint_name, point in (
                (segment["source"], (segment["x1"], segment["y1"])),
                (segment["target"], (segment["x2"], segment["y2"])),
            ):
                if endpoint_name not in frameworks:
                    continue
                assert _point_inside(point, frameworks[endpoint_name], tolerance=1.5)
                assert not any(
                    _point_inside(point, frameworks[nested_name], tolerance=1e-6)
                    for nested_name in nested_frameworks[endpoint_name]
                )


def test_section_break_nodes_are_not_rendered_in_diagram():
    examples = _reload_examples()
    svg = render.render_diagram(examples.limits)

    assert "__section_break_framework__" not in svg
    assert "__section_break_assertion__" not in svg


def test_outer_framework_objects_stay_outside_nested_frameworks():
    examples = _reload_examples()
    svg = render.render_diagram(examples.EXAMPLE_TREES["Dhom"])
    frameworks = _framework_geometry(svg)
    objects = _object_positions(svg)

    d_x, d_y, hosts = objects["D"]
    assert hosts == "x"
    assert _point_inside((d_x, d_y), frameworks["x"])
    assert not _point_inside((d_x, d_y), frameworks["B"])
    assert not _point_inside((d_x, d_y), frameworks["s"])


def test_object_in_two_frameworks_is_drawn_once_in_overlap_region():
    f_contains_g = Main.add_framework(None, "F")
    st_fg = Main.add_assertibility(f_contains_g, "f_has_g")
    g_inside_f = Main.add_obj(st_fg, "G", name_as=Main.Framework)
    Main.set_assertibility_child(st_fg, g_inside_f)
    Main.set_framework_children(f_contains_g, [st_fg])

    f_contains_a = Main.add_framework(None, "F")
    st_fa = Main.add_assertibility(f_contains_a, "f_has_a")
    a_in_f = Main.add_obj(st_fa, "a")
    Main.set_assertibility_child(st_fa, a_in_f)
    Main.set_framework_children(f_contains_a, [st_fa])

    g_contains_a = Main.add_framework(None, "G")
    st_ga = Main.add_assertibility(g_contains_a, "g_has_a")
    a_in_g = Main.add_obj(st_ga, "a")
    Main.set_assertibility_child(st_ga, a_in_g)
    Main.set_framework_children(g_contains_a, [st_ga])

    svg = render.render_diagram(Main.tree)
    frameworks = _framework_geometry(svg)
    objects = _object_positions(svg)

    assert "a" in objects
    a_x, a_y, hosts = objects["a"]
    assert hosts == "F,G"
    assert _point_inside((a_x, a_y), frameworks["F"])
    assert _point_inside((a_x, a_y), frameworks["G"])


def test_framework_cycle_does_not_break_rendering():
    f = Main.add_framework(None, "F")
    st_f = Main.add_assertibility(f, "f_stmt")
    g_obj = Main.add_obj(st_f, "G", name_as=Main.Framework)
    Main.set_assertibility_child(st_f, g_obj)
    Main.set_framework_children(f, [st_f])

    g = Main.add_framework(None, "G")
    st_g = Main.add_assertibility(g, "g_stmt")
    f_obj = Main.add_obj(st_g, "F", name_as=Main.Framework)
    Main.set_assertibility_child(st_g, f_obj)
    Main.set_framework_children(g, [st_g])

    svg = render.render_diagram(Main.tree)
    frameworks = _framework_geometry(svg)

    assert {"F", "G"} <= set(frameworks.keys())


def test_relation_only_objects_are_still_rendered():
    host = Main.add_framework(None, "H")
    st = Main.add_assertibility(host, "h_stmt")
    rel = Main.add_relation(st, "r")
    left = Main.add_obj(rel, "L")
    right = Main.add_obj(rel, "R")
    Main.set_relation_children(rel, left, right)
    Main.set_assertibility_child(st, rel)
    Main.set_framework_children(host, [st])

    svg = render.render_diagram(Main.tree)
    objects = _object_positions(svg)
    edges = _relation_edges(svg)

    assert "L" in objects
    assert "R" in objects
    assert ("r", "L", "R") in edges


def test_unassertibility_is_rendered_as_side_note():
    host = Main.add_framework(None, "d")
    unasserted = Main.add_unassertibility(host, "j", name_as=Main.Framework)
    st = Main.add_assertibility(unasserted, "j_stmt")
    child = Main.add_obj(st, "k", name_as=Main.Framework)
    Main.set_assertibility_child(st, child)
    Main.set_unassertibility_child(unasserted, st)
    Main.set_framework_children(host, [unasserted])

    svg = render.render_diagram(Main.tree)
    root = _parse_svg(svg)
    note_hosts = []
    for elem in root.iter():
        if not elem.tag.endswith("text"):
            continue
        host_name = elem.attrib.get("data-unassert-note-host")
        if host_name:
            note_hosts.append(host_name)

    assert "d" in note_hosts
    assert "data-framework=\"k\"" not in svg


def test_newline_is_not_rendered_in_diagram():
    host = Main.add_framework(None, "H")
    st = Main.add_assertibility(host, "h_stmt")
    rel = Main.add_relation(st, "r")
    left = Main.add_obj(rel, "A")
    newline = Main.add_newline(rel)
    Main.set_relation_children(rel, left, newline)
    Main.set_assertibility_child(st, rel)
    Main.set_framework_children(host, [st])

    svg = render.render_diagram(Main.tree)
    edges = _relation_edges(svg)

    assert ("r", "A", None) not in edges
    assert all(label != "r" for label, _, _ in edges)
    assert ">A</text>" in svg


def test_dense_diagram_scales_larger_than_simple_diagram():
    simple_root = Main.add_framework(None, "Simple")
    simple_stmt = Main.add_assertibility(simple_root, "simple_stmt")
    simple_obj = Main.add_obj(simple_stmt, "x")
    Main.set_assertibility_child(simple_stmt, simple_obj)
    Main.set_framework_children(simple_root, [simple_stmt])
    simple_svg = render.render_diagram(Main.tree)
    simple_size = _svg_size(simple_svg)

    Main.tree.clear()
    Main.name_registry.clear()
    Main.auto_used_names.clear()

    root = Main.add_framework(None, "Dense")
    prev_parent_name = "Dense"
    for idx in range(7):
        frame = Main.add_framework(None, prev_parent_name)
        stmt_frame = Main.add_assertibility(frame, f"stmt_f_{idx}")
        child_name = f"F{idx}"
        child_obj = Main.add_obj(stmt_frame, child_name, name_as=Main.Framework)
        Main.set_assertibility_child(stmt_frame, child_obj)
        Main.set_framework_children(frame, [stmt_frame])
        prev_parent_name = child_name

    for idx in range(28):
        frame = Main.add_framework(None, "Dense")
        stmt = Main.add_assertibility(frame, f"stmt_o_{idx}")
        obj = Main.add_obj(stmt, f"o{idx}")
        Main.set_assertibility_child(stmt, obj)
        Main.set_framework_children(frame, [stmt])

    dense_svg = render.render_diagram(Main.tree)
    dense_size = _svg_size(dense_svg)
    assert dense_size[0] >= simple_size[0]
    assert dense_size[1] >= simple_size[1]


def test_small_nested_frameworks_scale_text_to_fit():
    examples = _reload_examples()
    svg = render.render_diagram(examples.limits)
    framework_labels = _text_attributes(svg, "data-framework-label")
    object_labels = _text_attributes(svg, "data-object")

    assert min(float(attrs["font-size"]) for attrs in framework_labels.values()) < 18.0
    assert min(float(attrs["font-size"]) for attrs in object_labels.values()) < 18.0


def test_render_diagram_writes_svg_to_disk():
    host = Main.add_framework(None, "x")
    st = Main.add_assertibility(host, "x_stmt")
    obj = Main.add_obj(st, "p")
    Main.set_assertibility_child(st, obj)
    Main.set_framework_children(host, [st])

    output_path = Path("tests") / "_diagram_output.svg"
    try:
        svg = render.visualise_diagram(Main.tree, output_path=output_path)
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == svg
        assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    finally:
        if output_path.exists():
            output_path.unlink()


def test_shared_objects_fall_back_inside_real_hosts_when_host_circles_do_not_overlap():
    examples = _reload_examples()
    svg = render.render_diagram(examples.right_adjoints[0])
    frameworks = _framework_geometry(svg)
    objects = _object_positions(svg)

    for object_name, (ox, oy, hosts) in objects.items():
        host_names = [host_name for host_name in hosts.split(",") if host_name]
        if not host_names:
            continue
        assert any(
            _point_inside((ox, oy), frameworks[host_name], tolerance=1.5)
            for host_name in host_names
            if host_name in frameworks
        ), object_name

    assert _point_inside(objects["f"][:2], frameworks["a"], tolerance=1.5)
    assert _point_inside(objects["N"][:2], frameworks["i"], tolerance=1.5)
