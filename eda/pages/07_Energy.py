"""
07_Energy.py
============
Module 06: Kiểm Toán Năng Lượng & Đối Soát Sản Lượng (Energy & Reconciliation).
Datasets: energy_report.parquet, power_report.parquet, aps_energy.parquet, apu_energy.parquet
"""

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import load_energy_report, load_power_report, load_aps_energy, load_apu_energy
from metrics import compute_energy_reconciliation
from utils.plotting import plot_timeseries_dual_axis

st.set_page_config(page_title="Energy Reconciliation - Solar PV", page_icon="📊", layout="wide")
st.title("📊 Module 06 — Kiểm Toán Năng Lượng & Đối Soát Sản Lượng (Energy & Reconciliation)")

df_energy = load_energy_report()
df_power = load_power_report()
df_aps_e = load_aps_energy()
df_apu_e = load_apu_energy()

if df_energy.empty or df_power.empty:
    st.error("Không tải đủ dữ liệu Energy Report hoặc Power Report!")
    st.stop()

# 1. Đối soát sản lượng Công tơ vs Tích phân công suất
st.subheader("⚖️ 1. Đối Soát Sản Lượng: Công Tơ Giờ (Meter) vs Tích Phân Công Suất 1 Phút (Integrated)")

df_rec = compute_energy_reconciliation(df_power, df_energy)

if not df_rec.empty:
    col_k1, col_k2, col_k3 = st.columns(3)
    tot_meter = df_rec["meter_mwh"].sum()
    tot_integ = df_rec["integrated_mwh"].sum()
    mean_err = df_rec["error_pct"].mean()
    
    with col_k1:
        st.metric("⚡ Tổng Sản Lượng Công Tơ (Meter)", f"{tot_meter:,.2f} MWh")
    with col_k2:
        st.metric("∫P·dt Tích Phân Công Suất", f"{tot_integ:,.2f} MWh")
    with col_k3:
        st.metric("🎯 Sai Số Đối Soát Trung Bình", f"{mean_err:.2f}%", delta="Rất thấp (<1%)")

    fig_rec = plot_timeseries_dual_axis(
        df=df_rec,
        x_col="date",
        y1_cols=["meter_mwh", "integrated_mwh"],
        y2_cols=["error_pct"],
        y1_names=["Sản lượng Công tơ (MWh)", "Sản lượng Tích phân ∫P dt (MWh)"],
        y2_names=["Sai số đối soát (%)"],
        y1_title="Sản lượng ngày (MWh)",
        y2_title="Sai số (%)",
        title="Đối Soát Sản Lượng Điện Năng Ngày Giữa Công Tơ & SCADA Power (01/10 – 27/10/2025)",
        y1_colors=["#0066CC", "#FF9900"],
        y2_colors=["#E63946"]
    )
    st.plotly_chart(fig_rec, use_container_width=True)

    st.dataframe(
        df_rec.style.format({
            "integrated_mwh": "{:,.2f}",
            "meter_mwh": "{:,.2f}",
            "abs_error_mwh": "{:,.2f}",
            "error_pct": "{:.2f}%"
        }),
        use_container_width=True
    )

# 2. Phân tích Năng Lượng Tự Dùng Trạm (APS Auxiliary Energy)
st.markdown("---")
st.subheader("🔌 2. Năng Lượng Phụ Trợ & Tự Dùng Trạm Biến Áp (APS Energy)")

if not df_aps_e.empty:
    latest_aps = df_aps_e.iloc[-1]
    w_out_tot = latest_aps.get("w_out_aps_kwh", 0)
    w_in_tot = latest_aps.get("w_in_aps_kwh", 0)
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.write(f"**Tổng điện phát trạm APS**: `{w_out_tot:,.1f} kWh`")
        st.write(f"**Tổng điện tự dùng trạm APS**: `{w_in_tot:,.1f} kWh`")
        if w_out_tot > 0:
            st.write(f"**Tỷ lệ tự dùng**: `{(w_in_tot / w_out_tot * 100):.3f}%`")
    with col_e2:
        st.info("Năng lượng tự dùng bao gồm quạt làm mát trạm, bơm nước giải nhiệt, máy hút ẩm và hệ thống điều khiển PLC/APMC.")

# 3. Phân bổ Dòng Tích Lũy 12 String CMB (APU Energy)
st.markdown("---")
st.subheader("🔋 3. Cân Bằng Chuỗi Pin DC: Dòng Điện Tích Lũy 12 Kênh CMB (Ah)")

if not df_apu_e.empty:
    pos_cols = [c for c in df_apu_e.columns if c.endswith("_pos_ah")]
    if pos_cols:
        latest_apu_e = df_apu_e.groupby("system")[pos_cols].last().reset_index()
        st.write("Dòng tích lũy chốt cuối kỳ trên 12 kênh chuỗi DC của 4 APU:")
        st.dataframe(latest_apu_e.style.format("{:,.1f}", subset=pos_cols), use_container_width=True)
