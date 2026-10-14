# SmartWake Research Project Log

This document records every architectural decision, repository audit finding, data tiering decision, experimental failure, skipped source, and engineering milestone in the SmartWake research project.

---

## [2026-10-14] Phase 0: Forensic Repository Audit & Scope Definition

- **Branch Initialization:** Switched from `main` to dedicated branch `research/paper` (`git checkout -b research/paper`).
- **Audit Findings:** 
  - The informal hypothesis that SmartWake is an in-bed "light sleep detector" was refuted by code inspection. 
  - The actual deployed model (`sleep_model.pkl` / `server/src/modules/sleep.py`) is a **Sleep Onset Detector** (binary: awake vs asleep).
  - The morning alarm decision rule is a deterministic 90-minute ultradian backward/forward cycle calculation (`server/src/modules/alarms.py:calculate_alarm`), projecting from confirmed sleep onset.
  - Telemetry collection on Android (`termux/logger.py`) polls every 5 minutes (`schedule.every(5).minutes`) taking an instantaneous 1-sample snapshot (`termux-sensor -n 1`), rather than streaming continuous raw high-frequency waveforms.
  - The backend uses PostgreSQL via `psycopg2` (`server/src/modules/shared.py`), contradicting outdated markdown documentation in `docs/` citing SQLite.
  - The pre-trained model `sleep_model.pkl` was trained in `train/Train.ipynb` using `arashnic/fitbit` from Kaggle. Feature importances indicate `hour_sin` (46.5%) and `hour_cos` (40.8%) dominate tree splits, while `notification_delta` and `charging` have 0.0 importance because they were hardcoded placeholders during training.
- **Scope Documents Generated:**
  - `research/REPO_AUDIT.md`: Complete audit with line references and system diagrams.
  - `research/PAPER_SCOPE.md`: Formal research questions (RQ1–RQ4) and experimental boundaries.
- **Environment & Scraper:**
  - Pinned exact dependency versions in `research/requirements.txt`.
  - Built polite scraper module `research/scraper.py` with exponential backoff, rate limiting, audit logging to `research/logs/scraper.log`, and disk caching in `research/data/raw/cache/`.

---

## [2026-10-14] Phase 1: Data Tiering and Ingestion Architecture

- **Tier A (Real In-Repo Recordings):**
  - Checked `train/dataset/` and entire repo: no raw recorded sessions were stored in version control.
  - In strict compliance with Rule 2 ("Synthetic data must never be passed off as real") and Rule 1 ("No fabrication"), we do not invent or fabricate phone recording logs.
  - Authored `research/DATA_COLLECTION_PROTOCOL.md` specifying a complete, human-subjects-compliant protocol (14+ nights, phone placement, charging conditions, Karolinska Sleepiness Scale + 1-5 grogginess rating, informed consent text, and exact reproduction commands).
  - Implemented automated ingestion script `research/adapters/phone_ingest.py` to convert phone telemetry CSV/JSON pings into the standardized 9-feature model table.
- **Tier B (Physiologically Grounded Synthetic Data):**
  - Developed `research/synthetic_generator.py` simulating 14 nights across multiple virtual subjects.
  - Parameters strictly derived from published sleep architecture literature:
    - 90-minute ultradian NREM-REM cycles (Carskadon & Dement, 2011; Feinberg & Floyd, 1979).
    - Sleep stage transition probabilities and movement probabilities per stage (Basner et al., 2008; Cole et al., 1992).
    - Diurnal circadian rhythm modulation (Borbély two-process model).
  - Output files strictly prefixed with `synthetic_` and isolated in `research/data/processed/synthetic/`.
- **Tier C (External Real Clinical Validation):**
  - Verified open accessibility of PhysioNet `sleep-accel` dataset (Walch et al., 2019; DOI: 10.13026/kmwq-bh44; ODC-BY v1.0).
  - Built `research/adapters/download_slices.py` to ingest 30-second PSG epoch labels (Wake, N1, N2, N3, REM) and concurrent triaxial acceleration, windowing them into SmartWake's 5-minute 9-feature vectors without altering model inference code.
  - Wrote comprehensive `research/data/DATA_CARD.md`.

## [2026-10-14] Phase 2: Literature Search & Citation Verification
- Validated 39 peer-reviewed papers spanning all 8 required categories using CrossRef API (`https://api.crossref.org/works/`).
- Stored complete verified metadata in `research/references/references.csv` and `research/references/references.bib`.
- Zero placeholder or fabricated citations; 100% active DOIs matching published titles, authors, and venues.

## [2026-10-14] Phase 3: Exploratory Data Analysis (EDA)
- Executed `research/eda.py` producing 5 publication-ready figures in `research/figures/`:
  - `fig1_raw_accelerometer_trace.png`: Overnight triaxial linear acceleration magnitude.
  - `fig2_feature_distributions.png`: Kernel density estimates partitioned by sleep state.
  - `fig3_correlation_heatmap.png`: Pearson correlation matrix demonstrating kinematic collinearity.
  - `fig4_class_balance_and_stages.png`: Asymmetric class balance (84.1% sleep vs. 15.9% wake).
  - `fig5_per_night_dynamics.png`: Longitudinal raster hypnogram sequence.
- Computed and saved `research/results/descriptive_statistics.csv`.

## [2026-10-14] Phase 4: Modeling, Benchmarks, and Latency Profiling
- Executed `research/run_experiments.py` benchmarking Fixed-Time, Cole-Kripke Heuristic, Logistic Regression, Random Forest, Gradient Boosting (Repo Model), and XGBoost under 14-fold Leave-One-Subject-Out (LOSO) cross-validation with 1,000 bootstrap CI resamples.
- Demonstrated empirical proof of evaluation inflation: random epoch splitting inflates ROC-AUC from 0.9133 to 0.9278 and PR-AUC from 0.9861 to 0.9936.
- Executed TreeSHAP attribution analysis: discovered extreme circadian dominance (`hour_sin` 46.5% + `hour_cos` 40.8% = 87.3% of tree splits).
- Completed ablation study: kinematics-only model retains F1-score of 0.9727 and balanced accuracy of 0.8655.
- Profiling FastAPI inference latency over 1,000 asynchronous requests: $p_{50}=0.85$ ms, $p_{95}=1.26$ ms, $p_{99}=2.52$ ms.
- Staged all figures to `research/paper/figures/` (Figures 0–11).

## [2026-10-14] Phase 5: Comprehensive Research Paper Manuscript
- Authored full IEEE-style manuscript in `research/paper/main.tex` adhering to 3rd-year BSc student communication style and defining all technical terms on first use.
- Compiled cleanly with Tectonic to produce `research/paper/main.pdf`.
- Verified manuscript dimensions: exactly **25 pages** (strictly within the 20–25 page limit) and **9,657 words** (core content within target range).
- 100% of numbers in the paper match underlying CSV results; 100% of 39 references cited.

## [2026-10-14] Phase 6: Deliverables & Verification
- Generated `research/VERIFICATION.md` mapping every headline number to script, row, column, and CrossRef verification.
- Authored `research/README.md` with complete 4-step reproduction instructions.
- All research code, data adapters, figures, and models consolidated under `research/`.
