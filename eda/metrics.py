"""
metrics.py
==========
Thư viện tính toán các đại lượng vật lý, chỉ số hiệu suất, và sàng lọc dị thường Solar PV.
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np


def compute_voltage_unbalance(df_10s: pd.DataFrame) -> pd.Series:
    """Tính độ lệch pha điện áp Voltage Unbalance (%) theo chuẩn IEC 61000-4-30."""
    v_cols = ["vl1n_v", "vl2n_v", "vl3n_v"]
    if not all(c in df_10s.columns for c in v_cols):
        return pd.Series(np.nan, index=df_10s.index)
        
    v_avg = (df_10s["vl1n_v"] + df_10s["vl2n_v"] + df_10s["vl3n_v"]) / 3.0
    v_dev1 = (df_10s["vl1n_v"] - v_avg).abs()
    v_dev2 = (df_10s["vl2n_v"] - v_avg).abs()
    v_dev3 = (df_10s["vl3n_v"] - v_avg).abs()
    
    max_dev = pd.concat([v_dev1, v_dev2, v_dev3], axis=1).max(axis=1)
    vu_pct = np.where(v_avg > 50.0, (max_dev / v_avg) * 100.0, 0.0)
    return pd.Series(vu_pct, index=df_10s.index)


def compute_power_factor(df_10s: pd.DataFrame) -> pd.Series:
    """Tính hệ số công suất cos(phi) = P / sqrt(P^2 + Q^2)."""
    p_cols = ["pl1_kw", "pl2_kw", "pl3_kw"]
    q_cols = ["ql1_kvar", "ql2_kvar", "ql3_kvar"]
    
    if all(c in df_10s.columns for c in p_cols) and all(c in df_10s.columns for c in q_cols):
        p_tot = df_10s[p_cols].sum(axis=1)
        q_tot = df_10s[q_cols].sum(axis=1)
        s_tot = np.sqrt(p_tot**2 + q_tot**2)
        pf = np.where(s_tot > 1.0, p_tot / s_tot, 1.0)
        return pd.Series(pf, index=df_10s.index)
    return pd.Series(np.nan, index=df_10s.index)


def compute_energy_reconciliation(df_power: pd.DataFrame, df_energy: pd.DataFrame) -> pd.DataFrame:
    """Đối soát sản lượng điện: Tích phân công suất 1 phút vs Số nhảy công tơ giờ."""
    if df_power.empty or df_energy.empty:
        return pd.DataFrame()
        
    df_p = df_power.copy()
    ac_cols = [c for c in df_p.columns if c.endswith("_ac_kw")]
    df_p["plant_ac_kw"] = df_p[ac_cols].sum(axis=1)
    df_p["date"] = df_p["timestamp"].dt.date
    
    # 1. Tích phân công suất ngày (MWh)
    p_daily = df_p.groupby("date")["plant_ac_kw"].sum() / 60000.0
    
    # 2. Số nhảy công tơ ngày từ energy_report (MWh)
    df_e = df_energy.copy()
    inv_mwh_cols = [c for c in df_e.columns if c.endswith("_mwh")]
    df_e["plant_meter_mwh"] = df_e[inv_mwh_cols].sum(axis=1)
    df_e["date"] = df_e["timestamp"].dt.date
    
    e_daily_records = {}
    for d, grp in df_e.groupby("date"):
        start_val = grp.iloc[0]["plant_meter_mwh"]
        end_val = grp.iloc[-1]["plant_meter_mwh"]
        e_daily_records[d] = max(0.0, end_val - start_val)
        
    e_daily = pd.Series(e_daily_records)
    
    # Ghép 2 nguồn
    rec_df = pd.DataFrame({
        "integrated_mwh": p_daily,
        "meter_mwh": e_daily
    }).dropna().reset_index()
    rec_df.rename(columns={"index": "date"}, inplace=True)
    rec_df["date"] = pd.to_datetime(rec_df["date"])
    
    rec_df["abs_error_mwh"] = (rec_df["meter_mwh"] - rec_df["integrated_mwh"]).abs()
    rec_df["error_pct"] = np.where(
        rec_df["meter_mwh"] > 0,
        (rec_df["abs_error_mwh"] / rec_df["meter_mwh"]) * 100.0,
        0.0
    )
    return rec_df


def compute_switching_increments(df_switching: pd.DataFrame) -> pd.DataFrame:
    """Tính số lần đóng cắt gia tăng hàng ngày của contactor 4 APU."""
    if df_switching.empty or "timestamp" not in df_switching.columns:
        return pd.DataFrame()
        
    df = df_switching.copy()
    df["date"] = df["timestamp"].dt.date
    counter_cols = [c for c in df.columns if c not in ["log_type", "system", "timestamp", "date"]]
    
    # Lấy giá trị chốt cuối ngày
    daily_last = df.groupby("date")[counter_cols].last()
    daily_increments = daily_last.diff().fillna(0).clip(lower=0)
    daily_increments = daily_increments.reset_index()
    daily_increments["date"] = pd.to_datetime(daily_increments["date"])
    return daily_increments
