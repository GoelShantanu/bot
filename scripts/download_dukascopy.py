"""Download free 1-minute bid/ask candles from Dukascopy's public datafeed.

Dukascopy publishes one LZMA-compressed file per pair, day and side:

    http://datafeed.dukascopy.com/datafeed/{PAIR}/{YYYY}/{MM-1}/{DD}/{BID|ASK}_candles_min_1.bi5

Each file holds up to 1,440 records of 24 bytes (big-endian):
    uint32 seconds since 00:00 UTC, int32 open, close, low, high (price x
    point factor), float32 volume.

Raw files are cached under ``<out>/raw`` so the download can be stopped and
resumed. ``--build`` then writes one gzipped CSV per pair and year:

    <out>/<PAIR>_1m_<YEAR>.csv.gz
    columns: time_utc, bid_open, bid_high, bid_low, bid_close,
             ask_open, ask_high, ask_low, ask_close, volume

Minutes with zero volume on both sides (market closed / no quotes) are dropped.

Examples:
    python scripts/download_dukascopy.py --start 2021-10-01 --end 2026-09-30
    python scripts/download_dukascopy.py --build
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import lzma
import os
import struct
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "NZDUSD", "USDCHF"]
POINT = {"USDJPY": 1e3}  # everything else 1e5
BASE_URL = "http://datafeed.dukascopy.com/datafeed"  # https is blocked on some networks
RECORD = struct.Struct(">5if")


def raw_path(out: str, pair: str, day: date, side: str) -> str:
    return os.path.join(out, "raw", pair, f"{day:%Y%m%d}_{side}.bi5")


def fetch(out: str, pair: str, day: date, side: str, retries: int = 4) -> str:
    """Download one day file (skips files already cached). Returns a status."""
    path = raw_path(out, pair, day, side)
    if os.path.exists(path):
        return "cached"
    url = f"{BASE_URL}/{pair}/{day.year}/{day.month - 1:02d}/{day.day:02d}/{side}_candles_min_1.bi5"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".part"
            with open(tmp, "wb") as fh:
                fh.write(payload)
            os.replace(tmp, path)
            return "ok"
        except urllib.error.HTTPError as exc:
            if exc.code == 404:  # no data for that day
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, "wb").close()
                return "404"
            error = exc
        except Exception as exc:  # network hiccup: back off and retry
            error = exc
        time.sleep(2 ** attempt)
    return f"failed: {error}"


def trading_days(start: date, end: date):
    """Sunday–Friday (forex trades from Sunday evening to Friday evening UTC)."""
    day = start
    while day < end:
        if day.weekday() != 5:  # skip Saturday
            yield day
        day += timedelta(days=1)


def download(out: str, pairs: list[str], start: date, end: date, workers: int) -> None:
    jobs = [(p, d, s) for p in pairs for d in trading_days(start, end) for s in ("BID", "ASK")]
    todo = [j for j in jobs if not os.path.exists(raw_path(out, *j))]
    print(f"{len(jobs)} files in range, {len(jobs) - len(todo)} cached, {len(todo)} to download "
          f"with {workers} workers", flush=True)
    failed = []
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, out, *job): job for job in todo}
        for n, future in enumerate(cf.as_completed(futures), 1):
            status = future.result()
            if status.startswith("failed"):
                failed.append((futures[future], status))
            if n % 200 == 0 or n == len(todo):
                rate = n / (time.time() - t0)
                eta = (len(todo) - n) / rate / 60 if rate else 0
                print(f"  {n}/{len(todo)} done, {len(failed)} failed, ~{eta:.0f} min left", flush=True)
    for job, status in failed[:20]:
        print("FAILED", job, status)
    if failed:
        print(f"{len(failed)} files failed — re-run the same command to retry them.")


def decode(path: str, pair: str, day: date) -> dict[int, tuple]:
    """Return {epoch_seconds: (open, high, low, close, volume)}."""
    payload = open(path, "rb").read()
    if not payload:
        return {}
    data = lzma.decompress(payload)
    factor = POINT.get(pair, 1e5)
    midnight = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
    rows = {}
    for offset in range(0, len(data) - len(data) % RECORD.size, RECORD.size):
        secs, o, c, lo, hi, vol = RECORD.unpack_from(data, offset)
        rows[midnight + secs] = (o / factor, hi / factor, lo / factor, c / factor, vol)
    return rows


def build(out: str, pairs: list[str]) -> None:
    for pair in pairs:
        raw_dir = os.path.join(out, "raw", pair)
        if not os.path.isdir(raw_dir):
            continue
        days = sorted({name[:8] for name in os.listdir(raw_dir) if name.endswith(".bi5")})
        by_year: dict[int, list[str]] = {}
        for stamp in days:
            day = datetime.strptime(stamp, "%Y%m%d").date()
            bid = decode(raw_path(out, pair, day, "BID"), pair, day) if os.path.exists(raw_path(out, pair, day, "BID")) else {}
            ask = decode(raw_path(out, pair, day, "ASK"), pair, day) if os.path.exists(raw_path(out, pair, day, "ASK")) else {}
            for ts in sorted(bid.keys() & ask.keys()):
                b, a = bid[ts], ask[ts]
                if b[4] == 0 and a[4] == 0:
                    continue
                line = (f"{datetime.fromtimestamp(ts, timezone.utc):%Y-%m-%d %H:%M},"
                        f"{b[0]},{b[1]},{b[2]},{b[3]},{a[0]},{a[1]},{a[2]},{a[3]},{round(b[4] + a[4], 2)}")
                by_year.setdefault(day.year, []).append(line)
        for year, lines in sorted(by_year.items()):
            path = os.path.join(out, f"{pair}_1m_{year}.csv.gz")
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                fh.write("time_utc,bid_open,bid_high,bid_low,bid_close,"
                         "ask_open,ask_high,ask_low,ask_close,volume\n")
                fh.write("\n".join(lines) + "\n")
            print(f"wrote {path}: {len(lines)} candles", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pairs", nargs="+", default=PAIRS)
    parser.add_argument("--start", default="2021-10-01")
    parser.add_argument("--end", default=None, help="exclusive, default today (UTC)")
    parser.add_argument("--out", default="data/dukascopy")
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--build", action="store_true", help="only build CSVs from cached raw files")
    args = parser.parse_args()

    if not args.build:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end) if args.end else datetime.now(timezone.utc).date()
        download(args.out, args.pairs, start, end, args.workers)
    build(args.out, args.pairs)


if __name__ == "__main__":
    sys.exit(main())
