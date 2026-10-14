"""
Generate Additional Publication Figures for SmartWake Research Paper:
  1. fig0_system_architecture.png (Multi-tier System Topology)
  2. fig6_confusion_matrices.png (Confusion matrices across key baselines)
  3. fig10_ablation_analysis.png (Feature Group Ablation Performance)
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix
import joblib
from run_experiments import ColeKripkeHeuristic, FixedTimeBaseline

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.dpi": 300,
})

FIG_DIR = Path("research/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = Path("research/results")


from matplotlib.patches import FancyBboxPatch

def plot_system_architecture():
    """Generates clean high-level system architecture vector-style block diagram."""
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    # Tier 1: Client
    rect_client = FancyBboxPatch((5, 10), 25, 32, boxstyle="round,pad=1.0", facecolor="#ebf5fb", edgecolor="#2980b9", lw=1.5)
    ax.add_patch(rect_client)
    ax.text(17.5, 38, "1. Android Client\n(Termux / Flutter App)", ha="center", va="center", fontweight="bold", fontsize=10.5, color="#1b4f72")
    ax.text(17.5, 27, "- Triaxial Accelerometer\n  (Snapshot every 300s)\n- Battery & Charging Poller\n- Notification Count Poller\n- Local Mp3 Alarm Trigger", ha="center", va="center", fontsize=8.5)
    ax.text(17.5, 15, "Output: Raw JSON Ping", ha="center", va="center", fontsize=8.5, style="italic", color="#2980b9")

    # Arrow 1 -> 2
    ax.annotate("", xy=(38, 26), xytext=(30, 26), arrowprops=dict(arrowstyle="->", lw=2, color="#2c3e50"))
    ax.text(34, 28, "POST /logs/raw.log\nX-API-Key", ha="center", va="bottom", fontsize=7.5, fontweight="bold")

    # Tier 2: Server
    rect_server = FancyBboxPatch((38, 5), 32, 42, boxstyle="round,pad=1.0", facecolor="#fef9e7", edgecolor="#f39c12", lw=1.5)
    ax.add_patch(rect_server)
    ax.text(54, 43, "2. Cloud Backend Engine\n(FastAPI on Railway)", ha="center", va="center", fontweight="bold", fontsize=10.5, color="#7d6608")
    ax.text(54, 34, "- rolling 30-min buffer (6 pings)\n- 9-dimensional Feature Extractor\n  (Mean, Std, Max, ZCR, Sin/Cos)", ha="center", va="center", fontsize=8.5)
    ax.text(54, 25, "- GradientBoostingClassifier\n  (sleep_prob >= 0.75 threshold)\n- Sleep Onset State Machine\n  (2 consecutive pings)", ha="center", va="center", fontsize=8.5, color="#d35400", fontweight="bold")
    ax.text(54, 15, "- Ultradian Cycle Scheduler\n  onset + k * 90 min <= deadline\n- PostgreSQL Pool (schema.sql)", ha="center", va="center", fontsize=8.5)

    # Arrow 2 -> 3 (Alarm Status polling)
    ax.annotate("", xy=(30, 18), xytext=(38, 18), arrowprops=dict(arrowstyle="->", lw=2, color="#e67e22", ls="--"))
    ax.text(34, 15, "GET /alarm-status\n(60s poll)", ha="center", va="top", fontsize=7.5, color="#e67e22", fontweight="bold")

    # Tier 3: ML Training
    rect_ml = FancyBboxPatch((75, 12), 22, 28, boxstyle="round,pad=1.0", facecolor="#eafaf1", edgecolor="#27ae60", lw=1.5)
    ax.add_patch(rect_ml)
    ax.text(86, 36, "3. ML Training Tier\n(Offline Colab)", ha="center", va="center", fontweight="bold", fontsize=10.5, color="#145a32")
    ax.text(86, 26, "- Fitabase / Kaggle Data\n- 5-minute Resampling\n- Class-Weighted GBDT\n- Model Artifact Export:\n  sleep_model.pkl", ha="center", va="center", fontsize=8.5)

    # Arrow 3 -> 2
    ax.annotate("", xy=(70, 26), xytext=(75, 26), arrowprops=dict(arrowstyle="->", lw=1.8, color="#27ae60", ls="-."))
    ax.text(72.5, 28, "Artifact\nDrop", ha="center", va="bottom", fontsize=7.5, color="#27ae60")

    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig0_system_architecture.png", dpi=300)
    plt.close()
    print("Saved: fig0_system_architecture.png")


def plot_confusion_matrices():
    """Figure 6: Multi-panel Confusion Matrices across Key Models."""
    df_feats = pd.read_csv("research/data/processed/synthetic/synthetic_features.csv")
    models = {
        "Cole-Kripke Heuristic": joblib.load(RESULTS_DIR / "models/cole-kripke_heuristic.pkl") if (RESULTS_DIR / "models/cole-kripke_heuristic.pkl").exists() else None,
        "Logistic Regression": joblib.load(RESULTS_DIR / "models/logistic_regression.pkl"),
        "Random Forest": joblib.load(RESULTS_DIR / "models/random_forest.pkl"),
        "Gradient Boosting (Repo Model)": joblib.load(RESULTS_DIR / "models/gradient_boosting_repo_model.pkl"),
    }

    feature_cols = [
        "accel_magnitude_mean", "accel_magnitude_std", "accel_magnitude_max",
        "zero_crossing_rate", "notification_delta", "consecutive_still_count",
        "charging", "hour_sin", "hour_cos",
    ]
    X = df_feats[feature_cols].values
    y = df_feats["label"].values.astype(int)

    fig, axes = plt.subplots(1, 4, figsize=(11, 2.8), dpi=300)

    for idx, (m_name, m_obj) in enumerate(models.items()):
        ax = axes[idx]
        if m_obj is None:
            continue
        preds = m_obj.predict(X)
        cm = confusion_matrix(y, preds)
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
                    xticklabels=["Awake", "Asleep"], yticklabels=["Awake", "Asleep"])
        ax.set_title(m_name, fontsize=9.5, fontweight="bold")
        ax.set_ylabel("True Ground Truth" if idx == 0 else "")
        ax.set_xlabel("Predicted Stage")

    fig.suptitle("Confusion Matrices across Classification Paradigms [Tier B Benchmark]", fontsize=11, fontweight="bold", y=1.03)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig6_confusion_matrices.png", dpi=300)
    plt.close()
    print("Saved: fig6_confusion_matrices.png")


def plot_ablation_analysis():
    """Figure 10: Ablation bar chart."""
    df_ab = pd.read_csv(RESULTS_DIR / "ablations.csv")

    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=300)
    x = np.arange(len(df_ab))
    width = 0.25

    rects1 = ax.bar(x - width, df_ab["balanced_accuracy"], width, label="Balanced Accuracy", color="#2980b9")
    rects2 = ax.bar(x, df_ab["f1"], width, label="F1-Score", color="#27ae60")
    rects3 = ax.bar(x + width, df_ab["mcc"], width, label="Matthews Corr (MCC)", color="#e67e22")

    ax.set_ylabel("Validation Score")
    ax.set_title("Ablation Study: Feature Group Impact on Staging Performance", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(df_ab["ablation_group"], rotation=15, ha="right", fontsize=8.5)
    ax.set_ylim(0, 1.1)
    ax.legend(frameon=True, loc="upper right")

    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig10_ablation_analysis.png", dpi=300)
    plt.close()
    print("Saved: fig10_ablation_analysis.png")


if __name__ == "__main__":
    plot_system_architecture()
    plot_confusion_matrices()
    plot_ablation_analysis()
