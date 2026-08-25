"""
app.py
======
Cổng điều hướng trung tâm (Landing Page & Executive Summary)
Hệ thống EDA Web Interactive Nhà máy Điện Mặt Trời Trung Nam.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from config import MIN_DATE_STR, MAX_DATE_STR
from data_loader import load_power_report, load_dataset_summary
from utils.aggregation import compute_plant_power_totals, aggregate_power_daily
from utils.plotting import plot_timeseries_dual_axis

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Solar PV EDA Dashboard - Trung Nam",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("☀️ Nhà Máy Điện Mặt Trời Trung Nam — EDA Dashboard")
st.markdown("""
Hệ thống Phân tích Khám phá Dữ liệu Toàn diện (Interactive EDA Platform)  
*Dữ liệu vận hành 27 ngày (01/10/2025 – 27/10/2025) từ 102 Inverter SINACON PV & Hệ thống SCADA.*
""")

# Load dữ liệu nhanh để tính KPI
df_power = load_power_report()
if not df_power.empty:
    df_totals = compute_plant_power_totals(df_power)
    daily_df = aggregate_power_daily(df_totals)
    
    total_energy_mwh = daily_df["daily_energy_ac_mwh"].sum()
    peak_power_mw = daily_df["peak_ac_power_mw"].max()
    avg_efficiency = daily_df["mean_efficiency_pct"].mean()
    total_days = len(daily_df)
    
    # 4 Thẻ KPI chính
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="⚡ Tổng Sản Lượng Phát AC", value=f"{total_energy_mwh:,.1f} MWh", delta="27 Ngày")
    with col2:
        st.metric(label="🔥 Công Suất Đỉnh Toàn Trạm", value=f"{peak_power_mw:.2f} MW", delta="Toàn nhà máy")
    with col3:
        st.metric(label="⚙️ Hiệu Suất Chuyển Đổi Trung Bình", value=f"{avg_efficiency:.2f}%", delta="AC / DC")
    with col4:
        st.metric(label="📅 Quy Mô Giám Sát", value="102 Inverters", delta=f"{total_days} Ngày liên tục")

    st.markdown("---")
    
    # Biểu đồ xu hướng sản lượng 27 ngày
    st.subheader("📈 Xu Hướng Sản Lượng & Công Suất Toàn Trạm (27-Day Overview)")
    fig_overview = plot_timeseries_dual_axis(
        df=daily_df,
        x_col="date",
        y1_cols=["daily_energy_ac_mwh"],
        y2_cols=["peak_ac_power_mw", "daily_insolation_kwh_m2"],
        y1_names=["Sản lượng AC (MWh/ngày)"],
        y2_names=["Công suất đỉnh (MW)", "Bức xạ tích lũy (kWh/m²/ngày)"],
        y1_title="Sản lượng ngày (MWh)",
        y2_title="Công suất đỉnh (MW) / Bức xạ (kWh/m²)",
        title="Biểu đồ Sản Lượng Ngày & Công Suất Đỉnh Toàn Nhà Máy (01/10 - 27/10/2025)",
        y1_colors=["#FF9900"],
        y2_colors=["#E63946", "#FFCC00"]
    )
    st.plotly_chart(fig_overview, use_container_width=True)

st.markdown("---")
st.subheader("🧭 Hướng Dẫn Điều Hướng Các Mô-Đun Phân Tích (Navigation)")

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.info("""
    **⚡ [02 Generation](pages/02_Generation.py)**  
    Phân tích công suất AC/DC, bức xạ vs công suất, xếp hạng 102 Inverter, Top 5/Bottom 5.
    """)
    st.info("""
    **🌡️ [03 Environment & Thermal](pages/03_Environment_Thermal.py)**  
    Nhiệt độ cuộn kháng AC, van IGBT, máy biến áp, tấm pin và an toàn điện trở cách điện DC.
    """)
with col_m2:
    st.info("""
    **🔬 [04 Electrical 10s](pages/04_Electrical.py)**  
    Động học 10 giây: Điện áp 3 pha, dòng điện, tần số lưới, cân bằng pha và biểu đồ P-Q capability.
    """)
    st.info("""
    **🚨 [05 Events & Faults](pages/05_Events_Faults.py)**  
    Phân tích Pareto mã lỗi, sự cố trip, biểu đồ nhiệt theo giờ và timeline sự kiện.
    """)
with col_m3:
    st.info("""
    **🔄 [06 Reliability](pages/06_Reliability.py)**  
    Theo dõi số chu kỳ đóng cắt contactor AC & DC, tốc độ hao mòn và phát hiện đóng cắt bất thường.
    """)
    st.info("""
    **📊 [07 Energy Reconciliation](pages/07_Energy.py)**  
    Đối soát sản lượng công tơ MWh vs tích phân công suất, phân bổ dòng 12 string CMB.
    """)

st.markdown("---")
st.markdown("""
*💡 **Mẹo tương tác**: Sử dụng menu bên trái để chuyển đổi giữa các trang phân tích. Trong mỗi trang, bạn có thể chọn bất kỳ ngày nào trong 27 ngày hoặc phóng to từng khoảng giờ cụ thể.*
""")
