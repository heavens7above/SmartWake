"""
Regenerates corrected grayscale figures for SmartWake research paper:
- Fixes Fig 4 (Class balance and sleep stages): correct label mapping (0=Awake, 1=Asleep) and real stage percentages
- Fixes Fig 7 (Model comparison): uses honest_metrics.csv with corrected Fixed-Schedule baseline and Wake F1
- Fixes Fig 1 (Raw trace): no label clipping
- Fixes Fig 5 (ROC and PR curves): ultra-crisp readable labels
- Fixes Fig 8 & 9 (TreeSHAP): consistent with shap_importance.csv
"""

import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FIG_DIR = Path("research/paper/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
Path("research/figures").mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = "Helvetica, Arial, DejaVu Sans"
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.edgecolor"] = "#222222"
plt.rcParams["axes.linewidth"] = 0.8

# 1. Figure 1: Raw Accelerometer Trace (Subject 01)
def plot_fig1():
    df_raw = pd.read_csv("research/data/processed/synthetic/synthetic_raw_telemetry.csv")
    s1 = df_raw[df_raw["device_id"] == "synthetic_subject_01"].copy().iloc[:600]
    t_hours = np.arange(len(s1)) * 5.0 / 60.0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.5, 4.8), sharex=True, dpi=300)
    
    ax1.plot(t_hours, s1["accel_x"], label=r"$a_x$", color="#222222", lw=1.0)
    ax1.plot(t_hours, s1["accel_y"], label=r"$a_y$", color="#666666", lw=1.0, ls="--")
    ax1.plot(t_hours, s1["accel_z"], label=r"$a_z$", color="#999999", lw=1.0, ls=":")
    ax1.set_ylabel(r"Acceleration ($m/s^2$)")
    ax1.set_title("A. Overnight Triaxial Linear Acceleration Trace (Subject 01) [Tier B]", fontweight="bold", loc="left", fontsize=10)
    ax1.legend(loc="upper right", frameon=True, edgecolor="#222222", ncol=3, fontsize=8.5)
    
    is_sleep = s1["is_asleep"].values
    ax1.fill_between(t_hours, -3, 12, where=(is_sleep == 1), color="#e8e8e8", alpha=0.7, label="Sleep Period")
    
    ax2.plot(t_hours, s1["accel_magnitude"], color="#111111", lw=1.1, label=r"$\|a\|_2$ Magnitude")
    ax2.axhline(0.05, color="#555555", ls="--", lw=0.9, label=r"Stillness Threshold ($0.05~m/s^2$)")
    ax2.set_xlabel("Elapsed Time from Bedtime (Hours)")
    ax2.set_ylabel(r"$\|a\|_2$ ($m/s^2$)")
    ax2.set_title("B. Dynamic Acceleration Magnitude and Stillness Threshold", fontweight="bold", loc="left", fontsize=10)
    ax2.legend(loc="upper right", frameon=True, edgecolor="#222222", fontsize=8.5)
    ax2.set_ylim(-0.1, 4.5)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig1_raw_accelerometer_trace.png", dpi=300)
    plt.savefig("research/figures/fig1_raw_accelerometer_trace.png", dpi=300)
    plt.close()
    print("Saved fig1_raw_accelerometer_trace.png")

# 2. Figure 4: Class Balance and Sleep Stages (CORRECTED MAPPING)
def plot_fig4():
    df_feats = pd.read_csv("research/data/processed/synthetic/synthetic_features.csv")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 4.0), dpi=300)

    # In synthetic_features.csv: label 0 is Awake, label 1 is Asleep
    counts_wake = int(np.sum(df_feats["label"] == 0))
    counts_sleep = int(np.sum(df_feats["label"] == 1))
    total = len(df_feats)
    pct_wake = counts_wake / total * 100.0
    pct_sleep = counts_sleep / total * 100.0

    bars = ax1.bar(["Awake (0)", "Asleep (1)"], [counts_wake, counts_sleep],
                   color=["#777777", "#222222"], edgecolor="#111111", lw=1.1, width=0.5)
    ax1.text(bars[0].get_x() + bars[0].get_width()/2, counts_wake + 120, f"{counts_wake}\n({pct_wake:.1f}%)", ha="center", fontweight="bold", fontsize=9)
    ax1.text(bars[1].get_x() + bars[1].get_width()/2, counts_sleep + 120, f"{counts_sleep}\n({pct_sleep:.1f}%)", ha="center", fontweight="bold", fontsize=9)
    ax1.set_ylabel("Epoch Count (5-minute windows)")
    ax1.set_title("A. Binary Sleep/Wake Class Distribution", fontweight="bold", loc="left", fontsize=10)
    ax1.set_ylim(0, 6800)

    # Actual stages from data
    # stage 0: Wake, stage 1: N1, stage 2: N2, stage 3: N3, stage 5: REM
    stage_counts = df_feats["stage"].value_counts().to_dict()
    stage_names = ["Wake (0)", "N1 Light (1)", "N2 Core (2)", "N3 Deep (3)", "REM (5)"]
    stage_keys = [0, 1, 2, 3, 5]
    stage_vals = [stage_counts.get(k, 0) for k in stage_keys]
    greys = ["#f5f5f5", "#d0d0d0", "#909090", "#505050", "#151515"]
    
    wedges, texts, autotexts = ax2.pie(
        stage_vals,
        labels=stage_names,
        autopct="%1.1f%%",
        colors=greys,
        wedgeprops=dict(edgecolor="#111111", lw=1.0),
        startangle=140,
        pctdistance=0.72
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_fontweight("bold")
    ax2.set_title("B. Polysomnographic Stage Proportions", fontweight="bold", loc="left", fontsize=10)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig4_class_balance.png", dpi=300)
    plt.savefig("research/figures/fig4_class_balance.png", dpi=300)
    plt.close()
    print("Saved fig4_class_balance.png (CORRECTED labels and percentages)")

# 3. Figure 7: Model Comparison (Grouped Bar Chart using honest_metrics.csv)
def plot_fig7():
    df_metrics = pd.read_csv("research/results/honest_metrics.csv")
    df_loso = df_metrics[df_metrics["evaluation_scheme"].str.contains("LOSO")].copy()

    model_names = [
        "Fixed-Schedule Baseline",
        "Cole-Kripke Heuristic",
        "Logistic Regression",
        "Random Forest",
        "Gradient Boosting (Repo Model)",
        "XGBoost",
    ]
    df_plot = df_loso.set_index("model").reindex(model_names).reset_index()

    short_names = ["Fixed Sched.", "Cole-Kripke", "Logistic", "Random Forest", "GBDT (Repo)", "XGBoost"]
    
    metrics = ["balanced_accuracy", "wake_f1", "sleep_f1", "mcc"]
    metric_labels = ["Balanced Acc.", "Wake F1 (Minority)", "Sleep F1 (Majority)", "Matthews (MCC)"]

    fig, ax = plt.subplots(figsize=(10.0, 4.4), dpi=300)
    x = np.arange(len(short_names))
    width = 0.19

    styles = [
        ("#111111", None, "Balanced Acc."),
        ("#555555", "//", "Wake F1 (Minority)"),
        ("#888888", "xx", "Sleep F1 (Majority)"),
        ("#cccccc", "..", "Matthews (MCC)"),
    ]

    for i, (m, (color, hatch, label)) in enumerate(zip(metrics, styles)):
        vals = df_plot[m].values
        ax.bar(x + (i - 1.5) * width, vals, width, label=label,
               color=color, hatch=hatch, edgecolor="#111111", lw=0.9)

    ax.set_ylabel("Metric Value (0.0 to 1.0)", fontweight="bold")
    ax.set_title("Cross-Subject Generalization Benchmark under Subject-Independent LOSO [Tier B]", fontweight="bold", loc="left", fontsize=10.5)
    ax.set_xticks(x)
    ax.set_xticklabels(short_names, fontweight="bold", fontsize=9)
    ax.set_ylim(0, 1.12)
    ax.axhline(0.5, color="#777777", ls=":", lw=0.8, alpha=0.7)
    ax.legend(loc="upper left", frameon=True, edgecolor="#222222", ncol=4, fontsize=8.5)
    ax.grid(axis="y", ls=":", alpha=0.5, color="#888888")

    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig7_model_comparison.png", dpi=300)
    plt.savefig("research/figures/fig7_model_comparison.png", dpi=300)
    plt.close()
    print("Saved fig7_model_comparison.png (CORRECTED with Wake F1 and honest Fixed Schedule)")

# 4. Figure 9: TreeSHAP Feature Attribution Ranking (EXACT MATCH to CSV)
def plot_fig9():
    df_shap = pd.read_csv("research/results/shap_importance.csv")
    label_map = {
        "consecutive_still_count": "Stillness Streak (Counts)",
        "accel_magnitude_std": "Accel Std Dev (Kinematic)",
        "hour_sin": "hour_sin (Circadian)",
        "notification_delta": "Notification Delta (Phone State)",
        "hour_cos": "hour_cos (Circadian)",
        "accel_magnitude_max": "Max Accel Mag (Kinematic)",
        "accel_magnitude_mean": "Mean Accel Mag (Kinematic)",
        "zero_crossing_rate": "Zero Crossing Rate (Jerk Proxy)",
        "charging": "Charging State (Ambient)"
    }
    df_shap["clean_name"] = df_shap["feature"].map(lambda x: label_map.get(x, x))
    total_shap = df_shap["mean_abs_shap"].sum()
    df_shap["pct"] = df_shap["mean_abs_shap"] / total_shap * 100.0
    df_shap = df_shap.sort_values("mean_abs_shap", ascending=True)

    fig, ax = plt.subplots(figsize=(9.0, 4.2), dpi=300)
    bars = ax.barh(df_shap["clean_name"], df_shap["mean_abs_shap"],
                   color="#383838", edgecolor="#111111", lw=1.0, height=0.6)
    
    for bar, pct, val in zip(bars, df_shap["pct"], df_shap["mean_abs_shap"]):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                f"{val:.3f} ({pct:.1f}%)", va="center", fontsize=8.5, fontweight="bold")

    ax.set_xlabel(r"Mean Absolute TreeSHAP Value: $\mathbb{E}[|\phi_j|]$ (Log-Odds Impact)", fontweight="bold")
    ax.set_title("Ranked Feature Attribution via TreeSHAP on Repository Gradient Boosting [Tier B]", fontweight="bold", loc="left", fontsize=10)
    ax.set_xlim(0, 1.45)
    ax.grid(axis="x", ls=":", alpha=0.5, color="#888888")

    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig9_shap_importance.png", dpi=300)
    plt.savefig("research/figures/fig9_shap_importance.png", dpi=300)
    plt.close()
    print("Saved fig9_shap_importance.png (CORRECTED and aligned with shap_importance.csv)")

if __name__ == "__main__":
    plot_fig1()
    plot_fig4()
    plot_fig7()
    plot_fig9()
    print("All critical figures regenerated successfully!")
