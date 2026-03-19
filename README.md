# ⚙ OPC UA Quality Analyzer

> **Structural quality analysis of OPC UA NodeSet2 models via UML metrics**

OPC UA models are the backbone of industrial communication in Industry 4.0 — but how do you know if a model is well-structured? This tool makes that question answerable for the first time, by applying established software quality metrics from UML to OPC UA information models.

---

## Background

This tool is the practical implementation of the M.Sc. thesis:

> *"Quality Analysis of OPC UA Models by means of UML Metrics: A Conceptional Study"*
> Asif Sarfaraz Chaudhry — University of Stuttgart (ISW), 2025
> Supervisor: Prof. Dr.-Ing. Oliver Riedel

### The Problem

OPC UA Companion Specifications are written by domain experts — but there is no automated way to check whether a model follows the [OPC UA Modeling Best Practices](https://opcfoundation.org) or whether it has become overly complex over time. Reviews happen manually, if at all.

### The Idea

OPC UA information models share a structural similarity with UML class diagrams:

| OPC UA Concept | UML Equivalent |
|---|---|
| `ObjectType` | Class |
| `HasSubtype` | Inheritance |
| `HasProperty` | Aggregation |
| `HasComponent` | Composition |
| `Method` node | Method |
| `Variable` node | Attribute |

This similarity — formally established by **Lee et al. (2017)** — means that well-known UML quality metrics (Chidamber & Kemerer, Genero et al.) can be mapped onto OPC UA structures and computed directly from NodeSet2 XML files, **without converting the model to UML first**.

---

## What the Tool Does

1. **Parses** any OPC UA NodeSet2 `.xml` file
2. **Computes** structural quality metrics for the entire model and for each individual type
3. **Visualizes** results in an interactive dashboard with charts and tables
4. **Evaluates** the model against OPC UA Modeling Best Practices heuristics
5. **Exports** all results as CSV for further analysis

---

## Metrics Explained

### Global Metrics — the big picture

| Metric | What it measures | Why it matters |
|---|---|---|
| `NClass` | Number of `ObjectType` definitions | Overall model size |
| `NVarType` | Number of `VariableType` definitions | Structured data complexity |
| `NMet` | Total `Method` nodes in the model | Functional depth |
| `NAttrTotal` | Total `Variable` nodes | Attribute density |
| `MaxDIT` | Deepest inheritance chain (via `HasSubtype`) | Hierarchy depth — keep low |
| `NGenH` | Number of independent inheritance trees | Modularity of type hierarchy |
| `NAggH` | Number of independent aggregation trees | Modularity of composition |
| `NInst` | Object instances of internal types | How much types are reused |
| `NInstExternal` | Instances referencing external types | Cross-spec dependencies |

### Per-Type Metrics — per `ObjectType` or `VariableType`

| Metric | UML Origin | OPC UA Computation |
|---|---|---|
| `WMC` | Weighted Methods per Class | Count of `Method` nodes reachable via `HasComponent` / `HasProperty` (recursive, including inherited) |
| `DIT` | Depth of Inheritance Tree | Steps from this type to the root via `HasSubtype` (inverse direction) |
| `NOC` | Number of Children | Direct subtypes pointing to this type via `HasSubtype` |
| `NAttr` | Attributes | Count of `Variable` nodes reachable recursively via `HasComponent` / `HasProperty` |
| `NComp` | Compositions | `HasComponent` / `HasOrderedComponent` references to non-type nodes |
| `NAgg` | Aggregations | `HasProperty` references |
| `NAssoc` | Associations | `Organizes`, `HasNotifier`, `HasEventSource` references |
| `NInst` | Instance count | Number of `Object` nodes pointing to this type via `HasTypeDefinition` |

### Heuristic Interpretation

No absolute thresholds exist in the OPC UA literature — the thesis identifies this as an open research problem. The dashboard therefore uses **relative, heuristic** evaluation aligned with the OPC UA Modeling Best Practices Whitepaper (v1.03.01, 2025):

| Principle | Relevant Metrics | Signal |
|---|---|---|
| Keep inheritance shallow | `MaxDIT`, `DIT` | High values → harder to maintain |
| Prefer composition over inheritance | `NAggH` vs `NGenH` | More aggregation hierarchies = better |
| Limit complexity & granularity | `WMC`, `NAttr` | Very high values per type = overloaded |
| Reuse types only when warranted | `NClass`, `NInst` | Many types with zero instances = dead weight |
| Use standardized reference types | `NAgg`, `NComp`, `NAssoc` | High `NAssoc` = tight coupling |

---

## Installation & Quickstart

### Requirements

- Python 3.11+
- Works on Windows, macOS, Linux

### Install

```bash
pip install lxml pandas streamlit plotly
```

### Run the Dashboard

```bash
streamlit run src/dashboard/app.py
```

Your browser opens at `http://localhost:8501` automatically.

- Select **"Use example"** to load one of the bundled Companion Specifications
- Or upload your own NodeSet2 `.xml` file
- Click **▶ Analyze**

### Run via CLI

```bash
# Print metrics to console
python src/cli.py examples/Opc.Ua.MachineTool.NodeSet2.xml

# Export as CSV
python src/cli.py examples/Opc.Ua.Adi.NodeSet2.xml --csv --out results/
```

### Run with Docker

```bash
docker build -t opcua-analyzer .
docker run -p 8501:8501 opcua-analyzer
# Open http://localhost:8501
```

---

## Project Structure

```
opcua-quality-analyzer/
│
├── src/
│   ├── parser/
│   │   └── nodeset_parser.py     # Parses NodeSet2 XML into internal data structures
│   ├── metrics/
│   │   └── metric_engine.py      # Computes all metrics from parsed data
│   ├── dashboard/
│   │   └── app.py                # Streamlit web dashboard
│   └── cli.py                    # Command-line interface
│
├── tests/
│   └── test_metrics.py           # Unit tests validated against thesis results
│
├── examples/                     # Bundled OPC UA Companion Specifications
│   ├── Opc.Ua.MachineTool.NodeSet2.xml
│   ├── Opc.Ua.Adi.NodeSet2.xml
│   ├── Opc.Ua.LaserSystems.NodeSet2.xml
│   ├── Opc.Ua.AdditiveManufacturing.Nodeset2.xml
│   └── Opc.ISA95.NodeSet2.xml
│
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11 | Core implementation |
| XML Parsing | `lxml` | Fast, standards-compliant NodeSet2 parsing |
| Data Processing | `pandas` | Metric aggregation and CSV export |
| Dashboard | `Streamlit` | Interactive web UI without frontend boilerplate |
| Charts | `Plotly` | Interactive bar charts, scatter plots, radar charts |
| Packaging | `pyproject.toml` | Modern Python packaging (PEP 517) |
| CI/CD | GitHub Actions | Automatic test runs on every push |
| Containerization | Docker | One-command deployment |
| Testing | `pytest` | Unit tests validated against thesis ground truth |

---

## Validated Results

The metric engine is validated against the manually verified results from the thesis (Chapter 5):

| NodeSet | Metric | Thesis Value | Tool Output |
|---|---|---|---|
| LaserSystems | NClass | 12 | 12 ✅ |
| LaserSystems | MaxDIT | 1 | 1 ✅ |
| MachineTool | NClass | 62 | 62 ✅ |
| MachineTool | MaxDIT | 3 | 3 ✅ |
| ADI | NClass | 30 | 30 ✅ |
| ADI | MaxDIT | 2 | 2 ✅ |
| ISA-95 | NClass | 17 | 17 ✅ |
| ISA-95 | NVarType | 21 | 21 ✅ |

---

## Run Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Limitations & Future Work

- **No normative thresholds** — heuristic evaluation only. Empirical determination of thresholds from a large corpus of NodeSets is the key next research step.
- **Single-file analysis** — many Companion Specifications consist of multiple NodeSet files. Multi-file support is planned.
- **Custom reference types** — domain-specific references (e.g. in ISA-95) are not captured by the standard UML mapping and may underestimate complexity.
- **DataType nodes** — not covered by the current metric set.

---

## References

- Chidamber, S. R. & Kemerer, C. F. (1993). *A Metrics Suite for Object Oriented Design.*
- Genero, M., Piattini, M. & Calero, C. (2005). *A survey of metrics for UML class diagrams.* Journal of Object Technology.
- Lee, B. et al. (2017). *Model transformation between OPC UA and UML.* Computer Standards & Interfaces.
- OPC Foundation (2025). *UA Modeling Best Practices*, v1.03.01.

---

## License

MIT — free to use, modify and distribute.
