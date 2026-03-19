"""
Unit tests for the OPC UA Quality Analyzer.
Tests parser and metric engine against known NodeSet2 fixtures.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.nodeset_parser import parse
from src.metrics.metric_engine import compute

EXAMPLES = Path(__file__).parent.parent / "examples"


def get_example(name: str) -> str:
    path = EXAMPLES / name
    if not path.exists():
        pytest.skip(f"Example file not found: {name}")
    return str(path)


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestParser:
    def test_parse_lasersystems(self):
        path = get_example("Opc.Ua.LaserSystems.NodeSet2.xml")
        data = parse(path)
        assert len(data.objecttype_info) > 0, "Should find ObjectTypes"
        assert len(data.node_classes) > 0, "Should find nodes"

    def test_parse_machinetool(self):
        path = get_example("Opc.Ua.MachineTool.NodeSet2.xml")
        data = parse(path)
        assert len(data.objecttype_info) > 0
        assert len(data.parent_lookup) > 0, "Should find inheritance relations"

    def test_parse_adi(self):
        path = get_example("Opc.Ua.Adi.NodeSet2.xml")
        data = parse(path)
        assert data.n_method > 0, "ADI should have methods"

    def test_parse_returns_namespace(self):
        path = get_example("Opc.Ua.LaserSystems.NodeSet2.xml")
        data = parse(path)
        # All objecttype IDs should be strings
        for nid in data.objecttype_info:
            assert isinstance(nid, str)


# ── Metric engine tests ───────────────────────────────────────────────────────

class TestMetricEngine:
    def test_lasersystems_nclass(self):
        path = get_example("Opc.Ua.LaserSystems.NodeSet2.xml")
        result = compute(parse(path), filename="LaserSystems")
        # Thesis Table 5.1: NClass = 12
        assert result.global_metrics.NClass == 12

    def test_lasersystems_maxdit(self):
        path = get_example("Opc.Ua.LaserSystems.NodeSet2.xml")
        result = compute(parse(path))
        # Thesis: MaxDIT = 1 for LaserSystems
        assert result.global_metrics.MaxDIT == 1

    def test_lasersystems_no_methods(self):
        path = get_example("Opc.Ua.LaserSystems.NodeSet2.xml")
        result = compute(parse(path))
        # Thesis: NMet = 0
        assert result.global_metrics.NMet == 0

    def test_machinetool_nclass(self):
        path = get_example("Opc.Ua.MachineTool.NodeSet2.xml")
        result = compute(parse(path))
        # Thesis Table 5.11: NClass = 62
        assert result.global_metrics.NClass == 62

    def test_machinetool_maxdit(self):
        path = get_example("Opc.Ua.MachineTool.NodeSet2.xml")
        result = compute(parse(path))
        # Thesis: MaxDIT = 3
        assert result.global_metrics.MaxDIT == 3

    def test_adi_has_methods(self):
        path = get_example("Opc.Ua.Adi.NodeSet2.xml")
        result = compute(parse(path))
        # Thesis Table 5.8: NMet = 40
        assert result.global_metrics.NMet == 40

    def test_dit_non_negative(self):
        """DIT should never be negative."""
        for xml in EXAMPLES.glob("*.xml"):
            result = compute(parse(str(xml)))
            assert result.global_metrics.MaxDIT >= 0
            for t in result.object_types:
                assert t.DIT >= 0

    def test_noc_non_negative(self):
        """NOC should never be negative."""
        path = get_example("Opc.Ua.MachineTool.NodeSet2.xml")
        result = compute(parse(path))
        for t in result.object_types:
            assert t.NOC >= 0

    def test_wmc_non_negative(self):
        path = get_example("Opc.Ua.Adi.NodeSet2.xml")
        result = compute(parse(path))
        for t in result.object_types:
            assert t.WMC >= 0

    def test_filename_stored(self):
        path = get_example("Opc.Ua.LaserSystems.NodeSet2.xml")
        result = compute(parse(path), filename="test.xml")
        assert result.filename == "test.xml"

    def test_isa95_nclass(self):
        path = get_example("Opc.ISA95.NodeSet2.xml")
        result = compute(parse(path))
        # Thesis Table 5.3: NClass = 17
        assert result.global_metrics.NClass == 17

    def test_isa95_nvartype(self):
        path = get_example("Opc.ISA95.NodeSet2.xml")
        result = compute(parse(path))
        # Thesis Table 5.3: NVarType = 21
        assert result.global_metrics.NVarType == 21
