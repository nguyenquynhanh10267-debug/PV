"""
time_filter.py
==============
Bộ lọc thời gian chuẩn hóa cho 3 khung nhìn:
- VIEW A: Overview (Toàn bộ 27 ngày)
- VIEW B: Single Day (1 ngày cụ thể + lọc khoảng giờ)
- VIEW C: Custom Range (Khoảng ngày tùy chọn)
"""

from datetime import datetime, date, time
from typing import Tuple, Optional, Any, Dict
import pandas as pd
import streamlit as st

from config import MIN_DATE_STR, MAX_DATE_STR, DEFAULT_SELECTED_DATE

MIN_DATE = datetime.strptime(MIN_DATE_STR, "%Y-%m-%d").date()
MAX_DATE = datetime.strptime(MAX_DATE_STR, "%Y-%m-%d").date()
DEFAULT_DATE = datetime.strptime(DEFAULT_SELECTED_DATE, "%Y-%m-%d").date()


def render_time_sidebar(allow_resolution_switch: bool = True) -> Dict[str, Any]:
    """Render bộ điều khiển thời gian chuẩn hóa trên thanh Sidebar."""
    st.sidebar.markdown("### ⏱️ Khung Nhìn Thời Gian (Time View)")
    
    view_mode = st.sidebar.radio(
        "Chọn chế độ xem:",
        options=["VIEW A: 27-Day Overview", "VIEW B: Single Day Deep-Dive", "VIEW C: Custom Date Range"],
        index=1,
        help="VIEW A: Xu hướng vĩ mô toàn chu kỳ.\nVIEW B: Chi tiết 1 ngày (1-min/10-sec).\nVIEW C: Phóng to khoảng ngày tùy chọn."
    )
    
    selected_date = DEFAULT_DATE
    start_date = MIN_DATE
    end_date = MAX_DATE
    hour_range = (0, 23)
    resolution = "1-minute"
    
    if view_mode == "VIEW B: Single Day Deep-Dive":
        selected_date = st.sidebar.date_input(
            "Chọn ngày phân tích:",
            value=DEFAULT_DATE,
            min_value=MIN_DATE,
            max_value=MAX_DATE,
            help="Chọn bất kỳ ngày nào trong dải 01/10/2025 -> 27/10/2025"
        )
        hour_range = st.sidebar.slider(
            "Khoảng giờ trong ngày (Hour Range):",
            min_value=0,
            max_value=23,
            value=(5, 19),
            step=1,
            help="Thu hẹp khoảng giờ quan sát (mặc định: 05:00 - 19:00 có nắng)"
        )
        start_date = selected_date
        end_date = selected_date
        
    elif view_mode == "VIEW C: Custom Date Range":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Từ ngày:", value=date(2025, 10, 5), min_value=MIN_DATE, max_value=MAX_DATE)
        with col2:
            end_date = st.date_input("Đến ngày:", value=date(2025, 10, 8), min_value=MIN_DATE, max_value=MAX_DATE)
        if start_date > end_date:
            st.sidebar.error("Ngày bắt đầu không được sau ngày kết thúc!")
            start_date, end_date = end_date, start_date
            
        span_days = (end_date - start_date).days + 1
        if span_days > 3:
            resolution = "1-hour"
        else:
            resolution = "1-minute"
            
    else:  # VIEW A: Overview
        if allow_resolution_switch:
            res_choice = st.sidebar.selectbox(
                "Độ phân giải tổng hợp (Aggregation):",
                options=["Daily (Theo Ngày)", "Hourly (Theo Giờ)"],
                index=0
            )
            resolution = "Daily" if "Daily" in res_choice else "Hourly"
            
    return {
        "view_mode": view_mode,
        "selected_date": selected_date,
        "start_date": start_date,
        "end_date": end_date,
        "hour_range": hour_range,
        "resolution": resolution
    }


def apply_time_filter(
    df: pd.DataFrame,
    time_config: Dict[str, Any],
    ts_col: str = "timestamp"
) -> pd.DataFrame:
    """Lọc dữ liệu DataFrame theo cấu hình thời gian đã chọn."""
    if ts_col not in df.columns or df.empty:
        return df
        
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[ts_col]):
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
        
    view_mode = time_config["view_mode"]
    
    if view_mode == "VIEW B: Single Day Deep-Dive":
        target_date = time_config["selected_date"]
        h_start, h_end = time_config["hour_range"]
        
        mask = (df[ts_col].dt.date == target_date)
        if h_start > 0 or h_end < 23:
            mask = mask & (df[ts_col].dt.hour >= h_start) & (df[ts_col].dt.hour <= h_end)
        return df[mask].reset_index(drop=True)
        
    elif view_mode == "VIEW C: Custom Date Range":
        s_date = time_config["start_date"]
        e_date = time_config["end_date"]
        mask = (df[ts_col].dt.date >= s_date) & (df[ts_col].dt.date <= e_date)
        return df[mask].reset_index(drop=True)
        
    else:  # VIEW A: Overview
        return df
