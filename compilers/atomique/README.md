# Artifact Evaluation Documentation

Welcome to the repository for the artifact evaluation of our FPQA-C paper. This repository includes the necessary compilers, scripts, and configuration files to generate all the evaluation figures and tables presented in the paper.

## Getting Started

### Set up Environment

Before you begin, follow the steps below to set up your environment.

1. **Install Required Packages**: Assuming you are using Anaconda to manage the Python environment, install all the necessary Python packages listed in the `requirement.txt` file using the following command:

```bash
conda create -n fpqa
conda activate fpqa 
conda install python==3.9
pip install -r requirements.txt
```

2. **Set Up Environment Variable**: Export the Python path to the base directory to ensure the scripts run correctly.
```bash
export PYTHONPATH=.
```

### Repository Structure

The repository is organized into several directories:

- `benchmarks`: Contains the benchmark files for the artifact evaluation.
- `compilers`: Includes our fpqac compiler and other baselines.
- `configs`: Stores configuration and scripts for batch running the compilation tasks.
- `plot`: Contains scripts for plotting figures based on the generated data.
- `results`: The output directory storing all the compiled data.

### Generating Figures and Tables

To generate a specific figure or table, generate the data and plot the figure. For example, to reproduce the main table (Figure 13) presented in our paper, follow the following steps:

1. Run the script to generate data:
```bash
./configs/13_isca_maintable/script.sh
```

2. Once the script completes, generate the figure by running the plotting script:
```bash
python plot/13_maintable/maintable_plot.py
```

This will generate and save the specified figure in the `plot/13_maintable` directory.

To run all experiments automatically, you may use
```bash
./all_script.sh
```
After the script finishes, you can see all the figures in `plot/xx/xx.pdf`.
## Notice
1. In most of the code except for those related to Table 3, we use the term Geyser to refer to FAATriangular and FAA to refer to FAARectangular.

2. To run the Geyser compiler as a baseline for Table 3, you may need a separate Python environment. Notice that Geyser takes hours to finish.
```bash
conda env create -f geyser_environment.yml
conda activate geyser
cd compilers/GEYSER/code
python simulate_algorithm.py
```
The number of pulses is stored at compilers/GEYSER/code/xxx_result.txt.

3. To see the detailed output program of our fpqac compiler, use `configs/dump_full_report` and `plot/dump_full_report` as an example.

4. You may notice some minor discrepancies caused by randomness in qiskit.

5. Please see `configs/example/readme.md` for more details about the configuration files.

## Support

If you encounter any issues or have questions about reproducing the figures and tables, please feel free to contact us for support!