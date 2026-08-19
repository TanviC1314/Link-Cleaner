# ============================================================
# COMPLETE DENSITY PLOT SCRIPT
# LLM-CN vs KG-CN vs Multi-Agent CN
# ============================================================
#
import sys
import subprocess

# Install required libraries automatically
packages = ["numpy", "matplotlib", "scipy"]

for package in packages:
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            package
        ])

# ============================================================
# IMPORTS
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde


# ============================================================
# ILLUSTRATIVE QUALITY SCORES
# Higher score = better counter-narrative quality
# ============================================================

llm_cn = np.array([
    0.61, 0.63, 0.64, 0.65, 0.66,
    0.67, 0.68, 0.68, 0.69, 0.70,
    0.70, 0.71, 0.71, 0.72, 0.72,
    0.73, 0.74, 0.75, 0.76, 0.77
])

kg_cn = np.array([
    0.68, 0.69, 0.70, 0.71, 0.72,
    0.73, 0.74, 0.74, 0.75, 0.75,
    0.76, 0.76, 0.77, 0.77, 0.78,
    0.79, 0.79, 0.80, 0.81, 0.82
])

multiagent_cn = np.array([
    0.78, 0.79, 0.80, 0.81, 0.82,
    0.83, 0.84, 0.84, 0.85, 0.85,
    0.86, 0.86, 0.87, 0.87, 0.88,
    0.89, 0.89, 0.90, 0.91, 0.92
])


# ============================================================
# CREATE DENSITY CURVES
# ============================================================

x = np.linspace(0.55, 0.96, 500)

llm_density = gaussian_kde(llm_cn)(x)
kg_density = gaussian_kde(kg_cn)(x)
multi_density = gaussian_kde(multiagent_cn)(x)


# ============================================================
# CREATE FIGURE
# ============================================================

plt.figure(figsize=(10, 6))

plt.plot(
    x,
    llm_density,
    linewidth=2.5,
    label="Direct LLM-CN"
)

plt.plot(
    x,
    kg_density,
    linewidth=2.5,
    label="Knowledge-Grounded CN"
)

plt.plot(
    x,
    multi_density,
    linewidth=2.5,
    label="Multi-Agent CN"
)


# Fill areas under curves

plt.fill_between(
    x,
    llm_density,
    alpha=0.15
)

plt.fill_between(
    x,
    kg_density,
    alpha=0.15
)

plt.fill_between(
    x,
    multi_density,
    alpha=0.15
)


# ============================================================
# MEAN LINES
# ============================================================

plt.axvline(
    np.mean(llm_cn),
    linestyle="--",
    linewidth=1.5
)

plt.axvline(
    np.mean(kg_cn),
    linestyle="--",
    linewidth=1.5
)

plt.axvline(
    np.mean(multiagent_cn),
    linestyle="--",
    linewidth=1.5
)


# ============================================================
# LABELS
# ============================================================

plt.title(
    "Distribution of Counter-Narrative Quality Across Generation Methods",
    fontsize=15,
    fontweight="bold"
)

plt.xlabel(
    "Counter-Narrative Quality Score",
    fontsize=12
)

plt.ylabel(
    "Density",
    fontsize=12
)

plt.xlim(0.55, 0.96)

plt.grid(
    linestyle="--",
    alpha=0.25
)

plt.legend(
    fontsize=10,
    frameon=False
)

plt.tight_layout()


# ============================================================
# SAVE HIGH-QUALITY IMAGE
# ============================================================

plt.savefig(
    "cn_quality_density_plot.png",
    dpi=400,
    bbox_inches="tight"
)


# ============================================================
# SHOW GRAPH
# ============================================================

plt.show()


# ============================================================
# PRINT MEAN SCORES
# ============================================================

print("\nMean Counter-Narrative Quality Scores")
print("---------------------------------------")
print(f"Direct LLM-CN       : {np.mean(llm_cn):.3f}")
print(f"Knowledge-Grounded  : {np.mean(kg_cn):.3f}")
print(f"Multi-Agent CN      : {np.mean(multiagent_cn):.3f}")

print("\nPlot saved as: cn_quality_density_plot.png")