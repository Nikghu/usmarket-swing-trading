"""Phase 1 — tree-sitter parse → FileSkeleton dataclasses."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_MODULE_ID_RE = re.compile(r"Module:\s*(MD-[A-Z]+-\d+\.\d+\.M\d+)")
_SRD_ID_RE = re.compile(r"Parent SRD:\s*(SRD-[A-Z]+-[\d.]+)")
_TOOL_CODE_RE = re.compile(r"MD-([A-Z]+)-")


@dataclass
class FunctionSkeleton:
    name: str
    signature: str
    docstring: str | None
    decorators: list[str]
    is_private: bool
    line_start: int
    line_end: int
    calls: list[str] = field(default_factory=list)


@dataclass
class ClassSkeleton:
    name: str
    docstring: str | None
    bases: list[str]
    class_vars: list[str]
    methods: list[FunctionSkeleton]
    line_start: int
    line_end: int


@dataclass
class FileSkeleton:
    path: str
    module_id: str | None
    srd_id: str | None
    tool_code: str | None
    classes: list[ClassSkeleton]
    top_level_functions: list[FunctionSkeleton]
    constants: list[str]
    file_hash: str
    imports: list[str] = field(default_factory=list)


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _collect_calls(node: Node, src: bytes, out: list[str]) -> None:
    """Recursively walk a node and collect every call target name."""
    if node.type == "call":
        fn_node = node.child_by_field_name("function")
        if fn_node:
            out.append(_text(fn_node, src))
    for child in node.children:
        _collect_calls(child, src, out)


def _parse_imports(root: Node, src: bytes) -> list[str]:
    """Collect all import lines from the module root."""
    imports: list[str] = []
    for node in root.children:
        if node.type in ("import_statement", "import_from_statement"):
            imports.append(_text(node, src).strip())
    return imports


def _first_docstring(body_node: Node, src: bytes) -> str | None:
    for child in body_node.children:
        if child.type == "expression_statement":
            inner = child.children[0] if child.children else None
            if inner and inner.type in ("string", "concatenated_string"):
                raw = _text(inner, src).strip("'\"").strip()
                return raw.splitlines()[0][:80]
    return None


def _parse_function(node: Node, src: bytes, decorators: list[str]) -> FunctionSkeleton:
    name_node = node.child_by_field_name("name")
    name = _text(name_node, src) if name_node else "<unknown>"

    params_node = node.child_by_field_name("parameters")
    ret_node = node.child_by_field_name("return_type")

    params = _text(params_node, src) if params_node else "()"
    ret = f" -> {_text(ret_node, src)}" if ret_node else ""
    signature = f"def {name}{params}{ret}"

    body_node = node.child_by_field_name("body")
    docstring = _first_docstring(body_node, src) if body_node else None

    calls: list[str] = []
    if body_node:
        _collect_calls(body_node, src, calls)

    return FunctionSkeleton(
        name=name,
        signature=signature,
        docstring=docstring,
        decorators=decorators,
        is_private=name.startswith("_"),
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        calls=calls,
    )


def _parse_class(node: Node, src: bytes) -> ClassSkeleton:
    name_node = node.child_by_field_name("name")
    name = _text(name_node, src) if name_node else "<unknown>"

    bases: list[str] = []
    arg_node = node.child_by_field_name("argument_list")
    if arg_node:
        for child in arg_node.children:
            if child.type not in (",", "(", ")"):
                bases.append(_text(child, src))

    body_node = node.child_by_field_name("body")
    docstring = _first_docstring(body_node, src) if body_node else None

    class_vars: list[str] = []
    methods: list[FunctionSkeleton] = []

    if body_node:
        for child in body_node.children:
            if child.type == "decorated_definition":
                dec_list: list[str] = []
                inner_fn: Node | None = None
                for sub in child.children:
                    if sub.type == "decorator":
                        dec_list.append(_text(sub, src).strip())
                    elif sub.type == "function_definition":
                        inner_fn = sub
                if inner_fn:
                    methods.append(_parse_function(inner_fn, src, dec_list))
            elif child.type == "function_definition":
                methods.append(_parse_function(child, src, []))
            elif child.type == "expression_statement":
                for sub in child.children:
                    if sub.type == "assignment":
                        lhs = sub.child_by_field_name("left")
                        ann = sub.child_by_field_name("type")
                        if lhs and ann:  # type field present = annotated assignment
                            class_vars.append(f"{_text(lhs, src)}: {_text(ann, src)}")
                    break

    return ClassSkeleton(
        name=name,
        docstring=docstring,
        bases=bases,
        class_vars=class_vars,
        methods=methods,
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
    )


def _parse_header(src: bytes) -> tuple[str | None, str | None, str | None]:
    """Extract module_id, srd_id, tool_code from the file docstring."""
    text = src[:800].decode("utf-8", errors="replace")
    mod_match = _MODULE_ID_RE.search(text)
    srd_match = _SRD_ID_RE.search(text)
    module_id = mod_match.group(1) if mod_match else None
    srd_id = srd_match.group(1) if srd_match else None
    tool_code: str | None = None
    if module_id:
        tc = _TOOL_CODE_RE.search(module_id)
        tool_code = tc.group(1) if tc else None
    return module_id, srd_id, tool_code


def extract(path: Path) -> FileSkeleton:
    src = path.read_bytes()
    file_hash = hashlib.sha256(src).hexdigest()
    module_id, srd_id, tool_code = _parse_header(src)

    tree = _PARSER.parse(src)
    root = tree.root_node
    imports = _parse_imports(root, src)

    classes: list[ClassSkeleton] = []
    top_level_functions: list[FunctionSkeleton] = []
    constants: list[str] = []

    for node in root.children:
        if node.type == "decorated_definition":
            dec_list: list[str] = []
            inner: Node | None = None
            for sub in node.children:
                if sub.type == "decorator":
                    dec_list.append(_text(sub, src).strip())
                elif sub.type in ("function_definition", "class_definition"):
                    inner = sub
            if inner:
                if inner.type == "function_definition":
                    top_level_functions.append(_parse_function(inner, src, dec_list))
                else:
                    classes.append(_parse_class(inner, src))

        elif node.type == "class_definition":
            classes.append(_parse_class(node, src))

        elif node.type == "function_definition":
            top_level_functions.append(_parse_function(node, src, []))

        elif node.type == "expression_statement":
            for sub in node.children:
                if sub.type == "assignment":
                    lhs = sub.child_by_field_name("left")
                    if lhs and _text(lhs, src).isupper():
                        constants.append(_text(sub, src).splitlines()[0][:100])
                    break

    return FileSkeleton(
        path=str(path),
        module_id=module_id,
        srd_id=srd_id,
        tool_code=tool_code,
        classes=classes,
        top_level_functions=top_level_functions,
        constants=constants,
        file_hash=file_hash,
        imports=imports,
    )
