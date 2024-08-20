# switch solve --solver cplexamp --verbose --stream-solver
### Remove constraint on production by using RelaxBalanceUp and RelaxBalanceDown at the supply price

import os
from pyomo.environ import *
from switch_model.reporting import write_table

# dependencies = "switch_modules.timescales", "switch_model.financials"


def define_components(m):
    # Relax balance to get balance constraint feasibility
    m.RelaxBalanceUp = Var(
        m.GAS_ZONES_DATES, within=NonNegativeReals
    )  # Additional supply
    m.RelaxBalanceDown = Var(m.GAS_ZONES_DATES, within=NonNegativeReals)

    m.Zone_Gas_Injections.append("RelaxBalanceUp")
    m.Zone_Gas_Withdrawals.append("RelaxBalanceDown")

    m.RelaxCost = Expression(
        m.PERIODS,
        rule=lambda m, p: sum(
            # set very high price for Relax balance so it will force to optimize by build storage/pipeline OR
            # Set high price (ex. as much as $15/MMBtu) so the demand (that exceed supply) will be switched to other source of energy
            1e6 * (m.RelaxBalanceUp[z, gd])
            for (z, gd) in m.GAS_ZONES_DATES
            if m.dates_period[gd] == p
        ),
    )
    m.DisposalCost = Expression(
        m.PERIODS,
        rule=lambda m, p: sum(
            # set very high price for Relax balance so it will force to optimize by build storage/pipeline OR
            # Set high price (ex. as much as $15/MMBtu) so the demand (that exceed supply) will be switched to other source of energy
            1 * (m.RelaxBalanceDown[z, gd])
            for (z, gd) in m.GAS_ZONES_DATES
            if m.dates_period[gd] == p
        ),
    )
    m.Cost_Components_Per_Period.append("RelaxCost")
    m.Cost_Components_Per_Period.append("DisposalCost")


def define_dynamic_components(m):
    # BALANCE CONSTRAINT
    m.Zone_Gas_Balance = Constraint(
        m.GAS_ZONES_DATES,
        rule=lambda m, z, gd: (
            sum(getattr(m, component)[z, gd] for component in m.Zone_Gas_Injections)
            == sum(getattr(m, component)[z, gd] for component in m.Zone_Gas_Withdrawals)
        ),
    )
    if not hasattr(m, "dual"):
        m.dual = Suffix(direction=Suffix.IMPORT)


def post_solve(instance, outdir):
    mod = instance
    # infrastructure built
    write_table(
        instance,
        instance.NEW_GAS_STORAGE_TYPE_BLD_YRS,
        output_file=os.path.join(outdir, "gas_storage_build.csv"),
        headings=(
            "gas_zone",
            "storage_type",
            "period",
            "gas_storage_new_build_cap",
            # "gas_storage_removed_cap",
            "gas_storage_total_cap",
        ),
        values=lambda m, z, ty, p: (
            z,
            ty,
            p,
            m.BuildStorageCap[z, ty, p],
            # m.gas_storage_removed_cap[z, ty, p],
            m.GasStorageCapacity[z, ty, p],
        ),
    )

    write_table(
        instance,
        instance.NEW_GAS_D_LINE_BLD_YRS,
        output_file=os.path.join(outdir, "gas_line_build.csv"),
        headings=(
            "gas_line_gz1",
            "gas_line_gz2",
            "period",
            "GAS_LINES",
            "gas_line_build_directional_cap",
            # "gas_line_removed_directional_cap",
            "gas_line_directional_total_cap",
            "gas_line_build_general_cap",
            # "gas_line_removed_general_cap",
            "gas_line_general_total_cap",
        ),
        values=lambda m, zone_from, zone_to, p: (
            zone_from,
            zone_to,
            p,
            m.gas_d_line[zone_from, zone_to],
            m.BuildDirectionalGl[zone_from, zone_to, p],
            # m.gas_line_removed_cap_directional[zone_from, zone_to, p],
            m.DirectionalGlCapacityNameplate[zone_from, zone_to, p],
            m.BuildGl[m.gas_d_line[zone_from, zone_to], p],
            # m.gas_line_removed_cap_general[m.gas_d_line[zone_from, zone_to], p],
            m.GlCapacityNameplate[m.gas_d_line[zone_from, zone_to], p],
        ),
    )
    write_table(
        instance,
        instance.PERIODS,
        output_file=os.path.join(outdir, "FixedCosts.csv"),
        headings=(
            "period",
            "GasStorageFixedCosts",
            "GeneralGlFixedCosts",
            "DirectionalGlFixedCosts",
            "LNGStorageFixedCosts",
            "LNGLiquefactionFixedCosts",
            "LNGVaporizationFixedCosts",
            "GasWellFixedCosts",
        ),
        values=lambda m, p: (
            p,
            m.GasStorageFixedCosts[p],
            m.GeneralGlFixedCosts[p],
            m.DirectionalGlFixedCosts[p],
            m.LNGStorageFixedCosts[p],
            m.LNGLiquefactionFixedCosts[p],
            m.LNGVaporizationFixedCosts[p],
            m.GasWellFixedCosts[p],
        ),
    )
    # Gas flows and volumes
    # write_table(
    #     instance, instance.GAS_LINES_TIMESERIES,
    #     output_file=os.path.join(outdir, "gas_line_dispatch.csv"), #automatically export within SWITCH
    #     headings=("gas_line_gz1","gas_line_gz2","timeseries",
    #               "gas_line_dispatch_mmbtu"),
    #     values=lambda m, zone_from, zone_to, ts: (
    #         zone_from, zone_to, ts,
    #         m.DispatchGl[zone_from, zone_to, ts]
    #         ))

    write_table(
        instance,
        instance.GZ_STORAGE_TYPE_TIMESERIES,
        output_file=os.path.join(outdir, "gas_storage_type_volume.csv"),
        headings=(
            "gas_zone",
            "storage_type",
            "timeseries",
            "StorageInjections",
            "StorageWithdrawals",
            "StorageNetWithdrawals",
            "StorageQuantity",
        ),
        values=lambda m, z, ty, gd: (
            z,
            ty,
            gd,
            m.GasStorageInjectionQuantity[z, ty, gd],
            m.GasStorageWithdrawalQuantity[z, ty, gd],
            m.GasStorageNetWithdrawal[z, ty, gd],
            m.GasStorageQuantity[z, ty, gd],
        ),
    )

    # Total Gas cost per period
    # write_table(
    #     instance,
    #     instance.PERIODS,
    #     output_file=os.path.join(outdir, "gas_costs.csv"),
    #     headings=(
    #         "PERIOD",
    #         "SystemCostPerPeriod",
    #         "SystemCostPerPeriod_Real",
    #         "GasCostReal_per_MMBtu",
    #         "SystemDemand_MMBtu",
    #     ),
    #     values=lambda m, p: (
    #         p,
    #         m.SystemCostPerPeriod[p],
    #         m.SystemCostPerPeriod[p] / m.bring_annual_costs_to_base_year[p],
    #         m.SystemCostPerPeriod[p]
    #         / m.bring_annual_costs_to_base_year[p]
    #         / sum(m.zone_total_gas_demand_in_period_mmbtu[z, p] for z in m.GAS_ZONES),
    #         sum(m.zone_total_gas_demand_in_period_mmbtu[z, p] for z in m.GAS_ZONES),
    #     ),
    # )

    write_table(
        instance,
        instance.GAS_ZONES_DATES,
        output_file=os.path.join(outdir, "gas_shadow_prices.csv"),
        headings=("gas_zone", "timeseries", "ShadowPrice"),
        values=lambda m, z, gd: (
            z,
            gd,
            (m.dual[m.Zone_Gas_Balance[(z, gd)]] / m.gd_scale_to_period[gd])
            / (1 + m.discount_rate) ** (m.base_financial_year - m.dates_period[gd]),
        ),
    )
    # write_table(
    #     instance, instance.GAS_ZONES_DATES,
    #     output_file=os.path.join(outdir, "gas_supply_consumption.csv"),
    #     headings=("gas_zone", "timeseries",
    #               # "StorageInjections", "StorageWithdrawals",
    #               "StorageNetWithdrawals",
    #               # "StorageQuantity",
    #               "GasLineNetReceipts",
    #               "demand_quantity",
    #               "supply_quantity",
    #               "export_quantity", "import_quantity",
    #               # 'LNGStorageAdditions', 'LNGStorageWithdrawals',
    #               # 'LNGStorageQuantity',
    #               'GasQuantityLiquifiedToLNG', 'GasQuantityFromLNG',
    #               'LNGLiquefactionLoss', 'LNGRegasificationLoss',
    #               # "balancing_up_adjustment",
    #               "RelaxBalanceUp", "RelaxBalanceDown"),
    #     values=lambda m, z, ts: (
    #         z, ts,
    #         # m.GasStorageInjectionQuantity[z,ts], m.GasStorageWithdrawalQuantity[z, ts],
    #         m.GasStorageNetWithdrawalSum[z, ts],
    #         # m.GasStorageQuantity[z, ts],
    #         m.GLGasNet[z, ts],
    #         m.FlexibleDemand[z,ts],
    #         m.gas_supply_ref_quantity[z, ts],
    #         m.gas_export_ref_quantity[z, ts], m.gas_import_ref_quantity[z, ts],
    #         # m.LNGStorageAdditionQuantity[z,ts], m.LNGStorageWithdrawalQuantity[z,ts],
    #         # m.LNGStorageQuantity[z,ts],
    #         m.GasQuantityLiquefiedToLNG[z,ts], m.GasQuantityFromLNG[z,ts],
    #         m.LNGLiquefactionLoss[z,ts], m.LNGRegasificationLoss[z,ts],
    #         # m.gas_balancing_ref_quantity[z,ts],
    #         m.RelaxBalanceUp[z,ts], m.RelaxBalanceDown[z,ts]
    #         ))
    write_table(
        instance,
        instance.NEW_LNG_STORAGE_BLD_YRS,
        output_file=os.path.join(outdir, "LNG_storage_build.csv"),
        headings=(
            "gas_zone",
            "period",
            "BuildLNGStorageCap",
            # "LNG_storage_removed_cap",
            "LNG_storage_total_cap",
        ),
        values=lambda m, z, p: (
            z,
            p,
            m.BuildLNGStorageCap[z, p],
            # m.LNG_storage_removed_cap[z, p],
            m.LNGStorageCapacity[z, p],
        ),
    )
    write_table(
        instance,
        instance.NEW_LNG_LIQUEFACTION_BLD_YRS,
        output_file=os.path.join(outdir, "LNG_liquefaction_build.csv"),
        headings=(
            "gas_zone",
            "period",
            "BuildLNGLiquefactionCap",
            # "LNG_liquefaction_removed_cap",
            "LNGLiqefactionCapacity",
        ),
        values=lambda m, z, p: (
            z,
            p,
            m.BuildLNGLiquefactionCap[z, p],
            # m.LNG_liquefaction_removed_cap[z, p],
            m.LNGLiqefactionCapacity[z, p],
        ),
    )
    write_table(
        instance,
        instance.NEW_LNG_VAPORIZATION_BLD_YRS,
        output_file=os.path.join(outdir, "LNG_vaporization_build.csv"),
        headings=(
            "gas_zone",
            "period",
            "BuildLNGVaporizationCap",
            # "LNG_vaporization_removed_cap",
            "LNGVaporizationCapacity",
        ),
        values=lambda m, z, p: (
            z,
            p,
            m.BuildLNGVaporizationCap[z, p],
            # m.LNG_vaporization_removed_cap[z, p],
            m.LNGVaporizationCapacity[z, p],
        ),
    )
    write_table(
        instance,
        instance.GAS_ZONES_DATES,
        output_file=os.path.join(outdir, "LNG_quantity.csv"),
        headings=(
            "gas_zone",
            "timeseries",
            "LNG_import_ref_quantity",
            "SumLNGReceived",
            "LNGLiquefiedFromNG",
            "LNGStorageAdditionQuantity",
            "SumLNGShipped",
            "LNGRegasifiedToNG",
            "LNGStorageWithdrawalQuantity",
        ),
        values=lambda m, z, gd: (
            z,
            gd,
            m.LNG_import_ref_quantity[z, gd],
            m.SumLNGReceived[z, gd],
            m.LNGLiquefiedFromNG[z, gd],
            m.LNGStorageAdditionQuantity[z, gd],
            m.SumLNGShipped[z, gd],
            m.LNGRegasifiedToNG[z, gd],
            m.LNGStorageWithdrawalQuantity[z, gd],
        ),
    )
    # write_table(
    #     instance, instance.PERIODS,
    #     output_file=os.path.join(outdir, "LNGFixedCosts.csv"),
    #     headings=("period",
    #               "LNGStorageFixedCosts"),
    #     values=lambda m, p: (
    #         p,
    #         m.LNGStorageFixedCosts[p]
    #         ))
    # print("Shadow price example:")
    # print(
    #     (instance.dual[instance.Balance[('WV', 20170322)]]
    #     /
    #     instance.ts_scale_to_period[20170322])
    #     /
    #     (1+instance.discount_rate)**(instance.base_financial_year-instance.ts_period[20170322])
    # )
