"""
04_Electrical.py
================
Module 03: Động học Điện Lực Cao Tần 10 Giây (Electrical 10s Dynamics).
Datasets: apu_stat_10s.parquet, apu_ctrl_trig.parquet, apu_stat_60s.parquet
"""

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import load_apu_stat_10s
from utils.time_filter import render_time_sidebar
from metrics import compute_voltage_unbalance, compute_power_factor
from utils.plotting import (
    plot_timeseries_dual_axis,
    plot_pq_capability_diagram,
    plot_scatter_correlation
)

st.set_page_config(page_title="Electrical 10s - Solar PV", page_icon="🔬", layout="wide")
st.title("🔬 Module 03 — Động Học Điện Lực Cao Tần 10 Giây (High-Frequency Electrical)")

time_config = render_time_sidebar()

# APU Selector
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Chọn Ngăn Biến Tần (APU Unit)")
selected_apu = st.sidebar.selectbox("Chọn APU:", ["APU 1", "APU 2", "APU 3", "APU 4"], index=0)

# Nạp dữ liệu 10s theo ngày để tối ưu RAM
target_date_str = str(time_config["selected_date"]) if time_config["view_mode"] == "VIEW B: Single Day Deep-Dive" else None
df_10s_raw = load_apu_stat_10s(selected_date=target_date_str, system=selected_apu)

if df_10s_raw.empty:
    st.warning(f"Không có dữ liệu 10 giây cho {selected_apu} vào ngày {target_date_str or 'đã chọn'}!")
    st.stop()

# Lọc theo giờ nếu ở View B
h_start, h_end = time_config["hour_range"]
df_10s = df_10s_raw[(df_10s_raw["timestamp"].dt.hour >= h_start) & (df_10s_raw["timestamp"].dt.hour <= h_end)].reset_index(drop=True)

if df_10s.empty:
    st.warning("Không có dữ liệu trong khoảng giờ đã chọn!")
    st.stop()

# Tính các chỉ số dẫn xuất
df_10s["voltage_unbalance_pct"] = compute_voltage_unbalance(df_10s)
df_10s["power_factor"] = compute_power_factor(df_10s)
df_10s["p_total_kw"] = df_10s["pl1_kw"] + df_10s["pl2_kw"] + df_10s["pl3_kw"]
df_10s["q_total_kvar"] = df_10s["ql1_kvar"] + df_10s["ql2_kvar"] + df_10s["ql3_kvar"]

# 1. 3-Phase AC Voltage & Unbalance
st.subheader("⚡ 1. Điện Áp 3 Pha AC & Độ Lệch Pha (Voltage Balance)")
fig_voltage = plot_timeseries_dual_axis(
    df=df_10s,
    x_col="timestamp",
    y1_cols=["vl1n_v", "vl2n_v", "vl3n_v"],
    y2_cols=["voltage_unbalance_pct"],
    y1_names=["Điện áp Pha A (VL1N)", "Điện áp Pha B (VL2N)", "Điện áp Pha C (VL3N)"],
    y2_names=["Độ lệch pha VU (%)"],
    y1_title="Điện áp pha (V)",
    y2_title="Lệch pha (%)",
    title=f"Đặc Tuyến Điện Áp 3 Pha 10s - {selected_apu}",
    y1_colors=["#E63946", "#F4A261", "#2A9D8F"],
    y2_colors=["#9B2226"]
)
st.plotly_chart(fig_voltage, use_container_width=True)

# 2. 3-Phase AC Current
col1, col2 = st.columns(2)
with col1:
    st.subheader("🔌 2. Dòng Điện Phát 3 Pha AC (10-Second Currents)")
    fig_current = plot_timeseries_dual_axis(
        df=df_10s,
        x_col="timestamp",
        y1_cols=["il1_a", "il2_a", "il3_a"],
        y2_cols=[],
        y1_names=["Dòng pha IL1 (A)", "Dòng pha IL2 (A)", "Dòng pha IL3 (A)"],
        y1_title="Dòng điện AC (A)",
        title=f"Dòng Điện Phát 3 Pha - {selected_apu}",
        y1_colors=["#E63946", "#F4A261", "#2A9D8F"]
    )
    st.plotly_chart(fig_current, use_container_width=True)

with col2:
    st.subheader("🌐 3. Tần Số Lưới Điện & Ổn Định Hệ Thống (Grid Frequency)")
    fig_freq = plot_timeseries_dual_axis(
        df=df_10s,
        x_col="timestamp",
        y1_cols=["f_hz"],
        y2_cols=[],
        y1_names=["Tần số lưới f (Hz)"],
        y1_title="Tần số (Hz)",
        title="Biến Thiên Tần Số Lưới (Chuẩn 50.0 Hz)",
        y1_colors=["#6A4C93"]
    )
    st.plotly_chart(fig_freq, use_container_width=True)

# 3. Active vs Reactive Power & P-Q Capability
st.markdown("---")
col_pq1, col_pq2 = st.columns(2)

with col_pq1:
    st.subheader("📊 4. Công Suất Tác Dụng P & Phản Kháng Q")
    fig_pq_time = plot_timeseries_dual_axis(
        df=df_10s,
        x_col="timestamp",
        y1_cols=["p_total_kw"],
        y2_cols=["q_total_kvar"],
        y1_names=["Tổng công suất tác dụng P (kW)"],
        y2_names=["Tổng công suất phản kháng Q (kVar)"],
        y1_title="Công suất tác dụng P (kW)",
        y2_title="Công suất phản kháng Q (kVar)",
        title=f"Đặc Tuyến P & Q - {selected_apu}",
        y1_colors=["#1D3557"],
        y2_colors=["#457B9D"]
    )
    st.plotly_chart(fig_pq_time, use_container_width=True)

with col_pq2:
    st.subheader("🎯 5. Biểu Đồ Khả Năng Phát P-Q (Capability Diagram)")
    fig_pq_cap = plot_pq_capability_diagram(
        df_10s=df_10s[df_10s["p_total_kw"] > 5.0],
        p_col="p_total_kw",
        q_col="q_total_kvar",
        title=f"P-Q Operating Trajectory - {selected_apu}"
    )
    st.plotly_chart(fig_pq_cap, use_container_width=True)
