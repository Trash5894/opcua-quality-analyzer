"""
OPC UA NodeSet2 XML Parser
Parses NodeSet2 XML files and extracts nodes, references and type hierarchies.
Based on OPC UA Part 6 NodeSet2 specification.
"""

from lxml import etree
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

OPC_UA_NS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
NS = {"ua": OPC_UA_NS}

# Reference type categories based on Lee et al. mapping (Thesis Table 4.2)
GENERALIZATION_REFS = {"HasSubtype"}
AGGREGATION_REFS    = {"HasProperty"}
COMPOSITION_REFS    = {"HasComponent", "HasOrderedComponent"}
ASSOCIATION_REFS    = {"Organizes", "HasNotifier", "HasEventSource",
                       "GeneratesEvent", "HasEncoding", "HasModellingRule",
                       "HasTypeDefinition"}


@dataclass
class ParsedNodeSet:
    """All data extracted from a NodeSet2 XML file."""
    # Maps node_id -> BrowseName
    objecttype_info:    dict = field(default_factory=dict)
    variabletype_info:  dict = field(default_factory=dict)

    # Maps node_id -> tag (UAObjectType, UAVariable, UAMethod, ...)
    node_classes: dict = field(default_factory=dict)

    # Maps node_id -> list of (ref_type, target_id) for forward references
    references: dict = field(default_factory=lambda: defaultdict(list))

    # Maps parent_id -> [child_id, ...] via HasSubtype
    objecttype_children:  dict = field(default_factory=lambda: defaultdict(list))
    variabletype_children: dict = field(default_factory=lambda: defaultdict(list))

    # Maps node_id -> parent_id via HasSubtype (inverse)
    parent_lookup: dict = field(default_factory=dict)

    # Maps node_id -> [child_id, ...] via HasProperty
    aggregation_children: dict = field(default_factory=lambda: defaultdict(list))

    # Global counters
    n_variable:       int = 0
    n_method:         int = 0
    n_inst_internal:  int = 0
    n_inst_external:  int = 0

    # Maps type_id -> instance count
    inst_per_type: dict = field(default_factory=lambda: defaultdict(int))

    # Raw per-type reference counts (NAgg, NComp, NAssoc)
    objecttype_ref_counts:  dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    variabletype_ref_counts: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))


def parse(xml_path: str) -> ParsedNodeSet:
    """Parse a NodeSet2 XML file and return a ParsedNodeSet."""
    tree = etree.parse(xml_path)
    root = tree.getroot()
    data = ParsedNodeSet()

    # ── First pass: collect all node IDs and tags ──────────────────────────
    for node in root:
        tag     = etree.QName(node).localname
        node_id = node.attrib.get("NodeId")
        if not node_id:
            continue
        data.node_classes[node_id] = tag

        if tag == "UAObjectType":
            data.objecttype_info[node_id] = node.attrib.get("BrowseName", "")
        elif tag == "UAVariableType":
            data.variabletype_info[node_id] = node.attrib.get("BrowseName", "")

    # ── Second pass: process references ────────────────────────────────────
    for node in root:
        tag     = etree.QName(node).localname
        node_id = node.attrib.get("NodeId")
        if not node_id:
            continue

        for ref in node.findall("ua:References/ua:Reference", namespaces=NS):
            ref_type  = ref.attrib.get("ReferenceType", "")
            target_id = (ref.text or "").strip()
            is_forward = ref.attrib.get("IsForward", "true").lower() != "false"

            # Collect all forward references for recursive WMC/NAttr
            if is_forward:
                data.references[node_id].append((ref_type, target_id))

            # ── ObjectType ────────────────────────────────────────────────
            if tag == "UAObjectType":
                if ref_type in GENERALIZATION_REFS and not is_forward:
                    data.parent_lookup[node_id] = target_id
                    data.objecttype_children[target_id].append(node_id)
                elif ref_type in AGGREGATION_REFS and is_forward:
                    data.objecttype_ref_counts[node_id]["NAgg"] += 1
                    data.aggregation_children[node_id].append(target_id)
                elif ref_type in ASSOCIATION_REFS and is_forward:
                    data.objecttype_ref_counts[node_id]["NAssoc"] += 1
                elif ref_type in COMPOSITION_REFS and is_forward:
                    if target_id not in data.objecttype_info and target_id not in data.variabletype_info:
                        data.objecttype_ref_counts[node_id]["NComp"] += 1

            # ── VariableType ──────────────────────────────────────────────
            elif tag == "UAVariableType":
                if ref_type in GENERALIZATION_REFS and not is_forward:
                    data.parent_lookup[node_id] = target_id
                    data.variabletype_children[target_id].append(node_id)
                elif ref_type in AGGREGATION_REFS and is_forward:
                    data.variabletype_ref_counts[node_id]["NAgg"] += 1
                    data.aggregation_children[node_id].append(target_id)
                elif ref_type in ASSOCIATION_REFS and is_forward:
                    data.variabletype_ref_counts[node_id]["NAssoc"] += 1
                elif ref_type in COMPOSITION_REFS and is_forward:
                    if target_id not in data.objecttype_info and target_id not in data.variabletype_info:
                        data.variabletype_ref_counts[node_id]["NComp"] += 1

            # ── UAVariable / UAMethod ─────────────────────────────────────
            elif tag == "UAVariable":
                data.n_variable += 1
            elif tag == "UAMethod":
                data.n_method += 1

            # ── UAObject (instances) ──────────────────────────────────────
            elif tag == "UAObject":
                if ref_type == "HasTypeDefinition" and is_forward:
                    if target_id in data.objecttype_info or target_id in data.variabletype_info:
                        data.n_inst_internal += 1
                        data.inst_per_type[target_id] += 1
                    else:
                        data.n_inst_external += 1

    return data
