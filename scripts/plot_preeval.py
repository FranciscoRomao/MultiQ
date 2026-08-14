import pdb
import yaml
import numpy as np
import pandas as pd
import warnings
from scripts.plotting import bar_plot
from scripts.plotting import utils, defaults
import scripts.eval_functions as ppfunctions
from matplotlib import gridspec, figure
import logging

# Set up logging
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#
#warnings.simplefilter(action='ignore', category=UserWarning)
#warnings.simplefilter(action='ignore', category=RuntimeWarning)
#warnings.simplefilter(action='ignore', category=FutureWarning)
#warnings.simplefilter(action='ignore', level='INFO')

circuit_sizes = [25, 50, 100, 150, 200, 250]
benchmarks = ["ghz", "wstate", "dj"]

#fig, axes = utils.gen_subplots(3,2, figsize=(18, 6))
fig = figure.Figure(figsize=(18,6))
#gs = gridspec.GridSpec(5,1, figure=fig, height_ratios=[1, 1, -0.3, 1, 1])
gs = gridspec.GridSpec(2,3)

ax0 = fig.add_subplot(gs[0:2,0]) #Layout plot
ax1 = fig.add_subplot(gs[0,1]) 
ax2 = fig.add_subplot(gs[1,1])
#ax3 = fig.add_subplot(gs[0:2,2])
#ax4 = fig.add_subplot(gs[1,1])

#ppfunctions.plot_fidelity_shuttling_times_vs_layout_width_zac(ax=ax0, title='(a1) Shuttling time vs Utilization (ZAC)')

#handles = ppfunctions.plot_fidelity_shuttling_times_vs_layout_width_zac(ax=ax0, title='(a) Relative fidelity vs Circuit size')

#fig.legend(bbox_to_anchor=(0.01, 0.01), fontsize=12, frameon=True, labels=['Ratio 1:4', 'Ratio 1:1', 'Ratio 4:1'], title='Layout ratio (width:height)')

#ppfunctions.plot_shuttling_times_vs_utilization_zac(ax=ax1, title='(a1) Shuttling time vs Utilization (ZAC)')

#ppfunctions.plot_shuttling_times_vs_utilization_zac(ax=ax1, title='(b1) Shuttling time vs Utilization')

#ppfunctions.plot_shuttling_times_vs_utilization_pachinqo(ax=ax2, title='(a2) Shuttling time vs Utilization (PachinQo)')
##ppfunctions.plot_shuttling_times_vs_utilization_pachinqo(ax=ax2, title='(b2) Shuttling time vs Utilization')

ppfunctions.plot_fidelity_vs_utilization_zac(ax=ax0)

#ppfunctions.plot_fidelity_vs_utilization_pachinqo(ax=ax2)

#legend_handles_scatter, legend_labels_scatter = ppfunctions.plot_compilation_time_vs_fidelity_scatter_plot(ax=ax3, title='(c) Framework runtime vs Fidelity')
#ppfunctions.plot_compilation_time_vs_fidelity(ax=axes[5])
#fig.legend(loc='lower center', bbox_to_anchor=(0.527, -0.009), ncol=3, fontsize=12, frameon=True, labels=['Single', 'Grouped', 'Grouped Independent'])
#use legend_handles_scatter and legend_labels_scatter to create the legend

fig.legend(handles=legend_handles_scatter, labels=legend_labels_scatter, loc='lower center', bbox_to_anchor=(0.852, -0.01), ncol=2, fontsize=12, frameon=True)

fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0.01), ncol=3, fontsize=12, frameon=True, labels=['Single', 'Grouped', 'Grouped Independent'])

#pos = ax2.get_position()
#ax2.set_position([pos.x0, pos.y0 + 0.05, pos.width, pos.height])
fig.text(0.335, 0.23, "PachinQo", fontweight='bold', rotation=90, fontsize=18)
fig.text(0.335, 0.74, "ZAC", fontweight='bold', rotation=90, fontsize=18)

fig.tight_layout(rect=(0.005,0.07,1,1), h_pad=0.005)
#fig.tight_layout()
##fig.tight_layout(w_pad=-1, rect=[0.011,0.05,0.95,1])

fig.savefig('results/preeval.pdf', format='pdf')
