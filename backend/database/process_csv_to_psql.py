import pandas as pd

INPUT_FILE = ""
OUTPUT_FILE = ""
METRIC_NAME = ""

df = pd.read_csv(INPUT_FILE)
meta_cols = [
    "RegionID",
    "RegionName",
    "RegionType",
    "StateName",
    "SizeRank",
]  # housing_time_series table has these columns
date_cols = [col for col in df.columns if col not in meta_cols]

df_long = df.melt(id_vars=meta_cols, value_vars=date_cols, var_name="date", value_name="value")

df_long["date"] = pd.to_datetime(df_long["date"])
df_long["metric"] = METRIC_NAME
df_long = df_long.dropna(subset=["value"])
df_long = df_long[["RegionID", "RegionName", "RegionType", "StateName", "metric", "date", "value"]]
df_long.to_csv(OUTPUT_FILE, index=False)
print(f"Long-format CSV written to {OUTPUT_FILE}")
