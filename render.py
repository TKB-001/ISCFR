import sys
import math
from html import escape as _xml_escape
from collections import defaultdict

import Main
import examples

sys.stdout.reconfigure(encoding="utf-8")

_SECTION_BREAK_FRAMEWORK = "__section_break_framework__"
_SECTION_BREAK_ASSERTION = "__section_break_assertion__"

def check_naming_overlaps(tree):
    """Check for duplicate names in the tree and return overlaps."""
    name_count = defaultdict(list)

    def collect_names(node):
        if node is None:
            return

        if isinstance(node, Main.Obj):
            name_count[node.name].append(("Obj", node))
        elif isinstance(node, Main.Relation):
            name_count[node.name].append(("Relation", node))
            collect_names(node.left)
            collect_names(node.right)
        elif isinstance(node, Main.Assertibility):
            name_count[node.name].append(("Assertibility", node))
            collect_names(node.child)
        elif isinstance(node, Main.Unassertibility):
            name_count[node.name].append(("Unassertibility", node))
            collect_names(node.child)
        elif isinstance(node, Main.Framework):
            name_count[node.name].append(("Framework", node))
            for child in getattr(node, "children", []) or []:
                collect_names(child)

    for node in tree:
        collect_names(node)

    overlaps = {name: nodes for name, nodes in name_count.items() if len(nodes) > 1}
    ordered = {}
    for name in sorted(overlaps):
        ordered[name] = sorted(overlaps[name], key=lambda item: item[0])
    return ordered


def _is_section_break_name(name):
    return name in {_SECTION_BREAK_FRAMEWORK, _SECTION_BREAK_ASSERTION}


def _is_section_break_node(node):
    return _is_section_break_name(getattr(node, "name", None))

def _render_relation_arg(node):
    if node is None:
        raise ValueError("Relation nodes must have exactly two children.")
    if isinstance(node, Main.Newline):
        return "\n"
    if isinstance(node, Main.Obj):
        return str(node.name)
    if isinstance(node, Main.Assertibility):
        return _render_assertibility(node)
    if isinstance(node, Main.Unassertibility):
        return _render_unassertibility(node)
    if isinstance(node, Main.Framework):
        return str(node.name)
    if isinstance(node, Main.Relation):
        left = _render_relation_arg(node.left)
        right = _render_relation_arg(node.right)
        return f"({left}#{right})"
    raise TypeError(f"Unsupported node type: {type(node)}")

def _render_child(node):
    if isinstance(node, Main.Newline):
        return "\n"
    if isinstance(node, Main.Obj):
        return str(node.name)
    if isinstance(node, Main.Assertibility):
        return _render_assertibility(node)
    if isinstance(node, Main.Unassertibility):
        return _render_unassertibility(node)
    if isinstance(node, Main.Framework):
        return str(node.name)
    if isinstance(node, Main.Relation):
        left = _render_relation_arg(node.left)
        right = _render_relation_arg(node.right)
        return f"{left}#{right}"
    raise TypeError(f"Unsupported node type: {type(node)}")

def _render_assertibility(node):
    if node.child is None:
        raise ValueError("Assertibility nodes must have exactly one child.")
    if isinstance(node.child, Main.Newline):
        return ""
    parent_name = node.parent.name if node.parent is not None else ""
    return f"Γ_{parent_name}({_render_child(node.child)})"

def _render_unassertibility(node):
    if node.child is None:
        raise ValueError("Unassertibility nodes must have exactly one child.")
    if not isinstance(node.child, Main.Assertibility):
        raise TypeError("Unassertibility children must be Assertibility nodes.")
    parent_name = node.parent.name if node.parent is not None else ""
    return f"⊢_{parent_name}({_render_assertibility(node.child)})"

def _render_framework(node):
    parts = []
    for child in getattr(node, "children", []) or []:
        if isinstance(child, Main.Unassertibility):
            parts.append(_render_unassertibility(child))
        else:
            parts.append(_render_assertibility(child))
    return "".join(parts)

def _is_framework_class(cls):
    if not isinstance(cls, type):
        return False
    return (
        issubclass(cls, Main.Framework)
        and not issubclass(cls, (Main.Assertibility, Main.Unassertibility))
    )


def _is_framework_like_node(node):
    if isinstance(node, Main.Framework) and not isinstance(node, (Main.Assertibility, Main.Unassertibility)):
        return True
    if isinstance(node, Main.Obj):
        if _is_framework_class(getattr(node, "name_cls", None)):
            return True
        registry_cls = Main.name_registry.get(node.name)
        return _is_framework_class(registry_cls)
    return False


def _root_frameworks(tree):
    return [
        node
        for node in tree
        if isinstance(node, Main.Framework)
        and not isinstance(node, (Main.Assertibility, Main.Unassertibility))
        and node.parent is None
    ]


def _framework_statements(framework, tree):
    statements = list(getattr(framework, "children", []) or [])
    known_ids = {id(node) for node in statements}
    for node in tree:
        if isinstance(node, (Main.Assertibility, Main.Unassertibility)) and node.parent is framework:
            if id(node) not in known_ids:
                statements.append(node)
                known_ids.add(id(node))
    return statements


def _merge_style(existing, new_style):
    if existing == "asserted" or new_style == "asserted":
        return "asserted"
    return "unasserted"


class _DiagramGraph:
    def __init__(self):
        self.frameworks = set()
        self.framework_parent_candidates = defaultdict(set)
        self.framework_edge_style = {}
        self.object_hosts = defaultdict(set)
        self.object_host_style = {}
        self.object_relation_hosts = defaultdict(set)
        self.relation_edges = []
        self.unassertibility_notes = defaultdict(list)

    def add_framework(self, framework_name):
        self.frameworks.add(str(framework_name))

    def add_framework_membership(self, host_name, child_name, style):
        host_name = str(host_name)
        child_name = str(child_name)
        self.add_framework(host_name)
        self.add_framework(child_name)
        if host_name == child_name:
            return
        self.framework_parent_candidates[child_name].add(host_name)
        key = (host_name, child_name)
        self.framework_edge_style[key] = _merge_style(self.framework_edge_style.get(key), style)

    def add_object_membership(self, host_name, object_name, style):
        host_name = str(host_name)
        object_name = str(object_name)
        self.add_framework(host_name)
        self.object_hosts[object_name].add(host_name)
        key = (host_name, object_name)
        self.object_host_style[key] = _merge_style(self.object_host_style.get(key), style)

    def add_object_relation_reference(self, host_name, object_name):
        host_name = str(host_name)
        object_name = str(object_name)
        self.add_framework(host_name)
        self.object_relation_hosts[object_name].add(host_name)

    def add_relation_edge(self, host_name, label, source, target, style):
        self.relation_edges.append(
            {
                "host": str(host_name),
                "label": str(label),
                "source": source,
                "target": target,
                "style": style,
            }
        )

    def add_unassertibility_note(self, host_name, note):
        host_name = str(host_name)
        self.add_framework(host_name)
        normalized = str(note).replace("\n", "")
        if not normalized:
            return
        if normalized not in self.unassertibility_notes[host_name]:
            self.unassertibility_notes[host_name].append(normalized)


def _parse_relation_endpoint(node, host_name, graph, style):
    if node is None:
        return None
    name = getattr(node, 'name', None)

    if isinstance(node, Main.Newline) or _is_section_break_name(name):
        return None
    if isinstance(node, Main.Obj):
        if _is_framework_like_node(node):
            graph.add_framework(node.name)
            return {"kind": "framework", "name": str(node.name)}
        graph.add_object_relation_reference(host_name, node.name)
        return {"kind": "object", "name": str(node.name)}
    if isinstance(node, Main.Framework) and not isinstance(node, (Main.Assertibility, Main.Unassertibility)):
        graph.add_framework(node.name)
        return {"kind": "framework", "name": str(node.name)}
    if isinstance(node, Main.Assertibility):
        if node.child is None:
            raise ValueError("Assertibility nodes must have exactly one child.")
        return _parse_relation_endpoint(node.child, host_name, graph, style)
    if isinstance(node, Main.Unassertibility):
        if node.child is None:
            raise ValueError("Unassertibility nodes must have exactly one child.")
        if not isinstance(node.child, Main.Assertibility):
            raise TypeError("Unassertibility children must be Assertibility nodes.")
        if node.child.child is None:
            raise ValueError("Assertibility nodes must have exactly one child.")
        graph.add_unassertibility_note(host_name, _render_unassertibility(node))
        return None
    if isinstance(node, Main.Relation):
        if node.left is None or node.right is None:
            raise ValueError("Relation nodes must have exactly two children.")
        left = _parse_relation_endpoint(node.left, host_name, graph, style)
        right = _parse_relation_endpoint(node.right, host_name, graph, style)
        if left is not None and right is not None:
            graph.add_relation_edge(host_name, node.name, left, right, style)
            return right
        if left is not None:
            return left
        return right
    raise TypeError(f"Unsupported node type: {type(node)}")


def _parse_asserted_content(host_name, node, graph, style):
    if node is None:
        raise ValueError("Assertibility nodes must have exactly one child.")
    name = getattr(node, 'name', None)
    if isinstance(node, Main.Newline) or _is_section_break_name(name):
        return None
    if isinstance(node, Main.Obj):
        if _is_framework_like_node(node):
            graph.add_framework_membership(host_name, node.name, style)
        else:
            graph.add_object_membership(host_name, node.name, style)
        return
    if isinstance(node, Main.Framework) and not isinstance(node, (Main.Assertibility, Main.Unassertibility)):
        graph.add_framework_membership(host_name, node.name, style)
        return
    if isinstance(node, Main.Assertibility):
        if node.child is None:
            raise ValueError("Assertibility nodes must have exactly one child.")
        _parse_asserted_content(host_name, node.child, graph, style)
        return
    if isinstance(node, Main.Unassertibility):
        if node.child is None:
            raise ValueError("Unassertibility nodes must have exactly one child.")
        if not isinstance(node.child, Main.Assertibility):
            raise TypeError("Unassertibility children must be Assertibility nodes.")
        if node.child.child is None:
            raise ValueError("Assertibility nodes must have exactly one child.")
        graph.add_unassertibility_note(host_name, _render_unassertibility(node))
        return
    if isinstance(node, Main.Relation):
        if node.left is None or node.right is None:
            raise ValueError("Relation nodes must have exactly two children.")
        left = _parse_relation_endpoint(node.left, host_name, graph, style)
        right = _parse_relation_endpoint(node.right, host_name, graph, style)
        if left is not None and right is not None:
            graph.add_relation_edge(host_name, node.name, left, right, style)
        return
    raise TypeError(f"Unsupported node type: {type(node)}")


def _build_diagram_graph(tree):
    graph = _DiagramGraph()

    framework_nodes = [
        node
        for node in tree
        if isinstance(node, Main.Framework)
        and not isinstance(node, (Main.Assertibility, Main.Unassertibility))
        and not _is_section_break_node(node)
    ]

    for framework in framework_nodes:
        graph.add_framework(framework.name)

    for framework in framework_nodes:
        host_name = framework.name
        for statement in _framework_statements(framework, tree):
            if isinstance(statement, Main.Assertibility):
                if statement.child is None:
                    raise ValueError("Assertibility nodes must have exactly one child.")
                _parse_asserted_content(host_name, statement.child, graph, "asserted")
                continue
            if isinstance(statement, Main.Unassertibility):
                if statement.child is None:
                    raise ValueError("Unassertibility nodes must have exactly one child.")
                if not isinstance(statement.child, Main.Assertibility):
                    raise TypeError("Unassertibility children must be Assertibility nodes.")
                graph.add_unassertibility_note(host_name, _render_unassertibility(statement))
                continue
            raise TypeError("Framework children must be Assertibility or Unassertibility nodes.")

    return graph


def _build_primary_framework_tree(graph):
    children_by_parent = defaultdict(set)
    for child_name, parent_names in graph.framework_parent_candidates.items():
        for parent_name in parent_names:
            if parent_name != child_name:
                children_by_parent[parent_name].add(child_name)

    explicit_children = set(graph.framework_parent_candidates.keys())
    roots = sorted(graph.frameworks - explicit_children)
    if not roots and graph.frameworks:
        roots = [sorted(graph.frameworks)[0]]

    parent_of = {}
    visited = set(roots)
    queue = list(roots)
    while queue:
        parent = queue.pop(0)
        for child in sorted(children_by_parent.get(parent, ())):
            if child in visited:
                continue
            parent_of[child] = parent
            visited.add(child)
            queue.append(child)

    for framework_name in sorted(graph.frameworks):
        if framework_name in visited:
            continue
        candidate_parents = sorted(graph.framework_parent_candidates.get(framework_name, ()))
        chosen_parent = None
        for candidate in candidate_parents:
            if candidate in visited and candidate != framework_name:
                chosen_parent = candidate
                break
        if chosen_parent is None:
            roots.append(framework_name)
            visited.add(framework_name)
        else:
            parent_of[framework_name] = chosen_parent
            visited.add(framework_name)

    primary_children = defaultdict(list)
    for child_name, parent_name in parent_of.items():
        primary_children[parent_name].append(child_name)
    for parent_name in primary_children:
        primary_children[parent_name].sort()

    return roots, parent_of, primary_children


def _framework_tree_depth(root_name, children_by_parent):
    children = children_by_parent.get(root_name, [])
    if not children:
        return 1
    return 1 + max(_framework_tree_depth(child_name, children_by_parent) for child_name in children)


def _children_share_objects(child_frameworks, object_hosts):
    child_set = set(child_frameworks)
    for host_names in object_hosts.values():
        if len(child_set.intersection(host_names)) >= 2:
            return True
    return False


def _layout_framework_recursive(framework_name, cx, cy, radius, children_by_parent, graph, positions):
    positions[framework_name] = (cx, cy, radius)
    children = children_by_parent.get(framework_name, [])
    if not children:
        return

    count = len(children)
    if count == 1:
        child_name = children[0]
        child_radius = max(30.0, min(radius * 0.78, radius - 18.0))
        _layout_framework_recursive(
            child_name,
            cx,
            cy + radius * 0.10,
            child_radius,
            children_by_parent,
            graph,
            positions,
        )
        return

    shared = _children_share_objects(children, graph.object_hosts)
    if shared:
        child_radius = max(28.0, min(radius * 0.58, radius - 20.0))
        orbit = max(14.0, radius - child_radius - 12.0) * 0.72
    else:
        child_radius = max(26.0, min(radius * (0.86 / (1.0 + math.sqrt(count))), radius - 20.0))
        orbit = max(14.0, radius - child_radius - 12.0)

    for idx, child_name in enumerate(children):
        angle = (-math.pi / 2.0) + (2.0 * math.pi * idx / count)
        child_cx = cx + orbit * math.cos(angle)
        child_cy = cy + orbit * math.sin(angle)
        _layout_framework_recursive(
            child_name,
            child_cx,
            child_cy,
            child_radius,
            children_by_parent,
            graph,
            positions,
        )


def _layout_framework_positions(graph, roots, children_by_parent):
    if not roots:
        return {}

    max_depth = max(_framework_tree_depth(root_name, children_by_parent) for root_name in roots)
    host_object_counts = defaultdict(int)
    for object_name, host_names in graph.object_hosts.items():
        for host_name in host_names:
            host_object_counts[host_name] += 1
    for object_name, host_names in graph.object_relation_hosts.items():
        if object_name in graph.object_hosts:
            continue
        for host_name in host_names:
            host_object_counts[host_name] += 1
    max_objects = max(host_object_counts.values(), default=0)
    max_child_count = max((len(children_by_parent.get(name, [])) for name in graph.frameworks), default=0)
    max_note_count = max((len(notes) for notes in graph.unassertibility_notes.values()), default=0)

    root_radius = max(
        140.0,
        76.0 + (max_depth * 34.0) + (max_objects * 10.0) + (max_child_count * 7.0) + (max_note_count * 6.0),
    )
    root_diameter = root_radius * 2.0
    horizontal_gap = max(100.0, root_radius * 0.60)
    vertical_gap = max(90.0, root_radius * 0.50)
    margin = 30.0
    max_cols = 3
    cols = min(max_cols, len(roots))
    rows = (len(roots) + cols - 1) // cols

    positions = {}
    for idx, root_name in enumerate(roots):
        row = idx // cols
        col = idx % cols
        cx = margin + root_radius + col * (root_diameter + horizontal_gap)
        cy = margin + root_radius + row * (root_diameter + vertical_gap)
        _layout_framework_recursive(root_name, cx, cy, root_radius, children_by_parent, graph, positions)

    width = int(margin * 2 + cols * root_diameter + (cols - 1) * horizontal_gap)
    height = int(margin * 2 + rows * root_diameter + (rows - 1) * vertical_gap)
    return {"positions": positions, "width": width, "height": height}


def _shared_object_position(host_names, framework_positions):
    host_circles = [framework_positions[name] for name in host_names if name in framework_positions]
    if not host_circles:
        return None
    if len(host_circles) == 1:
        cx, cy, _ = host_circles[0]
        return (cx, cy)
    if len(host_circles) == 2:
        (x1, y1, r1), (x2, y2, r2) = host_circles
        dx = x2 - x1
        dy = y2 - y1
        distance = math.hypot(dx, dy)
        if distance < 1e-6:
            return (x1, y1)
        if distance + min(r1, r2) <= max(r1, r2):
            return (x1, y1) if r1 <= r2 else (x2, y2)
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    avg_x = sum(circle[0] for circle in host_circles) / len(host_circles)
    avg_y = sum(circle[1] for circle in host_circles) / len(host_circles)
    return (avg_x, avg_y)


def _circle_padding_for_label(radius):
    return max(11.0, min(24.0, radius * 0.65))


def _text_font_size_for_radius(radius, *, minimum=10.0, maximum=18.0):
    return max(minimum, min(maximum, radius * 0.42))


def _point_within_circle(point, circle, clearance=0.0):
    px, py = point
    cx, cy, radius = circle
    return math.hypot(px - cx, py - cy) <= max(0.0, radius - clearance)


def _framework_descendants(children_by_parent):
    descendants = {}

    def collect(framework_name):
        cached = descendants.get(framework_name)
        if cached is not None:
            return cached
        found = set()
        for child_name in children_by_parent.get(framework_name, []):
            found.add(child_name)
            found.update(collect(child_name))
        descendants[framework_name] = found
        return found

    for framework_name in children_by_parent:
        collect(framework_name)
    return descendants


def _point_in_framework_body(point, framework_name, framework_positions, descendants_by_host, clearance=0.0):
    framework_circle = framework_positions.get(framework_name)
    if framework_circle is None:
        return False
    if not _point_within_circle(point, framework_circle, clearance):
        return False

    for descendant_name in descendants_by_host.get(framework_name, ()):
        descendant_circle = framework_positions.get(descendant_name)
        if descendant_circle is None:
            continue
        if _point_within_circle(point, descendant_circle, clearance):
            return False
    return True


def _furthest_unblocked_distance_on_ray(angle, max_distance, blocked_circles, clearance):
    if max_distance <= 0.0:
        return None

    ux = math.cos(angle)
    uy = math.sin(angle)
    intervals = []
    for bx, by, br in blocked_circles:
        effective_radius = br + clearance
        projection = (bx * ux) + (by * uy)
        offset_sq = (bx * bx) + (by * by) - (projection * projection)
        radius_sq = effective_radius * effective_radius
        if offset_sq > radius_sq:
            continue
        chord = math.sqrt(max(0.0, radius_sq - offset_sq))
        start = projection - chord
        end = projection + chord
        if end <= 0.0 or start >= max_distance:
            continue
        intervals.append((max(0.0, start), min(max_distance, end)))

    if not intervals:
        return max_distance

    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
            continue
        merged[-1][1] = max(merged[-1][1], end)

    candidate_distance = max_distance
    nudge = max(0.5, clearance * 0.5)
    for start, end in reversed(merged):
        if candidate_distance > end:
            break
        candidate_distance = start - nudge

    if candidate_distance <= 0.0:
        return None
    return candidate_distance


def _framework_anchor_point(framework_name, other_point, framework_positions, descendants_by_host):
    framework_circle = framework_positions.get(framework_name)
    if framework_circle is None:
        return None

    cx, cy, radius = framework_circle
    if other_point is None:
        base_angle = -math.pi / 2.0
    else:
        dx = other_point[0] - cx
        dy = other_point[1] - cy
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            base_angle = -math.pi / 2.0
        else:
            base_angle = math.atan2(dy, dx)

    blocked_circles = []
    for descendant_name in sorted(descendants_by_host.get(framework_name, ())):
        descendant_circle = framework_positions.get(descendant_name)
        if descendant_circle is None:
            continue
        blocked_cx, blocked_cy, blocked_radius = descendant_circle
        blocked_circles.append((blocked_cx - cx, blocked_cy - cy, blocked_radius))

    body_clearance = max(1.5, min(5.0, radius * 0.04))
    boundary_inset = max(5.0, min(12.0, radius * 0.08))
    max_distance = max(0.0, radius - boundary_inset)
    if max_distance <= 0.0:
        return (cx, cy)

    angle_offsets = [0.0]
    angle_step = math.pi / 36.0
    for step in range(1, 37):
        delta = angle_step * step
        angle_offsets.append(delta)
        angle_offsets.append(-delta)

    preferred_distance = max(max_distance * 0.72, radius * 0.45)
    best_point = None
    best_score = None

    for offset in angle_offsets:
        angle = base_angle + offset
        distance = _furthest_unblocked_distance_on_ray(
            angle,
            max_distance,
            blocked_circles,
            body_clearance,
        )
        if distance is None:
            continue
        point = (
            cx + (distance * math.cos(angle)),
            cy + (distance * math.sin(angle)),
        )
        if not _point_in_framework_body(
            point,
            framework_name,
            framework_positions,
            descendants_by_host,
            clearance=body_clearance,
        ):
            continue
        if distance >= preferred_distance:
            return point
        score = (distance, -abs(offset))
        if best_score is None or score > best_score:
            best_score = score
            best_point = point

    if best_point is not None:
        return best_point

    center_point = (cx, cy)
    if _point_in_framework_body(
        center_point,
        framework_name,
        framework_positions,
        descendants_by_host,
        clearance=body_clearance,
    ):
        return center_point
    return center_point


def _relation_endpoint_reference(endpoint, object_positions, framework_positions):
    if endpoint["kind"] == "object":
        return object_positions.get(endpoint["name"])
    if endpoint["kind"] == "framework":
        framework_circle = framework_positions.get(endpoint["name"])
        if framework_circle is None:
            return None
        fx, fy, _ = framework_circle
        return (fx, fy)
    return None


def _object_font_size(object_name, hosts, framework_positions):
    radii = [framework_positions[host_name][2] for host_name in hosts if host_name in framework_positions]
    if not radii:
        return 18.0
    return _text_font_size_for_radius(min(radii))


def _object_clearance(object_name, host_radius):
    font_size = _text_font_size_for_radius(host_radius)
    text_width = len(str(object_name)) * (font_size * 0.34)
    return max(10.0, (text_width / 2.0) + (font_size * 0.45))


def _find_host_object_positions(host_name, object_names, framework_positions, blocked_framework_names):
    cx, cy, radius = framework_positions[host_name]
    host_circle = framework_positions[host_name]
    blocked_circles = [
        framework_positions[framework_name]
        for framework_name in sorted(blocked_framework_names)
        if framework_name in framework_positions
    ]

    if not object_names:
        return {}

    positions = {}
    placed = []
    ring_step = max(18.0, radius * 0.14)
    max_ring_radius = max(18.0, radius - max(20.0, radius * 0.14))
    min_ring_radius = max(12.0, radius * 0.20)
    ring_radii = []
    ring_radius = max_ring_radius
    while ring_radius >= min_ring_radius:
        ring_radii.append(ring_radius)
        ring_radius -= ring_step
    if not ring_radii:
        ring_radii = [max(radius * 0.45, 12.0)]

    angle_count = max(18, len(object_names) * 10)
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))

    for object_name in sorted(object_names):
        clearance = _object_clearance(object_name, radius)
        point = None
        for ring_index, ring_radius in enumerate(ring_radii):
            for angle_index in range(angle_count):
                angle = ((angle_index * golden_angle) + (ring_index * 0.31)) % (2.0 * math.pi)
                candidate = (
                    cx + ring_radius * math.cos(angle),
                    cy + ring_radius * math.sin(angle),
                )
                if not _point_within_circle(candidate, host_circle, clearance):
                    continue
                if any(
                    _point_within_circle(candidate, blocked_circle, clearance)
                    for blocked_circle in blocked_circles
                ):
                    continue
                if any(
                    math.hypot(candidate[0] - other_point[0], candidate[1] - other_point[1]) < (clearance + other_clearance)
                    for other_point, other_clearance in placed
                ):
                    continue
                point = candidate
                break
            if point is not None:
                break
        if point is None:
            if blocked_circles:
                point = (cx, cy - max(0.0, radius * 0.55))
            else:
                point = (cx, cy + (radius * 0.35))
        positions[object_name] = point
        placed.append((point, clearance))

    return positions


def _place_objects(graph, framework_positions, children_by_parent):
    object_positions = {}
    object_to_hosts = {}
    host_unique_objects = defaultdict(list)
    shared_objects = []
    floating_objects = []
    descendants_by_host = _framework_descendants(children_by_parent)

    all_object_names = sorted(set(graph.object_hosts.keys()) | set(graph.object_relation_hosts.keys()))
    for object_name in all_object_names:
        direct_hosts = set(graph.object_hosts.get(object_name, ()))
        fallback_hosts = set(graph.object_relation_hosts.get(object_name, ()))
        resolved_hosts = direct_hosts if direct_hosts else fallback_hosts
        resolved_hosts = [name for name in sorted(resolved_hosts) if name in framework_positions]
        object_to_hosts[object_name] = resolved_hosts
        if not resolved_hosts:
            floating_objects.append(object_name)
            continue
        if len(resolved_hosts) == 1:
            host_unique_objects[resolved_hosts[0]].append(object_name)
            continue
        shared_objects.append((object_name, resolved_hosts))

    for host_name, object_names in host_unique_objects.items():
        object_positions.update(
            _find_host_object_positions(
                host_name,
                object_names,
                framework_positions,
                descendants_by_host.get(host_name, set()),
            )
        )

    shared_cluster_offsets = defaultdict(int)
    for object_name, host_names in shared_objects:
        shared_position = _shared_object_position(host_names, framework_positions)
        if shared_position is not None:
            cluster_key = tuple(host_names)
            offset_index = shared_cluster_offsets[cluster_key]
            shared_cluster_offsets[cluster_key] += 1
            if offset_index == 0:
                object_positions[object_name] = shared_position
                continue
            angle = (2.0 * math.pi * (offset_index - 1)) / max(3, offset_index + 2)
            offset_radius = 14.0 + (4.0 * ((offset_index - 1) // 6))
            object_positions[object_name] = (
                shared_position[0] + offset_radius * math.cos(angle),
                shared_position[1] + offset_radius * math.sin(angle),
            )

    if floating_objects:
        floating_base_x = 28.0
        floating_base_y = 28.0
        for idx, object_name in enumerate(sorted(floating_objects)):
            object_positions[object_name] = (floating_base_x + (idx * 24.0), floating_base_y)

    return object_positions, object_to_hosts


def _style_for_framework_node(framework_name, parent_of, graph):
    parent_name = parent_of.get(framework_name)
    if parent_name is None:
        return "asserted"
    return graph.framework_edge_style.get((parent_name, framework_name), "asserted")


def _style_for_object_node(object_name, hosts, graph):
    if not hosts:
        return "asserted"
    style = None
    for host_name in hosts:
        style = _merge_style(style, graph.object_host_style.get((host_name, object_name), "asserted"))
    return style or "asserted"


def _escape_attr(value):
    return _xml_escape(str(value), quote=True)


def _build_diagram_svg(tree):
    graph = _build_diagram_graph(tree)
    if not graph.frameworks:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="160">'
            '<rect width="100%" height="100%" fill="#f8fafc" />'
            '<text x="240" y="85" text-anchor="middle" fill="#334155" '
            'font-family="Georgia, serif" font-size="16">No frameworks to render</text>'
            "</svg>"
        )

    roots, parent_of, children_by_parent = _build_primary_framework_tree(graph)
    if not roots:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="160">'
            '<rect width="100%" height="100%" fill="#f8fafc" />'
            '<text x="240" y="85" text-anchor="middle" fill="#334155" '
            'font-family="Georgia, serif" font-size="16">No frameworks to render</text>'
            "</svg>"
        )

    layout = _layout_framework_positions(graph, roots, children_by_parent)
    framework_positions = layout["positions"]
    width = layout["width"]
    height = layout["height"]
    object_positions, object_to_hosts = _place_objects(graph, framework_positions, children_by_parent)
    descendants_by_host = _framework_descendants(children_by_parent)

    note_blocks = []
    max_right = float(width)
    max_bottom = float(height)
    for framework_name, notes in graph.unassertibility_notes.items():
        if not notes or framework_name not in framework_positions:
            continue
        cx, cy, radius = framework_positions[framework_name]
        block_x = cx + radius + 18.0
        block_y = cy - radius + 24.0
        longest = max(len(note) for note in notes)
        approx_width = (longest * 8.0) + 18.0
        approx_height = (len(notes) * 20.0) + 6.0
        max_right = max(max_right, block_x + approx_width + 14.0)
        max_bottom = max(max_bottom, block_y + approx_height + 14.0)
        note_blocks.append((framework_name, block_x, block_y, notes))

    width = int(math.ceil(max_right))
    height = int(math.ceil(max_bottom))

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<defs>',
        '<marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">',
        '<polygon points="0 0, 8 4, 0 8" fill="#334155" />',
        '</marker>',
        '</defs>',
        '<rect width="100%" height="100%" fill="#f8fafc" />',
    ]

    for framework_name, (cx, cy, radius) in sorted(
        framework_positions.items(),
        key=lambda item: item[1][2],
        reverse=True,
    ):
        style = _style_for_framework_node(framework_name, parent_of, graph)
        if style == "unasserted":
            stroke = "#b91c1c"
            dash = ' stroke-dasharray="6,3"'
        else:
            stroke = "#1e293b"
            dash = ""
        svg_parts.append(
            f'<circle data-framework="{_escape_attr(framework_name)}" '
            f'cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" fill="#ffffff" '
            f'stroke="{stroke}" stroke-width="2.5"{dash} />'
        )

    for relation in graph.relation_edges:
        source = relation["source"]
        target = relation["target"]
        source_pos = _relation_endpoint_reference(source, object_positions, framework_positions)
        target_pos = _relation_endpoint_reference(target, object_positions, framework_positions)
        if source_pos is None or target_pos is None:
            continue
        if target["kind"] == "framework":
            target_pos = _framework_anchor_point(
                target["name"],
                source_pos,
                framework_positions,
                descendants_by_host,
            ) or target_pos
        if source["kind"] == "framework":
            source_pos = _framework_anchor_point(
                source["name"],
                target_pos,
                framework_positions,
                descendants_by_host,
            ) or source_pos
            if target["kind"] == "framework":
                target_pos = _framework_anchor_point(
                    target["name"],
                    source_pos,
                    framework_positions,
                    descendants_by_host,
                ) or target_pos
        x1, y1 = source_pos
        x2, y2 = target_pos
        if relation["style"] == "unasserted":
            stroke = "#b91c1c"
            dash = ' stroke-dasharray="6,3"'
        else:
            stroke = "#334155"
            dash = ""
        svg_parts.append(
            f'<line data-relation="{_escape_attr(relation["label"])}" '
            f'data-source="{_escape_attr(source["name"])}" '
            f'data-target="{_escape_attr(target["name"])}" '
            f'x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="2"{dash} marker-end="url(#arrowhead)" />'
        )
        label_x = (x1 + x2) / 2.0
        label_y = (y1 + y2) / 2.0 - 7.0
        svg_parts.append(
            f'<text data-relation-label="{_escape_attr(relation["label"])}" '
            f'x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="middle" '
            'font-family="Georgia, serif" font-size="13" fill="#0f172a">'
            f'{_xml_escape(relation["label"])}</text>'
        )

    for object_name, (ox, oy) in sorted(object_positions.items()):
        hosts = object_to_hosts.get(object_name, [])
        style = _style_for_object_node(object_name, hosts, graph)
        font_size = _object_font_size(object_name, hosts, framework_positions)
        if style == "unasserted":
            color = "#b91c1c"
        elif len(hosts) > 1:
            color = "#0f766e"
        else:
            color = "#0f172a"
        hosts_value = ",".join(sorted(hosts))
        svg_parts.append(
            f'<text data-object="{_escape_attr(object_name)}" '
            f'data-hosts="{_escape_attr(hosts_value)}" '
            f'x="{ox:.2f}" y="{oy:.2f}" text-anchor="middle" '
            f'font-family="Georgia, serif" font-size="{font_size:.2f}" '
            f'fill="{color}">{_xml_escape(object_name)}</text>'
        )

    for framework_name, (cx, cy, radius) in sorted(
        framework_positions.items(),
        key=lambda item: item[1][2],
        reverse=True,
    ):
        font_size = _text_font_size_for_radius(radius)
        label_y = cy - radius + _circle_padding_for_label(radius)
        svg_parts.append(
            f'<text data-framework-label="{_escape_attr(framework_name)}" '
            f'x="{cx:.2f}" y="{label_y:.2f}" text-anchor="middle" '
            f'font-family="Georgia, serif" font-size="{font_size:.2f}" font-weight="bold" fill="#0f172a">'
            f'{_xml_escape(framework_name)}</text>'
        )

    for framework_name, block_x, block_y, notes in sorted(note_blocks, key=lambda item: item[0]):
        for idx, note in enumerate(notes):
            note_y = block_y + (idx * 20.0)
            svg_parts.append(
                f'<text data-unassert-note-host="{_escape_attr(framework_name)}" '
                f'data-unassert-note-index="{idx}" '
                f'x="{block_x:.2f}" y="{note_y:.2f}" text-anchor="start" '
                'font-family="Georgia, serif" font-size="14" fill="#b91c1c">'
                f'{_xml_escape(note)}</text>'
            )

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def render_diagram(tree=Main.tree, output_path=None):
    """
    Render a tree as an SVG diagram.
    - Frameworks are circles.
    - Objects are rendered as letters/text.
    - Relations are arrows.
    - Asserted items are placed inside their host framework circle.
    """
    svg = _build_diagram_svg(tree)
    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(svg)
    return svg


def visualize_tree(tree=Main.tree, output_path=None):
    return render_diagram(tree=tree, output_path=output_path)


def visualise_tree(tree=Main.tree, output_path=None):
    return render_diagram(tree=tree, output_path=output_path)


def visualize_diagram(tree=Main.tree, output_path=None):
    return render_diagram(tree=tree, output_path=output_path)


def visualise_diagram(tree=Main.tree, output_path=None):
    return render_diagram(tree=tree, output_path=output_path)


def render(tree=Main.tree):
    overlaps = check_naming_overlaps(tree)
    if overlaps:
        print("WARNING: Naming overlaps detected:", file=sys.stderr)
        for name, nodes in overlaps.items():
            node_types = ", ".join([node_type for node_type, _ in nodes])
            print(f"  '{name}' appears {len(nodes)} times ({node_types})", file=sys.stderr)
        print()

    roots = _root_frameworks(tree)

    if not roots:
        lines = [
            _render_unassertibility(node) if isinstance(node, Main.Unassertibility) else _render_assertibility(node)
            for node in tree
            if isinstance(node, (Main.Assertibility, Main.Unassertibility))
        ]
        final = "\n".join(lines)
        print(final)
        return final

    if len(roots) == 1:

        final = _render_framework(roots[0])
        print(final)
        return final

    lines = [_render_framework(root) for root in roots]
    final = "\n".join(lines)
    print(final)
    return final

if __name__ == "__main__":
    for lim in examples.limits:
        render(lim)   
        print("_________________")     
    svg = render_diagram(examples.example_tree_1, output_path="limits.svg")
