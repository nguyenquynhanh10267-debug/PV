"""
aps_apu_cleaner.py
===================

Ham/module de lam sach VA GOP nhieu file log dang "nhieu schema gop
trong 1 CSV" (kieu file APS-000258_YYYYMMDD_...csv, moi file = 1 ngay).

Dung cho ca thu muc (vi du 24-35 file, moi file 1 ngay) -> gop lai
thanh MOI Log Type MOT file CSV duy nhat, noi tiep theo thoi gian,
header chi xuat hien 1 lan o dau:

    from aps_apu_cleaner import process
    process("raw_logs/", "cleaned_data/")

Hoac chay tu dong lenh:

    python aps_apu_cleaner.py --input raw_logs/ --output cleaned_data/
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

CANDIDATE_ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin1"]

# Nhan dien 1 o la ngay-gio (vd '01/10/2025 0:00' hoac '0:00:00' o cuoi).
DATE_CELL_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}")


# --------------------------------------------------------------------------
# 1. Doc file tho
# --------------------------------------------------------------------------

def read_raw_rows(path: Path, encoding: Optional[str] = None,
                  delimiter: str = ",") -> Tuple[List[List[str]], str]:
    encodings = [encoding] if encoding else CANDIDATE_ENCODINGS
    last_err = None
    for enc in encodings:
        try:
            with open(path, encoding=enc, newline="") as f:
                rows = list(csv.reader(f, delimiter=delimiter))
            return rows, enc
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    raise ValueError(f"Khong doc duoc file {path} voi cac encoding {encodings}: {last_err}")


# --------------------------------------------------------------------------
# 2. Tach vung SCHEMA va vung DATA
# --------------------------------------------------------------------------

def find_data_start(rows: List[List[str]]) -> Optional[int]:
    """Tra ve chi so dong dau tien la du lieu that (TimeStamp dang ngay/gio).
    Tra ve None (khong raise loi) neu ca file khong co dong du lieu nao.
    """
    for i, r in enumerate(rows):
        if len(r) >= 3 and DATE_CELL_RE.match(r[2].strip()):
            return i
    return None


def extract_schema(rows: List[List[str]], data_start: int) -> Dict[str, List[str]]:
    schema: Dict[str, List[str]] = {}
    for r in rows[1:data_start]:
        if not r or not r[0].strip():
            continue
        log_type = r[0].strip()
        col_names = [c for c in r[3:] if c.strip() != ""]
        if col_names:
            schema[log_type] = col_names
    return schema


# --------------------------------------------------------------------------
# 3. Tach du lieu theo Log Type -> DataFrame (cho 1 file)
# --------------------------------------------------------------------------

def split_by_log_type(rows: List[List[str]], data_start: int,
                      schema: Dict[str, List[str]]) -> Dict[str, pd.DataFrame]:
    buckets: Dict[str, List[List[str]]] = defaultdict(list)
    for r in rows[data_start:]:
        if len(r) >= 3 and r[0].strip() in schema:
            buckets[r[0].strip()].append(r)

    raw_tables: Dict[str, pd.DataFrame] = {}
    for log_type, cols in schema.items():
        recs = buckets.get(log_type, [])
        if not recs:
            continue
        n = len(cols)
        data = []
        for r in recs:
            vals = r[3:3 + n]
            vals = vals + [""] * (n - len(vals))
            data.append([r[1], r[2]] + vals)
        raw_tables[log_type] = pd.DataFrame(data, columns=["System", "TimeStamp"] + cols)
    return raw_tables


# --------------------------------------------------------------------------
# 4. Chuan hoa 1 bang
# --------------------------------------------------------------------------

def clean_table(df: pd.DataFrame, log_type: str, dayfirst: bool = True) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "Log Type", log_type)
    df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], dayfirst=dayfirst, errors="coerce")

    value_cols = [c for c in df.columns if c not in ("Log Type", "System", "TimeStamp")]
    for c in value_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    ordered = ["Log Type", "System", "TimeStamp"] + value_cols
    return df[ordered]


# --------------------------------------------------------------------------
# 5. Doc 1 file -> dict {log_type: DataFrame da chuan hoa}
# --------------------------------------------------------------------------

def parse_file(path: Path, encoding: Optional[str] = None,
               dayfirst: bool = True) -> Dict[str, pd.DataFrame]:
    rows, _ = read_raw_rows(path, encoding=encoding)
    data_start = find_data_start(rows)
    if data_start is None:
        return {}

    schema = extract_schema(rows, data_start)
    if not schema:
        return {}

    raw_tables = split_by_log_type(rows, data_start, schema)
    return {lt: clean_table(df, lt, dayfirst=dayfirst) for lt, df in raw_tables.items()}


# --------------------------------------------------------------------------
# 6. Ham chinh: doc NHIEU file, GOP theo Log Type, luu ra dia
# --------------------------------------------------------------------------

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def process(input_path: str | Path, output_dir: str | Path,
            pattern: str = "*.csv",
            encoding: Optional[str] = None,
            dayfirst: bool = True) -> Dict[str, pd.DataFrame]:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_path.glob(pattern)) if input_path.is_dir() else [input_path]
    if not files:
        print(f"Khong tim thay file nao khop '{pattern}' trong {input_path}")
        return {}

    print(f"Tim thay {len(files)} file. Bat dau doc va gop...\n")

    merged: Dict[str, List[pd.DataFrame]] = defaultdict(list)
    skipped: List[Dict[str, str]] = []
    ok_count = 0

    for f in files:
        try:
            tables = parse_file(f, encoding=encoding, dayfirst=dayfirst)
        except Exception as e:
            print(f"[LOI] {f.name}: {e}")
            skipped.append({"File": f.name, "Ly do": str(e)})
            continue

        if not tables:
            print(f"[BO QUA] {f.name}: khong tim thay dong du lieu nao trong file nay.")
            skipped.append({"File": f.name, "Ly do": "Khong co dong du lieu (file rong hoac sai dinh dang)"})
            continue

        for log_type, df in tables.items():
            merged[log_type].append(df)
        ok_count += 1
        print(f"[OK] {f.name}: {len(tables)} loai log")

    if not merged:
        print("\nKhong gop duoc du lieu nao. Kiem tra lai file dau vao.")
        if skipped:
            pd.DataFrame(skipped).to_csv(output_dir / "skipped_files.csv", index=False)
        return {}

    final_tables: Dict[str, pd.DataFrame] = {}
    for log_type, df_list in merged.items():
        combined = pd.concat(df_list, ignore_index=True, sort=False)

        # Bo cot toan rong -- CHI bo neu rong tren TOAN BO du lieu da gop
        keep_always = {"Log Type", "System", "TimeStamp"}
        empty_cols = [c for c in combined.columns if c not in keep_always and combined[c].isna().all()]
        if empty_cols:
            combined = combined.drop(columns=empty_cols)

        combined = combined.sort_values(["System", "TimeStamp"]).reset_index(drop=True)
        final_tables[log_type] = combined

    # Luu ra dia: moi log type 1 file CSV duy nhat
    for log_type, df in final_tables.items():
        out_path = output_dir / f"{_slugify(log_type)}.csv"
        df.to_csv(out_path, index=False)

    # Bao cao tong hop
    quality_rows = []
    for log_type, df in final_tables.items():
        value_cols = [c for c in df.columns if c not in ("Log Type", "System", "TimeStamp")]
        missing_pct = df[value_cols].isna().mean().mean() * 100 if value_cols else np.nan
        quality_rows.append({
            "Log Type": log_type,
            "So dong (tat ca cac file)": len(df),
            "Tu ngay": df["TimeStamp"].min(),
            "Den ngay": df["TimeStamp"].max(),
            "% thieu TB cac cot": round(missing_pct, 2) if not np.isnan(missing_pct) else np.nan,
            "So dong trung lap": int(df.duplicated().sum()),
        })
    pd.DataFrame(quality_rows).to_csv(output_dir / "quality_report.csv", index=False)

    dict_rows = []
    for log_type, df in final_tables.items():
        for c in df.columns:
            dict_rows.append({"Log Type": log_type, "Cot": c, "Kieu du lieu": str(df[c].dtype)})
    pd.DataFrame(dict_rows).to_csv(output_dir / "data_dictionary.csv", index=False)

    if skipped:
        pd.DataFrame(skipped).to_csv(output_dir / "skipped_files.csv", index=False)

    print(f"\nHoan tat: {ok_count}/{len(files)} file duoc gop thanh cong.")
    if skipped:
        print(f"{len(skipped)} file bi bo qua -> xem chi tiet trong skipped_files.csv")
    print(f"Da luu {len(final_tables)} file (1 file / Log Type) vao: {output_dir.resolve()}")

    return final_tables


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Lam sach VA GOP nhieu file log dang nhieu-schema-gop-1-CSV (kieu APS/APU)."
    )
    p.add_argument("--input", "-i", required=True,
                   help="Duong dan 1 file CSV, hoac 1 thu muc chua nhieu file CSV.")
    p.add_argument("--output", "-o", required=True,
                   help="Thu muc se luu ket qua da gop (1 file CSV / Log Type).")
    p.add_argument("--pattern", default="*.csv",
                   help="Mau ten file khi --input la thu muc (mac dinh: *.csv).")
    p.add_argument("--encoding", default=None,
                   help="Ep encoding cu the (vd cp1252). Mac dinh: tu dong thu.")
    p.add_argument("--month-first", action="store_true",
                   help="Dung neu TimeStamp trong file la mm/dd/yyyy thay vi dd/mm/yyyy.")
    return p


def main(argv: Optional[List[str]] = None) -> None:
    args = _build_arg_parser().parse_args(argv)
    process(
        args.input,
        args.output,
        pattern=args.pattern,
        encoding=args.encoding,
        dayfirst=not args.month_first,
    )


if __name__ == "__main__":
    main()