# RepoRisk — Python Repository Risk Analyzer

RepoRisk is a Python-based repository health analyzer that examines a codebase from multiple engineering perspectives and produces a structured risk assessment.

It combines static source analysis, Git history, dependency relationships, test coverage signals, complexity metrics, and change frequency to identify files and modules that may require additional engineering attention.

## Features

* Python repository scanning
* AST-based source analysis
* Code complexity estimation
* Lines-of-code analysis
* Function and class analysis
* Syntax-error detection
* Git commit history analysis
* Git churn analysis
* Change hotspot detection
* Import dependency graph
* Reverse dependency analysis
* Dependency impact propagation
* Test-file detection
* File-level risk scoring
* Repository-level risk scoring
* High-risk hotspot ranking
* JSON report generation
* Text report generation
* Built-in self-test
* Standard-library-only implementation

## Tech Stack

**Python | AST | Git | Graph Algorithms | Static Analysis | Data Structures & Algorithms | JSON**

## DSA Used

RepoRisk uses practical data structures and algorithms throughout the analysis engine:

* **Hash Maps** for file, metric, and dependency indexing
* **Sets** for unique files, imports, and relationships
* **Graphs** for module dependency analysis
* **BFS** for dependency-impact propagation
* **Deque** for graph traversal
* **Sorting** for risk and hotspot ranking
* **Counters** for change-frequency analysis

## Architecture

```text id="v9uxkh"
Repository
    ↓
File Discovery
    ↓
Python Source Analysis
    ↓
AST Parsing
    ↓
Complexity Metrics
    ↓
Import Graph
    ↓
Git History
    ↓
Churn Analysis
    ↓
Test Detection
    ↓
Risk Scoring
    ↓
Hotspot Ranking
    ↓
Repository Report
```

## Analysis Pipeline

RepoRisk evaluates a repository through several independent signals.

### Static Source Analysis

The analyzer inspects Python source files and extracts information such as:

```text id="7c2y7s"
lines of code
functions
classes
branches
loops
conditions
imports
syntax errors
```

AST parsing allows RepoRisk to inspect the structure of Python programs without executing them.

### Complexity Analysis

RepoRisk estimates structural complexity by examining control-flow constructs such as:

```text id="s7w4te"
if
elif
for
while
try
except
with
boolean conditions
```

Higher complexity can contribute to a higher file-level risk score.

### Git Churn Analysis

Git history is used to identify files that change frequently.

Typical signals include:

```text id="8x0v5y"
commit count
added lines
deleted lines
total changes
recent changes
```

Files with high change frequency and high complexity can become important engineering hotspots.

### Dependency Analysis

RepoRisk constructs a directed dependency graph from Python imports.

Example:

```text id="d5a7h7"
api.py
  ↓
service.py
  ↓
database.py
```

Reverse relationships are also calculated to determine which modules depend on a particular file.

### Impact Analysis

When a frequently changed module is modified, RepoRisk can propagate its dependency relationships through the graph to estimate potential impact.

Example:

```text id="4u1i5f"
database.py
     ↓
service.py
     ↓
api.py
     ↓
tests/
```

This helps identify files that may deserve additional review after structural changes.

## Risk Scoring

RepoRisk combines multiple signals into a repository-health score.

Example contributing factors:

```text id="rfy9vy"
Complexity
Code Size
Git Churn
Dependency Coupling
Test Presence
Syntax Errors
Impact
```

The result is summarized as a repository risk level.

Example:

```text id="n7n6f3"
Risk Score: 16.72
Risk Level: LOW
```

## Self-Test

RepoRisk contains a built-in demonstration and validation suite.

Run:

```bash id="zj5tq3"
python repo_risk.py
```

or:

```bash id="ncqvvd"
python repo_risk.py --self-test
```

Example output:

```text id="shw2fb"
REPORISK SELF-TEST: PASS
Files: 4
Commits: 2
Risk Score: 16.72
Risk Level: LOW
Hotspots: 4
```

## Analyze a Repository

Run RepoRisk against any local Python project:

```bash id="2glcd8"
python repo_risk.py "C:\Users\YourName\Desktop\MyProject"
```

Linux or macOS:

```bash id="4r2f2o"
python repo_risk.py /path/to/project
```

## Generate Reports

JSON report:

```bash id="p0v6e1"
python repo_risk.py "C:\Projects\MyProject" --json report.json
```

Text report:

```bash id="2nq8kj"
python repo_risk.py "C:\Projects\MyProject" --text report.txt
```

Both:

```bash id="z0ic7g"
python repo_risk.py "C:\Projects\MyProject" --json report.json --text report.txt
```

## Example Findings

A report can identify areas such as:

```text id="0i9wa9"
High Complexity
High Churn
Dependency Hotspot
Missing Tests
Syntax Error
High Impact
```

This allows developers to prioritize investigation rather than manually reviewing every source file.

## Example Workflow

```text id="ru5izn"
Python Repository
       ↓
Discover Files
       ↓
Parse AST
       ↓
Calculate Complexity
       ↓
Build Dependency Graph
       ↓
Read Git History
       ↓
Calculate Churn
       ↓
Detect Tests
       ↓
Calculate Risk
       ↓
Rank Hotspots
       ↓
Generate Report
```

## Project Structure

```text id="qkzj5n"
repo-risk/
├── repo_risk.py
├── README.md
├── report.json
└── report.txt
```

## Use Cases

RepoRisk can be used for:

* Software-maintenance analysis
* Technical-debt discovery
* Codebase health assessment
* Refactoring prioritization
* Pull-request review preparation
* Architecture analysis
* Dependency-risk analysis
* Legacy Python code assessment
* Engineering onboarding
* Repository portfolio analysis

## Why RepoRisk?

Traditional static analyzers usually focus on isolated code-quality rules.

RepoRisk combines several dimensions:

```text id="w6w0g8"
Source Structure
+
Complexity
+
Git History
+
Dependency Graph
+
Test Signals
+
Change Frequency
```

The result is a broader engineering view of where a repository may be difficult to maintain or where changes could have wider impact.

## Limitations

RepoRisk is a lightweight engineering analysis tool rather than a replacement for enterprise code-quality platforms.

Risk scores are heuristic indicators rather than absolute measurements of software quality.

The analyzer is currently focused primarily on Python repositories and local Git history.

## Future Improvements

Potential extensions include:

* Multi-language repository support
* Real cyclomatic-complexity calculation
* Coverage-file integration
* Pull-request analysis
* GitHub/GitLab integration
* Historical risk trends
* Interactive dependency graphs
* Architecture visualization
* Duplicate-code detection
* Technical-debt tracking
* CI/CD integration
* Automated refactoring suggestions

