# %%
import pdb
import yaml
import numpy as np
import pandas as pd
import warnings
from scipy.stats import gmean
from scripts.plotting import bar_plot, line_plot
from scripts.plotting import utils, defaults
import ast
import seaborn as sns
import random
import matplotlib.pyplot as plt
import matplotlib.transforms

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

def plot_shuttling_times_vs_utilization_zac(ax, title):
    # run_preeval_zac() (scripts/run_preeval.py) already tags each row's
    # 'type' (Single/Grouped/Grouped Independent) and precomputes Grouped
    # Independent's execution_time/shuttling_time (max of the group's own
    # sub-circuits' solo runs) at data-collection time, rather than this
    # function trying to reconstruct it after the fact from parsing
    # 'benchmark' name strings.
    data_zac = pd.read_csv("results/preeval/zac_preeval.csv")

    qpu_size_zac = 250
    data_zac['qpu_utilization'] = (data_zac['nqubits'] * 100 // qpu_size_zac).astype(int)
    # shuttling_time is stored raw (microseconds -- summed 'move' sub-
    # instruction durations out of ZAC's compiled-circuit code JSON, see
    # _zac_shuttling_time_us) -- convert to ms for display. NOT
    # execution_time (ZAC's cir_duration): that's the whole schedule's
    # makespan, which also includes gate-execution time layered in around
    # the moves and so roughly doubles the true shuttling time.
    data_zac['shuttling_time_ms'] = data_zac['shuttling_time'] / 1000
    # Drop the 25-qubit/10% point -- PREEVAL_ZAC_GROUP_COUNTS only forms
    # groups landing on 20/40/60/80/100%, so 10% would only ever show a
    # "Single" bar with nothing to compare it against.
    data_zac = data_zac[data_zac['nqubits'] != 25]

    ax.grid(True)

    bar_plot.grouped_barplot(data_zac,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='shuttling_time_ms',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=3,
                             # Matches the original
                             # ~/tmp_MultiQ/plot_preeval_functions.py, which
                             # doesn't show this annotation on either panel
                             # of this figure.
                             higher_lower_is_better=False,
                             higher_lower_is_better_loc=(0.665, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Shuttling time [ms]')
    # grouped_barplot's own default ylim call uses plt.ylim(0, None) against
    # matplotlib's global "current axes" rather than the `ax` passed in --
    # harmless with one pyplot-tracked axes, but with two stacked subplots
    # (see plot_preeval_motivation) it can silently target the other panel
    # before this one has any data, leaving this axes stuck at the
    # empty-axes default (0, 1) even after real bars are drawn. Worse,
    # set_ylim (which plt.ylim delegates to) disables that axis's autoscale
    # flag, so ax.relim()/autoscale_view() afterwards is a no-op -- compute
    # the real bound explicitly instead.
    max_height = max((bar.get_height() for bars in ax.containers for bar in bars), default=1)
    ax.set_ylim(0, max_height * 1.1)
    # No per-axes legend (legend=False above) -- plot_preeval_motivation()
    # builds one shared fig-level legend from this axes' handles/labels
    # instead, matching the original ~/tmp_MultiQ/plot_preeval.py layout.
    ax.text(0.03, 0.94, 'Compiler: ZAC', transform=ax.transAxes, fontsize=defaults.FONTSIZE,
            fontweight='bold', va='top', ha='left')

def plot_shuttling_times_vs_utilization_pachinqo(ax, title):
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")

    qpu_size_zac = 250
    data_pachinqo['qpu_utilization'] = [int(data_pachinqo.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_pachinqo))]
    data_pachinqo['type'] = ['Grouped' if len(data_pachinqo.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_pachinqo))]
    data_pachinqo['grouped_circuits'] = [len(data_pachinqo.iloc[i]['benchmark'].split('_')) for i in range(len(data_pachinqo))]

    for i in range(len(data_pachinqo)):
        if data_pachinqo.iloc[i]['type'] == 'Sequential':
            data_pachinqo.at[i, 'updated_shuttling_time'] = data_pachinqo.iloc[i]['cir_shuttling_time']
            #data_pachinqo.at[i, 'updated_execution_time'] = data_pachinqo.iloc[i]['execution_time']
        else:
            grouped_benchmarks = data_pachinqo.iloc[i]['benchmark'].split('_')

            solo_shuttling_times = []
            solo_exec_times = []

            for j in grouped_benchmarks:
                solo_shuttling_times.append(float(data_pachinqo[data_pachinqo['benchmark'] == j][data_pachinqo['nqubits'] == data_pachinqo.iloc[i]['nqubits']//len(grouped_benchmarks)]['cir_shuttling_time'].mean()))
                #solo_exec_times.append(float(data_pachinqo[data_pachinqo['benchmark'] == j][data_pachinqo['nqubits'] == data_pachinqo.iloc[i]['nqubits']//len(grouped_benchmarks)]['execution_time'].mean()))

            data_pachinqo.at[i, 'updated_shuttling_time'] = data_pachinqo.iloc[i]['cir_shuttling_time']
            #data_pachinqo.at[i, 'updated_execution_time'] = data_pachinqo.iloc[i]['execution_time']

            #add row to data_pachinqo copy of this one with uptated fidelity as g1_2q_mov_trans_avg
            data_pachinqo.loc[len(data_pachinqo)] = data_pachinqo.iloc[i]
            data_pachinqo.at[len(data_pachinqo)-1, 'updated_shuttling_time'] = max(solo_shuttling_times)
            #data_pachinqo.at[len(data_pachinqo)-1, 'updated_execution_time'] = max(solo_exec_times)
            data_pachinqo.at[len(data_pachinqo)-1, 'type'] = 'Grouped Independent'

    data_pachinqo = data_pachinqo[data_pachinqo['nqubits'] != 25]
    data_pachinqo = data_pachinqo[data_pachinqo['nqubits'] != 20]
    data_pachinqo = data_pachinqo[data_pachinqo['nqubits'] != 10]

    data_pachinqo['updated_shuttling_time'] = data_pachinqo['updated_shuttling_time'] / 1000

    bar_plot.grouped_barplot(data_pachinqo,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='updated_shuttling_time',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=3,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=(0.72, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Shuttling time [ms]')
    ax.grid(True)

def plot_shuttling_execution_times_vs_utilization_atomique(ax):
    data_atomique = pd.read_csv("organize/atomique_results.csv")

    qpu_size_atomique = 250
    data_atomique['qpu_utilization'] = [int(data_atomique.iloc[i]['nqubits']*100/qpu_size_atomique) for i in range(len(data_atomique))]
    data_atomique['type'] = ['Grouped' if len(data_atomique.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_atomique))]
    data_atomique['grouped_circuits'] = [len(data_atomique.iloc[i]['benchmark'].split('_')) for i in range(len(data_atomique))]

    for i in range(len(data_atomique)):
        if data_atomique.iloc[i]['type'] == 'Sequential':
            data_atomique.at[i, 'updated_shuttling_time'] = data_atomique.iloc[i]['total_move_distance'] / data_atomique.iloc[i]['avg_move_speed']
            #data_atomique.at[i, 'updated_execution_time'] = data_atomique.iloc[i]['execution_time']
        else:
            grouped_benchmarks = data_atomique.iloc[i]['benchmark'].split('_')

            solo_shuttling_times = []
            solo_exec_times = []

            for j in grouped_benchmarks:
                data1 = data_atomique[data_atomique['benchmark'] == j]
                data2 = data1[data1['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]
                data_updated_shuttling_distance = data_atomique[data_atomique['benchmark'] == j][data_atomique['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_move_distance'].mean()
                data3 = data_updated_shuttling_distance / data_atomique.iloc[i]['avg_move_speed']
                solo_shuttling_times.append(float(data3))
                #solo_shuttling_times.append(float(data_atomique[data_atomique['benchmark'] == j][data_atomique['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]['updated_shuttling_time'].mean()))
                #solo_exec_times.append(float(data_atomique[data_atomique['benchmark'] == j][data_atomique['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]['execution_time'].mean()))

            data_atomique.at[i, 'updated_shuttling_time'] = data_atomique.iloc[i]['total_move_distance'] / data_atomique.iloc[i]['avg_move_speed']
            #data_atomique.at[i, 'updated_execution_time'] = data_atomique.iloc[i]['execution_time']

            data_atomique.loc[len(data_atomique)] = data_atomique.iloc[i]
            data_atomique.at[len(data_atomique)-1, 'updated_shuttling_time'] = max(solo_shuttling_times)
            #data_atomique.at[len(data_atomique)-1, 'updated_execution_time'] = max(solo_exec_times)
            data_atomique.at[len(data_atomique)-1, 'type'] = 'Grouped Independent'

    data_atomique = data_atomique[data_atomique['nqubits'] != 25]
    data_atomique = data_atomique[data_atomique['nqubits'] != 20]
    data_atomique = data_atomique[data_atomique['nqubits'] != 10]

    bar_plot.grouped_barplot(data_atomique,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='updated_shuttling_time',
                             title='(b2) Shuttling time vs Utilization',
                             title_loc='left',
                             errorbar=None,
                             group_labels='',
                             linewidth=1.75,
                             legend_ncol=3,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=(0.65, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Shuttling time [ms]')
    
def plot_compilation_time_vs_utilization_atomique(ax):
    data_atomique = pd.read_csv("organize/atomique_results.csv")

    qpu_size_atomique = 250
    data_atomique['qpu_utilization'] = [int(data_atomique.iloc[i]['nqubits']*100/qpu_size_atomique) for i in range(len(data_atomique))]
    data_atomique['type'] = ['Grouped' if len(data_atomique.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_atomique))]
    data_atomique['grouped_circuits'] = [len(data_atomique.iloc[i]['benchmark'].split('_')) for i in range(len(data_atomique))]

    for i in range(len(data_atomique)):
        if data_atomique.iloc[i]['type'] == 'Sequential':
            data_atomique.at[i, 'updated_comp_time'] = data_atomique.iloc[i]['compilation_time']
        else:
            grouped_benchmarks = data_atomique.iloc[i]['benchmark'].split('_')

            solo_times = []
            for j in grouped_benchmarks:
                solo_times.append(float(data_atomique[data_atomique['benchmark'] == j][data_atomique['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]['compilation_time'].mean()))

            data_atomique.at[i, 'updated_comp_time'] = data_atomique.iloc[i]['compilation_time']

            #add row to data_atomique copy of this one with uptated fidelity as g1_2q_mov_trans_avg
            data_atomique.loc[len(data_atomique)] = data_atomique.iloc[i]
            data_atomique.at[len(data_atomique)-1, 'updated_comp_time'] = max(solo_times)
            data_atomique.at[len(data_atomique)-1, 'type'] = 'Grouped Independent'

    data_atomique = data_atomique[data_atomique['nqubits'] != 25]
    data_atomique = data_atomique[data_atomique['nqubits'] != 20]
    data_atomique = data_atomique[data_atomique['nqubits'] != 10]

    bar_plot.grouped_barplot(data_atomique,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='updated_comp_time',
                             title='(c2) Compilation time vs Utilization',
                             title_loc='left',
                             errorbar=None,
                             group_labels='',
                             linewidth=1.75,
                             legend_ncol=3,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.66, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Compilation time [s]')

def plot_compilation_time_vs_utilization_zac(ax):
    data_zac = pd.read_csv("organize/zac_results.csv")

    qpu_size_zac = 250
    data_zac['qpu_utilization'] = [int(data_zac.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_zac))]
    data_zac['type'] = ['Grouped' if len(data_zac.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_zac))]
    data_zac['grouped_circuits'] = [len(data_zac.iloc[i]['benchmark'].split('_')) for i in range(len(data_zac))]

    for i in range(len(data_zac)):
        if data_zac.iloc[i]['type'] == 'Sequential':
            data_zac.at[i, 'updated_comp_time'] = data_zac.iloc[i]['compilation_time']
        else:
            grouped_benchmarks = data_zac.iloc[i]['benchmark'].split('_')

            solo_times = []
            for j in grouped_benchmarks:
                solo_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['compilation_time'].mean()))

            data_zac.at[i, 'updated_comp_time'] = data_zac.iloc[i]['compilation_time']

            #add row to data_zac copy of this one with uptated fidelity as g1_2q_mov_trans_avg
            data_zac.loc[len(data_zac)] = data_zac.iloc[i]
            data_zac.at[len(data_zac)-1, 'updated_comp_time'] = max(solo_times)
            data_zac.at[len(data_zac)-1, 'type'] = 'Grouped Independent'

    data_zac = data_zac[data_zac['nqubits'] != 25]
    data_zac = data_zac[data_zac['nqubits'] != 20]
    data_zac = data_zac[data_zac['nqubits'] != 10]

    bar_plot.grouped_barplot(data_zac,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='updated_comp_time',
                             title='(c1) Compilation time vs Utilization',
                             title_loc='left',
                             errorbar=None,
                             group_labels='',
                             linewidth=1.75,
                             legend_ncol=3,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.66, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Compilation time [s]')  
    
def plot_fidelity_vs_utilization_zac(ax):
    data_zac = pd.read_csv("results/preeval/zac_preeval.csv")

    qpu_size_zac = 250
    data_zac['qpu_utilization'] = [int(data_zac.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_zac))]
    data_zac['type'] = ['Grouped' if len(data_zac.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_zac))]
    data_zac['grouped_circuits'] = [len(data_zac.iloc[i]['benchmark'].split('_')) for i in range(len(data_zac))]

    for i in range(len(data_zac)):
        if data_zac.iloc[i]['type'] == 'Sequential':
            data_zac.at[i, 'updated_fidelity'] = data_zac.iloc[i]['total_fidelity']
        else:
            #data_zac.at[i, 'updated_fidelity'] = data_zac.iloc[i]['total_fidelity']
            g1q_2q_geo_avg = 1
            g1q_2q_mov_trans_avg = 1
            grouped_benchmarks = data_zac.iloc[i]['benchmark'].split('_')
            for j in grouped_benchmarks:
                g1q_2q_geo_avg *= float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_1q_fidelity'].mean())*float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_2q_fidelity'].mean())
                g1q_2q_mov_trans_avg *= float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_fidelity'].mean())

            data_zac.at[i, 'updated_fidelity'] = (data_zac.iloc[i]['total_fidelity']*g1q_2q_geo_avg**(1/len(grouped_benchmarks)))/(data_zac.iloc[i]['total_1q_fidelity']*data_zac.iloc[i]['total_2q_fidelity'])

            #add row to data_zac copy of this one with uptated fidelity as g1_2q_mov_trans_avg
            data_zac.loc[len(data_zac)] = data_zac.iloc[i]
            data_zac.at[len(data_zac)-1, 'updated_fidelity'] = g1q_2q_mov_trans_avg**(1/len(grouped_benchmarks))
            data_zac.at[len(data_zac)-1, 'type'] = 'Grouped Independent'

    data_zac = data_zac[data_zac['nqubits'] != 20]
    data_zac = data_zac[data_zac['nqubits'] != 25]
    data_zac = data_zac[data_zac['nqubits'] != 10]

    bar_plot.grouped_barplot(data_zac,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='updated_fidelity',
                             title='(a1) Fidelity vs Utilization',
                             title_loc='left',
                             errorbar=None,
                             #group_labels='',
                             linewidth=1.75,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.65, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Fidelity',
                             ylim=(0,0.95))

def plot_fidelity_vs_circuit_size_average(ax, title):
    data_zac = pd.read_csv("organize/zac_results.csv")
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")

    df = pd.DataFrame(columns=['nqubits', 'total_fidelity'])

    #compute average fidelity for each nqubits in data_zac and data_pachinqo for same number of nqubits average the values of the benchmarks and the two dataframes
    for nqubits in data_zac['nqubits'].unique():
        zac_fidelity = data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean()
        pachinqo_fidelity = data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean()
        
        if not np.isnan(zac_fidelity) and not np.isnan(pachinqo_fidelity):
            df.loc[len(df)] = [nqubits, (zac_fidelity + pachinqo_fidelity) / 2]

    df.sort_values(by='nqubits', inplace=True)
    df['nqubits'] = df['nqubits'].astype(int)
    df = df[df['nqubits'] != 20]
    df = df[df['nqubits'] != 10]

    bars = bar_plot.simple_bar_plot(df=df,
                                    ax=ax,
                                    xcol='nqubits',
                                    ycol='total_fidelity',
                                    title=title,
                                    title_loc='left',
                                    linewidth=1.75,
                                    higher_lower_is_better='higher',
                                    higher_lower_is_better_loc=(0.7, 1.02),
                                    xlabel='Circuit Size [# Qubits]',
                                    legend=False,
                                    legend_loc=(0.5, -0.4),
                                    ylabel='Fidelity [%]',)

def plot_initialization_time_vs_qpu_size(ax, title):
    #define lambda function to compute initialization time
    get_initialization_time = lambda qpu_size: 40 + 20 + 4 + 5 + 5 + 0.025 * qpu_size
    x = np.arange(32, 512)

    title_loc = 'left'

    sns.set_theme()
    #sns.set_style("whitegrid")

    ax.set_facecolor('white')
    ax.spines['left'].set_color('black')
    ax.spines['bottom'].set_color('black')
    ax.grid(color='lightgray', linestyle='--', linewidth=0.5)

    ax.plot(x, get_initialization_time(x), linewidth=1.75)
    
    ax.set_title(title, fontweight='bold', loc=title_loc)

    ax.text(0.7, 1.02, defaults.LOWERISBETTER, transform=ax.transAxes, fontsize=defaults.FONTSIZE, fontweight="bold", color="midnightblue")

    ax.set_ylabel('Initialization time [ms]', color='black')

    ax.set_xlabel('QPU size [# atoms]', color='black')

    ax.vlines(x=250, ymin=0, ymax=80, color='red', linewidth=2, linestyle='--')
    ax.hlines(y=80, xmin=0, xmax=255, color='red', linewidth=2, linestyle='--')
    ax.plot(250, 80, marker='X', markersize=9, color='red', markeredgecolor='black', markeredgewidth=0.5)
    #ax.text(200, 81.5, '82 ms', fontsize=12, color='red', ha='center', va='center')
    #ax.text(285, 75, '280 atoms QPU', fontsize=12, color='red', ha='center', va='center')
    ax.annotate('Initialization time (82 ms) \n 250-atom QPU', xy=(247.5, 81), xytext=(220, 85), horizontalalignment='center', arrowprops=dict(color='black'))

    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    ax.set_ylim(73, 88)

    ax.set_xlim(0, 512)

    #plt.subplots_adjust(bottom=0.25)
    #plt.tight_layout()
    return ax

def plot_execution_time_vs_circuit_size_zac_pachinqo(ax, title):
    data_zac = pd.read_csv("organize/zac_results.csv")
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")

    df = pd.DataFrame(columns=['nqubits', 'execution_time', 'compiler'])

    #compute average fidelity for each nqubits in data_zac and data_pachinqo for same number of nqubits average the values of the benchmarks and the two dataframes
    for nqubits in data_zac['nqubits'].unique():
        df.loc[len(df)] = [nqubits, data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean(), 'ZAC']
        df.loc[len(df)] = [nqubits, data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean(), 'Pachinqo']
        #zac_exec_time = data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean()
        #pachinqo_exec_time = data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean()
        
        #if not np.isnan(zac_exec_time) and not np.isnan(pachinqo_exec_time):
        #    df.loc[len(df)] = [nqubits, (zac_exec_time + pachinqo_exec_time) / 2]

    df.sort_values(by='nqubits', inplace=True)
    df['execution_time'] = df['execution_time']/ 1000  # Convert to seconds
    df = df[df['nqubits'] != 20]
    df = df[df['nqubits'] != 10]

    bar_plot.grouped_barplot(data=df,
                             ax=ax,
                             xcol='nqubits',
                             ycol='execution_time',
                             grouping_column='compiler',
                             title=title,
                             title_loc='left',
                             linewidth=1.75,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.7, 1.02),
                             xlabel='QPU Size [# Atoms]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Execution time [ms]',)

def plot_execution_time_vs_circuit_size_zac_pachinqo_atomique(ax, title):
    data_zac = pd.read_csv("results/preeval/zac_preeval.csv")
    data_pachinqo = pd.read_csv("results/preeval/pachinqo_preeval.csv")
    data_atomique = pd.read_csv("results/preeval/atomique_preeval.csv")

    df = pd.DataFrame(columns=['nqubits', 'execution_time', 'compiler'])

    #compute average fidelity for each nqubits in data_zac and data_pachinqo for same number of nqubits average the values of the benchmarks and the two dataframes
    for nqubits in data_zac['nqubits'].unique():
        df.loc[len(df)] = [nqubits, data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean() / 1000, 'ZAC']
        df.loc[len(df)] = [nqubits, data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean() / 1000, 'Pachinqo']
        df.loc[len(df)] = [nqubits, data_atomique[data_atomique['nqubits'] == nqubits]['execution_time'].mean() * 1000, 'Atomique']
        #average
        df.loc[len(df)] = [nqubits, (data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean()/1000 + data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean()/1000 + data_atomique[data_atomique['nqubits'] == nqubits]['execution_time'].mean()*1000)/3, 'Average']
        #zac_exec_time = data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean()
        #pachinqo_exec_time = data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean()
        
        #if not np.isnan(zac_exec_time) and not np.isnan(pachinqo_exec_time):
        #    df.loc[len(df)] = [nqubits, (zac_exec_time + pachinqo_exec_time) / 2]
    
    df = df[df['nqubits'] != 20]
    df = df[df['nqubits'] != 10]

    ax.grid(color='lightgray', linestyle='--', linewidth=0.5)

    ax.set_ylim(0, 350)

    bar_plot.grouped_barplot(data=df[df['compiler'] != 'Average'],
                             ax=ax,
                             xcol='nqubits',
                             ycol='execution_time',
                             grouping_column='compiler',
                             title=title,
                             title_loc='left',
                             linewidth=1.75,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=(0.68, 1.02),
                             xlabel='Circuit Size [# qubits]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Execution time [ms]')

    unique_nqubits_sorted = sorted(df['nqubits'].unique())
    # Create a mapping from nqubits value to its categorical index
    nqubits_to_index = {val: i for i, val in enumerate(unique_nqubits_sorted)}

    # Apply this mapping to your DataFrame for plotting scatter
    df_scatter = df[df['compiler'] == 'Average'].copy()
    df_scatter['nqubits_indexed'] = df_scatter['nqubits'].map(nqubits_to_index)

    sns.lineplot(data=df_scatter,
                 x='nqubits_indexed',
                 y='execution_time',
                 ax=ax,
                 color='black',
                 marker='o',
                 linewidth=1.5,
                 label='Average')

    ax.set_xticks([nqubits_to_index[val] for val in unique_nqubits_sorted])
    ax.set_xticklabels(unique_nqubits_sorted)

    ax.vlines(x=3.35, ymin=0, ymax=90, color='red', linewidth=2, linestyle='--')
    ax.hlines(y=80, xmin=0, xmax=3.4, color='red', linewidth=2, linestyle='--')
    ax.plot(3.35, 80, marker='X', markersize=9, color='red', markeredgecolor='black', markeredgewidth=0.5)
    # arrowstyle is required here, not just cosmetic: without it, matplotlib's
    # legacy annotate-arrow fallback anchors the arrow at whichever corner of
    # the (wide, 2-line) text box is closest to `xy` -- for this text/target
    # pair that's the box's right edge, not its center, which is what made
    # the arrow look like it was pointing the wrong way.
    ax.annotate('Execution time = Initialization time (82 ms)\nThreshold point (170-qubit circuit)', xy=(3.3, 100), xytext=(2, 300), horizontalalignment='center', arrowprops=dict(color='black', arrowstyle='simple,head_length=0.7,head_width=0.6,tail_width=0.24', mutation_scale=20))
    ylim_top = 400
    ax.set_ylim(0, ylim_top)

    # Bars taller than the axis (e.g. PachinQo at 250 qubits) get clipped --
    # label the actual value just above the frame instead of silently
    # cutting it off.
    for bars in ax.containers:
        for bar in bars:
            height = bar.get_height()
            if height > ylim_top:
                ax.text(bar.get_x() - 0.02, ylim_top * 0.97, f'{height:.0f}',
                        ha='right', va='top', rotation=90, fontsize=defaults.FONTSIZE, fontweight='bold', color='black')

    ax.legend_.remove()

    sns.set_theme()
    sns.set_style("whitegrid")

def plot_fidelity_vs_circuit_size_zac_pachinqo(ax, title):
    data_zac = pd.read_csv("organize/zac_results.csv")
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")

    df = pd.DataFrame(columns=['nqubits', 'total_fidelity', 'compiler'])

    #compute average fidelity for each nqubits in data_zac and data_pachinqo for same number of nqubits average the values of the benchmarks and the two dataframes
    for nqubits in data_zac['nqubits'].unique():
        df.loc[len(df)] = [nqubits, data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean(), 'ZAC']
        df.loc[len(df)] = [nqubits, data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean(), 'Pachinqo']
        #zac_exec_time = data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean()
        #pachinqo_exec_time = data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean()
        
        #if not np.isnan(zac_exec_time) and not np.isnan(pachinqo_exec_time):
        #    df.loc[len(df)] = [nqubits, (zac_exec_time + pachinqo_exec_time) / 2]

    df.sort_values(by='nqubits', inplace=True)
    df['total_fidelity'] = df['total_fidelity']/ 1000  # Convert to seconds
    df = df[df['nqubits'] != 20]
    df = df[df['nqubits'] != 10]

    bar_plot.grouped_barplot(data=df,
                             ax=ax,
                             xcol='nqubits',
                             ycol='total_fidelity',
                             grouping_column='compiler',
                             title=title,
                             title_loc='left',
                             linewidth=1.75,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.7, 1.02),
                             xlabel='QPU Size [# Atoms]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Fidelity [%]',)

def plot_fidelity_vs_circuit_size_zac_pachinqo_atomique(ax, title):
    data_zac = pd.read_csv("results/preeval/zac_preeval.csv")
    data_pachinqo = pd.read_csv("results/preeval/pachinqo_preeval.csv")
    data_atomique = pd.read_csv("results/preeval/atomique_preeval.csv")

    df = pd.DataFrame(columns=['nqubits', 'total_fidelity', 'compiler'])

    #compute average fidelity for each nqubits in data_zac and data_pachinqo for same number of nqubits average the values of the benchmarks and the two dataframes
    for nqubits in data_zac['nqubits'].unique():
        df.loc[len(df)] = [nqubits, data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean(), 'ZAC']
        df.loc[len(df)] = [nqubits, data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean(), 'Pachinqo']
        df.loc[len(df)] = [nqubits, data_atomique[data_atomique['nqubits'] == nqubits]['total_fidelity'].mean(), 'Atomique']

        df.loc[len(df)] = [nqubits, (data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean() + data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean() + data_atomique[data_atomique['nqubits'] == nqubits]['total_fidelity'].mean())/3, 'Average']

        #zac_exec_time = data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean()
        #pachinqo_exec_time = data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean()
        
        #if not np.isnan(zac_exec_time) and not np.isnan(pachinqo_exec_time):
        #    df.loc[len(df)] = [nqubits, (zac_exec_time + pachinqo_exec_time) / 2]

    df = df[df['nqubits'] != 20]
    df = df[df['nqubits'] != 10]

    ax.grid(axis='y', color='lightgray', linestyle='--', linewidth=0.5)
    ax.grid(axis='x', color='lightgray', linestyle='--', linewidth=0.5)

    bar_plot.grouped_barplot(data=df[df['compiler'] != 'Average'],
                             ax=ax,
                             xcol='nqubits',
                             ycol='total_fidelity',
                             grouping_column='compiler',
                             title=title,
                             title_loc='left',
                             linewidth=1.75,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.68, 1.02),
                             xlabel='Circuit size [# qubits]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Fidelity')
    
    unique_nqubits_sorted = sorted(df['nqubits'].unique())
    nqubits_to_index = {val: i for i, val in enumerate(unique_nqubits_sorted)}

    df_scatter = df[df['compiler'] == 'Average'].copy()
    df_scatter['nqubits_indexed'] = df_scatter['nqubits'].map(nqubits_to_index)

    sns.lineplot(data=df_scatter,
                 x='nqubits_indexed',
                 y='total_fidelity',
                 ax=ax,
                 color='black',
                 marker='o',
                 linewidth=1.5,
                 label='Average',
                 legend=False)

    ax.set_xticks([nqubits_to_index[val] for val in unique_nqubits_sorted])
    ax.set_xticklabels(unique_nqubits_sorted)
    ax.hlines(y=0.08, xmin=0, xmax=3.4, color='red', linewidth=2, linestyle='--')
    ax.vlines(x=3.35, ymin=0, ymax=0.08, color='red', linewidth=2, linestyle='--')
    
    ax.plot(3.35, 0.08, marker='X', markersize=9, color='red', markeredgecolor='black', markeredgewidth=0.5)
    ax.annotate('170-qubit circuit \n 0.08 fidelity', xy=(3.375, 0.12), xytext=(3.65, 0.4), horizontalalignment='center', arrowprops=dict(color='black', arrowstyle='simple,head_length=0.7,head_width=0.6,tail_width=0.24', mutation_scale=20))

def plot_execution_time_vs_circuit_size_average(ax, title):
    data_zac = pd.read_csv("organize/zac_results.csv")
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")

    df = pd.DataFrame(columns=['nqubits', 'execution_time'])

    #compute average fidelity for each nqubits in data_zac and data_pachinqo for same number of nqubits average the values of the benchmarks and the two dataframes
    for nqubits in data_zac['nqubits'].unique():
        zac_fidelity = data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean()
        pachinqo_fidelity = data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean()
        
        if not np.isnan(zac_fidelity) and not np.isnan(pachinqo_fidelity):
            df.loc[len(df)] = [nqubits, (zac_fidelity + pachinqo_fidelity) / 2]

    df.sort_values(by='nqubits', inplace=True)
    df['execution_time'] = df['execution_time']/ 1000  # Convert to seconds
    df = df[df['nqubits'] != 20]
    df = df[df['nqubits'] != 10]

    bar_plot.simple_bar_plot(df=df,
                             ax=ax,
                             xcol='nqubits',
                             ycol='execution_time',
                             title=title,
                             title_loc='left',
                             linewidth=1.75,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.7, 1.02),
                             xlabel='Circuit Size [# Qubits]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Execution time [ms]',)

def plot_fidelity_vs_utilization_pachinqo(ax):
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")

    qpu_size_zac = 250
    data_pachinqo['qpu_utilization'] = [int(data_pachinqo.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_pachinqo))]
    data_pachinqo['type'] = ['Grouped' if len(data_pachinqo.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_pachinqo))]
    data_pachinqo['grouped_circuits'] = [len(data_pachinqo.iloc[i]['benchmark'].split('_')) for i in range(len(data_pachinqo))]

    for i in range(len(data_pachinqo)):
        if data_pachinqo.iloc[i]['type'] == 'Sequential':
            data_pachinqo.at[i, 'updated_fidelity'] = data_pachinqo.iloc[i]['total_fidelity']
        else:
            #data_pachinqo.at[i, 'updated_fidelity'] = data_pachinqo.iloc[i]['total_fidelity']
            g1q_2q_geo_avg = 1
            g1q_2q_mov_trans_avg = 1
            grouped_benchmarks = data_pachinqo.iloc[i]['benchmark'].split('_')
            
            for j in grouped_benchmarks:
                g1q_2q_geo_avg *= float(data_pachinqo[data_pachinqo['benchmark'] == j][data_pachinqo['nqubits'] == data_pachinqo.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_1q_fidelity'].mean())*float(data_pachinqo[data_pachinqo['benchmark'] == j][data_pachinqo['nqubits'] == data_pachinqo.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_2q_fidelity'].mean())
                g1q_2q_mov_trans_avg *= float(data_pachinqo[data_pachinqo['benchmark'] == j][data_pachinqo['nqubits'] == data_pachinqo.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_fidelity'].mean())

            data_pachinqo.at[i, 'updated_fidelity'] = (data_pachinqo.iloc[i]['total_fidelity']/(data_pachinqo.iloc[i]['total_1q_fidelity']*data_pachinqo.iloc[i]['total_2q_fidelity']))*g1q_2q_geo_avg**(1/len(grouped_benchmarks))

            #add row to data_pachinqo copy of this one with uptated fidelity as g1_2q_mov_trans_avg
            data_pachinqo.loc[len(data_pachinqo)] = data_pachinqo.iloc[i]
            data_pachinqo.at[len(data_pachinqo)-1, 'updated_fidelity'] = g1q_2q_mov_trans_avg**(1/len(grouped_benchmarks))
            data_pachinqo.at[len(data_pachinqo)-1, 'type'] = 'Grouped Independent'

    data_pachinqo = data_pachinqo[data_pachinqo['nqubits'] != 20]
    data_pachinqo = data_pachinqo[data_pachinqo['nqubits'] != 25]
    data_pachinqo = data_pachinqo[data_pachinqo['nqubits'] != 10]

    bar_plot.grouped_barplot(data_pachinqo,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='updated_fidelity',
                             title='(a1) Fidelity vs Utilization',
                             title_loc='left',
                             errorbar=None,
                             group_labels='',
                             linewidth=1.75,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.65, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Fidelity',
                             ylim=(0,0.95))
    
def plot_fidelity_vs_utilization_atomique(ax):

    data_atomique = pd.read_csv("organize/atomique_results.csv")

    qpu_size_atomique = 250
    data_atomique['qpu_utilization'] = [int(data_atomique.iloc[i]['nqubits']*100/qpu_size_atomique) for i in range(len(data_atomique))]
    data_atomique['type'] = ['Grouped' if len(data_atomique.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_atomique))]
    data_atomique['grouped_circuits'] = [len(data_atomique.iloc[i]['benchmark'].split('_')) for i in range(len(data_atomique))]

    for i in range(len(data_atomique)):
        if data_atomique.iloc[i]['type'] == 'Sequential':
            data_atomique.at[i, 'updated_fidelity'] = data_atomique.iloc[i]['total_fidelity']
        else:
            #data_atomique.at[i, 'updated_fidelity'] = data_atomique.iloc[i]['total_fidelity']
            g1q_2q_geo_avg = 1
            g1_2q_mov_trans_avg = 1
            grouped_benchmarks = data_atomique.iloc[i]['benchmark'].split('_')
            for j in grouped_benchmarks:
                g1q_2q_geo_avg *= float(data_atomique[data_atomique['benchmark'] == j][data_atomique['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_1q_fidelity'].mean())*float(data_atomique[data_atomique['benchmark'] == j][data_atomique['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_2q_fidelity'].mean())
                g1_2q_mov_trans_avg *= float(data_atomique[data_atomique['benchmark'] == j][data_atomique['nqubits'] == data_atomique.iloc[i]['nqubits']//len(grouped_benchmarks)]['total_fidelity'].mean())

            data_atomique.at[i, 'updated_fidelity'] = (data_atomique.iloc[i]['total_fidelity']*g1q_2q_geo_avg**(1/len(grouped_benchmarks)))/(data_atomique.iloc[i]['total_1q_fidelity']*data_atomique.iloc[i]['total_2q_fidelity'])

            #add row to data_atomique copy of this one with uptated fidelity as g1_2q_mov_trans_avg
            data_atomique.loc[len(data_atomique)] = data_atomique.iloc[i]
            data_atomique.at[len(data_atomique)-1, 'updated_fidelity'] = g1_2q_mov_trans_avg**(1/len(grouped_benchmarks))
            data_atomique.at[len(data_atomique)-1, 'type'] = 'Grouped Independent'

    data_atomique = data_atomique[data_atomique['nqubits'] != 20]
    data_atomique = data_atomique[data_atomique['nqubits'] != 25]
    data_atomique = data_atomique[data_atomique['nqubits'] != 10]

    bar_plot.grouped_barplot(data_atomique,
                             ax=ax,
                             grouping_column='type',
                             xcol='qpu_utilization',
                             ycol='updated_fidelity',
                             title='(a2) Fidelity vs Utilization',
                             title_loc='left',
                             errorbar=None,
                             group_labels='',
                             linewidth=1.75,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.65, 1.04),
                             xlabel='QPU Utilization [%]',
                             legend=False,
                             legend_loc=(0.5, -0.4),
                             ylabel='Fidelity',
                             ylim=(0,1))

def plot_compilation_time_vs_fidelity_pareto(ax):
    data_zac = pd.read_csv("organize/zac_results.csv")
    data_atomique = pd.read_csv("organize/atomique_results.csv")

    data_zac['type'] = ['Grouped' if len(data_zac.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_zac))]
    data_zac['grouped_circuits'] = [len(data_zac.iloc[i]['benchmark'].split('_')) for i in range(len(data_zac))]

    data_atomique['type'] = ['Grouped' if len(data_atomique.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_atomique))]
    data_atomique['grouped_circuits'] = [len(data_atomique.iloc[i]['benchmark'].split('_')) for i in range(len(data_atomique))]

    #data_zac = data_zac[data_zac['nqubits'] != 25]
    #data_zac = data_zac[data_zac['nqubits'] != 20]
    #data_zac = data_zac[data_zac['nqubits'] != 10]

    #data_atomique = data_atomique[data_atomique['nqubits'] != 25]
    #data_atomique = data_atomique[data_atomique['nqubits'] != 20]
    #data_atomique = data_atomique[data_atomique['nqubits'] != 10]

    #data_zac = data_zac[data_zac['qpu_utilization'] == 100]
    #data_atomique = data_atomique[data_atomique['qpu_utilization'] == 100]

def plot_compilation_time_vs_fidelity_scatter_plot(ax, title):
    # Data for the scatter plot including legend associations
    # We map each unique point to a label
    # Data for the scatter plot, including legend associations
    plot_data = {
        'X': [2, 3, 2, 4],
        'Y': [2, 3, 4, 4],
        'Label': [
            'ZAC',
            'PachinQo',
            'MultiQ + Hardware acceleration',
            'MultiQ'
        ],
        'Color': ['red', 'blue', 'green', 'purple'], # Assign distinct colors
        'Marker_Shape': ['o', 's', '^', 'X'] # Assign distinct marker shapes
    }

    df = pd.DataFrame(plot_data)

    # Lists to store legend handles and labels for manual legend creation
    legend_handles = []
    legend_labels = []

    # Plot each point individually to ensure specific marker shapes are applied
    for index, row in df.iterrows():
        # Using ax.scatter to plot each point
        scatter_artist = ax.scatter(
            row['X'], row['Y'],
            color=sns.color_palette("pastel")[index], # Use a pastel color palette
            s=250,              # Set the size of the points
            marker=row['Marker_Shape'], # Apply the specific marker shape
            edgecolors='black', # Add an edge for better visibility
            linewidth=1,        # Edge line width
            label=row['Label']  # Label for the legend
        )
        # Collect the legend handle and label for this specific point
        legend_handles.append(scatter_artist)
        legend_labels.append(row['Label'])

    ## List to hold legend handles and labels
    #legend_handles = []
    #legend_labels = []

    #for index, row in df.iterrows():
    #    # Using ax.scatter directly to control hatches
    #    scatter_artist = ax.scatter(
    #        row['X'], row['Y'],
    #        color=row['Color'], # Use a pastel color palette
    #        s=250,              # Set the size of the points
    #        marker='o',         # Use a circle marker for all points to apply hatch inside
    #        hatch=row['Hatch'], # Apply the specific hatch pattern
    #        edgecolors='black', # Add an edge color for better hatch visibility
    #        linewidth=1,        # Edge line width
    #        label=row['Label']  # Label for the legend
    #    )
    #    # Collect the legend handle and label for this specific point
    #    legend_handles.append(scatter_artist)
    #    legend_labels.append(row['Label'])

    # Add labels and title using the Axes object methods
    ax.set_xlabel('Framework runtime (relative values)')
    ax.set_ylabel('Fidelity (relative values)')
    ax.set_title(title, weight='bold')

    # Set ticks to clearly show the given points using Axes object methods
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.grid(True)

    # Position the legend outside the plot using the Axes object's legend method
    # and adjusting its position relative to the axes
    #ax.legend(bbox_to_anchor=(0.5, -0.1))

    return legend_handles, legend_labels

def plot_fidelity_shuttling_times_vs_layout_width_zac(ax, title):
    data_zac = pd.read_csv("results/preeval/zac_results.csv")

    for i in range(len(data_zac)):
        data_zac.at[i, 'relative_fidelity'] = float(data_zac.iloc[i]['total_fidelity']) / float(data_zac[data_zac['ratio']=='1_1'][data_zac['nqubits']==data_zac.iloc[i]['nqubits']][data_zac['benchmark']==data_zac.iloc[i]['benchmark']]['total_fidelity'])

    data_zac.sort_values(by='relative_fidelity', inplace=True)

    # Ratio 1:1 is the normalization baseline (always relative_fidelity==1)
    # -- shown implicitly, not as its own (trivial) bar.
    plot_data = data_zac[data_zac['ratio'] != '1_1']

    ylim_top = 1.3
    ax.set_ylim(0, ylim_top)

    bar_plot.grouped_barplot(data=plot_data,
                                   ax=ax,
                                   xcol='nqubits',
                                   ycol='relative_fidelity',
                                   grouping_column='ratio',
                                   title=title,
                                   title_loc='left',
                                   linewidth=1.75,
                                   higher_lower_is_better=False,
                                   higher_lower_is_better_loc=(0.61, 1.035),
                                   xlabel='Circuit size (#qubits)',
                                   legend=False,
                                   legend_loc=(0.55, 0.1),
                                   ylabel='Fidelity (relative to ratio 1:1)',)

    ax.set_ylim(0, ylim_top)

    # Bars taller than the axis get clipped -- label the actual value in red
    # just above the frame instead of silently cutting it off.
    for bars in ax.containers:
        for bar in bars:
            height = bar.get_height()
            if height > ylim_top:
                ax.text(1.7, ylim_top * 0.97, f'{height:.2f}',
                        ha='center', va='top', fontsize=defaults.FONTSIZE, fontweight='bold', color='red')

    # No per-axes legend here -- plot_preeval_motivation() builds one shared
    # fig-level legend from this axes' handles/labels instead, matching the
    # original ~/tmp_MultiQ/plot_preeval.py layout.

    ax.grid(True)

def plot_planner_eval_fidelity_multiq(ax, title, complete=False):
    data = pd.read_csv("results/multiq/planner_results.csv")

    #data_zac['benchmark'] = ['Grouped' if len(data_zac.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_zac))]
    #data_zac['qpu_utilization'] = [int(data_zac.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_zac))]
    #data_zac['grouped_circuits'] = [len(data_zac.iloc[i]['benchmark'].split('_')) for i in range(len(data_zac))]

    #for i in range(len(data_zac)):
    #    if data_zac.iloc[i]['type'] == 'Sequential':
    #        data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
    #        #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']
    #    else:
    #        grouped_benchmarks = data_zac.iloc[i]['benchmark'].split('_')
    #
    #        solo_shuttling_times = []
    #        solo_exec_times = []
    #
    #        for j in grouped_benchmarks:
    #            solo_shuttling_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['cir_shuttling_time'].mean()))
    #            #solo_exec_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['execution_time'].mean()))
    #
    #        data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
    #        #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']
    #
    #        #add row to data_zac copy of this one with uptated fidelity as g1_2q_mov_trans_avg
    #        data_zac.loc[len(data_zac)] = data_zac.iloc[i]
    #        data_zac.at[len(data_zac)-1, 'updated_shuttling_time'] = max(solo_shuttling_times)
    #        #data_zac.at[len(data_zac)-1, 'updated_execution_time'] = max(solo_exec_times)
    #        data_zac.at[len(data_zac)-1, 'type'] = 'Grouped Independent'

    #data_zac = data_zac[data_zac['nqubits'] != 25]
    #data_zac = data_zac[data_zac['nqubits'] != 20]
    #data_zac = data_zac[data_zac['nqubits'] != 10]

    if complete:
        data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
        data['decoherence_error'] = [(1 - float(i))*100 for i in data['total_coherence_fidelity']]
    else:
        benchmark_set = open("data/planner_eval_bench_list.txt").read().splitlines()
        benchmark_set = [i.split('/')[1] for i in benchmark_set]
        data = data[data['benchmark'].isin(benchmark_set)]
        data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
        data['decoherence_error'] = [(1 - float(i))*100 for i in data['total_coherence_fidelity']]

    ax.grid(True)

    bar_plot.grouped_barplot(data,
                             ax=ax,
                             grouping_column='perf_weight',
                             xcol='benchmark',
                             ycol='decoherence_error',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=(0.68, 1.04),
                             xlabel='Benchmarks',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Error by decoherence [%]')
    
def plot_planner_eval_utilization_multiq(ax, title, complete=False):
    data = pd.read_csv("results/multiq/planner_results.csv")

    #data_zac['benchmark'] = ['Grouped' if len(data_zac.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_zac))]
    #data_zac['qpu_utilization'] = [int(data_zac.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_zac))]
    #data_zac['grouped_circuits'] = [len(data_zac.iloc[i]['benchmark'].split('_')) for i in range(len(data_zac))]

    #for i in range(len(data_zac)):
    #    if data_zac.iloc[i]['type'] == 'Sequential':
    #        data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
    #        #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']
    #    else:
    #        grouped_benchmarks = data_zac.iloc[i]['benchmark'].split('_')
#
    #        solo_shuttling_times = []
    #        solo_exec_times = []
#
    #        for j in grouped_benchmarks:
    #            solo_shuttling_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['cir_shuttling_time'].mean()))
    #            #solo_exec_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['execution_time'].mean()))
#
    #        data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
    #        #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']
#
    #        #add row to data_zac copy of this one with uptated fidelity as g1_2q_mov_trans_avg
    #        data_zac.loc[len(data_zac)] = data_zac.iloc[i]
    #        data_zac.at[len(data_zac)-1, 'updated_shuttling_time'] = max(solo_shuttling_times)
    #        #data_zac.at[len(data_zac)-1, 'updated_execution_time'] = max(solo_exec_times)
    #        data_zac.at[len(data_zac)-1, 'type'] = 'Grouped Independent'

    #data_zac = data_zac[data_zac['nqubits'] != 25]
    #data_zac = data_zac[data_zac['nqubits'] != 20]
    #data_zac = data_zac[data_zac['nqubits'] != 10]

    qpu_width = 230 #um
    storage_cols_separation = 3 #um

    if complete:
        data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    else:
        benchmark_set = open("data/planner_eval_bench_list.txt").read().splitlines()
        benchmark_set = [i.split('/')[1] for i in benchmark_set]
        data = data[data['benchmark'].isin(benchmark_set)]
        data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
        data['decoherence_error'] = [(1 - float(i))*100 for i in data['total_coherence_fidelity']]

    data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    #data['decoherence_error'] = [(1 - float(i))*100 for i in data['total_fidelity']]
    data['utilization'] = [100-((i-1)*storage_cols_separation*100)/qpu_width for i in data['storage_zone_cols']]  # Assuming 250 is the max width

    data = data[data['benchmark'] != 'ghz_n40']
    data = data[data['benchmark'] != 'cat_n35']

    ax.grid(True)

    bar_plot.grouped_barplot(data,
                             ax=ax,
                             grouping_column='perf_weight',
                             xcol='benchmark',
                             ycol='utilization',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.68, 1.04),
                             xlabel='Benchmarks',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Free QPU space [%]',)
    
    ax.set_ylim(0, 100)  # Set y-axis limits to 0-100% for utilization

def plot_bundler_space_util(ax, title):
    data = pd.read_csv("results/multiq/bundler_results.csv")

    qpu_width = 230 #um
    nrows = 1

    df = pd.DataFrame(columns=['set_size', 'selector_algo','spatial_util'])
    
    # Processing data from fifo selection algorithm
    for set_size in data[data['selector_algo'] == 'fifo']['set_size'].unique():
        sum_widths = 0
        for bin in data[data['selector_algo'] == 'fifo']['bin_idx'].unique():
            data_snip = data[(data['selector_algo'] == 'fifo') & (data['set_size'] == set_size) & (data['bin_idx'] == bin)]
            sum_widths += sum(data_snip['tile_width'])
        
        bin_utilization = sum_widths/(len(data[data['selector_algo'] == 'fifo'][data['set_size'] == set_size]['bin_idx']) * (qpu_width*nrows)) * 100  # Convert to percentage
        df.loc[len(df)] = [set_size, 'fifo', bin_utilization]

    # Processing data from sa selection algorithm
    for set_size in data[data['selector_algo'] == 'sa']['set_size'].unique():
        for selector_weight in data[(data['selector_algo'] == 'sa') & (data['set_size'] == set_size)]['selector_weight'].unique():
            sum_widths = 0
            data_snip = data[(data['selector_algo'] == 'sa') & (data['set_size'] == set_size) & (data['selector_weight'] == selector_weight)]
            for bin in data_snip['bin_idx'].unique():
                sum_widths += sum(data_snip[data_snip['bin_idx']==bin]['tile_width'])
            
            bin_utilization = sum_widths/(len(data[data['selector_algo'] == 'sa'][data['set_size'] == set_size][data['selector_weight'] == selector_weight]['bin_idx'].unique()) * (qpu_width*nrows)) * 100  # Convert to percentage
            df.loc[len(df)] = [set_size, f'SA - {selector_weight}', bin_utilization]
    
    ax.grid(True)

    #selector_algo_order = [f'SA - {weight}' for weight in sorted(data['selector_weight'].unique())]
    #selector_algo_order.insert(0, 'fifo')  # Ensure 'fifo' is first

    #df['selector_algo'] = pd.Categorical(df['selector_algo'], categories=selector_algo_order, ordered=True)
    df.sort_values(by = "selector_algo")
    df = df[df['selector_algo'] != 'SA - 0.0']
    df = df[df['selector_algo'] != 'SA - 1.0']
    #df['set_size'] = pd.Categorical(df['set_size'], categories=set_order, ordered=True)
    #df['phase_duration'] = pd.Categorical(df['phase_duration'], categories=phase_order, ordered=True)

    bar_plot.grouped_barplot(df,
                             ax=ax,
                             grouping_column='selector_algo',
                             xcol='set_size',
                             ycol='spatial_util',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.7, 1.02),
                             xlabel='Sets of benchmarks',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Spatial utilization [%]',)
    
    ax.set_ylim(20, 100)  # Set y-axis limits to 0-100% for utilization

def plot_bundler_temporal_util(ax, title):
    data = pd.read_csv("results/multiq/bundler_results.csv")

    df = pd.DataFrame(columns=['set_size', 'selector_algo','temporal_util'])
    
    # Processing data from fifo selection algorithm
    for set_size in data[data['selector_algo'] == 'fifo']['set_size'].unique():

        avg_bin_utilization = 1
        for bin in data[(data['selector_algo'] == 'fifo') & (data['set_size'] == set_size)]['bin_idx'].unique():
            data_snip = data[(data['selector_algo'] == 'fifo') & (data['set_size'] == set_size) & (data['bin_idx']==bin)]
            sum_durations = sum(data_snip['cir_duration']*data_snip['tile_width'])
            total_tile_width = sum(data_snip['tile_width'])
            longest_circuit = data_snip['cir_duration'].max()
            max_bin_utilization = total_tile_width * longest_circuit
            avg_bin_utilization *= sum_durations/max_bin_utilization

        temporal_utilization = avg_bin_utilization ** (1/len(data[(data['selector_algo'] == 'fifo') & (data['set_size'] == set_size)]['bin_idx'].unique()))
        
        df.loc[len(df)] = [set_size, 'fifo', temporal_utilization*100]

    # Processing data from sa selection algorithm
    for set_size in data[data['selector_algo'] == 'sa']['set_size'].unique():
        for selector_weight in data[(data['selector_algo'] == 'sa') & (data['set_size'] == set_size)]['selector_weight'].unique():
            data_snip = data[(data['selector_algo'] == 'sa') & (data['set_size'] == set_size) & (data['selector_weight'] == selector_weight)]
            
            avg_bin_utilization = 1
            for bin in data_snip['bin_idx'].unique():
                longest_circuit = data_snip[data_snip['bin_idx']==bin]['cir_duration'].max()
                sum_durations = sum(data_snip[data_snip['bin_idx']==bin]['cir_duration']*data_snip[data_snip['bin_idx']==bin]['tile_width'])
                total_tile_width = sum(data_snip[data_snip['bin_idx']==bin]['tile_width'])
                max_bin_utilization = total_tile_width * longest_circuit
                avg_bin_utilization *= sum_durations/max_bin_utilization
            
            temporal_utilization = avg_bin_utilization ** (1/(len(data_snip['bin_idx'].unique())))
            df.loc[len(df)] = [set_size, f'SA - {selector_weight}', temporal_utilization*100]
    
    ax.grid(True)

    #selector_algo_order = [f'SA - {weight}' for weight in sorted(data['selector_weight'].unique())]
    #selector_algo_order.insert(0, 'fifo')  # Ensure 'fifo' is first
    #df['selector_algo'] = pd.Categorical(df['selector_algo'], categories=selector_algo_order)
    df.sort_values(by = "selector_algo")
    df = df[df['selector_algo'] != 'SA - 0.0']
    df = df[df['selector_algo'] != 'SA - 1.0']

    bar_plot.grouped_barplot(df,
                             ax=ax,
                             grouping_column='selector_algo',
                             xcol='set_size',
                             ycol='temporal_util',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.7, 1.02),
                             xlabel='Sets of benchmarks',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Temporal utilization [%]',)
    
    ax.set_ylim(70, 100)  # Set y-axis limits to 0-100% for utilization

def plot_controler_execution_time(ax, title, zac_results_file="results/zac/controller_results.csv", powermove_results_file="results/powermove/controller_results.csv", qmap_results_file="results/qmap/controller_results.csv", zap_results_file="results/zap/controller_results.csv", include_powermove=False, include_qmap=False, include_zap=False):
    data_multiq = pd.read_csv("results/multiq/e2e_results.csv")
    data_zac = pd.read_csv(zac_results_file)
    if include_powermove:
        data_powermove = pd.read_csv(powermove_results_file)
    if include_qmap:
        data_qmap = pd.read_csv(qmap_results_file)
    if include_zap:
        data_zap = pd.read_csv(zap_results_file)

    #data_zac['benchmark'] = ['Grouped' if len(data_zac.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_zac))]
    #data_zac['qpu_utilization'] = [int(data_zac.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_zac))]
    #data_zac['grouped_circuits'] = [len(data_zac.iloc[i]['benchmark'].split('_')) for i in range(len(data_zac))]

    #for i in range(len(data_zac)):
    #    if data_zac.iloc[i]['type'] == 'Sequential':
    #        data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
    #        #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']
    #    else:
    #        grouped_benchmarks = data_zac.iloc[i]['benchmark'].split('_')
#
    #        solo_shuttling_times = []
    #        solo_exec_times = []
#
    #        for j in grouped_benchmarks:
    #            solo_shuttling_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['cir_shuttling_time'].mean()))
    #            #solo_exec_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['execution_time'].mean()))
#
    #        data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
    #        #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']
#
    #        #add row to data_zac copy of this one with uptated fidelity as g1_2q_mov_trans_avg
    #        data_zac.loc[len(data_zac)] = data_zac.iloc[i]
    #        data_zac.at[len(data_zac)-1, 'updated_shuttling_time'] = max(solo_shuttling_times)
    #        #data_zac.at[len(data_zac)-1, 'updated_execution_time'] = max(solo_exec_times)
    #        data_zac.at[len(data_zac)-1, 'type'] = 'Grouped Independent'

    #data_zac = data_zac[data_zac['nqubits'] != 25]
    #data_zac = data_zac[data_zac['nqubits'] != 20]
    #data_zac = data_zac[data_zac['nqubits'] != 10]

    qpu_width = 230 #um
    storage_cols_separation = 3 #um

    set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']  # Define the order of set sizes explicitly

    # (compiler, set_label) pairs with no data - e.g. PowerMove can't place merged
    # sets whose qubit count exceeds its fixed entanglement-zone grid. These get a
    # zero-height placeholder bar plus an "x" marker instead of silently vanishing.
    failed_markers = []

    df = pd.DataFrame(columns=['set_size', 'total_duration', 'compiler'])
    set_sizes = data_multiq['set_size'].unique()

    for size in set_sizes:
        for j in data_multiq[data_multiq['set_size'] == size]['n_rows'].unique():
            df.loc[len(df)] = [f'Set {size}', data_multiq[data_multiq['set_size'] == size][data_multiq['n_rows'] == j]['cir_duration'].max()/1000, f'MultiQ ({j} Row)']

    for i in range(len(data_zac)):
        df.loc[len(df)] = [f'Set {len(data_zac.at[i,'benchmark'].split('-'))}', data_zac.at[i,'execution_time'], 'ZAC']

    if include_powermove:
        present = set()
        for i in range(len(data_powermove)):
            set_label = f'Set {len(data_powermove.at[i,'benchmark'].split('-'))}'
            df.loc[len(df)] = [set_label, data_powermove.at[i,'execution_time'], 'PowerMove']
            present.add(set_label)
        for set_label in set_order:
            if set_label not in present:
                df.loc[len(df)] = [set_label, 0, 'PowerMove']
                failed_markers.append(('PowerMove', set_label))

    if include_qmap:
        present = set()
        for i in range(len(data_qmap)):
            set_label = f'Set {len(data_qmap.at[i,'benchmark'].split('-'))}'
            df.loc[len(df)] = [set_label, data_qmap.at[i,'execution_time'], 'QMAP']
            present.add(set_label)
        for set_label in set_order:
            if set_label not in present:
                df.loc[len(df)] = [set_label, 0, 'QMAP']
                failed_markers.append(('QMAP', set_label))

    if include_zap:
        present = set()
        for i in range(len(data_zap)):
            set_label = f'Set {len(data_zap.at[i,'benchmark'].split('-'))}'
            df.loc[len(df)] = [set_label, data_zap.at[i,'execution_time'], 'ZAP']
            present.add(set_label)
        for set_label in set_order:
            if set_label not in present:
                df.loc[len(df)] = [set_label, 0, 'ZAP']
                failed_markers.append(('ZAP', set_label))

    #data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    #data['decoherence_error'] = [(1 - float(i))*100 for i in data['total_coherence_fidelity']]
    #data['utilization'] = [(i-1)*3/qpu_width for i in data['storage_zone_cols']]  # Assuming 250 is the max width

    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    if include_powermove:
        compiler_order.append('PowerMove')
    if include_qmap:
        compiler_order.append('QMAP')
    if include_zap:
        compiler_order.append('ZAP')

    df['compiler'] = pd.Categorical(df['compiler'], categories=compiler_order, ordered=True)
    df['set_size'] = pd.Categorical(df['set_size'], categories=set_order, ordered=True)

    df = df.sort_values(['compiler', 'set_size'])

    ax.grid(True)

    bar_plot.grouped_barplot(df,
                             ax=ax,
                             grouping_column='compiler',
                             xcol='set_size',
                             ycol='total_duration',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=(0.67, 1.02),
                             xlabel='Sets of benchmarks',
                             legend=False,
                             legend_loc=(0.6, -0.38),
                             ylabel='Execution time (ms)',)
    
    ax.set_ylim(0, max(df['total_duration']) + 2)  # Set y-axis limits to 0-100% for utilization

    marker_y = ax.get_ylim()[1] * 0.03
    for compiler_name, set_label in failed_markers:
        bar = ax.containers[compiler_order.index(compiler_name)][set_order.index(set_label)]
        ax.plot(bar.get_x() + bar.get_width() / 2, marker_y, marker='x', color='black', markersize=7, markeredgewidth=2, zorder=5)

    #ax.hlines(df[df['compiler']=='ZAC'][df['set_size']==4]['cir_duration'].mean(), xmin=ax.containers[0][0].get_x(), xmax=ax.containers[0][0].get_x()+ax.containers[0][4]._width*3, colors='red', linestyles='dashed')
    ax.annotate('', xy=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['total_duration']+1), xytext=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][4].get_x() - ax.containers[0][4].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration']/2, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['total_duration'].item()):.1f}x', fontsize=9, color='green')

    ax.annotate('', xy=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['total_duration']+1), xytext=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][0].get_x() - ax.containers[0][0].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration']/2+8, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['total_duration'].item()):.1f}x', fontsize=9, color='green')
    #ax.text(ax.containers[2][4].get_x() + ax.containers[2][0]._width/4, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['cir_duration'].mean()+0.5, f'+{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['cir_duration'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==4]["cir_duration"].mean()):.1f}', fontsize=9, color='red', rotation=90)

    ax.annotate('', xy=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['total_duration']+1), xytext=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][5].get_x() - ax.containers[0][5].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['total_duration']/2, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['total_duration'].item()):.1f}x', fontsize=9, color='green')
    
def plot_controler_decoherence_error(ax, title, zac_results_file="results/zac/controller_results.csv", powermove_results_file="results/powermove/controller_results.csv", qmap_results_file="results/qmap/controller_results.csv", zap_results_file="results/zap/controller_results.csv", include_powermove=False, include_qmap=False, include_zap=False):
    data_multiq = pd.read_csv("results/multiq/e2e_results.csv")
    data_zac = pd.read_csv(zac_results_file)
    if include_powermove:
        data_powermove = pd.read_csv(powermove_results_file)
    if include_qmap:
        data_qmap = pd.read_csv(qmap_results_file)
    if include_zap:
        data_zap = pd.read_csv(zap_results_file)

    qpu_width = 230 #um
    storage_cols_separation = 3 #um

    set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']  # Define the order of set sizes explicitly

    # (compiler, set_label) pairs with no data - e.g. PowerMove can't place merged
    # sets whose qubit count exceeds its fixed entanglement-zone grid. These get a
    # zero-height placeholder bar plus an "x" marker instead of silently vanishing.
    failed_markers = []

    df = pd.DataFrame(columns=['set_size', 'decoherence_error', 'compiler'])
    set_sizes = data_multiq['set_size'].unique()

    for size in set_sizes:
        for j in data_multiq[data_multiq['set_size'] == size]['n_rows'].unique():
            # Geometric mean of decoherence error for each benchmark with the same set size and number of rows
            decoherence_error = 100-(data_multiq[data_multiq['set_size'] == size][data_multiq['n_rows'] == j]['cir_coherence'].product()) ** (1/len(data_multiq[data_multiq['set_size'] == size][data_multiq['n_rows'] == j]['benchmark'])) * 100
            df.loc[len(df)] = [f'Set {size}', decoherence_error, f'MultiQ ({j} Row)']

    for i in range(len(data_zac)):
        decoherence_error = (1-data_zac.at[i,'total_coherence_fidelity'])*100
        df.loc[len(df)] = [f'Set {len(data_zac.at[i,'benchmark'].split('-'))}',
                             decoherence_error,
                             'ZAC']

    if include_powermove:
        present = set()
        for i in range(len(data_powermove)):
            set_label = f'Set {len(data_powermove.at[i,'benchmark'].split('-'))}'
            decoherence_error = (1-data_powermove.at[i,'total_coherence_fidelity'])*100
            df.loc[len(df)] = [set_label, decoherence_error, 'PowerMove']
            present.add(set_label)
        for set_label in set_order:
            if set_label not in present:
                df.loc[len(df)] = [set_label, 0, 'PowerMove']
                failed_markers.append(('PowerMove', set_label))

    if include_qmap:
        present = set()
        for i in range(len(data_qmap)):
            set_label = f'Set {len(data_qmap.at[i,'benchmark'].split('-'))}'
            decoherence_error = (1-data_qmap.at[i,'total_coherence_fidelity'])*100
            df.loc[len(df)] = [set_label, decoherence_error, 'QMAP']
            present.add(set_label)
        for set_label in set_order:
            if set_label not in present:
                df.loc[len(df)] = [set_label, 0, 'QMAP']
                failed_markers.append(('QMAP', set_label))

    if include_zap:
        present = set()
        for i in range(len(data_zap)):
            set_label = f'Set {len(data_zap.at[i,'benchmark'].split('-'))}'
            decoherence_error = (1-data_zap.at[i,'total_coherence_fidelity'])*100
            df.loc[len(df)] = [set_label, decoherence_error, 'ZAP']
            present.add(set_label)
        for set_label in set_order:
            if set_label not in present:
                df.loc[len(df)] = [set_label, 0, 'ZAP']
                failed_markers.append(('ZAP', set_label))

    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    if include_powermove:
        compiler_order.append('PowerMove')
    if include_qmap:
        compiler_order.append('QMAP')
    if include_zap:
        compiler_order.append('ZAP')

    df['compiler'] = pd.Categorical(df['compiler'], categories=compiler_order, ordered=True)
    df['set_size'] = pd.Categorical(df['set_size'], categories=set_order, ordered=True)

    df = df.sort_values(['compiler', 'set_size'])

    ax.grid(True)

    bar_plot.grouped_barplot(df,
                             ax=ax,
                             grouping_column='compiler',
                             xcol='set_size',
                             ycol='decoherence_error',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=(0.67, 1.02),
                             xlabel='Sets of benchmarks',
                             legend=False,
                             legend_loc=(0.5, -0.38),
                             ylabel='Error by decoherence [%]',)

    ax.set_ylim(0, 100)  # Set y-axis limits to 0-100% for utilization

    marker_y = ax.get_ylim()[1] * 0.03
    for compiler_name, set_label in failed_markers:
        bar = ax.containers[compiler_order.index(compiler_name)][set_order.index(set_label)]
        ax.plot(bar.get_x() + bar.get_width() / 2, marker_y, marker='x', color='black', markersize=7, markeredgewidth=2, zorder=5)

    ax.annotate('', xy=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['decoherence_error']+1), xytext=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['decoherence_error']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][4].get_x() - ax.containers[0][4].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['decoherence_error']/2, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['decoherence_error'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['decoherence_error'].item()):.1f}x', fontsize=9, color='green')

    ax.annotate('', xy=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['decoherence_error']+1), xytext=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['decoherence_error']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][0].get_x() - ax.containers[0][0].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['decoherence_error']/2, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['decoherence_error'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['decoherence_error'].item()):.1f}x', fontsize=9, color='green')

    ax.annotate('', xy=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['decoherence_error']+1), xytext=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['decoherence_error']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][5].get_x() - ax.containers[0][5].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['decoherence_error']/2, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['decoherence_error'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['decoherence_error'].item()):.1f}x', fontsize=9, color='green')

def plot_e2e_results_fidelity(ax, set_size, title, multiq_results_file="results/multiq/e2e_results.csv", zac_results_file="results/zac/e2e_results.csv", pachinqo_results_file="results/pachinqo/e2e_results.csv", powermove_results_file="results/powermove/e2e_results.csv", qmap_results_file="results/qmap/e2e_results.csv", zap_results_file="results/zap/e2e_results.csv", include_pachinqo=False, include_powermove=False, include_qmap=False, include_zap=False):
    data_multiq = pd.read_csv(multiq_results_file)
    data_zac = pd.read_csv(zac_results_file)
    data_pachinqo = pd.read_csv(pachinqo_results_file)
    data_powermove = pd.read_csv(powermove_results_file)
    data_qmap = pd.read_csv(qmap_results_file)
    data_zap = pd.read_csv(zap_results_file)

    df = pd.DataFrame(columns=['benchmark', 'total_fidelity', 'cir_duration', 'compiler'])

    #data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
#    for benchmark in data_multiq['benchmark'].unique():
#        df.loc[len(df)] = [benchmark, data_zac[data_zac['benchmark'] == benchmark]['total_fidelity'].item(), data_zac[data_zac['benchmark'] == benchmark]['cir_duration'].item(), 'ZAC']
#        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_aods'] == 1][data_multiq['n_rows'] == 1]['cir_fidelity'].item(), data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1][data_multiq['n_aods'] == 1]['cir_duration'].item(), 'MultiQ (1 Row/1 AOD)']
#        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_aods'] == 2][data_multiq['n_rows'] == 1]['cir_fidelity'].item(), data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1][data_multiq['n_aods'] == 2]['cir_duration'].item(), 'MultiQ (1 Row/2 AOD)']
#        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_aods'] == 1][data_multiq['n_rows'] == 2]['cir_fidelity'].item(), data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2][data_multiq['n_aods'] == 1]['cir_duration'].item(), 'MultiQ (2 Row/1 AOD)']
#        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_aods'] == 2][data_multiq['n_rows'] == 2]['cir_fidelity'].item(), data_multiq[data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2][data_multiq['n_aods'] == 2]['cir_duration'].item(), 'MultiQ (2 Row/2 AOD)']
    
    for benchmark in data_multiq[data_multiq['set_size']==set_size]['benchmark'].unique():
        df.loc[len(df)] = [benchmark, data_zac[data_zac['benchmark'] == benchmark]['total_fidelity'].item(), data_zac[data_zac['benchmark'] == benchmark]['cir_duration'].item(), 'ZAC']
        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1]['cir_fidelity'].item(), data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1]['cir_duration'].item(), 'MultiQ (1 Row)']
        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2]['cir_fidelity'].item(), data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2]['cir_duration'].item(), 'MultiQ (2 Row)']

        if include_powermove:
            if benchmark in data_powermove['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_powermove[data_powermove['benchmark'] == benchmark]['total_fidelity'].item(), data_powermove[data_powermove['benchmark'] == benchmark]['cir_duration'].item(), 'PowerMove']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'PowerMove']

        if include_qmap:
            if benchmark in data_qmap['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_qmap[data_qmap['benchmark'] == benchmark]['total_fidelity'].item(), data_qmap[data_qmap['benchmark'] == benchmark]['cir_duration'].item(), 'QMAP']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'QMAP']

        if include_zap:
            if benchmark in data_zap['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_zap[data_zap['benchmark'] == benchmark]['total_fidelity'].item(), data_zap[data_zap['benchmark'] == benchmark]['cir_duration'].item(), 'ZAP']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'ZAP']

        if include_pachinqo:
            if benchmark in data_pachinqo['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_pachinqo[data_pachinqo['benchmark'] == benchmark]['total_fidelity'].item(), data_pachinqo[data_pachinqo['benchmark'] == benchmark]['execution_time'].item(), 'Pachinqo']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'Pachinqo']

    # Add mean of all benchmarks for each compiler
    df.loc[len(df)] = ['Mean', df[df['compiler']=='ZAC']['total_fidelity'].mean(), data_zac['cir_duration'].mean(), 'ZAC']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean(), 'MultiQ (1 Row)']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean(), 'MultiQ (2 Row)']
    if include_powermove:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='PowerMove'][df['benchmark'].isin(data_powermove['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='PowerMove']['cir_duration'].mean(), 'PowerMove']
    if include_qmap:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='QMAP'][df['benchmark'].isin(data_qmap['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='QMAP']['cir_duration'].mean(), 'QMAP']
    if include_zap:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='ZAP'][df['benchmark'].isin(data_zap['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='ZAP']['cir_duration'].mean(), 'ZAP']
    if include_pachinqo:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='Pachinqo'][df['benchmark'].isin(data_pachinqo['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='Pachinqo']['cir_duration'].mean(), 'Pachinqo']

    ax.grid(True)

    higher_lower_is_better_loc = (0.68, 1.02)

    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    if include_powermove:
        compiler_order.append('PowerMove')
    if include_qmap:
        compiler_order.append('QMAP')
    if include_zap:
        compiler_order.append('ZAP')
    if include_pachinqo:
        compiler_order.append('Pachinqo')

    df['compiler'] = pd.Categorical(df['compiler'], categories=compiler_order, ordered=True)
    benchmark_order = df['benchmark'].unique().tolist()[::-1]
    df['benchmark'] = pd.Categorical(df['benchmark'], categories=benchmark_order, ordered=True)
    df = df.sort_values(['benchmark', 'compiler'], ascending=[True, False])

    bar_plot.grouped_barplot(df,
                             ax=ax,
                             grouping_column='compiler',
                             xcol='benchmark',
                             ycol='total_fidelity',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=higher_lower_is_better_loc,
                             xlabel='Benchmarks',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Fidelity')
    
    xtick_labels = df['benchmark'].unique().tolist()
    ax.set_xticklabels(xtick_labels, fontsize=11)  # Rotate x-tick labels for better readability
    ax.set_ylim(0.3, 0.9)  # Set y-axis limits to 0-1 for fidelity
    print(f'Mean ratios: \n \
          \t MultiQ (1 Row): {df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean()},\n \
          \t MultiQ (2 Row): {df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean()}, \n \
          \t ZAC: {df[df["compiler"] == "ZAC"]["total_fidelity"].mean()} \n ')
    
    '''
    if set_size == 6:
        ax.text(5.855, 0.65, f'{df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean() - df[df["compiler"] == "ZAC"]["total_fidelity"].mean():.3f}',
                rotation=90, fontsize=12, color='green')
        
        ax.text(6.15, 0.65, f'{df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean() - df[df["compiler"] == "ZAC"]["total_fidelity"].mean():.3f}',
                rotation=90, fontsize=12, color='green')
    elif set_size == 8:
        ax.text(7.855, 0.74, f'{df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean() - df[df["compiler"] == "ZAC"]["total_fidelity"].mean():.3f}',
                rotation=90, fontsize=12, color='red')

        ax.text(8.15, 0.75, f'{df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean() - df[df["compiler"] == "ZAC"]["total_fidelity"].mean():.3f}',
                rotation=90, fontsize=12, color='red')
    else:
        ax.text(9.87, 0.7, f'{df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean() - df[df["compiler"] == "ZAC"]["total_fidelity"].mean():.3f}',
                rotation=90, fontsize=12, color='red')

        ax.text(10.15, 0.7, f'{df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean() - df[df["compiler"] == "ZAC"]["total_fidelity"].mean():.3f}',
                rotation=90, fontsize=12, color='red')
    '''
            
    print(df)
    
def plot_e2e_results_duration(ax, set_size, title,multiq_results_file="results/multiq/e2e_results.csv", zac_results_file="results/zac/e2e_results.csv", pachinqo_results_file="results/pachinqo/e2e_results.csv", powermove_results_file="results/powermove/e2e_results.csv", qmap_results_file="results/qmap/e2e_results.csv", zap_results_file="results/zap/e2e_results.csv", include_pachinqo=False, include_powermove=False, include_qmap=False, include_zap=False, higher_lower_is_better='lower'):
    data_multiq = pd.read_csv(multiq_results_file)
    data_zac = pd.read_csv(zac_results_file)
    data_pachinqo = pd.read_csv(pachinqo_results_file)
    data_powermove = pd.read_csv(powermove_results_file)
    data_qmap = pd.read_csv(qmap_results_file)
    data_zap = pd.read_csv(zap_results_file)

    df = pd.DataFrame(columns=['benchmark', 'total_fidelity', 'cir_duration', 'compiler'])

    #data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    for benchmark in data_multiq[data_multiq['set_size']==set_size]['benchmark'].unique():
        df.loc[len(df)] = [benchmark, data_zac[data_zac['benchmark'] == benchmark]['total_fidelity'].item(), data_zac[data_zac['benchmark'] == benchmark]['cir_duration'].item()/1000, 'ZAC']
        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1]['cir_fidelity'].item(), data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1]['cir_duration'].item()/1000, 'MultiQ (1 Row)']
        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2]['cir_fidelity'].item(), data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2]['cir_duration'].item()/1000, 'MultiQ (2 Row)']

        if include_powermove:
            if benchmark in data_powermove['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_powermove[data_powermove['benchmark'] == benchmark]['total_fidelity'].item(), data_powermove[data_powermove['benchmark'] == benchmark]['cir_duration'].item()/1000, 'PowerMove']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'PowerMove']

        if include_qmap:
            if benchmark in data_qmap['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_qmap[data_qmap['benchmark'] == benchmark]['total_fidelity'].item(), data_qmap[data_qmap['benchmark'] == benchmark]['cir_duration'].item()/1000, 'QMAP']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'QMAP']

        if include_zap:
            if benchmark in data_zap['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_zap[data_zap['benchmark'] == benchmark]['total_fidelity'].item(), data_zap[data_zap['benchmark'] == benchmark]['cir_duration'].item()/1000, 'ZAP']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'ZAP']

        if include_pachinqo:
            if benchmark in data_pachinqo['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_pachinqo[data_pachinqo['benchmark'] == benchmark]['total_fidelity'].item(), data_pachinqo[data_pachinqo['benchmark'] == benchmark]['execution_time'].item()/1000, 'Pachinqo']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'Pachinqo']

    ax.grid(True)

    df.loc[len(df)] = ['Mean', df[df['compiler']=='ZAC']['total_fidelity'].mean(), df[df['compiler']=='ZAC']['cir_duration'].mean(), 'ZAC']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean(), 'MultiQ (1 Row)']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean(), 'MultiQ (2 Row)']
    if include_powermove:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='PowerMove'][df['benchmark'].isin(data_powermove['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='PowerMove']['cir_duration'].mean(), 'PowerMove']
    if include_qmap:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='QMAP'][df['benchmark'].isin(data_qmap['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='QMAP']['cir_duration'].mean(), 'QMAP']
    if include_zap:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='ZAP'][df['benchmark'].isin(data_zap['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='ZAP']['cir_duration'].mean(), 'ZAP']
    if include_pachinqo:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='Pachinqo'][df['benchmark'].isin(data_pachinqo['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='Pachinqo']['cir_duration'].mean(), 'Pachinqo']

    higher_lower_is_better_loc = (0.68, 1.02)

    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    if include_powermove:
        compiler_order.append('PowerMove')
    if include_qmap:
        compiler_order.append('QMAP')
    if include_zap:
        compiler_order.append('ZAP')
    if include_pachinqo:
        compiler_order.append('Pachinqo')
    df['compiler'] = pd.Categorical(df['compiler'], categories=compiler_order, ordered=True)
    benchmark_order = df['benchmark'].unique().tolist()[::-1]
    df['benchmark'] = pd.Categorical(df['benchmark'], categories=benchmark_order, ordered=True)
    df = df.sort_values(['compiler', 'benchmark'], ascending=[True, True])

    bar_plot.grouped_barplot(df,
                             ax=ax,
                             grouping_column='compiler',
                             xcol='benchmark',
                             ycol='cir_duration',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better=higher_lower_is_better,
                             higher_lower_is_better_loc=higher_lower_is_better_loc,
                             xlabel='Benchmarks',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Execution time [ms]')

    #ax.ticklabel_format(axis='y', scilimits=[0, 3])
    
    '''
    if len(data_multiq[data_multiq['set_size']==set_size]['benchmark'].unique()) == 6:
        ax.text(5.855, 11500, f'{df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')
        
        ax.text(6.15, 11500, f'{df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')
    elif len(data_multiq[data_multiq['set_size']==set_size]['benchmark'].unique()) == 8:
        ax.text(7.855, 9200, f'{df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')

        ax.text(8.17, 8300, f'{df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='green')
    else:
        ax.text(9.87, 13000, f'{df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')

        ax.text(10.15, 12500, f'{df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')
    '''
    if include_pachinqo:
        ax.set_yscale('log')

    # Add Mean to the x-ticks
    xtick_labels = df['benchmark'].unique().tolist()
    ax.set_ylim(0, max(df['cir_duration']+0.5))  # Set y-axis limits to 0-1000ms for circuit duration
    ax.set_xticklabels(xtick_labels, fontsize=11)  # Rotate x-tick labels for better readability
    print(f'Mean ratios: \n \t MultiQ (1 Row): {df[df["compiler"] == "MultiQ (1 Row)"]["cir_duration"].mean()} \n \t MultiQ (2 Row): {df[df["compiler"] == "MultiQ (2 Row)"]["cir_duration"].mean()}, \n\t ZAC: {df[df["compiler"] == "ZAC"]["cir_duration"].mean()}')

    # PachinQo's grid solver never terminates on bv_n19 (times out); mark the
    # placeholder zero-height bar as timed out instead of leaving it blank.
    if include_pachinqo and 'bv_n19' in xtick_labels:
        # Pachinqo is always the last hue group in compiler_order when included.
        pachinqo_bars = ax.containers[-1]
        bar = pachinqo_bars[xtick_labels.index('bv_n19')]
        trans = matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes)
        ax.text(bar.get_x() + bar.get_width() / 2, 0, 'x',
                transform=trans, ha='center', va='bottom', rotation=90, fontsize=12, color='black', fontweight='bold')

def plot_e2e_results_fidelity_means(ax, title, set_sizes, multiq_results_file="results/multiq/e2e_results.csv", zac_results_file="results/zac/e2e_results.csv", pachinqo_results_file="results/pachinqo/e2e_results.csv"):
    data_zac = pd.read_csv(zac_results_file)
    data_pachinqo = pd.read_csv(pachinqo_results_file)
    data_multiq = pd.read_csv(multiq_results_file)

    df = pd.DataFrame(columns=['set_size', 'total_fidelity', 'cir_duration', 'compiler'])

    #data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    avg_fids = []
    for set_size in set_sizes:
            benchmarks = data_multiq[data_multiq['set_size'] == set_size]['benchmark'].unique()
            df.loc[len(df)] = [set_size, data_zac[data_zac['benchmark'].isin(benchmarks)]['total_fidelity'].mean(), data_zac[data_zac['benchmark'].isin(benchmarks)]['cir_duration'].mean()/1000, 'ZAC']
            df.loc[len(df)] = [set_size, data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 1]['cir_fidelity'].mean(), data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 1]['cir_duration'].mean()/1000, 'MultiQ (1 Row)']
            df.loc[len(df)] = [set_size, data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 2]['cir_fidelity'].mean(), data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 2]['cir_duration'].mean()/1000, 'MultiQ (2 Row)']
            df.loc[len(df)] = [set_size, data_pachinqo[data_pachinqo['benchmark'].isin(benchmarks)]['total_fidelity'].mean(), data_pachinqo[data_pachinqo['benchmark'].isin(benchmarks)]['execution_time'].mean()/1000, 'Pachinqo']
    
    ax.grid(True)

    higher_lower_is_better_loc = (0.58, 1.02)

    plot_df = df[df['compiler'].isin(['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC'])]

    bar_plot.grouped_barplot(plot_df,
                             ax=ax,
                             grouping_column='compiler',
                             xcol='set_size',
                             ycol='total_fidelity',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=higher_lower_is_better_loc,
                             xlabel='Set size',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Fidelity')
    
    ax.hlines(df[df['compiler']=='ZAC'][df['set_size']==6]['total_fidelity'].mean(), xmin=ax.containers[0][1].get_x(), xmax=ax.containers[0][1].get_x()+ax.containers[0][1]._width*3, colors='red', linestyles='dashed')
    ax.text(ax.containers[1][1].get_x() + ax.containers[1][1]._width/4, df[df['compiler']=='ZAC'][df['set_size']==6]['total_fidelity'].mean()+0.03, f'{(df[df['compiler']=='MultiQ (1 Row)'][df['set_size']==6]['total_fidelity'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==6]["total_fidelity"].mean())*100:.2f}%', fontsize=9, color='red', rotation=90)
    ax.text(ax.containers[2][1].get_x() + ax.containers[2][1]._width/4, df[df['compiler']=='ZAC'][df['set_size']==6]['total_fidelity'].mean()+0.03, f'{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==6]['total_fidelity'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==6]["total_fidelity"].mean())*100:.2f}%', fontsize=9, color='red', rotation=90)
    
    ax.hlines(df[df['compiler']=='ZAC'][df['set_size']==12]['total_fidelity'].mean(), xmin=ax.containers[0][4].get_x(), xmax=ax.containers[0][4].get_x()+ax.containers[0][4]._width*3, colors='red', linestyles='dashed')
    ax.text(ax.containers[1][4].get_x() + ax.containers[1][4]._width/4, df[df['compiler']=='ZAC'][df['set_size']==12]['total_fidelity'].mean()+0.03, f'{(df[df['compiler']=='MultiQ (1 Row)'][df['set_size']==12]['total_fidelity'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==12]["total_fidelity"].mean())*100:.2f}%', fontsize=9, color='red', rotation=90)
    ax.text(ax.containers[2][4].get_x() + ax.containers[2][4]._width/4, df[df['compiler']=='ZAC'][df['set_size']==12]['total_fidelity'].mean()+0.03, f'{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==12]['total_fidelity'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==12]["total_fidelity"].mean())*100:.2f}%', fontsize=9, color='red', rotation=90)
    
    ax.hlines(df[df['compiler']=='ZAC'][df['set_size']==4]['total_fidelity'].mean(), xmin=ax.containers[0][0].get_x(), xmax=ax.containers[0][0].get_x()+ax.containers[0][4]._width*3, colors='red', linestyles='dashed')
    ax.text(ax.containers[1][0].get_x() + ax.containers[1][0]._width/4, df[df['compiler']=='ZAC'][df['set_size']==4]['total_fidelity'].mean()+0.03, f'{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['total_fidelity'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==4]["total_fidelity"].mean())*100:.2f}%', fontsize=9, color='red', rotation=90)
    ax.text(ax.containers[2][0].get_x() + ax.containers[2][0]._width/4, df[df['compiler']=='ZAC'][df['set_size']==4]['total_fidelity'].mean()+0.03, f'{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['total_fidelity'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==4]["total_fidelity"].mean())*100:.2f}%', fontsize=9, color='red', rotation=90)

    if len(data_multiq['benchmark'].unique()) == 6:
        ax.text(5.855, 11500, f'+{df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')
        
        ax.text(6.15, 11500, f'+{df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')
    elif len(data_multiq['benchmark'].unique()) == 8:
        ax.text(7.855, 9200, f'+{abs(df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='red')

        ax.text(8.17, 8300, f'-{abs(df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='green')
    else:
        ax.text(9.87, 13000, f'+{abs(df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='red')

        ax.text(10.15, 12500, f'+{abs(df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='red')

    # Add Mean to the x-ticks
    #xtick_labels = [*list(data_multiq['benchmark'].unique()), 'Mean']
    
    #ax.set_xticklabels(xtick_labels, rotation=10, ha='right')  # Rotate x-tick labels for better readability
    
    set_sizes = sorted(set_sizes)
    for set_size in set_sizes:
        print(f'Mean fidelities (Set size {set_size}):\n \
                \t ZAC {df[df["compiler"] == "ZAC"][df["set_size"] == set_size]["total_fidelity"].mean()*100:.2f} \n \
                \t MultiQ (1 Row) {df[df["compiler"] == "MultiQ (1 Row)"][df["set_size"] == set_size]["total_fidelity"].mean()*100:.2f} \n \
                \t MultiQ (2 Row) {df[df["compiler"] == "MultiQ (2 Row)"][df["set_size"] == set_size]["total_fidelity"].mean()*100:.2f}, \n \
                \t Pachinqo {df[df["compiler"] == "Pachinqo"][df["set_size"] == set_size]["total_fidelity"].mean()*100:.2f} \n ')
            #\t Pachinqo {df[df["compiler"] == "Pachinqo"]["total_fidelity"].mean()} \n ')
            #\t Pachinqo {df[df["compiler"] == "Pachinqo"]["total_fidelity"].mean()} \n ')
    
    #ax.set_ylim(0, 1)  # Set y-axis limits to 0-1000ms for circuit duration

def plot_e2e_results_duration_means(ax, title, set_sizes, multiq_results_file="results/multiq/e2e_results.csv", zac_results_file="results/zac/e2e_results.csv", pachinqo_results_file="results/pachinqo/e2e_results.csv"):
    data_zac = pd.read_csv(zac_results_file)
    data_pachinqo = pd.read_csv(pachinqo_results_file)
    data_multiq = pd.read_csv(multiq_results_file)

    df = pd.DataFrame(columns=['set_size', 'total_fidelity', 'cir_duration', 'compiler'])

    #data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    avg_fids = []
    for set_size in set_sizes:
            benchmarks = data_multiq[data_multiq['set_size'] == set_size]['benchmark'].unique()
            df.loc[len(df)] = [set_size, data_zac[data_zac['benchmark'].isin(benchmarks)]['total_fidelity'].mean(), data_zac[data_zac['benchmark'].isin(benchmarks)]['cir_duration'].mean()/1000, 'ZAC']
            df.loc[len(df)] = [set_size, data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 1]['cir_fidelity'].mean(), data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 1]['cir_duration'].mean()/1000, 'MultiQ (1 Row)']
            df.loc[len(df)] = [set_size, data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 2]['cir_fidelity'].mean(), data_multiq[data_multiq['set_size'] == set_size][data_multiq['n_rows'] == 2]['cir_duration'].mean()/1000, 'MultiQ (2 Row)']
            df.loc[len(df)] = [set_size, data_pachinqo[data_pachinqo['benchmark'].isin(benchmarks)]['total_fidelity'].mean(), data_pachinqo[data_pachinqo['benchmark'].isin(benchmarks)]['execution_time'].mean()/1000, 'Pachinqo']
    
    ax.grid(True)

    higher_lower_is_better_loc = (0.58, 1.02)

    plot_df = df[df['compiler'].isin(['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC'])]

    bar_plot.grouped_barplot(plot_df,
                             ax=ax,
                             grouping_column='compiler',
                             xcol='set_size',
                             ycol='cir_duration',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             legend_ncol=5,
                             higher_lower_is_better='lower',
                             higher_lower_is_better_loc=higher_lower_is_better_loc,
                             xlabel='Set size',
                             legend=False,
                             legend_loc=(0.5, -0.3),
                             ylabel='Circuit duration [ms]')
    
    ax.set_ylim(0, max(plot_df['cir_duration']+3))  # Set y-axis limits to 0-1000ms for circuit duration
    #ax.ticklabel_format(axis='y', scilimits=[0, 3])

    ax.hlines(df[df['compiler']=='ZAC'][df['set_size']==12]['cir_duration'].mean(), xmin=ax.containers[0][4].get_x(), xmax=ax.containers[0][4].get_x()+ax.containers[0][4]._width*3, colors='red', linestyles='dashed')
    ax.text(ax.containers[1][4].get_x() + ax.containers[1][4]._width/4, df[df['compiler']=='MultiQ (1 Row)'][df['set_size']==12]['cir_duration'].mean()+0.5, f'+{(df[df['compiler']=='MultiQ (1 Row)'][df['set_size']==12]['cir_duration'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==12]["cir_duration"].mean()):.1f}', fontsize=9, color='red', rotation=90)
    ax.text(ax.containers[2][4].get_x() + ax.containers[2][4]._width/4, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==12]['cir_duration'].mean()+0.5, f'+{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==12]['cir_duration'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==12]["cir_duration"].mean()):.1f}', fontsize=9, color='red', rotation=90)
    
    ax.hlines(df[df['compiler']=='ZAC'][df['set_size']==4]['cir_duration'].mean(), xmin=ax.containers[0][0].get_x(), xmax=ax.containers[0][0].get_x()+ax.containers[0][4]._width*3, colors='red', linestyles='dashed')
    ax.text(ax.containers[1][0].get_x() + ax.containers[1][0]._width/4, df[df['compiler']=='MultiQ (1 Row)'][df['set_size']==4]['cir_duration'].mean()+0.5, f'+{(df[df['compiler']=='MultiQ (1 Row)'][df['set_size']==4]['cir_duration'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==4]["cir_duration"].mean()):.1f}', fontsize=9, color='red', rotation=90)
    ax.text(ax.containers[2][0].get_x() + ax.containers[2][0]._width/4, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['cir_duration'].mean()+0.5, f'+{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['cir_duration'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==4]["cir_duration"].mean()):.1f}', fontsize=9, color='red', rotation=90)

    if len(data_multiq['benchmark'].unique()) == 6:
        ax.text(5.855, 11500, f'+{df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')
        
        ax.text(6.15, 11500, f'+{df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean():.0f}',
                rotation=90, fontsize=12, color='red')
    elif len(data_multiq['benchmark'].unique()) == 8:
        ax.text(7.855, 9200, f'+{abs(df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='red')

        ax.text(8.17, 8300, f'-{abs(df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='green')
    else:
        ax.text(9.87, 13000, f'+{abs(df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='red')

        ax.text(10.15, 12500, f'+{abs(df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()):.0f}',
                rotation=90, fontsize=12, color='red')

    # Add Mean to the x-ticks
    xtick_labels = [*list(data_multiq['benchmark'].unique()), 'Mean']

    
    ax.set_xticklabels(xtick_labels, rotation=10, ha='right')  # Rotate x-tick labels for better readability
    set_sizes = sorted(set_sizes)
    for set_size in set_sizes:
        print(f'Mean circuit duration (Set {set_size}): \n \
            \t ZAC {df[df["compiler"] == "ZAC"][df["set_size"] == set_size]["cir_duration"].mean():.2f} \n \
            \t MultiQ (1 Row) {df[df["compiler"] == "MultiQ (1 Row)"][df["set_size"] == set_size]["cir_duration"].mean():.2f} \n \
            \t MultiQ (2 Row) {df[df["compiler"] == "MultiQ (2 Row)"][df["set_size"] == set_size]["cir_duration"].mean():.2f} \n \
            \t Pachinqo {df[df["compiler"] == "Pachinqo"][df["set_size"] == set_size]["cir_duration"].mean():.2f} \n ')
        

def plot_e2e_results_total_runtime(ax, title, set_size, include_pachinqo=False, include_powermove=False, include_qmap=False, include_zap=False, higher_lower_is_better='lower', xticks_visible=True, bar_width=0.35):
    data_multiq = pd.read_csv(f"results/multiq/e2e_results.csv")
    data_zac = pd.read_csv("results/zac/e2e_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo/e2e_results.csv")
    data_powermove = pd.read_csv("results/powermove/e2e_results.csv")
    data_qmap = pd.read_csv("results/qmap/e2e_results.csv")
    data_zap = pd.read_csv("results/zap/e2e_results.csv")

    df = pd.DataFrame(columns=['run_phase', 'phase_duration', 'compiler', 'set_size'])

    rows = [1,2]

    init_time = 82
    benchmark_set = ''
    benchmark_set = f'Set {len(data_zac["benchmark"].unique())}'

    run_time = 0
    initialization_time = 0

    run_phases_zac = []

    for _, size in enumerate(set_size):
        data = data_multiq[data_multiq['set_size'] == size]
        run_time = 0
        initialization_time = 0
        for benchmark in data['benchmark'].unique():
            total_runtime = data_zac[data_zac['benchmark'] == benchmark]['cir_duration'].item()
            run_time += total_runtime/1000  # Convert to milliseconds
            initialization_time += init_time

        df.loc[len(df)] = ['Execution', run_time, 'ZAC', f'Set {size}']
        df.loc[len(df)] = ['Initialization', initialization_time, 'ZAC', f'Set {size}']

    if include_powermove:
        for _, size in enumerate(set_size):
            data = data_multiq[data_multiq['set_size'] == size]
            run_time = 0
            initialization_time = 0
            for benchmark in data['benchmark'].unique():
                total_runtime = data_powermove[data_powermove['benchmark'] == benchmark]['cir_duration'].item()
                run_time += total_runtime/1000  # Convert to milliseconds
                initialization_time += init_time

            df.loc[len(df)] = ['Execution', run_time, 'PowerMove', f'Set {size}']
            df.loc[len(df)] = ['Initialization', initialization_time, 'PowerMove', f'Set {size}']

    if include_qmap:
        for _, size in enumerate(set_size):
            data = data_multiq[data_multiq['set_size'] == size]
            run_time = 0
            initialization_time = 0
            for benchmark in data['benchmark'].unique():
                total_runtime = data_qmap[data_qmap['benchmark'] == benchmark]['cir_duration'].item()
                run_time += total_runtime/1000  # Convert to milliseconds
                initialization_time += init_time

            df.loc[len(df)] = ['Execution', run_time, 'QMAP', f'Set {size}']
            df.loc[len(df)] = ['Initialization', initialization_time, 'QMAP', f'Set {size}']

    if include_zap:
        for _, size in enumerate(set_size):
            data = data_multiq[data_multiq['set_size'] == size]
            run_time = 0
            initialization_time = 0
            for benchmark in data['benchmark'].unique():
                total_runtime = data_zap[data_zap['benchmark'] == benchmark]['cir_duration'].item()
                run_time += total_runtime/1000  # Convert to milliseconds
                initialization_time += init_time

            df.loc[len(df)] = ['Execution', run_time, 'ZAP', f'Set {size}']
            df.loc[len(df)] = ['Initialization', initialization_time, 'ZAP', f'Set {size}']

    if include_pachinqo:
        for _, size in enumerate(set_size):
            data = data_multiq[data_multiq['set_size'] == size]
            run_time = 0
            initialization_time = 0
            for benchmark in data['benchmark'].unique():
                if benchmark not in data_pachinqo['benchmark'].unique():
                    run_time += data_pachinqo[data_pachinqo['benchmark'].isin(data['benchmark'].unique())]['execution_time'].mean()/1000
                    initialization_time += init_time
                    continue
                run_time += data_pachinqo[data_pachinqo['benchmark'] == benchmark]['execution_time'].item()/1000
                initialization_time += init_time

            df.loc[len(df)] = ['Execution', run_time, 'PachinQo', f'Set {size}']
            df.loc[len(df)] = ['Initialization', initialization_time, 'PachinQo', f'Set {size}']

    for _,size in enumerate(set_size):
        data = data_multiq[data_multiq['set_size'] == size]
        for row in rows:
            run_time = 0
            initialization_time = 0
            for bin_idx in data[data['n_rows'] == row]['bin_idx'].unique():
                longest_duration = data[
                    (data['bin_idx'] == bin_idx) &
                    (data['n_rows'] == row)]['cir_duration'].max()
                #benchmark = '-'.join(data_multiq[
                #    (data_multiq['bin_idx'] == bin_idx) &
                #    (data_multiq['n_aods'] == aod_row[0]) &
                #    (data_multiq['n_rows'] == aod_row[1])]['benchmark'].unique())

                if longest_duration != 0:
                    run_time += longest_duration / 1000  # Convert to milliseconds
                    initialization_time += init_time

            df.loc[len(df)] = ['Execution', run_time, f'MultiQ({row} Row)', f'Set {size}']
            df.loc[len(df)] = ['Initialization', initialization_time, f'MultiQ({row} Row)', f'Set {size}']

    # Compute mean for each compiler over all sets sizes
    #df.loc[len(df)] = ['Mean', 'Execution', df[df['compiler'] == 'ZAC'][df['run_phase'] == 'Execution']['phase_duration'].mean(), 'ZAC', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Initialization', df[df['compiler'] == 'ZAC'][df['run_phase'] == 'Initialization']['phase_duration'].mean(), 'ZAC', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Execution', df[df['compiler'] == 'MultiQ(2 Row)'][df['run_phase'] == 'Execution']['phase_duration'].mean(), 'MultiQ(2 Row)', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Initialization', df[df['compiler'] == 'MultiQ(2 Row)'][df['run_phase'] == 'Initialization']['phase_duration'].mean(), 'MultiQ(2 Row)', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Execution', df[df['compiler'] == 'MultiQ(1 Row)'][df['run_phase'] == 'Execution']['phase_duration'].mean(), 'MultiQ(1 Row)', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Initialization', df[df['compiler'] == 'MultiQ(1 Row)'][df['run_phase'] == 'Initialization']['phase_duration'].mean(), 'MultiQ(1 Row)', 'Mean']
    
    ax.grid(True)

    #ax.set_yscale('log')

    compiler_order = ['MultiQ(1 Row)', 'MultiQ(2 Row)', 'ZAC']
    if include_powermove:
        compiler_order.append('PowerMove')
    if include_qmap:
        compiler_order.append('QMAP')
    if include_zap:
        compiler_order.append('ZAP')
    if include_pachinqo:
        compiler_order.append('PachinQo')
    
    phase_order = ['Execution', 'Initialization']
    set_order = [f'Set {size}' for size in set_size]  # Define the order of set sizes explicitly, matching what was requested
    #set_order.append('Mean')  # Add 'Mean' to the set order

    # Convert to categorical with specified order
    df['compiler'] = pd.Categorical(df['compiler'], categories=compiler_order, ordered=True)
    df['set_size'] = pd.Categorical(df['set_size'], categories=set_order, ordered=True)
    df['run_phase'] = pd.Categorical(df['run_phase'], categories=phase_order, ordered=True)

    # Sort the dataframe by the categorical columns
    df = df.sort_values(['compiler', 'run_phase'], ascending=[True, False])
    
    ax = bar_plot.stacked_grouped_barplot(df,
                                          ax=ax,
                                          grouping_column='compiler',
                                          stacking_column='run_phase',
                                          xcol='set_size',
                                          ycol='phase_duration',
                                          title=title,
                                          title_loc='left',
                                          spacing=0.85,
                                          linewidth=1.75,
                                          legend_ncol=1,
                                          higher_lower_is_better=higher_lower_is_better,
                                          higher_lower_is_better_loc=(0.8, 1.02),
                                          xlabel='Benchmarks sets',
                                          legend=True,
                                          legend_loc=(0.3, 0.755) if not include_pachinqo else (0.01, 0.7),
                                          ylabel='Total runtime [ms]',
                                          ylim=600,
                                          xticks=xticks_visible)
    
    #ax.text(ax.containers[0][1], 0.95, f'{df[df["compiler"] == "ZAC"][df["set_size"] == "Set 8"]["phase_duration"].sum():.0f} ms', transform=ax.transAxes, fontsize=12, color='red', ha='center', va='center')
    #ax.text(0.6, 0.95, f'{df[df["compiler"] == "ZAC"][df["set_size"] == "Set 10"]["phase_duration"].sum():.0f} ms', transform=ax.transAxes, fontsize=12, color='red', ha='center', va='center')
    #ax.text(0.837, 0.95, f'{df[df["compiler"] == "ZAC"][df["set_size"] == "Mean"]["phase_duration"].sum():.0f} ms', transform=ax.transAxes, fontsize=12, color='red', ha='center', va='center')
    
    #ax.get_legend().remove()  # Remove the legend from the stacked bar plot

    #ax.rectangle

    #ax.annotate('', xy=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 4']['phase_duration'].sum()+1), xytext=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][0].get_x()+ ax.containers[0][0]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 4']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    #ax.annotate('', xy=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 6']['phase_duration'].sum()+1), xytext=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][0].get_x()+ ax.containers[0][1]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 6']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][1].get_x() + ax.containers[2][1]._width/2, df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 8']['phase_duration'].sum()+2), xytext=(ax.containers[2][1].get_x() + ax.containers[2][1]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][1].get_x()+ ax.containers[0][1]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 8']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][2].get_x() + ax.containers[2][2]._width/2, df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 10']['phase_duration'].sum()+1), xytext=(ax.containers[2][2].get_x() + ax.containers[2][2]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][2].get_x()+ ax.containers[0][2]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 10']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][3].get_x() + ax.containers[2][3]._width/2, df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 12']['phase_duration'].sum()+1), xytext=(ax.containers[2][3].get_x() + ax.containers[2][3]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][3].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 12']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][4].get_x() + ax.containers[2][4]._width/2, df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 14']['phase_duration'].sum()+1), xytext=(ax.containers[2][4].get_x() + ax.containers[2][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][4].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 14']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    #print(f'Mean ratios: \n \t MultiQ (1 Row) vs ZAC {df[df["compiler"] == "MultiQ (1 Row)"][""].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()} \n \t MultiQ (2 Row) vs ZAC {df[df["compiler"] == "MultiQ (2 Row)"]["cir_duration"].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()}')
    print(f'(Set 4) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 4"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 4"]['phase_duration'].sum():.1f}')
    print(f'(Set 6) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 6"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 6"]['phase_duration'].sum():.1f}')
    print(f'(Set 8) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 8"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 8"]['phase_duration'].sum():.1f}')
    print(f'(Set 10) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 10"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 10"]['phase_duration'].sum():.1f}')
    print(f'(Set 12) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 12"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 12"]['phase_duration'].sum():.1f}')
    print(f'(Set 12) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 14"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 14"]['phase_duration'].sum():.1f}')
    ax.set_ylim(0, 1300)
    
    if include_pachinqo:
        ax.set_ylim(0, 1800)
    
    return df

    
    #labels = ['ZAC'] + [f'MultiQ ({row} Row/Set {size})' for row in rows for size in set_size]
    #Set the x-ticks to the specific labels for MultiQ and ZAC
    #ax.set_xticks(range(1, 6))
    #ax.set_xticklabels(labels, ha='right', rotation=45)  # Rotate x-tick labels for better readability


# Per-stage hatch, reused across all three overhead-breakdown plots so a
# stage stays identifiable by pattern alone in grayscale printouts (the
# journal's b/w-readability requirement) -- combined in
# stacked_grouped_barplot with the row-config's own hatch ('*' for 1 Row,
# 'o' for 2 Row), so neither channel collides with the other.
_OVERHEAD_STAGE_HATCHES = {
    'Planning': '..',
    'Bundling': 'xx',
    'Backend compilation (ZAC)': '//',
    'Placement': '\\\\',
    'Routing': '||',
}


def _annotate_overhead_totals(ax, df, xcol, row_order):
    """
    Adds value/percentage callouts above the bars. Two layouts, chosen by
    how many groups this panel has:

    - 2 groups (vs set size: MultiQ 1 Row/2 Row only, no backend-only
      reference bar available for that sweep) -- "+N%" of 2-Row over 1-Row,
      as a pairwise comparison.
    - 3 groups (vs circuit size / vs QPU size, which do have a "Backend
      only" bar per x-group) -- "+N%" of *each* of 1-Row and 2-Row over
      that shared backend-only baseline, rather than over each other.

    Either way this is plain numeric annotation rather than compressing the
    y-axis -- more honest than hiding the gap with a broken or log axis.
    """
    positions = getattr(ax, '_grouped_bar_positions', None)
    if not positions or len(row_order) not in (2, 3):
        return

    totals = df.groupby([xcol, 'row_config'], observed=True)['duration'].sum()
    x_labels = df[xcol].cat.categories if hasattr(df[xcol], 'cat') else df[xcol].unique()

    # Headroom for the value labels above the tallest bar (each "T\n+P%"
    # label is two lines tall).
    ax.set_ylim(0, ax.get_ylim()[1] * 1.22)
    max_label_pad = ax.get_ylim()[1] * 0.06

    if len(row_order) == 3:
        _annotate_overhead_vs_backend(ax, totals, positions, x_labels, row_order, max_label_pad)
    else:
        _annotate_overhead_pairwise(ax, totals, positions, x_labels, row_order)


def _annotate_overhead_pairwise(ax, totals, positions, x_labels, row_order):
    """
    Plain total above each of the two bars (1-Row, 2-Row) in the same
    x-group -- no "+N%" delta, just the numbers, both in black.
    """
    r1, r2 = row_order

    for label in x_labels:
        if (label, r1) not in totals.index or (label, r2) not in totals.index:
            continue
        x1, x2 = positions.get(r1, {}).get(label), positions.get(r2, {}).get(label)
        t1, t2 = totals[(label, r1)], totals[(label, r2)]
        if x1 is None or x2 is None or t1 <= 0:
            continue

        ax.text(x1, t1, f'{t1:.0f}', ha='center', va='bottom', fontsize=9, zorder=6)
        ax.text(x2, t2, f'{t2:.0f}', ha='center', va='bottom', fontsize=9, zorder=6)


def _annotate_overhead_vs_backend(ax, totals, positions, x_labels, row_order, max_label_pad):
    """
    "+N%" of *each* of 1-Row and 2-Row over the shared "Backend only" bar in
    the same x-group -- i.e. how much MultiQ's own stages add on top of the
    backend compiler's own unavoidable cost, rather than one row-config
    compared to the other. The Backend bar itself (plain black total) is
    the visible baseline; 1-Row's and 2-Row's own two-line labels are
    stacked upward off of it (and each other) when they'd otherwise land at
    almost the same height and collide.
    """
    backend, r1, r2 = row_order

    for label in x_labels:
        if any((label, r) not in totals.index for r in row_order):
            continue
        xb = positions.get(backend, {}).get(label)
        tb = totals.get((label, backend))
        if xb is None or tb is None or tb <= 0:
            continue

        fontsize = 9

        # Plain black total on the Backend bar (no "+N%", it's the
        # baseline) -- black rather than the firebrick used for the other
        # two bars' callouts keeps it visually distinct as the reference,
        # not another delta to read.
        ax.text(xb, tb, f'{tb:.0f}', ha='center', va='bottom',
                fontsize=fontsize, color='black', zorder=6)

        # r1 and r2 are adjacent, narrow bars that can land at nearly the
        # same height as Backend and each other (e.g. ~20q: B=93, 1R=94,
        # 2R=113 on an axis that also has to fit ~100q's 663) -- track the
        # previous label's top edge (starting from Backend's own, just
        # placed above) so each subsequent label gets bumped up instead of
        # overlapping, rather than relying on bar-height differences alone.
        prev_label_top = tb + max_label_pad

        for r in (r1, r2):
            x, t = positions.get(r, {}).get(label), totals.get((label, r))
            if x is None or t is None or t <= tb:
                continue

            pct = (t - tb) / tb * 100

            # Absolute total always on top of the percentage, two lines.
            text = f'{t:.0f}\n+{pct:.0f}%'

            text_y = max(t, prev_label_top)
            ax.text(x, text_y, text, ha='center', va='bottom',
                    fontsize=fontsize, color='firebrick', fontweight='bold', zorder=6,
                    multialignment='center', linespacing=1.3)
            prev_label_top = text_y + max_label_pad * 1.9


def _plot_multiq_overhead_breakdown(df, ax, title, xcol, xlabel, include_backend_bar=False):
    """
    Shared renderer for the three MultiQ overhead-breakdown plots (vs set
    size / circuit size / QPU size). `df` columns: [xcol, 'row_config',
    'stage', 'duration']. Stacks MultiQ's own stages (planning, bundling,
    placement, routing) with the embedded/swappable backend compiler's own
    per-circuit compilation step ("Backend compilation (ZAC)") capping the top
    as its own labeled segment -- MultiQ accepts any NA compiler as that
    backend, so its cost is shown separately rather than folded into
    MultiQ's own overhead.

    include_backend_bar adds a leading "Backend" bar/group per x-category
    holding just the compilation(backend) stage (df already has a
    'Backend' row_config with only that stage populated), used as the
    reference the "+N%" callouts are measured against instead of comparing
    1-Row/2-Row to each other.
    """
    stage_order = ['Planning', 'Bundling', 'Backend compilation (ZAC)', 'Placement', 'Routing']
    row_order = ['Backend', 'MultiQ(1 Row)', 'MultiQ(2 Row)'] if include_backend_bar else ['MultiQ(1 Row)', 'MultiQ(2 Row)']

    df['stage'] = pd.Categorical(df['stage'], categories=stage_order, ordered=True)
    df['row_config'] = pd.Categorical(df['row_config'], categories=row_order, ordered=True)

    ax = bar_plot.stacked_grouped_barplot(df,
                                          ax=ax,
                                          grouping_column='row_config',
                                          stacking_column='stage',
                                          xcol=xcol,
                                          ycol='duration',
                                          title=title,
                                          title_loc='left',
                                          linewidth=1.75,
                                          higher_lower_is_better='lower',
                                          xlabel=xlabel,
                                          legend=True,
                                          legend_loc=(0.5, -0.3),
                                          legend_ncol=3,
                                          ylabel='Overhead [s]',
                                          higher_lower_is_better_loc=(0.5, 1.05),
                                          stack_hatch_map=_OVERHEAD_STAGE_HATCHES,
                                          per_bar_group_labels=True,
                                          group_label_formatter=lambda g: 'B' if g == 'Backend' else g.replace('MultiQ(', '').replace(' Row)', 'R'))

    _annotate_overhead_totals(ax, df, xcol, row_order)

    return df


def plot_multiq_overhead_vs_set_size(ax, title, set_sizes,
                                      results_file="results/multiq/overhead_by_set_size.csv"):
    data = pd.read_csv(results_file)

    stage_cols = {
        'Planning': 'planning_time',
        'Bundling': 'bundling_time',
        'Backend compilation (ZAC)': 'scheduling_time',
        'Placement': 'placement_time',
        'Routing': 'routing_time',
    }

    df = pd.DataFrame(columns=['set_size', 'row_config', 'stage', 'duration'])
    for size in set_sizes:
        label = f'Set {size}'
        for row in [1, 2]:
            row_data = data[(data['set_size'] == size) & (data['n_rows'] == row)]
            if row_data.empty:
                continue
            for stage_label, col in stage_cols.items():
                df.loc[len(df)] = [label, f'MultiQ({row} Row)', stage_label, row_data[col].iloc[0]]

    df['set_size'] = pd.Categorical(df['set_size'], categories=[f'Set {s}' for s in set_sizes], ordered=True)

    return _plot_multiq_overhead_breakdown(df, ax, title, xcol='set_size', xlabel='Benchmark set size')


def plot_multiq_overhead_vs_circuit_size(ax, title, circuit_sizes,
                                          results_file_template="results/multiq/overhead_by_circuit_size_{size}q.csv"):
    stage_cols = {
        'Planning': 'planning_time',
        'Bundling': 'bundling_time',
        'Backend compilation (ZAC)': 'scheduling_time',
        'Placement': 'placement_time',
        'Routing': 'routing_time',
    }

    df = pd.DataFrame(columns=['group', 'row_config', 'stage', 'duration'])
    for size in circuit_sizes:
        label = f'~{size}q'
        data = pd.read_csv(results_file_template.format(size=size))
        backend_times = []
        for row in [1, 2]:
            row_data = data[data['n_rows'] == row]
            if row_data.empty:
                continue
            for stage_label, col in stage_cols.items():
                df.loc[len(df)] = [label, f'MultiQ({row} Row)', stage_label, row_data[col].iloc[0]]
            backend_times.append(row_data['scheduling_time'].iloc[0])

        # Reference bar: backend-compiler-only cost (the "Compilation
        # (backend)" stage on its own, averaged over the two row configs --
        # they differ only slightly since the row count barely affects the
        # backend compiler's own per-bin work), so the "+N%" callouts below
        # can be measured against it instead of against each other.
        if backend_times:
            df.loc[len(df)] = [label, 'Backend', 'Backend compilation (ZAC)', sum(backend_times) / len(backend_times)]

    df['group'] = pd.Categorical(df['group'], categories=[f'~{s}q' for s in circuit_sizes], ordered=True)

    return _plot_multiq_overhead_breakdown(df, ax, title, xcol='group', xlabel='Circuit size (6 circuits, fixed QPU)',
                                            include_backend_bar=True)


def plot_multiq_overhead_vs_qpu_size(ax, title, qpu_capacities,
                                      results_file_template="results/multiq/overhead_by_qpu_size_{capacity}q.csv"):
    stage_cols = {
        'Planning': 'planning_time',
        'Bundling': 'bundling_time',
        'Backend compilation (ZAC)': 'scheduling_time',
        'Placement': 'placement_time',
        'Routing': 'routing_time',
    }

    df = pd.DataFrame(columns=['group', 'row_config', 'stage', 'duration'])
    for capacity in qpu_capacities:
        label = f'~{capacity}q'
        data = pd.read_csv(results_file_template.format(capacity=capacity))
        backend_times = []
        for row in [1, 2]:
            row_data = data[data['n_rows'] == row]
            if row_data.empty:
                continue
            for stage_label, col in stage_cols.items():
                df.loc[len(df)] = [label, f'MultiQ({row} Row)', stage_label, row_data[col].iloc[0]]
            backend_times.append(row_data['scheduling_time'].iloc[0])

        # See plot_multiq_overhead_vs_circuit_size's comment on this same
        # pattern -- backend-only reference bar, averaged over row configs.
        if backend_times:
            df.loc[len(df)] = [label, 'Backend', 'Backend compilation (ZAC)', sum(backend_times) / len(backend_times)]

    df['group'] = pd.Categorical(df['group'], categories=[f'~{c}q' for c in qpu_capacities], ordered=True)

    return _plot_multiq_overhead_breakdown(df, ax, title, xcol='group', xlabel='QPU capacity (6x30q circuits, fixed)',
                                            include_backend_bar=True)


def plot_e2e_rows_sweep_fidelity(ax, title, row_values,
                                  results_file_template="results/multiq/rows_sweep_{rows}rows.csv"):
    """
    Grouped bar chart: one group per storage-zone row count (`row_values`),
    one bar per benchmark within each group. MultiQ only -- baselines have
    no equivalent "storage zone rows" axis.
    """
    df = pd.DataFrame(columns=['rows', 'benchmark', 'fidelity'])
    for rows in row_values:
        data = pd.read_csv(results_file_template.format(rows=rows))
        for benchmark in data['benchmark'].unique():
            df.loc[len(df)] = [str(rows), benchmark, data[data['benchmark'] == benchmark]['cir_fidelity'].item()]

    df['rows'] = pd.Categorical(df['rows'], categories=[str(r) for r in row_values], ordered=True)

    bar_plot.grouped_barplot(df,
                             ax=ax,
                             grouping_column='benchmark',
                             xcol='rows',
                             ycol='fidelity',
                             title=title,
                             title_loc='left',
                             errorbar=None,
                             linewidth=1.75,
                             xlabel='Storage zone rows',
                             legend=False,
                             ylabel='Fidelity',
                             legend_ncol=2)
    ax.grid(True)