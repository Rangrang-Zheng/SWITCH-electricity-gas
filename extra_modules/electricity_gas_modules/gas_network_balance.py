# switch solve --solver cplexamp --verbose --stream-solver
### Remove constraint on production by using RelaxBalanceUp and RelaxBalanceDown at the supply price

import os
from pyomo.environ import *
from switch_model.reporting import write_table

# dependencies = "switch_model.timescales", "switch_model.financials"


def define_components(m):
    # 1 GAS LINES
    """
    Zone_Gas_Injections and Zone_Gas_Withdrawals are lists of
    components that contribute to gas-zone level gas balance equations.
    sum(Zone_Gas_Injections[z,t]) == sum(Zone_Gas_Withdrawals[z,t])
        for all z,t
    Other modules may append to either list, as long as the components they
    add are indexed by [zone, DATES] and have units of MMBtu. Other modules
    often include Expressions to summarize decision variables on a zonal basis.
    """
    m.GAS_LINES_DATES = Set(dimen=3, initialize=lambda m: m.DIRECTIONAL_GL * m.DATES)
    m.DispatchGl = Var(m.GAS_LINES_DATES, within=NonNegativeReals)
    ## Constraints: Flow on each gas line-direction must be less than installed capacity on that corridor as of that DATES
    m.Maximum_DispatchGl = Constraint(
        m.GAS_LINES_DATES,
        rule=lambda m, zone_from, zone_to, gd: (
            m.DispatchGl[zone_from, zone_to, gd]
            <= m.DirectionalGlCapacityNameplate[zone_from, zone_to, m.dates_period[gd]]
        ),
    )
    m.GlGasSent = Expression(
        m.GAS_LINES_DATES,
        rule=lambda m, zone_from, zone_to, gd: (m.DispatchGl[zone_from, zone_to, gd]),
    )
    ### Gas line fuel cost = 3.04% of total consumption (US average, 2015-2019, EIA data). Temporarily use the same number for all states.
    # ==>  m.gl_efficiency: default = 1 - 0.03 = 0.97 --> GlGasReceived = 0.97*GlGasSent
    # Gas line fuel is accounted in gas line fuel expense and the gas_fuel_demand_ref_quantity. Here set gl_efficiency = 1
    m.gl_efficiency = Param(m.GAS_LINES, within=PercentFraction, default=1)
    m.GlGasReceived = Expression(
        m.GAS_LINES_DATES,
        rule=lambda m, zone_from, zone_to, gd: (
            m.DispatchGl[zone_from, zone_to, gd]
            * m.gl_efficiency[m.gas_d_line[zone_from, zone_to]]
        ),
    )

    def GLGasNet_calculation(m, z, gd):
        return sum(
            m.GlGasReceived[zone_from, z, gd]
            for zone_from in m.GL_CONNECTIONS_TO_ZONE[z]
        ) - sum(m.GlGasSent[z, zone_to, gd] for zone_to in m.GL_CONNECTIONS_TO_ZONE[z])

    m.GLGasNet = Expression(m.GAS_ZONES, m.GASDATES, rule=GLGasNet_calculation)
    # Register net transmission as contributing to zonal energy balance
    m.Zone_Gas_Injections.append("GLGasNet")

    # 2 GAS STORAGE
    m.GZ_STORAGE_TYPE_DATES = Set(
        dimen=3,
        ordered=True,
        initialize=lambda m: m.GAS_ZONES * m.GAS_STORAGE_TYPES * m.DATES,
    )
    ### the amount of gas added to storage in each gas zone during each DATES
    m.GasStorageQuantity = Var(m.GZ_STORAGE_TYPE_DATES, within=NonNegativeReals)
    m.GasStorageInjectionQuantity = Var(
        m.GZ_STORAGE_TYPE_DATES, within=NonNegativeReals
    )
    ### the amount of gas removed from storage in each gas zone during each DATES,
    m.GasStorageWithdrawalQuantity = Var(
        m.GZ_STORAGE_TYPE_DATES, within=NonNegativeReals
    )
    m.GasStorageNetWithdrawal = Expression(
        m.GZ_STORAGE_TYPE_DATES,
        rule=lambda m, z, ty, gd: m.GasStorageWithdrawalQuantity[z, ty, gd]
        - m.GasStorageInjectionQuantity[z, ty, gd],
    )
    ### the quantity of gas in storage in each (gas zone - DATES)
    m.GasStorageNetWithdrawalSum = Expression(
        m.GAS_ZONES_DATES,
        rule=lambda m, z, gd: sum(
            m.GasStorageNetWithdrawal[z, ty, gd] for ty in m.GAS_STORAGE_TYPES
        ),
    )

    ### Register net injections with zonal gas balance
    m.Zone_Gas_Injections.append("GasStorageNetWithdrawalSum")
    ### the quantity of gas in storage in each gas zone at the end of each DATES
    # use # hours of capacity when specified

    ## Constraints - Storage
    ### quantity of gas in storage in each gas zone at the end of each DATES
    ### must equal the level at the end of the prior DATES (wrapping from start of year to end)
    ### Some documents: storage fuel cost = 4% gross of injection and withdrawal gas.
    ### (m.GasStorageInjectionQuantity[z, ts] + m.GasStorageWithdrawalQuantity[z, ts]) * (1 - m.gas_store_to_release_ratio[z])
    ### But that seems to be too much
    ### Check with: storage fuel cost = 4% injection gas

    ### track state of storage: previous quantity + injections - withdrawals - gas fuel loss
    def Track_State_Of_Storage_rule(m, z, ty, gd):
        return m.GasStorageQuantity[z, ty, gd] == m.GasStorageQuantity[
            z, ty, m.ts_previous[gd]
        ] + (
            m.GasStorageInjectionQuantity[z, ty, gd] * m.gas_storage_efficiency[z, ty]
            - m.GasStorageWithdrawalQuantity[z, ty, gd]
        ) - (
            (m.GasStorageInjectionQuantity[z, ty, gd])
            * (1 - m.gas_store_to_release_ratio[z, ty])
        )  # equal to zero for now

    m.Track_State_Of_Storage = Constraint(
        m.GZ_STORAGE_TYPE_DATES, rule=Track_State_Of_Storage_rule
    )
    ### quantity of gas in storage in each gas zone must never be below zero or
    ### above the amount of non-retired storage capacity existing during that DATES

    def State_Of_Storage_Upper_Limit_rule(m, z, ty, gd):
        return (
            m.GasStorageQuantity[z, ty, gd]
            <= m.GasStorageCapacity[z, ty, m.dates_period[gd]]
        )

    m.State_Of_Storage_Upper_Limit = Constraint(
        m.GZ_STORAGE_TYPE_DATES, rule=State_Of_Storage_Upper_Limit_rule
    )
    ### storages can only complete the specified number of cycles per year, averaged over each period
    m.Storage_Cycle_Limit = Constraint(
        m.GZ_STORAGE_TYPE_PERIODS,
        rule=lambda m, z, ty, p:
        # solvers sometimes perform badly with infinite constraint
        (
            Constraint.Skip
            if m.gas_storage_max_cycles_per_year[ty] == float("inf")
            else (
                sum(
                    m.GasStorageWithdrawalQuantity[z, ty, gd] * m.gd_scale_to_year[gd]
                    for gd in m.DATES_IN_PERIOD[p]
                )
                <= m.GasStorageCapacity[z, ty, p]
                * m.gas_storage_max_cycles_per_year[ty]
            )
        ),
    )

    # 4 GAS IMPORT - EXPORT
    m.gas_import_ref_quantity = Param(
        m.GAS_ZONES_DATES, within=NonNegativeReals, default=0
    )
    m.gas_export_ref_quantity = Param(
        m.GAS_ZONES_DATES, within=NonNegativeReals, default=0
    )
    m.Zone_Gas_Withdrawals.append("gas_export_ref_quantity")
    m.Zone_Gas_Injections.append("gas_import_ref_quantity")
    # 4 GAS DEMAND
    ## use demand price to compute cost of fuel loss
    m.gas_ref_price = Param(
        m.GAS_ZONES_DATES,
        within=NonNegativeReals,
        default=6.96,  # Max city gate price among contiguous US states in 2019: 7.22*1000/(NG_btu_per_cf); or use Residential price at national US in 2019 (10.51*1000/(NG_btu_per_cf) = 10.1). [or 5.17 = weighted average of gas price in US in 2019]
    )
    m.gas_demand_ref_quantity = Param(
        m.GAS_ZONES_DATES,
        within=NonNegativeReals,
        default=0.001,  # avoid 'float division by zero' error in the 'gas_iterative_demand_response.py'
    )
    m.Zone_Gas_Withdrawals.append("gas_demand_ref_quantity")
    # Total demand in each period
    m.zone_total_gas_demand_in_period_mmbtu = Param(
        m.GAS_ZONES,
        m.PERIODS,
        within=NonNegativeReals,
        initialize=lambda m, z, p: (
            sum(
                m.gas_demand_ref_quantity[z, gd] * m.gd_scale_to_period[gd]
                for gd in m.DATES_IN_PERIOD[p]
            )
        ),
    )

    # #5 OPERATIONAL COST
    # # 5.1 GAS PRODUCTION COST
    ## The amount of gas produced in each gas zone during each period depends on number of wells available and production_year.
    ### in gas_well_build.py
    m.Zone_Gas_Injections.append("GasSupplyQuantity")

    # Summarize gas production costs in each timepoint for the objective function
    m.gas_well_operating_cost_perMMbtud = Param(
        m.GAS_ZONES_DATES,
        within=NonNegativeReals,
        default=0.1,  # $0.8/MMcfd ~ $0.0008/MMbtud in 2013 for operation cost only, not yet count labor cost etc. https://rbnenergy.com/shale-production-economics-part-4-variable-cost-and-net-present-value
    )
    m.gas_well_operating_cost = Param(
        m.GAS_ZONES_DATES,
        within=NonNegativeReals,
        initialize=lambda m, z, gd: (
            # cost per DATES equals cost per day / number of DATES per day
            m.gas_well_operating_cost_perMMbtud[z, gd]
            # / (24 / m.ts_duration_hrs[gd])  # m.ts_duration_hrs[tp]= 24
        ),
    )
    m.GasProdCost = Expression(
        m.PERIODS,
        rule=lambda m, p: sum(
            # The m.tp_ts and m.tp_duration_hrs parameters are defined in switch_model.timescales:
            # m.tp_ts[tp] identifies the DATES that contains timepoint tp)
            # total production cost per timpoint equals (gas supply quantity * cost per DATES /  number of timepoints in that DATES)
            m.GasSupplyQuantity[z, gd] * m.gas_well_operating_cost[z, gd]
            for (z, gd) in m.GAS_ZONES_DATES
            if m.dates_period[gd] == p
        ),
    )
    m.Cost_Components_Per_Period.append("GasProdCost")

    # 5.2 TRANSMISSION FUEL COST: the volume of gas pipeline uses was also included as m.gl_efficiency
    m.gas_transmission_fuel_cost = Param(
        m.GAS_ZONES_DATES,
        within=NonNegativeReals,
        default=0.03,  # pipeline and distribution uses is 1.5% of total U.S. inter-state movement volume (US average, 2019, EIA data). Temporarily use the same number for all states.
    )

    def DispatchGl_calculation(m, z, gd):
        return sum(
            m.DispatchGl[z, zone_to, gd] for zone_to in m.GL_CONNECTIONS_TO_ZONE[z]
        )

    m.SumDispatchGl = Expression(m.GAS_ZONES, m.DATES, rule=DispatchGl_calculation)
    m.TransmissionCost = Expression(
        m.PERIODS,
        rule=lambda m, p: sum(
            m.gas_transmission_fuel_cost[z, gd]
            * m.SumDispatchGl[z, gd]
            * m.gas_ref_price[z, gd]
            for (z, gd) in m.GAS_ZONES_DATES
            if m.dates_period[gd] == p
        ),
    )
    m.Cost_Components_Per_Period.append("TransmissionCost")

    # 5.3 STORAGE FUEL COST:
    m.gas_storage_fuel_cost = Param(
        m.GAS_STORAGE_TYPES,
        within=NonNegativeReals,
        default=0.02,  # 4% of gross storage injections and withdrawals
    )
    m.StorageFuelCostTS = Expression(
        m.GAS_ZONES_DATES,
        rule=lambda m, z, gd: sum(
            m.gas_storage_fuel_cost[ty]
            * (
                # m.GasStorageQuantity[z, ty, ts]
                m.GasStorageInjectionQuantity[z, ty, gd]
                + m.GasStorageWithdrawalQuantity[z, ty, gd]
            )
            for ty in m.GAS_STORAGE_TYPES
        ),
    )
    m.StorageCost = Expression(
        m.PERIODS,
        rule=lambda m, p: sum(
            m.StorageFuelCostTS[z, gd] * m.gas_ref_price[z, gd]
            for (z, gd) in m.GAS_ZONES_DATES
            if m.dates_period[gd] == p
        ),
    )
    m.Cost_Components_Per_Period.append("StorageCost")

    # LNG processing cost
    # Liquefaction cost in term of dollars
    m.LNGLiquefactionCost = Expression(
        m.PERIODS,
        rule=lambda m, p: sum(
            m.LNGLiquefactionLoss[z, gd] * m.gas_ref_price[z, gd]
            for (z, gd) in m.GAS_ZONES_DATES
            if m.dates_period[gd] == p
        ),
    )
    m.Cost_Components_Per_Period.append("LNGLiquefactionCost")
    ## Regasification (i.e.Vaporization) cost in term of dollars
    m.LNGRegasificationCost = Expression(
        m.PERIODS,
        rule=lambda m, p: sum(
            m.LNGRegasificationLoss[z, gd] * m.gas_ref_price[z, gd]
            for (z, gd) in m.GAS_ZONES_DATES
            if m.dates_period[gd] == p
        ),
    )
    m.Cost_Components_Per_Period.append("LNGRegasificationCost")
