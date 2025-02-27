# SWITCH-electricity-gas
This Repo will serve as the work table for electricity and gas intergration project. The integrated gas-electricity modules are located under extra_modules folder. 
# Introduction and Installations

## Install miniconda
Download from https://docs.conda.io/projects/miniconda/en/latest/
Install
or whatever powergenome recommends (mainly to get git)
if you already have this or miniconda or anaconda, you can skip ahead

## Install VS Code and Python Extensions

We assume you are using the Visual Studio Code (VS Code) text editor to view and
edit code and data files and run Switch. You can use a different text editor
(and terminal app) if you like, but it should be capable of doing
programming-oriented tasks, like quickly adjusting the indentation of many lines
in a text file. If you prefer, you can also open the .csv data files directly in
your spreadsheet software instead of using VS Code.

Download and install the VS Code text editor from https://code.visualstudio.com/.

If you need more information on installing VS Code, see
https://code.visualstudio.com/docs/setup/setup-overview. (On a Mac you may need
to double-click on the downloaded zip file to uncompress it, then use the Finder
to move the “Visual Studio Code” app from your download folder to your
Applications folder.)

If you'd like a quick introduction to VS Code, see
https://code.visualstudio.com/docs.

Launch Visual Studio Code from the Start menu (Windows) or Applications folder
(Mac). You can choose a color theme and/or work your way through the “Get
Started” steps (it’s a scrollable list), or you can skip them if you don’t want
to do that now.

Follow these steps to install the Python extension for VS Code:

- Click on the Extensions icon on the Activity Bar on the left side of the
  Visual Studio Code window (or choose View > Extensions from the menu). The
  icon looks like four squares.
- This will open the Extensions pane on the left side of the window. Type
  “Python” in the search box, then click on “Install” next to the Python
  extension that lists Microsoft as the developer:
- After installing the Python extension, you will see a “Get started with Python
  development” tab and a “Get started with Jupyter Notebooks” tab. You can close
  these.

Follow these steps to install two more extensions that will be useful. These are
optional, but they make it easier to read and edit data stored in text files,
such as the .csv files used by Switch:

- Type “rainbow csv” in the search box in the Extensions pane, then click on
  “Install” next to the Rainbow CSV extension (this is optional, but makes it
  easier to read and edit data stored in text files, such as the .csv files used
  by Switch):
- Type “excel viewer” in the search box, then click to install the Excel Viewer
  extension (this is also optional, but gives a nice grid view of .csv files):


## Setup modeling software

Open VS Code.

Press shift-control-P (Windows) or shift-cmd-P (Mac). Choose `Python: Select
Interpreter`, then select the Python interpreter you installed in the previous
step (you may be able to find it by searching for "base").

Open a terminal pane: Terminal > New Terminal

Run these commands in the terminal pane.

```
# create a minimal switch-pg environement with enough to bootstrap the rest
conda create -y -c conda-forge -n gas-electricity python=3.10 mamba git ipykernel
conda activate gas-electricity
```

## clone this repository and the dependency submodules. 
cd <wherever you want the SWITCH-electricity-gas code>
git clone https://github.com/Rangrang-Zheng/SWITCH-electricity-gas.git
cd SWITCH-electricity-gas
```

You may skip the tw if you have switch installed already. If not, install switch from submodule here.
## Step 1: install switch from this repository
```
# Create and activate the environment
# the command below will install a local version of switch under the gas-electricity environment
mamba env update -n gas-electricity -f environment.yml
conda activate gas-electricity
```

## Step 2: Run the commands below in the terminal pane.

```
# Direct to the work folder
cd extra_modules

# get switch inputs from the author and store under extra_modules/pj/test/2025/all_in and  create related output folder. If you would like to store them otherwise, make sure to change and specify them in switch solve command below.
# Run switch
switch solve --inputs-dir  ../all_in_2days_2sectors --outputs-dir  ../all_out_2days_0price_S1A --module-list modules_nondr.txt --input-alias fuel_cost.csv=fuel_cost_delta.csv gen_info.csv=info_filtered.csv gen_build_costs.csv=costs_filtered.csv variable_capacity_factors.csv=vcf_filtered.csv


```
