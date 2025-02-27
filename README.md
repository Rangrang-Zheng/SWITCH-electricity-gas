# SWITCH-electricity-gas
This Repo will serve as the work table for electricity and gas intergration project
# test runs
```
# clone this repository and the dependency submodules. 
cd <wherever you want the SWITCH-electricity-gas code>
git clone https://github.com/Rangrang-Zheng/SWITCH-electricity-gas.git
cd SWITCH-electricity-gas
```

You may skip Step 1 if you have switch installed already. If not, install switch from submodule here.
## Step 1: install switch from this repository
```

# the command below will install a local version of switch which added extra components for
# electricity-gas integration
pip install -editable switch

```

## Step 2: Run the commands below in the terminal pane.

```
# Direct to the work folder
cd extra_modules

# get switch inputs from the author and store under extra_modules/pj/test/2025/all_in and  create related output folder. If you would like to store them otherwise, make sure to change and specify them in switch solve command below.
# Run switch
switch solve --inputs-dir  ../all_in_2days_2sectors --outputs-dir  ../all_out_2days_0price_S1A --module-list modules_nondr.txt --input-alias fuel_cost.csv=fuel_cost_delta.csv gen_info.csv=info_filtered.csv gen_build_costs.csv=costs_filtered.csv variable_capacity_factors.csv=vcf_filtered.csv


```
