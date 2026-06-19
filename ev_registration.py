import pandas as pd

atlanta_msa_counties = [
    "Barrow", "Clayton", "Douglas", "Haralson", "Meriwether", 
    "Pike", "Bartow", "Cobb", "Fayette", "Heard", "Morgan", 
    "Rockdale", "Butts", "Coweta", "Forsyth", "Henry", "Newton",
    "Spalding", "Carroll", "Dawson", "Fulton", "Jasper", "Paulding", 
    "Walton", "Cherokee", "DeKalb", "Gwinnett", "Lamar", "Pickens"]

def ev_registration(file_path, year, region):
    # Reads CSV file
    try:
        ev_registration_df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None
    except pd.errors.EmptyDataError:
        print("Error: The file is empty.")
        return None
    except pd.errors.ParserError:
        print("Error: There was a parsing error while reading the file.")
        return None
        
    # Check for required columns and keep only those needed for analysis
    columns_to_keep = ['county', 'total_vehicle', "ev"]
    missing_cols = [col for col in columns_to_keep if col not in ev_registration_df.columns]
    if missing_cols:
        print(f"Missing columns: {missing_cols}")
    ev_registration_df = ev_registration_df[columns_to_keep]

    # Define counties based on the specified region
    if region == "Atlanta MSA":
        counties = atlanta_msa_counties
    elif region == "Atlanta MPO":
        counties = [county for county in atlanta_msa_counties if county not in ["Haralson", "Meriwether", "Bartow", "Heard", "Morgan", "Butts", "Jasper", "Lamar", "Pickens"]]
    elif region == "ARC Core":
        counties = [county for county in atlanta_msa_counties if county in ["Cherokee", "Cobb", "Douglas", "Fulton", "Fayette", "Clayton", "Henry", "DeKalb", "Gwinnett", "Forsyth", "Rockdale"]]
    else:
        raise ValueError("region must be 'Atlanta MSA', 'Atlanta MPO', or 'ARC Core'")

     # Clean 'county' column and filter for Atlanta MSA counties
    ev_registration_df['county'] = ev_registration_df['county'].fillna('').str.strip() # can't do title case because of "DeKalb"
    # Case-insensitive filter
    counties_lower = {c.lower() for c in counties}
    missing_counties = counties_lower - set(ev_registration_df['county'].str.lower())
    if missing_counties:
        print(f"Warning: The following counties are missing from the data: {missing_counties}")
    ev_registration_df = ev_registration_df[ev_registration_df['county'].str.lower().isin(counties_lower)]

    # Calculate light-duty, medium-duty, and heavy-duty EVs based on the provided percentages
    if year in [2020, 2021, 2022]:
        ev_registration_df['light_duty_evs'] = round(ev_registration_df['ev'] * 0.9690835613, 0).astype(int)
        ev_registration_df['medium_duty_evs'] = round(ev_registration_df['ev'] * 0.0309164387, 0).astype(int)
        ev_registration_df['heavy_duty_evs'] = round(ev_registration_df['ev'] * 0.0000000000, 0).astype(int)

    elif year == 2023:
        ev_registration_df['light_duty_evs'] = round(ev_registration_df['ev'] * 0.9194743390, 0).astype(int)
        ev_registration_df['medium_duty_evs'] = round(ev_registration_df['ev'] * 0.0801836380, 0).astype(int)
        ev_registration_df['heavy_duty_evs'] = round(ev_registration_df['ev'] * 0.0003420230, 0).astype(int)

    elif year == 2024:
        ev_registration_df['light_duty_evs'] = round(ev_registration_df['ev'] * 0.8612182545, 0).astype(int)
        ev_registration_df['medium_duty_evs'] = round(ev_registration_df['ev'] * 0.1359837941, 0).astype(int)
        ev_registration_df['heavy_duty_evs'] = round(ev_registration_df['ev'] * 0.0017735712, 0).astype(int)

    elif year == 2025:
        ev_registration_df['light_duty_evs'] = round(ev_registration_df['ev'] * 0.8474387356, 0).astype(int)
        ev_registration_df['medium_duty_evs'] = round(ev_registration_df['ev'] * 0.1510654460, 0).astype(int)
        ev_registration_df['heavy_duty_evs'] = round(ev_registration_df['ev'] * 0.0020271385, 0).astype(int)

    elif year == 2026:
        ev_registration_df['light_duty_evs'] = round(ev_registration_df['ev'] * 0.9167054444, 0).astype(int)
        ev_registration_df['medium_duty_evs'] = round(ev_registration_df['ev'] * 0.0822087793, 0).astype(int)
        ev_registration_df['heavy_duty_evs'] = round(ev_registration_df['ev'] * 0.0010857763, 0).astype(int)

    print(f"\nTotal light-duty EVs in {region} in {year}: {ev_registration_df['light_duty_evs'].sum():,.0f}")
    print(f"Total medium-duty EVs in {region} in {year}: {ev_registration_df['medium_duty_evs'].sum():,.0f}")
    print(f"Total heavy-duty EVs in {region} in {year}: {ev_registration_df['heavy_duty_evs'].sum():,.0f}")
    print(f"Total EVs in {region} in {year}: {ev_registration_df['ev'].sum():,.0f}")
    print(f"Total vehicles in {region} in {year}: {ev_registration_df['total_vehicle'].sum():,.0f}")
    print(f"Percentage of light-duty EVs in {region} in {year}: {ev_registration_df['light_duty_evs'].sum() / ev_registration_df['total_vehicle'].sum() * 100:.2f}%\n")

    save_region = safe_region = region.lower().replace(" ", "_")
    return ev_registration_df.to_csv(f"ev_registration_by_county_{save_region}_{year}.csv", index=False)

# Format: ev_registration(file_path, year, region)
# file_path: string, path to the CSV file containing EV registration data
# year: integer, the year for which to calculate EV registrations (e.g., 2025)
# region: string, the region for which to calculate EV registrations ("Atlanta MSA", "Atlanta MPO", or "ARC Core")
print(ev_registration("registered_vehicles_by_county_04-2025.csv", 2025, "ARC Core"))