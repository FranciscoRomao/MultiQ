import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.ticker as ticker
from matplotlib import gridspec
from .defaults import hatches, FONTSIZE

def grouped_barplot(data,
                    title,
                    grouping_column,
                    xcol,
                    ycol,
                    xlabel='',
                    ylabel='',
                    linewidth=2,
                    title_loc='left',
                    figsize=(7, 4.5),
                    spacing=0.95,
                    capsize=0.1,
                    errorbar=None,
                    ax=None,
                    xlim=None,
                    ylim=None,
                    legend=False,
                    legend_loc=(0.5, -0.2),
                    legend_ncol=3,
                    higher_lower_is_better=None,
                    higher_lower_is_better_loc=(0.85, 1.2),
                    yscale=None):

    if ax is None:
        fig, ax = plt.subplots(1,1, figsize=figsize)

    num_groups, num_bars = data.shape
    bar_width = spacing / (num_bars + 1)
    bar_width = bar_width * 1.1

    colors = sns.color_palette("pastel")

    sns.set_theme()
    sns.set_style("whitegrid")

    ax = sns.barplot(ax=ax, data=data, x=xcol, y=ycol, hue=grouping_column, palette=colors, edgecolor='black', linewidth=linewidth, errorbar=errorbar, capsize=capsize)

    for bars, color, hatch in zip(ax.containers, colors, hatches):
        for i, bar in enumerate(bars):
            #color, hatch = colors[i % len(ax.containers)], hatches[i % len(ax.containers)]
            bar.set_color(color)
            bar.set_edgecolor("black")
            bar.set_hatch(hatch)
            #bar.set_facecolor("none")
            #bar.set_alpha(1)

    ax.set_title(title, fontweight='bold', loc=title_loc)

    if xlim is not None:
        plt.xlim(xlim)

    if ylim is not None:
        plt.ylim(ylim)
    else:
        plt.ylim(0, None)
    
    if higher_lower_is_better:
        if higher_lower_is_better == 'higher':
            text = "Higher is better ↑"
        else:
            text = "Lower is better ↓"

        ax.text(*higher_lower_is_better_loc, text, transform=ax.transAxes, fontsize=FONTSIZE, fontweight="bold", color="midnightblue")

    ax.set_ylabel(ylabel, color='black')

    ax.set_xlabel(xlabel, color='black')

    if yscale is not None:
        ax.set_yscale(yscale)
            
    if legend:
        ax.legend(loc="lower center", ncol=legend_ncol, bbox_to_anchor=legend_loc, fontsize=FONTSIZE)
    else:
        ax.legend_.remove()
      
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    
    #plt.subplots_adjust(bottom=0.25)
    plt.tight_layout()
    return ax
    #plt.savefig(output_file, dpi=600)

def simple_bar_plot(
    ax: plt.Axes,
    df: pd.DataFrame,
    xcol: str = "num_qubits",
    ycol: str = "relative",
    spacing: float = 1.0,
    title='(a1) Fidelity vs Utilization',
    title_loc='left',
    linewidth=1.75,
    higher_lower_is_better='higher',
    higher_lower_is_better_loc=(0.65, 1.04),
    xlabel='QPU Utilization [%]',
    legend=False,
    legend_loc=(0.5, -0.4),
    ylabel='Fidelity',
    ylim=None):
    #assert len(dataframes) == len(labels) > 0

    ax.grid(axis="y", linestyle="--")

    bar_width = spacing / (len(df[ycol].values)) + 1

    bars = sns.barplot(
        ax=ax,
        data=df,
        x=xcol,
        y=ycol,
        palette=sns.color_palette("pastel")[1:],
        edgecolor="black",
        linewidth=linewidth,
        errorbar=None
    )

    for i, bar in enumerate(bars.patches):
        bar.set_hatch(hatches[i % len(hatches)])

    ax.set_title(title, fontweight='bold', loc=title_loc)
    ax.set_xlabel(xlabel, color='black')
    ax.set_ylabel(ylabel, color='black')
    
    if ylim is not None:
        ax.set_ylim(ylim)

    if higher_lower_is_better:
        if higher_lower_is_better == 'higher':
            text = "Higher is better ↑"
        else:
            text = "Lower is better ↓"

        ax.text(*higher_lower_is_better_loc, text, transform=ax.transAxes, fontsize=FONTSIZE, fontweight="bold", color="midnightblue")
    
    if legend:
        ax.legend(loc="lower center", ncol=3, bbox_to_anchor=legend_loc, fontsize=FONTSIZE)

    plt.rcParams['pdf.fonttype'] = 42

'''
def stacked_grouped_barplot(data,
                            title,
                            grouping_column,
                            stacking_cols,
                            group_labels,
                            xcol,
                            ycol,
                            xlabel='',
                            ylabel='',
                            linewidth=2,
                            title_loc='left',
                            figsize=(7, 4.5),
                            spacing=0.95,
                            capsize=0.1,
                            errorbar=None,
                            ax=None,
                            xlim=None,
                            ylim=None,
                            legend=False,
                            legend_loc=(0.5, -0.2),
                            legend_ncol=3,
                            higher_lower_is_better=None,
                            higher_lower_is_better_loc=(0.85, 1.2),
                            yscale=None):

    if ax is None:
        fig, ax = plt.subplots(1,1, figsize=figsize)

    num_groups, num_bars = data.shape
    bar_width = spacing / (num_bars + 1)
    bar_width = bar_width * 1.1

    colors = sns.color_palette("pastel")[1:]

    sns.set_theme()
    sns.set_style("whitegrid")

    plt.figure(figsize=(10, 6))

    stacking_cols_data = data[stacking_cols]

    stacking_cols_cummulative = stacking_cols_data.cumsum(axis=1)

    bar_per_group = len(data[grouping_column].unique())

    for i, bar_per_group in enumerate(stacking_cols.columns):
        plt.bar(df_pivot.index, df_pivot[subcat],
                bottom=df_cum[subcat] - df_pivot[subcat],
                color=colors[i], label=subcat)

    plt.xlabel('Category')
    plt.ylabel('Value')
    plt.title('Stacked Grouped Bar Plot')
    plt.legend(title='Subcategory')
    plt.show()

    ax = sns.barplot(ax=ax, data=data, x=xcol, y=ycol, hue=grouping_column, palette=colors, edgecolor='black', linewidth=linewidth, errorbar=errorbar, capsize=capsize)

    for bars, color, hatch in zip(ax.containers, colors, hatches):
        for i, bar in enumerate(bars):
            #color, hatch = colors[i % len(ax.containers)], hatches[i % len(ax.containers)]
            bar.set_color(color)
            bar.set_edgecolor("black")
            bar.set_hatch(hatch)
            #bar.set_facecolor("none")
            #bar.set_alpha(1)

    ax.set_title(title, fontweight='bold', loc=title_loc)

    if xlim is not None:
        plt.xlim(xlim)

    if ylim is not None:
        plt.ylim(ylim)
    else:
        plt.ylim(0, None)
    
    if higher_lower_is_better:
        if higher_lower_is_better == 'higher':
            text = "Higher is better ↑"
        else:
            text = "Lower is better ↓"

        ax.text(*higher_lower_is_better_loc, text, transform=ax.transAxes, fontsize=FONTSIZE, fontweight="bold", color="midnightblue")

    ax.set_ylabel(ylabel, color='black')

    ax.set_xlabel(xlabel, color='black')

    if yscale is not None:
        ax.set_yscale(yscale)
            
    if legend:
        ax.legend(loc="lower center", ncol=legend_ncol, bbox_to_anchor=legend_loc, fontsize=FONTSIZE)
      
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    
    #plt.subplots_adjust(bottom=0.25)
    plt.tight_layout()

    #plt.savefig(output_file, dpi=600)
'''