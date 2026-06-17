# Atlanta MSA EV Registration Estimation
This project estimates light-duty, medium-duty, and heavy-duty electric vehicle (EV) registrations within the Atlanta Metropolitan Statistical Area (MSA) using county-level vehicle registration data from the Georgia Department of Revenue and statewide EV fleet composition ratios derived from Atlas EV Hub data. The script filters county-level registration records to Atlanta MSA counties, applies annual EV vehicle-class ratios, and generates estimated EV counts by vehicle class for regional transportation electrification analysis.

## Features
- Reads county-level vehicle registration data from a CSV file
- Validates required input columns before analysis
- Filters data to include only Atlanta MSA counties
- Supports both MACAP and RTEP county definitions
- Applies annual EV vehicle-class ratios derived from Atlas EV Hub data
- Estimates light-duty, medium-duty, and heavy-duty EV registrations
- Computes Atlanta MSA-wide EV totals by vehicle class
- Computes total registered vehicles across the Atlanta MSA
- Calculates percentage of registered vehicles that are estimated light-duty EVs 
- Exports filtered and processed data to a CSV file

## Technologies Used
- Python 3
- Pandas

## Input Data
- The script requires a CSV file generated from the Georgia Registered Vehicle Statistics Automation project: https://github.com/palak1176/automate-registered-vehicles
- Vehicle-class ratios are derived from quarterly Georgia EV registration data obtained from the Atlas EV Hub State EV Summary Dashboard: https://www.atlasevhub.com/market-data/state-ev-summary-dashboard/

## Output Data
- The script generates a CSV file containing Atlanta MSA county-level EV registration estimates by vehicle class: ev_registration_by_county_atlanta_msa_year.csv (replace the year)

## Usage
- Install required packages: pip install pandas
- Run the script: python ev_registration.py
- Update the input file path here: print(ev_registration("registered_vehicles_by_county_2021.csv"))
- Update vehicle-class ratios to match the analysis year:
    - Use 2022 ratios for 2022 data
    - Use 2023 ratios for 2023 data
    - Use 2024 ratios for 2024 data
    - Use 2025 ratios for 2025 data
    - Use 2026 ratios for 2026 data
    - For 2020 and 2021 analyses, use the 2022 annual average vehicle-class ratios because vehicle-class-specific EV registration data was unavailable
- Review summary statistics printed to the console and save the generated CSV file

## Methodology
- County-level vehicle registration data are collected from the Georgia Department of Revenue
- Statewide quarterly EV registration data are collected from Atlas EV Hub
- Quarterly EV vehicle-class proportions are calculated by dividing light-duty, medium-duty, and heavy-duty EV registrations by total EV registrations
- Annual average vehicle-class ratios are calculated from quarterly values
- County-level EV registration totals are multiplied by the annual average ratios to estimate EV registrations by vehicle class
- County estimates are aggregated to calculate Atlanta MSA totals and EV penetration metrics

## Notes
- Annual vehicle-class ratios must be updated manually before running the analysis
- Results represent estimates because county-level EV registrations are not publicly available by vehicle class
- For 2020 and 2021, vehicle-class estimates are based on 2022 statewide vehicle-class proportions
- The script supports the full 29-county Atlanta MSA used in MACAP analyses
- For RTEP analyses, uncomment the provided code block to remove counties that are outside the Regional Transportation Electrification Plan study area