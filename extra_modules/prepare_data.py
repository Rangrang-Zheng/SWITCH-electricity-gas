import os, json, sys
from datetime import date
import pandas as pd
import numpy as np

from transmission_scripts.TX_util import tp_to_date

# note: this will work relative to the directory where the script is run, which
# should usually be Switch-USA-PG. But for special cases, you can copy the
# inputs and outputs directories to a different location and run it there, as
# long as they are in the expected structure (26-zone/in/year/case and 26-zone/out/year/case)

################################### FOR 26 ZONE ###################################
root_folder = "/Users/rangrang/Desktop/Switch-USA-PG/RR_study"
scenarios = [
    # "nodecarb_hydrogen_co2p",
    # "nodecarb_hydrogen",
    "decarb_hydrogen",
    # "boosted_decarb_no",
]
lv_agg = pd.DataFrame()
for scenario in scenarios:

    print(f"\nMAKING TABLES for:", {scenario})
    # results folder should be one level up from this script
    # results_folder = os.path.abspath(
    #     os.path.join(os.path.dirname(__file__), "..", "MIP_results_comparison")
    # )
    results_folder = os.path.abspath(
        # os.path.join(root_folder, "cluster_study/results_data/co2_200")
        os.path.join(root_folder, "trans_study_21TW/results_data", scenario)
    )

    year_list = [2050]
    case_list = {
        # "2050_10_c146": "c146",
        # "2050_10_c246": "c246",
        # "2050_10_c346": "c346",
        # "2050_10_c446": "c446",
        # "2050_10_c546": "c546",
        # "2050_10_c1046": "c1046",
        # "2050_10_c2046": "c2046",
        # "2050_10_c4046": "c4046",
        # "2050_10_c8046": "c8046",
        # "no": "no",
        # "withintra": "withintra",
        # "withall": "withall",
        "withall_25": "withall_25",
        # "withall_50": "withall_50",
    }

    # def skip_case(case):
    #     test_in_files = [output_file(case, y, "BuildGen.csv") for y in year_list]
    #     test_out_files = [
    #         comparison_file(case, f)
    #         for f in [
    #             "resource_capacity.csv",
    #             "transmission.csv",
    #             "transmission_expansion.csv",
    #             "dispatch.csv",
    #             "generation.csv",
    #             "emissions.csv",
    #         ]
    #     ]

    #     if not all(os.path.exists(f) for f in test_in_files):
    #         print(f"Skipping unsolved case '{i}'.")
    #         return True

    #     if "--skip-saved" in sys.argv and all(os.path.exists(f) for f in test_out_files):
    #         latest_change = max(os.path.getmtime(f) for f in test_in_files)
    #         earliest_record = min(os.path.getmtime(f) for f in test_out_files)

    #         if latest_change < earliest_record:
    #             print(f"Skipping previously saved case '{i}'.")
    #             return True

    #     print(f"Processing case '{i}'")
    #     return False

    def output_file(scenario, case, file):
        """
        Give path to output file generated for the specified case.
        """
        # This is easy because every model has its own outputs dir
        return os.path.join(
            # root_folder, "RR_study/cluster_study/out/co2_200_10_week", case, file
            root_folder,
            "trans_study_21TW/out",
            scenario,
            case,
            file,
        )

    def input_file(case, file):
        """
        Give path to output file generated for the specified case.
        """
        # This is tricky because the inputs dir may not have the same name as the
        # outputs dir (several models may use the same inputs with different
        # settings for each case) and the inputs file could be an alternative
        # version for this scenario and/or chained from the previous period
        # (for myopic models)
        with open(output_file(scenario, case, "model_config.json"), "r") as f:
            case_settings = json.load(f)

        # lookup correct inputs_dir
        in_dir = case_settings["options"]["inputs_dir"]
        # apply input_alias if specified
        alias_list = case_settings["options"].get("input_aliases", [])
        aliases = dict(x.split("=") for x in alias_list)
        file = aliases.get(file, file)

        return os.path.join(root_folder, in_dir, file)

    # def comparison_file(case, file):
    #     return os.path.join(results_folder, case_list[case], "SWITCH_results_summary", file)
    def comparison_file(case, file):
        return os.path.join(results_folder, case_list[case], file)

    def tech_type(gen_proj):
        """
        Accept a vector of generation projects / resources, and return
        a vector of tech types for them.
        """
        df = pd.DataFrame({"resource_name": gen_proj.unique()})
        df["tech_type"] = "Other"
        patterns = [
            ("batter", "Battery"),
            ("storage", "Battery"),
            ("coal", "Coal"),
            ("solar|pv", "Solar"),
            ("wind", "Wind"),
            ("hydro|water", "Hydro"),
            ("hydrogen", "Hydrogen"),
            ("distribute", "Distributed Solar"),
            # ("geothermal", "Geothermal"),
            ("nuclear", "Nuclear"),
            ("natural", "Natural Gas"),
            ("ccs", "CCS"),
        ]
        for pat, tech_type in patterns:
            df.loc[df["resource_name"].str.contains(pat, case=False), "tech_type"] = (
                tech_type
            )

        # Now use a mapping to assign all of them at once. For very long vectors,
        # this is much faster than running the code above on the original vector.
        all_tech_types = gen_proj.map(df.set_index("resource_name")["tech_type"])
        return all_tech_types

    ################################## make  resource_capacity.csv
    # resource_name,zone,tech_type,model,planning_year,case,unit,start_value,end_value,start_MWh,end_MWh

    print("\ncreating resource_capacity.csv")
    for i in case_list:
        # if skip_case(i):
        #     continue

        build_dfs = [
            pd.DataFrame(
                columns=[
                    "resource_name",
                    "zone",
                    "tech_type",
                    "model",
                    "planning_year",
                    "case",
                    "unit",
                    "start_value",
                    "end_value",
                    "start_MWh",
                    "end_MWh",
                ]
            )
        ]
        for y in year_list:
            # find the capacity built in this model (including existing projects)
            # that is still online for the period, i.e., has
            # build year + max_age_years > model start year

            # lookup start and end years for period(s) in this model
            periods = pd.read_csv(input_file(i, "periods.csv")).rename(
                columns={"INVESTMENT_PERIOD": "planning_year"}
            )

            # get the construction plan (all years up through this model, but some
            # capacity may have retired before the model started)
            build_mw = pd.read_csv(output_file(scenario, i, "BuildGen.csv")).rename(
                columns={
                    "GEN_BLD_YRS_1": "resource_name",
                    "GEN_BLD_YRS_2": "build_year",
                    "BuildGen": "build_mw",
                }
            )
            build_mwh = pd.read_csv(
                output_file(scenario, i, "BuildStorageEnergy.csv")
            ).rename(
                columns={
                    "STORAGE_GEN_BLD_YRS_1": "resource_name",
                    "STORAGE_GEN_BLD_YRS_2": "build_year",
                    "BuildStorageEnergy": "build_mwh",
                }
            )
            build = build_mw.merge(build_mwh, how="outer")

            # cross-reference with the period information for this model
            build = (
                build.assign(__x=1)
                .merge(periods.assign(__x=1), on="__x")
                .drop(columns=["__x"])
            )

            # add suspension/retirement info if available
            # TODO: avoid the retirement calculations by adding --save-expression
            # GenCapacity when solving, then read GenCapacity.csv, or alternatively,
            # pull info from gen_cap.csv instead of working from GenBuild.csv (which
            # includes the obsolete generators).
            susp_file = output_file(scenario, i, "SuspendGen.csv")
            if os.path.exists(susp_file):
                # get endogenous retirements (suspensions)
                suspend_mw = pd.read_csv(susp_file).rename(
                    columns={
                        "GEN_BLD_SUSPEND_YRS_1": "resource_name",
                        "GEN_BLD_SUSPEND_YRS_2": "build_year",
                        "GEN_BLD_SUSPEND_YRS_3": "planning_year",
                        "SuspendGen": "suspend_mw",
                    }
                )
                build = build.merge(
                    suspend_mw, on=["resource_name", "build_year", "planning_year"]
                )
                missing = build[build["suspend_mw"].isna()]
                if not missing.empty:
                    print(
                        f"WARNING: unexpected missing SuspendGen values found in case {i} in year {y}:"
                    )
                    print(missing)
                    build["suspend_mw"] = build["suspend_mw"].fillna(0)
            else:
                # no suspension file
                build["suspend_mw"] = 0

            # get retirement age from gen_info.csv
            gen_info = pd.read_csv(input_file(i, "gen_info.csv")).set_index(
                "GENERATION_PROJECT"
            )
            build["retire_year"] = build["build_year"] + build["resource_name"].map(
                gen_info["gen_max_age"]
            )

            # find amount of capacity online before and after each period
            # (note: with retirement, "before" becomes ill-defined in myopic models,
            # because we don't know how much was suspended in the previous period,
            # so we fix that up later)
            # Assume "start" means capacity available immediately prior to running
            # this model, possibly including capacity that retired just as this
            # model started.
            cap_start = (
                build.query(
                    "(build_year < period_start) & (retire_year > period_start - 1)"
                )
                .groupby(["resource_name", "planning_year"], as_index=False)[
                    ["build_mw", "build_mwh"]
                ]
                .sum()
            ).rename(columns={"build_mw": "start_value", "build_mwh": "start_MWh"})
            # assume anything that made it _past_ the start of this period is still
            # there at the end, since that is what Switch does and it captures the
            # notion of "what's running in this period" (if capacity is online one
            # period and retired by the next period, it is treated as retired in the
            # second period)
            cap_end = (
                build.query("(build_year <= period_end) & (retire_year > period_start)")
                # subtract suspensions/retirements from the capacity that would
                # otherwise be online through this study period (shows as not online
                # at end)
                .assign(build_mw=lambda df: df["build_mw"] - df["suspend_mw"])
                .groupby(["resource_name", "planning_year"], as_index=False)[
                    ["build_mw", "build_mwh"]
                ]
                .sum()
            ).rename(columns={"build_mw": "end_value", "build_mwh": "end_MWh"})

            # need an outer join to get any that didn't exist at the start (new
            # build) or end (retired during study)
            build_sum = cap_start.merge(cap_end, how="outer").fillna(0)
            # add other columns needed for the report
            build_sum["zone"] = build_sum["resource_name"].map(
                gen_info["gen_load_zone"]
            )
            build_sum["tech_type"] = tech_type(build_sum["resource_name"])
            build_sum["model"] = "SWITCH"
            build_sum["planning_year"] = y
            build_sum["case"] = i
            build_sum["unit"] = "MW"

            build_dfs.append(build_sum)
            ##############################
            hydrogen = pd.DataFrame()
            # Add endogeneous hydrogen
            # find out how much hydrogen are built
            hydrogen_original = pd.read_csv(
                output_file(scenario, i, "BuildFuelCellMW.csv")
            )
            hydrogen = hydrogen_original.rename(
                {
                    "BuildFuelCellMW_index_1": "resource_name",
                    "BuildFuelCellMW_index_2": "planning_year",
                    "BuildFuelCellMW": "end_value",
                },
                axis=1,
            )
            hydrogen["zone"] = hydrogen["resource_name"]
            hydrogen["tech_type"] = "Hydrogen"
            hydrogen["model"] = "SWITCH"
            hydrogen["case"] = i
            hydrogen["planning_year"] = y
            hydrogen["unit"] = "MW"
            hydrogen["start_value"] = 0
        # combine and round results (there are some 1e-14's in there)
        resource_capacity_agg = pd.concat(build_dfs).round(6)
        #  combine df df with hydrigen
        resource_capacity_agg = pd.concat([resource_capacity_agg, hydrogen]).round(6)
        #################################
        # TODO: use previous period's end_value as start_value for next period,
        # if available; this is a better estimate than the ones above, because it
        # accounts for retirements/suspensions in the previous period (they are
        # treated as not there at the start, but there at the end if unsuspended)
        # For now, we ignore this because start_value is not used anywhere.

        # fill missing capacity values; these are generally due to old plants that
        # got carried forward to later models. They don't participate in the
        # objective or constraints, so the solver doesn't assign them values
        # resource_capacity_agg = resource_capacity_agg.fillna(
        #     {"start_value": 0, "end_value": 0, "start_MWh": 0, "end_MWh": 0}
        # )

        # drop empty rows
        resource_capacity_agg = resource_capacity_agg.loc[
            (resource_capacity_agg["end_value"] > 0)
            | (resource_capacity_agg["end_MWh"] > 0)
        ]
        resource_capacity_agg.to_csv(
            comparison_file(i, "resource_capacity.csv"),
            index=False,
        )

    ####################################### make  transmission.csv

    print("\ncreating transmission.csv")
    for i in case_list:
        # if skip_case(i):
        #     continue
        tx_agg = pd.DataFrame()
        for y in year_list:
            transmission2030_new = pd.read_csv(
                output_file(scenario, i, "transmission.csv")
            )

            # find the existing transmission capacity
            transmission2030_ex = pd.read_csv(input_file(i, "transmission_lines.csv"))

            transmission2030 = transmission2030_new.merge(
                transmission2030_ex, how="left"
            )

            df = transmission2030.copy()
            df["model"] = "SWITCH"
            df["line_name"] = df["trans_lz1"] + "_to_" + df["trans_lz2"]
            df["planning_year"] = df["PERIOD"]
            df["case"] = i
            df["unit"] = "MW"
            # for foreight scenario:
            # define a function to find the values of "TxCapacityNameplate" from last period
            # and fill it as the "start_value" of next period for same line.

            if y == "foresight":
                df.loc[df["PERIOD"] == 2030, "start_value"] = df["existing_trans_cap"]

                fill_dict2030 = (
                    df.loc[df["PERIOD"] == 2030]
                    .groupby("line_name")["TxCapacityNameplate"]
                    .last()
                    .to_dict()
                )
                df.loc[df["PERIOD"] == 2040, "start_value"] = df["line_name"].map(
                    fill_dict2030
                )

                fill_dict2040 = (
                    df.loc[df["PERIOD"] == 2040]
                    .groupby("line_name")["TxCapacityNameplate"]
                    .last()
                    .to_dict()
                )
                df.loc[df["PERIOD"] == 2050, "start_value"] = df["line_name"].map(
                    fill_dict2040
                )
            else:
                df["start_value"] = df["existing_trans_cap"]

            df["end_value"] = df["TxCapacityNameplate"]
            df = df[
                [
                    "model",
                    "line_name",
                    "planning_year",
                    "case",
                    "unit",
                    "start_value",
                    "end_value",
                ]
            ]
            tx_agg = pd.concat([tx_agg, df])

        tx_agg.to_csv(comparison_file(i, "transmission.csv"), index=False)
        df = tx_agg.copy()
        df["value"] = df["end_value"] - df["start_value"]
        df2 = df[["model", "line_name", "planning_year", "case", "unit", "value"]]
        df2.to_csv(
            comparison_file(i, "transmission_expansion.csv"),
            index=False,
        )

    ################################### make  generation.csv

    print("\ncreating generation.csv")
    for i in case_list:
        # if skip_case(i):
        #     continue
        generation_agg = pd.DataFrame()
        dispatch_agg = pd.DataFrame()
        for y in year_list:
            ts = pd.read_csv(input_file(i, "timeseries.csv"))
            tp = pd.read_csv(input_file(i, "timepoints.csv"))
            df = pd.read_csv(output_file(scenario, i, "dispatch.csv"))
            df["model"] = "SWITCH"
            df["zone"] = df["gen_load_zone"]
            df["resource_name"] = df["generation_project"]
            df["tech_type"] = tech_type(df["resource_name"])
            df["planning_year"] = y
            df["case"] = i
            df["timestep"] = "all"
            df["unit"] = "MWh"

            dp = df.copy()
            dp["value"] = dp["DispatchGen_MW"]
            # do the time conversions once and map back (for speed)
            dp_stamps = dp[["timestamp"]].drop_duplicates()
            dp_stamps = tp_to_date(dp_stamps, "timestamp")
            dp_stamps["days"] = pd.to_numeric(dp_stamps["days"])
            dp_stamps["date"] = dp_stamps.apply(
                lambda dfrow: date.fromisocalendar(
                    dfrow["period"], dfrow["week"], dfrow["days"]
                ),
                axis=1,
            )
            dp_stamps = dp_stamps.rename(columns={"period": "planning_year"})
            dp = dp.merge(dp_stamps, on="timestamp")
            ### dispatched hydrogen
            hydrogen = (
                pd.read_csv(
                    output_file(
                        scenario,
                        i,
                        "DispatchFuelCellMW.csv",
                    )
                )
                .rename(
                    {
                        "DispatchFuelCellMW_index_1": "resource_name",
                        "DispatchFuelCellMW_index_2": "timepoint_id",
                        "DispatchFuelCellMW": "value",
                    },
                    axis=1,
                )
                .merge(tp, on="timepoint_id", how="left")
            )
            hydrogen["model"] = "SWITCH"
            hydrogen["zone"] = hydrogen["resource_name"]
            hydrogen["tech_type"] = "Hydrogen"
            hydrogen["unit"] = "MWh"
            hydrogen["case"] = i
            hydrogen = hydrogen.merge(dp_stamps, on="timestamp")
            hydrogen["planning_year"] = y
            hydrogen_sum = hydrogen.groupby(
                ["resource_name", "planning_year"], as_index=False
            ).agg(
                {
                    "value": "sum",
                    "model": "first",
                    "zone": "first",
                    "resource_name": "first",
                    "tech_type": "first",
                    "case": "first",
                    "unit": "first",
                }
            )
            df["value"] = df["DispatchGen_MW"] * df["tp_weight_in_year_hrs"]
            generation = df.groupby(
                ["resource_name", "planning_year"], as_index=False
            ).agg(
                {
                    "value": "sum",
                    "model": "first",
                    "zone": "first",
                    "resource_name": "first",
                    "tech_type": "first",
                    "case": "first",
                    "unit": "first",
                }
            )
            # dispatch_agg = pd.concat([dispatch_agg, dp])
            generation_agg = pd.concat([generation_agg, generation, hydrogen_sum])

        # dispatch_agg.to_csv(comparison_file(i, "dispatch.csv"), index=False)
        generation_agg.to_csv(comparison_file(i, "generation.csv"), index=False)

    ################################### make  emission.csv

    print("\ncreating emission.csv")
    for i in case_list:
        # if skip_case(i):
        #     continue
        emission_agg = pd.DataFrame()
        for y in year_list:
            emission2030 = pd.read_csv(output_file(scenario, i, "dispatch.csv"))
            df = emission2030.copy()

            df = df.groupby(["gen_load_zone", "period"], as_index=False).agg(
                {
                    "DispatchEmissions_tCO2_per_typical_yr": "sum",
                }
            )
            df["planning_year"] = df["period"]
            df = df.rename(
                {
                    "gen_load_zone": "zone",
                    "DispatchEmissions_tCO2_per_typical_yr": "value",
                },
                axis=1,
            )
            df["model"] = "SWITCH"
            df["case"] = i
            df["unit"] = "kg"
            df["value"] = df["value"] * 1000  # from ton to kg
            df = df[["model", "zone", "planning_year", "case", "unit", "value"]]
            emission_agg = pd.concat([emission_agg, df])

        emission_agg.to_csv(comparison_file(i, "emissions.csv"), index=False)

    ####################################### Make MC tables ###############################
    print("\ncreating unweighted_yealy_MC.csv")

    for i in case_list:
        # if skip_case(i):
        #     continue
        es_agg = pd.DataFrame()
        for y in year_list:
            result = [
                filename
                for filename in os.listdir(
                    os.path.join(root_folder, "trans_study_21TW/out", scenario, i)
                )
                if filename.startswith("energy_sources")
            ]
            if result == []:
                break

            es = pd.read_csv(output_file(scenario, i, result[0]))
            es = es.loc[es["load_zone"] != "loadzone"]
            es["timeseries"] = [
                x[0] + "_" + x[1] for x in es["timepoint_label"].str.split("_")
            ]
            ts = pd.read_csv(
                os.path.join(root_folder, "trans_study_21TW/in", "timeseries.csv")
            )
            es_ts = pd.merge(es, ts, how="left", on="timeseries")
            es_ts = es_ts[
                [
                    "load_zone",
                    "timepoint_label",
                    "period",
                    "zone_demand_mw",
                    "marginal_cost",
                    "ts_scale_to_period",
                    "peak_day",
                    "timeseries",
                ]
            ]
            es_ts["model"] = i
            es_weighted = es_ts.copy()
            es_weighted["demand_sum"] = (
                es_weighted["zone_demand_mw"]
                .groupby(es_weighted["timepoint_label"])
                .transform("sum")
            )
            es_agg = pd.concat([es_agg, es_weighted])

        es_agg.to_csv(comparison_file(i, "unweighted_yealy_MC.csv"), index=False)
    ###################################### Make Levelized cost table ###############################
    print("\ncreating levelized_cost.csv")
    for i in case_list:
        # if skip_case(i):
        #     continue
        for y in year_list:
            if os.path.exists(output_file(scenario, i, "electricity_cost.csv")):
                lv = pd.read_csv(output_file(scenario, i, "electricity_cost.csv"))
                lv["scenario"] = scenario + "/" + i
                lv_agg = pd.concat([lv_agg, lv])
            else:
                continue
lv_agg.to_csv(
    "/Users/rangrang/Desktop/Switch-USA-PG/RR_study/trans_study_21TW/results_data/levelized_cost.csv",
    index=False,
)

# ######################################################################
# # Find out the most expensive 3 consecutive days for each region and boost
# # the demand to 25% higher.
# ######################################################################
# # defind a function to do it
# def find_largest_neibor(window_size, df):
#     i = 0
#     window = []
#     base_average = 0
#     arr = df["marginal_cost"]

#     while i < len(df) - window_size + 1:
#         # Calculate the average of current window
#         window_average = round(np.sum(arr[i : i + window_size]) / window_size, 2)
#         if window_average > base_average:
#             base_average = window_average
#             window = df.iloc[i : i + window_size]

#         # Shift window to right by one position
#         i += 1

#     return window


# def readfile(path, file):
#     df = pd.read_csv(os.path.join(path, file))
#     return df


# def converttodate(dfrow):
#     return date.fromisocalendar(dfrow["period"], dfrow["week"], dfrow["days"])


# # Only look at decarb cases for now
# case_list = [
#     "decarb_hydrogen/no",
#     "decarb_hydrogen/withall",
#     "nodecarb_hydrogen/no",
#     "nodecarb_hydrogen/withall",
#     # "boosted_decarb_no/no",
#     # "boosted_decarb_no/withall",
#     "nodecarb_hydrogen_co2p/no",
#     "nodecarb_hydrogen_co2p/withall",
# ]
# # case_folder = "decarb_hydrogen/no"
# for case_folder in case_list:
#     in_folder = os.path.join(root_folder, "trans_study_21TW/in")
#     base_folder = os.path.join(
#         root_folder, "trans_study_21TW/out", "decarb_hydrogen/no"
#     )
#     out_folder = os.path.join(root_folder, "trans_study_21TW/out", case_folder)
#     # Read mariginal cost table for base case -- decarb no
#     result_base = [
#         filename
#         for filename in os.listdir(base_folder)
#         if filename.startswith("energy_sources")
#     ]
#     es_base = readfile(base_folder, result_base[0])

#     es_base = es_base[
#         [
#             "load_zone",
#             "period",
#             "timepoint_label",
#             "zone_demand_mw",
#             "marginal_cost",
#             "peak_day",
#         ]
#     ]
#     es_base = es_base.loc[es_base["load_zone"] != "loadzone"].merge(
#         readfile(in_folder, "timepoints.csv"),
#         left_on="timepoint_label",
#         right_on="timestamp",
#     )
#     result = [
#         filename
#         for filename in os.listdir(out_folder)
#         if filename.startswith("energy_sources")
#     ]
#     # read marginal cost for each output cases
#     es = readfile(out_folder, result[0])

#     es = es[
#         [
#             "load_zone",
#             "period",
#             "timepoint_label",
#             "zone_demand_mw",
#             "marginal_cost",
#             "peak_day",
#         ]
#     ]
#     es = es.loc[es["load_zone"] != "loadzone"].merge(
#         readfile(in_folder, "timepoints.csv"),
#         left_on="timepoint_label",
#         right_on="timestamp",
#     )
#     # read input and output files
#     load = readfile(in_folder, "loads.csv")
#     dp = readfile(out_folder, "dispatch.csv")[
#         ["generation_project", "gen_load_zone", "timestamp", "DispatchGen_MW"]
#     ]
#     ### dispatched hydrogen
#     hydrogen = (
#         readfile(
#             out_folder,
#             "DispatchFuelCellMW.csv",
#         )
#         .rename(
#             {
#                 "DispatchFuelCellMW_index_1": "generation_project",
#                 "DispatchFuelCellMW_index_2": "timepoint_id",
#                 "DispatchFuelCellMW": "DispatchGen_MW",
#             },
#             axis=1,
#         )
#         .merge(readfile(in_folder, "timepoints.csv"), on="timepoint_id", how="left")
#     )
#     hydrogen["tech_type"] = "Hydrogen"
#     hydrogen["gen_load_zone"] = hydrogen["generation_project"]
#     # clean up dispatch.csv
#     dp["tech_type"] = tech_type(dp["generation_project"])
#     dp = pd.concat([dp, hydrogen])
#     # save a copy oof dispatch aggregated by zone and tech
#     dp_by_tech_zone = (
#         dp.groupby(["gen_load_zone", "tech_type", "timestamp"], as_index=False)
#         .agg({"DispatchGen_MW": "sum"})
#         .merge(
#             readfile(in_folder, "timepoints.csv"),
#             on="timestamp",
#         )
#     )
#     dp_by_tech_zone = tp_to_date(dp_by_tech_zone, "timestamp")
#     dp_by_tech_zone["days"] = pd.to_numeric(dp_by_tech_zone["days"])
#     dp_by_tech_zone["date"] = dp_by_tech_zone.apply(
#         lambda dfrow: converttodate(dfrow), axis=1
#     )  # pd.to_datetime(df.Year.astype(str), format='%Y') + \
#     #          pd.to_timedelta(df.Week.mul(7).astype(str) + ' days')
#     dp_by_zone = dp_by_tech_zone.groupby(
#         ["gen_load_zone", "timestamp"], as_index=False
#     ).agg({"DispatchGen_MW": "sum", "days": "first", "date": "first", "hour": "first"})
#     # clean up DispatchTX.csv
#     dp_tx = readfile(out_folder, "DispatchTx.csv")
#     out_tx = (
#         dp_tx.groupby(["TRANS_TIMEPOINTS_1", "TRANS_TIMEPOINTS_3"])
#         .agg({"DispatchTx": "sum"})
#         .reset_index()
#     )
#     in_tx = (
#         dp_tx.groupby(["TRANS_TIMEPOINTS_2", "TRANS_TIMEPOINTS_3"])
#         .agg({"DispatchTx": "sum"})
#         .reset_index()
#     )
#     flow = pd.merge(
#         out_tx,
#         pd.DataFrame(in_tx),
#         left_on=["TRANS_TIMEPOINTS_1", "TRANS_TIMEPOINTS_3"],
#         right_on=["TRANS_TIMEPOINTS_2", "TRANS_TIMEPOINTS_3"],
#         how="outer",
#     ).rename(
#         {
#             "TRANS_TIMEPOINTS_1": "zone",
#             "TRANS_TIMEPOINTS_3": "timepoint",
#             "DispatchTx_x": "outflow",
#             "DispatchTx_y": "inflow",
#         },
#         axis=1,
#     )
#     tough_all = pd.DataFrame()
#     dp_by_tech_zone_all = pd.DataFrame()
#     zones = es_base.load_zone.unique()
#     for z in zones:
#         es_base_zonal = es_base.loc[es_base["load_zone"] == z]
#         es_base_zonal = es_base_zonal.sort_values(by=["timepoint_id"])
#         # find the 3 days (consecutive 72 hours) with the largest average marginal cost
#         toughest_tp = find_largest_neibor(72, es_base_zonal)
#         # details of flows and dispatch
#         es_zonal = es.loc[es["load_zone"] == z]
#         es_zonal = es_zonal.sort_values(by=["timepoint_id"])
#         toughest_zonal_es = es_zonal.loc[
#             es["timepoint_id"].isin(toughest_tp["timepoint_id"])
#         ].rename({"load_zone": "zone"}, axis=1)
#         toughest_zonal_dp = dp_by_zone.loc[
#             (dp_by_zone["gen_load_zone"] == z)
#             & (dp_by_zone["timestamp"].isin(toughest_tp["timestamp"]))
#         ].rename({"gen_load_zone": "zone"}, axis=1)
#         toughest_zonal_flow = flow.loc[
#             (flow["zone"] == z) & (flow["timepoint"].isin(toughest_tp["timepoint_id"]))
#         ].rename({"timepoint": "timepoint_id"}, axis=1)
#         toughest = toughest_zonal_es.merge(
#             toughest_zonal_dp, on=["zone", "timestamp"]
#         ).merge(toughest_zonal_flow, on=["zone", "timepoint_id"])
#         toughest["ordered_time"] = toughest["timepoint_id"] - min(
#             toughest["timepoint_id"]
#         )
#         #
#         tough_dp_by_tech_zone = dp_by_tech_zone.loc[
#             (dp_by_tech_zone["gen_load_zone"] == z)
#             & (dp_by_tech_zone["timestamp"].isin(toughest_tp["timestamp"]))
#         ]
#         tough_dp_by_tech_zone["ordered_time"] = tough_dp_by_tech_zone[
#             "timepoint_id"
#         ] - min(tough_dp_by_tech_zone["timepoint_id"])
#         dp_by_tech_zone_all = pd.concat([dp_by_tech_zone_all, tough_dp_by_tech_zone])
#         tough_all = pd.concat([tough_all, toughest])

#     tough_all = tp_to_date(tough_all, "timestamp")
#     tough_all["days"] = pd.to_numeric(tough_all["days"])
#     tough_all["date"] = tough_all.apply(lambda dfrow: converttodate(dfrow), axis=1)
#     tough_all.to_csv(
#         os.path.join(
#             root_folder, "trans_study_21TW/results_data", case_folder, "tough_hours.csv"
#         ),
#         index=False,
#     )
#     dp_by_tech_zone_all.to_csv(
#         os.path.join(
#             root_folder,
#             "trans_study_21TW/results_data",
#             case_folder,
#             "dp_by_tech_zone.csv",
#         ),
#         index=False,
#     )

###################################################
# Boost demand
###################################################
# for z in zones:
#     es_base_zonal = es_base.loc[es_base["load_zone"] == z]
#     es_base_zonal = es_base_zonal.sort_values(by=["timepoint_id"])
#     # find the 3 days (consecutive 72 hours) with the largest average marginal cost
#     toughest_tp = find_largest_neibor(72, es_base_zonal)
#     # boost the related load inputs
#     load.loc[
#         (load["LOAD_ZONE"] == z)
#         & (load["TIMEPOINT"].isin(toughest_tp["timepoint_id"])),
#         "zone_demand_mw",
#     ] *= 1.25
# load.to_csv(
#     os.path.join(root_folder, "trans_study_21TW/in/load_boosted_decarb_no/loads.csv"),
#     index=False,
# )
