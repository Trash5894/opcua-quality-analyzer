"""
UML Metric Engine for OPC UA Models
Computes all metrics defined in thesis Chapter 4 (Tabellen 4.3 & 4.4).

Global metrics:  NClass, NVarType, NMet, NAttrTotal, MaxDIT,
                 NGenH, NAggH, NInst, NInstExternal
Per-type metrics: WMC, DIT, NOC, NAttr, NComp, NAgg, NAssoc, NInst
"""

from dataclasses import dataclass, field
from typing import Optional

from src.parser.nodeset_parser import ParsedNodeSet


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class TypeMetrics:
    """Metrics for a single ObjectType or VariableType."""
    node_id:    str = ""
    browse_name: str = ""
    type_kind:  str = ""   # "ObjectType" | "VariableType"
    WMC:   int = 0
    DIT:   int = 0
    NOC:   int = 0
    NAttr: int = 0
    NComp: int = 0
    NAgg:  int = 0
    NAssoc: int = 0
    NInst: int = 0


@dataclass
class GlobalMetrics:
    """System-wide metrics for the full NodeSet."""
    NClass:        int = 0
    NVarType:      int = 0
    NMet:          int = 0
    NAttrTotal:    int = 0
    MaxDIT:        int = 0
    NGenH:         int = 0
    NAggH:         int = 0
    NInst:         int = 0
    NInstExternal: int = 0


@dataclass
class MetricResult:
    """Full result of a metric computation run."""
    filename:       str = ""
    global_metrics: GlobalMetrics = field(default_factory=GlobalMetrics)
    object_types:   list[TypeMetrics] = field(default_factory=list)
    variable_types: list[TypeMetrics] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _collect_supertypes(node_id: str, parent_lookup: dict) -> list[str]:
    """Return ordered list of ancestor type IDs (nearest first)."""
    chain = []
    current = parent_lookup.get(node_id)
    while current:
        chain.append(current)
        current = parent_lookup.get(current)
    return chain


def _compute_dit(node_id: str, parent_lookup: dict) -> int:
    """Depth of Inheritance Tree – steps to root via HasSubtype."""
    depth = 0
    current = node_id
    while current in parent_lookup:
        current = parent_lookup[current]
        depth += 1
    return depth


def _count_wmc_nattr(start_id: str, references: dict,
                     node_classes: dict, visited: Optional[set] = None) -> tuple[int, int]:
    """
    Recursively count Method nodes (WMC) and Variable nodes (NAttr)
    reachable via HasComponent / HasProperty / HasAddIn.
    Matches thesis Figure 4.4 algorithm.
    """
    if visited is None:
        visited = set()
    if start_id in visited:
        return 0, 0
    visited.add(start_id)

    wmc = nattr = 0
    for ref_type, target_id in references.get(start_id, []):
        if ref_type in ("HasComponent", "HasProperty", "HasAddIn"):
            kind = node_classes.get(target_id, "")
            if kind == "UAMethod":
                wmc += 1
            elif kind == "UAVariable":
                nattr += 1
            sub_wmc, sub_nattr = _count_wmc_nattr(target_id, references, node_classes, visited)
            wmc  += sub_wmc
            nattr += sub_nattr
    return wmc, nattr


def _count_wmc_nattr_inherited(node_id: str, parent_lookup: dict,
                                references: dict, node_classes: dict) -> tuple[int, int]:
    """WMC and NAttr including inherited elements from all supertypes."""
    visited: set = set()
    wmc_total = nattr_total = 0
    for tid in [node_id] + _collect_supertypes(node_id, parent_lookup):
        w, n = _count_wmc_nattr(tid, references, node_classes, visited)
        wmc_total   += w
        nattr_total += n
    return wmc_total, nattr_total


def _count_hierarchy_roots(child_map: dict) -> int:
    """
    Count independent hierarchy roots.
    A root is a node that has children but is not itself a child of anyone.
    Used for NGenH and NAggH (thesis Section 4.4).
    """
    all_children = {c for children in child_map.values() for c in children}
    roots = [nid for nid in child_map
             if nid not in all_children and child_map[nid]]
    return len(roots)


# ── Main computation ──────────────────────────────────────────────────────────

def compute(data: ParsedNodeSet, filename: str = "") -> MetricResult:
    """
    Compute all metrics from a ParsedNodeSet and return a MetricResult.
    This is the single entry point for metric computation.
    """
    result = MetricResult(filename=filename)
    gm = result.global_metrics

    # ── Global counts ─────────────────────────────────────────────────────
    gm.NClass        = len(data.objecttype_info)
    gm.NVarType      = len(data.variabletype_info)
    gm.NMet          = data.n_method
    gm.NAttrTotal    = data.n_variable
    gm.NInst         = data.n_inst_internal
    gm.NInstExternal = data.n_inst_external

    # ── DIT per type + MaxDIT ─────────────────────────────────────────────
    dit_values = []

    def _build_type_metrics(type_info: dict, ref_counts: dict,
                            children_map: dict, kind: str) -> list[TypeMetrics]:
        metrics_list = []
        for node_id, browse_name in type_info.items():
            dit = _compute_dit(node_id, data.parent_lookup)
            dit_values.append(dit)
            wmc, nattr = _count_wmc_nattr_inherited(
                node_id, data.parent_lookup, data.references, data.node_classes)
            noc = len(children_map.get(node_id, []))
            rc  = ref_counts.get(node_id, {})
            tm  = TypeMetrics(
                node_id    = node_id,
                browse_name = browse_name,
                type_kind  = kind,
                WMC   = wmc,
                DIT   = dit,
                NOC   = noc,
                NAttr = nattr,
                NComp = rc.get("NComp", 0),
                NAgg  = rc.get("NAgg",  0),
                NAssoc= rc.get("NAssoc",0),
                NInst = data.inst_per_type.get(node_id, 0),
            )
            metrics_list.append(tm)
        return metrics_list

    result.object_types   = _build_type_metrics(
        data.objecttype_info,
        data.objecttype_ref_counts,
        data.objecttype_children,
        "ObjectType",
    )
    result.variable_types = _build_type_metrics(
        data.variabletype_info,
        data.variabletype_ref_counts,
        data.variabletype_children,
        "VariableType",
    )

    gm.MaxDIT = max(dit_values) if dit_values else 0
    gm.NGenH  = _count_hierarchy_roots(data.objecttype_children)
    gm.NAggH  = _count_hierarchy_roots(data.aggregation_children)

    return result
