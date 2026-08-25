"""
02_Generation.py
================
Module 01: Phân tích Công suất & Hiệu suất Phát điện (Generation & Power Performance).
Datasets: power_report.parquet, weather_report.parquet, energy_report.parquet
"""

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import load_power_report, load_weather_report
from utils.time_filter import render_time_sidebar, apply_time_filter
from utils.aggregation import compute_plant_power_totals, rank_inverters
from utils.plotting import (
    plot_timeseries_dual_axis,
    plot_scatter_correlation,
    plot_inverter_ranking_bar
)

st.set_page_config(page_title="Generation & Power - Solar PV", page_icon="⚡", layout="wide")
st.title("⚡ Module 01 — Công Suất & Hiệu Suất Phát Điện (Generation & Power)")

# Time controls
time_config = render_time_sidebar()

df_power_raw = load_power_report()
if df_power_raw.empty:
    st.error("Không tải được dữ liệu Power Report!")
    st.stop()

# Lọc thời gian
df_filtered = apply_time_filter(df_power_raw, time_config)
if df_filtered.empty:
    st.warning("Không có dữ liệu trong khoảng thời gian đã chọn!")
    st.stop()

df_totals = compute_plant_power_totals(df_filtered)

# Inverter Selector
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔌 Lọc Inverter (Inverter Selection)")
ac_cols = [c for c in df_power_raw.columns if c.endswith("_ac_kw")]
inverter_list = ["ALL (Toàn nhà máy)"] + sorted([c.replace("_ac_kw", "") for c in ac_cols])
selected_inverter = st.sidebar.selectbox("Chọn Inverter khảo sát:", inverter_list, index=0)

# Section A: Plant Power / Selected Inverter Profile
st.subheader("📈 1. Đường Cong Công Suất Phát & Bức Xạ (Power & Radiation Profile)")

rad_col = "radiation_clipped_w_m2" if "radiation_clipped_w_m2" in df_totals.columns else "radiation_w_m2"

if selected_inverter == "ALL (Toàn nhà máy)":
    fig_power = plot_timeseries_dual_axis(
        df=df_totals,
        x_col="timestamp",
        y1_cols=["plant_ac_mw", "plant_dc_mw"],
        y2_cols=[rad_col],
        y1_names=["Công suất phát AC (MW)", "Công suất chuỗi DC (MW)"],
        y2_names=["Cường độ bức xạ (W/m²)"],
        y1_title="Công suất (MW)",
        y2_title="Bức xạ (W/m²)",
        title=f"Đặc Tuyến Công Suất Toàn Trạm [{time_config['view_mode']}]",
        y1_colors=["#FF9900", "#0066CC"],
        y2_colors=["#FFCC00"]
    )
else:
    ac_c = f"{selected_inverter}_ac_kw"
    dc_c = f"{selected_inverter}_dc_kw"
    fig_power = plot_timeseries_dual_axis(
        df=df_totals,
        x_col="timestamp",
        y1_cols=[ac_c, dc_c],
        y2_cols=[rad_col],
        y1_names=[f"{selected_inverter} AC (kW)", f"{selected_inverter} DC (kW)"],
        y2_names=["Bức xạ (W/m²)"],
        y1_title="Công suất (kW)",
        y2_title="Bức xạ (W/m²)",
        title=f"Đặc Tuyến Công Suất Inverter: {selected_inverter} [{time_config['view_mode']}]",
        y1_colors=["#FF9900", "#0066CC"],
        y2_colors=["#FFCC00"]
    )

st.plotly_chart(fig_power, use_container_width=True)

# Section B: Radiation vs Power & Efficiency
col1, col2 = st.columns(2)
with col1:
    st.subheader("🔍 2. Tương Quan Bức Xạ vs Công Suất AC")
    if selected_inverter == "ALL (Toàn nhà máy)":
        y_scatter = "plant_ac_mw"
        y_label = "Công suất AC toàn trạm (MW)"
    else:
        y_scatter = f"{selected_inverter}_ac_kw"
        y_label = f"Công suất AC {selected_inverter} (kW)"
        
    fig_rad_p = plot_scatter_correlation(
        df=df_totals[df_totals[rad_col] > 20.0],
        x_col=rad_col,
        y_col=y_scatter,
        title="Độ Nhạy Công Suất Theo Cường Độ Nắng (Scatter)",
        x_title="Cường độ bức xạ (W/m²)",
        y_title=y_label
    )
    st.plotly_chart(fig_rad_p, use_container_width=True)

with col2:
    st.subheader("⚙️ 3. Đường Cong Hiệu Suất Biến Tần (Efficiency Curve)")
    if selected_inverter == "ALL (Toàn nhà máy)":
        df_eff = df_totals[(df_totals["plant_dc_kw"] >= 50.0) & (df_totals[rad_col] > 50.0)]
        fig_eff = plot_scatter_correlation(
            df=df_eff,
            x_col="plant_dc_mw",
            y_col="plant_efficiency_pct",
            title="Hiệu Suất Chuyển Đổi η (%) Theo Tải DC Toàn Trạm",
            x_title="Công suất DC (MW)",
            y_title="Hiệu suất chuyển đổi (%)"
        )
    else:
        ac_c = f"{selected_inverter}_ac_kw"
        dc_c = f"{selected_inverter}_dc_kw"
        df_inv_eff = df_totals[df_totals[dc_c] >= 10.0].copy()
        df_inv_eff["inv_eff"] = (df_inv_eff[ac_c] / df_inv_eff[dc_c] * 100.0).clip(0, 100)
        fig_eff = plot_scatter_correlation(
            df=df_inv_eff,
            x_col=dc_c,
            y_col="inv_eff",
            title=f"Hiệu Suất Chuyển Đổi η (%) {selected_inverter}",
            x_title="Công suất DC (kW)",
            y_title="Hiệu suất (%)"
        )
    st.plotly_chart(fig_eff, use_container_width=True)

# Section C: Inverter Rankings
st.markdown("---")
st.subheader("🏆 4. Bảng Xếp Hạng & So Sánh 102 Inverter (Inverter Rankings)")

df_ranks = rank_inverters(df_filtered)

tab_top, tab_bot, tab_all = st.tabs(["⭐ Top 10 Hiệu Quả Nhất", "⚠️ Bottom 10 Thấp Nhất", "📋 Toàn Bộ 102 Inverter"])

with tab_top:
    top10 = df_ranks.head(10)
    fig_top = plot_inverter_ranking_bar(top10, metric_col="energy_mwh", title="Top 10 Inverter Có Sản Lượng Cao Nhất (MWh)", top_n=10)
    st.plotly_chart(fig_top, use_container_width=True)
    st.dataframe(top10.style.format({"energy_mwh": "{:.2f}", "peak_ac_kw": "{:.1f}", "avg_ac_kw": "{:.1f}", "mean_efficiency_pct": "{:.2f}%"}))

with tab_bot:
    bot10 = df_ranks.tail(10)
    fig_bot = plot_inverter_ranking_bar(bot10, metric_col="energy_mwh", title="Bottom 10 Inverter Có Sản Lượng Thấp Nhất (MWh)", top_n=10)
    st.plotly_chart(fig_bot, use_container_width=True)
    st.dataframe(bot10.style.format({"energy_mwh": "{:.2f}", "peak_ac_kw": "{:.1f}", "avg_ac_kw": "{:.1f}", "mean_efficiency_pct": "{:.2f}%"}))

with tab_all:
    st.dataframe(
        df_ranks.style.format({
            "energy_mwh": "{:.2f}",
            "peak_ac_kw": "{:.1f}",
            "avg_ac_kw": "{:.1f}",
            "mean_efficiency_pct": "{:.2f}%"
        }),
        use_container_width=True
    )
