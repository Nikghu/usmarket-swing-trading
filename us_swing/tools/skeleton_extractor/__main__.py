"""Phase 4 — CLI entrypoint: refresh and query subcommands."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).parents[2] / "src" / "us_swing"


def _cmd_refresh(args: argparse.Namespace) -> None:
    from skeleton_extractor.cache import refresh
    from skeleton_extractor.renderer import render_all, token_stats

    skeletons = refresh(_SRC_ROOT, tool_filter=args.tool)

    render_all(skeletons)

    if args.stats:
        token_stats(skeletons)

    if args.debug:
        from skeleton_extractor.extractor import extract
        skel = extract(Path(args.debug))
        _print_file_skeleton(skel)


def _cmd_query(args: argparse.Namespace) -> None:
    from skeleton_extractor.cache import find_uncached, load_all
    skeletons = load_all()

    if not skeletons:
        print("Cache is empty — run `python -m skeleton_extractor` first.", file=sys.stderr)
        sys.exit(1)

    uncached = find_uncached(_SRC_ROOT)
    if uncached:
        print(
            f"WARNING: {len(uncached)} file(s) added manually and not in cache"
            " — run `python -m skeleton_extractor` to refresh:\n"
            + "\n".join(f"  {p}" for p in uncached),
            file=sys.stderr,
        )

    if args.overview:
        _query_overview(skeletons, args.overview)
    elif args.cls:
        _query_class(skeletons, args.cls)
    elif args.symbol:
        _query_symbol(skeletons, args.symbol, args.cls)
    elif args.find:
        _query_find(skeletons, args.find)
    elif args.usages:
        _query_usages(skeletons, args.usages)
    elif args.file:
        _query_file(skeletons, args.file)
    elif args.list_files:
        _query_list_files(skeletons, args.list_files)
    else:
        print("Specify a query option. Use --help for details.")


def _match_tool(skel: object, query: str) -> bool:  # type: ignore[type-arg]
    """Match a skeleton by tool_code (exact, case-insensitive) or path substring."""
    from skeleton_extractor.extractor import FileSkeleton
    assert isinstance(skel, FileSkeleton)
    q = query.strip().replace("\\", "/")
    if skel.tool_code and skel.tool_code.upper() == q.upper():
        return True
    return q.lower() in skel.path.replace("\\", "/").lower()


def _query_overview(skeletons: dict, query: str) -> None:  # type: ignore[type-arg]
    found = False
    for skel in skeletons.values():
        if not _match_tool(skel, query):
            continue
        found = True
        print(f"\n## {Path(skel.path).name}")
        for cls in skel.classes:
            pub = [m.name for m in cls.methods if not m.is_private]
            print(f"  class {cls.name}: {', '.join(pub)}")
        for fn in skel.top_level_functions:
            print(f"  def {fn.name}")
    if not found:
        print(f"No entries found for '{query}'.")


def _query_class(skeletons: dict, class_name: str) -> None:  # type: ignore[type-arg]
    found = False
    for skel in skeletons.values():
        for cls in skel.classes:
            if cls.name == class_name:
                print(f"# {Path(skel.path).name}")
                _print_class(cls)
                found = True
    if not found:
        print(f"Class '{class_name}' not found in cache.")


def _query_symbol(skeletons: dict, symbol: str, class_name: str | None) -> None:  # type: ignore[type-arg]
    found = False
    for skel in skeletons.values():
        for cls in skel.classes:
            if class_name and cls.name != class_name:
                continue
            for fn in cls.methods:
                if fn.name == symbol:
                    print(f"  [{cls.name}.{fn.name}] {fn.signature}")
                    if fn.docstring:
                        print(f"    # {fn.docstring}")
                    found = True
        for fn in skel.top_level_functions:
            if fn.name == symbol:
                print(f"  [module-level] {fn.signature}")
                if fn.docstring:
                    print(f"    # {fn.docstring}")
                found = True
    if not found:
        print(f"Symbol '{symbol}' not found.")


def _query_usages(skeletons: dict, symbol: str) -> None:  # type: ignore[type-arg]
    """Find every function/method that calls the given symbol (impact analysis)."""
    found = False
    for skel in skeletons.values():
        file_name = Path(skel.path).name
        hits: list[str] = []
        for cls in skel.classes:
            for fn in cls.methods:
                if any(symbol in call for call in fn.calls):
                    hits.append(f"  {cls.name}.{fn.name}  [line {fn.line_start}]")
        for fn in skel.top_level_functions:
            if any(symbol in call for call in fn.calls):
                hits.append(f"  {fn.name}  [line {fn.line_start}]")
        if hits:
            found = True
            print(f"\n{file_name}")
            for h in hits:
                print(h)
    if not found:
        print(f"No usages of '{symbol}' found.")


def _query_find(skeletons: dict, query: str) -> None:  # type: ignore[type-arg]
    q = query.lower()
    for skel in skeletons.values():
        file_name = Path(skel.path).name
        for cls in skel.classes:
            if q in cls.name.lower():
                print(f"  class {cls.name}  [{file_name}:{cls.line_start}]")
            for fn in cls.methods:
                if q in fn.name.lower():
                    print(f"  {cls.name}.{fn.name}  [{file_name}:{fn.line_start}]")
        for fn in skel.top_level_functions:
            if q in fn.name.lower():
                print(f"  def {fn.name}  [{file_name}:{fn.line_start}]")


def _query_file(skeletons: dict, file_query: str) -> None:  # type: ignore[type-arg]
    for skel in skeletons.values():
        if file_query in skel.path:
            _print_file_skeleton(skel)
            return
    print(f"No cached file matching '{file_query}'.")


def _query_list_files(skeletons: dict, query: str) -> None:  # type: ignore[type-arg]
    for skel in sorted(skeletons.values(), key=lambda s: s.path):
        if not _match_tool(skel, query):
            continue
        mod = skel.module_id or "—"
        print(f"  {Path(skel.path).name:<45} {mod}")


def _print_file_skeleton(skel: object) -> None:  # type: ignore[type-arg]
    from skeleton_extractor.extractor import FileSkeleton
    assert isinstance(skel, FileSkeleton)
    print(f"\n# {Path(skel.path).name}  [{skel.module_id or ''}]")
    if skel.imports:
        print("\n  ## imports")
        for imp in skel.imports:
            print(f"  {imp}")
    for cls in skel.classes:
        _print_class(cls)
    for fn in skel.top_level_functions:
        print(f"  {fn.signature}: ...")
        if fn.docstring:
            print(f"    # {fn.docstring}")
        if fn.calls:
            print(f"    # calls: {', '.join(sorted(set(fn.calls)))}")


def _print_class(cls: object) -> None:  # type: ignore[type-arg]
    from skeleton_extractor.extractor import ClassSkeleton
    assert isinstance(cls, ClassSkeleton)
    bases = f"({', '.join(cls.bases)})" if cls.bases else ""
    print(f"\nclass {cls.name}{bases}:")
    if cls.docstring:
        print(f'  """{cls.docstring}"""')
    for var in cls.class_vars:
        print(f"  {var}")
    for fn in cls.methods:
        prefix = "  "
        for dec in fn.decorators:
            print(f"{prefix}{dec}")
        print(f"{prefix}{fn.signature}: ...")
        if fn.docstring and not fn.is_private:
            print(f"{prefix}    # {fn.docstring}")
        if fn.calls and not fn.is_private:
            print(f"{prefix}    # calls: {', '.join(sorted(set(fn.calls)))}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skeleton_extractor",
        description="Skeleton extractor — parse Python sources into MODULE_MAP.json index files.",
    )
    sub = parser.add_subparsers(dest="command")

    # --- refresh (default) ---
    ref = sub.add_parser("refresh", help="Refresh cache and regenerate MODULE_MAP.json files")
    ref.add_argument("tool", nargs="?", help="Only refresh this tool (e.g. scr)")

    ref.add_argument("--debug", metavar="FILE", help="Debug: print skeleton for one file path")
    ref.add_argument("--stats", action="store_true", help="Print token savings stats")

    # --- query ---
    qry = sub.add_parser("query", help="Query the skeleton cache")
    qry.add_argument("--overview", metavar="TOOL", help="All classes + public methods for a tool")
    qry.add_argument("--class", dest="cls", metavar="CLASS", help="Full skeleton of one class")
    qry.add_argument("--symbol", metavar="NAME", help="Single method signature")
    qry.add_argument("--find", metavar="QUERY", help="Substring search across all symbols")
    qry.add_argument("--usages", metavar="SYMBOL", help="Find every function/method that calls SYMBOL")
    qry.add_argument("--file", metavar="PATH", help="All symbols in a specific file")
    qry.add_argument("--list-files", metavar="TOOL", help="List source files for a tool")

    args = parser.parse_args()

    if args.command == "query":
        _cmd_query(args)
    else:
        # default to refresh even without subcommand
        if args.command is None:
            args.tool = None
            args.debug = None
            args.stats = False
        _cmd_refresh(args)


if __name__ == "__main__":
    main()
