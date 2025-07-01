import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.ticker as ticker
from matplotlib import gridspec

from .defaults import hatches, FONTSIZE

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from scipy.interpolate import make_interp_spline

def sharedY_lineplot(data,
                  title,
                  grouping_column,
                  xcol,
                  y1col,
                  y2col,
                  xlabel='',
                  y1label='',
                  y2label='',
                  linewidth=2,
                  title_loc='left',
                  figsize=(7, 4.5),
                  legend=False,
                  legend_loc_y1=(0.5, -0.2),
                  legend_loc_y2=(0.5, -0.2),
                  legend_ncol=3,
                  higher_lower_is_better_y1=None,
                  higher_lower_is_better_y1_loc=(0.85, 1.2),
                  higher_lower_is_better_y2=None,
                  higher_lower_is_better_y2_loc=(0.85, 1.2),
                  yscale=None,
                  ax=None,
                  xlim=None,
                  ylim=None,
                  y1_marker='X',
                  y2_marker='o',
                  markersize=8,
                  smoothing=True,
                  spline_degree=3,
                  num_points_smoothing=100):

    # Set the style for better aesthetics
    sns.set_style("whitegrid")
    colors = sns.color_palette("pastel")

    data['updated_shuttling_time'] = data['updated_shuttling_time']/1000
    data['updated_execution_time'] = data['updated_execution_time']/1000
    
    # Plot first y-axis
    sns.lineplot(data=data[data[grouping_column] == 'Single'], x=xcol, y=y1col, marker=y1_marker, label='Single (Shuttling Time)', ax=ax, color=colors[1], errorbar=None, linewidth=linewidth, markersize=markersize)
    sns.lineplot(data=data[data[grouping_column] == 'Grouped'], x=xcol, y=y1col, marker=y1_marker, label='Grouped (Shuttling Time)', ax=ax, color=colors[2], errorbar=None, linewidth=linewidth, markersize=markersize)
    sns.lineplot(data=data[data[grouping_column] == 'Grouped Independent'], x=xcol, y=y1col, marker=y1_marker, label='Independent Grouped (Shuttling Time)', ax=ax, color=colors[3], errorbar=None, linewidth=linewidth, markersize=markersize)
    ax.set_xlabel(xlabel, color='black')
    ax.set_ylabel(y1label, color='blue')
    ax.tick_params(axis='y', labelcolor='blue')
    ax.set_title(title, fontweight='bold', loc=title_loc)

    if higher_lower_is_better_y1:
        if higher_lower_is_better_y2 == 'higher':
            text = "Higher is better ↑"
        else:
            text = "Lower is better ↓"

        ax.text(*higher_lower_is_better_y1_loc, text, transform=ax.transAxes, fontsize=FONTSIZE, fontweight="bold", color="midnightblue")
    
    if legend:
        ax.legend(loc='upper left', fontsize=FONTSIZE, ncol=legend_ncol)
    else:
        ax.legend_.remove()
    
    #Create the second axes sharing the x-axis
    ax1 = ax.twinx()

    # Plot second y-axis
    sns.lineplot(data=data[data[grouping_column] == 'Single'], x=xcol, y=y2col, marker=y2_marker, linestyle='--', label='Single (Execution Time)', ax=ax1, errorbar=None, linewidth=linewidth, markersize=markersize, color=colors[1])
    sns.lineplot(data=data[data[grouping_column] == 'Grouped'], x=xcol, y=y2col, marker=y2_marker, linestyle='--', label='Grouped (Execution Time)', ax=ax1, color=colors[2], errorbar=None, linewidth=linewidth, markersize=markersize)
    sns.lineplot(data=data[data[grouping_column] == 'Grouped Independent'], x=xcol, y=y2col, marker=y2_marker, linestyle='--', label='Independent Grouped (Execution Time)', ax=ax1, color=colors[3], errorbar=None, linewidth=linewidth, markersize=markersize)
    ax1.set_ylabel(y2label, color='red')
    ax1.tick_params(axis='y', labelcolor='red')
    ax1.legend(loc='upper right')
    
    if higher_lower_is_better_y2:
        if higher_lower_is_better_y2 == 'higher':
            text = "Higher is better ↑"
        else:
            text = "Lower is better ↓"

        ax1.text(*higher_lower_is_better_y2_loc, text, transform=ax.transAxes, fontsize=FONTSIZE, fontweight="bold", color="midnightblue")

    if legend:
        ax1.legend(loc='upper left', fontsize=FONTSIZE, ncol=legend_ncol, bbox_to_anchor=(0.0, 0.85))
    else:
        ax1.legend_.remove()

'''
def lineplot(data,
             title,
             grouping_column,
             group_labels,
             xcol,
             ycol,
             xlabel='',
             ylabel='',
             linewidth=2,
             title_loc='left',
             figsize=(7, 4.5),
             legend=False,
             legend_loc=(0.5, -0.2),
             legend_ncol=3,
             higher_lower_is_better=None,
             higher_lower_is_better_loc=(0.85, 1.2),
             yscale=None,
             ax=None,
             xlim=None,
             ylim=None,
             marker='X',
             markersize=8,
             smoothing=True,
             spline_degree=3,
             num_points_smoothing=100):

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    sns.set_theme()
    sns.set_style("whitegrid")
    colors = sns.color_palette("pastel")[1:]

    grouped_data = data.groupby(grouping_column)

    for i, (group_name, group_df) in enumerate(grouped_data):
        group_df_sorted = group_df.sort_values(by=xcol)
        x_values = group_df_sorted[xcol]
        y_values = group_df_sorted[ycol]
        color = colors[i % len(colors)]

        ax.plot(x_values, y_values, marker=marker, markersize=markersize, linewidth=linewidth, color=color, label=group_name)

        if smoothing and len(x_values) > 2:
            x_smooth = np.linspace(x_values.min(), x_values.max(), num_points_smoothing)
            spl = make_interp_spline(x_values, y_values, k=spline_degree)
            y_smooth = spl(x_smooth)
            ax.plot(x_smooth, y_smooth, linewidth=linewidth * 0.75, alpha=0.7, color=color)

    ax.set_title(title, fontweight='bold', loc=title_loc)

    if xlim is not None:
        ax.set_xlim(xlim)

    if ylim is not None:
        ax.set_ylim(ylim)
    else:
        ax.set_ylim(bottom=0)

    if higher_lower_is_better:
        FONTSIZE = plt.rcParams['font.size']  # Use default font size
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
        ax.legend(loc="lower center", ncol=legend_ncol, bbox_to_anchor=legend_loc, fontsize=plt.rcParams['font.size'])
    else:
        ax.legend_.remove()

    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.tight_layout()
    return ax

if __name__ == '__main__':
    # Example Usage:
    data = pd.DataFrame({
        'Category': ['A', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'C'],
        'Time': [1, 2, 3, 1, 2, 3, 1, 2, 3],
        'Value': [10, 15, 12, 8, 11, 9, 14, 13, 16]
    })

    grouped_lineplot(
        data=data.copy(),
        title='Value Over Time by Category',
        grouping_column='Category',
        group_labels=['A', 'B', 'C'],
        xcol='Time',
        ycol='Value',
        xlabel='Time (Units)',
        ylabel='Measured Value',
        legend=True,
        smoothing=True
    )
    plt.show()

    # Example with more data points for better smoothing
    data_smooth = pd.DataFrame({
        'Group': ['X'] * 10 + ['Y'] * 10,
        'Step': np.linspace(0, 9, 10).tolist() * 2,
        'Score': [5, 7, 6, 8, 7, 9, 8, 10, 9, 11, 6, 8, 7, 9, 8, 10, 9, 11, 10, 12]
    })

    grouped_lineplot(
        data=data_smooth.copy(),
        title='Score Progression',
        grouping_column='Group',
        group_labels=['X', 'Y'],
        xcol='Step',
        ycol='Score',
        xlabel='Step Number',
        ylabel='Score Value',
        legend=True,
        smoothing=True,
        marker='o'
    )
    plt.show()

'''