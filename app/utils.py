from dateutil.relativedelta import relativedelta
from datetime import datetime
from typing import List
import pandas as pd

from app.loc_access import LocDataAccess


def infer_shards_for_date(date_str: str, shard_labels: List[str]) -> str:
    """
    Given a date, return the first shard label where the date falls within the shard window.

    Args:
        date_str (str): Date string (e.g. "2019-03-15")
        shard_labels (List[str]): List of shard labels (e.g., ["2019-01-01_2019-02-28", ...])

    Returns:
        str: Matching shard label that contains the date (inclusive range)

    Raises:
        ValueError: If the date doesn't fall within any shard.
    """
    try:
        query_date = pd.to_datetime(date_str)

        for label in shard_labels:
            try:
                start_str, end_str = label.split("_")
                start_date = pd.to_datetime(start_str)
                end_date = pd.to_datetime(end_str)

                if start_date <= query_date <= end_date:
                    return label
            except Exception as e:
                print(f"⚠️ Skipping malformed label: {label} | Error: {e}")
                continue

        raise ValueError(f"No shard found for date: {date_str}")
    except Exception as e:
        raise ValueError(f"Invalid date input: {date_str}") from e
    
def infer_shards_for_date_range(start_date_str: str, end_date_str: str, shard_labels: List[str]) -> List[str]:
    """
    Given a date range, return all shard labels that overlap with this range.

    Args:
        start_date_str (str): Start date of the query (e.g. "2019-01-01")
        end_date_str (str): End date of the query (e.g. "2019-04-30")
        shard_labels (List[str]): List of shard labels (e.g., ["2019-01-01_2019-02-28", "2019-03-01_2019-04-30", ...])

    Returns:
        List[str]: Shard labels that overlap with the query date range.
    """
    try:
        start_query = pd.to_datetime(start_date_str)
        end_query = pd.to_datetime(end_date_str)

        overlapping_shards = []
        for label in shard_labels:
            try:
                start_str, end_str = label.split("_")
                shard_start = pd.to_datetime(start_str)
                shard_end = pd.to_datetime(end_str)

                if shard_start <= end_query and shard_end >= start_query:
                    overlapping_shards.append(label)
            except Exception as e:
                print(f"⚠️ Skipping malformed label: {label} | Error: {e}")
                continue

        return overlapping_shards
    except Exception as e:
        raise ValueError(f"Invalid date range input: {start_date_str} to {end_date_str}") from e
    

def compute_relative_age(df):
    today = pd.Timestamp("today")
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df["relative_age"] = (today - df["dob"]).dt.days / 365.25
    df["relative_age"] = df["relative_age"].fillna(df["relative_age"].mean())
    return df

def enrich_location(df):
    loc_access = LocDataAccess.get_instance()
    df["dep_lon"], df["dep_lat"] = zip(*df["iata_o"].map(loc_access.get_airport_lon_lat_by_iata))
    df["arr_lon"], df["arr_lat"] = zip(*df["iata_d"].map(loc_access.get_airport_lon_lat_by_iata))

    df["dep_lon"] = df["dep_lon"].fillna(0.0).infer_objects(copy=False)
    df["dep_lat"] = df["dep_lat"].fillna(0.0).infer_objects(copy=False)
    df["arr_lon"] = df["arr_lon"].fillna(0.0).infer_objects(copy=False)
    df["arr_lat"] = df["arr_lat"].fillna(0.0).infer_objects(copy=False)
    return df

