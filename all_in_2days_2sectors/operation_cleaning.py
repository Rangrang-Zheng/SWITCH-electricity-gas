# Remove candidate generators, so that only existing generators are in the
# electricity system hence conduct the operaton optimization.

import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
from tqdm.notebook import trange, tqdm

##########################
# fpath = "/Users/rangrang/Downloads/2020ATB_NREL_Reference_15MW_240.csv"
pre_determined = pd.read_csv("gen_build_predetermined.csv")
costs = pd.read_csv("gen_build_costs.csv")
info = pd.read_csv("gen_info.csv")
vcf = pd.read_csv("variable_capacity_factors.csv")

# info_filtered = info.loc[
#     info["GENERATION_PROJECT"].isin(pre_determined["GENERATION_PROJECT"]),
# ]
# costs_filterd = costs.loc[
#     costs["GENERATION_PROJECT"].isin(pre_determined["GENERATION_PROJECT"]),
# ]
vcf_filtered = vcf.loc[
    vcf["GENERATION_PROJECT"].isin(pre_determined["GENERATION_PROJECT"]),
]

# info_filtered.to_csv(
#     "info_filtered.csv",
#     index=False,
# )
# costs_filterd.to_csv(
#     "costs_filtered.csv",
#     index=False,
# )
vcf_filtered.to_csv(
    "vcf_filtered.csv",
    index=False,
)
