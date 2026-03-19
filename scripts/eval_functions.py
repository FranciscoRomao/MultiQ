# %%
import pdb
import yaml
import numpy as np
import pandas as pd
import warnings
from plotting import bar_plot, line_plot
from plotting import utils, defaults
import ast
import seaborn as sns
import random
import matplotlib.pyplot as plt

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

def plot_shuttling_times_vs_utilization_zac(ax, title):
    data_zac = pd.read_csv("organize/zac_results.csv")

    qpu_size_zac = 250
    data_zac['qpu_utilization'] = [int(data_zac.iloc[i]['nqubits']*100/qpu_size_zac) for i in range(len(data_zac))]
    data_zac['type'] = ['Grouped' if len(data_zac.iloc[i]['benchmark'].split('_')) > 1 else 'Sequential' for i in range(len(data_zac))]
    data_zac['grouped_circuits'] = [len(data_zac.iloc[i]['benchmark'].split('_')) for i in range(len(data_zac))]

    for i in range(len(data_zac)):
        if data_zac.iloc[i]['type'] == 'Sequential':
            data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
            #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']
        else:
            grouped_benchmarks = data_zac.iloc[i]['benchmark'].split('_')

            solo_shuttling_times = []
            solo_exec_times = []

            for j in grouped_benchmarks:
                solo_shuttling_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['cir_shuttling_time'].mean()))
                #solo_exec_times.append(float(data_zac[data_zac['benchmark'] == j][data_zac['nqubits'] == data_zac.iloc[i]['nqubits']//len(grouped_benchmarks)]['execution_time'].mean()))

            data_zac.at[i, 'updated_shuttling_time'] = data_zac.iloc[i]['cir_shuttling_time']
            #data_zac.at[i, 'updated_execution_time'] = data_zac.iloc[i]['execution_time']

            #add row to data_zac copy of this one with uptated fidelity as g1_2q_mov_trans_avg
            data_zac.loc[len(data_zac)] = data_zac.iloc[i]
            data_zac.at[len(data_zac)-1, 'updated_shuttling_time'] = max(solo_shuttling_times)
            #data_zac.at[len(data_zac)-1, 'updated_execution_time'] = max(solo_exec_times)
            data_zac.at[len(data_zac)-1, 'type'] = 'Grouped Independent'

    data_zac = data_zac[data_zac['nqubits'] != 25]
    data_zac = data_zac[data_zac['nqubits'] != 20]
    data_zac = data_zac[data_zac['nqubits'] != 10]

    data_zac['updated_shuttling_time'] = data_zac['updated_shuttling_time'] / 1000

    ax.grid(True)

    bar_plot.grouped_barplot(data_zac,
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
    data_zac = pd.read_csv("organize/zac_results.csv")

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
                             group_labels='',
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
    data_zac = pd.read_csv("organize/zac_results.csv")
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")
    data_atomique = pd.read_csv("organize/atomique_results.csv")

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
                             higher_lower_is_better='higher',
                             higher_lower_is_better_loc=(0.7, 1.02),
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
    ax.annotate('Threshold point (170-qubit circuit) \n Execution time = Initialization time (82 ms)] ', xy=(3.35, 100), xytext=(3.05, 258), horizontalalignment='center', arrowprops=dict(color='black'))
    
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
    data_zac = pd.read_csv("organize/zac_results.csv")
    data_pachinqo = pd.read_csv("organize/pachinqo_results.csv")
    data_atomique = pd.read_csv("organize/atomique_results.csv")

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
                             higher_lower_is_better_loc=(0.7, 1.02),
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
    ax.annotate('170-qubit circuit \n 0.08 fidelity', xy=(3.375, 0.12), xytext=(3.65, 0.4), horizontalalignment='center', arrowprops=dict(color='black'))

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
    data_zac = pd.read_csv("results/preeval/zac_preeval.csv")

    for i in range(len(data_zac)):
        data_zac.at[i, 'relative_fidelity'] = float(data_zac.iloc[i]['total_fidelity']) / float(data_zac[data_zac['ratio']=='1_1'][data_zac['nqubits']==data_zac.iloc[i]['nqubits']][data_zac['benchmark']==data_zac.iloc[i]['benchmark']]['total_fidelity'])

    data_zac.sort_values(by='relative_fidelity', inplace=True)

    # Plot the grouped data
    out = bar_plot.grouped_barplot(data=data_zac,
                                   ax=ax,
                                   xcol='nqubits',
                                   ycol='relative_fidelity',
                                   grouping_column='ratio',
                                   title=title,
                                   title_loc='left',
                                   linewidth=1.75,
                                   higher_lower_is_better='higher',
                                   higher_lower_is_better_loc=(0.7, 1.02),
                                   xlabel='Circuit size (#qubits)',
                                   legend=False,
                                   legend_loc=(0.5, -0.4),
                                   ylabel='Fidelity (relative to ratio 1:1)',)
    
    #handles = out.get_children()
    
    ax.legend(bbox_to_anchor=(0.01, 1), ncol=1, fontsize=12, frameon=True, labels=['Ratio 1:4', 'Ratio 1:1', 'Ratio 4:1'], title='Layout ratio (width:height)', title_fontsize=12, loc='upper left')

    ax.grid(True)

    #return handles

    #ax.set_title(title, fontweight='bold', loc='left')
    #ax.set_xlabel('Layout Width')
    #sax.set_ylabel('Shuttling Time [ms]')

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

def plot_controler_execution_time(ax, title):
    data_multiq = pd.read_csv("results/multiq/e2e_results.csv")
    data_zac = pd.read_csv("results/zac/controller_results.csv")

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

    df = pd.DataFrame(columns=['set_size', 'total_duration', 'compiler'])
    set_sizes = data_multiq['set_size'].unique()
    
    for size in set_sizes:
        for j in data_multiq[data_multiq['set_size'] == size]['n_rows'].unique():
            df.loc[len(df)] = [f'Set {size}', data_multiq[data_multiq['set_size'] == size][data_multiq['n_rows'] == j]['cir_duration'].max()/1000, f'MultiQ ({j} Row)']
    
    for i in range(len(data_zac)):
        df.loc[len(df)] = [f'Set {len(data_zac.at[i,'benchmark'].split('-'))}', data_zac.at[i,'execution_time'], 'ZAC']

    #data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    #data['decoherence_error'] = [(1 - float(i))*100 for i in data['total_coherence_fidelity']]
    #data['utilization'] = [(i-1)*3/qpu_width for i in data['storage_zone_cols']]  # Assuming 250 is the max width

    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']  # Define the order of set sizes explicitly

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
                             legend_loc=(0.5, -0.38),
                             ylabel='Execution time (ms)',)
    
    ax.set_ylim(0, max(df['total_duration']) + 2)  # Set y-axis limits to 0-100% for utilization
    
    #ax.hlines(df[df['compiler']=='ZAC'][df['set_size']==4]['cir_duration'].mean(), xmin=ax.containers[0][0].get_x(), xmax=ax.containers[0][0].get_x()+ax.containers[0][4]._width*3, colors='red', linestyles='dashed')
    ax.annotate('', xy=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['total_duration']+1), xytext=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][4].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration']/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['total_duration'].item()):.1f}x', fontsize=9, color='green')

    ax.annotate('', xy=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['total_duration']+1), xytext=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][0].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration']/2+8, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['total_duration'].item()):.1f}x', fontsize=9, color='green')
    #ax.text(ax.containers[2][4].get_x() + ax.containers[2][0]._width/4, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['cir_duration'].mean()+0.5, f'+{(df[df['compiler']=='MultiQ (2 Row)'][df['set_size']==4]['cir_duration'].mean() - df[df["compiler"] == "ZAC"][df['set_size']==4]["cir_duration"].mean()):.1f}', fontsize=9, color='red', rotation=90)

    ax.annotate('', xy=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['total_duration']+1), xytext=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][5].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['total_duration']/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['total_duration'].item()):.1f}x', fontsize=9, color='green')
    
def plot_controler_decoherence_error(ax, title):
    data_multiq = pd.read_csv("results/multiq/e2e_results.csv")
    data_zac = pd.read_csv("results/zac/controller_results.csv")

    qpu_width = 230 #um
    storage_cols_separation = 3 #um

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
        
    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']  # Define the order of set sizes explicitly

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

    ax.annotate('', xy=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['decoherence_error']+1), xytext=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['decoherence_error']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][4].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['decoherence_error']/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['decoherence_error'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['decoherence_error'].item()):.1f}x', fontsize=9, color='green')

    ax.annotate('', xy=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['decoherence_error']+1), xytext=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['decoherence_error']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][0].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['decoherence_error']/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['decoherence_error'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['decoherence_error'].item()):.1f}x', fontsize=9, color='green')

    ax.annotate('', xy=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['decoherence_error']+1), xytext=(ax.containers[1][5].get_x() + ax.containers[1][5]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['decoherence_error']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][5].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['decoherence_error']/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['decoherence_error'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 14']['decoherence_error'].item()):.1f}x', fontsize=9, color='green')

def plot_e2e_results_fidelity(ax, set_size, title, multiq_results_file="results/multiq/e2e_results.csv", zac_results_file="results/zac/e2e_results.csv", pachinqo_results_file="results/pachinqo/e2e_results.csv", include_pachinqo=False):
    data_multiq = pd.read_csv(multiq_results_file)
    data_zac = pd.read_csv(zac_results_file)
    data_pachinqo = pd.read_csv(pachinqo_results_file)

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
        
        if include_pachinqo:
            if benchmark in data_pachinqo['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_pachinqo[data_pachinqo['benchmark'] == benchmark]['total_fidelity'].item(), data_pachinqo[data_pachinqo['benchmark'] == benchmark]['execution_time'].item(), 'Pachinqo']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'Pachinqo']
    
    # Add mean of all benchmarks for each compiler
    df.loc[len(df)] = ['Mean', df[df['compiler']=='ZAC']['total_fidelity'].mean(), data_zac['cir_duration'].mean(), 'ZAC']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean(), 'MultiQ (1 Row)']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean(), 'MultiQ (2 Row)']
    if include_pachinqo:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='Pachinqo'][df['benchmark'].isin(data_pachinqo['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='Pachinqo']['cir_duration'].mean(), 'Pachinqo']

    ax.grid(True)

    higher_lower_is_better_loc = (0.68, 1.02)

    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
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
    ax.set_xticklabels(xtick_labels, rotation=20 if include_pachinqo else 15, ha='right')  # Rotate x-tick labels for better readability
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
    
def plot_e2e_results_duration(ax, set_size, title,multiq_results_file="results/multiq/e2e_results.csv", zac_results_file="results/zac/e2e_results.csv", pachinqo_results_file="results/pachinqo/e2e_results.csv", include_pachinqo=False):
    data_multiq = pd.read_csv(multiq_results_file)
    data_zac = pd.read_csv(zac_results_file)
    data_pachinqo = pd.read_csv(pachinqo_results_file)

    df = pd.DataFrame(columns=['benchmark', 'total_fidelity', 'cir_duration', 'compiler'])

    #data['benchmark'] = [i.split('.')[0] for i in data['benchmark']]
    for benchmark in data_multiq[data_multiq['set_size']==set_size]['benchmark'].unique():
        df.loc[len(df)] = [benchmark, data_zac[data_zac['benchmark'] == benchmark]['total_fidelity'].item(), data_zac[data_zac['benchmark'] == benchmark]['cir_duration'].item()/1000, 'ZAC']
        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1]['cir_fidelity'].item(), data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 1]['cir_duration'].item()/1000, 'MultiQ (1 Row)']
        df.loc[len(df)] = [benchmark, data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2]['cir_fidelity'].item(), data_multiq[data_multiq['set_size']==set_size][data_multiq['benchmark'] == benchmark][data_multiq['n_rows'] == 2]['cir_duration'].item()/1000, 'MultiQ (2 Row)']

        if include_pachinqo:
            if benchmark in data_pachinqo['benchmark'].unique():
                df.loc[len(df)] = [benchmark, data_pachinqo[data_pachinqo['benchmark'] == benchmark]['total_fidelity'].item(), data_pachinqo[data_pachinqo['benchmark'] == benchmark]['execution_time'].item()/1000, 'Pachinqo']
            else:
                df.loc[len(df)] = [benchmark, 0, 0, 'Pachinqo']
    
    ax.grid(True)

    df.loc[len(df)] = ['Mean', df[df['compiler']=='ZAC']['total_fidelity'].mean(), df[df['compiler']=='ZAC']['cir_duration'].mean(), 'ZAC']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (1 Row)']['cir_duration'].mean(), 'MultiQ (1 Row)']
    df.loc[len(df)] = ['Mean', df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean(), df[df['compiler']=='MultiQ (2 Row)']['cir_duration'].mean(), 'MultiQ (2 Row)']
    if include_pachinqo:
        df.loc[len(df)] = ['Mean', df[df['compiler']=='Pachinqo'][df['benchmark'].isin(data_pachinqo['benchmark'].unique())]['total_fidelity'].mean(), df[df['compiler']=='Pachinqo']['cir_duration'].mean(), 'Pachinqo']

    higher_lower_is_better_loc = (0.68, 1.02)

    compiler_order = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
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
                             higher_lower_is_better='lower',
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
    ax.set_xticklabels(xtick_labels, rotation=20 if include_pachinqo else 15, ha='right')  # Rotate x-tick labels for better readability
    print(f'Mean ratios: \n \t MultiQ (1 Row): {df[df["compiler"] == "MultiQ (1 Row)"]["cir_duration"].mean()} \n \t MultiQ (2 Row): {df[df["compiler"] == "MultiQ (2 Row)"]["cir_duration"].mean()}, \n\t ZAC: {df[df["compiler"] == "ZAC"]["cir_duration"].mean()}')

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
        

def plot_e2e_results_total_runtime(ax, title, set_size, include_pachinqo=False, higher_lower_is_better='lower', xticks_visible=True, bar_width=0.35):
    data_multiq = pd.read_csv(f"results/multiq/e2e_results.csv")
    data_zac = pd.read_csv("results/zac/e2e_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo/e2e_results.csv")

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

            df.loc[len(df)] = ['Execution', run_time, f'MultiQ\n{row} Row', f'Set {size}']
            df.loc[len(df)] = ['Initialization', initialization_time, f'MultiQ\n{row} Row', f'Set {size}']

    # Compute mean for each compiler over all sets sizes
    #df.loc[len(df)] = ['Mean', 'Execution', df[df['compiler'] == 'ZAC'][df['run_phase'] == 'Execution']['phase_duration'].mean(), 'ZAC', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Initialization', df[df['compiler'] == 'ZAC'][df['run_phase'] == 'Initialization']['phase_duration'].mean(), 'ZAC', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Execution', df[df['compiler'] == 'MultiQ\n2 Row'][df['run_phase'] == 'Execution']['phase_duration'].mean(), 'MultiQ\n2 Row', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Initialization', df[df['compiler'] == 'MultiQ\n2 Row'][df['run_phase'] == 'Initialization']['phase_duration'].mean(), 'MultiQ\n2 Row', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Execution', df[df['compiler'] == 'MultiQ\n1 Row'][df['run_phase'] == 'Execution']['phase_duration'].mean(), 'MultiQ\n1 Row', 'Mean']
    #df.loc[len(df)] = ['Mean', 'Initialization', df[df['compiler'] == 'MultiQ\n1 Row'][df['run_phase'] == 'Initialization']['phase_duration'].mean(), 'MultiQ\n1 Row', 'Mean']
    
    ax.grid(True)

    #ax.set_yscale('log')

    compiler_order = ['MultiQ\n1 Row', 'MultiQ\n2 Row', 'ZAC']
    if include_pachinqo:
        compiler_order.append('PachinQo')
    
    phase_order = ['Execution', 'Initialization']
    #set_order = [f'Set {size}' for size in set_size]
    #set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']  # Define the order of set sizes explicitly
    set_order = ['Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']  # Define the order of set sizes explicitly

    if include_pachinqo:
        set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']
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
                                          higher_lower_is_better_loc=(0.73, 1.02),
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

    #ax.annotate('', xy=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 4']['phase_duration'].sum()+1), xytext=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][0].get_x()+ ax.containers[0][0]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 4']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    #ax.annotate('', xy=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 6']['phase_duration'].sum()+1), xytext=(ax.containers[2][0].get_x() + ax.containers[2][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][0].get_x()+ ax.containers[0][1]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 6']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][1].get_x() + ax.containers[2][1]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 8']['phase_duration'].sum()+2), xytext=(ax.containers[2][1].get_x() + ax.containers[2][1]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][1].get_x()+ ax.containers[0][1]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 8']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][2].get_x() + ax.containers[2][2]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 10']['phase_duration'].sum()+1), xytext=(ax.containers[2][2].get_x() + ax.containers[2][2]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][2].get_x()+ ax.containers[0][2]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 10']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][3].get_x() + ax.containers[2][3]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 12']['phase_duration'].sum()+1), xytext=(ax.containers[2][3].get_x() + ax.containers[2][3]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][3].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 12']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')
#
    #ax.annotate('', xy=(ax.containers[2][4].get_x() + ax.containers[2][4]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 14']['phase_duration'].sum()+1), xytext=(ax.containers[2][4].get_x() + ax.containers[2][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    #ax.text(ax.containers[0][4].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 14']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    #print(f'Mean ratios: \n \t MultiQ (1 Row) vs ZAC {df[df["compiler"] == "MultiQ (1 Row)"][""].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()} \n \t MultiQ (2 Row) vs ZAC {df[df["compiler"] == "MultiQ (2 Row)"]["cir_duration"].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()}')
    print(f'(Set 4) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 4"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 4"]['phase_duration'].sum():.1f}')
    print(f'(Set 6) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 6"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 6"]['phase_duration'].sum():.1f}')
    print(f'(Set 8) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 8"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 8"]['phase_duration'].sum():.1f}')
    print(f'(Set 10) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 10"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 10"]['phase_duration'].sum():.1f}')
    print(f'(Set 12) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 12"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 12"]['phase_duration'].sum():.1f}')
    print(f'(Set 12) MultiQ (2 Row) vs ZAC (times faster) {df[df["compiler"] == "ZAC"][df["set_size"] == "Set 14"]["phase_duration"].sum() / df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 14"]['phase_duration'].sum():.1f}')
    ax.set_ylim(0, 1300)
    
    if include_pachinqo:
        ax.set_ylim(0, 1800)
    
    return df

    
    #labels = ['ZAC'] + [f'MultiQ ({row} Row/Set {size})' for row in rows for size in set_size]
    #Set the x-ticks to the specific labels for MultiQ and ZAC
    #ax.set_xticks(range(1, 6))
    #ax.set_xticklabels(labels, ha='right', rotation=45)  # Rotate x-tick labels for better readability