"""
poerev.py – Steam reviews data utilities & quick‑stats

This script can now operate **offline** by reading the previously‑saved review CSVs
(`positive.csv` and `negative.csv`). It still contains the original network
fetch helpers so you can switch back to live‑polling later if desired.

Key additions
-------------
* **load_reviews_from_csv()** – returns the positive & negative review frames
  from local disk.
* **_summarise()** – upgraded so it works with either raw API data or the CSVs
  (which already have flattened author fields). Adds several new metrics.
* **write_reviews_to_txt() / count_occurrences()** – dumps review bodies to
  plain‑text files and does quick keyword frequency checks.

Invoke the module directly to print summary tables and (re)generate
`positive.txt` and `negative.txt`.
"""

from __future__ import annotations

import os
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests

# ------------------------------------------------------------------------------------------ #
# Constants & config
# ------------------------------------------------------------------------------------------ #
TOTAL_REVIEWS = 167_399
REVIEWS_PER_PAGE = 100
PAGES = TOTAL_REVIEWS // REVIEWS_PER_PAGE + 1

POE2ID = "2694490"
BASE_URL = "https://store.steampowered.com/appreviews/{appid}"

DEFAULT_PARAMS = {
    "json": 1,
    "language": "all",
    "filter": "recent",
    "num_per_page": REVIEWS_PER_PAGE,
    "review_type": "all",
    "purchase_type": "all",
    "filter_offtopic_activity": 0,
}

# Launch: 6 Dec 2024 11:00 PST (19:00 UTC)
LAUNCH_DATE = datetime( 2024, 12, 6, 11, 0, 0 )

# ------------------------------------------------------------------------------------------ #
# Time helpers
# ------------------------------------------------------------------------------------------ #


def _hours_since_launch( csv_path: str | Path = "./positive.csv" ) -> float:
    """Hours between **launch** and the last update of *csv_path*."""
    data_time = datetime.fromtimestamp( Path( csv_path ).stat().st_mtime )
    return ( data_time - LAUNCH_DATE ).total_seconds() / 3600 # hours‑float


def _hours( minutes: float ) -> str:
    """Convert minutes → rounded hours string (e.g. 293 → "5h")."""
    return f"{round(minutes / 60)}h"


# ------------------------------------------------------------------------------------------ #
# Data transforms
# ------------------------------------------------------------------------------------------ #


def _normalize_timestamps( df: pd.DataFrame ) -> pd.DataFrame:
    ts_cols = [
        "timestamp_created",
        "timestamp_updated",
        "last_played",
    ]
    for col in ts_cols:
        if col in df.columns:
            df[ col ] = pd.to_datetime( df[ col ], unit = "s", errors = "coerce" )
    return df


def _flatten_author( df: pd.DataFrame ) -> pd.DataFrame:
    """If the DataFrame still has a nested *author* column, flatten it."""
    if "author" in df.columns:
        df = df.join( pd.json_normalize( df.pop( "author" ) ) )
    return df


def _summarise( df: pd.DataFrame, label: str ) -> pd.DataFrame:
    df = _flatten_author( df.copy() )
    df = _normalize_timestamps( df )

    if "playtime_since_review" not in df.columns:
        df[ "playtime_since_review" ] = df.playtime_forever - df.playtime_at_review

    active20 = df.playtime_last_two_weeks >= 600 # ≥10 h
    active80 = df.playtime_last_two_weeks >= 2400 # ≥40 h

    stats = {
        "Games Owned": int( round( df.num_games_owned.mean() ) ),
        "Reviews Written": int( round( df.num_reviews.mean() ) ),
        "Total Hours": _hours( df.playtime_forever.mean() ),
        "Hours Last 2 Wks": _hours( df.playtime_last_two_weeks.mean() ),
        "Hours Since Review": _hours( df.playtime_since_review.mean() ),
        "% 0h Last 2 Wks": f"{( df.playtime_last_two_weeks == 0 ).mean() * 100:.1f}%",
        "% 0h Since Review": f"{( df.playtime_since_review == 0 ).mean() * 100:.1f}%",
        "% >=10h Last 2 Wks": f"{active20.mean() * 100:.1f}%",
        "% >=40h Last 2 Wks": f"{active80.mean() * 100:.1f}%",
    }

    lang_counts = df.language.str.lower().value_counts()
    lang_pct = ( lang_counts / len( df ) * 100 ).round( 1 )

    lines = [ f"{label} reviews: {len(df):,}", "" ]

    for k, v in stats.items():
        lines.append( f"{k:<24} {v}" )

    lines.extend( [ "", "Language Breakdown:" ] )
    for lang, pct in lang_pct.items():
        lines.append( f"  {lang:<12} {pct:>5}%  ({lang_counts[lang]})" )

    Path( f"{label.lower()}_summary.txt" ).write_text( "\n".join( lines ), encoding = "utf-8" )

    return df


# ------------------------------------------------------------------------------------------ #
# Local‑file helpers
# ------------------------------------------------------------------------------------------ #


def load_reviews_from_csv( pos_path: str | Path = "positive.csv",
                           neg_path: str | Path = "negative.csv" ) -> Tuple[ pd.DataFrame, pd.DataFrame ]:
    """Read *positive* and *negative* review CSVs from disk."""
    pos = pd.read_csv( pos_path )
    neg = pd.read_csv( neg_path )
    return pos, neg


def write_reviews_to_txt( df: pd.DataFrame, outfile: str | Path ):
    """Dump the *review* column to *outfile*, one review per line."""
    Path( outfile ).write_text( "\n".join( df[ "review" ].fillna( "" ).astype( str ) ), encoding = "utf‑8" )


WORD_RE = re.compile( r"[A‑Za‑z]+", re.I )


def count_occurrences( text_file: str | Path, term: str ) -> int:
    """Return (case‑insensitive, partial) occurrence count of *term* in *text_file*."""
    with open( text_file, "r", encoding = "utf‑8", errors = "ignore" ) as f:
        text = f.read().lower()
    return len( re.findall( re.escape( term.lower() ), text ) )


# ------------------------------------------------------------------------------------------ #
# Original network fetchers (unused when working offline)
# ------------------------------------------------------------------------------------------ #


def _fetch( appid: str, cursor: str = "*" ) -> dict:
    params = DEFAULT_PARAMS | { "cursor": cursor }
    resp = requests.get( BASE_URL.format( appid = appid ), params = params, timeout = 30 )
    resp.raise_for_status()
    return resp.json()


def get_reviews( appid: str, pages: int = 5, pause: float = 0.5 ) -> pd.DataFrame:
    reviews, cursor = [], "*"
    for _ in range( pages ):
        data = _fetch( appid, cursor )
        reviews.extend( data.get( "reviews", [] ) )
        cursor = data.get( "cursor" )
        if not cursor or not data[ "reviews" ]:
            break
        time.sleep( pause ) # be nice to Steam’s servers
    return pd.DataFrame( reviews )


# ------------------------------------------------------------------------------------------ #
# CLI / script entry point
# ------------------------------------------------------------------------------------------ #


def main():
    # Work entirely from the on‑disk CSVs
    pos_df, neg_df = load_reviews_from_csv()

    pos_df = _summarise( pos_df, "Positive" )
    neg_df = _summarise( neg_df, "Negative" )


if __name__ == "__main__":
    main()
"""
REFINE TASKS
1. Don't print the summary data to console -- instead, write it to a text file with basic formatting.
2. Expand the language summary data to break down the % of reviews by language for positive and negative.
3. Add a metric to determine what percentage of players writing certain types of reviews are "active" -- calculate the
% of players by review type who have played at least 20 total hours in the last two weeks.
"""
