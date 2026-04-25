from Main import *
from functools import partial

# Example-building guide:
# - Each example builder should only mutate `tree` via the add_* helpers.
# - Prefer using _add_statement() to create the framework -> assertibility -> child pattern.
# - If you need to "pretend" a node is another type for name overlap rules,
#   pass `name_as=...` at creation time or call `tag_name_as(node, ...)`.
#   in EXAMPLE_TREES.

def _collect_name_entries(tree_nodes):
    name_count = {}
    stack = list(tree_nodes)

    while stack:
        node = stack.pop()
        if node is None:
            continue
        if isinstance(node, Obj):
            name_count.setdefault(node.name, []).append(("Obj", node))
        elif isinstance(node, Relation):
            name_count.setdefault(node.name, []).append(("Relation", node))
            if node.left is not None:
                stack.append(node.left)
            if node.right is not None:
                stack.append(node.right)
        elif isinstance(node, Assertibility):
            name_count.setdefault(node.name, []).append(("Assertibility", node))
            if node.child is not None:
                stack.append(node.child)
        elif isinstance(node, Unassertibility):
            name_count.setdefault(node.name, []).append(("Unassertibility", node))
            if node.child is not None:
                stack.append(node.child)
        elif isinstance(node, Framework):
            name_count.setdefault(node.name, []).append(("Framework", node))
            children = getattr(node, "children", None)
            if children:
                stack.extend(children)
    return name_count


def _iter_sorted_overlaps(name_count):
    overlaps = {name: nodes for name, nodes in name_count.items() if len(nodes) > 1}
    for name in sorted(overlaps):
        yield name, overlaps[name]


def _warn_name_overlaps(tree_nodes):
    name_count = _collect_name_entries(tree_nodes)
    overlaps = list(_iter_sorted_overlaps(name_count))
    if overlaps:
        import warnings

        lines = ["Naming overlaps detected:"]
        for name, nodes in overlaps:
            node_types = ", ".join(sorted(node_type for node_type, _ in nodes))
            lines.append(f"  '{name}' appears {len(nodes)} times ({node_types})")
        warnings.warn("\n".join(lines), stacklevel=2)


def _warn_cross_tree_name_overlaps(trees, tree_labels=None, *, error_on_overlap=False):
    if tree_labels is None:
        tree_labels = [f"tree_{idx + 1}" for idx in range(len(trees))]
    name_to_trees = {}
    for idx, tree_nodes in enumerate(trees):
        if not tree_nodes:
            continue
        names = _collect_name_entries(tree_nodes).keys()
        for name in names:
            name_to_trees.setdefault(name, set()).add(idx)

    overlaps = {name: sorted(trees_set) for name, trees_set in name_to_trees.items() if len(trees_set) > 1}
    if not overlaps:
        return

    lines = ["Cross-tree name overlaps detected:"]
    for name in sorted(overlaps):
        labels = ", ".join(tree_labels[idx] for idx in overlaps[name])
        lines.append(f"  '{name}' appears in {len(overlaps[name])} trees ({labels})")

    message = "\n".join(lines)
    if error_on_overlap:
        raise ValueError(message)

    import warnings
    warnings.warn(message, stacklevel=2)


def _collect_names_from_trees(trees):
    names = set()
    for tree_nodes in trees:
        if not tree_nodes:
            continue
        names.update(_collect_name_entries(tree_nodes).keys())
    return names


def _build_randomized_trees(builders, seed_names):
    import Main as _Main

    previous_tree = list(tree)
    previous_registry = dict(name_registry)
    previous_auto = set(auto_used_names)
    previous_process = _Main.process_name
    try:
        tree.clear()
        name_registry.clear()
        auto_used_names.clear()
        auto_used_names.update(seed_names)

        def _auto_process_name(_name, owner_cls):
            return previous_process(None, owner_cls)

        _Main.process_name = _auto_process_name

        built = []
        for build_fn in builders:
            start_len = len(tree)
            build_fn()
            built.append(list(tree[start_len:]))
        return built
    finally:
        _Main.process_name = previous_process
        tree.clear()
        tree.extend(previous_tree)
        name_registry.clear()
        name_registry.update(previous_registry)
        auto_used_names.clear()
        auto_used_names.update(previous_auto)


def build_examples_shared(builders, *, warn=True, warn_cross_tree=True, error_on_cross_tree_overlap=False, warn_intra_tree=True):
    """
    Build multiple trees in a shared naming context.
    Returns (trees_by_name, merged_tree).
    """
    previous_tree = list(tree)
    previous_registry = dict(name_registry)
    previous_auto = set(auto_used_names)
    try:
        tree.clear()
        name_registry.clear()
        auto_used_names.clear()

        trees_by_name = {}
        merged = []
        for name, build_fn in builders:
            start_len = len(tree)
            build_fn()
            nodes = list(tree[start_len:])
            trees_by_name[name] = nodes
            merged.extend(nodes)

        if error_on_cross_tree_overlap:
            _warn_cross_tree_name_overlaps(
                list(trees_by_name.values()),
                list(trees_by_name.keys()),
                error_on_overlap=True,
            )
        elif warn and warn_cross_tree:
            _warn_cross_tree_name_overlaps(
                list(trees_by_name.values()),
                list(trees_by_name.keys()),
                error_on_overlap=False,
            )
        if warn and warn_intra_tree:
            _warn_name_overlaps(merged)
        return trees_by_name, merged
    finally:
        tree.clear()
        tree.extend(previous_tree)
        name_registry.clear()
        name_registry.update(previous_registry)
        auto_used_names.clear()
        auto_used_names.update(previous_auto)


def merge_trees(
    *trees,
    tree_labels=None,
    warn=True,
    warn_cross_tree=True,
    error_on_cross_tree_overlap=False,
    warn_intra_tree=True,
):
    """
    Merge multiple trees for rendering, with name overlap warnings.
    Accepts tree node lists and/or builder functions. Builder functions are
    executed with auto-generated names.
    """
    items = list(trees)
    if tree_labels is not None and len(tree_labels) != len(items):
        raise ValueError("tree_labels must match the number of trees/builders.")

    builder_indices = [idx for idx, item in enumerate(items) if callable(item)]
    if builder_indices:
        existing_trees = [item for item in items if not callable(item)]
        seed_names = _collect_names_from_trees(existing_trees)

        builder_fns = [items[idx] for idx in builder_indices]
        built_trees = _build_randomized_trees(builder_fns, seed_names)
        for idx, built in zip(builder_indices, built_trees):
            items[idx] = built

    merged = []
    for tree_nodes in items:
        if tree_nodes:
            merged.extend(tree_nodes)

    if error_on_cross_tree_overlap:
        _warn_cross_tree_name_overlaps(
            list(items),
            tree_labels,
            error_on_overlap=True,
        )
    elif warn and warn_cross_tree:
        _warn_cross_tree_name_overlaps(
            list(items),
            tree_labels,
            error_on_overlap=False,
        )
    if warn and warn_intra_tree:
        _warn_name_overlaps(merged)
    return merged

def _build_example(build_fn):
    """Build one example in isolation and return the list of nodes created."""
    previous_tree = list(tree)
    previous_registry = dict(name_registry)
    previous_auto = set(auto_used_names)
    try:
        tree.clear()
        name_registry.clear()
        auto_used_names.clear()
        build_fn()
        return list(tree)
    finally:
        tree.clear()
        tree.extend(previous_tree)
        name_registry.clear()
        name_registry.update(previous_registry)
        auto_used_names.clear()
        auto_used_names.update(previous_auto)

def _build_nested_relations():
    """Example: a framework with nested relations (relation inside relation)."""
    framework = add_framework(None, "x")

    statement = add_assertibility(framework, "r", name_as=Relation)
    outer = add_relation(statement, "r")
    inner = add_relation(outer, "r_inner")

    left = add_obj(inner, "A")
    right = add_obj(inner, "B", name_as=Framework)
    set_relation_children(inner, left, right)

    outer_right = add_obj(outer, "C")
    set_relation_children(outer, inner, outer_right)

    set_assertibility_child(statement, outer)
    set_framework_children(framework, [statement])

def _add_statement(framework_name, build_child):
    """
    Create a single framework with one assertibility and one child.
    `build_child(assertion)` should return the node that becomes the assertion's child.
    """
    framework = add_framework(None, framework_name)
    assertion = add_assertibility(framework, f"{framework_name}_stmt")
    child = build_child(assertion)
    set_assertibility_child(assertion, child)
    set_framework_children(framework, [assertion])
    return framework


def _add_attached_statement(parent, framework_name, build_child, statement_name=None):
    """
    Create a non-root helper framework with one assertibility and one child.
    This is useful when an assertion should render with a framework context but
    should not become its own top-level printed line.
    """
    framework = add_framework(parent, framework_name)
    assertion = add_assertibility(framework, statement_name or f"{framework_name}_stmt")
    child = build_child(assertion)
    set_assertibility_child(assertion, child)
    set_framework_children(framework, [assertion])
    return framework, assertion

def add_section_break():
    """Insert a render-only separator that becomes a blank output line."""
    framework = add_framework(None, "__section_break_framework__")
    assertion = add_assertibility(framework, "__section_break_assertion__")
    newline = add_newline(assertion)
    set_assertibility_child(assertion, newline)
    set_framework_children(framework, [assertion])
    return framework

def add_unassertibility_statement(parent_framework_name, child_assertable_name, subject):
    """
    Create ⊢_{parent}(Γ_{child}(x)) as a framework -> unassertibility -> assertibility -> child chain.
    `subject` can be a name string or a (name, Framework) tuple to create a framework child.
    """
    framework = add_framework(None, parent_framework_name)
    unassertion = add_unassertibility(framework, child_assertable_name, name_as=Framework)
    assertion = add_assertibility(unassertion, f"{child_assertable_name}_stmt")

    if isinstance(subject, tuple):
        subject_name, subject_kind = subject
    else:
        subject_name, subject_kind = subject, None

    if subject_kind is Framework:
        child = add_framework(assertion, subject_name)
    else:
        child = add_obj(assertion, subject_name)

    set_assertibility_child(assertion, child)
    set_unassertibility_child(unassertion, assertion)
    set_framework_children(framework, [unassertion])
    return framework

def rel_child(assertion, name1, name2, name3, relation_name_as=None, left_name_as=None, right_name_as=None):
    relation = add_relation(assertion, name1, name_as=relation_name_as)
    if isinstance(name2, (Assertibility, Unassertibility, Relation, Obj)):
        left = name2
    else:
        left = add_obj(relation, name2, name_as=left_name_as)
    if isinstance(name3, (Assertibility, Unassertibility, Relation, Obj)):
        right = name3
    else:
        right = add_obj(relation, name3, name_as=right_name_as)
    set_relation_children(relation, left, right)
    return relation

def _resolve_example_names(defaults, provided, owner_classes):
    changed_keys = [key for key in defaults if provided[key] != defaults[key]]
    single_override = len(changed_keys) == 1
    normalized = dict(provided)
    if single_override:
        changed_key = changed_keys[0]
        for key in normalized:
            if key != changed_key:
                normalized[key] = None

    explicit_names = {str(value) for value in normalized.values() if value is not None}
    resolved = {}
    chosen = set(explicit_names)
    if single_override:
        chosen.update(str(value) for value in defaults.values())
    for key, value in normalized.items():
        if value is None:
            generated = process_name(None, owner_classes[key])
            while generated in chosen:
                generated = process_name(None, owner_classes[key])
            resolved[key] = generated
            chosen.add(generated)
        else:
            resolved[key] = value
    return resolved


def Ahom_set(
    x_name="x",
    b_name="B",
    s_name="s",
    d_name="D",
    a_name="A",
    relation_name="r",
):
    resolved = _resolve_example_names(
        defaults={
            "x_name": "x",
            "b_name": "B",
            "s_name": "s",
            "d_name": "D",
            "a_name": "A",
            "relation_name": "r",
        },
        provided={
            "x_name": x_name,
            "b_name": b_name,
            "s_name": s_name,
            "d_name": d_name,
            "a_name": a_name,
            "relation_name": relation_name,
        },
        owner_classes={
            "x_name": Framework,
            "b_name": Framework,
            "s_name": Framework,
            "d_name": Obj,
            "a_name": Obj,
            "relation_name": Relation,
        },
    )
    x_name = resolved["x_name"]
    b_name = resolved["b_name"]
    s_name = resolved["s_name"]
    d_name = resolved["d_name"]
    a_name = resolved["a_name"]
    relation_name = resolved["relation_name"]
    framework_names = {x_name, b_name, s_name}

    def _obj(parent, name):
        name_as = Framework if name in framework_names else None
        return add_obj(parent, name, name_as=name_as)

    _add_statement(b_name, lambda assertion: _obj(assertion, s_name))
    x_framework = add_framework(None, x_name)
    x_statement = add_assertibility(x_framework, f"{x_name}_stmt")
    s_framework = add_framework(None, s_name)
    s_statement = add_assertibility(s_framework, f"{s_name}_stmt")

    helper_x, x_b_assertion = _add_attached_statement(
        x_statement,
        x_name,
        lambda assertion: _obj(assertion, b_name),
        statement_name=f"{x_name}_nested_b",
    )
    _helper_x, x_d_assertion = _add_attached_statement(
        helper_x,
        x_name,
        lambda assertion: _obj(assertion, d_name),
        statement_name=f"{x_name}_nested_d",
    )
    _helper_s, s_a_assertion = _add_attached_statement(
        s_statement,
        s_name,
        lambda assertion: _obj(assertion, a_name),
        statement_name=f"{s_name}_nested_a",
    )

    x_relation = rel_child(
        x_statement,
        relation_name,
        s_a_assertion,
        x_b_assertion,
    )
    s_relation = rel_child(
        s_statement,
        relation_name,
        x_b_assertion,
        x_d_assertion,
    )

    set_assertibility_child(x_statement, x_relation)
    set_framework_children(x_framework, [x_statement])
    set_assertibility_child(s_statement, s_relation)
    set_framework_children(s_framework, [s_statement])
    return b_name


def Dhom_set(
    x_name="x",
    b_name="B",
    s_name="s",
    d_name="D",
    a_name="A",
    relation_name="r",
):
    resolved = _resolve_example_names(
        defaults={
            "x_name": "x",
            "b_name": "B",
            "s_name": "s",
            "d_name": "D",
            "a_name": "A",
            "relation_name": "r",
        },
        provided={
            "x_name": x_name,
            "b_name": b_name,
            "s_name": s_name,
            "d_name": d_name,
            "a_name": a_name,
            "relation_name": relation_name,
        },
        owner_classes={
            "x_name": Framework,
            "b_name": Framework,
            "s_name": Framework,
            "d_name": Obj,
            "a_name": Obj,
            "relation_name": Relation,
        },
    )
    x_name = resolved["x_name"]
    b_name = resolved["b_name"]
    s_name = resolved["s_name"]
    d_name = resolved["d_name"]
    a_name = resolved["a_name"]
    relation_name = resolved["relation_name"]
    framework_names = {x_name, b_name, s_name}

    def _obj(parent, name):
        name_as = Framework if name in framework_names else None
        return add_obj(parent, name, name_as=name_as)

    _add_statement(b_name, lambda assertion: _obj(assertion, s_name))
    x_framework = add_framework(None, x_name)
    x_statement = add_assertibility(x_framework, f"{x_name}_stmt")
    s_framework = add_framework(None, s_name)
    s_statement = add_assertibility(s_framework, f"{s_name}_stmt")

    helper_x, x_b_assertion = _add_attached_statement(
        x_statement,
        x_name,
        lambda assertion: _obj(assertion, b_name),
        statement_name=f"{x_name}_nested_b",
    )
    _helper_x, x_d_assertion = _add_attached_statement(
        helper_x,
        x_name,
        lambda assertion: _obj(assertion, d_name),
        statement_name=f"{x_name}_nested_d",
    )
    _helper_s, s_a_assertion = _add_attached_statement(
        s_statement,
        s_name,
        lambda assertion: _obj(assertion, a_name),
        statement_name=f"{s_name}_nested_a",
    )

    x_relation = rel_child(
        x_statement,
        relation_name,
        x_d_assertion,
        x_b_assertion,
    )
    s_relation = rel_child(
        s_statement,
        relation_name,
        x_b_assertion,
        s_a_assertion,
    )

    set_assertibility_child(x_statement, x_relation)
    set_framework_children(x_framework, [x_statement])
    set_assertibility_child(s_statement, s_relation)
    set_framework_children(s_framework, [s_statement])
    return b_name

def cone(
    d_name="d",
    h_name="h",
    i_name="i",
    j_name="j",
    x_name="x",
    n_name="N",
):
    resolved = _resolve_example_names(
        defaults={
            "d_name": "d",
            "h_name": "h",
            "i_name": "i",
            "j_name": "j",
            "x_name": "x",
            "n_name": "N",
        },
        provided={
            "d_name": d_name,
            "h_name": h_name,
            "i_name": i_name,
            "j_name": j_name,
            "x_name": x_name,
            "n_name": n_name,
        },
        owner_classes={
            "d_name": Framework,
            "h_name": Framework,
            "i_name": Framework,
            "j_name": Framework,
            "x_name": Obj,
            "n_name": Obj,
        },
    )
    d_name = resolved["d_name"]
    h_name = resolved["h_name"]
    i_name = resolved["i_name"]
    j_name = resolved["j_name"]
    x_name = resolved["x_name"]
    n_name = resolved["n_name"]

    _add_statement(d_name, lambda assertion: add_obj(assertion, n_name))

    add_unassertibility_statement(h_name, j_name, x_name)
    add_unassertibility_statement(i_name, j_name, x_name)
    add_unassertibility_statement(d_name, j_name, x_name)

    st1 = _add_statement(d_name, lambda assertion: add_framework(assertion, j_name))
    st2 = _add_statement(i_name, lambda assertion: add_obj(assertion, n_name))

    st1_assertion = st1.children[0]
    st2_assertion = st2.children[0]
    Cone_child = partial(
        rel_child,
        name1=h_name,
        name2=st2_assertion,
        name3=st1_assertion,
        relation_name_as=Framework,
    )
    _add_statement(h_name, lambda assertion: Cone_child(assertion))
    return j_name

def _build_limit_colimit(kind, hom1 = "D", hom2 = "A", B_name1 = "B", B_name2 = "B", A2_name = "a", D2_name = "d") :
    hom1_builder = Dhom_set if hom1 == "D" else Ahom_set
    hom2_builder = Dhom_set if hom2 == "D" else Ahom_set
    factor_builder = Dhom_set if kind == "limit" else Ahom_set

    def _build_sequence():
        # foundational cones
        cone()
        add_section_break()

        cone(j_name="k")
        add_section_break()

        # hom-sets
        J_B = hom1_builder(x_name="j", b_name = B_name1)
        add_section_break()

        K_B = hom2_builder(x_name="k", b_name = B_name2, a_name= A2_name, d_name = D2_name)
        add_section_break()

        # factor property
        factor_builder(x_name=K_B, s_name=J_B)

    _trees_by_name, merged = build_examples_shared(
        [("limit_sequence", _build_sequence)],
        warn=False,
        warn_cross_tree=False,
        warn_intra_tree=False,
    )
    tree.extend(merged)
    return merged


def limit(hom1 = "D", hom2 = "A", Bo_name1 = "B", Bo_name2 = "B", a2_name = "a", d2_name = "d"):
    return _build_limit_colimit("limit", hom1, hom2, B_name1 = Bo_name1, B_name2 =Bo_name2, A2_name = a2_name, D2_name = d2_name)

def colimit(hom1 = "A", hom2 = "D", Bo_name1 = "B", Bo_name2 = "B", a2_name = "g", d2_name = "d"):
    return _build_limit_colimit("colimit", hom1, hom2, B_name1 = Bo_name1, B_name2 =Bo_name2, A2_name = a2_name, D2_name = d2_name)

def adjoint(kind, hom1 = "D", hom2 = "A", so_name = "σ", xo_name = "M"):

    base = limit if kind == "R" else colimit
    def _build_sequence():
        base(hom1, hom2, Bo_name2 = so_name, a2_name = xo_name) if kind == "R" else base(hom1, hom2, Bo_name2 = so_name, d2_name = xo_name)
        add_section_break()

        Dhom_set(s_name = so_name, x_name = xo_name)


    
    _trees_by_name, merged = build_examples_shared(
        [("adjoint_sequence", _build_sequence)],
        warn=False,
        warn_cross_tree=False,
        warn_intra_tree=False,
    )
    tree.extend(merged)
    return merged



    

def build_examples():
    """
    Build and return all example trees.
    Add examples here to expose them via EXAMPLE_TREES.
    """
    DAl = partial(limit,hom1 = "D", hom2 = "A")
    ADl = partial(limit,hom1 = "A", hom2 = "D")
    DDl = partial(limit,hom1 = "D", hom2 = "D")
    AAl = partial(limit,hom1 = "A", hom2 = "A")

    cDAl = partial(colimit,hom1 = "D", hom2 = "A")
    cADl = partial(colimit,hom1 = "A", hom2 = "D")
    cDDl = partial(colimit,hom1 = "D", hom2 = "D")
    cAAl = partial(colimit,hom1 = "A", hom2 = "A")

    adjlDA = partial(adjoint,hom1 = "D", hom2 = "A", kind = "L")
    adjlAD = partial(adjoint,hom1 = "A", hom2 = "D", kind = "L")
    adjlDD = partial(adjoint,hom1 = "D", hom2 = "D", kind = "L")
    adjlAA = partial(adjoint,hom1 = "A", hom2 = "A", kind = "L")

    adjrDA = partial(adjoint,hom1 = "D", hom2 = "A", kind = "R")
    adjrAD = partial(adjoint,hom1 = "A", hom2 = "D", kind = "R")
    adjrDD = partial(adjoint,hom1 = "D", hom2 = "D", kind = "R")
    adjrAA = partial(adjoint,hom1 = "A", hom2 = "A", kind = "R")
    return {
        "Dhom": _build_example(Dhom_set),
        "Ahom": _build_example(Ahom_set),
        "Cone": _build_example(cone),

        "DAlimit": _build_example(DAl),
        "ADlimit": _build_example(ADl),
        "DDlimit": _build_example(DDl),
        "AAlimit": _build_example(AAl),

        "cDAlimit": _build_example(cDAl),
        "cADlimit": _build_example(cADl),
        "cDDlimit": _build_example(cDDl),
        "cAAlimit": _build_example(cAAl),

        "lDAadjoint": _build_example(adjlDA),
        "lADadjoint": _build_example(adjlAD),
        "lDDadjoint": _build_example(adjlDD),
        "lAAadjoint": _build_example(adjlAA),

        "rDAadjoint": _build_example(adjrDA),
        "rADadjoint": _build_example(adjrAD),
        "rDDadjoint": _build_example(adjrDD),
        "rAAadjoint": _build_example(adjrAA),
    }


EXAMPLE_TREES = build_examples()
limits = [EXAMPLE_TREES["DAlimit"],EXAMPLE_TREES["ADlimit"], EXAMPLE_TREES["AAlimit"], EXAMPLE_TREES["DDlimit"]]
colimits = [EXAMPLE_TREES["cDAlimit"],EXAMPLE_TREES["cADlimit"], EXAMPLE_TREES["cAAlimit"], EXAMPLE_TREES["cDDlimit"]]

example_tree_1 = EXAMPLE_TREES["Dhom"]
example_tree_2 = EXAMPLE_TREES["Ahom"]
example_tree_3 = EXAMPLE_TREES["Cone"]
