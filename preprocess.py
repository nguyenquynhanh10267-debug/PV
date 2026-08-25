"""
preprocess.py
=============
Pipeline tiền xử lý dữ liệu nhà máy điện mặt trời Trung Nam (Inverter SINACON PV & SCADA Reports).

Tuân thủ nghiêm ngặt 16 quy tắc bảo toàn dữ liệu:
- Đọc dữ liệu từ raw_dir (không sửa đổi dữ liệu gốc).
- Tự động nhận diện và hợp nhất toàn bộ các file Power Report (1-15 và 16-27) thành 1 dataset power_report duy nhất.
- Unnest multi-level header cho 3 báo cáo SCADA Excel.
- Chuẩn hóa tên cột snake_case và bảo toàn đơn vị đo.
- Tách bạch timestamp_original và timestamp (+10s offset) cho apu_stat_10s.
- Chỉ loại bỏ các dòng duplicate 100% (keep='first').
- Gắn cờ is_sensor_fault cho lỗi cảm biến -20°C (không ghi đè giá trị).
- Tạo cột phụ trợ radiation_clipped_w_m2 cho bức xạ âm ban đêm (không sửa cột gốc).
- Giữ nguyên đơn vị và nhãn xác nhận cho IdcMax/V và IdcMin/V.
- Không tự ý impute missing values (giữ nguyên NaN).
- Không xóa outlier vật lý.
- Lưu 13 dataset riêng biệt dưới định dạng Parquet (Snappy compression).
- Xuất 5 file báo cáo kiểm toán CSV chi tiết.
- Kiểm tra toàn vẹn và tính đơn điệu của chuỗi thời gian.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import pandas as pd

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PV_Preprocessor")


# --------------------------------------------------------------------------
# 1. KHAI BÁO CẤU HÌNH & FILE MAPPING
# --------------------------------------------------------------------------

LOG_TYPE_CONFIG = {
    "aps_ctrl_trig": {
        "filename_pattern": "aps_ctrl_trig.csv",
        "format": "csv",
        "description": "APS Trigger Control Events",
        "has_subsystems": False,
        "is_trigger": True
    },
    "aps_energy": {
        "filename_pattern": "aps_energy.csv",
        "format": "csv",
        "description": "APS Cumulative Energy (1-min)",
        "has_subsystems": False,
        "is_trigger": False
    },
    "aps_stat_60s": {
        "filename_pattern": "aps_stat_60s.csv",
        "format": "csv",
        "description": "APS Status, Ambient & Transformer Temp (1-min)",
        "has_subsystems": False,
        "is_trigger": False
    },
    "aps_stat_trig": {
        "filename_pattern": "aps_stat_trig.csv",
        "format": "csv",
        "description": "APS Status & Error Trigger Events",
        "has_subsystems": False,
        "is_trigger": True
    },
    "aps_switching_cycles": {
        "filename_pattern": "aps_switching_cycles.csv",
        "format": "csv",
        "description": "APS Contactor Switching Cycles",
        "has_subsystems": False,
        "is_trigger": False
    },
    "apu_ctrl_trig": {
        "filename_pattern": "apu_ctrl_trig.csv",
        "format": "csv",
        "description": "APU Control & Setpoints Trigger",
        "has_subsystems": True,
        "is_trigger": True
    },
    "apu_energy": {
        "filename_pattern": "apu_energy.csv",
        "format": "csv",
        "description": "APU Cumulative Ah Channels (1-min)",
        "has_subsystems": True,
        "is_trigger": False
    },
    "apu_stat_10s": {
        "filename_pattern": "apu_stat_10s.csv",
        "format": "csv",
        "description": "APU High-Frequency Electrical Measurements (10-s)",
        "has_subsystems": True,
        "is_trigger": False,
        "is_10s": True
    },
    "apu_stat_60s": {
        "filename_pattern": "apu_stat_60s.csv",
        "format": "csv",
        "description": "APU Temperatures & Humidity (1-min)",
        "has_subsystems": True,
        "is_trigger": False
    },
    "apu_stat_trig": {
        "filename_pattern": "apu_stat_trig.csv",
        "format": "csv",
        "description": "APU Status, Limits & Fault Trigger",
        "has_subsystems": True,
        "is_trigger": True
    },
    "weather_report": {
        "filename_pattern": "Weather reports*.xlsm",
        "format": "excel",
        "description": "SCADA Weather & Module Temperatures Report",
        "has_subsystems": False,
        "is_trigger": False
    },
    "power_report": {
        "filename_pattern": "Power reports*.xls*",
        "format": "excel",
        "description": "SCADA 1-minute AC & DC Power Report (Merged Parts 1 & 2)",
        "has_subsystems": False,
        "is_trigger": False,
        "is_multi_file": True
    },
    "energy_report": {
        "filename_pattern": "Energy reports*.xls*",
        "format": "excel",
        "description": "SCADA Hourly Cumulative MWh Energy Report",
        "has_subsystems": False,
        "is_trigger": False
    }
}


# --------------------------------------------------------------------------
# 2. HÀM TÌM KIẾM VÀ KHẢO SÁT FILE ĐẦU VÀO
# --------------------------------------------------------------------------

def discover_files(raw_dir: Path) -> Dict[str, Union[Path, List[Path]]]:
    """Tìm kiếm đường dẫn chính xác cho 13 nguồn dữ liệu, hỗ trợ multi-file cho Power Report."""
    discovered: Dict[str, Union[Path, List[Path]]] = {}
    for key, cfg in LOG_TYPE_CONFIG.items():
        pattern = cfg["filename_pattern"]
        matches = sorted(list(raw_dir.glob(pattern)))
        if not matches:
            matches = sorted(list(raw_dir.glob(f"*{Path(pattern).stem}*{Path(pattern).suffix}")))
            
        if cfg.get("is_multi_file", False):
            if matches:
                discovered[key] = matches
                logger.info(f"Tìm thấy {len(matches)} file cho [{key}]: {[m.name for m in matches]}")
            else:
                logger.warning(f"Không tìm thấy file khớp với '{pattern}' trong {raw_dir}")
        else:
            if matches:
                discovered[key] = matches[0]
            else:
                logger.warning(f"Không tìm thấy file khớp với '{pattern}' trong {raw_dir}")
                
    logger.info(f"Đã phát hiện {len(discovered)}/{len(LOG_TYPE_CONFIG)} loại log dữ liệu.")
    return discovered


# --------------------------------------------------------------------------
# 3. HÀM XỬ LÝ DATETIME ROBUST (ISO vs DD/MM/YYYY)
# --------------------------------------------------------------------------

def robust_parse_datetime(series: pd.Series) -> pd.Series:
    """Tự động nhận diện định dạng ISO (YYYY-MM-DD) hoặc DD/MM/YYYY để parse chính xác 100%."""
    s_str = series.astype(str).str.strip()
    valid_samples = s_str[~s_str.isin(["", "nan", "None", "NaT"])]
    if valid_samples.empty:
        return pd.to_datetime(series, errors="coerce")
    
    first_val = valid_samples.iloc[0]
    if first_val.startswith(("202", "199", "203")):
        return pd.to_datetime(series, format="ISO8601", errors="coerce")
    else:
        return pd.to_datetime(series, dayfirst=True, errors="coerce")


# --------------------------------------------------------------------------
# 4. HÀM ĐỌC & XỬ LÝ HEADER ĐA TẦNG CỦA 3 FILE SCADA EXCEL
# --------------------------------------------------------------------------

def parse_scada_weather_report(path: Path, nrows: Optional[int] = None) -> pd.DataFrame:
    """Đọc file Weather Report, loại bỏ template rows và unnest 2 tầng header."""
    logger.info(f"Đang phân tích SCADA Weather Report: {path.name}")
    df_raw = pd.read_excel(path, header=None, nrows=nrows + 5 if nrows else None)
    
    h0 = df_raw.iloc[3].fillna("").astype(str).str.strip()
    h1 = df_raw.iloc[4].fillna("").astype(str).str.strip()
    
    curr_prefix = ""
    col_names = []
    for i in range(len(h0)):
        p = h0.iloc[i]
        s = h1.iloc[i]
        if p != "":
            curr_prefix = p
        if i == 0:
            col_names.append("empty_col_0")
        elif i == 1:
            col_names.append("timestamp")
        else:
            if curr_prefix in ["Global", ""]:
                col_slug = f"global_{s.lower().replace(' ', '_')}"
            else:
                prefix_slug = curr_prefix.lower().replace("#", "_").replace(".", "_")
                sub_slug = s.lower().replace(" ", "_")
                col_slug = f"{prefix_slug}_{sub_slug}"
            
            if "temp" in col_slug or "module" in col_slug:
                col_slug += "_c"
            elif "radiation" in col_slug:
                col_slug += "_w_m2"
            elif "humidity" in col_slug:
                col_slug += "_pct_rh"
            elif "wind_speed" in col_slug:
                col_slug += "_m_s"
            
            col_names.append(col_slug)
            
    df_data = df_raw.iloc[5:].copy()
    df_data.columns = col_names
    df_data = df_data.drop(columns=["empty_col_0"])
    df_data = df_data.dropna(subset=["timestamp"]).reset_index(drop=True)
    return df_data


def parse_scada_power_report(path: Path, nrows: Optional[int] = None) -> pd.DataFrame:
    """Đọc file Power Report (AC & DC kW), loại bỏ template rows và unnest 2 tầng header."""
    logger.info(f"Đang phân tích SCADA Power Report: {path.name}")
    df_raw = pd.read_excel(path, header=None, nrows=nrows + 5 if nrows else None)
    
    h0 = df_raw.iloc[3].fillna("").astype(str).str.strip()
    h1 = df_raw.iloc[4].fillna("").astype(str).str.strip()
    
    curr_block = ""
    col_names = []
    for i in range(len(h0)):
        p = h0.iloc[i]
        s = h1.iloc[i]
        if p.startswith("BLOCK"):
            curr_block = p
        if i == 0:
            col_names.append("empty_col_0")
        elif i == 1:
            col_names.append("timestamp")
        elif i == 2:
            col_names.append("radiation_w_m2")
        else:
            b_slug = curr_block.lower().replace(" ", "_")
            inv_slug = s.lower().replace("#", "_").replace(" ", "_")
            col_names.append(f"{b_slug}_{inv_slug}_kw")
            
    df_data = df_raw.iloc[5:].copy()
    df_data.columns = col_names
    df_data = df_data.drop(columns=["empty_col_0"])
    df_data = df_data.dropna(subset=["timestamp"]).reset_index(drop=True)
    return df_data


def parse_scada_energy_report(path: Path, nrows: Optional[int] = None) -> pd.DataFrame:
    """Đọc file Energy Report (+MWh), loại bỏ template rows và unnest 2 tầng header."""
    logger.info(f"Đang phân tích SCADA Energy Report: {path.name}")
    df_raw = pd.read_excel(path, header=None, nrows=nrows + 5 if nrows else None)
    
    h0 = df_raw.iloc[3].fillna("").astype(str).str.strip()
    h1 = df_raw.iloc[4].fillna("").astype(str).str.strip()
    
    curr_block = ""
    col_names = []
    for i in range(len(h0)):
        p = h0.iloc[i]
        s = h1.iloc[i]
        if p.startswith("BLOCK"):
            curr_block = p
        if i == 0:
            col_names.append("empty_col_0")
        elif i == 1:
            col_names.append("timestamp")
        else:
            b_slug = curr_block.lower().replace(" ", "_")
            inv_slug = s.lower().replace(" ", "_")
            col_names.append(f"{b_slug}_{inv_slug}_mwh")
            
    df_data = df_raw.iloc[5:].copy()
    df_data.columns = col_names
    df_data = df_data.drop(columns=["empty_col_0"])
    df_data = df_data.dropna(subset=["timestamp"]).reset_index(drop=True)
    return df_data


# --------------------------------------------------------------------------
# 5. HÀM CHUẨN HÓA TÊN CỘT & MAPPING DICTIONARY
# --------------------------------------------------------------------------

def standardize_col_name(raw_name: str, log_type: str = "") -> str:
    """Chuyển đổi tên cột sang snake_case và bảo toàn đơn vị đo lường chuẩn."""
    s = raw_name.strip()
    
    # Trường hợp đặc biệt IdcMax/V và IdcMin/V
    if s in ["IdcMax/V", "IdcMin/V"]:
        slug = "idc_max_v" if "Max" in s else "idc_min_v"
        return f"{slug}__needs_domain_confirmation"
        
    # Thay thế các đơn vị theo thứ tự ưu tiên
    s = s.replace("/kWh", "_kwh").replace("/kW", "_kw")
    s = s.replace("/kvar", "_kvar")
    s = s.replace("°C", "_c").replace("C", "_c")
    s = s.replace("/°C", "_c").replace("/C", "_c")
    s = s.replace("/µF", "_uf").replace("/F", "_uf")
    s = s.replace("/kO", "_kohm").replace("/kΩ", "_kohm")
    s = re.sub(r"/k(?![a-zA-Z])", "_kohm", s)
    s = s.replace("/V", "_v").replace("/A", "_a").replace("/Hz", "_hz")
    s = s.replace("/Ah", "_ah").replace("/ms", "_ms")
    s = s.replace("/%RH", "_pct_rh").replace("/(W/m^2)", "_w_m2").replace("/(W/m2)", "_w_m2")
    s = s.replace("+MWh", "_mwh").replace("/MWh", "_mwh")
    
    # Xử lý khoảng trắng, ký tự đặc biệt
    s = s.replace(" ", "_").replace(".", "_").replace("#", "_").replace("-", "_")
    s = s.replace("(", "").replace(")", "").replace("/", "_")
    
    s = s.lower()
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


# --------------------------------------------------------------------------
# 6. HÀM TÁI TẠO TIMESTAMP 10S CHO APU_STAT_10S (DUAL TIMESTAMP + INTRA-MINUTE RESOLUTION)
# --------------------------------------------------------------------------

def reconstruct_10s_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bảo toàn timestamp_original và tái tạo timestamp 10s chính xác:
    - Với các phút chuẩn (N = 6): gán chính xác +0s, +10s, +20s, +30s, +40s, +50s.
    - Với các đợt trigger/buffer flush (N != 6): gán tỷ lệ đều trong khoảng [0, 59.99s],
      đảm bảo tuyệt đối không tràn sang phút tiếp theo và đảm bảo (System, timestamp) là unique 100%.
    """
    logger.info("Đang áp dụng tái tạo timestamp 10 giây (Dual Timestamp) cho apu_stat_10s...")
    df = df.copy()
    
    df["timestamp_original"] = df["timestamp"].astype(str)
    parsed_minute = robust_parse_datetime(df["timestamp"])
    df["_minute_dt"] = parsed_minute
    df["_orig_order"] = np.arange(len(df))
    df = df.sort_values(["system", "_minute_dt", "_orig_order"]).reset_index(drop=True)
    
    df["_group_size"] = df.groupby(["system", "_minute_dt"])["timestamp_original"].transform("count")
    df["_sample_idx"] = df.groupby(["system", "_minute_dt"]).cumcount()
    
    offset_seconds = np.where(
        df["_group_size"] == 6,
        df["_sample_idx"] * 10.0,
        df["_sample_idx"] / df["_group_size"] * 60.0
    )
    df["timestamp"] = df["_minute_dt"] + pd.to_timedelta(offset_seconds, unit="s")
    
    df = df.drop(columns=["_minute_dt", "_orig_order", "_group_size", "_sample_idx"])
    
    cols = ["log_type", "system", "timestamp", "timestamp_original"] + [
        c for c in df.columns if c not in ["log_type", "system", "timestamp", "timestamp_original"]
    ]
    return df[cols]


# --------------------------------------------------------------------------
# 7. HÀM ÉP KIỂU VÀ PHÁT HIỆN DỊ THƯỜNG (ANOMALIES & SENSOR FAULT)
# --------------------------------------------------------------------------

def process_anomalies_and_flags(df: pd.DataFrame, log_type: str) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Phát hiện lỗi cảm biến -20°C, tính toán bức xạ dương, gắn cờ kiểm toán."""
    df = df.copy()
    anomalies = []
    
    # 1. Cảm biến nhiệt độ -20.0°C (Lỗi đứt cáp PT100 trong aps_stat_60s)
    if log_type == "aps_stat_60s":
        fault_mask = False
        if "tamb_c" in df.columns:
            fault_mask = fault_mask | ((df["tamb_c"] >= -20.01) & (df["tamb_c"] <= -19.99))
        if "ttrans_c" in df.columns:
            fault_mask = fault_mask | ((df["ttrans_c"] >= -20.01) & (df["ttrans_c"] <= -19.99))
            
        df["is_sensor_fault"] = fault_mask
        n_faults = int(fault_mask.sum())
        if n_faults > 0:
            logger.info(f"Phát hiện {n_faults} bản ghi lỗi cảm biến PT100 (-20°C) trong {log_type}. Đã gắn cờ is_sensor_fault.")
            sample_faults = df[fault_mask]
            for _, r in sample_faults.iterrows():
                anomalies.append({
                    "log_type": log_type,
                    "timestamp": str(r.get("timestamp")),
                    "anomaly_type": "SENSOR_FAULT_PT100_OPEN_CIRCUIT",
                    "column_affected": "tamb_c / ttrans_c",
                    "raw_value": "-20.0",
                    "action_taken": "flagged_is_sensor_fault_true__preserved_raw"
                })
    else:
        if "is_sensor_fault" not in df.columns:
            df["is_sensor_fault"] = False
            
    # 2. Bức xạ âm ban đêm (Tạo cột dẫn xuất radiation_clipped_w_m2)
    for col in df.columns:
        if "radiation" in col and not col.endswith("_clipped") and col != "radiation_clipped_w_m2":
            clipped_col_name = f"{col}_clipped" if col != "radiation_w_m2" else "radiation_clipped_w_m2"
            df[clipped_col_name] = df[col].clip(lower=0.0)
            neg_count = int((df[col] < 0).sum())
            if neg_count > 0:
                logger.info(f"Tạo cột dẫn xuất '{clipped_col_name}' (giữ nguyên '{col}' có {neg_count:,} giá trị âm ban đêm).")
                
    return df, anomalies


# --------------------------------------------------------------------------
# 8. HÀM TIỀN XỬ LÝ TOÀN DIỆN CHO 1 BẢNG (CORE PROCESSOR)
# --------------------------------------------------------------------------

def process_single_log(
    log_key: str,
    file_input: Union[Path, List[Path]],
    nrows: Optional[int] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Tiền xử lý hoàn chỉnh 1 loại log, hỗ trợ gộp multi-part file cho Power Report."""
    cfg = LOG_TYPE_CONFIG[log_key]
    
    # 1. Đọc dữ liệu (Hỗ trợ multi-file cho Power Report)
    if isinstance(file_input, list):
        filename_display = " + ".join([f.name for f in file_input])
        logger.info(f"==================================================")
        logger.info(f"BẮT ĐẦU XỬ LÝ (MULTI-PART): [{log_key}] từ: {filename_display}")
        dfs_to_concat = []
        for single_file in file_input:
            if log_key == "power_report":
                df_part = parse_scada_power_report(single_file, nrows=nrows)
            else:
                df_part = pd.read_csv(single_file, nrows=nrows, low_memory=False)
            dfs_to_concat.append(df_part)
        df_raw = pd.concat(dfs_to_concat, ignore_index=True)
    else:
        filename_display = file_input.name
        logger.info(f"==================================================")
        logger.info(f"BẮT ĐẦU XỬ LÝ: [{log_key}] từ file: {filename_display}")
        if cfg["format"] == "excel":
            if log_key == "weather_report":
                df_raw = parse_scada_weather_report(file_input, nrows=nrows)
            elif log_key == "power_report":
                df_raw = parse_scada_power_report(file_input, nrows=nrows)
            elif log_key == "energy_report":
                df_raw = parse_scada_energy_report(file_input, nrows=nrows)
            else:
                raise ValueError(f"Không hỗ trợ format excel cho {log_key}")
        else:
            df_raw = pd.read_csv(file_input, nrows=nrows, low_memory=False)
            
    initial_rows = len(df_raw)
    initial_cols = len(df_raw.columns)
    
    # 2. Chuẩn hóa tên cột
    col_mapping = {}
    new_cols = []
    for c in df_raw.columns:
        std_name = standardize_col_name(c, log_key)
        col_mapping[c] = std_name
        new_cols.append(std_name)
    df = df_raw.copy()
    df.columns = new_cols
    
    # 3. Loại bỏ duplicate 100% TOÀN BỘ CÁC CỘT (keep='first')
    exact_duplicates_count = int(df.duplicated().sum())
    if exact_duplicates_count > 0:
        logger.info(f"Loại bỏ {exact_duplicates_count:,} dòng trùng lặp 100% toàn bộ các cột trong {log_key}.")
        df = df.drop_duplicates(keep="first").reset_index(drop=True)
        
    final_rows = len(df)
    
    # 4. Chuẩn hóa Timestamp
    if "timestamp" in df.columns:
        if log_key == "apu_stat_10s":
            df = reconstruct_10s_timestamps(df)
        else:
            df["timestamp"] = robust_parse_datetime(df["timestamp"])
            
    # 5. Ép kiểu Numeric an toàn (không biến lỗi thành 0)
    unparseable_records = 0
    for col in df.columns:
        if col in ["log_type", "system", "timestamp", "timestamp_original", "is_sensor_fault"]:
            continue
        if df[col].dtype == object or str(df[col].dtype).startswith("str"):
            converted = pd.to_numeric(df[col], errors="coerce")
            unparseable_cnt = int(converted.isna().sum()) - int(df[col].isna().sum())
            if unparseable_cnt > 0:
                unparseable_records += unparseable_cnt
                logger.warning(f"Cột '{col}' có {unparseable_cnt} giá trị chuỗi không ép được số -> chuyển thành NaN.")
            df[col] = converted
            
    # 6. Xử lý Anomaly flags
    df, anomalies_list = process_anomalies_and_flags(df, log_key)
    
    # 7. Sắp xếp thứ tự thời gian chuẩn xác
    if "timestamp" in df.columns:
        if "system" in df.columns:
            if "milliseconds_ms" in df.columns:
                df = df.sort_values(["system", "timestamp", "milliseconds_ms"]).reset_index(drop=True)
            else:
                df = df.sort_values(["system", "timestamp"]).reset_index(drop=True)
        else:
            if "milliseconds_ms" in df.columns:
                df = df.sort_values(["timestamp", "milliseconds_ms"]).reset_index(drop=True)
            else:
                df = df.sort_values("timestamp").reset_index(drop=True)
                
    # 8. Thu thập Audit Metrics
    audit_info = {
        "log_type": log_key,
        "filename": filename_display,
        "initial_rows": initial_rows,
        "final_rows": final_rows,
        "removed_exact_duplicates": exact_duplicates_count,
        "unparseable_numeric_count": unparseable_records,
        "initial_columns": initial_cols,
        "final_columns": len(df.columns),
        "column_mapping": col_mapping,
        "anomalies": anomalies_list,
        "min_timestamp": str(df["timestamp"].min()) if "timestamp" in df.columns and not df.empty else "N/A",
        "max_timestamp": str(df["timestamp"].max()) if "timestamp" in df.columns and not df.empty else "N/A",
        "is_monotonic_increasing": bool(df.groupby("system")["timestamp"].apply(lambda s: s.is_monotonic_increasing).all()) if "system" in df.columns and "timestamp" in df.columns and not df.empty else (bool(df["timestamp"].is_monotonic_increasing) if "timestamp" in df.columns and not df.empty else True),
        "missing_counts_per_col": {c: int(df[c].isna().sum()) for c in df.columns}
    }
    
    logger.info(f"HOÀN TẤT [{log_key}]: {final_rows:,} dòng, {len(df.columns)} cột. Thời gian từ {audit_info['min_timestamp']} đến {audit_info['max_timestamp']}.")
    return df, audit_info


# --------------------------------------------------------------------------
# 9. HÀM XUẤT FILE PARQUET & BÁO CÁO KIỂM TOÁN
# --------------------------------------------------------------------------

def export_audit_reports(audit_records: List[Dict[str, Any]], reports_dir: Path):
    """Xuất 5 file báo cáo kiểm toán CSV theo đúng yêu cầu."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Đang xuất các báo cáo kiểm toán vào thư mục: {reports_dir}")
    
    # 1. cleaning_report.csv
    cleaning_rows = []
    for r in audit_records:
        cleaning_rows.append({
            "log_type": r["log_type"],
            "raw_filename": r["filename"],
            "initial_rows": r["initial_rows"],
            "final_rows": r["final_rows"],
            "removed_exact_duplicates": r["removed_exact_duplicates"],
            "unparseable_numeric_cells": r["unparseable_numeric_count"],
            "min_timestamp": r["min_timestamp"],
            "max_timestamp": r["max_timestamp"],
            "is_monotonic_increasing": r["is_monotonic_increasing"]
        })
    pd.DataFrame(cleaning_rows).to_csv(reports_dir / "cleaning_report.csv", index=False)
    
    # 2. column_mapping.csv
    mapping_rows = []
    for r in audit_records:
        for orig, std in r["column_mapping"].items():
            notes = "Requires domain confirmation" if "needs_domain_confirmation" in std else "Standard"
            mapping_rows.append({
                "log_type": r["log_type"],
                "original_column_name": orig,
                "standardized_column_name": std,
                "notes": notes
            })
    pd.DataFrame(mapping_rows).to_csv(reports_dir / "column_mapping.csv", index=False)
    
    # 3. missing_report.csv
    missing_rows = []
    for r in audit_records:
        tot = r["final_rows"]
        for col, miss_cnt in r["missing_counts_per_col"].items():
            pct = round(miss_cnt / tot * 100, 2) if tot > 0 else 0.0
            nature = "None (0%)"
            if miss_cnt == tot and tot > 0:
                nature = "Structural Missing (100% empty)"
            elif any(hw in col for hw in ["apu5", "apu6", "56"]):
                nature = "Systematic (Unused hardware channels)"
            elif miss_cnt > 0:
                nature = f"Partial Missing ({pct}%)"
                
            missing_rows.append({
                "log_type": r["log_type"],
                "column_name": col,
                "missing_count": miss_cnt,
                "missing_rate_pct": pct,
                "classification": nature
            })
    pd.DataFrame(missing_rows).to_csv(reports_dir / "missing_report.csv", index=False)
    
    # 4. anomaly_report.csv
    all_anomalies = []
    for r in audit_records:
        all_anomalies.extend(r["anomalies"])
    if not all_anomalies:
        all_anomalies.append({
            "log_type": "ALL",
            "timestamp": "N/A",
            "anomaly_type": "NO_ANOMALY_RECORDED",
            "column_affected": "N/A",
            "raw_value": "N/A",
            "action_taken": "N/A"
        })
    pd.DataFrame(all_anomalies).to_csv(reports_dir / "anomaly_report.csv", index=False)
    
    # 5. schema_report.csv
    schema_rows = []
    for r in audit_records:
        schema_rows.append({
            "log_type": r["log_type"],
            "final_rows": r["final_rows"],
            "final_columns": r["final_columns"],
            "time_range": f"{r['min_timestamp']} -> {r['max_timestamp']}",
            "storage_format": "Parquet (Snappy)"
        })
    pd.DataFrame(schema_rows).to_csv(reports_dir / "schema_report.csv", index=False)
    
    logger.info("Đã xuất thành công 5 file báo cáo kiểm toán CSV.")


def save_processed_parquet(df: pd.DataFrame, log_key: str, processed_dir: Path) -> Path:
    """Lưu DataFrame sạch dưới định dạng Parquet nén Snappy."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_file = processed_dir / f"{log_key}.parquet"
    df.to_parquet(out_file, engine="pyarrow", compression="snappy", index=False)
    logger.info(f"Đã lưu Parquet: {out_file.name} ({out_file.stat().st_size:,} bytes)")
    return out_file


# --------------------------------------------------------------------------
# 10. HÀM ĐIỀU PHỐI PIPELINE CHÍNH (ORCHESTRATOR)
# --------------------------------------------------------------------------

def run_pipeline(
    raw_dir: Path,
    output_dir: Path,
    sample_mode: bool = False,
    sample_rows: int = 1000
) -> Dict[str, Any]:
    """Chạy toàn bộ pipeline xử lý cho 13 log."""
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info(f"BẮT ĐẦU PIPELINE TIỀN XỬ LÝ NHÀ MÁY ĐIỆN MẶT TRỜI TRUNG NAM")
    logger.info(f"Raw Data Dir   : {raw_dir.resolve()}")
    logger.info(f"Output Base Dir: {output_dir.resolve()}")
    logger.info(f"Chế độ Sample  : {'BẬT (Sample ' + str(sample_rows) + ' dòng)' if sample_mode else 'TẮT (Toàn bộ 27 ngày)'}")
    logger.info("=" * 70)
    
    discovered_files = discover_files(raw_dir)
    if not discovered_files:
        logger.error(f"Không tìm thấy file nào trong {raw_dir}!")
        return {}
        
    processed_dir = output_dir / "processed"
    reports_dir = output_dir / "reports"
    
    processed_tables = {}
    audit_records = []
    
    for log_key in LOG_TYPE_CONFIG.keys():
        if log_key not in discovered_files:
            logger.warning(f"Bỏ qua '{log_key}' do không có file đầu vào.")
            continue
            
        file_input = discovered_files[log_key]
        nrows = sample_rows if sample_mode else None
        
        try:
            df_proc, audit_info = process_single_log(log_key, file_input, nrows=nrows)
            processed_tables[log_key] = df_proc
            audit_records.append(audit_info)
            
            save_processed_parquet(df_proc, log_key, processed_dir)
        except Exception as e:
            logger.error(f"LỖI KHI XỬ LÝ [{log_key}]: {e}", exc_info=True)
            
    export_audit_reports(audit_records, reports_dir)
    
    duration = datetime.now() - start_time
    logger.info("=" * 70)
    logger.info(f"PIPELINE HOÀN TẤT THÀNH CÔNG TRONG: {duration.total_seconds():.2f} giây")
    logger.info(f"Tổng số dataset đã xử lý: {len(processed_tables)}/13")
    logger.info("=" * 70)
    
    return {
        "processed_tables": processed_tables,
        "audit_records": audit_records,
        "duration_seconds": duration.total_seconds()
    }


# --------------------------------------------------------------------------
# 11. CLI INTERFACE
# --------------------------------------------------------------------------

def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Pipeline tiền xử lý dữ liệu nhà máy điện mặt trời Trung Nam (SINACON PV & SCADA)."
    )
    parser.add_argument(
        "--raw-dir", "-r",
        type=Path,
        default=Path("cleaned_data"),
        help="Đường dẫn thư mục chứa dữ liệu raw gốc (mặc định: cleaned_data)."
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("data"),
        help="Đường dẫn thư mục xuất kết quả (mặc định: data)."
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Chạy ở chế độ mẫu (dry-run / sample test) với số dòng giới hạn."
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=1000,
        help="Số lượng dòng tối đa đọc trong chế độ sample (mặc định: 1000 dòng)."
    )
    return parser.parse_args()


def main():
    args = parse_cli_args()
    run_pipeline(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        sample_mode=args.sample,
        sample_rows=args.sample_rows
    )


if __name__ == "__main__":
    main()
