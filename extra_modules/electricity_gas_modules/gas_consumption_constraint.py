from __future__ import division
import os
from pyomo.environ import *
from switch_model.financials import capital_recovery_factor as crf

"""

"""
# dependencies = (
#     "switch_model.timescales",
#     "switch_model.balancing.load_zones",
#     "switch_model.financials",
#     "switch_model.generators.core.build",
#     "switch_model.generators.core.dispatch",
#     "",
# )


def define_components(mod):
    ############
    # Calculate total use of gas in each zone during
    # each timepoint
    # first, identify all generators that can use gas
    mod.state = Param(mod.GENERATION_PROJECTS, within=Any)

    mod.gen_uses_gas = Param(
        mod.GENERATION_PROJECTS,
        within=Boolean,
        initialize=lambda m, g: (m.gen_energy_source[g] == "Naturalgas"),
    )
    mod.GAS_GENS = Set(
        dimen=1,
        initialize=mod.GENERATION_PROJECTS,
        filter=lambda m, g: m.gen_uses_gas[g],
    )

    # next, identify all the gas generators that are active in each zone in each period
    def GAS_GENS_IN_STATE_PERIOD_init(m, s, p):
        try:
            d = m.GAS_GENS_IN_STATE_ZONE_PERIOD_dict
        except AttributeError:
            d = m.GAS_GENS_IN_STATE_ZONE_PERIOD_dict = {
                (s2, p2): [] for s2 in m.GAS_ZONES for p2 in m.PERIODS
            }
            # tabulate all GAS gens active in each zone in each period
            for g in m.GAS_GENS:
                for p2 in m.PERIODS_FOR_GEN[g]:
                    d[m.state[g], p2].append(g)
        return d.pop((s, p))

    mod.GAS_GENS_IN_STATE_PERIOD = Set(
        mod.GAS_ZONES,
        mod.PERIODS,
        initialize=GAS_GENS_IN_STATE_PERIOD_init,
        within=mod.GAS_GENS,
    )

    # calculate fuel consumption by all gas generators in each zone during
    # each timepoint(MMbtu)
    mod.ConsumeGasKgPerHour = Expression(
        mod.GAS_ZONES,
        mod.TIMEPOINTS,
        rule=lambda m, z, tp: (
            sum(
                m.GenFuelUseRate[g, tp, "Naturalgas"]  # H2 MMBtu/hr
                for g in m.GAS_GENS_IN_STATE_PERIOD[z, m.tp_period[tp]]
            )
        ),
    )
    # Calculate the gas used in each GAS ZONE AT EACH timeseries/date.
    mod.GasConsumedByElectricity = Expression(
        mod.GAS_ZONES,
        mod.GASDATES,
        rule=lambda m, z, gd: (
            sum(
                m.ConsumeGasKgPerHour[z, tp]  # H2 MMBtu/hr
                for tp in m.TPS_IN_GASDATES[gd]
            )
        ),
    )
    mod.Zone_Gas_Withdrawals.append("GasConsumedByElectricity")
