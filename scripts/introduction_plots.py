import pdb
import yaml
import numpy as np
import pandas as pd
import warnings
from plotting import bar_plot
from plotting import utils, defaults
import eval_functions as ppfunctions
from matplotlib import gridspec, figure

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

circuit_sizes = [25, 50, 100, 150, 200, 250]
benchmarks = ["ghz", "wstate", "dj"]

#fig, [ax0, ax1, ax2] = utils.gen_subplots(1,3, figsize=(6.5, 8.6))

fig, [ax0] = utils.gen_subplots(1,1, figsize=(6.5, 3.5))

ppfunctions.plot_fidelity_vs_circuit_size_zac_pachinqo_atomique(ax0, title='(a) Fidelity vs Circuit size')

ppfunctions.plot_initialization_time_vs_qpu_size(ax0, title='(b) Initialization Time vs QPU size')

ppfunctions.plot_execution_time_vs_circuit_size_zac_pachinqo_atomique(ax0, title='(c) Execution time vs Circuit size')

#ax2.set_position([ax2_pos.x0, ax2_pos.y0+0.2, ax2_pos.width, ax2_pos.height])
#fig.subplots_adjust(left=0.1, bottom=0.1, right=0.95, top=0.90, hspace=1.0, wspace=0.5)
fig.tight_layout()
#fig.tight_layout(rect=[0.005,0,1,1])
#fig.tight_layout(rect=(0,0,1,0.95), h_pad=-0.0008)
#fig.tight_layout(w_pad=-1, rect=[0.011,0.05,0.95,1])

#fig.suptitle('Introduction Plots', fontsize=16)

fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0.935), ncol=4, fontsize=12, frameon=True, labels=['ZAC', 'PachinQo', 'Atomique', 'Average'])

fig.savefig('results/introduction_plots31.png', format='png', dpi=300, bbox_inches='tight')
