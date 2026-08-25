"""
01_Overview.py
==============
Trang phân tích tổng quan toàn bộ 27 ngày (VIEW A).
"""

import streamlit as st
import pandas as pd

from data_loader import load_power_report, load_weather_report, load_event_datasets
from utils.aggregation import compute_plant_power_totals, aggregate_power_daily, aggregate_power_hourly
from utils.plotting import plot_timeseries_dual_axis, plot_scatter_correlation

st.set_page_config(page_title="27-Day Overview - Solar PV", page_icon="🌐", layout="wide")
st.title("🌐 VIEW A — Tổng Quan Toàn Bộ 27 Ngày (Full-Period Macro View)")

# Sidebar chọn độ phân giải
st.sidebar.markdown("### ⚙️ Tùy Chọn Tổng Hợp (Aggregation)")
agg_mode = st.sidebar.radio("Chọn mức độ tổng hợp:", ["Daily (Theo Ngày)", "Hourly (Theo Giờ)"], index=0)

df_power = load_power_report()
if df_power.empty:
    st.error("Không tìm thấy dữ liệu Power Report!")
    st.stop()

df_totals = compute_plant_power_totals(df_power)

if agg_mode == "Daily (Theo Ngày)":
    daily_df = aggregate_power_daily(df_totals)
    
    st.subheader("📊 Sản Lượng Năng Lượng & Bức Xạ Hàng Ngày (Daily Insolation vs Generation)")
    fig_daily = plot_timeseries_dual_axis(
        df=daily_df,
        x_col="date",
        y1_cols=["daily_energy_ac_mwh", "daily_energy_dc_mwh"],
        y2_cols=["daily_insolation_kwh_m2"],
        y1_names=["Sản lượng AC (MWh)", "Sản lượng DC (MWh)"],
        y2_names=["Bức xạ tích lũy (kWh/m²/ngày)"],
        y1_title="Sản lượng ngày (MWh)",
        y2_title="Bức xạ tích lũy (kWh/m²)",
        title="Quan Hệ Giữa Bức Xạ Đầu Vào & Sản Lượng Đầu Ra Hàng Ngày",
        y1_colors=["#FF9900", "#0066CC"],
        y2_colors=["#FFCC00"]
    )
    st.plotly_chart(fig_daily, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Công Suất Đỉnh & Hiệu Suất Trung Bình Ngày")
        fig_peak = plot_timeseries_dual_axis(
            df=daily_df,
            x_col="date",
            y1_cols=["peak_ac_power_mw"],
            y2_cols=["mean_efficiency_pct"],
            y1_names=["Công suất đỉnh AC (MW)"],
            y2_names=["Hiệu suất trung bình (%)"],
            y1_title="Công suất đỉnh (MW)",
            y2_title="Hiệu suất (%)",
            title="Biến Thiên Công Suất Đỉnh & Hiệu Suất Qua 27 Ngày",
            y1_colors=["#E63946"],
            y2_colors=["#2A9D8F"]
        )
        st.plotly_chart(fig_peak, use_container_width=True)
        
    with col2:
        st.subheader("🔍 Tương Quan Bức Xạ Ngày vs Sản Lượng Ngày")
        fig_corr = plot_scatter_correlation(
            df=daily_df,
            x_col="daily_insolation_kwh_m2",
            y_col="daily_energy_ac_mwh",
            title="Độ Nhạy Sản Lượng Theo Cường Độ Nắng (Scatter)",
            x_title="Bức xạ tích lũy (kWh/m²/ngày)",
            y_title="Sản lượng AC (MWh/ngày)"
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("### 📋 Bảng Số Liệu Vận Hành Từng Ngày")
    st.dataframe(
        daily_df.style.format({
            "daily_energy_ac_mwh": "{:,.2f}",
            "daily_energy_dc_mwh": "{:,.2f}",
            "peak_ac_power_mw": "{:.2f}",
            "peak_dc_power_mw": "{:.2f}",
            "avg_ac_power_mw": "{:.2f}",
            "daily_insolation_kwh_m2": "{:.2f}",
            "mean_efficiency_pct": "{:.2f}%"
        }),
        use_container_width=True
    )

else:  # Hourly
    hourly_df = aggregate_power_hourly(df_totals)
    st.subheader("⏱️ Chuỗi Thời Gian Công Suất Tổng Hợp Theo Giờ (Hourly Profile)")
    fig_hourly = plot_timeseries_dual_axis(
        df=hourly_df,
        x_col="timestamp",
        y1_cols=["avg_ac_mw", "peak_ac_mw"],
        y2_cols=["mean_radiation_w_m2"],
        y1_names=["Công suất AC trung bình (MW)", "Công suất đỉnh (MW)"],
        y2_names=["Cường độ bức xạ (W/m²)"],
        y1_title="Công suất (MW)",
        y2_title="Bức xạ (W/m²)",
        title="Đường Cong Công Suất & Bức Xạ Tổng Hợp Theo Giờ (01/10 – 27/10/2025)",
        y1_colors=["#FF9900", "#E63946"],
        y2_colors=["#FFCC00"]
    )
    st.plotly_chart(fig_hourly, use_container_width=True)
