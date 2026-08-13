"""
aps_apu_cleaner.py
===================

Ham/module tai su dung de lam sach cac file log dang "nhieu schema gop
trong 1 CSV" (kieu file APS-000258_...csv): moi Log Type co so cot va
y nghia cot khac nhau, dinh nghia o cac dong dau file, du lieu that
nam ben duoi.

Dung cho 1 file:
    from aps_apu_cleaner import process_file
    tables = process_file("APS-000258_20251001_000000.csv", "cleaned_data")

Dung cho nhieu file (vi du ca thu muc):
    from aps_apu_cleaner import batch_process
    batch_process("raw_logs/", "cleaned_data/")

Hoac chay truc tiep tu dong lenh:
    python aps_apu_cleaner.py --input raw_logs/ --output cleaned_data/
    python aps_apu_cleaner.py --input mot_file.csv --output cleaned_data/
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Cac encoding se thu lan luot cho den khi doc duoc file.
CANDIDATE_ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin1"]

# Regex nhan dien 1 o la ngay thang (dd/mm/yyyy hoac tuong tu) -> danh dau
# diem bat dau cua vung DU LIEU THAT (khac voi vung dinh nghia SCHEMA).
DATE_CELL_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}")


# --------------------------------------------------------------------------
# 1. Doc file tho
# --------------------------------------------------------------------------
def read_raw_rows(path: Path, encoding: Optional[str] = None,
                   delimiter: str = ",") -> tuple[List[List[str]], str]:
    """Doc toan bo file CSV tho thanh list-of-rows (list[str]).

    Neu khong chi dinh encoding, tu dong thu lan luot CANDIDATE_ENCODINGS.
    Tra ve (rows, encoding_da_dung) de biet file dung encoding gi.
    """
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
# 2. Tach vung SCHEMA (dinh nghia cot) va vung DATA (du lieu that)
# --------------------------------------------------------------------------

def find_data_start(rows: List[List[str]]) -> int:
    """Tim chi so dong dau tien la DU LIEU THAT (cot TimeStamp la 1 ngay
    thuc su, vi du '01/10/2025 0:00'), thay vi dinh nghia schema.

    Cach lam nay khong hard-code so dong schema (11 dong o file mau) de
    ham van chay dung neu file khac co nhieu/it Log Type hon.
    """
    for i, r in enumerate(rows):
        if len(r) >= 3 and DATE_CELL_RE.match(r[2].strip()):
            return i
    raise ValueError(
        "Khong tim thay dong du lieu nao co TimeStamp dang ngay/gio "
        "(vi du '01/10/2025 0:00'). Kiem tra lai dinh dang file dau vao."
    )

# trích xuất schema: {log_type: [col1, col2, ...]}
def extract_schema(rows: List[List[str]], data_start: int) -> Dict[str, List[str]]:
    """Doc cac dong tu sau dong mo ta chung (dong 1, index=1) cho toi truoc
    data_start: moi dong la 'Log Type;System;TimeStamp;ten_cot_1;ten_cot_2;...'
    """
    schema: Dict[str, List[str]] = {}
    for r in rows[1:data_start]:
        if not r or not r[0].strip():
            continue
        log_type = r[0].strip()
        col_names = [c for c in r[3:] if c.strip() != ""]
        if col_names:
            schema[log_type] = col_names
    if not schema:
        raise ValueError("Khong trich xuat duoc schema nao tu file. Kiem tra cau truc file dau vao.")
    return schema


# --------------------------------------------------------------------------
# 3. Tach du lieu theo Log Type -> DataFrame
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
# 4. Chuan hoa 1 bang: kieu du lieu, sap xep, tach Unit
# --------------------------------------------------------------------------

def clean_table(df: pd.DataFrame, log_type: str, dayfirst: bool = True) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "Log Type", log_type)

    df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], dayfirst=dayfirst, errors="coerce")

    value_cols = [c for c in df.columns if c not in ("Log Type", "System", "TimeStamp")]
    for c in value_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    

    ordered = ["Log Type", "System", "TimeStamp"] + value_cols
    df = df[ordered]
    df = df.sort_values(["System", "TimeStamp"]).reset_index(drop=True)
    return df

# xóa cột hoàn toàn trống (ngoại trừ "Log Type", "System", "TimeStamp")
def drop_fully_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep_always = {"Log Type", "System", "TimeStamp"}
    empty_cols = [c for c in df.columns if c not in keep_always and df[c].isna().all()]
    return df.drop(columns=empty_cols) if empty_cols else df


# --------------------------------------------------------------------------
# 5. Bao cao chat luong du lieu
# --------------------------------------------------------------------------

def quality_report_for_tables(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for log_type, df in tables.items():
        value_cols = [c for c in df.columns if c not in ("Log Type", "System", "TimeStamp")]
        missing_pct = df[value_cols].isna().mean().mean() * 100 if value_cols else np.nan
        rows.append({
            "Log Type": log_type,
            "So dong": len(df),
            "Tu ngay": df["TimeStamp"].min() if len(df) else pd.NaT,
            "Den ngay": df["TimeStamp"].max() if len(df) else pd.NaT,
            "% thieu TB cac cot": round(missing_pct, 2) if not np.isnan(missing_pct) else np.nan,
            "So dong trung lap (toan bo cot)": int(df.duplicated().sum()),
        })
    return pd.DataFrame(rows)

# tạo data dictionary: {Log Type, Cot, Kieu du lieu}
def data_dictionary_for_tables(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for log_type, df in tables.items():
        for c in df.columns:
            rows.append({"Log Type": log_type, "Cot": c, "Kieu du lieu": str(df[c].dtype)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 6. Ham xu ly toan bo 1 file -> luu ket qua ra thu muc
# --------------------------------------------------------------------------
# chuẩn hóa tên file
def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def process_file(input_path: str | Path, output_dir: str | Path,
                  encoding: Optional[str] = None,
                  save_per_table: bool = True,
                  dayfirst: bool = True) -> Dict[str, pd.DataFrame]:
    """Lam sach 1 file log va (mac dinh) luu ket qua ra output_dir.

    output_dir se co dang:
        output_dir/<ten_file_goc>/<log_type>.csv
        output_dir/<ten_file_goc>/data_dictionary.csv
        output_dir/<ten_file_goc>/quality_report.csv

    Tra ve dict {log_type: DataFrame} de dung tiep trong code (khong bat
    buoc phai doc lai file CSV vua luu).
    """
    input_path = Path(input_path)
    rows, used_encoding = read_raw_rows(input_path, encoding=encoding)

    data_start = find_data_start(rows)
    schema = extract_schema(rows, data_start)
    raw_tables = split_by_log_type(rows, data_start, schema)

    clean_tables: Dict[str, pd.DataFrame] = {}
    for log_type, df in raw_tables.items():
        cleaned = clean_table(df, log_type, dayfirst=dayfirst)
        cleaned = drop_fully_empty_columns(cleaned)
        clean_tables[log_type] = cleaned

    missing_log_types = sorted(set(schema) - set(clean_tables))
    if missing_log_types:
        print(f"[{input_path.name}] Log Type khong co du lieu: {missing_log_types}")

    if save_per_table:
        out_subdir = Path(output_dir) / input_path.stem
        out_subdir.mkdir(parents=True, exist_ok=True)
        for log_type, df in clean_tables.items():
            df.to_csv(out_subdir / f"{_slugify(log_type)}.csv", index=False)
        data_dictionary_for_tables(clean_tables).to_csv(out_subdir / "data_dictionary.csv", index=False)
        quality_report_for_tables(clean_tables).to_csv(out_subdir / "quality_report.csv", index=False)
        print(f"[{input_path.name}] encoding={used_encoding}  ->  da luu {len(clean_tables)} bang vao {out_subdir}")

    return clean_tables


# --------------------------------------------------------------------------
# 7. Xu ly hang loat nhieu file
# --------------------------------------------------------------------------

def batch_process(input_path: str | Path, output_dir: str | Path,
                   pattern: str = "*.csv",
                   encoding: Optional[str] = None,
                   dayfirst: bool = True) -> None:
    """Xu ly 1 file HOAC toan bo file khop `pattern` trong 1 thu muc.

    Loi o 1 file se duoc bao va bo qua, khong lam dung ca batch.
    """
    input_path = Path(input_path)
    if input_path.is_dir():
        files = sorted(input_path.glob(pattern))
    else:
        files = [input_path]

    if not files:
        print(f"Khong tim thay file nao khop '{pattern}' trong {input_path}")
        return

    print(f"Tim thay {len(files)} file. Bat dau xu ly...\n")
    ok, failed = 0, []
    for f in files:
        try:
            process_file(f, output_dir, encoding=encoding, dayfirst=dayfirst)
            ok += 1
        except Exception as e:  # noqa: BLE001 - muon tiep tuc voi file khac
            print(f"[LOI] {f.name}: {e}")
            failed.append(f.name)

    print(f"\nHoan tat: {ok}/{len(files)} file thanh cong.")
    if failed:
        print("Cac file loi:", ", ".join(failed))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Lam sach file log dang nhieu-schema-gop-1-CSV (kieu APS/APU)."
    )
    p.add_argument("--input", "-i", required=True,
                    help="Duong dan 1 file CSV, hoac 1 thu muc chua nhieu file CSV.")
    p.add_argument("--output", "-o", required=True,
                    help="Thu muc se luu ket qua da lam sach.")
    p.add_argument("--pattern", default="*.csv",
                    help="Mau ten file khi --input la thu muc (mac dinh: *.csv).")
    p.add_argument("--encoding", default=None,
                    help="Ep encoding cu the (vd cp1252). Mac dinh: tu dong thu.")
    p.add_argument("--month-first", action="store_true",
                    help="Dung neu TimeStamp trong file la mm/dd/yyyy thay vi dd/mm/yyyy.")
    return p


def main(argv: Optional[List[str]] = None) -> None:
    args = _build_arg_parser().parse_args(argv)
    batch_process(
        args.input,
        args.output,
        pattern=args.pattern,
        encoding=args.encoding,
        dayfirst=not args.month_first,
    )


if __name__ == "__main__":
    main()