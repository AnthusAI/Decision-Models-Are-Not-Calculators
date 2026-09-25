"""Create data-faithful article plots and the 1200x630 social preview."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np

from .records import read_jsonl
from .study import ENGINE_NAMES, FACES, REPRESENTATIONS, complete_request_ids

BG = "#F0F9FC"
INK = "#292B31"
MUTED = "#68747D"
GRID = "#C7DAE2"
FACE_ONE = "#0784CC"
FACE_SIX = "#C72D80"
OTHER = "#9AAEB8"
ENGINE_COLOR = {"jev": FACE_ONE, "kev": "#7056B5", "laya": FACE_SIX}
ENGINE_LABEL = {"jev": "Jev", "kev": "Kev", "laya": "Laya"}


def _font(path: Path, size: float):
    return FontProperties(fname=str(path), size=size)


def _complete_rows(data_dir: Path) -> dict[str, list[dict]]:
    output = {}
    for engine in ENGINE_NAMES:
        rows = [row for row in read_jsonl(data_dir / f"{engine}.jsonl")
                if row.get("status") == "ok"]
        seen = {row["request_id"] for row in rows}
        expected = complete_request_ids(engine)
        if seen != expected:
            raise RuntimeError(f"cannot create final charts: {engine} has "
                               f"{len(seen)}/{len(expected)} valid responses")
        output[engine] = rows
    return output


def _social_preview(rows_by_engine: dict[str, list[dict]], output: Path,
                    display: FontProperties, body: FontProperties, bold: FontProperties):
    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
    fig.text(0.055, 0.80, "Decision Models\nAre Not Calculators", color=INK,
             fontproperties=_font(display.get_file(), 39), linespacing=0.95, va="top")
    fig.text(0.058, 0.57, "A fair die. Every choice order. Three decision models.",
             color=MUTED, fontproperties=_font(body.get_file(), 12.5), va="top")
    fig.text(0.058, 0.48, "8,640 requests  ·  2,880 per model", color=INK,
             fontproperties=_font(bold.get_file(), 11.5), va="top")
    fig.text(0.058, 0.12, "Mean returned probability by semantic face\n"
             "for digit labels  ·  uniform reference = 16.7%", color=MUTED,
             fontproperties=_font(body.get_file(), 8.5), va="bottom", linespacing=1.4)

    ax = fig.add_axes([0.48, 0.16, 0.47, 0.64], facecolor=BG)
    ax.set_title("Digit labels", loc="left", color=INK,
                 fontproperties=_font(bold.get_file(), 12), pad=12)
    y = np.arange(3)
    width = 0.105
    face_offsets = np.linspace(-0.26, 0.26, 6)
    for index, face in enumerate(FACES):
        vals = []
        for engine in ENGINE_NAMES:
            selected = [r["probabilities_by_face"][face] for r in rows_by_engine[engine]
                        if r["representation"] == "digits"]
            vals.append(float(np.mean(selected)))
        color = FACE_ONE if face == "1" else FACE_SIX if face == "6" else OTHER
        ax.barh(y + face_offsets[index], vals, height=width, color=color, edgecolor="none",
                label=f"Face {face}")
    ax.axvline(1 / 6, color=INK, linestyle=(0, (3, 3)), linewidth=1, alpha=0.65)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, .25, .5, .75, 1], labels=["0", "25%", "50%", "75%", "100%"])
    ax.set_yticks(y, [ENGINE_LABEL[e] for e in ENGINE_NAMES])
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelcolor=INK, labelsize=9, length=0, pad=7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(ncol=6, loc="lower center", bbox_to_anchor=(0.5, -0.30), frameon=False,
              prop=_font(body.get_file(), 8), handlelength=1.2, columnspacing=1)
    fig.savefig(output, dpi=100, facecolor=BG)
    plt.close(fig)


def generate(data_dir: Path, image_dir: Path) -> list[Path]:
    """Generate all plots only after the full, successful matrix is present."""
    rows_by_engine = _complete_rows(data_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    font_dir = Path(__file__).resolve().parents[2] / "assets" / "fonts"
    display = FontProperties(fname=str(font_dir / "Jersey25-Regular.ttf"))
    body = FontProperties(fname=str(font_dir / "Montserrat-Regular.ttf"))
    bold = FontProperties(fname=str(font_dir / "Montserrat-Bold.ttf"))
    files: list[Path] = []

    social = image_dir / "decision-models-are-not-calculators-cover.png"
    _social_preview(rows_by_engine, social, display, body, bold)
    files.append(social)

    fig, axes = plt.subplots(3, 2, figsize=(14, 11), sharex=True, sharey=True,
                             facecolor=BG, constrained_layout=True)
    fig.suptitle("Same die, same model, different labels", color=INK,
                 fontproperties=_font(display.get_file(), 30))
    for row_index, engine in enumerate(ENGINE_NAMES):
        engine_rows = rows_by_engine[engine]
        for col_index, representation in enumerate(REPRESENTATIONS):
            ax = axes[row_index, col_index]
            records = [record for record in engine_rows
                       if record["representation"] == representation]
            means = [np.mean([r["probabilities_by_face"][face] for r in records])
                     for face in FACES]
            ax.bar(FACES, means, color=[FACE_ONE if face == "1" else
                                        FACE_SIX if face == "6" else OTHER
                                        for face in FACES], width=0.68)
            ax.axhline(1 / 6, color=INK, linestyle=(0, (3, 3)), linewidth=1, alpha=0.6)
            ax.set_title(f"{ENGINE_LABEL[engine]}  ·  "
                         f"{'digits' if representation == 'digits' else 'words'}",
                         loc="left", color=INK, fontproperties=_font(bold.get_file(), 12))
            ax.set_ylim(0, 1)
            ax.set_yticks([0, .25, .5, .75, 1], labels=["0", ".25", ".50", ".75", "1.0"])
            ax.set_xticks(range(1, 7), [f"{face} / {word}" for face, word in
                                        zip(FACES, ("one", "two", "three", "four", "five", "six"))])
            ax.grid(axis="y", color=GRID, linewidth=0.7)
            ax.set_axisbelow(True)
            ax.tick_params(axis="both", labelcolor=INK, labelsize=8, length=0, pad=5)
            for spine in ax.spines.values():
                spine.set_visible(False)
    fig.text(0.006, 0.5, "Mean returned probability", rotation="vertical", va="center",
             color=MUTED, fontproperties=_font(body.get_file(), 10))
    fig.text(0.5, -0.005, "Semantic die face (digit label / word label)", ha="center",
             color=MUTED, fontproperties=_font(body.get_file(), 10))
    probabilities = image_dir / "decision-models-face-probabilities.png"
    fig.savefig(probabilities, dpi=160, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    files.append(probabilities)

    fig, axes = plt.subplots(3, 2, figsize=(14, 10), sharex=True, sharey=True,
                             facecolor=BG, constrained_layout=True)
    fig.suptitle("Changing only the order of choices changes where models select",
                 color=INK, fontproperties=_font(display.get_file(), 27))
    for row_index, engine in enumerate(ENGINE_NAMES):
        for col_index, representation in enumerate(REPRESENTATIONS):
            ax = axes[row_index, col_index]
            counts = Counter(record["choice_position"] for record in rows_by_engine[engine]
                             if record["representation"] == representation)
            denominator = sum(record["representation"] == representation
                              for record in rows_by_engine[engine])
            positions = np.arange(1, 7)
            rates = [counts[position] / denominator for position in positions]
            ax.plot(positions, rates, marker="o", color=ENGINE_COLOR[engine], linewidth=2.3)
            ax.axhline(1 / 6, color=INK, linestyle=(0, (3, 3)), linewidth=1, alpha=0.6)
            ax.set_title(f"{ENGINE_LABEL[engine]}  ·  "
                         f"{'digits' if representation == 'digits' else 'words'}",
                         loc="left", color=INK, fontproperties=_font(bold.get_file(), 12))
            ax.set_ylim(0, 1)
            ax.set_yticks([0, .25, .5, .75, 1], labels=["0%", "25%", "50%", "75%", "100%"])
            ax.set_xticks(positions)
            ax.grid(axis="y", color=GRID, linewidth=0.7)
            ax.set_axisbelow(True)
            ax.tick_params(axis="both", labelcolor=INK, labelsize=8, length=0, pad=5)
            for spine in ax.spines.values():
                spine.set_visible(False)
    fig.text(0.006, 0.5, "Share of responses selected at each list position",
             rotation="vertical", va="center", color=MUTED,
             fontproperties=_font(body.get_file(), 10))
    fig.text(0.5, -0.005, "Position of selected choice (each face balanced at each position)",
             ha="center", color=MUTED, fontproperties=_font(body.get_file(), 10))
    position_plot = image_dir / "decision-models-option-position.png"
    fig.savefig(position_plot, dpi=160, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    files.append(position_plot)
    return files
