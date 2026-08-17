import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================================================
# MODEL COMPARISON VALUES FROM YOUR OVERLEAF TABLE
# =========================================================

data = {
    "BLEU-1": {
        "GPT": 0.1584,
        "Claude": 0.1569,
        "Grok": 0.1481,
        "Gemini": 0.1307
    },

    "BLEU-2": {
        "GPT": 0.0290,
        "Claude": 0.0228,
        "Grok": 0.0170,
        "Gemini": 0.0153
    },

    "METEOR-like": {
        "GPT": 0.2052,
        "Claude": 0.1945,
        "Grok": 0.1858,
        "Gemini": 0.1433
    },

    "ROUGE-L": {
        "GPT": 0.1374,
        "Claude": 0.1326,
        "Grok": 0.1357,
        "Gemini": 0.0907
    }
}

# Keep GPT first
models = ["GPT", "Claude", "Grok", "Gemini"]

df = pd.DataFrame(data).loc[models]

print(df)

# =========================================================
# NORMALIZE EACH METRIC
# Only used for heatmap colour.
# Raw values will still be written inside the cells.
# =========================================================

normalized = (df - df.min()) / (df.max() - df.min())

# =========================================================
# CREATE HEATMAP
# =========================================================

fig, ax = plt.subplots(figsize=(10, 5.8))

im = ax.imshow(
    normalized.values,
    cmap="Blues",
    aspect="auto",
    vmin=0,
    vmax=1
)

# Axis labels
ax.set_xticks(np.arange(len(df.columns)))
ax.set_xticklabels(
    df.columns,
    fontsize=12,
    fontweight="bold"
)

ax.set_yticks(np.arange(len(df.index)))
ax.set_yticklabels(
    df.index,
    fontsize=12,
    fontweight="bold"
)

# =========================================================
# WRITE RAW VALUES INSIDE CELLS
# =========================================================

for i in range(len(df.index)):
    for j in range(len(df.columns)):

        raw_value = df.iloc[i, j]
        norm_value = normalized.iloc[i, j]

        # White text on darker cells
        text_color = "white" if norm_value > 0.60 else "black"

        ax.text(
            j,
            i,
            f"{raw_value:.4f}",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color=text_color
        )

# =========================================================
# GRID BETWEEN CELLS
# =========================================================

ax.set_xticks(
    np.arange(-0.5, len(df.columns), 1),
    minor=True
)

ax.set_yticks(
    np.arange(-0.5, len(df.index), 1),
    minor=True
)

ax.grid(
    which="minor",
    color="white",
    linewidth=3
)

ax.tick_params(which="minor", bottom=False, left=False)

# Put metric names on top
ax.tick_params(
    top=True,
    bottom=False,
    labeltop=True,
    labelbottom=False
)

# =========================================================
# TITLE
# =========================================================

ax.set_title(
    "LLM Comparison for Dataset Augmentation",
    fontsize=17,
    fontweight="bold",
    pad=25
)

# =========================================================
# COLORBAR
# =========================================================

cbar = plt.colorbar(
    im,
    ax=ax,
    fraction=0.035,
    pad=0.04
)

cbar.set_label(
    "Relative Performance",
    fontsize=11
)

# =========================================================
# CLEAN STYLE
# =========================================================

for spine in ax.spines.values():
    spine.set_visible(False)

plt.tight_layout()

# =========================================================
# SAVE HIGH-QUALITY IMAGE FOR OVERLEAF
# =========================================================

plt.savefig(
    "model_selection_heatmap.png",
    dpi=400,
    bbox_inches="tight"
)

plt.show()