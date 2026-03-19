"""
Command-line interface for OPC UA Quality Analyzer.
Usage: opcua-analyze <nodeset.xml> [--csv]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.parser.nodeset_parser import parse
from src.metrics.metric_engine import compute


def main():
    parser = argparse.ArgumentParser(
        prog="opcua-analyze",
        description="Compute UML quality metrics for an OPC UA NodeSet2 file.",
    )
    parser.add_argument("file", help="Path to NodeSet2 XML file")
    parser.add_argument("--csv", action="store_true",
                        help="Export results as CSV files")
    parser.add_argument("--out", default="output",
                        help="Output directory for CSV export (default: ./output)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    print(f"\nAnalyzing: {path.name}")
    print("─" * 60)

    data   = parse(str(path))
    result = compute(data, filename=path.name)
    gm     = result.global_metrics

    # ── Global metrics ────────────────────────────────────────────────────
    print("\n=== Global Metrics ===")
    rows = [
        ("NClass",        gm.NClass),
        ("NVarType",      gm.NVarType),
        ("NMet",          gm.NMet),
        ("NAttrTotal",    gm.NAttrTotal),
        ("MaxDIT",        gm.MaxDIT),
        ("NGenH",         gm.NGenH),
        ("NAggH",         gm.NAggH),
        ("NInst",         gm.NInst),
        ("NInstExternal", gm.NInstExternal),
    ]
    col_w = max(len(r[0]) for r in rows) + 2
    for name, val in rows:
        print(f"  {name:<{col_w}} {val}")

    # ── ObjectTypes ───────────────────────────────────────────────────────
    if result.object_types:
        print("\n=== ObjectType Metrics ===")
        header = f"{'BrowseName':<45} {'WMC':>4} {'DIT':>4} {'NOC':>4} {'NAttr':>6} {'NComp':>6} {'NAgg':>5} {'NInst':>6}"
        print(header)
        print("─" * len(header))
        for t in sorted(result.object_types, key=lambda x: x.NAttr, reverse=True):
            name = t.browse_name.split(":")[-1][:44]
            print(f"  {name:<43} {t.WMC:>4} {t.DIT:>4} {t.NOC:>4} {t.NAttr:>6} {t.NComp:>6} {t.NAgg:>5} {t.NInst:>6}")

    # ── VariableTypes ─────────────────────────────────────────────────────
    if result.variable_types:
        print("\n=== VariableType Metrics ===")
        for t in result.variable_types:
            name = t.browse_name.split(":")[-1][:44]
            print(f"  {name:<43} DIT={t.DIT} NAttr={t.NAttr} NAgg={t.NAgg}")

    # ── CSV export ────────────────────────────────────────────────────────
    if args.csv:
        import pandas as pd
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        stem = path.stem

        pd.DataFrame(rows, columns=["Metric", "Value"]).to_csv(
            out / f"{stem}_global.csv", index=False)
        pd.DataFrame([t.__dict__ for t in result.object_types]).to_csv(
            out / f"{stem}_objecttypes.csv", index=False)
        pd.DataFrame([t.__dict__ for t in result.variable_types]).to_csv(
            out / f"{stem}_variabletypes.csv", index=False)
        print(f"\nCSV files written to: {out}/")

    print("\n✓ Done")


if __name__ == "__main__":
    main()
