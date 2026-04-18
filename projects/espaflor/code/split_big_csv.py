"""
Split big CSV into batches of N rows.

Purpose:
    Odoo import UI throws "Content too large" when CSV has too many rows
    with base64 image data. Split into files of 100 rows each for reliable
    import.

Input:
    <INPUT_CSV> — any CSV with header row

Output:
    <INPUT_BASE>_batch_01.csv, _batch_02.csv, ...

Usage:
    python split_big_csv.py
    # or customize:
    INPUT_CSV="odoo_images_import.csv" BATCH_SIZE=100 python split_big_csv.py
"""

import csv
import os

INPUT_CSV = os.environ.get("INPUT_CSV", "odoo_images_import.csv")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))


def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    base = os.path.splitext(INPUT_CSV)[0]
    batch_num = 1
    rows_in_batch = 0
    batch_file = None
    batch_writer = None
    header = None
    total_rows = 0

    with open(INPUT_CSV, "r", encoding="utf-8", newline="") as f_in:
        reader = csv.reader(f_in)
        for idx, row in enumerate(reader):
            if idx == 0:
                header = row
                continue

            if rows_in_batch == 0:
                # open new batch file
                fname = f"{base}_batch_{batch_num:02d}.csv"
                batch_file = open(fname, "w", encoding="utf-8", newline="")
                batch_writer = csv.writer(batch_file)
                batch_writer.writerow(header)
                print(f"Writing {fname}")

            batch_writer.writerow(row)
            rows_in_batch += 1
            total_rows += 1

            if rows_in_batch >= BATCH_SIZE:
                batch_file.close()
                batch_num += 1
                rows_in_batch = 0
                batch_file = None
                batch_writer = None

        if batch_file:
            batch_file.close()

    total_batches = batch_num if rows_in_batch == 0 else batch_num
    print(f"\nDone. Split {total_rows} rows into {total_batches} batches of {BATCH_SIZE}.")
    print(f"Import each {base}_batch_XX.csv into Odoo one by one.")


if __name__ == "__main__":
    main()
