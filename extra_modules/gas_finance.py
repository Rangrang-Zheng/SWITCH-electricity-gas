from __future__ import print_function
from __future__ import division
from pyomo.environ import *
import os
import pandas as pd

dependencies = "switch_model.timescales"


def define_dynamic_lists(mod):
    """
    There are two lists of costs components that form the cost-minimization
    objective function. Other modules may add elements to these lists.

    Cost_Components_Per_TP is a list of components that contribute to overall
    system costs in each timepoint. Each component in this list needs to be
    indexed by timepoint and specified in non-discounted real dollars per hour
    (not $/timepoint). The objective function will apply weights and
    discounting to these terms. If this indexing is not convenient for native
    model components, I advise writing an Expression object indexed by [t]
    that contains logic to access or summarize native model components.

    Cost_Components_Per_Period is a list of components that contribute to
    overall system costs on an annual basis. Each component in this list
    needs to be indexed by period and specified in non-discounted real
    dollars over a typical year in the period. The objective function
    will apply discounting to these terms. If this indexing is not
    convenient for native model components, I advise writing an
    Expression object indexed by [p] that contains logic to access or
    summarize native model components.

    """
    mod.Gas_Cost_Components_Per_TP = []
    mod.Gas_Cost_Components_Per_Period = []

def define_dynamic_components(mod):
    """

    Adds components to a Pyomo abstract model object to summarize net present
    value of all system costs. Other modules will register cost components into
    dynamic lists that are used here to calculate total system costs. This
    function is called after define_components() so that other modules have a
    chance to add entries to the dynamic lists.

    Unless otherwise stated, all terms describing power are in units of MW and
    all terms describing energy are in units of MWh. Future costs (both hourly
    and annual) are in real dollars relative to the base_year and are converted
    to net present value in the base year within this module.

    SystemCostPerPeriod[p in PERIODS] is an expression that sums total system
    costs in each period on a discounted basis, based on the two lists
    Cost_Components_Per_TP and Cost_Components_Per_Period. Components in the
    first list are indexed by timepoint and components in the second are indexed
    by period. Components in the _Per_TP list should have costs given in $/hour
    (not $/timepoint) and components in the _Per_Period list should have costs
    given in $/year (not $/period).

    Minimize_System_Cost is the objective function that seeks to minimize
    TotalSystemCost.

    """

    def gas_calc_tp_costs_in_period(m, t):
        return sum(
            getattr(m, tp_cost)[t] * m.tp_weight_in_year[t]
            for tp_cost in m.Gas_Cost_Components_Per_TP
        )

    # Note: multiply annual costs by a conversion factor if running this
    # model on an intentional subset of annual data whose weights do not
    # add up to a full year: sum(tp_weight_in_year) / hours_per_year
    # This would also require disabling the validate_time_weights check.
    def gas_calc_annual_costs_in_period(m, p):
        return sum(
            getattr(m, annual_cost)[p] for annual_cost in m.Gas_Cost_Components_Per_Period
        )

    def gas_calc_sys_costs_per_period(m, p):
        return (
            # All annual payments in the period
            (
                gas_calc_annual_costs_in_period(m, p)
                + sum(gas_calc_tp_costs_in_period(m, t) for t in m.TPS_IN_PERIOD[p])
            )
            # Conversion from annual costs to base year
            * m.bring_annual_costs_to_base_year[p]
        )

    mod.GasSystemCostPerPeriod = Expression(mod.PERIODS, rule=gas_calc_sys_costs_per_period)
    # starting with Pyomo 4.2, it is impossible to call Objective.reconstruct()
    # or calculate terms like Objective / <some other model component>,
    # so it's best to define a separate expression and use that for these purposes.
    mod.GasSystemCost = Expression(
        rule=lambda m: sum(m.GasSystemCostPerPeriod[p] for p in m.PERIODS)
    )
