# Atlanta MSA EV Registration by Duty Class

## What this script does

Takes year-over-year Georgia DRIVES county vehicle registration pulls (see
the companion scraper notebook, [`automate-registered-vehicles.ipynb`](https://github.com/palak1176/automate-registered-vehicles)) and
Atlas Public Policy's EV registration data, and estimates how many
light-duty, medium-duty, and heavy-duty EVs were **added** each year in a
given Atlanta-area region (MSA, MPO, or ARC's 11-county core).

It does this in two steps:
1. Diffs two consecutive years of DRIVES county data to get the net change
   in vehicles/EVs per county over that period.
2. Splits that net change into light/medium/heavy-duty using that year's
   real registration mix, pulled directly from Atlas's raw data (not a
   hand-typed percentage).

## Why it works this way (read this before changing anything)

DRIVES gives you a **cumulative total** (all vehicles currently registered),
but Atlas's duty-class mix describes a **flow** (the mix of vehicles newly
registered in a given year). Those aren't the same kind of number, so you
can't apply Atlas's ratio straight to a DRIVES total. Diffing two DRIVES
years first converts the DRIVES side into a flow too (net vehicles added
over that period), so both sides of the split are now the same type of
quantity. This is the reason the script works on **pairs** of years rather
than one file at a time.

## Requirements

- Python packages: `pandas`, `matplotlib` (only needed for `plot_summary`)
- Atlas Public Policy's raw **"EV Sales and Market Share"** export (`.xlsx`),
  with `Date Hierarchy - Year`, `Date Hierarchy - Quarter`, `GVWR Category`,
  and `Registrations` columns. Header starts on row 3 of the sheet (i.e.
  `header_row=2`, zero-indexed) — this is the default.
- DRIVES county-level CSVs, one per year you want to cover, each with at
  minimum `county`, `total_vehicle`, and `ev` columns.

## Input file naming

The script doesn't require a specific naming convention — you pass exact
file paths in the `year_files` dict — but be consistent about **what date
within the year each file represents** (see "Known limitations" below on
why mixing snapshot types across years causes problems).

## Function reference

### `duty_class_ratios(file_path, header_row=2)`
Reads the Atlas Excel export and returns a dict keyed by year:
```python
{2022: {'light_duty': 0.9655, 'medium_duty': 0.0345, 'heavy_duty': 0.0}, ...}
```
Includes both BEV and PHEV (doesn't filter on `Technology`). Raises
`ValueError` if the expected columns aren't present.

### `flag_partial_years(file_path, header_row=2)`
Prints which years in the Atlas file don't have all 4 quarters of data.
Run this once after loading `ratios` — don't treat a partial year's ratio
as a stable full-year mix (most relevant for the current year, which is
usually still in progress).

### `carry_ratio_backward(ratios, missing_year, source_year)`
Atlas's data only goes back to 2022. This copies another year's ratio onto
a year that has none, and prints a note flagging it as an assumption. It
modifies `ratios` in place. **The further apart the two years are, the
weaker this assumption gets** — carrying 2022 back to 2021 is a one-year
stretch and reasonably safe (duty-class mix moves slowly), but carrying
2022 all the way back to 2020 (two years) is a bigger assumption and
should be flagged more prominently wherever these numbers get used.

### `ev_registration(past_year_file, target_year_file, year, region, ratios)`
Runs the full pipeline for a single year-pair: reads both files, diffs
them by county, filters to the given `region`, applies that year's
duty-class ratio, prints a summary, saves
`ev_registration_by_county_{region}_{year}.csv`, and returns the resulting
DataFrame.

- `region` must be exactly `"Atlanta MSA"`, `"Atlanta MPO"`, or
  `"ARC Core"` (case-sensitive).
- `year` is used to pick which row of `ratios` to apply — this should be
  the **target** year (the later of the two files), since the vehicles
  added over the period take on that period's registration mix.
- Prints a warning if any county's EV count went *down* between the two
  files — a drop shouldn't normally happen and may indicate a data issue
  worth checking by hand rather than trusting as-is.

### `run_all_years(year_files, region, ratios)`
Loops `ev_registration()` across every consecutive pair of years in
`year_files` (a `{year: file_path}` dict) and stitches the region-level
totals into one summary DataFrame, indexed by year. Automatically skips
any year-pair whose target year has no ratio available in `ratios`
(rather than crashing), and saves
`ev_registration_summary_{region}.csv`.

Also computes and prints **`pct_light_duty_of_total_added`** — light-duty
EVs added that year as a percentage of *all* new vehicles added that year
(every fuel type, not just EVs). Note: DRIVES has no private-vs-fleet
ownership field, so this is light-duty EVs as a share of total vehicle
growth, not filtered by ownership type — if you need that distinction,
it would have to come from a different data source.

The **first** year in `year_files` never appears as a row on its own —
it's only ever used as the "past" half of the first pair — so this
summary only ever shows *additions*, not the total EV stock. Everything
this function reports (`light_duty_evs`, `medium_duty_evs`,
`heavy_duty_evs`, and the print statements in `ev_registration()`) is a
per-year addition, not a running total — for a total, see
`cumulative_totals()` below.

### `cumulative_totals(year_files, region, ratios, summary_df=None)`
Gives you the TOTAL number of light/medium/heavy-duty EVs currently in
`region`, as of the most recent file in `year_files` — not just the
year-over-year additions `run_all_years()` reports.

It works by splitting the **earliest** year's own EV count into duty
classes (using that year's ratio) as a baseline — since that year is
never counted by `run_all_years()` on its own — then adding every
subsequent year's additions on top. Prints the baseline breakdown
separately from the final total, so it's clear how much of the number
rests on the earliest-year ratio (which is often an assumption carried
back via `carry_ratio_backward()`, not real data for that year).

Requires a ratio to exist for the **earliest** year in `year_files` — use
`carry_ratio_backward()` first if Atlas doesn't cover it, or this raises
a `ValueError`.

Pass `summary_df` if you already have one from `run_all_years()` for the
*same region* to avoid recomputing it. Note that calling this for a
different region than one you've already summarized (e.g. `run_all_years`
for "Atlanta MPO" followed by `cumulative_totals` for "Atlanta MSA")
means the diff pipeline runs a second time internally, once per region —
expected, but worth knowing if runtime becomes a concern with larger
files.

### `plot_summary(summary_df, region, save_path=None)`
Stacked bar chart (light/medium/heavy per year) from `run_all_years()`'s
output. Saves to `save_path` if given.

## Step-by-step usage

1. **Get your Atlas export.** Download the raw "EV Sales and Market Share"
   data from [Atlas Public Policy's State EV Summary Dashboard](https://www.atlasevhub.com/market-data/state-ev-summary-dashboard/) for Georgia, save it as an
   `.xlsx` in your working directory.

2. **Get your DRIVES files.** Run the scraper notebook for each year you
   want, or gather CSVs you already have. You need at minimum two
   consecutive years to get any output — more years gives you a longer
   time series.

3. **Load and prep the ratios:**
   ```python
   ratios = duty_class_ratios("EV_Sales_and_Market_Share.xlsx")
   flag_partial_years("EV_Sales_and_Market_Share.xlsx")
   ```
   Check the printed output for any "PARTIAL" warnings before trusting
   that year's ratio.

4. **Fill in any years Atlas doesn't cover**, if needed:
   ```python
   carry_ratio_backward(ratios, missing_year=2021, source_year=2022)
   carry_ratio_backward(ratios, missing_year=2020, source_year=2022)
   ```
   Only do this for years before Atlas's data starts (2022). Don't use it
   to paper over a year Atlas *should* have but is missing for another
   reason — track that down instead.

5. **Point at your DRIVES files:**
   ```python
   year_files = {
       2020: "registered_vehicles_by_county_2020.csv",
       2021: "registered_vehicles_by_county_2021.csv",
       2022: "registered_vehicles_by_county_2022.csv",
       2023: "registered_vehicles_by_county_2023.csv",
       2024: "registered_vehicles_by_county_2024.csv",
       2025: "registered_vehicles_by_county_04-2025.csv",
       2026: "registered_vehicles_by_county_07-2026.csv",
   }
   ```

6. **Run it for your region:**
   ```python
   summary = run_all_years(year_files, "Atlanta MPO", ratios)
   ```
   Read the printed warnings as you go — missing counties, negative EV
   diffs, and skipped years all print here. Don't skip past them.

7. **Plot it:**
   ```python
   plot_summary(summary, "Atlanta MPO", save_path="atlanta_mpo_ev_duty_class.png")
   ```

8. **Get a total, not just additions, if you need it:**
   ```python
   totals = cumulative_totals(year_files, "Atlanta MPO", ratios, summary_df=summary)
   ```
   This is a separate question from the summary above — `run_all_years`
   tells you how many EVs were *added* each year, this tells you how many
   are on the road *in total* as of your most recent file. Pass
   `summary_df=summary` to skip recomputing it, but only if `summary` was
   built for the same region you're passing here.

9. **Check the output files** in your working directory:
   - `ev_registration_by_county_{region}_{year}.csv` — one per year-pair,
     county-level detail.
   - `ev_registration_summary_{region}.csv` — the full time series.
   - Your plot, if you saved one.

## Known limitations

- **Mixing snapshot types across years causes visible artifacts.** If one
  year's file is a fixed year-end snapshot and another is a live/current
  pull (e.g. because the official snapshot wasn't published yet), that
  year-pair's diff gets noisier — some counties may show implausible
  swings, including small negative EV counts. Check for and note this
  explicitly if it happens; don't silently accept the numbers.
- **County-level duplicate rows get dropped, not summed.** If a county
  appears twice with identical values, that's treated as a scraper repeat
  and one copy is discarded. If a county appears twice with *different*
  values, the script does NOT guess how to combine them — it prints a
  warning and leaves both rows in, so check those by hand.
- **The blank/statewide-total row.** Georgia has 159 counties, but the
  DRIVES county dropdown has 160 options — one produces a row with a blank
  `county` and a statewide total. This is dropped automatically.
- **Region definitions are whole-county only.** `total_vehicle`/`ev` come
  from DRIVES at the whole-county level, but the real Atlanta MPO/MPA
  boundary only partially includes several counties. Whole-county
  filtering will over- or under-count vehicles in those counties relative
  to the officially adopted boundary — confirm the current region
  definitions against ARC's own adopted boundary documents rather than
  assuming the hardcoded county lists in this script stay accurate over
  time.
- **The `pct_light_duty_of_total_added` percentage is sensitive to swings
  in TOTAL vehicle registrations, not just EV adoption.** A year with an
  unusually large or small denominator (e.g. a post-2020 rebound year)
  will move this percentage even when EV growth itself is perfectly
  normal — don't read a dip or spike in this number as an EV-specific
  signal without checking the denominator first.
