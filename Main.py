"three types of Nodes: relations, objs, and assertibility."
"Relations must have 2 childs"
"Assertibility one child"
"OBjs none"
tree = []

name_registry = {}
auto_used_names = set()

def _check_name_overlap(name, owner_cls):
    existing_cls = name_registry.get(name)
    if existing_cls is None or existing_cls is owner_cls:
        return False
    return True

def _register_name(name, owner_cls):
    if _check_name_overlap(name, owner_cls):
        raise ValueError(
            f"Name overlap across different node types is not allowed: '{name}' "
            f"already used by {name_registry[name].__name__}."
        )
    name_registry[name] = owner_cls

def process_name(name, owner_cls):
    if name is None:
        preferred = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZΓΔΘΛΞΠΣΦΨΩαβγδεζηθικλμνξπρστυφχψω'
        for c in preferred:
            if c not in auto_used_names and not _check_name_overlap(c, owner_cls):
                auto_used_names.add(c)
                _register_name(c, owner_cls)
                return c
        # if all used, use other ASCII printable
        import string
        for c in string.printable:
            if c not in auto_used_names and c not in '\n\r\t':
                if not _check_name_overlap(c, owner_cls):
                    auto_used_names.add(c)
                    _register_name(c, owner_cls)
                    return c
        # last resort, use combinations
        import itertools
        for length in range(2, 10):
            for combo in itertools.product(preferred, repeat=length):
                s = ''.join(combo)
                if s not in auto_used_names and not _check_name_overlap(s, owner_cls):
                    auto_used_names.add(s)
                    _register_name(s, owner_cls)
                    return s
    elif isinstance(name, Obj):
        name = name.name
    name_str = str(name)
    _register_name(name_str, owner_cls)
    return name_str

def tag_name_as(node, name_as):
    if not isinstance(name_as, type):
        raise TypeError("name_as must be a class.")
    if not hasattr(node, "name"):
        raise TypeError("Only named nodes can be tagged.")
    existing_cls = name_registry.get(node.name)
    if existing_cls is not None and existing_cls is not node.name_cls and existing_cls is not name_as:
        raise ValueError(
            f"Name overlap across different node types is not allowed: '{node.name}' "
            f"already used by {existing_cls.__name__}."
        )
    name_registry[node.name] = name_as
    node.name_cls = name_as
    return node

class Obj:
    def __init__(self, parent, name, name_as=None):
        if parent is None or not isinstance(parent, (Assertibility, Relation)):
            raise ValueError("Obj nodes must have an assert or relation parent.")
        self.parent = parent
        self.name_cls = name_as or type(self)
        self.name = process_name(name, self.name_cls)

class Newline:
    def __init__(self, parent):
        if parent is None or not isinstance(parent, (Assertibility, Relation)):
            raise ValueError("Newline nodes must have an assert or relation parent.")
        self.parent = parent

class Relation:
    def __init__(self, parent, name, name_as=None):
        if parent is None or not isinstance(parent, (Assertibility, Relation)):
            raise ValueError("Relation nodes must have an assert or relation parent.")
        self.parent = parent
        self.left = None
        self.right = None
        self.name_cls = name_as or type(self)
        self.name = process_name(name, self.name_cls) 


class Framework:
    def __init__(self, parent, name, name_as=None):
        self.parent = parent
        self.name_cls = name_as or type(self)
        self.name = process_name(name, self.name_cls)

class Assertibility(Framework):
    def __init__(self, parent, name, name_as=None):
        if parent is None or not isinstance(parent, (Framework, Relation)):
            raise ValueError("Assertibility nodes must have a framework or relation parent.")
        super().__init__(parent, name, name_as=name_as)
        self.child = None

class Unassertibility(Framework):
    def __init__(self, parent, name, name_as=None):
        if parent is None or not isinstance(parent, (Framework, Relation)):
            raise ValueError("Unassertibility nodes must have a framework or relation parent.")
        super().__init__(parent, name, name_as=name_as)
        self.child = None

def add_obj(parent, name, name_as=None):
    node = Obj(parent, name, name_as=name_as)
    tree.append(node)
    return node

def add_newline(parent):
    node = Newline(parent)
    tree.append(node)
    return node

def add_framework(parent, name, children=None, name_as=None):
    node = Framework(parent, name, name_as=name_as)
    if children is not None:
        set_framework_children(node, children)
    tree.append(node)
    return node

def add_relation(parent, name, left=None, right=None, name_as=None):
    node = Relation(parent, name, name_as=name_as)
    if left is not None or right is not None:
        set_relation_children(node, left, right)
    tree.append(node)
    return node

def add_assertibility(parent, name, child=None, name_as=None):
    node = Assertibility(parent, name, name_as=name_as)
    if child is not None:
        set_assertibility_child(node, child)
    tree.append(node)
    return node

def add_unassertibility(parent, name, child=None, name_as=None):
    node = Unassertibility(parent, name, name_as=name_as)
    if child is not None:
        set_unassertibility_child(node, child)
    tree.append(node)
    return node

def set_relation_children(relation_node, left, right):
    if left is None or right is None:
        raise ValueError("Relation nodes must have exactly two children.")
    allowed_types = (Assertibility, Unassertibility, Relation, Obj, Newline)
    if not isinstance(left, allowed_types) or not isinstance(right, allowed_types):
        raise TypeError("Relation children must be Assertibility, Unassertibility, Relation, Obj, or Newline nodes.")
    relation_node.left = left
    relation_node.right = right
    # Keep assertion parents intact so nested renderings preserve their framework context.
    if not isinstance(left, (Assertibility, Unassertibility)):
        left.parent = relation_node
    if not isinstance(right, (Assertibility, Unassertibility)):
        right.parent = relation_node
    return relation_node

def set_assertibility_child(assert_node, child):
    if child is None:
        raise ValueError("Assertibility nodes must have exactly one child.")
    assert_node.child = child
    child.parent = assert_node
    return assert_node

def set_unassertibility_child(unassert_node, child):
    if child is None:
        raise ValueError("Unassertibility nodes must have exactly one child.")
    if not isinstance(child, Assertibility):
        raise TypeError("Unassertibility children must be Assertibility nodes.")
    unassert_node.child = child
    child.parent = unassert_node
    return unassert_node

def set_framework_children(framework_node, children):
    if children is None or len(children) == 0:
        raise ValueError("Framework nodes must have at least one child.")
    for child in children:
        if not isinstance(child, (Assertibility, Unassertibility)):
            raise TypeError("Framework children must be Assertibility or Unassertibility nodes.")
        child.parent = framework_node
    framework_node.children = list(children)
    return framework_node

def add_framework_child(framework_node, child):
    if not isinstance(child, (Assertibility, Unassertibility)):
        raise TypeError("Framework children must be Assertibility or Unassertibility nodes.")
    child.parent = framework_node
    framework_node.children.append(child)
    return framework_node
