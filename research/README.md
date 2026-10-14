# SmartWake: Empirical Analysis of a Smartphone Accelerometer-Based Sleep Onset and Ultradian Smart Alarm Engine

This directory contains the complete, reproducible academic research package, empirical code, benchmarks, figures, and LaTeX manuscript for the paper:

> *Author:* **Samarth Singh**, BSc (Hons) Data Science and Artificial Intelligence  
> *Affiliation:* Department of Data Science, School of Sciences, CHRIST (Deemed to be University), Delhi NCR, India  
> *Compiled Manuscript:* [`research/paper/main.pdf`](paper/main.pdf) (25 pages, IEEE Journal format, 9,660 words)

---

## 1. Directory Structure

```
research/
├── README.md                     # This reproduction guide
├── VERIFICATION.md               # Complete metrics & CrossRef citation audit table
├── LOG.md                        # Chronological research and engineering decisions log
├── REPO_AUDIT.md                 # Forensic line-by-line audit of SmartWake codebase
├── PAPER_SCOPE.md                # Formal research questions (RQ1-RQ4) and scope
├── DATA_COLLECTION_PROTOCOL.md   # Tier A prospective human subjects protocol
├── requirements.txt              # Pinned Python dependencies
├── scraper.py                    # ScraperAPI utility with academic fallback
├── build_literature.py           # Verification script for 39 real CrossRef citations
├── eda.py                        # Exploratory data analysis generating Figures 1-5
├── run_experiments.py            # Complete benchmarking suite (LOSO, baselines, SHAP, latency)
├── synthetic_generator.py        # Tier B physiologically-grounded synthetic generator
├── adapters/                     # Dataset adapters (download_slices.py for Tier C PSG)
├── data/
│   ├── DATA_CARD.md              # Data provenance, dimensions, and tier partitions
│   ├── raw/                      # Raw sensor telemetry
│   └── processed/                # Processed 9-feature tabular arrays
├── figures/                      # High-resolution PNG figures (Figures 0-11)
├── results/                      # Output CSV metrics, ablations, latency, and saved models
└── paper/
    ├── main.tex                  # Complete 25-page LaTeX manuscript
    ├── main.pdf                  # Compiled PDF
    ├── references.bib            # 39 verified BibTeX references
    └── figures/                  # Staged figures embedded in paper
```

---

## 2. Experimental Reproduction in 4 Steps

All experiments are deterministic and seeded with `SEED = 42`.

### Step 1: Set Up Python Environment
Ensure Python 3.10+ is installed. Activate the sandboxed virtual environment:
```bash
python3 -m venv research/venv
source research/venv/bin/activate
pip install -r research/requirements.txt
```

### Step 2: Run Exploratory Data Analysis (Figures 1–5)
Generate raw sensor plots, feature distributions, correlation heatmaps, and longitudinal raster dynamics:
```bash
python research/eda.py
```
*Outputs:* `research/figures/fig1` through `fig5` and `research/results/descriptive_statistics.csv`.

### Step 3: Run Full Benchmark Harness (Figures 6–11, Tables I–V)
Execute the Leave-One-Subject-Out cross-validation across all 6 models, run feature ablations, TreeSHAP interpretability, and FastAPI latency micro-benchmarks:
```bash
python research/run_experiments.py
```
*Outputs:* 
- `research/results/metrics.csv`
- `research/results/ablations.csv`
- `research/results/shap_importance.csv`
- `research/results/backend_latency.csv`
- Serialized models in `research/results/models/`
- `research/figures/fig6` through `fig11`

### Step 4: Compile the Research Paper
Compile `main.tex` into `main.pdf` using Tectonic or XeLaTeX:
```bash
cd research/paper
tectonic main.tex
```
*Verification:* Inspect `main.pdf` to confirm it compiles cleanly to exactly 25 pages.

---

## 3. Key Findings

1. **Operational Reality:** SmartWake's model is a **sleep onset detector**, not a real-time EEG sleep-stage decoder. Morning light-sleep arousal is determined by a **90-minute ultradian backward step** from detected sleep onset.
2. **Predictive Performance:** The repository's `GradientBoostingClassifier` achieves a balanced accuracy of **0.8625** (95% CI: [0.8418, 0.8817]), an F1-score of **0.9751** (95% CI: [0.9723, 0.9778]), and a PR-AUC of **0.9861** under strict subject-independent LOSO cross-validation.
3. **Data Leakage Proof:** Random epoch splitting inflates ROC-AUC to **0.9278** and PR-AUC to **0.9936**, proving that non-subject-independent validation introduces significant autocorrelation leakage.
4. **Circadian Dominance:** TreeSHAP reveals that trigonometric time encodings (`hour_sin`, `hour_cos`) account for **87.3%** of all tree split decisions. Ablating circadian features maintains an F1 of **0.9727**, demonstrating that mattress kinematics alone provide strong discriminatory signal.
5. **Backend Scalability:** Local micro-benchmarking confirms median FastAPI request latency of **0.85 ms** ($p_{95}=1.26$ ms, $p_{99}=2.52$ ms), adding negligible overhead to alarm dispatch.
