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
    return df[columns_to_keep]

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
    return ev_registration_df.to_csv(f"ev_registration_by_county_{save_region}_{year}.csv", index=False)

# Format: ev_registration(past_year_file, target_year_file, year, region)
# past_year_file: string, path to the CSV file containing EV registration data for the past year (eg. 2024 if looking for 2025 data)
# target_year_file: string, path to the CSV file containing EV registration data for the target year
# year: integer, the year for which to calculate EV registrations (e.g., 2025)
# region: string, the region for which to calculate EV registrations ("Atlanta MSA", "Atlanta MPO", or "ARC Core")
# print(ev_registration("registered_vehicles_by_county_04-2024.csv", "registered_vehicles_by_county_04-2025.csv", 2025, "Atlanta MPO"))

ratios = duty_class_ratios("EV_Sales_and_Market_Share.xlsx")
print(flag_partial_years("EV_Sales_and_Market_Share.xlsx"))
print(ev_registration(
    "registered_vehicles_by_county_04-2024.csv",
    "registered_vehicles_by_county_04-2025.csv",
    2025,
    "Atlanta MSA",
    ratios))