import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
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
            bar.set_color(color)
            bar.set_edgecolor("black")
            bar.set_hatch(hatch)

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
                           xticks=True,
                           group_legend_loc=None,
                           group_legend_ncol=None,
                           stack_hatch_map=None,
                           per_bar_group_labels=False,
                           group_label_formatter=str):
    """Grouped stacked bar plot."""
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    pivot_data = data.pivot_table(
        index=xcol, 
        columns=[grouping_column, stacking_column], 
        values=ycol, 
        aggfunc='sum', 
        fill_value=0
    )
    
    groups = pivot_data.columns.get_level_values(0).unique()
    categories = pivot_data.columns.get_level_values(1).unique()
    
    x_labels = pivot_data.index
    n_groups = len(groups)
    n_categories = len(x_labels)
    
    group_width = spacing / n_groups
    bar_positions = np.arange(len(x_labels))

    # Hatches are keyed by compiler name so each compiler keeps the same hatch across plots.
    hatch_map = {
        "MultiQ(1 Row)": hatches[7],
        "MultiQ 1 Row": hatches[7],
        "MultiQ (1 Row)": hatches[7],
        "MultiQ(2 Row)": hatches[8],
        "MultiQ 2 Row": hatches[8],
        "MultiQ (2 Row)": hatches[8],
        "ZAC": hatches[2],
        "PachinQo": hatches[3],
        "Pachinqo": hatches[3],
        "PowerMove": hatches[4],
        "QMAP": hatches[5],
        "ZAP": "+",
    }

    colors = sns.color_palette("pastel")
    
    sns.set_theme()
    sns.set_style("whitegrid")

    ax.grid(axis="y", linestyle="--")
    ax.set_axisbelow(True)

    # Bar positions are stored on the axes so callers can add annotations.
    ax._grouped_bar_positions = {}
    ax._grouped_bar_width = group_width * 0.9

    for i, group in enumerate(groups):
        group_data = pivot_data[group].fillna(0)

        if normalize:
            group_data = group_data.div(group_data.sum(axis=1), axis=0) * 100

        positions = bar_positions + (i - n_groups/2 + 0.5) * group_width
        ax._grouped_bar_positions[group] = dict(zip(x_labels, positions))

        bottom = np.zeros(len(x_labels))

        group_hatch = hatch_map.get(group, hatches[i % len(hatches)])

        for j, category in enumerate(categories):
            if category in group_data.columns:
                values = group_data[category].values

                if i == 0:
                    label = f'{category}'
                else:
                    label = ""

                # A per-stage hatch replaces the group hatch so stages stay distinguishable in grayscale.
                combined_hatch = stack_hatch_map.get(category, '') if stack_hatch_map else group_hatch

                bars = ax.bar(positions, values,
                            width=group_width * 0.9,
                            bottom=bottom,
                            color=colors[j],
                            edgecolor='black',
                            linewidth=2,
                            label=label,
                            hatch=combined_hatch,)

                bottom += values

    if xticks:
        ax.set_xticks(bar_positions)
        ax.set_xticklabels(x_labels)
    
    
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
        stack_handles = []
        for j, category in enumerate(categories):
            handle = plt.Rectangle((0,0), 1, 1,
                                 facecolor=colors[j],
                                 edgecolor='black',
                                 linewidth=linewidth,
                                 hatch=stack_hatch_map.get(category) if stack_hatch_map else None)
            stack_handles.append(handle)

        stage_legend = ax.legend(stack_handles, categories,
                  loc=legend_loc,
                  ncol=legend_ncol,
                  fontsize=12,
                  title='')
        # Group hatch legend, skipped when groups are labeled under each bar.
        if not per_bar_group_labels:
            # ax.legend() replaces the current legend, so keep this one as an artist.
            ax.add_artist(stage_legend)

            group_handles = [
                plt.Rectangle((0, 0), 1, 1,
                             facecolor='white',
                             edgecolor='black',
                             linewidth=linewidth,
                             hatch=hatch_map.get(group, hatches[i % len(hatches)]))
                for i, group in enumerate(groups)
            ]
            resolved_group_legend_loc = group_legend_loc if group_legend_loc is not None else (legend_loc[0], legend_loc[1] - 0.18)
            resolved_group_legend_ncol = group_legend_ncol if group_legend_ncol is not None else len(groups)
            ax.legend(group_handles, groups,
                      loc=resolved_group_legend_loc,
                      ncol=resolved_group_legend_ncol,
                      fontsize=12,
                      title='')

        if xticks:
            if len(groups) > 1:
                ax.set_xticklabels([])

                category_y = -0.14 if per_bar_group_labels else -0.03

                per_bar_fontsize = 11

                for x_idx, x_label in enumerate(x_labels):
                    if per_bar_group_labels:
                        for i, group in enumerate(groups):
                            bar_pos = x_idx + (i - n_groups / 2 + 0.5) * group_width
                            ax.text(bar_pos, -0.03, group_label_formatter(group),
                                   ha='center', va='top',
                                   transform=ax.get_xaxis_transform(),
                                   fontsize=per_bar_fontsize, fontweight='bold',
                                   color='black')

                    ax.text(x_idx, category_y, str(x_label),
                           ha='center', va='top',
                           transform=ax.get_xaxis_transform(),
                           fontsize=11, fontweight='bold')

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