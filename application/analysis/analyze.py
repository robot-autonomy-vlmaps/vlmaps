"""
Evaluation analysis: reads evaluations/leaderboard.jsonl and evaluations/detailed/,
produces CSVs, figures, and a text summary in evaluations/analysis/.

CLI: vlmaps analyze [--leaderboard PATH] [--detailed PATH] [--output PATH]
"""
import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import seaborn as sns

from vlmaps.eval.results import pass_at_k, wilson_ci

logger = logging.getLogger(__name__)

_DPI = 150
_PALETTE = "Set2"
_ERROR_COLORS = {
    "success": "#4caf50",
    "code_error": "#ff9800",
    "llm_error": "#f44336",
    "sim_error": "#9e9e9e",
    "unknown": "#bdbdbd",
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_leaderboard(path: Path) -> pd.DataFrame:
    rows: List[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)

    cfg = pd.json_normalize(df["llm_config"].tolist())  # type: ignore[arg-type]
    cfg.columns = [f"cfg_{c}" for c in cfg.columns]
    df = pd.concat([df.drop(columns=["llm_config"]), cfg], axis=1)

    df["success"] = df["success"].fillna(False).astype(bool)
    df["failed"] = df["failed"].fillna(False).astype(bool)
    return df


def _load_detailed_fields(detailed_dir: Path, uuid_set: set) -> Dict[str, dict]:
    result: Dict[str, dict] = {}
    for f in detailed_dir.iterdir():
        if f.suffix != ".json":
            continue
        uid = f.stem
        if uid not in uuid_set:
            continue
        try:
            with open(f) as fh:
                data = json.load(fh)
            result[uid] = {
                "goal_classes": data.get("goal_classes"),
                "finished_subgoal_ids": data.get("finished_subgoal_ids") or [],
            }
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → %s", path.name)


def _save_data(data: pd.DataFrame, fig_path: Path) -> None:
    csv_path = fig_path.with_suffix(".csv")
    data.to_csv(csv_path, float_format="%.4f")
    logger.info("  → %s", csv_path.name)


def _pct_fmt(ax: plt.Axes, axis: str = "y") -> None:
    fmt = mtick.PercentFormatter(xmax=1)
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)


def _bar_labels(ax: plt.Axes, bars, fmt: str = "{:.2f}", offset: float = 0.01,
                horiz: bool = False) -> None:
    for bar in bars:
        val = bar.get_width() if horiz else bar.get_height()
        if val < 0.005:
            continue
        if horiz:
            ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                    fmt.format(val), va="center", fontsize=7)
        else:
            ax.text(bar.get_x() + bar.get_width() / 2, val + offset,
                    fmt.format(val), ha="center", va="bottom", fontsize=7)


def _scene_color_map(scenes: List[str]) -> Dict[str, str]:
    palette = sns.color_palette(_PALETTE, len(scenes))
    return {s: palette[i] for i, s in enumerate(sorted(set(scenes)))}


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _plot_config_task_sr(df: pd.DataFrame, fig_dir: Path) -> None:
    """One figure per task type: effective vs conditional subgoal SR per config."""
    agg_eff = df.groupby(["run_name", "task_type"]).agg(
        eff_subgoal_sr=("eff_subgoal_sr", "mean"),
    ).reset_index()
    agg_cond = df[~df["failed"]].groupby(["run_name", "task_type"]).agg(
        cond_subgoal_sr=("subgoal_success_rate", "mean"),
    ).reset_index()
    agg = agg_eff.merge(agg_cond, on=["run_name", "task_type"], how="left").fillna(0)

    run_names = sorted(agg["run_name"].unique())
    colors = sns.color_palette(_PALETTE, 2)
    width = 0.35

    for tt in sorted(agg["task_type"].unique()):
        sub = agg[agg["task_type"] == tt].set_index("run_name").reindex(run_names).fillna(0)
        xs = list(range(len(run_names)))

        fig, ax = plt.subplots(figsize=(max(7, len(run_names) * 1.4), 5))
        b1 = ax.bar([i - width / 2 for i in xs], sub["eff_subgoal_sr"], width,
                    label="Effective SR (all runs)", color=colors[0])
        b2 = ax.bar([i + width / 2 for i in xs], sub["cond_subgoal_sr"], width,
                    label="Conditional SR (non-failed)", color=colors[1], alpha=0.7)
        _bar_labels(ax, b1)
        _bar_labels(ax, b2)
        ax.set_title(f"Subgoal SR by Configuration  [{tt} tasks]  (effective vs conditional)")
        ax.set_xticks(xs)
        ax.set_xticklabels(run_names, rotation=30, ha="right", fontsize=8)
        ax.set_ylim(0, 1.05)
        _pct_fmt(ax)
        ax.legend(fontsize=8)
        fig.tight_layout()

        out = fig_dir / f"config_task_sr_{tt}.png"
        _save(fig, out)
        _save_data(sub.reset_index(), out)


def _plot_model_comparison(df: pd.DataFrame, fig_dir: Path) -> None:
    """
    Effective subgoal SR by model family.
    One overall figure (bars grouped by task_type) and one per task type.
    """
    def _one(sub: pd.DataFrame, suffix: str, title: str) -> None:
        agg = sub.groupby(["cfg_model", "task_type"]).agg(
            eff_subgoal_sr=("eff_subgoal_sr", "mean"),
            failure_rate=("failed", "mean"),
        ).reset_index()

        pivot = agg.pivot(index="cfg_model", columns="task_type", values="eff_subgoal_sr").fillna(0)
        models = list(pivot.index)

        fig, ax = plt.subplots(figsize=(max(6, len(models) * 1.5), 5))
        pivot.plot(kind="bar", ax=ax, rot=0, colormap=_PALETTE)
        ax.set_title(title)
        ax.set_xlabel("Model")
        ax.set_ylim(0, 1.05)
        _pct_fmt(ax)
        ax.legend(title="Task type")

        # Annotate overall failure rate per model
        fail_by_model = sub.groupby("cfg_model")["failed"].mean()
        for i, model in enumerate(models):
            fr = fail_by_model.get(model, 0)
            ax.text(i, 0.02, f"fail={fr:.0%}", ha="center", fontsize=7, color="red")

        fig.tight_layout()
        out = fig_dir / f"model_comparison{suffix}.png"
        _save(fig, out)
        _save_data(agg, out)

    _one(df, "", "Model Family Comparison — Effective Subgoal SR  (failures counted as 0)")

    for tt in sorted(df["task_type"].unique()):
        sub = df[df["task_type"] == tt]
        agg = sub.groupby("cfg_model").agg(
            eff_subgoal_sr=("eff_subgoal_sr", "mean"),
            eff_task_sr=("eff_success", "mean"),
            failure_rate=("failed", "mean"),
            n_runs=("uuid", "count"),
        ).reset_index()

        models = list(agg["cfg_model"])
        fig, ax = plt.subplots(figsize=(max(6, len(models) * 1.5), 5))
        colors = sns.color_palette(_PALETTE, len(models))
        bars = ax.bar(range(len(models)), agg["eff_subgoal_sr"], color=colors, alpha=0.85)
        _bar_labels(ax, bars)
        for i, (_, row) in enumerate(agg.iterrows()):
            ax.text(i, 0.02, f"fail={row['failure_rate']:.0%}", ha="center", fontsize=7, color="red")
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(models, rotation=0)
        ax.set_title(f"Model Comparison — Effective Subgoal SR  [{tt} tasks]")
        ax.set_xlabel("Model")
        ax.set_ylim(0, 1.05)
        _pct_fmt(ax)
        fig.tight_layout()

        out = fig_dir / f"model_comparison_{tt}.png"
        _save(fig, out)
        _save_data(agg, out)


def _plot_temperature_effect(df: pd.DataFrame, fig_dir: Path) -> None:
    """
    Temperature effect: one figure for SR, one for failure rate.
    """
    dfc = df.copy()
    dfc["temp_label"] = dfc["cfg_temperature"].apply(lambda t: f"temp={t:.1f}")

    agg_sr = dfc.groupby(["cfg_model", "temp_label"])["eff_subgoal_sr"].mean().reset_index()
    agg_fail = dfc.groupby(["cfg_model", "temp_label"])["failed"].mean().reset_index()

    pivot_sr = agg_sr.pivot(index="cfg_model", columns="temp_label", values="eff_subgoal_sr").fillna(0)
    pivot_fail = agg_fail.pivot(index="cfg_model", columns="temp_label", values="failed").fillna(0)

    # SR figure
    fig, ax = plt.subplots(figsize=(max(6, len(pivot_sr) * 1.5), 5))
    pivot_sr.plot(kind="bar", ax=ax, rot=0, colormap="coolwarm_r")
    ax.set_title("Effective Subgoal SR by Temperature  (failures counted as 0)")
    ax.set_xlabel("Model")
    ax.set_ylim(0, 1.05)
    _pct_fmt(ax)
    ax.legend(title="Temperature")
    fig.tight_layout()
    out_sr = fig_dir / "temperature_effect_sr.png"
    _save(fig, out_sr)
    _save_data(pivot_sr.reset_index(), out_sr)

    # Failure rate figure
    fig, ax = plt.subplots(figsize=(max(6, len(pivot_fail) * 1.5), 5))
    pivot_fail.plot(kind="bar", ax=ax, rot=0, colormap="Reds")
    ax.set_title("Failure Rate by Temperature")
    ax.set_xlabel("Model")
    ax.set_ylim(0, 1.05)
    _pct_fmt(ax)
    ax.legend(title="Temperature")
    fig.tight_layout()
    out_fail = fig_dir / "temperature_effect_failure.png"
    _save(fig, out_fail)
    _save_data(pivot_fail.reset_index(), out_fail)


def _plot_scene_heatmap(df: pd.DataFrame, fig_dir: Path) -> None:
    """Heatmap: config × scene — effective mean subgoal SR (failures=0)."""
    pivot = (
        df.groupby(["run_name", "scene_folder"])["eff_subgoal_sr"]
        .mean()
        .unstack(fill_value=0)
    )

    nrows, ncols = pivot.shape
    fig, ax = plt.subplots(figsize=(max(9, ncols * 1.2), max(4, nrows * 0.9)))
    sns.heatmap(
        pivot, ax=ax, annot=True, fmt=".2f", cmap="YlGn",
        vmin=0, vmax=1, linewidths=0.5,
        cbar_kws={"label": "Subgoal SR"},
    )
    ax.set_title("Subgoal SR: Configuration × Scene")
    ax.set_xlabel("Scene")
    ax.set_ylabel("Configuration")
    plt.xticks(rotation=35, ha="right", fontsize=8)
    out = fig_dir / "config_scene_heatmap.png"
    _save(fig, out)
    _save_data(pivot, out)


def _plot_task_ranking_easiest(task_df: pd.DataFrame, fig_dir: Path, n: int = 10) -> None:
    """Horizontal bars: top-N easiest tasks by avg subgoal SR."""
    top = task_df.sort_values("avg_subgoal_sr", ascending=False).head(n)
    labels = [f"{r['task_key']}  [{r['task_type']}]" for _, r in top.iterrows()]
    vals = top["avg_subgoal_sr"].tolist()

    fig, ax = plt.subplots(figsize=(9, max(5, n * 0.5 + 1)))
    bars = ax.barh(range(len(labels)), vals, color="#66bb6a", alpha=0.82)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlim(0, 1.1)
    _pct_fmt(ax, "x")
    ax.set_title(f"Easiest {n} Tasks  (avg subgoal SR, all configs)")
    ax.set_xlabel("Avg Subgoal SR")
    _bar_labels(ax, bars, horiz=True)
    fig.tight_layout()

    out = fig_dir / "task_ranking_easiest.png"
    _save(fig, out)
    _save_data(top.reset_index(drop=True), out)


def _plot_task_ranking_hardest(task_df: pd.DataFrame, fig_dir: Path, n: int = 10) -> None:
    """Horizontal bars: bottom-N hardest tasks with avg subgoal SR > 0."""
    # Exclude tasks with SR == 0 (those get their own figure)
    nonzero = task_df[task_df["avg_subgoal_sr"] > 0].sort_values("avg_subgoal_sr")
    bottom = nonzero.head(n)
    labels = [f"{r['task_key']}  [{r['task_type']}]" for _, r in bottom.iterrows()]
    vals = bottom["avg_subgoal_sr"].tolist()

    fig, ax = plt.subplots(figsize=(9, max(5, n * 0.5 + 1)))
    bars = ax.barh(range(len(labels)), vals, color="#ef5350", alpha=0.82)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlim(0, 1.1)
    _pct_fmt(ax, "x")
    ax.set_title(f"Hardest {n} Tasks with SR > 0  (avg subgoal SR, all configs)")
    ax.set_xlabel("Avg Subgoal SR")
    _bar_labels(ax, bars, horiz=True)
    fig.tight_layout()

    out = fig_dir / "task_ranking_hardest.png"
    _save(fig, out)
    _save_data(bottom.reset_index(drop=True), out)


def _plot_zero_sr_tasks(task_df: pd.DataFrame, fig_dir: Path) -> None:
    """All tasks with avg subgoal SR == 0, grouped and colour-coded by scene."""
    zero = task_df[task_df["avg_subgoal_sr"] == 0].copy()
    if zero.empty:
        logger.info("No zero-SR tasks — skipping task_ranking_zero_sr.png")
        return

    zero = zero.sort_values(["scene_folder", "task_type", "task_key"])
    scenes = sorted(zero["scene_folder"].unique())
    cmap = _scene_color_map(scenes)

    labels = [f"{r['task_key']}  [{r['task_type']}]" for _, r in zero.iterrows()]
    colors = [cmap[r["scene_folder"]] for _, r in zero.iterrows()]
    failure_rates = (zero["n_failed"] / zero["n_runs"]).tolist()

    fig, ax = plt.subplots(figsize=(9, max(5, len(zero) * 0.45 + 1.5)))
    bars = ax.barh(range(len(labels)), failure_rates, color=colors, alpha=0.85)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlim(0, 1.15)
    _pct_fmt(ax, "x")
    ax.set_title(f"Tasks with Zero Subgoal SR  ({len(zero)} tasks)  — coloured by scene")
    ax.set_xlabel("Failure Rate  (n_failed / n_runs)")

    # Annotate n_failed/n_runs
    for bar, (_, row) in zip(bars, zero.iterrows()):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{int(row['n_failed'])}/{int(row['n_runs'])} failed",
                va="center", fontsize=6)

    # Legend for scenes
    from matplotlib.patches import Patch
    handles = [Patch(color=cmap[s], label=s) for s in scenes]
    ax.legend(handles=handles, title="Scene", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=7)

    fig.tight_layout()
    out = fig_dir / "task_ranking_zero_sr.png"
    _save(fig, out)
    _save_data(zero.reset_index(drop=True), out)


def _plot_per_class(class_df: pd.DataFrame, fig_dir: Path) -> None:
    """Horizontal bar: per-class success rate, colour-coded by quartile."""
    if class_df.empty:
        logger.warning("No per-class data — skipping per_class_sr.png")
        return

    sdf = class_df.sort_values("sr")
    colors = ["#ef5350" if v < 0.3 else "#ffa726" if v < 0.6 else "#66bb6a"
              for v in sdf["sr"]]

    fig, ax = plt.subplots(figsize=(8, max(5, len(sdf) * 0.38 + 1)))
    bars = ax.barh(range(len(sdf)), sdf["sr"], color=colors, alpha=0.85)
    ax.set_yticks(range(len(sdf)))
    ax.set_yticklabels(sdf["class_name"], fontsize=8)
    ax.set_xlim(0, 1.15)
    _pct_fmt(ax, "x")
    ax.set_title("Per-Class Success Rate (Object Navigation, All Configs)")
    ax.set_xlabel("Success Rate")
    for bar, (_, row) in zip(bars, sdf.iterrows()):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{int(row['finished'])}/{int(row['total'])}", va="center", fontsize=7)
    fig.tight_layout()
    out = fig_dir / "per_class_sr.png"
    _save(fig, out)
    _save_data(sdf.reset_index(drop=True), out)


def _plot_consecutive(consec_df: pd.DataFrame, fig_dir: Path) -> None:
    """Grouped bars: consecutive subgoal completion per config — starts at 1 (0 means no streak)."""
    if consec_df.empty:
        return
    # Drop 0-consecutive entries: a streak of 0 means no subgoals in order, not meaningful here
    consec_df = consec_df[consec_df["consecutive"] >= 1]
    if consec_df.empty:
        return

    pivot = consec_df.pivot(index="run_name", columns="consecutive", values="n_tasks").fillna(0)
    for c in range(1, 5):
        if c not in pivot.columns:
            pivot[c] = 0.0
    pivot = pivot[[c for c in sorted(pivot.columns) if c >= 1]]

    fig, ax = plt.subplots(figsize=(max(9, len(pivot) * 1.8), 5))
    pivot.plot(kind="bar", ax=ax, rot=25, colormap="Blues_r")
    ax.set_title("Consecutive Subgoal Completion per Configuration\n(tasks that completed ≥N subgoals in order from the start)")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Number of Tasks")
    ax.legend(title="Consecutive\nsubgoals", bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    out = fig_dir / "consecutive_subgoals.png"
    _save(fig, out)
    _save_data(pivot, out)


def _plot_error_breakdown(df: pd.DataFrame, fig_dir: Path) -> None:
    """Stacked bars: success + error types per config."""
    dfc = df.copy()
    dfc["status"] = dfc.apply(
        lambda r: (r["error_type"] if r["failed"] and r["error_type"]
                   else ("success" if not r["failed"] else "unknown")),
        axis=1,
    )
    counts = dfc.groupby(["run_name", "status"]).size().unstack(fill_value=0)
    order = ["success", "code_error", "llm_error", "sim_error", "unknown"]
    for s in order:
        if s not in counts.columns:
            counts[s] = 0
    counts = counts[[s for s in order if s in counts.columns]]

    fig, ax = plt.subplots(figsize=(max(9, len(counts) * 1.8), 5))
    bottom = pd.Series([0] * len(counts), index=counts.index, dtype=float)
    for status in counts.columns:
        col = counts[status].astype(float)
        ax.bar(range(len(counts)), col, bottom=bottom,
               label=status, color=_ERROR_COLORS.get(status, "#bdbdbd"), alpha=0.88)
        bottom += col

    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, rotation=28, ha="right", fontsize=8)
    ax.set_title("Evaluation Outcome per Configuration")
    ax.set_ylabel("Number of Runs")
    ax.legend(title="Outcome", bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    out = fig_dir / "error_breakdown.png"
    _save(fig, out)
    _save_data(counts, out)


# ---------------------------------------------------------------------------
# Multi-sample plots
# ---------------------------------------------------------------------------

def _plot_pass_k(cfg_ns: pd.DataFrame, fig_dir: Path) -> None:
    """Grouped bars: pass@1 and pass@5 per config. Skips configs with all-NaN pass@5."""
    data = cfg_ns.dropna(subset=["pass_at_1"]).copy()
    if data.empty:
        return

    run_names = list(data["run_name"])
    xs = list(range(len(run_names)))
    colors = sns.color_palette(_PALETTE, 2)
    width = 0.35

    fig, ax = plt.subplots(figsize=(max(7, len(run_names) * 1.4), 5))
    p1_vals = data["pass_at_1"].tolist()
    p5_vals = [v if not (isinstance(v, float) and v != v) else 0.0
               for v in data["pass_at_5"].tolist()]

    b1 = ax.bar([i - width / 2 for i in xs], p1_vals, width, label="pass@1", color=colors[0])
    b2 = ax.bar([i + width / 2 for i in xs], p5_vals, width, label="pass@5", color=colors[1], alpha=0.8)
    _bar_labels(ax, b1)
    _bar_labels(ax, b2)
    ax.set_xticks(xs)
    ax.set_xticklabels(run_names, rotation=30, ha="right", fontsize=8)
    ax.set_ylim(0, 1.05)
    _pct_fmt(ax)
    ax.set_title("pass@k (unbiased Chen et al. 2021 estimator)")
    ax.set_xlabel("Configuration")
    ax.legend(fontsize=9)
    fig.tight_layout()
    out = fig_dir / "pass_k_comparison.png"
    _save(fig, out)
    _save_data(data, out)


def _plot_self_consistency(cfg_ns: pd.DataFrame, fig_dir: Path) -> None:
    """Horizontal bar: self-consistency (majority-vote agreement) per config."""
    data = cfg_ns.dropna(subset=["self_consistency"]).sort_values("self_consistency")
    if data.empty:
        return

    fig, ax = plt.subplots(figsize=(8, max(4, len(data) * 0.5 + 1)))
    colors = ["#66bb6a" if v >= 0.8 else "#ffa726" if v >= 0.6 else "#ef5350"
              for v in data["self_consistency"]]
    bars = ax.barh(range(len(data)), data["self_consistency"], color=colors, alpha=0.85)
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels(data["run_name"], fontsize=8)
    ax.set_xlim(0, 1.1)
    _pct_fmt(ax, "x")
    ax.set_title("Self-Consistency (majority-vote agreement rate)")
    ax.set_xlabel("Agreement Rate")
    _bar_labels(ax, bars, horiz=True)
    fig.tight_layout()
    out = fig_dir / "self_consistency.png"
    _save(fig, out)
    _save_data(data.reset_index(drop=True), out)


def _plot_output_diversity(cfg_ns: pd.DataFrame, fig_dir: Path) -> None:
    """Horizontal bar: output diversity (distinct-SR fraction) per config."""
    data = cfg_ns.dropna(subset=["output_diversity"]).sort_values("output_diversity")
    if data.empty:
        return

    fig, ax = plt.subplots(figsize=(8, max(4, len(data) * 0.5 + 1)))
    colors = sns.color_palette(_PALETTE, len(data))
    bars = ax.barh(range(len(data)), data["output_diversity"], color=colors, alpha=0.85)
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels(data["run_name"], fontsize=8)
    ax.set_xlim(0, 1.1)
    _pct_fmt(ax, "x")
    ax.set_title("Output Diversity (fraction of distinct subgoal SR values across samples)")
    ax.set_xlabel("Diversity Rate")
    _bar_labels(ax, bars, horiz=True)
    fig.tight_layout()
    out = fig_dir / "output_diversity.png"
    _save(fig, out)
    _save_data(data.reset_index(drop=True), out)


def _plot_determinism(task_run: pd.DataFrame, df: pd.DataFrame, fig_dir: Path) -> None:
    """
    For greedy configs (temperature==0, n_drawn==2): % of task pairs where
    both samples produced identical success outcome.
    """
    greedy_runs = df[df["cfg_temperature"] == 0.0]["run_name"].unique()
    rows = task_run[
        (task_run["run_name"].isin(greedy_runs)) & (task_run["n_drawn"] == 2)
    ].copy()
    if rows.empty:
        logger.info("No greedy n_samples=2 pairs — skipping determinism_check.png")
        return

    rows["identical"] = rows["success_list"].apply(
        lambda sl: sl[0] == sl[1] if len(sl) == 2 else False
    )
    det = rows.groupby("run_name")["identical"].mean().reset_index()
    det.columns = ["run_name", "determinism_rate"]
    det = det.sort_values("determinism_rate")

    fig, ax = plt.subplots(figsize=(max(6, len(det) * 1.5), 5))
    colors = ["#66bb6a" if v == 1.0 else "#ffa726" if v >= 0.9 else "#ef5350"
              for v in det["determinism_rate"]]
    bars = ax.bar(range(len(det)), det["determinism_rate"], color=colors, alpha=0.85)
    _bar_labels(ax, bars)
    ax.set_xticks(range(len(det)))
    ax.set_xticklabels(det["run_name"], rotation=20, ha="right", fontsize=8)
    ax.set_ylim(0, 1.05)
    _pct_fmt(ax)
    ax.set_title("Greedy Determinism Check  (n_samples=2, % identical outcomes)")
    ax.set_xlabel("Configuration")
    fig.tight_layout()
    out = fig_dir / "determinism_check.png"
    _save(fig, out)
    _save_data(det, out)


# ---------------------------------------------------------------------------
# Summary text
# ---------------------------------------------------------------------------

def _build_summary(
    df: pd.DataFrame,
    cfg_agg: pd.DataFrame,
    task_agg: pd.DataFrame,
    class_df: pd.DataFrame,
    cfg_ns: pd.DataFrame,
    lb_path: Path,
    out_dir: Path,
) -> str:
    W = 76
    lines: List[str] = []

    def sec(title: str) -> None:
        lines.append(f"\n── {title} {'─' * max(0, W - len(title) - 4)}")

    lines.append("=" * W)
    lines.append("  VLMaps Evaluation Analysis")
    lines.append("=" * W)
    lines.append(f"Generated   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Leaderboard : {lb_path}")
    lines.append(
        f"Total runs  : {len(df)}  |  Configs: {df['run_name'].nunique()}"
        f"  |  Scenes: {df['scene_folder'].nunique()}"
        f"  |  Task types: {', '.join(sorted(df['task_type'].unique()))}"
    )
    lines.append(f"Failed runs : {int(df['failed'].sum())}  ({100 * df['failed'].mean():.1f}%)")

    lines.append("")
    lines.append("NOTE: 'Effective SR' counts failed runs as 0 — the fair cross-config ranking.")
    lines.append("      'Conditional SR' excludes failed runs — shows quality on valid outputs.")

    sec("Configuration Rankings  (sorted by Effective Subgoal SR)")
    lines.append(
        f"{'Rank':<5} {'Run Name':<30} {'Model':<12} {'Temp':>5}"
        f" {'Eff Sub SR':>11} {'Cond Sub SR':>12} {'Failed%':>8} {'N':>5}"
    )
    lines.append("-" * W)
    for rank, (_, r) in enumerate(cfg_agg.iterrows(), 1):
        fail_pct = 100 * int(r["n_failed"]) / int(r["n_total"]) if r["n_total"] > 0 else 0
        cond = r.get("cond_subgoal_sr", float("nan"))
        lines.append(
            f"{rank:<5} {r['run_name']:<30} {r['model']:<12} {r['temperature']:>5.1f}"
            f" {r['eff_subgoal_sr']:>11.3f} {cond:>12.3f} {fail_pct:>7.1f}% {int(r['n_total']):>5}"
        )
    best = cfg_agg.iloc[0]
    worst = cfg_agg.iloc[-1]
    lines.append(
        f"\nBest config  : {best['run_name']}"
        f"  (eff_subgoal_sr={best['eff_subgoal_sr']:.3f},  failure_rate={100*best['n_failed']/best['n_total']:.1f}%)"
    )
    lines.append(
        f"Worst config : {worst['run_name']}"
        f"  (eff_subgoal_sr={worst['eff_subgoal_sr']:.3f},  failure_rate={100*worst['n_failed']/worst['n_total']:.1f}%)"
    )

    valid = df[~df["failed"]]

    sec("By Task Type  (Effective Subgoal SR)")
    tt_pivot = df.groupby(["run_name", "task_type"])["eff_subgoal_sr"].mean().unstack()
    tts = sorted(tt_pivot.columns)
    lines.append(f"{'Run Name':<30}" + "".join(f"  {tt:>8}" for tt in tts))
    lines.append("-" * W)
    for rn, row in tt_pivot.iterrows():
        lines.append(f"{str(rn):<30}" + "".join(
            f"  {row.get(tt, float('nan')):>8.3f}" for tt in tts
        ))

    sec("By Model Family  (effective metrics)")
    for tt in sorted(df["task_type"].unique()):
        sub = df[df["task_type"] == tt]
        lines.append(f"  [{tt}]")
        for model, grp in sub.groupby("cfg_model"):
            lines.append(
                f"    {str(model):<12}  eff_subgoal_sr={grp['eff_subgoal_sr'].mean():.3f}"
                f"  eff_task_sr={grp['eff_success'].mean():.3f}"
                f"  failure_rate={grp['failed'].mean():.1%}  ({len(grp)} runs)"
            )
    lines.append("\n  [overall]")
    for model, grp in df.groupby("cfg_model"):
        lines.append(
            f"    {str(model):<12}  eff_subgoal_sr={grp['eff_subgoal_sr'].mean():.3f}"
            f"  eff_task_sr={grp['eff_success'].mean():.3f}"
            f"  failure_rate={grp['failed'].mean():.1%}  ({len(grp)} runs)"
        )

    sec("Temperature Effect  (Effective SR  |  Conditional SR  |  Failure Rate)")
    temp_eff = df.groupby(["cfg_model", "cfg_temperature"])["eff_subgoal_sr"].mean().unstack()
    temp_cond = valid.groupby(["cfg_model", "cfg_temperature"])["subgoal_success_rate"].mean().unstack()
    temp_fail = df.groupby(["cfg_model", "cfg_temperature"])["failed"].mean().unstack()
    temps = sorted(temp_eff.columns)
    lines.append(f"{'Model':<12}" + "".join(
        f"  temp={t:.1f} [eff/cond/fail%]" for t in temps
    ))
    lines.append("-" * W)
    for model in temp_eff.index:
        parts = []
        for t in temps:
            eff = temp_eff.loc[model, t] if t in temp_eff.columns else float("nan")
            cond = temp_cond.loc[model, t] if (model in temp_cond.index and t in temp_cond.columns) else float("nan")
            fail = temp_fail.loc[model, t] if t in temp_fail.columns else float("nan")
            parts.append(f"  {eff:.3f}/{cond:.3f}/{fail:.0%}")
        lines.append(f"{str(model):<12}" + "".join(parts))

    sec("Easiest Tasks  (top 5 by avg subgoal SR)")
    lines.append(f"{'Task Key':<42} {'Type':<5} {'Avg SR':>7} {'Runs':>5}")
    for _, r in task_agg.head(5).iterrows():
        lines.append(
            f"{r['task_key']:<42} {r['task_type']:<5} {r['avg_subgoal_sr']:>7.3f} {int(r['n_runs']):>5}"
        )

    sec("Hardest Tasks with SR > 0  (bottom 5 excluding zero-SR tasks)")
    nonzero_tasks = task_agg[task_agg["avg_subgoal_sr"] > 0].sort_values("avg_subgoal_sr")
    lines.append(f"{'Task Key':<42} {'Type':<5} {'Avg SR':>7} {'Runs':>5}")
    for _, r in nonzero_tasks.head(5).iterrows():
        lines.append(
            f"{r['task_key']:<42} {r['task_type']:<5} {r['avg_subgoal_sr']:>7.3f} {int(r['n_runs']):>5}"
        )

    zero_tasks = task_agg[task_agg["avg_subgoal_sr"] == 0]
    if not zero_tasks.empty:
        sec(f"Zero-SR Tasks  ({len(zero_tasks)} tasks, grouped by scene)")
        for scene, grp in zero_tasks.groupby("scene_folder"):
            lines.append(f"  {scene}")
            for _, r in grp.iterrows():
                lines.append(
                    f"    {r['task_key']:<40} [{r['task_type']}]"
                    f"  n_failed={int(r['n_failed'])}/{int(r['n_runs'])}"
                )

    if not class_df.empty:
        sec("Per-Class Success Rates  (Object Navigation, all configs)")
        lines.append(f"{'Class':<25} {'Finished':>9} {'Total':>7} {'SR':>7}")
        lines.append("-" * W)
        for _, r in class_df.iterrows():
            lines.append(
                f"{r['class_name']:<25} {int(r['finished']):>9}"
                f" {int(r['total']):>7} {r['sr']:>7.3f}"
            )

    sec("Error Breakdown per Configuration")
    dfc = df.copy()
    dfc["status"] = dfc.apply(
        lambda r: (r["error_type"] if r["failed"] and r["error_type"]
                   else ("success" if not r["failed"] else "unknown")),
        axis=1,
    )
    err_piv = dfc.groupby(["run_name", "status"]).size().unstack(fill_value=0)
    status_cols = [c for c in ["success", "code_error", "llm_error", "sim_error", "unknown"]
                   if c in err_piv.columns]
    lines.append(f"{'Run Name':<30}" + "".join(f"  {c:>12}" for c in status_cols))
    lines.append("-" * W)
    for rn, row in err_piv.iterrows():
        lines.append(
            f"{str(rn):<30}" + "".join(f"  {int(row.get(c, 0)):>12}" for c in status_cols)
        )

    if not cfg_ns.empty:
        sec("n-Sample Robustness  (pass@k, Wilson 95% CI, self-consistency, diversity)")
        lines.append(
            f"{'Run Name':<30} {'n_s':>4}  {'pass@1':>7} {'pass@5':>7}"
            f"  {'CI_lo':>6} {'CI_hi':>6}  {'consist':>8} {'diverse':>8}"
        )
        lines.append("-" * W)
        for _, r in cfg_ns.iterrows():
            p5 = r.get("pass_at_5", float("nan"))
            p5_s = f"{p5:7.3f}" if p5 == p5 else "    N/A"
            lines.append(
                f"{r['run_name']:<30} {int(r.get('n_samples_config', 1)):>4}"
                f"  {r['pass_at_1']:>7.3f} {p5_s}"
                f"  {r['ci_lo']:>6.3f} {r['ci_hi']:>6.3f}"
                f"  {r['self_consistency']:>8.3f} {r['output_diversity']:>8.3f}"
            )

    lines.append("\n" + "=" * W)
    lines.append(f"Output: {out_dir.resolve()}")
    lines.append("=" * W)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(
    leaderboard: str = "evaluations/leaderboard.jsonl",
    detailed_dir: str = "evaluations/detailed",
    output_dir: str = "evaluations/analysis",
) -> None:
    from vlmaps.utils.logging_utils import setup_logging
    setup_logging()

    lb_path = Path(leaderboard)
    det_dir = Path(detailed_dir)
    out_dir = Path(output_dir)
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    if not lb_path.exists():
        raise FileNotFoundError(f"Leaderboard not found: {lb_path}")

    logger.info("Loading leaderboard: %s", lb_path)
    df = _load_leaderboard(lb_path)
    logger.info(
        "%d rows | %d configs | %d task_keys | %d scenes",
        len(df), df["run_name"].nunique(), df["task_key"].nunique(), df["scene_folder"].nunique(),
    )

    logger.info("Loading detailed results for per-class & consecutive analysis...")
    detail = _load_detailed_fields(det_dir, set(df["uuid"])) if det_dir.exists() else {}
    df["_finished_ids"] = df["uuid"].map(lambda u: detail.get(u, {}).get("finished_subgoal_ids", []))
    df["_goal_classes"] = df["uuid"].map(lambda u: detail.get(u, {}).get("goal_classes"))

    df["eff_subgoal_sr"] = df.apply(
        lambda r: r["subgoal_success_rate"] if not r["failed"] else 0.0, axis=1
    )
    df["eff_success"] = df.apply(
        lambda r: bool(r["success"]) if not r["failed"] else False, axis=1
    )

    valid = df[~df["failed"]]

    # ── CSVs ─────────────────────────────────────────────────────────────────
    logger.info("Computing aggregates and writing CSVs...")

    cfg_eff = df.groupby("run_name").agg(
        n_total=("uuid", "count"),
        eff_task_sr=("eff_success", "mean"),
        eff_subgoal_sr=("eff_subgoal_sr", "mean"),
        n_failed=("failed", "sum"),
        model=("cfg_model", "first"),
        temperature=("cfg_temperature", "first"),
        top_k=("cfg_top_k", "first"),
        top_p=("cfg_top_p", "first"),
        max_new_tokens=("cfg_max_new_tokens", "first"),
    ).reset_index()
    cfg_eff["n_failed"] = cfg_eff["n_failed"].astype(int)
    cfg_cond = valid.groupby("run_name").agg(
        n_valid=("uuid", "count"),
        cond_task_sr=("success", "mean"),
        cond_subgoal_sr=("subgoal_success_rate", "mean"),
    ).reset_index()
    cfg_agg = cfg_eff.merge(cfg_cond, on="run_name", how="left")
    cfg_agg = cfg_agg.sort_values("eff_subgoal_sr", ascending=False)
    cfg_agg.to_csv(out_dir / "config_summary.csv", index=False, float_format="%.4f")

    task_agg = df.groupby("task_key").agg(
        avg_subgoal_sr=("eff_subgoal_sr", "mean"),
        avg_task_sr=("eff_success", "mean"),
        n_runs=("uuid", "count"),
        n_failed=("failed", "sum"),
        task_type=("task_type", "first"),
        scene_folder=("scene_folder", "first"),
    ).reset_index().sort_values("avg_subgoal_sr", ascending=False)
    task_agg["n_failed"] = task_agg["n_failed"].astype(int)
    task_agg["n_runs"] = task_agg["n_runs"].astype(int)
    task_agg.to_csv(out_dir / "task_ranking.csv", index=False, float_format="%.4f")

    class_counts: Dict[str, dict] = defaultdict(lambda: {"finished": 0, "total": 0})
    for _, row in valid[valid["task_type"] == "obj"].iterrows():
        gc = row["_goal_classes"]
        fids = row["_finished_ids"] or []
        if not gc:
            continue
        for i, cls in enumerate(gc):
            class_counts[cls]["total"] += 1
            if i in fids:
                class_counts[cls]["finished"] += 1
    class_df = pd.DataFrame([
        {"class_name": k, "finished": v["finished"], "total": v["total"],
         "sr": v["finished"] / v["total"] if v["total"] > 0 else 0.0}
        for k, v in class_counts.items()
    ]).sort_values("sr", ascending=False)
    class_df.to_csv(out_dir / "per_class.csv", index=False, float_format="%.4f")

    dfc = df.copy()
    dfc["status"] = dfc.apply(
        lambda r: (r["error_type"] if r["failed"] and r["error_type"]
                   else ("success" if not r["failed"] else "unknown")),
        axis=1,
    )
    err_piv = dfc.groupby(["run_name", "status"]).size().unstack(fill_value=0)
    err_piv.to_csv(out_dir / "error_analysis.csv")

    consec_rows: List[dict] = []
    for _, row in valid.iterrows():
        fids = row["_finished_ids"] or []
        n_sub = int(row.get("num_subgoals", 4))
        n_consec = 0
        for i in range(n_sub):
            if i in fids:
                n_consec += 1
            else:
                break
        consec_rows.append({"run_name": row["run_name"], "consecutive": n_consec})
    consec_df = (
        pd.DataFrame(consec_rows)
        .groupby(["run_name", "consecutive"])
        .size()
        .reset_index(name="n_tasks")
    )

    # ── Multi-sample metrics ──────────────────────────────────────────────────
    logger.info("Computing multi-sample metrics (pass@k, self-consistency, diversity)...")

    task_run = df.groupby(["task_key", "run_name"]).agg(
        n_drawn=("uuid", "count"),
        n_success=("eff_success", "sum"),
        sr_values=("eff_subgoal_sr", list),
        success_list=("eff_success", list),
        task_type=("task_type", "first"),
        scene_folder=("scene_folder", "first"),
    ).reset_index()

    task_run["pass@1"] = task_run.apply(
        lambda r: pass_at_k(int(r["n_drawn"]), int(r["n_success"]), 1), axis=1
    )
    task_run["pass@5"] = task_run.apply(
        lambda r: pass_at_k(int(r["n_drawn"]), int(r["n_success"]), 5), axis=1
    )
    task_run["self_consistency"] = task_run.apply(
        lambda r: (
            max(int(r["n_success"]), int(r["n_drawn"]) - int(r["n_success"])) / int(r["n_drawn"])
            if int(r["n_drawn"]) > 0 else float("nan")
        ),
        axis=1,
    )
    task_run["output_diversity"] = task_run["sr_values"].apply(
        lambda sl: len({round(v, 4) for v in sl}) / len(sl) if sl else float("nan")
    )

    # Config-level n-sample summary
    cfg_ns = task_run.groupby("run_name").agg(
        pass_at_1=("pass@1", "mean"),
        pass_at_5=("pass@5", "mean"),
        self_consistency=("self_consistency", "mean"),
        output_diversity=("output_diversity", "mean"),
    ).reset_index()

    # Wilson CI from row-level counts
    ci_rows = []
    for rn, grp in df.groupby("run_name"):
        lo, hi = wilson_ci(int(grp["eff_success"].sum()), len(grp))
        ci_rows.append({"run_name": rn, "ci_lo": lo, "ci_hi": hi})
    cfg_ns = cfg_ns.merge(pd.DataFrame(ci_rows), on="run_name", how="left")

    # Attach n_samples_config for display (from llm_config stored field if present)
    if "cfg_n_samples" in df.columns:
        ns_map = df.groupby("run_name")["cfg_n_samples"].first().reset_index()
        ns_map.columns = ["run_name", "n_samples_config"]
        cfg_ns = cfg_ns.merge(ns_map, on="run_name", how="left")
    else:
        cfg_ns["n_samples_config"] = task_run.groupby("run_name")["n_drawn"].max().reindex(
            cfg_ns["run_name"]
        ).values

    cfg_ns = cfg_ns.sort_values("pass_at_1", ascending=False)
    cfg_ns.to_csv(out_dir / "config_nsamples_metrics.csv", index=False, float_format="%.4f")

    logger.info("Wrote 5 CSV files to %s", out_dir)

    # ── Figures ──────────────────────────────────────────────────────────────
    sns.set_theme(style="whitegrid", palette=_PALETTE)
    logger.info("Generating figures...")

    _plot_config_task_sr(df, fig_dir)           # config_task_sr_{obj,spt}.png
    _plot_model_comparison(df, fig_dir)         # model_comparison.png + _{obj,spt}.png
    _plot_temperature_effect(df, fig_dir)       # temperature_effect_sr.png + _failure.png
    _plot_scene_heatmap(df, fig_dir)
    _plot_task_ranking_easiest(task_agg, fig_dir)
    _plot_task_ranking_hardest(task_agg, fig_dir)
    _plot_zero_sr_tasks(task_agg, fig_dir)
    _plot_per_class(class_df, fig_dir)
    _plot_consecutive(consec_df, fig_dir)
    _plot_error_breakdown(df, fig_dir)
    _plot_pass_k(cfg_ns, fig_dir)
    _plot_self_consistency(cfg_ns, fig_dir)
    _plot_output_diversity(cfg_ns, fig_dir)
    _plot_determinism(task_run, df, fig_dir)

    # ── Summary ──────────────────────────────────────────────────────────────
    summary = _build_summary(df, cfg_agg, task_agg, class_df, cfg_ns, lb_path, out_dir)
    (out_dir / "summary.txt").write_text(summary)
    print(summary)
    logger.info("Analysis complete. Output: %s", out_dir.resolve())


if __name__ == "__main__":
    main()
