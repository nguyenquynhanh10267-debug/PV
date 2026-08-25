"""
06_Reliability.py
=================
Module 05: Độ Tin Cậy & Chu Kỳ Đóng Cắt Contactor (Reliability & Switching Cycles).
Datasets: aps_switching_cycles.parquet, aps_stat_trig.parquet
"""

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import load_event_datasets
from utils.time_filter import render_time_sidebar
from metrics import compute_switching_increments
from utils.plotting import plot_timeseries_dual_axis

st.set_page_config(page_title="Reliability - Solar PV", page_icon="🔄", layout="wide")
st.title("🔄 Module 05 — Độ Tin Cậy & Chu Kỳ Đóng Cắt Contactor (Reliability)")

event_data = load_event_datasets()
df_sw_raw = event_data.get("aps_switching_cycles", pd.DataFrame())

if df_sw_raw.empty:
    st.error("Không tải được dữ liệu chu kỳ đóng cắt (aps_switching_cycles)!")
    st.stop()

# 1. Diễn biến lũy kế số lần đóng cắt
st.subheader("📈 1. Số Lần Đóng Cắt Lũy Kế Contactor AC & DC (4 APU Units)")

fig_cum_sw = plot_timeseries_dual_axis(
    df=df_sw_raw,
    x_col="timestamp",
    y1_cols=["apu1_a_c", "apu2_a_c", "apu3_a_c", "apu4_a_c"],
    y2_cols=["apu1_d_c", "apu2_d_c", "apu3_d_c", "apu4_d_c"],
    y1_names=["APU 1 AC", "APU 2 AC", "APU 3 AC", "APU 4 AC"],
    y2_names=["APU 1 DC", "APU 2 DC", "APU 3 DC", "APU 4 DC"],
    y1_title="Số chu kỳ AC (Lũy kế)",
    y2_title="Số chu kỳ DC (Lũy kế)",
    title="Lũy Kế Chu Kỳ Đóng Cắt Contactor AC & DC Qua 27 Ngày",
    y1_colors=["#1D3557", "#457B9D", "#2A9D8F", "#E76F51"],
    y2_colors=["#9B2226", "#D62828", "#E63946", "#F4A261"]
)
st.plotly_chart(fig_cum_sw, use_container_width=True)

# 2. Số lần đóng cắt gia tăng hàng ngày (Daily Increments)
st.markdown("---")
st.subheader("📊 2. Số Lần Đóng Cắt Mới Hàng Ngày (Daily Switching Increments ΔCycle)")

df_inc = compute_switching_increments(df_sw_raw)
if not df_inc.empty:
    ac_inc_cols = [c for c in df_inc.columns if "_a_c" in c]
    dc_inc_cols = [c for c in df_inc.columns if "_d_c" in c]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Số lần đóng cắt Contactor AC mới mỗi ngày**")
        st.bar_chart(df_inc.set_index("date")[ac_inc_cols])
    with col2:
        st.write("**Số lần đóng cắt Contactor DC mới mỗi ngày**")
        st.bar_chart(df_inc.set_index("date")[dc_inc_cols])

# 3. Bảng tổng kết số liệu hao mòn
st.markdown("---")
st.subheader("📋 3. Bảng Tổng Hợp Hao Mòn Thiết Bị Contactor")

latest_row = df_sw_raw.iloc[-1]
initial_row = df_sw_raw.iloc[0]

summary_records = []
for apu_idx in range(1, 5):
    ac_c = f"apu{apu_idx}_a_c"
    dc_c = f"apu{apu_idx}_d_c"
    if ac_c in latest_row and dc_c in latest_row:
        ac_start = int(initial_row[ac_c])
        ac_end = int(latest_row[ac_c])
        dc_start = int(initial_row[dc_c])
        dc_end = int(latest_row[dc_c])
        
        summary_records.append({
            "Ngăn Biến Tần": f"APU {apu_idx}",
            "AC Bắt đầu": ac_start,
            "AC Hiện tại": ac_end,
            "AC Tăng thêm (27 ngày)": ac_end - ac_start,
            "DC Bắt đầu": dc_start,
            "DC Hiện tại": dc_end,
            "DC Tăng thêm (27 ngày)": dc_end - dc_start
        })

st.dataframe(pd.DataFrame(summary_records), use_container_width=True)
