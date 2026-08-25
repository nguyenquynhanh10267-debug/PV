"""
03_Environment_Thermal.py
=========================
Module 02: Phân tích Môi trường & Hành vi Nhiệt (Environmental & Thermal Behavior).
Datasets: weather_report.parquet, aps_stat_60s.parquet, apu_stat_60s.parquet, power_report.parquet
"""

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import load_weather_report, load_aps_stat_60s, load_apu_stat_60s, load_power_report
from utils.time_filter import render_time_sidebar, apply_time_filter
from utils.plotting import plot_timeseries_dual_axis, plot_scatter_correlation

st.set_page_config(page_title="Environment & Thermal - Solar PV", page_icon="🌡️", layout="wide")
st.title("🌡️ Module 02 — Môi Trường & Hành Vi Nhiệt (Environment & Thermal)")

time_config = render_time_sidebar()

df_aps_raw = load_aps_stat_60s()
df_apu_raw = load_apu_stat_60s()
df_weather_raw = load_weather_report()

df_aps = apply_time_filter(df_aps_raw, time_config)
df_apu = apply_time_filter(df_apu_raw, time_config)

if df_aps.empty or df_apu.empty:
    st.warning("Không có dữ liệu nhiệt độ trong khoảng thời gian đã chọn!")
    st.stop()

# APU Selector
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Chọn Ngăn Biến Tần (APU Unit)")
apu_list = sorted(df_apu["system"].unique().tolist())
selected_apu = st.sidebar.selectbox("Chọn APU:", apu_list, index=0)

df_apu_selected = df_apu[df_apu["system"] == selected_apu].reset_index(drop=True)

# 1. Thermal Curves of Inverter Components
st.subheader("🔥 1. Diễn Biến Nhiệt Độ Cuộn Kháng AC & Van Bán Dẫn IGBT")
fig_thermal = plot_timeseries_dual_axis(
    df=df_apu_selected,
    x_col="timestamp",
    y1_cols=["tind_c", "tl1_c", "tl2_c", "tl3_c"],
    y2_cols=["hum_pct_rh"],
    y1_names=["Nhiệt độ cuộn kháng AC Tind (°C)", "IGBT Pha L1 (°C)", "IGBT Pha L2 (°C)", "IGBT Pha L3 (°C)"],
    y2_names=["Độ ẩm không khí (%RH)"],
    y1_title="Nhiệt độ thành phần (°C)",
    y2_title="Độ ẩm (%RH)",
    title=f"Đặc Tuyến Phát Nhiệt Cuộn Kháng & IGBT - {selected_apu} [{time_config['view_mode']}]",
    y1_colors=["#9B2226", "#E63946", "#F4A261", "#2A9D8F"],
    y2_colors=["#457B9D"]
)
st.plotly_chart(fig_thermal, use_container_width=True)

# 2. Ambient & Transformer Temperature
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏭 2. Nhiệt Độ Môi Trường & Máy Biến Áp (APS Station)")
    fig_station = plot_timeseries_dual_axis(
        df=df_aps,
        x_col="timestamp",
        y1_cols=["ttrans_c", "tamb_c"],
        y2_cols=[],
        y1_names=["Nhiệt độ Máy Biến Áp (°C)", "Nhiệt độ Môi Trường (°C)"],
        y1_title="Nhiệt độ (°C)",
        title="Nhiệt Độ Trạm Biến Áp APS",
        y1_colors=["#D62828", "#457B9D"]
    )
    st.plotly_chart(fig_station, use_container_width=True)

with col2:
    st.subheader("⚡ 3. An Toàn Cách Điện DC (Insulation Resistance Riso)")
    fig_iso = plot_timeseries_dual_axis(
        df=df_aps,
        x_col="timestamp",
        y1_cols=["riso12_kohm", "riso34_kohm"],
        y2_cols=["cleak12_uf"],
        y1_names=["Điện trở cách điện String 1-2 (kΩ)", "Điện trở cách điện String 3-4 (kΩ)"],
        y2_names=["Điện dung rò rỉ (µF)"],
        y1_title="Điện trở Riso (kΩ)",
        y2_title="Điện dung rò (µF)",
        title="Giám Sát Cách Điện DC & Rò Rỉ Đất",
        y1_colors=["#2A9D8F", "#264653"],
        y2_colors=["#E76F51"]
    )
    st.plotly_chart(fig_iso, use_container_width=True)

# 3. Correlation: Thermal Rise vs Ambient
st.markdown("---")
st.subheader("🔍 4. Tương Quan Nhiệt Độ Cuộn Kháng vs Nhiệt Độ Môi Trường")

# Join APS ambient với APU thermal
merged_thermal = pd.merge_asof(
    df_apu_selected.sort_values("timestamp"),
    df_aps[["timestamp", "tamb_c", "ttrans_c"]].sort_values("timestamp"),
    on="timestamp",
    direction="nearest"
)
merged_thermal["thermal_rise_c"] = merged_thermal["tind_c"] - merged_thermal["tamb_c"]

fig_rise = plot_scatter_correlation(
    df=merged_thermal[merged_thermal["tamb_c"] > 0],
    x_col="tamb_c",
    y_col="tind_c",
    color_col="thermal_rise_c",
    title=f"Mức Độ Tăng Nhiệt Cuộn Kháng AC (Tind) Theo Nhiệt Độ Môi Trường (Tamb) - {selected_apu}",
    x_title="Nhiệt độ môi trường trạm Tamb (°C)",
    y_title="Nhiệt độ cuộn kháng AC Tind (°C)",
    color_title="Độ tăng nhiệt ΔT (°C)"
)
st.plotly_chart(fig_rise, use_container_width=True)
