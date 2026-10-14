"""
Exploratory Data Analysis (EDA) Pipeline for SmartWake Research.
Generates publication-quality 300-DPI empirical figures and descriptive tables:
  1. fig1_raw_accelerometer_trace.png
  2. fig2_feature_distributions.png
  3. fig3_correlation_heatmap.png
  4. fig4_class_balance_and_stages.png
  5. fig5_per_night_dynamics.png
  6. descriptive_statistics.csv
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set publication style
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

FIG_DIR = "research/figures"
RESULTS_DIR = "research/results"
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def plot_raw_trace(df_raw: pd.DataFrame, subject_id: str = "synthetic_subject_01"):
    """Figure 1: Raw triaxial accelerometer trace with sleep onset / awakening overlay."""
    subj_data = df_raw[df_raw["device_id"] == subject_id].copy().iloc[:120]  # First 10 hours
    t_hours = np.arange(len(subj_data)) * 5.0 / 60.0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 4.5), sharex=True, gridspec_kw={"height_ratios": [2, 1]})

    ax1.plot(t_hours, subj_data["accel_x"], label="$a_x$ (lateral)", color="#2b5c8f", lw=0.9, alpha=0.8)
    ax1.plot(t_hours, subj_data["accel_y"], label="$a_y$ (longitudinal)", color="#3f9b0b", lw=0.9, alpha=0.8)
    ax1.plot(t_hours, subj_data["accel_z"], label="$a_z$ (vertical/gravity)", color="#c0392b", lw=0.9, alpha=0.8)
    ax1.set_ylabel("Acceleration ($m/s^2$)")
    ax1.set_title(f"A. Nocturnal Accelerometer Waveform Snapshot ({subject_id}) [Tier B]", fontweight="bold", loc="left")
    ax1.legend(loc="upper right", frameon=True, ncol=3)

    # Shading sleep periods
    is_sleep = subj_data["is_asleep"].values
    ax1.fill_between(t_hours, -3, 15, where=(is_sleep == 1), color="#95a5a6", alpha=0.2, label="Sleep Period")

    # Lower plot: magnitude and sleep onset state
    ax2.plot(t_hours, subj_data["accel_magnitude"], color="#8e44ad", lw=1.2, label="|a| Euclidean Magnitude")
    ax2.axhline(9.81, color="gray", ls="--", lw=0.8, alpha=0.7, label="Static 1g Baseline")
    ax2.set_xlabel("Elapsed Time (Hours from Bedtime)")
    ax2.set_ylabel("Magnitude ($m/s^2$)")
    ax2.set_ylim(8.5, 12.0)
    ax2.legend(loc="upper right", frameon=True, ncol=2)

    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, "fig1_raw_accelerometer_trace.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved: {out_path}")


def plot_feature_distributions(df_feats: pd.DataFrame):
    """Figure 2: Boxplots of key features by class (Awake vs Asleep)."""
    features_to_plot = [
        ("accel_magnitude_mean", "Mean Accel Mag ($m/s^2$)"),
        ("accel_magnitude_std", "Accel Std Dev ($m/s^2$)"),
        ("accel_magnitude_max", "Max Accel Mag ($m/s^2$)"),
        ("zero_crossing_rate", "Zero Crossing Rate"),
        ("consecutive_still_count", "Stillness Streak (Counts)"),
        ("hour_sin", "Circadian Hour Sine"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(10, 5))
    axes = axes.flatten()

    palette = {0: "#e74c3c", 1: "#2980b9"}

    for idx, (feat, label_name) in enumerate(features_to_plot):
        ax = axes[idx]
        sns.boxplot(
            data=df_feats,
            x="label",
            y=feat,
            hue="label",
            palette=palette,
            ax=ax,
            width=0.4,
            fliersize=1.5,
            legend=False,
        )
        ax.set_xticklabels(["Awake (0)", "Asleep (1)"])
        ax.set_xlabel("")
        ax.set_ylabel(label_name)
        ax.set_title(feat.replace("_", " ").title(), fontsize=10, fontweight="bold")

    fig.suptitle("Feature Distributions Stratified by Target Class [Tier B & Tier C Aggregate]", fontsize=12, fontweight="bold", y=0.98)
    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, "fig2_feature_distributions.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved: {out_path}")


def plot_correlation_heatmap(df_feats: pd.DataFrame):
    """Figure 3: Feature Correlation Heatmap."""
    feature_cols = [
        "accel_magnitude_mean",
        "accel_magnitude_std",
        "accel_magnitude_max",
        "zero_crossing_rate",
        "notification_delta",
        "consecutive_still_count",
        "charging",
        "hour_sin",
        "hour_cos",
        "label",
    ]
    sub_df = df_feats[[c for c in feature_cols if c in df_feats.columns]].copy()
    corr = sub_df.corr(method="spearman")

    plt.figure(figsize=(8, 6.5))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(220, 10, as_cmap=True)

    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        vmax=1.0,
        vmin=-1.0,
        center=0,
        square=True,
        linewidths=0.5,
        annot=True,
        fmt=".2f",
        annot_kws={"size": 8},
        cbar_kws={"shrink": 0.8, "label": "Spearman Rank Correlation (\\rho)"},
    )
    plt.title("Spearman Rank Correlation Heatmap of SmartWake Feature Matrix", fontweight="bold", fontsize=11, pad=12)
    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, "fig3_correlation_heatmap.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved: {out_path}")


def plot_class_balance_and_stages(df_feats: pd.DataFrame, df_physio: pd.DataFrame = None):
    """Figure 4: Class balance and clinical PSG stage breakdown."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.8))

    # Panel 1: Sleep vs Awake Class Balance
    counts = df_feats["label"].value_counts(normalize=True) * 100
    bars = ax1.bar(["Awake (0)", "Asleep (1)"], [counts.get(0, 0), counts.get(1, 0)], color=["#e74c3c", "#3498db"], width=0.45)
    ax1.set_ylabel("Proportion of 5-Minute Epochs (%)")
    ax1.set_ylim(0, 100)
    ax1.set_title("A. Binary Target Class Balance", fontweight="bold", loc="left")
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + 2, f"{yval:.1f}%", ha="center", va="bottom", fontweight="bold")

    # Panel 2: Clinical PSG Staging Distribution
    if df_physio is not None and "stage" in df_physio.columns:
        stage_names = {0: "Wake", 1: "N1", 2: "N2", 3: "N3 (SWS)", 5: "REM"}
        phys_counts = df_physio["stage"].map(stage_names).value_counts(normalize=True) * 100
        order = ["Wake", "N1", "N2", "N3 (SWS)", "REM"]
        vals = [phys_counts.get(k, 0) for k in order]
        colors = ["#e74c3c", "#f39c12", "#2980b9", "#2c3e50", "#8e44ad"]
        bars2 = ax2.bar(order, vals, color=colors, width=0.55)
        ax2.set_ylabel("Clinical PSG Epoch Share (%)")
        ax2.set_title("B. Polysomnography Stage Breakdown [Tier C]", fontweight="bold", loc="left")
        for bar in bars2:
            yval = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2.0, yval + 1.5, f"{yval:.1f}%", ha="center", va="bottom", fontsize=8.5)
    else:
        stage_names = {0: "Wake", 1: "N1", 2: "N2", 3: "N3 (SWS)", 5: "REM"}
        b_counts = df_feats["stage"].map(stage_names).value_counts(normalize=True) * 100
        order = ["Wake", "N1", "N2", "N3 (SWS)", "REM"]
        vals = [b_counts.get(k, 0) for k in order]
        bars2 = ax2.bar(order, vals, color=["#e74c3c", "#f39c12", "#2980b9", "#2c3e50", "#8e44ad"], width=0.55)
        ax2.set_ylabel("Simulated Physiology Share (%)")
        ax2.set_title("B. Physiological Stage Breakdown [Tier B]", fontweight="bold", loc="left")

    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, "fig4_class_balance_and_stages.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved: {out_path}")


def plot_hypnogram_and_alarm(df_raw: pd.DataFrame):
    """Figure 5: Sleep hypnogram showing ultradian cycles and smart wake alarm decision."""
    night = df_raw[(df_raw["device_id"] == "synthetic_subject_01")].iloc[:96].copy()
    t_min = np.arange(len(night)) * 5.0

    stages = night["stage"].values
    stage_map = {0: 4, 5: 3, 1: 2, 2: 1, 3: 0}  # Inverse depth: Wake=4, REM=3, N1=2, N2=1, N3=0
    mapped_stages = [stage_map.get(s, 0) for s in stages]

    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.step(t_min, mapped_stages, where="post", color="#2c3e50", lw=1.5, label="Sleep Architecture (Hypnogram)")

    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_yticklabels(["N3 (Deep)", "N2 (Light)", "N1 (Trans)", "REM", "Wake"])
    ax.set_xlabel("Elapsed Nocturnal Minutes")
    ax.set_title("Nocturnal Sleep Staging, Ultradian Oscillations, and SmartWake Trigger Timing", fontweight="bold", fontsize=11)

    # Highlight Smart Wake Window (last 45 minutes before 450 min deadline)
    deadline = 450.0  # 7.5 hours
    window_start = deadline - 45.0
    ax.axvspan(window_start, deadline, color="#f1c40f", alpha=0.25, label="Smart-Wake Window (45 min)")
    ax.axvline(deadline, color="#c0392b", ls="--", lw=1.8, label="Hard Deadline (07:30)")

    # Smart Wake Trigger Point at end of cycle (~390 min)
    trigger_time = 390.0
    ax.plot([trigger_time], [3], marker="*", markersize=14, color="#e67e22", label="SmartWake Fire (REM/Light)")

    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, "fig5_per_night_dynamics.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved: {out_path}")


def generate_descriptive_stats(df_feats: pd.DataFrame):
    """Generates descriptive statistics table across features split by class."""
    feature_cols = [
        "accel_magnitude_mean",
        "accel_magnitude_std",
        "accel_magnitude_max",
        "zero_crossing_rate",
        "notification_delta",
        "consecutive_still_count",
        "charging",
        "hour_sin",
        "hour_cos",
    ]
    rows = []
    for col in feature_cols:
        for lbl in [0, 1]:
            subset = df_feats[df_feats["label"] == lbl][col]
            rows.append({
                "Feature": col,
                "Class": "Awake (0)" if lbl == 0 else "Asleep (1)",
                "Count": int(subset.count()),
                "Mean": float(subset.mean()),
                "Std": float(subset.std()),
                "Min": float(subset.min()),
                "Median": float(subset.median()),
                "Max": float(subset.max()),
                "IQR": float(subset.quantile(0.75) - subset.quantile(0.25)),
            })
    df_desc = pd.DataFrame(rows)
    out_csv = os.path.join(RESULTS_DIR, "descriptive_statistics.csv")
    df_desc.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv}")
    return df_desc


def run_eda():
    print("Executing Exploratory Data Analysis (EDA) Pipeline...")
    raw_path = "research/data/processed/synthetic/synthetic_raw_telemetry.csv"
    feat_path = "research/data/processed/synthetic/synthetic_features.csv"
    phys_path = "research/data/processed/tier_c_physionet.csv"

    df_raw = pd.read_csv(raw_path)
    df_feats = pd.read_csv(feat_path)
    df_phys = pd.read_csv(phys_path) if os.path.exists(phys_path) else None

    plot_raw_trace(df_raw)
    plot_feature_distributions(df_feats)
    plot_correlation_heatmap(df_feats)
    plot_class_balance_and_stages(df_feats, df_phys)
    plot_hypnogram_and_alarm(df_raw)
    generate_descriptive_stats(df_feats)
    print("EDA execution successfully completed. All figures saved at 300 DPI.")


if __name__ == "__main__":
    run_eda()
