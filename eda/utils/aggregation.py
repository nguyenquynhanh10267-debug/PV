"""
aggregation.py
==============
Các hàm tổng hợp dữ liệu (Daily, Hourly, Plant totals, Inverter rankings).
"""

from typing import List, Tuple, Optional, Dict
import pandas as pd
import numpy as np


def compute_plant_power_totals(df_power: pd.DataFrame) -> pd.DataFrame:
    """Tính tổng công suất AC (kW), DC (kW), và Hiệu suất toàn trạm."""
    if df_power.empty:
        return df_power
        
    df = df_power.copy()
    ac_cols = [c for c in df.columns if c.endswith("_ac_kw")]
    dc_cols = [c for c in df.columns if c.endswith("_dc_kw")]
    
    df["plant_ac_kw"] = df[ac_cols].sum(axis=1)
    df["plant_dc_kw"] = df[dc_cols].sum(axis=1)
    
    # Tính công suất MW
    df["plant_ac_mw"] = df["plant_ac_kw"] / 1000.0
    df["plant_dc_mw"] = df["plant_dc_kw"] / 1000.0
    
    # Hiệu suất toàn trạm (%) khi DC > 50 kW
    valid_mask = (df["plant_dc_kw"] >= 50.0)
    df["plant_efficiency_pct"] = np.where(
        valid_mask,
        (df["plant_ac_kw"] / df["plant_dc_kw"]) * 100.0,
        np.nan
    )
    # Clip hiệu suất vật lý hợp lý [0, 100%]
    df["plant_efficiency_pct"] = df["plant_efficiency_pct"].clip(lower=0.0, upper=100.0)
    return df


def aggregate_power_daily(df_power_with_totals: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp dữ liệu công suất theo Ngày cho View A Overview."""
    if df_power_with_totals.empty or "timestamp" not in df_power_with_totals.columns:
        return pd.DataFrame()
        
    df = df_power_with_totals.copy()
    df["date"] = df["timestamp"].dt.date
    
    rad_col = "radiation_clipped_w_m2" if "radiation_clipped_w_m2" in df.columns else "radiation_w_m2"
    
    daily_records = []
    for d, grp in df.groupby("date"):
        # Tích phân năng lượng ngày (MWh) = sum(kW) * (1/60h) / 1000
        daily_energy_ac_mwh = grp["plant_ac_kw"].sum() / 60000.0
        daily_energy_dc_mwh = grp["plant_dc_kw"].sum() / 60000.0
        
        peak_ac_mw = grp["plant_ac_mw"].max()
        peak_dc_mw = grp["plant_dc_mw"].max()
        avg_ac_mw = grp["plant_ac_mw"].mean()
        
        # Bức xạ trung bình và tích lũy (kWh/m2/day) = sum(W/m2) * (1/60h) / 1000
        rad_insolation = grp[rad_col].sum() / 60000.0 if rad_col in grp.columns else np.nan
        mean_rad = grp[rad_col].mean() if rad_col in grp.columns else np.nan
        
        # Hiệu suất trung bình ban ngày (khi có nắng G > 50 W/m2)
        daylight = grp[grp[rad_col] > 50.0] if rad_col in grp.columns else grp
        mean_eff = daylight["plant_efficiency_pct"].mean() if not daylight.empty else grp["plant_efficiency_pct"].mean()
        
        daily_records.append({
            "date": pd.to_datetime(d),
            "daily_energy_ac_mwh": daily_energy_ac_mwh,
            "daily_energy_dc_mwh": daily_energy_dc_mwh,
            "peak_ac_power_mw": peak_ac_mw,
            "peak_dc_power_mw": peak_dc_mw,
            "avg_ac_power_mw": avg_ac_mw,
            "daily_insolation_kwh_m2": rad_insolation,
            "mean_radiation_w_m2": mean_rad,
            "mean_efficiency_pct": mean_eff,
            "sample_count": len(grp)
        })
        
    return pd.DataFrame(daily_records)


def aggregate_power_hourly(df_power_with_totals: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp dữ liệu công suất theo Giờ cho View A / View C."""
    if df_power_with_totals.empty or "timestamp" not in df_power_with_totals.columns:
        return pd.DataFrame()
        
    df = df_power_with_totals.copy()
    df["hourly_dt"] = df["timestamp"].dt.floor("1h")
    
    rad_col = "radiation_clipped_w_m2" if "radiation_clipped_w_m2" in df.columns else "radiation_w_m2"
    
    hourly_df = df.groupby("hourly_dt").agg({
        "plant_ac_mw": ["mean", "max"],
        "plant_dc_mw": ["mean", "max"],
        rad_col: "mean",
        "plant_efficiency_pct": "mean"
    }).reset_index()
    
    hourly_df.columns = [
        "timestamp", "avg_ac_mw", "peak_ac_mw", "avg_dc_mw", "peak_dc_mw",
        "mean_radiation_w_m2", "mean_efficiency_pct"
    ]
    return hourly_df


def rank_inverters(df_power: pd.DataFrame) -> pd.DataFrame:
    """Xếp hạng 102 Inverter theo Sản lượng (MWh), Công suất đỉnh, Hiệu suất."""
    if df_power.empty:
        return pd.DataFrame()
        
    ac_cols = [c for c in df_power.columns if c.endswith("_ac_kw")]
    dc_cols = [c for c in df_power.columns if c.endswith("_dc_kw")]
    
    inverter_stats = []
    for ac_c in ac_cols:
        inv_id = ac_c.replace("_ac_kw", "")
        dc_c = f"{inv_id}_dc_kw"
        
        ac_series = df_power[ac_c]
        dc_series = df_power[dc_c] if dc_c in df_power.columns else pd.Series(np.nan, index=df_power.index)
        
        # Sản lượng MWh = sum(kW) * 1/60 / 1000
        energy_mwh = ac_series.sum() / 60000.0
        peak_kw = ac_series.max()
        avg_kw = ac_series.mean()
        
        # Hiệu suất
        valid = (dc_series >= 10.0)
        eff = (ac_series[valid] / dc_series[valid] * 100.0).mean() if valid.sum() > 0 else np.nan
        
        block_name = inv_id.split("_inv_")[0].replace("_", " ").upper()
        
        inverter_stats.append({
            "inverter_id": inv_id,
            "block": block_name,
            "energy_mwh": energy_mwh,
            "peak_ac_kw": peak_kw,
            "avg_ac_kw": avg_kw,
            "mean_efficiency_pct": min(eff, 100.0) if not np.isnan(eff) else np.nan
        })
        
    res_df = pd.DataFrame(inverter_stats).sort_values("energy_mwh", ascending=False).reset_index(drop=True)
    res_df["rank"] = np.arange(1, len(res_df) + 1)
    return res_df
