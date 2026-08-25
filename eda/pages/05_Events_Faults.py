"""
05_Events_Faults.py
===================
MODULE 05 — HỆ THỐNG ĐIỀU TRA SỰ CỐ & PHÂN TÍCH LỖI THIẾT BỊ (EVENTS & FAULTS INVESTIGATION)
Nguyên tắc cốt lõi: Hướng sự kiện (Event-Driven), Chỉ hiển thị thiết bị thực tế phát sinh lỗi (Device-Specific Layers),
Dòng thời gian chi tiết theo ngày được chọn (Daily Event Timeline), Ánh xạ chuẩn từ config.py, và Phân tích Trước lỗi/Tại thời điểm lỗi/Sau lỗi.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

from config import (
    COLORS,
    PLOTLY_TEMPLATE,
    APS_ERROR_WINDOW_SECONDS,
    MIN_DATE_STR,
    MAX_DATE_STR,
    ERROR_CODES_APS,
    ERROR_CODES_APU,
    WARNING_CODES,
    OPSTATE_MAP
)
from data_loader import load_event_datasets
from fault_engine import (
    build_standard_fault_events,
    calculate_daily_event_breakdown,
    calculate_hourly_event_histogram,
    group_events_into_episodes,
    extract_correlated_signals_robust,
    get_error_description,
    get_warning_description,
    get_opstate_description
)
from utils.plotting import add_event_marker_line

st.set_page_config(page_title="Điều Tra Sự Cố & Lỗi - Solar PV", page_icon="🚨", layout="wide")

# Tiêu đề chuẩn tiếng Việt
st.title("🚨 MODULE 05 — HỆ THỐNG ĐIỀU TRA SỰ CỐ & PHÂN TÍCH LỖI")
st.caption("Điều tra phân tầng sự cố: Lỗi trạm APS, Lỗi ngăn biến tần APU và Cảnh báo vận hành (01/10 – 27/10/2025).")

# ------------------------------------------------------------------------------
# NẠP VÀ CHUẨN BỊ DỮ LIỆU SỰ CỐ TOÀN DIỆN
# ------------------------------------------------------------------------------
event_data = load_event_datasets()
df_all_events = build_standard_fault_events(event_data)

if df_all_events.empty:
    st.error("Không tìm thấy dữ liệu sự kiện hoặc trigger trong hệ thống!")
    st.stop()

# ==============================================================================
# SECTION 1 — TỔNG QUAN SỰ CỐ TOÀN THÁNG (27-DAY OVERVIEW)
# ==============================================================================
st.markdown("---")
st.header("⚡ 1. TỔNG QUAN SỰ CỐ TOÀN THÁNG (27-Day Overview)")
st.markdown("""
*Ưu tiên hiển thị **Lỗi nghiêm trọng (Critical Faults & Trips)** trước Cảnh báo không dừng máy (Warnings).*
""")

daily_breakdown = calculate_daily_event_breakdown(df_all_events)

# Thống kê chính xác
raw_apu_err_cnt = len(df_all_events[df_all_events["event_category_en"] == "APU ERROR"])
raw_aps_err_cnt = len(df_all_events[df_all_events["event_category_en"] == "APS ERROR"])
raw_warn_cnt = len(df_all_events[df_all_events["event_category_en"] == "WARNING"])
aps_code_occurrences = df_all_events[df_all_events["event_category_en"] == "APS ERROR"]["num_error_codes"].sum()
corr_4apu_cnt = len(df_all_events[df_all_events["is_4apu_correlated"] == True])
days_with_crit = len(daily_breakdown[daily_breakdown["has_critical_error"] == True])

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        label="🔴 Tổng LỖI APU (APU ERROR)",
        value=f"{raw_apu_err_cnt:,} Bản ghi",
        delta="4 Ngăn Biến Tần",
        delta_color="inverse"
    )
with col2:
    st.metric(
        label="🟥 Tổng LỖI APS (APS ERROR)",
        value=f"{raw_aps_err_cnt} Bản ghi",
        delta=f"{aps_code_occurrences} Lượt mã lỗi",
        delta_color="inverse"
    )
with col3:
    st.metric(
        label="🧱 Sự Cố Đồng Thời 4 APU",
        value=f"{corr_4apu_cnt} Bản ghi",
        delta="Sự kiện liên đới (Cascade)",
        delta_color="inverse"
    )
with col4:
    st.metric(
        label="🟠 Tổng CẢNH BÁO (WARNING)",
        value=f"{raw_warn_cnt:,} Bản ghi",
        delta="Không dừng máy",
        delta_color="normal"
    )

# Biểu đồ cột tổng hợp số lỗi theo ngày
col_ch1, col_ch2 = st.columns([1.2, 0.8])
with col_ch1:
    st.subheader("📊 Số Lượng Lỗi Nghiêm Trọng Theo Ngày (Critical Errors by Day)")
    fig_daily_err = go.Figure()
    fig_daily_err.add_trace(go.Bar(
        x=daily_breakdown["date"],
        y=daily_breakdown["apu_error_count"],
        name="LỖI APU (APU ERROR)",
        marker_color=COLORS["apu_error"]
    ))
    fig_daily_err.add_trace(go.Bar(
        x=daily_breakdown["date"],
        y=daily_breakdown["aps_error_count"],
        name="LỖI APS (APS ERROR)",
        marker_color=COLORS["aps_error"]
    ))
    fig_daily_err.update_layout(
        title="Phân Bố Lỗi Nghiêm Trọng 27 Ngày (01/10 – 27/10/2025)",
        xaxis_title="Ngày",
        yaxis_title="Số sự kiện (Event Count)",
        barmode="stack",
        template=PLOTLY_TEMPLATE,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(tickangle=-45),
        margin=dict(l=30, r=30, t=40, b=50)
    )
    st.plotly_chart(fig_daily_err, use_container_width=True)

with col_ch2:
    st.subheader("📅 Ma Trận Trạng Thái Sự Cố 27 Ngày")
    st.dataframe(
        daily_breakdown[["date", "daily_status", "apu_error_count", "aps_error_count", "affected_devices"]].style.map(
            lambda v: "background-color: #F8D7DA; color: #721C24; font-weight: bold;" if "Lỗi APS" in str(v) or "4 APU" in str(v) else ("background-color: #FFE3E3; color: #900C3F;" if "Lỗi APU" in str(v) else ""),
            subset=["daily_status"]
        ),
        use_container_width=True,
        height=320
    )

# ==============================================================================
# SECTION 2 — CHỌN NGÀY VÀ DÒNG THỜI GIAN SỰ KIỆN THEO THIẾT BỊ THỰC TẾ
# ==============================================================================
st.markdown("---")
st.header("🎯 2. ĐIỀU TRA DÒNG THỜI GIAN SỰ CỐ THEO NGÀY (Daily Event Timeline)")
st.markdown("""
* **Nguyên tắc cốt lõi**: Chỉ vẽ các tầng thiết bị **thực tế phát sinh sự cố trong ngày** (APS, APU 1, APU 2, APU 3, APU 4, SYSTEM). Thiết bị không có lỗi sẽ **không được hiển thị** để tránh gây rối mắt.
* Các lỗi liên tiếp trong khoảng thời gian ngắn được gom cụm thành **Event Episode** ($T_\\text{start} \\rightarrow T_\\text{end}$) kèm số lượng bản ghi gốc.
""")

# Nút truy cập nhanh các ngày trọng điểm
col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
with col_btn1:
    btn_04 = st.button("🔥 2025-10-04 (Đại sự cố Cascade)", use_container_width=True)
with col_btn2:
    btn_09 = st.button("⚡ 2025-10-09 (Trip APU nhiều)", use_container_width=True)
with col_btn3:
    btn_16 = st.button("⚡ 2025-10-16 (Trip APU 2 & 4)", use_container_width=True)
with col_btn4:
    btn_21 = st.button("⚡ 2025-10-21 (Trip APU 4)", use_container_width=True)
with col_btn5:
    btn_26 = st.button("⏱️ 2025-10-26 (Khoảng hở SCADA)", use_container_width=True)

target_selected_date = date(2025, 10, 4)
if btn_04: target_selected_date = date(2025, 10, 4)
elif btn_09: target_selected_date = date(2025, 10, 9)
elif btn_16: target_selected_date = date(2025, 10, 16)
elif btn_21: target_selected_date = date(2025, 10, 21)
elif btn_26: target_selected_date = date(2025, 10, 26)

col_sel1, col_sel2 = st.columns([1.5, 2.5])
with col_sel1:
    selected_date = st.date_input(
        "Chọn ngày điều tra sự cố:",
        value=target_selected_date,
        min_value=date(2025, 10, 1),
        max_value=date(2025, 10, 27)
    )

with col_sel2:
    include_warnings_in_timeline = st.checkbox("Hiển thị thêm CẢNH BÁO (WARNING) trên dòng thời gian ngày", value=False)

# Lọc sự kiện trong ngày
day_events_raw = df_all_events[df_all_events["date"] == selected_date].copy()

if not include_warnings_in_timeline:
    day_events_filtered = day_events_raw[day_events_raw["event_category_en"].isin(["APU ERROR", "APS ERROR"])].copy()
else:
    day_events_filtered = day_events_raw.copy()

# Gom cụm sự kiện thành Episodes
df_day_episodes = group_events_into_episodes(day_events_filtered, episode_gap_seconds=15)

if df_day_episodes.empty:
    st.success(f"✅ Ngày {selected_date.strftime('%d/%m/%Y')}: Không có sự cố nghiêm trọng nào được ghi nhận.")
else:
    # 1. Xác định danh sách thiết bị THỰC TẾ phát sinh lỗi
    active_devices = sorted(df_day_episodes["device"].unique().tolist())
    st.info(f"📍 **Các thiết bị phát sinh sự cố trong ngày {selected_date.strftime('%d/%m/%Y')} ({len(active_devices)} thiết bị):** `{', '.join(active_devices)}`")
    
    # 2. Vẽ Dòng thời gian sự kiện chỉ chứa các tầng thiết bị thực tế
    fig_event_timeline = px.scatter(
        df_day_episodes,
        x="start_time",
        y="device",
        color="event_category",
        symbol="event_category",
        symbol_map={
            "LỖI APS": "diamond",
            "LỖI APU": "circle",
            "CẢNH BÁO": "triangle-up"
        },
        color_discrete_map={
            "LỖI APS": COLORS["aps_error"],
            "LỖI APU": COLORS["apu_error"],
            "CẢNH BÁO": COLORS["warning"]
        },
        hover_data={
            "start_time_str": True,
            "end_time_str": True,
            "device": True,
            "fault_code_str": True,
            "error_description": True,
            "raw_records_count": True,
            "opstate_desc": True,
            "start_time": False
        },
        labels={
            "start_time": "Thời điểm",
            "device": "Thiết bị",
            "event_category": "Phân loại sự kiện",
            "start_time_str": "Bắt đầu",
            "end_time_str": "Kết thúc",
            "raw_records_count": "Số sự kiện (Event Count)",
            "fault_code_str": "Mã lỗi",
            "error_description": "Mô tả lỗi",
            "opstate_desc": "Trạng thái vận hành"
        },
        title=f"Dòng Thời Gian Sự Cố Ngày {selected_date.strftime('%d/%m/%Y')} (Chỉ hiển thị thiết bị có lỗi)",
        template=PLOTLY_TEMPLATE
    )
    
    fig_event_timeline.update_yaxes(categoryorder="array", categoryarray=active_devices)
    fig_event_timeline.update_traces(marker=dict(size=12, opacity=0.9, line=dict(width=1.5, color="#1D3557")))
    fig_event_timeline.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
        yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
        margin=dict(l=40, r=40, t=50, b=40)
    )
    st.plotly_chart(fig_event_timeline, use_container_width=True)

    # 3. Biểu đồ phân bố sự cố theo giờ trong ngày (00h - 23h)
    st.subheader(f"⏱️ Phân Bố Sự Cố Theo Khung Giờ Ngày {selected_date.strftime('%d/%m/%Y')}")
    hourly_df = calculate_hourly_event_histogram(df_all_events, selected_date)
    
    fig_hourly_bar = go.Figure()
    fig_hourly_bar.add_trace(go.Bar(x=hourly_df["hour"], y=hourly_df["APU_ERROR"], name="LỖI APU", marker_color=COLORS["apu_error"]))
    fig_hourly_bar.add_trace(go.Bar(x=hourly_df["hour"], y=hourly_df["APS_ERROR"], name="LỖI APS", marker_color=COLORS["aps_error"]))
    fig_hourly_bar.add_trace(go.Bar(x=hourly_df["hour"], y=hourly_df["WARNING"], name="CẢNH BÁO", marker_color=COLORS["warning"]))
    fig_hourly_bar.update_layout(
        title=f"Số lượng sự cố từng giờ ngày {selected_date.strftime('%d/%m/%Y')} (00h – 23h)",
        xaxis_title="Giờ trong ngày (00h - 23h)",
        yaxis_title="Số sự kiện (Event Count)",
        barmode="group",
        template=PLOTLY_TEMPLATE,
        xaxis=dict(tickmode="linear", tick0=0, dtick=1),
        margin=dict(l=30, r=30, t=40, b=40)
    )
    st.plotly_chart(fig_hourly_bar, use_container_width=True)

# ==============================================================================
# SECTION 3 — CHỌN VÀ ĐIỀU TRA CHI TIẾT SỰ KIỆN (DEEP-DIVE EVENT INVESTIGATION)
# ==============================================================================
st.markdown("---")
st.header("🔎 3. ĐIỀU TRA CHI TIẾT SỰ KIỆN ĐƯỢC CHỌN (Event Detail & Deep-Dive)")

selected_episode = None
if not df_day_episodes.empty:
    ep_options = []
    for idx, row in df_day_episodes.iterrows():
        opt_str = f"[{row['start_time_str']}] {row['device']} — Lỗi {row['primary_code']} — {row['error_description']} ({row['raw_records_count']} bản ghi)"
        ep_options.append((idx, opt_str))
        
    selected_ep_idx = st.selectbox(
        "👉 Chọn sự kiện cần điều tra Trước lỗi / Tại thời điểm lỗi / Sau lỗi (T):",
        options=[opt[0] for opt in ep_options],
        format_func=lambda idx: next(opt[1] for opt in ep_options if opt[0] == idx)
    )
    selected_episode = df_day_episodes.loc[selected_ep_idx]
    target_event_ts = selected_episode["start_time"]
    target_device = selected_episode["device"]
else:
    target_event_ts = datetime.combine(selected_date, datetime.min.time())
    target_device = "APU 1"

if selected_episode is not None:
    # Card thông tin chi tiết sự kiện
    col_card1, col_card2 = st.columns([1.5, 1.5])
    with col_card1:
        st.markdown(f"""
        <div style="background-color: #F8D7DA; padding: 16px; border-radius: 6px; border-left: 5px solid #721C24;">
            <h4 style="color: #721C24; margin-top: 0;">🔴 {selected_episode['device']} — {selected_episode['event_category']}</h4>
            <p><b>Thiết bị:</b> <code>{selected_episode['device']}</code></p>
            <p><b>Mã lỗi:</b> <code>{selected_episode['primary_code']}</code> ({selected_episode['fault_code_str']})</p>
            <p><b>Mô tả lỗi:</b> <b>{selected_episode['error_description']}</b></p>
            <p><b>Thời điểm bắt đầu:</b> <code>{selected_episode['start_time_str']}</code> (Kết thúc: <code>{selected_episode['end_time_str']}</code>)</p>
            <p><b>Số sự kiện (Event Count):</b> <b>{selected_episode['raw_records_count']} bản ghi</b></p>
            <p><b>Trạng thái vận hành OpState:</b> {selected_episode['opstate_desc']} (<code>OpState = {selected_episode['opstate']}</code>)</p>
            <p><b>Sự cố đồng thời 4 APU:</b> {'⚠️ Có — Cụm sự cố đồng thời cả 4 APU' if selected_episode['is_4apu_correlated'] else 'ℹ️ Sự cố đơn lẻ trên ngăn'}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_card2:
        st.markdown("#### 📦 Danh Sách Tất Cả Mã Lỗi Tại Mốc Thời Gian Này:")
        if selected_episode["error_items"]:
            for item in selected_episode["error_items"]:
                st.markdown(f"* **Thanh ghi `{item['register']}`:** Mã lỗi `{item['code']}` — *{item['desc']}*")
        elif selected_episode["warning_items"]:
            for item in selected_episode["warning_items"]:
                st.markdown(f"* **Thanh ghi `{item['register']}`:** Mã cảnh báo `{item['code']}` — *{item['desc']}*")
        else:
            st.write("Không có mã lỗi phụ trợ.")
            
        with st.expander("🔍 Xem dữ liệu gốc từ thanh ghi PLC / SCADA"):
            st.json(selected_episode["raw_row_reference"])

    # Phân tích chuỗi liên đới sự cố (Event Cascade Sequence) nếu có
    st.markdown("---")
    st.subheader("🔗 Trình Tự Xuất Hiện Sự Cố Quanh Mốc Thời Gian Này (Cascade Sequence)")
    
    t_cascade_start = target_event_ts - timedelta(seconds=60)
    t_cascade_end = target_event_ts + timedelta(seconds=60)
    cascade_events = df_day_episodes[(df_day_episodes["start_time"] >= t_cascade_start) & (df_day_episodes["start_time"] <= t_cascade_end)].sort_values("start_time")
    
    if len(cascade_events) > 1:
        st.markdown(f"*Phát hiện **{len(cascade_events)} sự kiện** xuất hiện gần nhau trong khoảng $\\pm 60\\text{{s}}$ quanh mốc sự cố:*")
        cascade_display = cascade_events[["start_time_str", "device", "event_category", "primary_code", "error_description"]].copy()
        cascade_display.columns = ["Thời điểm", "Thiết bị", "Phân loại", "Mã lỗi", "Mô tả lỗi"]
        st.table(cascade_display)
        st.caption("ℹ️ *Ghi chú quan sát: Dữ liệu ghi nhận trình tự thời gian xuất hiện sự kiện (Temporal sequence observed), không tự ý suy diễn quan hệ nhân quả tuyệt đối.*")
    else:
        st.write("Sự cố xảy ra đơn lẻ trên thiết bị này, không có sự kiện liên đới trên các thiết bị khác trong vòng $\\pm 60\\text{s}$.")

    # ==============================================================================
    # SECTION 4 — ĐỐI CHIẾU TRƯỚC LỖI / TẠI THỜI ĐIỂM LỖI / SAU LỖI (BEFORE / AT / AFTER)
    # ==============================================================================
    st.markdown("---")
    st.header("📊 4. ĐỐI CHIẾU THÔNG SỐ VẬN HÀNH TRƯỚC LỖI / TẠI THỜI ĐIỂM LỖI / SAU LỖI")
    st.markdown("""
    * **Trước lỗi (Before)**: Toàn bộ khoảng thời gian $[T - \\text{window}, T)$.
    * **Tại thời điểm lỗi (At Event)**: Mẫu dữ liệu đo đạc gần nhất với mốc thời gian $T$.
    * **Sau lỗi (After)**: Toàn bộ khoảng thời gian $(T, T + \\text{window}]$.
    * Hệ thống tính toán đầy đủ: Giá trị Trung bình $\\pm$ Độ lệch chuẩn, Dải biến thiên [Min..Max], Độ thay đổi tuyệt đối và Thay đổi $\%$.
    """)
    
    col_w1, col_w2 = st.columns([1.5, 2.5])
    with col_w1:
        selected_window_mins = st.radio(
            "Chọn cửa sổ thời gian đối chiếu (T ± Window):",
            options=[5, 15, 30, 60],
            index=2,
            format_func=lambda m: f"±{m} Phút",
            horizontal=True
        )
    with col_w2:
        st.info(f"🎯 **Đang ưu tiên đối chiếu tín hiệu từ thiết bị:** `{target_device}`")

    signal_results = extract_correlated_signals_robust(
        event_timestamp=target_event_ts,
        window_minutes=selected_window_mins,
        target_device=target_device
    )

    st.subheader(f"📋 Bảng Đối Chiếu Thống Kê Các Thông Số Vật Lý (T ± {selected_window_mins} Phút)")
    st.dataframe(signal_results["observations_table"], use_container_width=True)

    # 4 Biểu đồ động học đồng bộ quanh sự cố T
    st.subheader(f"📈 Biểu Đồ Động Học Quanh Thời Điểm Sự Cố (T = {selected_episode['start_time_str']})")
    
    df_p_win = signal_results["df_power_win"]
    df_apu_t_win = signal_results["df_apu_t_win"]
    df_10s_win = signal_results["df_10s_win"]
    active_apu_name = signal_results["active_apu"]

    col_plt1, col_plt2 = st.columns(2)
    with col_plt1:
        if not df_p_win.empty:
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(x=df_p_win["timestamp"], y=df_p_win["plant_ac_mw"], name="Công suất phát AC (MW)", line=dict(color="#FF9900", width=2)))
            fig_p.add_trace(go.Scatter(x=df_p_win["timestamp"], y=df_p_win["plant_dc_mw"], name="Công suất chuỗi DC (MW)", line=dict(color="#0066CC", width=2, dash="dot")))
            add_event_marker_line(fig_p, target_event_ts, label=f"Sự cố tại {selected_episode['start_time_str']}", line_color=COLORS["apu_error"])
            fig_p.update_layout(title="1. Đặc Tuyến Công Suất AC & DC Nhà Máy", xaxis_title="Thời gian", yaxis_title="Công suất (MW)", template=PLOTLY_TEMPLATE)
            st.plotly_chart(fig_p, use_container_width=True)

    with col_plt2:
        if not df_apu_t_win.empty:
            fig_th = go.Figure()
            fig_th.add_trace(go.Scatter(x=df_apu_t_win["timestamp"], y=df_apu_t_win["tind_c"], name=f"Nhiệt độ cuộn kháng Tind ({active_apu_name})", line=dict(color="#9B2226", width=2)))
            fig_th.add_trace(go.Scatter(x=df_apu_t_win["timestamp"], y=df_apu_t_win["tl1_c"], name=f"Nhiệt độ IGBT TL1 ({active_apu_name})", line=dict(color="#E63946", width=2)))
            add_event_marker_line(fig_th, target_event_ts, label="Sự cố T", line_color=COLORS["apu_error"])
            fig_th.update_layout(title=f"2. Nhiệt Độ Các Thành Phần ({active_apu_name})", xaxis_title="Thời gian", yaxis_title="Nhiệt độ (°C)", template=PLOTLY_TEMPLATE)
            st.plotly_chart(fig_th, use_container_width=True)

    if not df_10s_win.empty:
        col_plt3, col_plt4 = st.columns(2)
        with col_plt3:
            fig_v = go.Figure()
            fig_v.add_trace(go.Scatter(x=df_10s_win["timestamp"], y=df_10s_win["vl1n_v"], name="Điện áp Pha A VL1N (V)", line=dict(color="#E63946")))
            fig_v.add_trace(go.Scatter(x=df_10s_win["timestamp"], y=df_10s_win["vl2n_v"], name="Điện áp Pha B VL2N (V)", line=dict(color="#F4A261")))
            fig_v.add_trace(go.Scatter(x=df_10s_win["timestamp"], y=df_10s_win["vl3n_v"], name="Điện áp Pha C VL3N (V)", line=dict(color="#2A9D8F")))
            add_event_marker_line(fig_v, target_event_ts, label="Sự cố T", line_color=COLORS["apu_error"])
            fig_v.update_layout(title=f"3. Điện Áp 3 Pha AC 10s ({active_apu_name})", xaxis_title="Thời gian", yaxis_title="Điện áp (V)", template=PLOTLY_TEMPLATE)
            st.plotly_chart(fig_v, use_container_width=True)

        with col_plt4:
            fig_pq = go.Figure()
            fig_pq.add_trace(go.Scatter(x=df_10s_win["timestamp"], y=df_10s_win["p_total_kw"], name="Công suất tác dụng P (kW)", line=dict(color="#1D3557", width=2)))
            fig_pq.add_trace(go.Scatter(x=df_10s_win["timestamp"], y=df_10s_win["q_total_kvar"], name="Công suất phản kháng Q (kVar)", line=dict(color="#457B9D", width=2)))
            add_event_marker_line(fig_pq, target_event_ts, label="Sự cố T", line_color=COLORS["apu_error"])
            fig_pq.update_layout(title=f"4. Công Suất Tác Dụng & Phản Kháng 10s ({active_apu_name})", xaxis_title="Thời gian", yaxis_title="kW / kVar", template=PLOTLY_TEMPLATE)
            st.plotly_chart(fig_pq, use_container_width=True)

# ==============================================================================
# SECTION 5 — PHÂN TÍCH CẢNH BÁO VẬN HÀNH (WARNING ANALYSIS)
# ==============================================================================
st.markdown("---")
st.header("⚠️ 5. PHÂN TÍCH CẢNH BÁO VẬN HÀNH (Warning Analysis)")
st.markdown("""
*Phân hệ cảnh báo được tách riêng biệt ở cuối trang. Cảnh báo phản ánh các trạng thái suy giảm cách điện, độ ẩm cao, quạt làm mát hoạt động hoặc giảm tải nhiệt độ mà **không gây ngắt mạch biến tần**.*
""")

df_warns_only = df_all_events[df_all_events["event_category_en"] == "WARNING"].copy()

col_w_st1, col_w_st2 = st.columns([1.5, 1.5])
with col_w_st1:
    st.subheader("📊 Tần Suất Cảnh Báo Theo Mã (Warning Code Frequency)")
    w_summary = df_warns_only["warning_description"].value_counts().reset_index()
    w_summary.columns = ["Mô tả cảnh báo", "Số sự kiện (Event Count)"]
    st.dataframe(w_summary, use_container_width=True, height=280)

with col_w_st2:
    st.subheader("🗺️ Phân Bố Cảnh Báo Theo Thiết Bị Liên Kết")
    dev_w_counts = df_warns_only["device"].value_counts().reset_index()
    dev_w_counts.columns = ["Thiết bị", "Số sự kiện"]
    
    fig_w_pie = px.pie(
        dev_w_counts,
        names="Thiết bị",
        values="Số sự kiện",
        title="Tỷ lệ Cảnh Báo Gán Cho Thiết Bị / Hệ Thống",
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=["#E9C46A", "#F4A261", "#E76F51", "#2A9D8F", "#457B9D"]
    )
    st.plotly_chart(fig_w_pie, use_container_width=True)

# ==============================================================================
# SECTION 6 — BẢNG TRA CỨU SỰ KIỆN TỔNG THỂ & XUẤT BÁO CÁO (MASTER TABLE)
# ==============================================================================
st.markdown("---")
st.header("📋 6. BẢNG TRA CỨU SỰ KIỆN TỔNG THỂ & XUẤT BÁO CÁO")

col_exp1, col_exp2 = st.columns([3, 1])
with col_exp1:
    st.write(f"Tổng số bản ghi sự kiện khả dụng: **{len(df_all_events):,} sự kiện** (Sắp xếp theo thời gian mới nhất):")
with col_exp2:
    csv_bytes = df_all_events.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Tải Báo Cáo CSV Toàn Bộ Sự Cố",
        data=csv_bytes,
        file_name="bao_cao_su_co_27ngay.csv",
        mime="text/csv"
    )

display_cols = ["timestamp", "time_str", "device", "event_category", "fault_code_str", "error_description", "warning_code_str", "warning_description", "opstate_desc", "is_4apu_correlated"]
df_display_table = df_all_events[display_cols].copy()
df_display_table.columns = ["Thời gian", "Thời điểm", "Thiết bị", "Phân loại", "Mã lỗi", "Mô tả lỗi", "Mã cảnh báo", "Mô tả cảnh báo", "Trạng thái vận hành", "Đồng thời 4 APU"]

st.dataframe(
    df_display_table.sort_values("Thời gian", ascending=False).style.map(
        lambda v: "background-color: #F8D7DA; color: #721C24; font-weight: bold;" if v == "LỖI APS" else ("background-color: #FFE3E3; color: #900C3F; font-weight: bold;" if v == "LỖI APU" else ("background-color: #FFF3CD; color: #856404;" if v == "CẢNH BÁO" else "")),
        subset=["Phân loại"]
    ),
    use_container_width=True,
    height=380
)
