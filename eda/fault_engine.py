"""
fault_engine.py
===============
Engine chuyên sâu cho Điều tra Sự cố & Phân tích Lỗi (Events & Faults Investigation Engine).
Tuân thủ nguyên tắc: Thiết bị thực tế phát sinh lỗi (Device-Specific), Gom cụm sự kiện (Episode Grouping),
Ánh xạ mã lỗi chuẩn Siemens SINACON PV từ config.py, và Phân tích Trước lỗi/Tại thời điểm lỗi/Sau lỗi (Before/At/After).
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

from config import (
    ERROR_CODES_APS,
    ERROR_CODES_APU,
    WARNING_CODES,
    OPSTATE_MAP,
    WARNING_DEVICE_ROUTING,
    APS_ERROR_DEVICE_ROUTING,
    COLORS,
    APS_ERROR_WINDOW_SECONDS
)
from data_loader import (
    load_event_datasets,
    load_power_report,
    load_apu_stat_10s,
    load_aps_stat_60s,
    load_apu_stat_60s,
    load_weather_report
)


def get_error_description(code: int, device_type: str = "APU") -> str:
    """Trả về mô tả kỹ thuật tiếng Anh chuẩn từ config.py."""
    if device_type == "APS":
        if code in ERROR_CODES_APS:
            return ERROR_CODES_APS[code]
    else:
        if code in ERROR_CODES_APU:
            return ERROR_CODES_APU[code]
    return f"Code {code}"


def get_warning_description(code: int) -> str:
    """Trả về mô tả cảnh báo tiếng Anh chuẩn từ config.py."""
    if code in WARNING_CODES:
        return WARNING_CODES[code]
    return f"Warning {code}"


def get_opstate_description(op: int) -> str:
    """Trả về mô tả trạng thái vận hành OpState."""
    return OPSTATE_MAP.get(op, f"Trạng thái {op}")


def build_standard_fault_events(event_data: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    """
    Xây dựng bảng sự cố chuẩn hóa từ toàn bộ các nguồn trigger.
    Gán đúng thiết bị phát sinh (Device-specific), phân loại: LỖI APU, LỖI APS và CẢNH BÁO.
    """
    if event_data is None:
        event_data = load_event_datasets()
        
    records = []
    event_counter = 1
    
    # ---------------------------------------------------------
    # 1. Quét APS Stat Trig -> LỖI APS & CẢNH BÁO
    # ---------------------------------------------------------
    df_aps = event_data.get("aps_stat_trig", pd.DataFrame())
    if not df_aps.empty:
        err_cols = [c for c in df_aps.columns if c.startswith("error")]
        warn_cols = [c for c in df_aps.columns if c.startswith("warning")]
        
        for idx, row in df_aps.iterrows():
            ts = pd.to_datetime(row["timestamp"])
            ms = int(row.get("milliseconds_ms", 0))
            op = int(row.get("opstate", 0))
            
            raw_errors = {c: int(row[c]) for c in err_cols if int(row[c]) > 0}
            raw_warnings = {c: int(row[c]) for c in warn_cols if int(row[c]) > 0}
            
            raw_row_dump = {
                "source": "aps_stat_trig",
                "opstate": op,
                "errors": raw_errors,
                "warnings": raw_warnings
            }
            
            # A. Nếu có Error code > 0 hoặc OpState == 130 -> LỖI APS
            if raw_errors or op == 130:
                error_items = []
                primary_code = list(raw_errors.values())[0] if raw_errors else op
                for ec, code in raw_errors.items():
                    desc = get_error_description(code, device_type="APS")
                    error_items.append({"register": ec, "code": code, "desc": desc})
                    
                if not raw_errors and op == 130:
                    error_items.append({"register": "OPSTATE", "code": 130, "desc": "Master Protective Trip (130)"})
                    
                # Ánh xạ thiết bị cụ thể nếu mã lỗi chỉ đích danh APU
                target_dev = "APS"
                if primary_code in APS_ERROR_DEVICE_ROUTING:
                    target_dev = APS_ERROR_DEVICE_ROUTING[primary_code]
                    
                primary_desc = error_items[0]["desc"] if error_items else "APS Error"
                
                records.append({
                    "event_id": f"EVT-{event_counter:05d}",
                    "timestamp": ts,
                    "date": ts.date(),
                    "hour": ts.hour,
                    "minute": ts.minute,
                    "second": ts.second,
                    "milliseconds_ms": ms,
                    "time_str": ts.strftime("%H:%M:%S") + f".{ms:03d}",
                    "event_category": "LỖI APS",
                    "event_category_en": "APS ERROR",
                    "severity": "CRITICAL",
                    "device": target_dev,
                    "apu_id": target_dev,
                    "fault_code_str": ", ".join([f"Lỗi {item['code']}" for item in error_items]),
                    "primary_code": primary_code,
                    "error_description": primary_desc,
                    "error_items": error_items,
                    "warning_code_str": "N/A",
                    "warning_description": "N/A",
                    "warning_items": [],
                    "opstate": op,
                    "opstate_desc": get_opstate_description(op),
                    "is_4apu_correlated": False,
                    "source_dataset": "aps_stat_trig",
                    "raw_row_reference": raw_row_dump,
                    "num_error_codes": len(error_items)
                })
                event_counter += 1
                
            # B. Nếu chỉ có Warnings -> CẢNH BÁO
            elif raw_warnings:
                warning_items = []
                primary_wcode = list(raw_warnings.values())[0]
                
                for wc, code in raw_warnings.items():
                    wdesc = get_warning_description(code)
                    warning_items.append({"register": wc, "code": code, "desc": wdesc})
                    
                target_dev = WARNING_DEVICE_ROUTING.get(primary_wcode, "APS")
                primary_wdesc = warning_items[0]["desc"]
                
                records.append({
                    "event_id": f"EVT-{event_counter:05d}",
                    "timestamp": ts,
                    "date": ts.date(),
                    "hour": ts.hour,
                    "minute": ts.minute,
                    "second": ts.second,
                    "milliseconds_ms": ms,
                    "time_str": ts.strftime("%H:%M:%S") + f".{ms:03d}",
                    "event_category": "CẢNH BÁO",
                    "event_category_en": "WARNING",
                    "severity": "WARNING",
                    "device": target_dev,
                    "apu_id": target_dev,
                    "fault_code_str": "N/A",
                    "primary_code": 0,
                    "error_description": "N/A",
                    "error_items": [],
                    "warning_code_str": ", ".join([f"Cảnh báo {item['code']}" for item in warning_items]),
                    "warning_description": primary_wdesc,
                    "warning_items": warning_items,
                    "opstate": op,
                    "opstate_desc": get_opstate_description(op),
                    "is_4apu_correlated": False,
                    "source_dataset": "aps_stat_trig",
                    "raw_row_reference": raw_row_dump,
                    "num_error_codes": 0
                })
                event_counter += 1

    # ---------------------------------------------------------
    # 2. Quét APU Stat Trig -> LỖI APU & DERATING
    # ---------------------------------------------------------
    df_apu = event_data.get("apu_stat_trig", pd.DataFrame())
    if not df_apu.empty:
        err_cols_apu = [c for c in df_apu.columns if c.startswith("error")]
        
        for idx, row in df_apu.iterrows():
            ts = pd.to_datetime(row["timestamp"])
            ms = int(row.get("milliseconds_ms", 0))
            sys_name = str(row.get("system", "APU"))
            op = int(row.get("opstate", 0))
            
            raw_errors_apu = {c: int(row[c]) for c in err_cols_apu if int(row[c]) > 0}
            
            raw_row_dump = {
                "source": "apu_stat_trig",
                "system": sys_name,
                "opstate": op,
                "errors": raw_errors_apu,
                "limits": {
                    "pl1lim_kw": float(row.get("pl1lim_kw", 0)),
                    "vdcmaxlim_v": float(row.get("vdcmaxlim_v", 0)),
                    "idcmaxlim_a": float(row.get("idcmaxlim_a", 0))
                }
            }
            
            # A. LỖI APU: error > 0 hoặc opstate in [130, 330]
            if raw_errors_apu or op in [130, 330]:
                error_items = []
                primary_code = list(raw_errors_apu.values())[0] if raw_errors_apu else op
                
                for ec, code in raw_errors_apu.items():
                    desc = get_error_description(code, device_type="APU")
                    error_items.append({"register": ec, "code": code, "desc": desc})
                    
                if not raw_errors_apu and op in [130, 330]:
                    desc = f"Protective Trip (OpState {op})"
                    error_items.append({"register": "OPSTATE", "code": op, "desc": desc})
                    
                primary_desc = error_items[0]["desc"]
                
                records.append({
                    "event_id": f"EVT-{event_counter:05d}",
                    "timestamp": ts,
                    "date": ts.date(),
                    "hour": ts.hour,
                    "minute": ts.minute,
                    "second": ts.second,
                    "milliseconds_ms": ms,
                    "time_str": ts.strftime("%H:%M:%S") + f".{ms:03d}",
                    "event_category": "LỖI APU",
                    "event_category_en": "APU ERROR",
                    "severity": "CRITICAL",
                    "device": sys_name,
                    "apu_id": sys_name,
                    "fault_code_str": ", ".join([f"Lỗi {item['code']}" for item in error_items]),
                    "primary_code": primary_code,
                    "error_description": primary_desc,
                    "error_items": error_items,
                    "warning_code_str": "N/A",
                    "warning_description": "N/A",
                    "warning_items": [],
                    "opstate": op,
                    "opstate_desc": get_opstate_description(op),
                    "is_4apu_correlated": False,
                    "source_dataset": "apu_stat_trig",
                    "raw_row_reference": raw_row_dump,
                    "num_error_codes": max(1, len(error_items))
                })
                event_counter += 1
                
            # B. CẢNH BÁO GIẢM TẢI: opstate == 160 (Power Derating)
            elif op == 160:
                records.append({
                    "event_id": f"EVT-{event_counter:05d}",
                    "timestamp": ts,
                    "date": ts.date(),
                    "hour": ts.hour,
                    "minute": ts.minute,
                    "second": ts.second,
                    "milliseconds_ms": ms,
                    "time_str": ts.strftime("%H:%M:%S") + f".{ms:03d}",
                    "event_category": "CẢNH BÁO",
                    "event_category_en": "WARNING",
                    "severity": "WARNING",
                    "device": sys_name,
                    "apu_id": sys_name,
                    "fault_code_str": "N/A",
                    "primary_code": 0,
                    "error_description": "N/A",
                    "error_items": [],
                    "warning_code_str": "OpState 160",
                    "warning_description": "Power derating active",
                    "warning_items": [{"register": "OPSTATE", "code": 160, "desc": "Power derating active"}],
                    "opstate": op,
                    "opstate_desc": get_opstate_description(op),
                    "is_4apu_correlated": False,
                    "source_dataset": "apu_stat_trig",
                    "raw_row_reference": raw_row_dump,
                    "num_error_codes": 0
                })
                event_counter += 1
                
    df_res = pd.DataFrame(records)
    if not df_res.empty:
        df_res = df_res.sort_values(["timestamp", "milliseconds_ms"]).reset_index(drop=True)
        df_res = tag_simultaneous_4apu_events(df_res, window_seconds=APS_ERROR_WINDOW_SECONDS)
        
    return df_res


def tag_simultaneous_4apu_events(df_events: pd.DataFrame, window_seconds: int = 60) -> pd.DataFrame:
    """Gắn cờ nhận diện khi CẢ 4 APU cùng xuất hiện lỗi trong khoảng tolerance window."""
    if df_events.empty:
        return df_events
        
    df = df_events.copy()
    apu_errors = df[df["event_category_en"] == "APU ERROR"].copy()
    if apu_errors.empty:
        return df
        
    apu_errors["window_key"] = apu_errors["timestamp"].dt.floor(f"{window_seconds}s")
    
    correlated_windows = []
    for win, grp in apu_errors.groupby("window_key"):
        units = grp["device"].unique()
        if len(units) >= 4:
            correlated_windows.append(win)
            
    if correlated_windows:
        for win in correlated_windows:
            t_min = win
            t_max = win + timedelta(seconds=window_seconds)
            mask = (df["timestamp"] >= t_min) & (df["timestamp"] <= t_max) & (df["event_category_en"] == "APU ERROR")
            df.loc[mask, "is_4apu_correlated"] = True
            
    return df


def group_events_into_episodes(df_day_events: pd.DataFrame, episode_gap_seconds: int = 15) -> pd.DataFrame:
    """
    Gom cụm các sự kiện liên tiếp từ cùng một thiết bị và cùng mã lỗi thành một Event Episode.
    """
    if df_day_events.empty:
        return pd.DataFrame()
        
    df_sorted = df_day_events.sort_values("timestamp").copy()
    episodes = []
    
    for (dev, cat, code_str), grp in df_sorted.groupby(["device", "event_category", "fault_code_str"]):
        grp_list = grp.to_dict("records")
        current_ep = None
        
        for rec in grp_list:
            if current_ep is None:
                current_ep = {
                    "device": dev,
                    "event_category": cat,
                    "event_category_en": rec["event_category_en"],
                    "severity": rec["severity"],
                    "fault_code_str": code_str,
                    "primary_code": rec["primary_code"],
                    "error_description": rec["error_description"],
                    "warning_code_str": rec["warning_code_str"],
                    "warning_description": rec["warning_description"],
                    "opstate": rec["opstate"],
                    "opstate_desc": rec["opstate_desc"],
                    "is_4apu_correlated": rec["is_4apu_correlated"],
                    "start_time": rec["timestamp"],
                    "end_time": rec["timestamp"],
                    "start_time_str": rec["time_str"],
                    "end_time_str": rec["time_str"],
                    "raw_records_count": 1,
                    "event_ids": [rec["event_id"]],
                    "error_items": rec.get("error_items", []),
                    "warning_items": rec.get("warning_items", []),
                    "raw_row_reference": rec.get("raw_row_reference", {})
                }
            else:
                time_diff = (rec["timestamp"] - current_ep["end_time"]).total_seconds()
                if time_diff <= episode_gap_seconds:
                    current_ep["end_time"] = rec["timestamp"]
                    current_ep["end_time_str"] = rec["time_str"]
                    current_ep["raw_records_count"] += 1
                    current_ep["event_ids"].append(rec["event_id"])
                    if rec["is_4apu_correlated"]:
                        current_ep["is_4apu_correlated"] = True
                else:
                    episodes.append(current_ep)
                    current_ep = {
                        "device": dev,
                        "event_category": cat,
                        "event_category_en": rec["event_category_en"],
                        "severity": rec["severity"],
                        "fault_code_str": code_str,
                        "primary_code": rec["primary_code"],
                        "error_description": rec["error_description"],
                        "warning_code_str": rec["warning_code_str"],
                        "warning_description": rec["warning_description"],
                        "opstate": rec["opstate"],
                        "opstate_desc": rec["opstate_desc"],
                        "is_4apu_correlated": rec["is_4apu_correlated"],
                        "start_time": rec["timestamp"],
                        "end_time": rec["timestamp"],
                        "start_time_str": rec["time_str"],
                        "end_time_str": rec["time_str"],
                        "raw_records_count": 1,
                        "event_ids": [rec["event_id"]],
                        "error_items": rec.get("error_items", []),
                        "warning_items": rec.get("warning_items", []),
                        "raw_row_reference": rec.get("raw_row_reference", {})
                    }
                    
        if current_ep is not None:
            episodes.append(current_ep)
            
    df_ep = pd.DataFrame(episodes)
    if not df_ep.empty:
        df_ep = df_ep.sort_values("start_time").reset_index(drop=True)
    return df_ep


def calculate_daily_event_breakdown(df_events: pd.DataFrame) -> pd.DataFrame:
    """Tính bảng tổng kết 27 ngày phân định rõ LỖI APU, LỖI APS, Sự cố 4 APU và CẢNH BÁO."""
    date_range = pd.date_range("2025-10-01", "2025-10-27", freq="D").date
    summary_rows = []
    
    for d in date_range:
        d_events = df_events[df_events["date"] == d] if not df_events.empty else pd.DataFrame()
        
        if d_events.empty:
            summary_rows.append({
                "date": d,
                "total_events": 0,
                "apu_error_count": 0,
                "aps_error_count": 0,
                "warning_count": 0,
                "four_apu_correlated_count": 0,
                "affected_devices": "Không có",
                "affected_devices_count": 0,
                "has_critical_error": False,
                "daily_status": "Bình thường (Normal)"
            })
            continue
            
        n_apu_err = len(d_events[d_events["event_category_en"] == "APU ERROR"])
        n_aps_err = len(d_events[d_events["event_category_en"] == "APS ERROR"])
        n_warn = len(d_events[d_events["event_category_en"] == "WARNING"])
        n_4apu = len(d_events[d_events["is_4apu_correlated"] == True])
        
        crit_events = d_events[d_events["event_category_en"].isin(["APU ERROR", "APS ERROR"])]
        aff_devs = sorted(crit_events["device"].unique().tolist())
        aff_str = ", ".join(aff_devs) if aff_devs else "Không có"
        
        has_critical = (n_apu_err > 0) or (n_aps_err > 0)
        
        if n_aps_err > 0 and n_4apu > 0:
            status = "Lỗi APS + Đồng thời 4 APU (Cascade)"
        elif n_aps_err > 0:
            status = "Lỗi APS cấp trạm"
        elif n_4apu > 0:
            status = "Sự cố đồng thời 4 APU"
        elif n_apu_err > 0:
            status = f"Lỗi APU ({len(aff_devs)} ngăn)"
        elif n_warn > 0:
            status = "Chỉ có cảnh báo"
        else:
            status = "Bình thường"
            
        summary_rows.append({
            "date": d,
            "total_events": len(d_events),
            "apu_error_count": n_apu_err,
            "aps_error_count": n_aps_err,
            "warning_count": n_warn,
            "four_apu_correlated_count": n_4apu,
            "affected_devices": aff_str,
            "affected_devices_count": len(aff_devs),
            "has_critical_error": has_critical,
            "daily_status": status
        })
        
    return pd.DataFrame(summary_rows)


def calculate_hourly_event_histogram(df_events: pd.DataFrame, selected_date: date) -> pd.DataFrame:
    """Tạo ma trận sự cố 24 giờ (00..23h) cho ngày được chọn."""
    hours_df = pd.DataFrame({"hour": list(range(24))})
    
    if df_events.empty:
        hours_df["APU_ERROR"] = 0
        hours_df["APS_ERROR"] = 0
        hours_df["WARNING"] = 0
        return hours_df
        
    day_events = df_events[df_events["date"] == selected_date].copy()
    if day_events.empty:
        hours_df["APU_ERROR"] = 0
        hours_df["APS_ERROR"] = 0
        hours_df["WARNING"] = 0
        return hours_df
        
    day_apu = day_events[day_events["event_category_en"] == "APU ERROR"]
    day_aps = day_events[day_events["event_category_en"] == "APS ERROR"]
    day_warn = day_events[day_events["event_category_en"] == "WARNING"]
    
    apu_h = day_apu["hour"].value_counts().reset_index()
    apu_h.columns = ["hour", "APU_ERROR"]
    
    aps_h = day_aps["hour"].value_counts().reset_index()
    aps_h.columns = ["hour", "APS_ERROR"]
    
    warn_h = day_warn["hour"].value_counts().reset_index()
    warn_h.columns = ["hour", "WARNING"]
    
    res = hours_df.merge(apu_h, on="hour", how="left") \
                  .merge(aps_h, on="hour", how="left") \
                  .merge(warn_h, on="hour", how="left").fillna(0)
                  
    res["APU_ERROR"] = res["APU_ERROR"].astype(int)
    res["APS_ERROR"] = res["APS_ERROR"].astype(int)
    res["WARNING"] = res["WARNING"].astype(int)
    return res


def calculate_interval_statistics(
    series_before: pd.Series,
    val_at: Optional[float],
    series_after: pd.Series,
    metric_name: str,
    unit: str = ""
) -> Dict[str, Any]:
    """
    Tính toán thống kê khoảng đầy đủ cho Trước lỗi [T-win, T), Tại thời điểm lỗi, Sau lỗi (T, T+win].
    """
    bef_clean = series_before.dropna()
    aft_clean = series_after.dropna()
    
    if bef_clean.empty or aft_clean.empty:
        return {
            "Thông số": metric_name,
            "Trước lỗi [T-win, T) (TB ± SD)": "Không đủ dữ liệu",
            "Tại thời điểm lỗi (T)": f"{val_at:.2f} {unit}" if val_at is not None and not np.isnan(val_at) else "N/A",
            "Sau lỗi (T, T+win] (TB ± SD)": "Không đủ dữ liệu",
            "Thay đổi tuyệt đối": "N/A",
            "Thay đổi %": "N/A",
            "Thay đổi quan sát được": "Không đủ dữ liệu"
        }
        
    bef_mean = float(bef_clean.mean())
    bef_std = float(bef_clean.std()) if len(bef_clean) > 1 else 0.0
    bef_min = float(bef_clean.min())
    bef_max = float(bef_clean.max())
    
    aft_mean = float(aft_clean.mean())
    aft_std = float(aft_clean.std()) if len(aft_clean) > 1 else 0.0
    aft_min = float(aft_clean.min())
    aft_max = float(aft_clean.max())
    
    abs_diff = aft_mean - bef_mean
    pct_diff = (abs_diff / abs(bef_mean) * 100.0) if abs(bef_mean) > 1e-4 else 0.0
    
    if abs(pct_diff) < 2.0 or abs(abs_diff) < 0.01:
        obs_text = "Không thay đổi đáng kể"
    elif abs_diff > 0:
        obs_text = f"Quan sát thấy tăng (+{abs_diff:.2f} {unit}, +{pct_diff:.1f}%)"
    else:
        obs_text = f"Quan sát thấy giảm ({abs_diff:.2f} {unit}, {pct_diff:.1f}%)"
        
    return {
        "Thông số": metric_name,
        "Trước lỗi [T-win, T) (TB ± SD)": f"{bef_mean:.2f} ± {bef_std:.2f} [{bef_min:.1f}..{bef_max:.1f}] {unit}",
        "Tại thời điểm lỗi (T)": f"{val_at:.2f} {unit}" if val_at is not None and not np.isnan(val_at) else "N/A",
        "Sau lỗi (T, T+win] (TB ± SD)": f"{aft_mean:.2f} ± {aft_std:.2f} [{aft_min:.1f}..{aft_max:.1f}] {unit}",
        "Thay đổi tuyệt đối": f"{abs_diff:+.2f} {unit}",
        "Thay đổi %": f"{pct_diff:+.1f}%",
        "Thay đổi quan sát được": obs_text
    }


def extract_correlated_signals_robust(
    event_timestamp: datetime,
    window_minutes: int = 30,
    target_device: str = "APU 1"
) -> Dict[str, Any]:
    """
    Trích xuất tín hiệu đồng bộ và tính toán thống kê khoảng Trước lỗi / Tại thời điểm lỗi / Sau lỗi.
    Ưu tiên tín hiệu từ chính thiết bị gặp sự cố target_device.
    """
    t_start = event_timestamp - timedelta(minutes=window_minutes)
    t_end = event_timestamp + timedelta(minutes=window_minutes)
    
    active_apu = target_device if target_device.startswith("APU") else "APU 1"
    
    # 1. Power Report (AC / DC Power)
    df_p = load_power_report()
    df_p_win = df_p[(df_p["timestamp"] >= t_start) & (df_p["timestamp"] <= t_end)].copy() if not df_p.empty else pd.DataFrame()
    if not df_p_win.empty:
        ac_cols = [c for c in df_p_win.columns if c.endswith("_ac_kw")]
        dc_cols = [c for c in df_p_win.columns if c.endswith("_dc_kw")]
        df_p_win["plant_ac_mw"] = df_p_win[ac_cols].sum(axis=1) / 1000.0
        df_p_win["plant_dc_mw"] = df_p_win[dc_cols].sum(axis=1) / 1000.0
        
    # 2. Nhiệt độ APU (apu_stat_60s)
    df_apu_t = load_apu_stat_60s()
    df_apu_t_win = df_apu_t[(df_apu_t["system"] == active_apu) & (df_apu_t["timestamp"] >= t_start) & (df_apu_t["timestamp"] <= t_end)].copy() if not df_apu_t.empty else pd.DataFrame()
    
    # 3. Thông số môi trường & MBA (aps_stat_60s)
    df_aps_t = load_aps_stat_60s()
    df_aps_t_win = df_aps_t[(df_aps_t["timestamp"] >= t_start) & (df_aps_t["timestamp"] <= t_end)].copy() if not df_aps_t.empty else pd.DataFrame()

    # 4. Điện áp & Dòng điện 10 giây (apu_stat_10s)
    df_10s = load_apu_stat_10s(selected_date=str(event_timestamp.date()), system=active_apu)
    df_10s_win = df_10s[(df_10s["timestamp"] >= t_start) & (df_10s["timestamp"] <= t_end)].copy() if not df_10s.empty else pd.DataFrame()
    if not df_10s_win.empty:
        df_10s_win["p_total_kw"] = df_10s_win["pl1_kw"] + df_10s_win["pl2_kw"] + df_10s_win["pl3_kw"]
        df_10s_win["q_total_kvar"] = df_10s_win["ql1_kvar"] + df_10s_win["ql2_kvar"] + df_10s_win["ql3_kvar"]

    # 5. Bức xạ & Thời tiết (weather_report)
    df_w = load_weather_report()
    df_w_win = df_w[(df_w["timestamp"] >= t_start) & (df_w["timestamp"] <= t_end)].copy() if not df_w.empty else pd.DataFrame()

    stat_rows = []
    
    # A. Công suất AC & DC
    if not df_p_win.empty:
        p_bef = df_p_win[df_p_win["timestamp"] < event_timestamp]["plant_ac_mw"]
        p_aft = df_p_win[df_p_win["timestamp"] > event_timestamp]["plant_ac_mw"]
        df_p_win["diff_t"] = (df_p_win["timestamp"] - event_timestamp).abs()
        p_at = float(df_p_win.sort_values("diff_t").iloc[0]["plant_ac_mw"])
        stat_rows.append(calculate_interval_statistics(p_bef, p_at, p_aft, "Công suất phát AC toàn trạm", "MW"))
        
        rad_col = "radiation_clipped_w_m2" if "radiation_clipped_w_m2" in df_p_win.columns else "radiation_w_m2"
        rad_bef = df_p_win[df_p_win["timestamp"] < event_timestamp][rad_col]
        rad_aft = df_p_win[df_p_win["timestamp"] > event_timestamp][rad_col]
        rad_at = float(df_p_win.sort_values("diff_t").iloc[0][rad_col])
        stat_rows.append(calculate_interval_statistics(rad_bef, rad_at, rad_aft, "Bức xạ mặt trời toàn trạm", "W/m²"))

    # B. Nhiệt độ thiết bị
    if not df_apu_t_win.empty:
        tind_bef = df_apu_t_win[df_apu_t_win["timestamp"] < event_timestamp]["tind_c"]
        tind_aft = df_apu_t_win[df_apu_t_win["timestamp"] > event_timestamp]["tind_c"]
        df_apu_t_win["diff_t"] = (df_apu_t_win["timestamp"] - event_timestamp).abs()
        tind_at = float(df_apu_t_win.sort_values("diff_t").iloc[0]["tind_c"])
        stat_rows.append(calculate_interval_statistics(tind_bef, tind_at, tind_aft, f"Nhiệt độ cuộn kháng Tind ({active_apu})", "°C"))
        
        tl1_bef = df_apu_t_win[df_apu_t_win["timestamp"] < event_timestamp]["tl1_c"]
        tl1_aft = df_apu_t_win[df_apu_t_win["timestamp"] > event_timestamp]["tl1_c"]
        tl1_at = float(df_apu_t_win.sort_values("diff_t").iloc[0]["tl1_c"])
        stat_rows.append(calculate_interval_statistics(tl1_bef, tl1_at, tl1_aft, f"Nhiệt độ van IGBT TL1 ({active_apu})", "°C"))

    # C. Điện áp & Dòng điện 10s
    if not df_10s_win.empty:
        v_bef = df_10s_win[df_10s_win["timestamp"] < event_timestamp]["vl1n_v"]
        v_aft = df_10s_win[df_10s_win["timestamp"] > event_timestamp]["vl1n_v"]
        df_10s_win["diff_t"] = (df_10s_win["timestamp"] - event_timestamp).abs()
        v_at = float(df_10s_win.sort_values("diff_t").iloc[0]["vl1n_v"])
        stat_rows.append(calculate_interval_statistics(v_bef, v_at, v_aft, f"Điện áp Pha L1 VL1N ({active_apu})", "V"))
        
        f_bef = df_10s_win[df_10s_win["timestamp"] < event_timestamp]["f_hz"]
        f_aft = df_10s_win[df_10s_win["timestamp"] > event_timestamp]["f_hz"]
        f_at = float(df_10s_win.sort_values("diff_t").iloc[0]["f_hz"])
        stat_rows.append(calculate_interval_statistics(f_bef, f_at, f_aft, "Tần số lưới điện", "Hz"))

    return {
        "observations_table": pd.DataFrame(stat_rows),
        "df_power_win": df_p_win,
        "df_apu_t_win": df_apu_t_win,
        "df_aps_t_win": df_aps_t_win,
        "df_10s_win": df_10s_win,
        "df_weather_win": df_w_win,
        "active_apu": active_apu
    }
