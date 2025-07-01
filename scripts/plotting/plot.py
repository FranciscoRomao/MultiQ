#from qiskit.transpiler.passes import SabreLayout
from qiskit import QuantumCircuit
import warnings
warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

import numpy as np
import pandas as pd
from plot import grouped_bar_plot, plot_line, stacked_grouped_bar_plot
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mtick

plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

n_variables = [20, 100, 250]

def plot_compilation_time():

    data_atomique = pd.read_csv('results/atomique_results.csv')
    data_geyser = pd.read_csv('results/geyser_results.csv')
    data_superconducting = pd.read_csv('results/superconducting_results.csv')
    data_weaver = pd.read_csv('results/weaver_results.csv')
    data_dpqa = pd.read_csv('results/dpqa_results.csv')

    data = []
    #fig, ax = plt.subplots(1,2, figsize=(20, 4.5)) - paper
    fig, ax = plt.subplots(1,1, figsize=(7, 4.5))

    #benchmarks = ['uf20-01', 'uf20-02', 'uf20-03', 'uf20-04', 'uf20-05', 'uf20-06', 'uf20-07', 'uf20-08', 'uf20-09', 'uf20-10', 'Mean'] - paper
    benchmarks = ['uf20-01', 'uf20-02', 'uf20-03', 'uf20-04', 'Mean']

    data = []

    for var in n_variables:
        atomique_compilation_time = data_atomique[data_atomique['n_variables']==var]['compilation_time'].mean()
        geyser_compilation_time = data_geyser[data_geyser['n_variables']==var]['runtime'].mean()
        superconducting_compilation_time = np.array(data_superconducting[data_superconducting['n_variables']==var]['runtime']).mean()
        weaver_compilation_time = data_weaver[data_weaver['ccz_fidelity']==0.98][data_weaver['num_variables']==var]['compilation_time (seconds)'].mean()
        dpqa_compilation_time = data_dpqa[data_dpqa['n_variables']==var]['compile_time'].mean()
        data.append([superconducting_compilation_time, atomique_compilation_time, weaver_compilation_time, dpqa_compilation_time, geyser_compilation_time])
    

    data = np.array(data)
    print(data)

    '''
    [[3.72214489e+00 1.93267910e+00 4.21629667e-02 1.29484442e+04 1.54951740e+03]
 [2.53974207e+01 1.75359244e+01 6.76959634e-01            nan
             nan]
 [           nan 6.42368088e+01 3.70936790e+00            nan
             nan]]
    '''

    grouped_bar_plot(ax, data, bar_labels=['Superconducting', 'Atomique', 'Weaver', 'DPQA', 'Geyser'], group_labels=[str(i) for i in n_variables])

    ax.set_yscale('log')
    #ax.set_title('Compilation time', fontweight='bold', loc='left')

    num_groups, num_bars = data.shape
    print(num_groups, num_bars)
    spacing = 0.95
    bar_width = None

    if bar_width == None:
        bar_width = spacing / (num_bars + 1)

    bar_width = bar_width * 1.1

    ax.set_xlim(-0.3, 3)

    for nan_n in range(5):
        for j in range(num_groups):
            if np.isnan(data[j][nan_n]):
                ax.text((nan_n+j*5)//5+nan_n*bar_width, 10**-1.63, "X", ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.text(
        2.3,
        10**4.5,
        "Lower is better ↓",
        ha="center",
        fontsize=14,
        fontweight="bold",
        color="midnightblue",
    )

    ax.set_xlabel('Number of variables')
    ax.set_ylabel('Compilation time [s]')

    #ax[0].set_xlabel('MAX-3SAT Benchmark Suite')
    #ax[0].legend(loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.285), fontsize=13)
    ax.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.45), fontsize=11)

    plt.subplots_adjust(bottom=0.22)
    plt.tight_layout()

    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42

    output_file = 'plots/figure9.png'
    plt.savefig(output_file, dpi=600)
    

def plot_execution_time():
        # Execution time fixed 20 variables

        data_atomique = pd.read_csv('results/atomique_results.csv')
        data_geyser = pd.read_csv('results/geyser_results.csv')
        data_superconducting = pd.read_csv('results/superconducting_results.csv')
        data_weaver = pd.read_csv('results/weaver_results.csv')
        data_dpqa = pd.read_csv('results/dpqa_results.csv')

        data = []
        fig, ax = plt.subplots(1,1, figsize=(7, 4.5))

        spacing = 0.95
        
        # Execution time variable

        data = []
        for var in n_variables:
            atomique_execution_time = data_atomique[data_atomique['n_variables']==var]['execution_time'].mean()# * 1e6
            geyser_execution_time = data_geyser[data_geyser['n_variables']==var]['execution_time'].mean() / 1e6
            superconducting_execution_time = np.array(data_superconducting[data_superconducting['n_variables']==var]['execution_time']).mean()# * 1e6
            weaver_execution_time = data_weaver[data_weaver['ccz_fidelity']==0.98][data_weaver['num_variables']==var]['execution_time (microseconds)'].mean() / 1e6
            dpqa_execution_time = data_dpqa[data_dpqa['n_variables']==var]['eps'].mean()

            data.append([superconducting_execution_time, atomique_execution_time, weaver_execution_time, dpqa_execution_time, geyser_execution_time])

        data = np.array(data)

        num_groups, num_bars = data.shape

        num_groups, num_bars = data.shape
        spacing = 0.95
        bar_width = None

        if bar_width == None:
            bar_width = spacing / (num_bars + 1)

        bar_width = bar_width * 1.1

        grouped_bar_plot(ax, data, bar_labels=['Superconducting', 'Atomique', 'Weaver', 'DPQA', 'Geyser'], group_labels=[str(i) for i in n_variables], edgecolor='black')

        ax.text(
            2.3,
            4,
            "Lower is better ↓",
            ha="center",
            fontsize=14,
            fontweight="bold",
            color="midnightblue",
        )

        #ax.set_title('(b) Execution time - Variable size', fontweight='bold', loc='left')

        ax.set_yscale('log')

        ax.set_xlabel('Number of variables')

        #ax.set_xlabel('MAX-3SAT Benchmark Suite')
        ax.set_ylabel('Execution time [s]')

        ax.set_xlim(-0.3, 3)

        for nan_n in range(5):
            for j in range(num_groups):
                if np.isnan(data[j][nan_n]):
                    ax.text((nan_n+j*5)//5+nan_n*bar_width, 10**-3.65, "X", ha='center', va='bottom', fontsize=12, fontweight='bold')

        #ax[0].legend(loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.285), fontsize=13)

        ax.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.4), fontsize=13)

        plt.subplots_adjust(bottom=0.3)

        plt.tight_layout()

        plt.rcParams['pdf.fonttype'] = 42
        plt.rcParams['ps.fonttype'] = 42

        output_file = 'plots/figure11.png'
        plt.savefig(output_file, dpi=600)


def plot_analysis():

        data = []
        fig, ax = plt.subplots(1, 3, figsize=(14, 4))
        spacing = 0.95

        data_atomique = pd.read_csv('results/atomique_results.csv')
        data_geyser = pd.read_csv('results/geyser_results.csv')
        data_superconducting = pd.read_csv('results/superconducting_results.csv')
        data_weaver = pd.read_csv('results/weaver_results.csv')
        data_dpqa = pd.read_csv('results/dpqa_results.csv')

        var = 20

        n_qubits = range(20,200)

        superconducting_complexity = [n_qubits[i]**3 for i in range(len(n_qubits))]

        weaver_complexity = [n_qubits[i]**2 for i in range(len(n_qubits))]

        atomique_complexity = [n_qubits[i]**2.8 for i in range(len(n_qubits))]

        geyser_complexity = [5789.6487*n_qubits[i]**2 - 87825.2997*n_qubits[i] - 103601.8515 for i in range(len(n_qubits))]

        dpqa_complexity = [2**n_qubits[i] for i in range(len(n_qubits))]
        
        df = pd.DataFrame({'n_qubits': list(n_qubits),
                           'Superconducting': superconducting_complexity,
                           'Weaver': weaver_complexity,
                           'Geyser': geyser_complexity,
                           'Atomique': atomique_complexity,
                           'DPQA': dpqa_complexity})
        
        df_melted = df.melt('n_qubits', var_name='complexity_type', value_name='complexity')

        sns.set_theme()
        sns.set_style("whitegrid")
        ax[0].set_yscale('log')

        sns.lineplot(ax=ax[0], x='n_qubits', y='complexity', hue='complexity_type', data=df_melted, linewidth=2)

        ax[0].set_ylim(1e2, 1e20)

        ax[0].legend().set_title('')
        ax[0].legend().set_bbox_to_anchor((0.45, 0.45))

        ax[0].text(105, 10**20.1, "Lower is better ↓", ha='center', va='bottom', fontsize=14, fontweight='bold', color='midnightblue')

        ax[0].text(190, 10**18.5, "10⁶⁰", ha='center', va='bottom', fontsize=14, fontweight='bold', color=sns.color_palette()[4])

        ax[0].text(150, 10**18.5, "10⁴⁵", ha='center', va='bottom', fontsize=14, fontweight='bold', color=sns.color_palette()[4])

        ax[0].set_title('(a) Complexity Comparison', fontweight='bold', pad=20)

        ax[0].set_xlabel('Number of variables')
        ax[0].set_ylabel('Complexity [Number of steps]')

        FONTSIZE = 12

        #--------------------------------------------------------------------

        data = []

        for var in n_variables:
            weaver_gates1q = data_weaver[data_weaver['num_variables']==var][data_weaver['ccz_fidelity']==0.98]['#u3'].mean()
            weaver_gates2q = data_weaver[data_weaver['num_variables']==var][data_weaver['ccz_fidelity']==0.98]['#cz'].mean()
            weaver_gates3q = data_weaver[data_weaver['num_variables']==var][data_weaver['ccz_fidelity']==0.98]['#ccz'].mean()

            dpqa_gates1q = data_dpqa[data_dpqa['n_variables']==var]['1q_gates'].mean()
            dpqa_gates2q = data_dpqa[data_dpqa['n_variables']==var]['2q_gates'].mean() 

            atomique_gates1q = data_atomique[data_atomique['n_variables']==var]['n_1q_gate'].mean()
            atomique_gates2q = data_atomique[data_atomique['n_variables']==var]['n_2q_gate'].mean()
    
            geyser_pulses = data_geyser[data_geyser['n_variables']==var]['n_pulses'].mean()

            weaver_pulses = weaver_gates1q + weaver_gates2q*3 + weaver_gates3q*5

            atomique_pulses = atomique_gates1q + atomique_gates2q*3

            print(atomique_pulses, weaver_pulses, atomique_pulses/weaver_pulses)

            dpqa_pulses = dpqa_gates1q + dpqa_gates2q*3

            data.append([atomique_pulses, weaver_pulses, geyser_pulses, dpqa_pulses])

        data = np.array(data)

        grouped_bar_plot(ax[1], data, bar_labels=['Atomique', 'Weaver', 'Geyser', 'DPQA'], group_labels=[str(i) for i in n_variables])

        spacing = 0.95

        num_groups, num_bars = data.shape

        bar_width = None

        if bar_width == None:
            bar_width = spacing / (num_bars + 1)

        bar_width = bar_width * 1.1

        ax[1].set_yscale('log')

        for nan_n in range(4):
            for j in range(num_groups):
                if np.isnan(data[j][nan_n]):
                    ax[1].text((nan_n+j*num_groups)//num_groups+nan_n*bar_width, 10**2.81, "X", ha='center', va='bottom', fontsize=9, fontweight='bold')

        ax[1].set_title('(b) Number of pulses', fontweight='bold', pad=20)

        ax[1].set_xlim(-0.3, 5.85)

        ax[1].set_ylabel('Number of pulses')

        ax[1].set_xlabel('Number of variables')

        ax[1].legend(loc="upper left", ncol=1)

        #--------------------------------------------------------------------
    
        data = []

        fids = [0.9775, 0.98, 0.9825, 0.985, 0.9875, 0.99, 0.9925, 0.995, 0.9975]

        for var in fids:
            weaver_fidelity = data_weaver[data_weaver['ccz_fidelity']==var][data_weaver['num_variables']==n_variables[0]]['eps (fidelity)'].mean()
            data.append(weaver_fidelity)

        atomique_fidelity = data_atomique[data_atomique['n_variables']==n_variables[0]]['total_fidelity'].mean()
        superconducting_fidelity = np.array(data_superconducting[data_superconducting['n_variables']==n_variables[0]]['eps']).mean()
        dpqa_fidelity = data_dpqa[data_dpqa['n_variables']==n_variables[0]]['eps'].mean()

        data = [[data[i],fids[i]] for i in range(len(fids))]
        
        data = pd.DataFrame(data, columns=['ccz_fidelity', 'eps'])

        sns.set_theme()
        sns.set_style("whitegrid")

        sns.lineplot(ax=ax[2], data=data, x='eps', y='ccz_fidelity', label='Weaver', markers='o', linewidth=2, legend=False)

        ax[2].set_ylabel('Estimated probability of success (eps)')

        ax[2].set_title('(c) CCZ fidelty threshold', fontweight='bold', pad=20)

        ax[2].set_xlabel('CCZ Gate fidelity')

        #higher is better
        ax[2].text(0.988, 0.127, "Higher is better ↑", ha='center', va='bottom', fontsize=14, fontweight='bold', color='midnightblue')

        ax[2].text(0.9916, dpqa_fidelity-0.006, "X", ha='center', va='bottom', fontsize=18, fontweight='bold', color='r')
        ax[2].hlines(atomique_fidelity, label='Atomique', colors='r', linestyles='dashed', xmin=0.9775, xmax=0.9975, linewidth=2)
        ax[2].hlines(superconducting_fidelity, label='Superconducting', colors='g', linestyles='dashdot', xmin=0.9775, xmax=0.9975, linewidth=2)
        ax[2].hlines(dpqa_fidelity, label='DPQA', colors='b', linestyles='dotted', xmin=0.9775, xmax=0.9975, linewidth=2)

        ax[2].text(0.985, dpqa_fidelity+0.001, "CCZ Fidelity = 0.9916", ha='center', va='bottom', fontsize=12, fontweight='bold')

        ax[2].legend(loc="upper left", ncol=1)

        plt.gca().yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))

        plt.tight_layout()

        plt.rcParams['pdf.fonttype'] = 42
        plt.rcParams['ps.fonttype'] = 42

        output_file = 'plots/figure10.pdf'
        plt.savefig(output_file)




from ast import List, Tuple
from cProfile import label
import pdb
from .defaults import *
import pandas as pd
import seaborn as sns
import numpy as np
from .defaults import *
import matplotlib.pyplot as plt
from .defaults import COLUMN_FIGSIZE
from matplotlib import gridspec
from itertools import cycle, product


def line_plot_better(data, x, y, xlabel='XLabel', ylabel='YLabel', legend:str|list[str]=None, show_legend=True, title=None):

    fig = plt.figure(figsize=COLUMN_FIGSIZE)
    nrows = 1
    ncols = 1
    gs = gridspec.GridSpec(nrows=nrows, ncols=ncols)
    ax = [fig.add_subplot(gs[i, j]) for i in range(nrows) for j in range(ncols)][0]

    sns.set_theme()
    sns.set_style("whitegrid")
    colors = sns.color_palette("pastel")
    #colors = sns.color_palette("deep")
    ax.grid(True)

    for i, data_i in enumerate(data):
        ax = sns.lineplot(data_i, x=x, y=y, marker=line_markers[i], color=colors[i], dashes=False, label=legend[i] if legend != None else None)

    ax.set_xlabel(xlabel, color='black')
    ax.set_ylabel(ylabel, color='black')
    
    if title != None:
        ax.set_title(title, fontweight='bold')
    return fig




def line_plot(data, x, y, xlabel='XLabel', ylabel='YLabel', legend:str|list[str]=None, show_legend=True, axis=None, save=False, title=None):
    
    if axis == None:
        fig = plt.figure(figsize=COLUMN_FIGSIZE)
        nrows = 1
        ncols = 1
        gs = gridspec.GridSpec(nrows=nrows, ncols=ncols)
        ax = [fig.add_subplot(gs[i, j]) for i in range(nrows) for j in range(ncols)][0]
    else:
        ax = axis

    sns.set_theme()
    sns.set_style("whitegrid")
    ax.grid(True)

    if isinstance(y, list) or isinstance(y, np.ndarray):
        line_data = pd.DataFrame()
        line_data['x'] = x
        line_data.set_index('x', inplace=True)
        colors = sns.color_palette("deep")
        ax.set_xlabel(xlabel, color='black')
        ax.set_ylabel(ylabel, color='black')

        for i in range(len(y)):
            if legend == None:
                sns.lineplot(x=x, y=y[i], ax=ax, marker=line_markers[i], color=colors[i], dashes=False)
            else:
                sns.lineplot(x=x, y=y[i], ax=ax, marker=line_markers[i], color=colors[i], label=legend[i], dashes=False, legend=False if not show_legend else True)

    else:
        line_data = pd.DataFrame()
        line_data['x'] = x
        sns.set_theme()
        sns.set_style("whitegrid")
        colors = sns.color_palette("pastel")
        line_data['y'] = y
        fig, ax1 = plt.subplots()
        sns.lineplot(data=line_data, x='x', y='y', ax=ax1, label=ylabel, marker='o', color=colors[1])
        yticks = np.arange(min(y), max(y), (max(y)-min(y))/10)
        ax1.set_yticks(yticks)
        ax1.legend(loc='upper left')
        ax1.set_ylabel(ylabel, color='black')
        ax1.set_xlabel(xlabel, color='black')

    if title != None:
        ax.set_title(title, fontweight='bold')    

    if axis == None or save:
        return fig



def bar_plot(
    y: np.ndarray,
    bar_labels: list[str],
    colors: list[str] | None = None,
    hatches: list[str] | None = None,
    spacing: float = 2,
    zorder: int = 2000,
    filename: str = None,
    y_integer: bool = False,
    text=None,
    text_pos:tuple=None
    ):
    if colors is None:
        colors = sns.color_palette("pastel")

    #assert len(y.shape) == len(yerr.shape) == 2
    #assert len(y.shape) == 2
    #assert y.shape == yerr.shape

    num_bars = len(y)
    x = np.arange(num_bars)

    fig, ax = plt.subplots()

    color, hatch = colors[:len(y)], hatches[:len(y)]

    bar_width = spacing / (num_bars)

    plt.xticks(rotation=45)

    ax.bar(
        x,
        y,
        bar_width,
        hatch=hatch,
        tick_label=bar_labels,
        #yerr=yerr_bars,
        color=color,
        edgecolor="black",
        linewidth=1.5,
        error_kw=dict(lw=2, capsize=3),
        zorder=zorder,
    )
    if text != None:
        plt.text(*text_pos, text)

    if y_integer:
        y_ticks_integer = np.arange(0, max(y) + 1, (max(y) // 10) + 1)
        ax.set_yticks(ticks=y_ticks_integer)

    save_figure(fig, filename)
    plt.close()


def stacked_grouped_bar_plot(data:pd.DataFrame, value_labels:list[str], groups, group_labels=None, bar_labels=None, ylabel=None, title=None, xlabel=None, bar_width=2):

    ax = plt.subplots()
    colors = sns.color_palette('pastel')

    #xticks = [len(bar_labels)//len(groups)//2 + len(bar_labels)//len(groups)*i for i in range(len(groups))]
    #ax = data.plot.bar(x='groups', y=value_labels, rot=0, width=bar_width, stacked=True, edgecolor='black', linewidth=1.5, alpha=0.7, color=colors, xticks=xticks, figsize=figsize)
    ax = data.plot.bar(x='groups', y=value_labels, rot=0, stacked=True, edgecolor='black', linewidth=1.5, color=colors, figsize=COLUMN_FIGSIZE)

    ##ax = sns.barplot(x='groups', y='max', data=data, hue='bar_labels', palette=colors, edgecolor='black', linewidth=2, alpha=0.7, legend=False, width=bar_width)
    #ax = sns.barplot(x='groups', y='max', data=data, hue='bar_labels', palette=colors[2:3], edgecolor='black', linewidth=2, alpha=1, legend=False, width=bar_width)
    ##ax = sns.barplot(x='groups', y=value_labels[0], data=data, hue='bar_labels', palette=colors[3:4], edgecolor='black', linewidth=2, alpha=0.7, legend=False, width=bar_width)
    ##ax = sns.barplot(x='groups', y='min', data=data, hue='bar_labels', palette=colors[len(groups):], edgecolor='black', linewidth=2, alpha=0.7, legend=False, width=bar_width)
#
    ##for i in ax.containers:
    ##    ax.bar_label(i, label_type='center', fmt='%.2f', fontweight='bold')

    #pdb.set_trace()

    #top_labels = [bar_labels[i] for i in range(len(bar_labels)) for _ in groups]
#
    #for bar, lab in zip(ax.patches[:len(bar_labels)], bar_labels):
    #    plt.text(bar.get_x() + bar.get_width() / 2., 0, '%d' % int(lab), ha='center', va='bottom', fontweight='bold', color='black')
#
    ##ax = sns.barplot(x='groups', y=value_labels[1], data=data, hue='bar_labels', palette=colors[2:3], edgecolor='black', linewidth=2, alpha=1, legend=False, width=bar_width) 
    #ax = sns.barplot(x='groups', y='min', data=data, hue='bar_labels', palette=colors[3:4], edgecolor='black', linewidth=2, alpha=1, legend=False, width=bar_width)
    ##for i in ax.containers:
    ##ax.bar_label(i, label_type='center', labels=groups)
    ##ax.bar_label(ax.containers[1], label_type='center', padding=2)
#
    ##ax = sns.barplot(x='groups', y='min', data=data, hue='bar_labels', palette=colors, edgecolor='black', linewidth=2, alpha=1)
#
    ##sns.set_color_codes('muted')
    ##colors = sns.color_palette("pastel")
    ##ax = sns.barplot(x='bar_labels', y='x2', hue='groups', data=data, label= palette=colors, edgecolor='black', linewidth=1.5)
#
    ##sns.set_color_codes('muted')
    ##colors = sns.color_palette("muted")
    ##ax = sns.barplot(x='bar_labels', y='x1', hue='groups', data=data, palette=colors, edgecolor='black', linewidth=1.5)

    containers_groups1 = [ax.patches[i*(len(bar_labels)//len(groups)):(i+1)*(len(bar_labels)//len(groups))] for i in range(len(groups))]
    containers_groups2 = [ax.patches[len(bar_labels)+i*(len(bar_labels)//len(groups)):len(bar_labels)+(i+1)*(len(bar_labels)//len(groups))] for i in range(len(groups))]

    #for container,hatch,color in zip(containers_groups1, hatches, cycle(colors[:2])):
    #    for bar in container:
    #        bar.set_hatch(hatch)
    #        bar.set_facecolor(color)
#
    #for container,hatch,color in zip(containers_groups2, hatches, cycle(colors[2:4])):
    #    for bar in container:
    #        bar.set_hatch(hatch)
    #        bar.set_facecolor(color)

    for bars, hatch in zip(ax.containers, hatches):
        for bar in bars:
            bar.set_hatch(hatch)

    #plt.bar_label(fo)
            
    
    plt.title(title, fontweight='bold')
    #ax.set_xticklabels(groups)
    plt.xlabel(xlabel, color='black')
    plt.ylabel(ylabel, color='black')
    ax.legend(handles=[ax.patches[0], ax.patches[len(bar_labels)]], loc='upper left', labels=['Compilation Time', 'Execution Time'])
    return plt.gcf()