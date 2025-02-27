from pg_to_switch_2days import main

main(
    settings_file="case_settings/26-zone/settings-atb2023_less",
    results_folder="pj/E_2days",
    # case_id=["base_short"],
    case_id=["base_2days_2023"],
    year=[
        2023,
    ],
    myopic=False,
)
