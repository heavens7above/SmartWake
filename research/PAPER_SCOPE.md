# SmartWake Research Paper Scope & Formal Research Questions

**Document Status:** Approved & Locked for Empirical Execution  
**Project:** SmartWake: Empirical Analysis of a Smartphone Accelerometer-Based Sleep Onset and Ultradian Smart Alarm Engine  

---

## 1. Scope Formulation & Context

Based on the forensic audit conducted in `research/REPO_AUDIT.md`, this research project rigorously grounds all academic claims in the verified code and operational architecture of the SmartWake codebase. 

The paper refrains from making unverified medical assertions (such as claiming direct real-time polysomnographic EEG sleep-stage decoding from a bedside smartphone). Instead, it examines SmartWake for what it truly is: **a multi-modal telemetry ingestion and Gradient Boosting framework designed to detect sleep onset from smartphone accelerometer and ambient state features, paired with an ultradian 90-minute cycle projection engine for sleep inertia mitigation.**

---

## 2. Formal Research Questions (RQs)

### RQ1: Sleep Onset Classification Performance & Cross-Subject Generalization
* **Question:** What is the classification efficacy (Balanced Accuracy, PR-AUC, F1-score, and Matthews Correlation Coefficient) of the repository's 9-feature `GradientBoostingClassifier` for sleep/wake discrimination, and how significantly do performance metrics degrade when moving from random epoch shuffling to strict subject-independent (Leave-One-Subject-Out / Group-Shuffle) cross-validation?
* **Baselines for Comparison:**
  1. Static Fixed-Threshold Classifier
  2. Actigraphic Heuristic Rule (Cole-Kripke formulation adapted to windowed acceleration)
  3. Logistic Regression (Linear baseline with balanced weighting)
  4. Random Forest Classifier (100 estimators, balanced class weights)
  5. Repository Model: `GradientBoostingClassifier` ($n=200, d=4, \eta=0.1$)
  6. Extreme Gradient Boosting (`XGBoost`)
  7. Light Gradient Boosting Machine (`LightGBM`)

### RQ2: Feature Attribution, Circadian Dominance, and Ablation
* **Question:** How do individual feature groups (circadian trigonometric encodings vs. kinematic acceleration moments vs. device state indicators) contribute to the model's decision boundary under TreeSHAP and permutation feature importance? Specifically, does the model's empirical reliance on circadian priors ($\sim 87\%$ of tree splits) degrade performance during atypical sleep schedules?
* **Ablations to Execute:**
  - Full 9-feature model vs. kinematics-only (excluding `hour_sin` and `hour_cos`)
  - Circadian-only model (excluding all accelerometer features)
  - Window length variations (3-min, 5-min, 10-min aggregations)

### RQ3: Alarm Decision Mechanics & Ground-Truth Clinical Validation (Tier C)
* **Question:** When simulated across clinical sleep recordings with ground-truth polysomnography (PhysioNet `sleep-accel` benchmark), how often does SmartWake's 90-minute backward-stepping cycle projection awaken the user from light sleep (N1/REM) versus slow-wave sleep (N3), and what is the empirical fallback rate to the hard deadline?
* **Metrics:**
  - Distribution of wake advance times (minutes before deadline)
  - Proportion of wake alarms triggered during light/REM sleep vs. deep N3 sleep
  - Fallback-to-deadline frequency under varying sleep onset delays and target wake windows (15, 30, 45, 60 minutes)

### RQ4: System Scalability, Operational Latency, and Network Resilience
* **Question:** What are the computational overhead, end-to-end inference latency percentiles ($p_{50}, p_{95}, p_{99}$), and throughput capacity of the FastAPI inference server, and how gracefully does the phone-side polling architecture handle intermittent connectivity during alarm verification?
* **Empirical Targets:**
  - Local micro-benchmark of `/logs/raw.log` and `/alarm-status` endpoints
  - Serialization and payload size analysis
  - Graceful degradation verification when server connection fails near the alarm deadline

---

## 3. Data Tiering Structure

To maintain strict academic integrity and avoid synthetic data inflation:
* **Tier A (Real In-Repo Recordings):** The repository does not currently contain local real-night telemetry recordings. We specify a comprehensive `DATA_COLLECTION_PROTOCOL.md` and automated ingestion pipeline for field trials.
* **Tier B (Physiologically-Grounded Synthetic Telemetry):** Implemented in `research/synthetic_generator.py` using parameters derived from peer-reviewed literature (AASM sleep staging, Basner et al. movement probabilities, ultradian cycle variance). Strictly reserved for sensitivity testing and demonstrating synthetic evaluation limits.
* **Tier C (External Clinical PSG Ground-Truth):** PhysioNet `sleep-accel` dataset (Walch et al., 2019; $N=31$ subjects with concurrent triaxial wrist acceleration and PSG 30-second epoch labels). Adapted directly into SmartWake's 9-feature schema to provide independent ground-truth evaluation.
