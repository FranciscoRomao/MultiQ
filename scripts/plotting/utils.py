import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec
from .defaults import COLUMN1_FIGSIZE

def gen_subplots(ncols, nrows, figsize=COLUMN1_FIGSIZE):
    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(nrows=nrows, ncols=ncols)
    axes = [fig.add_subplot(gs[i, j]) for i in range(nrows) for j in range(ncols)]

    return fig, axes

def save_figure(fig: plt.Figure, exp_name: str):
    plt.tight_layout()
    fig.savefig(
        exp_name + ".pdf",
        bbox_inches="tight",
    )