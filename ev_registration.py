import pandas as pd

atlanta_msa_counties = [
    "Barrow", "Clayton", "Douglas", "Haralson", "Meriwether", 
    "Pike", "Bartow", "Cobb", "Fayette", "Heard", "Morgan", 
    "Rockdale", "Butts", "Coweta", "Forsyth", "Henry", "Newton", 
    "Spalding", "Carroll", "Dawson", "Fulton", "Jasper", "Paulding", 
    "Walton", "Cherokee", "DeKalb", "Gwinnett", "Lamar", "Pickens"]

# uncomment the line below if conducting analysis for RTEP because these 9 counties are not part of the RTEP but are included in MACAP
# atlanta_msa_counties = [county for county in atlanta_msa_counties if county not in ["Haralson", "Meriwether", "Bartow", "Heard", "Morgan", "Butts", "Jasper", "Lamar", "Pickens"]]

def ev_registration(file_path):
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

     # Clean 'county' column and filter for Atlanta MSA counties
    ev_registration_df['county'] = ev_registration_df['county'].fillna('').str.strip() # can't do title case because of "DeKalb"
    # Case-insensitive filter
    atlanta_msa_counties_lower = {c.lower() for c in atlanta_msa_counties}
    missing_counties = atlanta_msa_counties_lower - set(ev_registration_df['county'].str.lower())
    if missing_counties:
        print(f"Warning: The following counties are missing from the data: {missing_counties}")
    ev_registration_df = ev_registration_df[ev_registration_df['county'].str.lower().isin(atlanta_msa_counties_lower)]

    # Calculate light-duty, medium-duty, and heavy-duty EVs based on the provided percentages
    # Default ratios are 2022 ratios but input correct annual averages from Atlas Public Policy Analysis (2026 ratios for 2026 data, etc.)
    ev_registration_df['light_duty_evs'] = round(ev_registration_df['ev'] * 0.9690835613, 0).astype(int)
    ev_registration_df['medium_duty_evs'] = round(ev_registration_df['ev'] * 0.0309164387, 0).astype(int)
    ev_registration_df['heavy_duty_evs'] = round(ev_registration_df['ev'] * 0.0000000000, 0).astype(int) 

    print(f"\nTotal light-duty EVs in Atlanta MSA: {ev_registration_df['light_duty_evs'].sum():,.0f}")
    print(f"Total medium-duty EVs in Atlanta MSA: {ev_registration_df['medium_duty_evs'].sum():,.0f}")
    print(f"Total heavy-duty EVs in Atlanta MSA: {ev_registration_df['heavy_duty_evs'].sum():,.0f}")
    print(f"Total EVs in Atlanta MSA: {ev_registration_df['ev'].sum():,.0f}")
    print(f"Total vehicles in Atlanta MSA: {ev_registration_df['total_vehicle'].sum():,.0f}")
    print(f"Percentage of light-duty EVs in Atlanta MSA: {ev_registration_df['light_duty_evs'].sum() / ev_registration_df['total_vehicle'].sum() * 100:.2f}%\n")

    return ev_registration_df.to_csv("ev_registration_by_county_atlanta_msa_year.csv", index=False)

print(ev_registration("registered_vehicles_by_county_2021.csv"))