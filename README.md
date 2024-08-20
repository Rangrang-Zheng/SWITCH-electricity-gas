# SWITCH-electricity-gas
This Repo will serve as the work table for electricity and gas intergration project
# test runs
## Step 1: install switch from local repository
```
# clone this repository and the dependency submodules. 
cd <wherever you want the SWITCH-electricity-gas code>
git clone https://github.com/Rangrang-Zheng/SWITCH-electricity-gas.git
cd SWITCH-electricity-gas

# the command below will install a local version of switch which added extra components for
# electricity-gas integration
pip install -editable switch

```

## Step 2: Run the commands below in the terminal pane.

```
# Direct to the work folder
cd extra_modules

# Run switch
switch solve --inputs-dir ../SWITCH-electricity-gas/pj/test/2025/all_in --outputs-dir ../SWITCH-electricity-gas/pj/test/2025/all_out 

```
