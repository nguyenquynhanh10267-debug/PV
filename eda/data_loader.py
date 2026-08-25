"""
data_loader.py
==============
Module nạp dữ liệu Parquet với bộ nhớ đệm @st.cache_data và Lazy Loading tối ưu.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import pandas as pd
import streamlit as st

from config import PROCESSED_DIR, REPORTS_DIR


@st.cache_data(show_spinner="Đang tải dữ liệu Power Report...")
def load_power_report() -> pd.DataFrame:
    """Nạp dữ liệu chuỗi công suất AC/DC 102 Inverter (1 phút)."""
    p = PROCESSED_DIR / "power_report.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(show_spinner="Đang tải dữ liệu Weather Report...")
def load_weather_report() -> pd.DataFrame:
    """Nạp dữ liệu thời tiết SCADA (1 giờ tháng 10 / 1 phút tháng 9)."""
    p = PROCESSED_DIR / "weather_report.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    # Mặc định lọc dải đo tháng 10/2025
    df_oct = df[(df["timestamp"] >= "2025-10-01") & (df["timestamp"] <= "2025-10-27 23:59:59")].reset_index(drop=True)
    return df_oct if not df_oct.empty else df


@st.cache_data(show_spinner="Đang tải dữ liệu Energy Report...")
def load_energy_report() -> pd.DataFrame:
    """Nạp dữ liệu sản lượng công tơ MWh 103 Inverter (1 giờ)."""
    p = PROCESSED_DIR / "energy_report.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(show_spinner="Đang tải dữ liệu APS Stat 60s...")
def load_aps_stat_60s() -> pd.DataFrame:
    """Nạp dữ liệu nhiệt độ môi trường trạm, máy biến áp và cách điện DC (1 phút)."""
    p = PROCESSED_DIR / "aps_stat_60s.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(show_spinner="Đang tải dữ liệu APU Stat 60s...")
def load_apu_stat_60s() -> pd.DataFrame:
    """Nạp dữ liệu nhiệt độ cuộn kháng AC và van bán dẫn IGBT 4 APU (1 phút)."""
    p = PROCESSED_DIR / "apu_stat_60s.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(show_spinner="Đang tải dữ liệu APU Stat 10s...")
def load_apu_stat_10s(selected_date: Optional[str] = None, system: Optional[str] = None) -> pd.DataFrame:
    """Nạp dữ liệu động học điện lực 10 giây (cho phép lọc theo ngày và ngăn APU)."""
    p = PROCESSED_DIR / "apu_stat_10s.parquet"
    if not p.exists():
        return pd.DataFrame()
        
    df = pd.read_parquet(p)
    if selected_date:
        df = df[df["timestamp"].dt.date == pd.to_datetime(selected_date).date()]
    if system and system != "ALL":
        df = df[df["system"] == system]
    return df.reset_index(drop=True)


@st.cache_data(show_spinner="Đang tải dữ liệu APS Energy...")
def load_aps_energy() -> pd.DataFrame:
    """Nạp dữ liệu năng lượng tự dùng và phát trạm APS (1 phút)."""
    p = PROCESSED_DIR / "aps_energy.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(show_spinner="Đang tải dữ liệu APU Energy...")
def load_apu_energy() -> pd.DataFrame:
    """Nạp dữ liệu dòng điện tích lũy 12 string CMB (1 phút)."""
    p = PROCESSED_DIR / "apu_energy.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(show_spinner="Đang tải nhật ký sự kiện & cảnh báo...")
def load_event_datasets() -> Dict[str, pd.DataFrame]:
    """Nạp toàn bộ 4 file trigger và 1 file switching cycles."""
    datasets = {}
    files = {
        "aps_ctrl_trig": "aps_ctrl_trig.parquet",
        "aps_stat_trig": "aps_stat_trig.parquet",
        "apu_ctrl_trig": "apu_ctrl_trig.parquet",
        "apu_stat_trig": "apu_stat_trig.parquet",
        "aps_switching_cycles": "aps_switching_cycles.parquet"
    }
    for k, fname in files.items():
        p = PROCESSED_DIR / fname
        if p.exists():
            datasets[k] = pd.read_parquet(p)
        else:
            datasets[k] = pd.DataFrame()
    return datasets


@st.cache_data
def load_dataset_summary() -> pd.DataFrame:
    """Nạp bảng số liệu kiểm toán tổng hợp 13 dataset."""
    p = Path(r"C:\PV\dataset_audit_summary.csv")
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()
