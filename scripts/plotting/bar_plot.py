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
                    linewidth:float=2,
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


def stacked_barplot(data,
                    title,
                    stacking_column,
                    xcol,
                    ycol,
                    xlabel='',
                    ylabel='',
                    linewidth: float = 2,
                    title_loc='left',
                    figsize=(7, 4.5),
                    ax=None,
                    xlim=None,
                    ylim=None,
                    legend=False,
                    legend_loc=(0.5, -0.2),
                    legend_ncol=3,
                    higher_lower_is_better=None,
                    higher_lower_is_better_loc=(0.85, 1.2),
                    yscale=None,
                    normalize=False):
    """
    Create a stacked column plot
    
    Parameters:
    -----------
    data : pandas.DataFrame
        Data to plot
    title : str
        Plot title
    stacking_column : str
        Column name for stacking categories
    xcol : str
        Column name for x-axis
    ycol : str
        Column name for y-axis values
    xlabel : str
        X-axis label
    ylabel : str
        Y-axis label
    linewidth : float
        Edge line width
    title_loc : str
        Title location ('left', 'center', 'right')
    figsize : tuple
        Figure size (width, height)
    ax : matplotlib axis
        Existing axis to plot on
    xlim : tuple
        X-axis limits
    ylim : tuple
        Y-axis limits
    legend : bool
        Whether to show legend
    legend_loc : tuple
        Legend location
    legend_ncol : int
        Number of legend columns
    higher_lower_is_better : str
        'higher' or 'lower' to indicate direction
    higher_lower_is_better_loc : tuple
        Location for the better direction text
    yscale : str
        Y-axis scale ('linear', 'log', etc.)
    normalize : bool
        Whether to normalize to 100% stacked
    """
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    # Pivot data for stacking
    pivot_data = data.pivot_table(index=xcol, columns=stacking_column, values=ycol, aggfunc='sum', fill_value=0)
    
    # Normalize if requested (for percentage stacking)
    if normalize:
        pivot_data = pivot_data.div(pivot_data.sum(axis=1), axis=0) * 100
    
    colors = sns.color_palette("pastel")
    
    sns.set_theme()
    sns.set_style("whitegrid")
    
    # Create stacked bar plot
    pivot_data.plot(kind='bar', 
                   stacked=True, 
                   ax=ax, 
                   color=colors,
                   edgecolor='black',
                   linewidth=linewidth,
                   width=0.8)
    
    # Apply hatching patterns if available
    for i, (bars, color, hatch) in enumerate(zip(ax.containers, colors, hatches[3:])):
        for idx,bar in enumerate(bars):
            #bar.set_color(colors[idx])
            bar.set_color(color)
            bar.set_edgecolor("black")
            bar.set_hatch(hatch)

    # If hatches is not defined, just apply colors
    #for i, (bars, color) in enumerate(zip(ax.containers, colors)):
    #    for bar in bars:
    #        bar.set_color(color)
    #        bar.set_edgecolor("black")
    
    ax.set_title(title, fontweight='bold', loc=title_loc)
    
    if xlim is not None:
        ax.set_xlim(xlim)
    
    if ylim is not None:
        ax.set_ylim(ylim)
    else:
        ax.set_ylim(0, None)
    
    if higher_lower_is_better:
        if higher_lower_is_better == 'higher':
            text = "Higher is better ↑"
        else:
            text = "Lower is better ↓"
        
        ax.text(*higher_lower_is_better_loc, text, transform=ax.transAxes, 
                fontsize=FONTSIZE, fontweight="bold", color="midnightblue")
    
    ax.set_ylabel(ylabel, color='black')
    ax.set_xlabel(xlabel, color='black')
    
    if yscale is not None:
        ax.set_yscale(yscale)
    
    if legend:
        ax.legend(loc="lower center", ncol=legend_ncol, bbox_to_anchor=legend_loc, 
                 fontsize=FONTSIZE, title=stacking_column)
    else:
        ax.legend_.remove()
    
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    
    plt.tight_layout()
    return ax

def stacked_grouped_barplot(data,
                           title,
                           grouping_column,
                           stacking_column,
                           xcol,
                           ycol,
                           xlabel='',
                           ylabel='',
                           linewidth:float=2,
                           title_loc='left',
                           figsize=(10, 6),
                           spacing=0.8,
                           ax=None,
                           xlim=None,
                           ylim=None,
                           legend=False,
                           legend_loc=(0.5, -0.2),
                           legend_ncol=3,
                           higher_lower_is_better=None,
                           higher_lower_is_better_loc=(0.85, 1.2),
                           yscale=None,
                           normalize=False,
                           xticks=True):
    """
    Create a grouped stacked barplot
    
    Parameters:
    -----------
    data : pandas.DataFrame
        Data to plot
    title : str
        Plot title
    grouping_column : str
        Column name for grouping (creates separate bar groups)
    stacking_column : str
        Column name for stacking within each group
    xcol : str
        Column name for x-axis categories
    ycol : str
        Column name for y-axis values
    spacing : floathex_colors = [seaborn.utils.rgb2hex(color) for color in colors]

        Spacing between groups (0.8 = 80% of available space)
    normalize : bool
        Whether to normalize each group to 100% stacked
    """
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    # Create a hierarchical pivot table
    pivot_data = data.pivot_table(
        index=xcol, 
        columns=[grouping_column, stacking_column], 
        values=ycol, 
        aggfunc='sum', 
        fill_value=0
    )
    
    # Get unique groups and categories
    groups = pivot_data.columns.get_level_values(0).unique()
    categories = pivot_data.columns.get_level_values(1).unique()
    
    # Set up positioning
    x_labels = pivot_data.index
    n_groups = len(groups)
    n_categories = len(x_labels)
    
    # Calculate bar width and positions
    group_width = spacing / n_groups
    bar_positions = np.arange(len(x_labels))

    new_hatches = [hatches[7], hatches[8], hatches[2], hatches[3]]

    # Colors for stacking
    colors = sns.color_palette("pastel")
    
    sns.set_theme()
    sns.set_style("whitegrid")
    
    # Plot each group
    for i, group in enumerate(groups):
        # Get data for this group
        group_data = pivot_data[group].fillna(0)
        
        # Normalize if requested
        if normalize:
            group_data = group_data.div(group_data.sum(axis=1), axis=0) * 100
        
        # Calculate positions for this group
        positions = bar_positions + (i - n_groups/2 + 0.5) * group_width
        
        # Create stacked bars for this group
        bottom = np.zeros(len(x_labels))
        
        for j, category in enumerate(categories):
            if category in group_data.columns:
                values = group_data[category].values
                
                # Create label that combines both category and group info
                if i == 0:
                    label = f'{category}'  # First group shows category
                else:
                    label = ""  # Other groups don't show in legend
                
                bars = ax.bar(positions, values, 
                            width=group_width * 0.9,  # Slightly narrower for visual separation
                            bottom=bottom,
                            color=colors[j],
                            edgecolor='black',
                            linewidth=2,
                            label=label,
                            hatch=new_hatches[i % len(new_hatches)],)
                
                bottom += values
    
    # Set x-axis labels and ticks
    if xticks:
        ax.set_xticks(bar_positions)
        ax.set_xticklabels(x_labels)
    
    # Add group labels - improved visibility
    #if len(groups) > 1:
    #    # Add group labels with better positioning
    #    for i, group in enumerate(groups):
    #        positions = bar_positions + (i - n_groups/2 + 0.5) * group_width
    #        for pos in positions:
    #            ax.text(pos, ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.08, 
    #                   str(group), ha='center', va='top', fontsize=9, 
    #                   fontweight='bold', color='black')
    
    ax.set_title(title, fontweight='bold', loc=title_loc)
    
    if xlim is not None:
        ax.set_xlim(xlim)
    
    if ylim is not None:
        ax.set_ylim(0, ylim)
    else:
        ax.set_ylim(0, None)
    
    if higher_lower_is_better:
        if higher_lower_is_better == 'higher':
            text = "Higher is better ↑"
        else:
            text = "Lower is better ↓"
        
        ax.text(*higher_lower_is_better_loc, text, transform=ax.transAxes, 
                fontsize=12, fontweight="bold", color="midnightblue")
    
    ax.set_ylabel(ylabel, color='black')
    ax.set_xlabel(xlabel, color='black')
    
    if yscale is not None:
        ax.set_yscale(yscale)
    
    if legend:
        # Create legend for stacking categories only
        stack_handles = []
        for j, category in enumerate(categories):
            handle = plt.Rectangle((0,0), 1, 1, 
                                 color=colors[j], 
                                 edgecolor='black', 
                                 linewidth=linewidth)
            stack_handles.append(handle)

        # Create the main legend for categories
        ax.legend(stack_handles, categories, 
                  loc=legend_loc, 
                  ncol=legend_ncol,
                  fontsize=12, 
                  title='')

        if xticks:
            # Handle group labels in the x-axis area
            if len(groups) > 1:
                # Clear existing x-axis labels
                ax.set_xticklabels([])

                # Create custom x-axis with both category and group labels
                for x_idx, x_label in enumerate(x_labels):
                    # Main x-axis label (category) #-0.13
                    ax.text(x_idx, -0.03, str(x_label), 
                           ha='center', va='top', 
                           transform=ax.get_xaxis_transform(),
                           fontsize=11, fontweight='bold')

                    '''
                    # Group labels for each bar in this x-category
                    for i, group in enumerate(groups):
                        bar_pos = x_idx + (i - n_groups/2 + 0.5) * group_width

                        ax.text(bar_pos, -0.03, f'{group}', 
                               ha='center', va='top', 
                               transform=ax.get_xaxis_transform(),
                               fontsize=9, 
                               color='black',
                               style='italic')
                    '''

    else:
        if ax.legend_:
            ax.legend_.remove()
        plt.rcParams['pdf.fonttype'] = 42
        plt.rcParams['ps.fonttype'] = 42

    for spine in ax.spines.values():
        spine.set_edgecolor('black')

    ax.xaxis.set_label_coords(0.5, -0.15)
    ax.set_xlabel('')

    return ax