# %%
import pdb
import yaml
import numpy as np
import pandas as pd
import warnings
from plotting import bar_plot, line_plot
from plotting import utils, defaults
import seaborn as sns
import matplotlib.pyplot as plt

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

def plot_shuttling_times_vs_utilization_zac(ax, title):
    data_zac = pd.read_csv("results/zac_results.csv")

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
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")

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
    data_atomique = pd.read_csv("results/atomique_results.csv")

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
    data_atomique = pd.read_csv("results/atomique_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")
    data_atomique = pd.read_csv("results/atomique_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")
    data_atomique = pd.read_csv("results/atomique_results.csv")

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
                 label='Average')

    ax.set_xticks([nqubits_to_index[val] for val in unique_nqubits_sorted])
    ax.set_xticklabels(unique_nqubits_sorted)

    ax.legend_.remove()

    ax.hlines(y=0.08, xmin=0, xmax=3.4, color='red', linewidth=2, linestyle='--')
    ax.vlines(x=3.35, ymin=0, ymax=0.08, color='red', linewidth=2, linestyle='--')
    
    ax.plot(3.35, 0.08, marker='X', markersize=9, color='red', markeredgecolor='black', markeredgewidth=0.5)
    ax.annotate('170-qubit circuit \n 0.08 fidelity', xy=(3.375, 0.12), xytext=(3.65, 0.4), horizontalalignment='center', arrowprops=dict(color='black'))

def plot_execution_time_vs_circuit_size_average(ax, title):
    data_zac = pd.read_csv("results/zac_results.csv")
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")

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
    data_pachinqo = pd.read_csv("results/pachinqo_results.csv")

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

    data_atomique = pd.read_csv("results/atomique_results.csv")

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
    data_zac = pd.read_csv("results/zac_results.csv")
    data_atomique = pd.read_csv("results/atomique_results.csv")

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
    data_zac = pd.read_csv("results/preeval_layouts/zac_results.csv")

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