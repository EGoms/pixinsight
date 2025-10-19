#!/usr/bin/env python3

import argparse
import logging
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta
import re
import subprocess

from rich.console import Console

console = Console()

# Constants
BASE_DIR = Path.home() / "stellar"
CONSOLIDATED_DIR = BASE_DIR / "consolidated"
CALIBRATION_DIR = BASE_DIR / "calibration"
ORGANIZED_DIR = BASE_DIR / "organized"

FILTERS = ["L", "R", "G", "B", "S", "H", "O"]
AVAILABLE_DARK_TEMPS = ["0C", "-10C", "-20C"]


def setup_logging(verbosity=1):
    level = logging.WARNING
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)-8s %(message)s",
        level=level,
        datefmt="%H:%M:%S",
    )


def run_cmd(msg, dry_run):
    if dry_run:
        console.print(f"[yellow][DRY RUN][/yellow] {msg}")
    else:
        console.print(f"[green]{msg}[/green]")


def get_epoch(date_str, time_str):
    """
    date_str: yyyymmdd
    time_str: HHMMSS
    """
    # Use GNU date if available; else fallback to Python
    try:
        out = subprocess.check_output(
            ["gdate", "-d", f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}", "+%s"]
        )
        return int(out.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        dt = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
        return int(dt.timestamp())


def closest_temp(target_temp):
    """Return closest int temp from AVAILABLE_DARK_TEMPS"""
    try:
        target = float(target_temp)
    except ValueError:
        return None
    candidates = [float(t.rstrip("C")) for t in AVAILABLE_DARK_TEMPS]
    closest = min(candidates, key=lambda x: abs(x - target))
    return int(closest)


def parse_light_filename(fname_noext):
    """
    Parse light FIT/XISF filename parts from naming scheme:
    TYPE_OBJECT_EXPOSURE_BIN_CAMERA_FILTER_GAIN_DATETIME_TEMP_NUMBER
    Example: Light_M42_120s_BIN-1_6248x4176_L_GAIN-100_20230922-213015_-10.0C_001

    Returns dict with keys:
        type, object, exposure (float seconds), bin, camera, filter, gain (str), date (yyyymmdd),
        time (HHMMSS), temp (float), number (str)
    """

    parts = fname_noext.split("_")
    if len(parts) < 10:
        logging.warning(f"Filename parts less than expected: {fname_noext}")
        return None

    # Extract parts based on position
    TYPE = parts[0]
    OBJECT = parts[1]
    try:
        EXPOSURE = float(parts[2].rstrip("s"))
    except Exception:
        logging.warning(f"Invalid exposure in filename: {parts[2]}")
        return None
    BIN = parts[3]
    CAMERA = parts[4]
    FILTER = parts[5]
    # gain is like GAIN-100
    gain_match = re.match(r"gain-?(\d+)", parts[6], re.IGNORECASE)
    if not gain_match:
        logging.warning(f"Invalid gain format in filename: {parts[6]}")
        return None
    GAIN = gain_match.group(1)
    # datetime like 20230922-213015
    datetime_str = parts[7]
    if "-" not in datetime_str:
        logging.warning(f"Invalid datetime format in filename: {datetime_str}")
        return None
    DATE, TIME = datetime_str.split("-")
    # temp like -10.0C
    temp_str = parts[8]
    if not temp_str.endswith("C"):
        logging.warning(f"Invalid temp format in filename: {temp_str}")
        return None
    try:
        TEMP = float(temp_str[:-1])
    except Exception:
        logging.warning(f"Invalid temp value: {temp_str}")
        return None
    NUMBER = parts[9]

    return {
        "type": TYPE,
        "object": OBJECT,
        "exposure": EXPOSURE,
        "bin": BIN,
        "camera": CAMERA,
        "filter": FILTER,
        "gain": GAIN,
        "date": DATE,
        "time": TIME,
        "temp": TEMP,
        "number": NUMBER,
    }


def consolidate(src_dir: Path, dry_run=False):
    if not src_dir.exists() or not src_dir.is_dir():
        console.print(f"[red]Source directory {src_dir} does not exist or not a directory[/red]")
        sys.exit(1)

    CONS_DIR = CONSOLIDATED_DIR
    CONS_DIR.mkdir(parents=True, exist_ok=True)

    for file in src_dir.rglob("*.fit"):
        fname = file.name
        fname_noext = file.stem

        # Parse filename
        parts = fname_noext.split("_")
        if len(parts) < 9:
            logging.warning(f"Skipping file with unexpected filename format: {fname}")
            continue

        TYPE = parts[0]

        if TYPE == "Flat":
            OBJECT = "Flat"
            # parts: Flat_EXPOSURE_BIN_CAMERA_FILTER_GAIN_DATETIME_TEMP_NUMBER
            # so unpack accordingly
            try:
                _, EXPOSURE, BIN, CAMERA, FILTER, GAIN, DATETIME, TEMP, NUMBER = parts
            except ValueError:
                logging.warning(f"Unexpected Flat filename format: {fname_noext}")
                continue
        elif TYPE == "Dark":
            OBJECT = "Dark"
            FILTER = "Dark"
            try:
                _, EXPOSURE, BIN, CAMERA, FILTER, GAIN, DATETIME, TEMP, NUMBER = parts
            except ValueError:
                logging.warning(f"Unexpected Dark filename format: {fname_noext}")
                continue
        else:
            try:
                _, OBJECT, EXPOSURE, BIN, CAMERA, FILTER, GAIN, DATETIME, TEMP, NUMBER = parts
            except ValueError:
                logging.warning(f"Unexpected Light filename format: {fname_noext}")
                continue

        # Validate TYPE
        if TYPE not in ["Light", "Flat", "Dark", "Bias"]:
            continue

        # Validate FILTER
        if FILTER not in FILTERS and TYPE != "Dark":
            continue

        # Clean values
        EXPOSURE_VAL = float(EXPOSURE.rstrip("s"))
        GAIN_VAL = GAIN.lstrip("gain").lstrip("GAIN-")  # just in case
        TEMP_VAL = TEMP.rstrip("C")

        # Extract DATE, TIME from DATETIME
        if "-" not in DATETIME:
            logging.warning(f"Invalid datetime field: {DATETIME}")
            continue
        DATE, TIME = DATETIME.split("-")

        file_epoch = get_epoch(DATE, TIME)
        day1_noon = get_epoch(DATE, "120100")
        # Day 2 noon = day1 + 1 day at noon
        day2_date = (datetime.strptime(DATE, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        day2_noon = get_epoch(day2_date, "120000")

        if day1_noon <= file_epoch < day2_noon:
            group_date = DATE
        else:
            group_date = (datetime.strptime(DATE, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")

        if TYPE == "Dark":
            target_dir = CONS_DIR / "Dark" / GAIN / str(int(EXPOSURE_VAL))
        else:
            target_dir = CONS_DIR / OBJECT / FILTER / group_date / str(int(EXPOSURE_VAL))

        if dry_run:
            console.print(f"[yellow][DRY RUN][/yellow] mkdir -p {target_dir}")
            console.print(f"[yellow][DRY RUN][/yellow] mv {file} -> {target_dir}")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file), target_dir)

    console.print("[green]Consolidation Complete.[/green]")


def organize(object_name: str, dry_run=False):
    obj_dir = CONSOLIDATED_DIR / object_name
    if not obj_dir.exists():
        console.print(f"[red]Object folder '{obj_dir}' does not exist.[/red]")
        sys.exit(1)

    output_dir = ORGANIZED_DIR / object_name
    if dry_run:
        console.print(f"[yellow][DRY RUN][/yellow] mkdir -p {output_dir}")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Collect unique dates from consolidated structure under filters
    dates = set()
    for filt in FILTERS:
        filter_dir = obj_dir / filt
        if filter_dir.exists():
            for date_dir in filter_dir.iterdir():
                if date_dir.is_dir():
                    dates.add(date_dir.name)
    if not dates:
        console.print(f"[red]No observation dates found for object '{object_name}'.[/red]")
        return

    # Collect light file metadata to gather gains, temps, exposures used
    used_combos = set()  # (gain:str, temp:float, exposure:float)

    # Create nights
    night_count = 1
    for date in sorted(dates):
        night_dir = output_dir / f"night {night_count}"
        lights_dir = night_dir / "lights"
        flats_dir = night_dir / "flats"

        if dry_run:
            console.print(f"[yellow][DRY RUN][/yellow] mkdir -p {lights_dir}")
            console.print(f"[yellow][DRY RUN][/yellow] mkdir -p {flats_dir}")
        else:
            lights_dir.mkdir(parents=True, exist_ok=True)
            flats_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"Creating {night_dir} for date {date}")

        # Copy lights
        for filt in FILTERS:
            filt_date_dir = obj_dir / filt / date
            if filt_date_dir.exists():
                for exptime_dir in filt_date_dir.iterdir():
                    if exptime_dir.is_dir():
                        # Copy light files to lights_dir
                        for file in exptime_dir.glob("*"):
                            if file.suffix.lower() not in [".fit", ".fits", ".xisf"]:
                                continue
                            # Parse gain/temp/exposure from filename for combo
                            parsed = parse_light_filename(file.stem)
                            if parsed is None:
                                continue
                            used_combos.add(
                                (parsed["gain"], parsed["temp"], parsed["exposure"])
                            )
                            if dry_run:
                                console.print(f"[yellow][DRY RUN][/yellow] copy {file} -> {lights_dir}")
                            else:
                                shutil.copy(file, lights_dir)

        # Copy flats (.xisf)
        for filt in FILTERS:
            flat_dir = CONSOLIDATED_DIR / "Flat" / filt / date
            if flat_dir.exists():
                for flat_file in flat_dir.glob("*.xisf"):
                    if dry_run:
                        console.print(f"[yellow][DRY RUN][/yellow] copy {flat_file} -> {flats_dir}")
                    else:
                        shutil.copy(flat_file, flats_dir)

        night_count += 1

    # After nights created, copy bias and darks once per unique gain/temp/exposure combo
    bias_dir = CALIBRATION_DIR / "bias"
    darks_base_dir = CALIBRATION_DIR / "darks"
    calibration_out_dir = output_dir
    if dry_run:
        console.print(f"[yellow][DRY RUN][/yellow] mkdir -p {calibration_out_dir}")
    else:
        calibration_out_dir.mkdir(exist_ok=True)

    # Copy biases (one per gain)
    copied_biases = set()
    for gain, _, _ in used_combos:
        if gain in copied_biases:
            continue
        bias_gain_dir = bias_dir / gain
        if not bias_gain_dir.exists():
            logging.warning(f"No bias directory for gain={gain} at {bias_gain_dir}")
            continue
        # Copy all files in bias_gain_dir
        for bias_file in bias_gain_dir.glob("*"):
            if dry_run:
                console.print(f"[yellow][DRY RUN][/yellow] copy {bias_file} -> {calibration_out_dir}")
            else:
                shutil.copy(bias_file, calibration_out_dir)
            logging.info(f"Copied bias file: {bias_file.name}")
        copied_biases.add(gain)

    # Copy darks (per gain/temp/exposure)
    for gain, temp, exposure in used_combos:
        temp_int = closest_temp(temp)
        if temp_int is None:
            logging.warning(f"Invalid light temp: {temp}")
            continue
        matched_temp = f"{temp_int}C"
        dark_temp_dir = darks_base_dir / gain / matched_temp
        if not dark_temp_dir.exists():
            logging.warning(f"No dark temp directory: {dark_temp_dir}")
            continue

        exp_str = f"EXPOSURE-{exposure:.2f}s"
        matched_files = [f for f in dark_temp_dir.glob("*.xisf") if exp_str in f.name]

        if not matched_files:
            logging.warning(f"No darks for gain={gain}, temp={matched_temp}, exposure={exposure}")
            continue

        for dark_file in matched_files:
            if dry_run:
                console.print(f"[yellow][DRY RUN][/yellow] copy {dark_file} -> {calibration_out_dir}")
            else:
                shutil.copy(dark_file, calibration_out_dir)
            logging.info(f"Copied dark: {dark_file.name}")

    console.print(f"[green]Organizing complete for {object_name}. Output: {output_dir}[/green]")

def main():
    parser = argparse.ArgumentParser(description="Consolidate or organize astronomical FITS/XISF files.")
    parser.add_argument("mode", choices=["consolidate", "organize"], help="Operation mode.")
    parser.add_argument("--src", type=Path, help="Source directory for consolidate mode.")
    parser.add_argument("--object", type=str, help="Object name for organize mode.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without file operations.")
    parser.add_argument("-v", "--verbose", action="count", default=1, help="Increase verbosity level (use -v, -vv)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (warnings and errors only)")

    args = parser.parse_args()

    # Adjust verbosity
    if args.quiet:
        verbosity = 0
    else:
        verbosity = args.verbose

    setup_logging(verbosity)

    if args.mode == "consolidate":
        if not args.src:
            console.print("[red]Error:[/red] --src is required for consolidate mode.")
            sys.exit(1)
        consolidate(args.src, args.dry_run)
    elif args.mode == "organize":
        if not args.object:
            console.print("[red]Error:[/red] --object is required for organize mode.")
            sys.exit(1)
        organize(args.object, args.dry_run)

if __name__ == "__main__":
    main()
