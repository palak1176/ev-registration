import pandas as pd

"""
Computes light/medium/heavy-duty EV registration ratios by year from Atlas
Public Policy's raw "EV Sales and Market Share" export.
 
NOTE: This uses the 'Registrations' field, which is a per-quarter FLOW metric
(new registrations that quarter), not a cumulative stock. See conversation
notes on why this matters for how these ratios get applied to DRIVES data.
 
NOTE: Includes both BEV and PHEV (Technology column).
 
NOTE: The most recent year in the file may be a partial year (check quarter
coverage) -- don't treat it as a full annual mix without checking.
"""
 
def duty_class_ratios(file_path, header_row=2):
    """
    Returns a dict keyed by year, e.g.:
        {2022: {'light_duty': 0.9655, 'medium_duty': 0.0345, 'heavy_duty': 0.0},
         2023: {...}, ...}
    """
    df = pd.read_excel(file_path, sheet_name="Sheet1", header=header_row)
 
    required_cols = ["Date Hierarchy - Year", "GVWR Category", "Registrations"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
 
    grouped = (
        df.groupby(["Date Hierarchy - Year", "GVWR Category"])["Registrations"]
        .sum()
        .unstack(fill_value=0)
        .rename(
            columns={
                "Light Duty (Class 1-2A)": "light_duty",
                "Medium Duty (Class 2B-6)": "medium_duty",
                "Heavy Duty (Class 7-8)": "heavy_duty",}))
 
    # In case a duty class is entirely absent in some year
    for col in ["light_duty", "medium_duty", "heavy_duty"]:
        if col not in grouped.columns:
            grouped[col] = 0
 
    totals = grouped[["light_duty", "medium_duty", "heavy_duty"]].sum(axis=1)
 
    ratios = {}
    for year, row in grouped.iterrows():
        total = totals.loc[year]
        ratios[int(year)] = {
            "light_duty": row["light_duty"] / total,
            "medium_duty": row["medium_duty"] / total,
            "heavy_duty": row["heavy_duty"] / total}
 
    return ratios

def carry_ratio_backward(ratios, missing_year, source_year):
    """
    Fills in a year missing from the Atlas ratios by reusing another year's
    ratio -- e.g. carry_ratio_backward(ratios, 2021, 2022) uses 2022's
    duty-class mix as a stand-in for 2021, since Atlas's data doesn't go
    back that far.
 
    This is an ASSUMPTION (that the duty-class mix didn't change much
    between the two years), not real data for missing_year -- document it
    as such wherever this feeds into RTEP/MACAP tracking. Modifies and
    returns the ratios dict in place.
    """
    if source_year not in ratios:
        raise ValueError(f"Can't carry from {source_year} -- it's not in ratios either.")
    ratios[missing_year] = dict(ratios[source_year])
    print(
        f"NOTE: {missing_year} duty-class ratio is copied from {source_year} "
        f"(assumption, not real {missing_year} data).")
    return ratios
 
 
def flag_partial_years(file_path, header_row=2):
    """Prints which years in the file don't have all 4 quarters present."""
    df = pd.read_excel(file_path, sheet_name="Sheet1", header=header_row)
    coverage = df.groupby("Date Hierarchy - Year")["Date Hierarchy - Quarter"].unique()
    for year, quarters in coverage.items():
        if len(quarters) < 4:
            print(f"Year {int(year)} is PARTIAL -- only has quarters: {sorted(quarters)}")


atlanta_msa_counties = [
    "Barrow", "Clayton", "Douglas", "Haralson", "Meriwether", 
    "Pike", "Bartow", "Cobb", "Fayette", "Heard", "Morgan", 
    "Rockdale", "Butts", "Coweta", "Forsyth", "Henry", "Newton",
    "Spalding", "Carroll", "Dawson", "Fulton", "Jasper", "Paulding", 
    "Walton", "Cherokee", "DeKalb", "Gwinnett", "Lamar", "Pickens"]

def _read_county_csv(file_path):
    """Reads one DRIVES county-level CSV and keeps only the columns we need."""
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None
    except pd.errors.EmptyDataError:
        print("Error: The file is empty.")
        return None
    except pd.errors.ParserError:
        print("Error: There was a parsing error while reading the file.")
        return None
 
    columns_to_keep = ['county', 'total_vehicle', 'ev']
    missing_cols = [col for col in columns_to_keep if col not in df.columns]
    if missing_cols:
        print(f"Missing columns: {missing_cols}")
        return None  # can't safely subset if a required column is missing
 
    df['county'] = df['county'].fillna('').str.strip()  # can't title-case because of "DeKalb"
    df = df[columns_to_keep]
 
    # Drop the phantom statewide total row some DRIVES pulls include (blank
    # county, total_vehicle = all of Georgia). Georgia has 159 real counties;
    # a blank-county row is not one of them.
    blank_rows = (df['county'] == '').sum()
    if blank_rows:
        print(f"Warning: {file_path} has {blank_rows} row(s) with a blank county "
              f"(likely a statewide total row) -- dropping.")
        df = df[df['county'] != '']
 
    # Exact duplicate rows (same county, same values) are scraper artifacts --
    # drop them, don't sum them, or counts get double/triple counted.
    exact_dupes = df[df.duplicated(keep=False)]
    if len(exact_dupes):
        print(f"Warning: {file_path} has {len(exact_dupes)} exact duplicate row(s) "
              f"for: {sorted(exact_dupes['county'].unique())}. Dropping repeats.")
        df = df.drop_duplicates()
 
    # Same county, DIFFERENT values -- this is not a scraper repeat, something
    # else is going on (e.g. two distinct records for one county). Don't
    # silently sum these; flag them so they can be checked by hand.
    remaining_dupes = df.loc[df.duplicated('county', keep=False), 'county'].unique().tolist()
    if remaining_dupes:
        print(f"Warning: {file_path} still has multiple DIFFERING rows for: "
              f"{remaining_dupes}. NOT auto-combined -- check the raw file.")
 
    return df
    

def ev_registration(past_year_file, target_year_file, year, region, ratios):
    """
    ratios: the dict returned by duty_class_ratios(), e.g.
        ratios = duty_class_ratios("EV_Sales_and_Market_Share.xlsx")
        ev_registration(past_file, target_file, 2025, "Atlanta MPO", ratios)
    """
    if year not in ratios:
        raise ValueError(
            f"No duty-class ratio available for {year}. "
            f"Ratios cover: {sorted(ratios.keys())}")
 
    past_df = _read_county_csv(past_year_file)
    target_df = _read_county_csv(target_year_file)
    if past_df is None or target_df is None:
        return None
 
    # Merge past and target snapshots on county, then diff to get the
    # net change over the period (this is the "flow" that lines up with
    # Atlas's per-year registration ratios -- see conversation notes on
    # why a raw cumulative total can't be split with these ratios directly).
    merged = past_df.merge(
        target_df, on='county', suffixes=('_past', '_target'), how='outer')
    merged[['total_vehicle_past', 'ev_past', 'total_vehicle_target', 'ev_target']] = (
        merged[['total_vehicle_past', 'ev_past', 'total_vehicle_target', 'ev_target']]
        .fillna(0))
    merged['total_vehicle'] = merged['total_vehicle_target'] - merged['total_vehicle_past']
    merged['ev'] = merged['ev_target'] - merged['ev_past']
 
    negative_ev_counties = merged.loc[merged['ev'] < 0, 'county'].tolist()
    if negative_ev_counties:
        print(
            f"Warning: net EV count DECREASED between the two files in: "
            f"{negative_ev_counties}. Check for data issues before trusting these rows.")
 
    ev_registration_df = merged[['county', 'total_vehicle', 'ev']]

    # Define counties based on the specified region
    if region == "Atlanta MSA":
        counties = atlanta_msa_counties
    elif region == "Atlanta MPO":
        counties = [county for county in atlanta_msa_counties if county not in ["Haralson", "Meriwether", "Bartow", "Heard", "Morgan", "Butts", "Jasper", "Lamar", "Pickens", "Pike"]]
    elif region == "ARC Core":
        counties = [county for county in atlanta_msa_counties if county in ["Cherokee", "Cobb", "Douglas", "Fulton", "Fayette", "Clayton", "Henry", "DeKalb", "Gwinnett", "Forsyth", "Rockdale"]]
    else:
        raise ValueError("region must be 'Atlanta MSA', 'Atlanta MPO', or 'ARC Core'")

    # Case-insensitive filter
    counties_lower = {c.lower() for c in counties}
    missing_counties = counties_lower - set(ev_registration_df['county'].str.lower())
    if missing_counties:
        print(f"Warning: The following counties are missing from the data: {missing_counties}")
    ev_registration_df = ev_registration_df[ev_registration_df['county'].str.lower().isin(counties_lower)]

    # Apply this year's duty-class ratios (from Atlas raw data) to the diffed EV counts
    year_ratios = ratios[year]
    ev_registration_df['light_duty_evs'] = round(
        ev_registration_df['ev'] * year_ratios['light_duty'], 0).astype(int)
    ev_registration_df['medium_duty_evs'] = round(
        ev_registration_df['ev'] * year_ratios['medium_duty'], 0).astype(int)
    ev_registration_df['heavy_duty_evs'] = round(
        ev_registration_df['ev'] * year_ratios['heavy_duty'], 0).astype(int)
 
    print(f"\nTotal light-duty EVs in {region} in {year}: {ev_registration_df['light_duty_evs'].sum():,.0f}")
    print(f"Total medium-duty EVs in {region} in {year}: {ev_registration_df['medium_duty_evs'].sum():,.0f}")
    print(f"Total heavy-duty EVs in {region} in {year}: {ev_registration_df['heavy_duty_evs'].sum():,.0f}")
    print(f"Total EVs added in {region} in {year}: {ev_registration_df['ev'].sum():,.0f}")
    print(f"Total vehicles added in {region} in {year}: {ev_registration_df['total_vehicle'].sum():,.0f}")
 
    save_region = region.lower().replace(" ", "_")
    ev_registration_df.to_csv(f"ev_registration_by_county_{save_region}_{year}.csv", index=False)
    return ev_registration_df
 
 
def run_all_years(year_files, region, ratios):
    """
    Runs ev_registration() across every consecutive pair of years and stitches
    the region-level totals into one DataFrame -- no need to call
    ev_registration() by hand for each year.
 
    year_files: dict mapping year -> DRIVES county CSV path, e.g.
        {
            2020: "registered_vehicles_by_county_04-2020.csv",
            2021: "registered_vehicles_by_county_04-2021.csv",
            2022: "registered_vehicles_by_county_04-2022.csv",
            2023: "registered_vehicles_by_county_04-2023.csv",
            2024: "registered_vehicles_by_county_04-2024.csv",
            2025: "registered_vehicles_by_county_04-2025.csv",
        }
    Each consecutive pair (2020->2021, 2021->2022, ...) is diffed and has
    that later year's Atlas ratio applied, same as calling ev_registration()
    yourself for each pair. The first year in year_files has nothing before
    it to diff against, so it won't appear as a row in the output -- only
    years that have a prior-year file to compare to will.
 
    Returns a DataFrame indexed by year with summed light/medium/heavy EV
    counts, total EVs added, and total vehicles added for the region.
    """
    years = sorted(year_files.keys())
    summary_rows = []
 
    for past_year, target_year in zip(years[:-1], years[1:]):
        print(f"\n=== Processing {past_year} -> {target_year} ===")
        if target_year not in ratios:
            print(
                f"Skipping {target_year} -- no Atlas duty-class ratio available "
                f"for this year (ratios cover: {sorted(ratios.keys())})."
            )
            continue
        result_df = ev_registration(
            year_files[past_year], year_files[target_year], target_year, region, ratios
        )
        if result_df is None:
            print(f"Skipping {target_year} -- see error above.")
            continue
        summary_rows.append({
            "year": target_year,
            "light_duty_evs": result_df["light_duty_evs"].sum(),
            "medium_duty_evs": result_df["medium_duty_evs"].sum(),
            "heavy_duty_evs": result_df["heavy_duty_evs"].sum(),
            "total_evs_added": result_df["ev"].sum(),
            "total_vehicles_added": result_df["total_vehicle"].sum(),
        })
 
    summary_df = pd.DataFrame(summary_rows).set_index("year")

    # % of light-duty EVs relative to ALL new vehicles added that year (every fuel type, not just EVs) 
    # -- NOTE: DRIVES has no private-vs-fleet ownership field, so this is light-duty EVs as a
    # share of total vehicle growth, not filtered by ownership type.
    summary_df["pct_light_duty_of_total_added"] = (summary_df["light_duty_evs"] / summary_df["total_vehicles_added"] * 100).round(2)

    print("\n=== % of light-duty EVs relative to total vehicles added, by year ===")
    for year, row in summary_df.iterrows():
        print(f"{year}: {row['pct_light_duty_of_total_added']:.2f}%")

    summary_df.to_csv(f"ev_registration_summary_{region.lower().replace(' ', '_')}.csv")
    return summary_df

def cumulative_totals(year_files, region, ratios, summary_df=None):
    """
    Estimates the TOTAL number of light/medium/heavy-duty EVs currently on
    the road in `region`, as of the MOST RECENT file in `year_files` --
    not just the year-over-year additions run_all_years() reports.

    run_all_years() only ever counts ADDITIONS between consecutive files --
    the earliest year in year_files is never counted on its own, since it's
    only ever used as the "past" half of the first diff. This function adds
    that missing piece back in: it splits the earliest year's own EV count
    into duty classes (using that year's ratio) as a baseline, then adds
    every year-over-year addition on top of it.

    Requires a ratio for the EARLIEST year in year_files -- use
    carry_ratio_backward() first if Atlas doesn't cover it.

    Pass summary_df if you already have one from run_all_years() (saves
    re-running it); otherwise it's computed for you.
    """
    earliest_year = min(year_files.keys())
    most_recent_year = max(year_files.keys())

    if earliest_year not in ratios:
        raise ValueError(
            f"No ratio available for {earliest_year}, the earliest year in "
            f"year_files. Use carry_ratio_backward() to fill it in first."
        )

    baseline_df = _read_county_csv(year_files[earliest_year])
    if baseline_df is None:
        raise ValueError(f"Could not read {year_files[earliest_year]}")

    if region == "Atlanta MSA":
        counties = atlanta_msa_counties
    elif region == "Atlanta MPO":
        counties = [c for c in atlanta_msa_counties if c not in
                    ["Haralson", "Meriwether", "Bartow", "Heard", "Morgan",
                     "Butts", "Jasper", "Lamar", "Pickens", "Pike"]]
    elif region == "ARC Core":
        counties = [c for c in atlanta_msa_counties if c in
                    ["Cherokee", "Cobb", "Douglas", "Fulton", "Fayette",
                     "Clayton", "Henry", "DeKalb", "Gwinnett", "Forsyth", "Rockdale"]]
    else:
        raise ValueError("region must be 'Atlanta MSA', 'Atlanta MPO', or 'ARC Core'")

    counties_lower = {c.lower() for c in counties}
    baseline_region = baseline_df[baseline_df["county"].str.lower().isin(counties_lower)]
    baseline_ev_total = baseline_region["ev"].sum()

    baseline_ratio = ratios[earliest_year]
    baseline_light = round(baseline_ev_total * baseline_ratio["light_duty"])
    baseline_medium = round(baseline_ev_total * baseline_ratio["medium_duty"])
    baseline_heavy = round(baseline_ev_total * baseline_ratio["heavy_duty"])

    if summary_df is None:
        summary_df = run_all_years(year_files, region, ratios)

    total_light = baseline_light + summary_df["light_duty_evs"].sum()
    total_medium = baseline_medium + summary_df["medium_duty_evs"].sum()
    total_heavy = baseline_heavy + summary_df["heavy_duty_evs"].sum()
    total_all = total_light + total_medium + total_heavy

    print(f"\n=== Cumulative EV stock in {region}, as of {most_recent_year} pull ===")
    print(f"Light-duty:  {total_light:,.0f}")
    print(f"Medium-duty: {total_medium:,.0f}")
    print(f"Heavy-duty:  {total_heavy:,.0f}")
    print(f"Total:       {total_all:,.0f}")
    print(
        f"(Baseline from {earliest_year}: light={baseline_light:,}, "
        f"medium={baseline_medium:,}, heavy={baseline_heavy:,} -- split "
        f"using {earliest_year}'s ratio, which is an assumption if that "
        f"ratio was carried back from a later year via carry_ratio_backward.)")

    return {
        "light_duty": total_light,
        "medium_duty": total_medium,
        "heavy_duty": total_heavy,
        "total": total_all,
        "as_of_year": most_recent_year,}

def plot_summary(summary_df, region, save_path=None):
    """
    Stacked bar chart of light/medium/heavy-duty EVs added per year, for the
    summary_df returned by run_all_years().
    """
    import matplotlib.pyplot as plt
 
    fig, ax = plt.subplots(figsize=(9, 5.5))
    years = summary_df.index.astype(str)
 
    ax.bar(years, summary_df["light_duty_evs"], label="Light-duty", color="#26428b")
    ax.bar(years, summary_df["medium_duty_evs"], bottom=summary_df["light_duty_evs"],
           label="Medium-duty", color="#cc0000")
    bottom_heavy = summary_df["light_duty_evs"] + summary_df["medium_duty_evs"]
    ax.bar(years, summary_df["heavy_duty_evs"], bottom=bottom_heavy,
           label="Heavy-duty", color="#f1c232")
 
    ax.set_title(f"EVs Added by Duty Class -- {region}")
    ax.set_xlabel("Year")
    ax.set_ylabel("EVs added (net change from prior year)")
    ax.legend()
    fig.tight_layout()
 
    if save_path:
        fig.savefig(save_path, dpi=150)
        print(f"Saved plot to {save_path}")
    return fig
 
 
ratios = duty_class_ratios("EV_Sales_and_Market_Share.xlsx")
flag_partial_years("EV_Sales_and_Market_Share.xlsx")
carry_ratio_backward(ratios, missing_year=2021, source_year=2022)
carry_ratio_backward(ratios, missing_year=2020, source_year=2022) 

year_files = {
    2020: "registered_vehicles_by_county_2020.csv",
    2021: "registered_vehicles_by_county_2021.csv",
    2022: "registered_vehicles_by_county_2022.csv",
    2023: "registered_vehicles_by_county_2023.csv",
    2024: "registered_vehicles_by_county_2024.csv",
    2025: "registered_vehicles_by_county_04-2025.csv",
    2026: "registered_vehicles_by_county_07-2026.csv"
}
summary = run_all_years(year_files, "Atlanta MSA", ratios)
plot_summary(summary, "Atlanta MSA", save_path="atlanta_msa_ev_duty_class.png")
cumulative_totals(year_files, "Atlanta MSA", ratios)