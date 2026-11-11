import os
import pandas as pd
import warnings
from scripts.plotting import bar_plot
from scripts.plotting import defaults
import seaborn as sns
import matplotlib.transforms

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)


    

    


def plot_execution_time_vs_circuit_size_zac_pachinqo_atomique(ax, title):
    data_zac = pd.read_csv("results/preeval/zac_preeval.csv")
    data_pachinqo = pd.read_csv("results/preeval/pachinqo_preeval.csv")
    data_atomique = pd.read_csv("results/preeval/atomique_preeval.csv")

    df = pd.DataFrame(columns=['nqubits', 'execution_time', 'compiler'])

    for nqubits in data_zac['nqubits'].unique():
        df.loc[len(df)] = [nqubits, data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean() / 1000, 'ZAC']
        df.loc[len(df)] = [nqubits, data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean() / 1000, 'Pachinqo']
        df.loc[len(df)] = [nqubits, data_atomique[data_atomique['nqubits'] == nqubits]['execution_time'].mean() * 1000, 'Atomique']
        df.loc[len(df)] = [nqubits, (data_zac[data_zac['nqubits'] == nqubits]['execution_time'].mean()/1000 + data_pachinqo[data_pachinqo['nqubits'] == nqubits]['execution_time'].mean()/1000 + data_atomique[data_atomique['nqubits'] == nqubits]['execution_time'].mean()*1000)/3, 'Average']
        
    
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
    nqubits_to_index = {val: i for i, val in enumerate(unique_nqubits_sorted)}

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
    # Without arrowstyle, matplotlib anchors the arrow at a corner of the text box.
    ax.annotate('Execution time = Initialization time (82 ms)\nThreshold point (170-qubit circuit)', xy=(3.3, 100), xytext=(2, 300), horizontalalignment='center', arrowprops=dict(color='black', arrowstyle='simple,head_length=0.7,head_width=0.6,tail_width=0.24', mutation_scale=20))
    ylim_top = 400
    ax.set_ylim(0, ylim_top)

    # Label bars clipped by the y-limit with their real value.
    for bars in ax.containers:
        for bar in bars:
            height = bar.get_height()
            if height > ylim_top:
                ax.text(bar.get_x() - 0.02, ylim_top * 0.97, f'{height:.0f}',
                        ha='right', va='top', rotation=90, fontsize=defaults.FONTSIZE, fontweight='bold', color='black')

    ax.legend_.remove()

    sns.set_theme()
    sns.set_style("whitegrid")


def plot_fidelity_vs_circuit_size_zac_pachinqo_atomique(ax, title):
    data_zac = pd.read_csv("results/preeval/zac_preeval.csv")
    data_pachinqo = pd.read_csv("results/preeval/pachinqo_preeval.csv")
    data_atomique = pd.read_csv("results/preeval/atomique_preeval.csv")

    df = pd.DataFrame(columns=['nqubits', 'total_fidelity', 'compiler'])

    for nqubits in data_zac['nqubits'].unique():
        df.loc[len(df)] = [nqubits, data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean(), 'ZAC']
        df.loc[len(df)] = [nqubits, data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean(), 'Pachinqo']
        df.loc[len(df)] = [nqubits, data_atomique[data_atomique['nqubits'] == nqubits]['total_fidelity'].mean(), 'Atomique']

        df.loc[len(df)] = [nqubits, (data_zac[data_zac['nqubits'] == nqubits]['total_fidelity'].mean() + data_pachinqo[data_pachinqo['nqubits'] == nqubits]['total_fidelity'].mean() + data_atomique[data_atomique['nqubits'] == nqubits]['total_fidelity'].mean())/3, 'Average']

        

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


    






def plot_planner_eval_fidelity_multiq(ax, title, complete=False):
    data = pd.read_csv("results/multiq/planner_results.csv")




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
    data['utilization'] = [100-((i-1)*storage_cols_separation*100)/qpu_width for i in data['storage_zone_cols']]

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
    
    ax.set_ylim(0, 100)

def plot_bundler_space_util(ax, title):
    data = pd.read_csv("results/multiq/bundler_results.csv")

    qpu_width = 230 #um
    nrows = 1

    df = pd.DataFrame(columns=['set_size', 'selector_algo','spatial_util'])
    
    for set_size in data[data['selector_algo'] == 'fifo']['set_size'].unique():
        sum_widths = 0
        for bin in data[data['selector_algo'] == 'fifo']['bin_idx'].unique():
            data_snip = data[(data['selector_algo'] == 'fifo') & (data['set_size'] == set_size) & (data['bin_idx'] == bin)]
            sum_widths += sum(data_snip['tile_width'])
        
        bin_utilization = sum_widths/(len(data[data['selector_algo'] == 'fifo'][data['set_size'] == set_size]['bin_idx']) * (qpu_width*nrows)) * 100
        df.loc[len(df)] = [set_size, 'fifo', bin_utilization]

    for set_size in data[data['selector_algo'] == 'sa']['set_size'].unique():
        for selector_weight in data[(data['selector_algo'] == 'sa') & (data['set_size'] == set_size)]['selector_weight'].unique():
            sum_widths = 0
            data_snip = data[(data['selector_algo'] == 'sa') & (data['set_size'] == set_size) & (data['selector_weight'] == selector_weight)]
            for bin in data_snip['bin_idx'].unique():
                sum_widths += sum(data_snip[data_snip['bin_idx']==bin]['tile_width'])
            
            bin_utilization = sum_widths/(len(data[data['selector_algo'] == 'sa'][data['set_size'] == set_size][data['selector_weight'] == selector_weight]['bin_idx'].unique()) * (qpu_width*nrows)) * 100
            df.loc[len(df)] = [set_size, f'SA - {selector_weight}', bin_utilization]
    
    ax.grid(True)


    df.sort_values(by = "selector_algo")
    df = df[df['selector_algo'] != 'SA - 0.0']
    df = df[df['selector_algo'] != 'SA - 1.0']

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
    
    ax.set_ylim(20, 100)

def plot_bundler_temporal_util(ax, title):
    data = pd.read_csv("results/multiq/bundler_results.csv")

    df = pd.DataFrame(columns=['set_size', 'selector_algo','temporal_util'])
    
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
    
    ax.set_ylim(70, 100)

def plot_controler_execution_time(ax, title, zac_results_file="results/zac/controller_results.csv", powermove_results_file="results/powermove/controller_results.csv", qmap_results_file="results/qmap/controller_results.csv", zap_results_file="results/zap/controller_results.csv", include_powermove=False, include_qmap=False, include_zap=False):
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

    set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']

    # (compiler, set_label) pairs with no data, drawn as an x marker.
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
    
    ax.set_ylim(0, max(df['total_duration']) + 2)

    marker_y = ax.get_ylim()[1] * 0.03
    for compiler_name, set_label in failed_markers:
        bar = ax.containers[compiler_order.index(compiler_name)][set_order.index(set_label)]
        ax.plot(bar.get_x() + bar.get_width() / 2, marker_y, marker='x', color='black', markersize=7, markeredgewidth=2, zorder=5)

    ax.annotate('', xy=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['total_duration']+1), xytext=(ax.containers[1][4].get_x() + ax.containers[1][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][4].get_x() - ax.containers[0][4].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration']/2, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 12']['total_duration'].item()):.1f}x', fontsize=9, color='green')

    ax.annotate('', xy=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['total_duration']+1), xytext=(ax.containers[1][0].get_x() + ax.containers[1][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration']), fontsize=9, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax.text(ax.containers[0][0].get_x() - ax.containers[0][0].get_width(), df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration']/2+8, f'{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['total_duration'].item()/df[df['compiler']=='MultiQ (2 Row)'][df['set_size']=='Set 4']['total_duration'].item()):.1f}x', fontsize=9, color='green')

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

    set_order = ['Set 4', 'Set 6', 'Set 8', 'Set 10', 'Set 12', 'Set 14']

    # (compiler, set_label) pairs with no data, drawn as an x marker.
    failed_markers = []

    df = pd.DataFrame(columns=['set_size', 'decoherence_error', 'compiler'])
    set_sizes = data_multiq['set_size'].unique()

    for size in set_sizes:
        for j in data_multiq[data_multiq['set_size'] == size]['n_rows'].unique():
            # Geometric mean over benchmarks with the same set size and row count.
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

    ax.set_ylim(0, 100)

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

    higher_lower_is_better_loc = (0.6, 1.05)

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
    ax.set_xticklabels(xtick_labels, fontsize=11)
    ax.set_ylim(0.3, 0.9)
    print(f'Mean ratios: \n \
          \t MultiQ (1 Row): {df[df['compiler']=='MultiQ (1 Row)']['total_fidelity'].mean()},\n \
          \t MultiQ (2 Row): {df[df['compiler']=='MultiQ (2 Row)']['total_fidelity'].mean()}, \n \
          \t ZAC: {df[df["compiler"] == "ZAC"]["total_fidelity"].mean()} \n ')
    
            
    print(df)
    
def plot_e2e_results_duration(ax, set_size, title,multiq_results_file="results/multiq/e2e_results.csv", zac_results_file="results/zac/e2e_results.csv", pachinqo_results_file="results/pachinqo/e2e_results.csv", powermove_results_file="results/powermove/e2e_results.csv", qmap_results_file="results/qmap/e2e_results.csv", zap_results_file="results/zap/e2e_results.csv", include_pachinqo=False, include_powermove=False, include_qmap=False, include_zap=False, higher_lower_is_better='lower'):
    data_multiq = pd.read_csv(multiq_results_file)
    data_zac = pd.read_csv(zac_results_file)
    data_pachinqo = pd.read_csv(pachinqo_results_file)
    data_powermove = pd.read_csv(powermove_results_file)
    data_qmap = pd.read_csv(qmap_results_file)
    data_zap = pd.read_csv(zap_results_file)

    df = pd.DataFrame(columns=['benchmark', 'total_fidelity', 'cir_duration', 'compiler'])

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

    higher_lower_is_better_loc = (0.6, 1.05)

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

    
    if include_pachinqo:
        ax.set_yscale('log')

    xtick_labels = df['benchmark'].unique().tolist()
    ax.set_ylim(0, max(df['cir_duration']+0.5))
    ax.set_xticklabels(xtick_labels, fontsize=11)
    print(f'Mean ratios: \n \t MultiQ (1 Row): {df[df["compiler"] == "MultiQ (1 Row)"]["cir_duration"].mean()} \n \t MultiQ (2 Row): {df[df["compiler"] == "MultiQ (2 Row)"]["cir_duration"].mean()}, \n\t ZAC: {df[df["compiler"] == "ZAC"]["cir_duration"].mean()}')

    # PachinQo times out on bv_n19, so mark its empty bar.
    if include_pachinqo and 'bv_n19' in xtick_labels:
        # PachinQo is the last hue group when included.
        pachinqo_bars = ax.containers[-1]
        bar = pachinqo_bars[xtick_labels.index('bv_n19')]
        trans = matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes)
        ax.text(bar.get_x() + bar.get_width() / 2, 0, 'x',
                transform=trans, ha='center', va='bottom', rotation=90, fontsize=12, color='black', fontweight='bold')

    

        

def generate_e2e_means_table(
    set_sizes=(4, 6, 8, 10, 12, 14),
    multiq_results_file="results/multiq/e2e_results.csv",
    zac_results_file="results/zac/e2e_results.csv",
    pachinqo_results_file="results/pachinqo/e2e_results.csv",
    powermove_results_file="results/powermove/e2e_results.csv",
    qmap_results_file="results/qmap/e2e_results.csv",
    zap_results_file="results/zap/e2e_results.csv",
    output_file="results/plots/e2e_means_table.tex",
):
    # Fidelity and time means per compiler and set size, filtered like the means plots.
    data_multiq = pd.read_csv(multiq_results_file)

    # (results file, fidelity column, time column) per baseline.
    baseline_specs = {
        "ZAC": (zac_results_file, "total_fidelity", "cir_duration"),
        "PowerMove": (powermove_results_file, "total_fidelity", "cir_duration"),
        "QMAP": (qmap_results_file, "total_fidelity", "cir_duration"),
        "ZAP": (zap_results_file, "total_fidelity", "cir_duration"),
        "PachinQo": (pachinqo_results_file, "total_fidelity", "execution_time"),
    }
    baseline_data = {name: pd.read_csv(path) for name, (path, _, _) in baseline_specs.items()}

    compilers = ["ZAC", "MultiQ (1 Row)", "MultiQ (2 Row)", "PowerMove", "QMAP", "ZAP", "PachinQo"]
    fidelity = {c: [] for c in compilers}
    time_ms = {c: [] for c in compilers}

    for size in set_sizes:
        benchmarks = data_multiq[data_multiq["set_size"] == size]["benchmark"].unique()
        m1 = data_multiq[(data_multiq["set_size"] == size) & (data_multiq["n_rows"] == 1)]
        m2 = data_multiq[(data_multiq["set_size"] == size) & (data_multiq["n_rows"] == 2)]

        fidelity["MultiQ (1 Row)"].append(m1["cir_fidelity"].mean() * 100)
        fidelity["MultiQ (2 Row)"].append(m2["cir_fidelity"].mean() * 100)
        # Durations are recorded in microseconds.
        time_ms["MultiQ (1 Row)"].append(m1["cir_duration"].mean() / 1000)
        time_ms["MultiQ (2 Row)"].append(m2["cir_duration"].mean() / 1000)

        for name, (_, fid_col, time_col) in baseline_specs.items():
            subset = baseline_data[name][baseline_data[name]["benchmark"].isin(benchmarks)]
            fidelity[name].append(subset[fid_col].mean() * 100)
            time_ms[name].append(subset[time_col].mean() / 1000)

    # Only the first and last set sizes are highlighted.
    highlight_cols = {0, len(set_sizes) - 1}
    main_compilers = ["ZAC", "MultiQ (1 Row)", "MultiQ (2 Row)", "PowerMove", "QMAP", "ZAP"]

    def _cell(value, color=None):
        text = f"{value:.2f}"
        return f"\\cellcolor{{{color}}} {text}" if color else text

    def _row_cells(values_by_compiler, compiler, higher_is_better):
        cells = []
        for col in range(len(set_sizes)):
            color = None
            if col in highlight_cols:
                if compiler == "PachinQo":
                    color = "red!50"
                else:
                    col_values = {c: values_by_compiler[c][col] for c in main_compilers}
                    best = max(col_values, key=col_values.get) if higher_is_better else min(col_values, key=col_values.get)
                    worst = min(col_values, key=col_values.get) if higher_is_better else max(col_values, key=col_values.get)
                    if compiler == best:
                        color = "green!25"
                    elif compiler == worst:
                        color = "red!25"
            cells.append(_cell(values_by_compiler[compiler][col], color))
        return " & ".join(cells)

    display_names = {
        "ZAC": "ZAC",
        "MultiQ (1 Row)": "MultiQ~(1~Row)",
        "MultiQ (2 Row)": "MultiQ~(2~Row)",
        "PowerMove": "PowerMove",
        "QMAP": "QMAP",
        "ZAP": "ZAP",
        "PachinQo": "PachinQo",
    }

    def _compiler_row(values_by_compiler, compiler, higher_is_better, last_in_block):
        cells = _row_cells(values_by_compiler, compiler, higher_is_better)
        line = f"    & \\textbf{{{display_names[compiler]}}} & {cells}\\\\"
        if not last_in_block:
            line += " \\cmidrule(lr){2-8}"
        return line

    n_rows = len(compilers)
    fidelity_rows = "\n".join(
        _compiler_row(fidelity, c, higher_is_better=True, last_in_block=(c == compilers[-1]))
        for c in compilers
    )
    time_rows = "\n".join(
        _compiler_row(time_ms, c, higher_is_better=False, last_in_block=(c == compilers[-1]))
        for c in compilers
    )

    header_cols = " & ".join(f"\\textbf{{{size}}}" for size in set_sizes)

    latex = f"""\\begin{{table}}[t]
    \\small
    \\caption{{\\textbf{{RQ \\#1:}} Fidelity and circuit execution time means for different multi-programming sets of circuits.}}
    \\begin{{tabular}}{{p{{0.03\\linewidth}}|p{{0.23\\linewidth}}|p{{0.065\\linewidth}}|p{{0.065\\linewidth}}|p{{0.065\\linewidth}}|p{{0.065\\linewidth}}|p{{0.065\\linewidth}}|p{{0.065\\linewidth}}|}}
    \\toprule
    & \\textbf{{Compiler}} & {header_cols}\\\\
    \\midrule
    \\multirow{{{n_rows}}}{{*}}{{\\rotatebox[origin=c]{{90}}{{\\textbf{{Fidelity (\\%)}}}}}}
{fidelity_rows}
    \\midrule
    \\multirow{{{n_rows}}}{{*}}{{\\rotatebox[origin=c]{{90}}{{\\textbf{{Time (ms)}}}}}}
{time_rows}
    \\hline
    \\bottomrule
    \\end{{tabular}}
    \\vspace{{-1mm}}
    \\label{{tab:means}}
\\end{{table}}
"""

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        f.write(latex)

    print(f"Wrote {output_file}")
    for metric_name, values in [("Fidelity", fidelity), ("Time", time_ms)]:
        for i, size in enumerate(set_sizes):
            line = ", ".join(f"{c}={values[c][i]:.2f}" for c in compilers)
            print(f"  Set {size}: {metric_name} {line}")

    return latex


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
            run_time += total_runtime/1000
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
                run_time += total_runtime/1000
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
                run_time += total_runtime/1000
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
                run_time += total_runtime/1000
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

                if longest_duration != 0:
                    run_time += longest_duration / 1000
                    initialization_time += init_time

            df.loc[len(df)] = ['Execution', run_time, f'MultiQ({row} Row)', f'Set {size}']
            df.loc[len(df)] = ['Initialization', initialization_time, f'MultiQ({row} Row)', f'Set {size}']

    
    ax.grid(True)


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
    set_order = [f'Set {size}' for size in set_size]

    df['compiler'] = pd.Categorical(df['compiler'], categories=compiler_order, ordered=True)
    df['set_size'] = pd.Categorical(df['set_size'], categories=set_order, ordered=True)
    df['run_phase'] = pd.Categorical(df['run_phase'], categories=phase_order, ordered=True)

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

    


# Per-stage hatches so stages stay readable in grayscale.
_OVERHEAD_STAGE_HATCHES = {
    'Planning': '..',
    'Bundling': 'xx',
    'Backend compilation (ZAC)': '//',
    'Placement': '\\\\',
    'Routing': '||',
}


def _annotate_overhead_totals(ax, df, xcol, row_order):
    """Annotate totals, either 1-Row vs 2-Row or as a percentage over the Backend bar."""
    positions = getattr(ax, '_grouped_bar_positions', None)
    if not positions or len(row_order) not in (2, 3):
        return

    totals = df.groupby([xcol, 'row_config'], observed=True)['duration'].sum()
    x_labels = df[xcol].cat.categories if hasattr(df[xcol], 'cat') else df[xcol].unique()

    # Headroom for the two-line value labels.
    ax.set_ylim(0, ax.get_ylim()[1] * 1.22)
    max_label_pad = ax.get_ylim()[1] * 0.06

    if len(row_order) == 3:
        _annotate_overhead_vs_backend(ax, totals, positions, x_labels, row_order, max_label_pad)
    else:
        _annotate_overhead_pairwise(ax, totals, positions, x_labels, row_order)


def _annotate_overhead_pairwise(ax, totals, positions, x_labels, row_order):
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
    """Label each MultiQ bar with its total and its percentage over the Backend bar."""
    backend, r1, r2 = row_order

    for label in x_labels:
        if any((label, r) not in totals.index for r in row_order):
            continue
        xb = positions.get(backend, {}).get(label)
        tb = totals.get((label, backend))
        if xb is None or tb is None or tb <= 0:
            continue

        fontsize = 9

        # Backend is the reference bar, so it gets no percentage.
        ax.text(xb, tb, f'{tb:.0f}', ha='center', va='bottom',
                fontsize=fontsize, color='black', zorder=6)

        # Stack each label above the previous one so close bars do not overlap.
        prev_label_top = tb + max_label_pad

        for r in (r1, r2):
            x, t = positions.get(r, {}).get(label), totals.get((label, r))
            if x is None or t is None or t <= tb:
                continue

            pct = (t - tb) / tb * 100

            text = f'{t:.0f}\n+{pct:.0f}%'

            text_y = max(t, prev_label_top)
            ax.text(x, text_y, text, ha='center', va='bottom',
                    fontsize=fontsize, color='firebrick', fontweight='bold', zorder=6,
                    multialignment='center', linespacing=1.3)
            prev_label_top = text_y + max_label_pad * 1.9


def _plot_multiq_overhead_breakdown(df, ax, title, xcol, xlabel, include_backend_bar=False):
    """Stacked overhead plot; df has columns [xcol, 'row_config', 'stage', 'duration']."""
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

        # Backend-only reference bar, averaged over both row configs.
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

        # Backend-only reference bar, averaged over both row configs.
        if backend_times:
            df.loc[len(df)] = [label, 'Backend', 'Backend compilation (ZAC)', sum(backend_times) / len(backend_times)]

    df['group'] = pd.Categorical(df['group'], categories=[f'~{c}q' for c in qpu_capacities], ordered=True)

    return _plot_multiq_overhead_breakdown(df, ax, title, xcol='group', xlabel='QPU capacity (6x30q circuits, fixed)',
                                            include_backend_bar=True)


def plot_e2e_rows_sweep_fidelity(ax, title, row_values,
                                  results_file_template="results/multiq/rows_sweep_{rows}rows.csv"):
    """MultiQ fidelity per benchmark, grouped by storage-zone row count."""
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