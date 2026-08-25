"""
08_Data_Quality.py
==================
Trang Báo Cáo Chất Lượng Dữ Liệu & Nhật Ký Kiểm Toán (Data Quality & Audit Findings).
"""

import streamlit as st
import pandas as pd

from data_loader import load_dataset_summary

st.set_page_config(page_title="Data Quality Audit - Solar PV", page_icon="🛡️", layout="wide")
st.title("🛡️ Báo Cáo Chất Lượng Dữ Liệu & Kiểm Toán (Data Quality Audit)")

df_summary = load_dataset_summary()

# 1. Bảng tổng hợp trạng thái 13 Dataset
st.subheader("📋 1. Bảng Đánh Giá Chất Lượng Tổng Thể (Audit Matrix)")
if not df_summary.empty:
    st.dataframe(
        df_summary.style.map(
            lambda v: "background-color: #D4EDDA; color: #155724; font-weight: bold;" if v == "SAFE TO USE" else ("background-color: #FFF3CD; color: #856404; font-weight: bold;" if "WARNING" in str(v) else ""),
            subset=["status"]
        ),
        use_container_width=True
    )
else:
    st.info("Không tìm thấy tệp dataset_audit_summary.csv.")

st.markdown("---")

# 2. Chi tiết các cảnh báo đã được xác minh (Verified Warnings)
st.subheader("⚠️ 2. Chi Tiết Các Cảnh Báo & Hiện Tượng Dữ Liệu Khách Quan")

col1, col2 = st.columns(2)

with col1:
    st.warning("""
    **1. Khoảng Hở Thời Gian Trong SCADA Power Report (3 Gaps)**
    - **17 phút** ngày 01/10 (07:31 → 07:49): Mất tín hiệu truyền thông SCADA.
    - **10 giờ 16 phút** đêm 15 → 16/10: Ranh giới ngắt ca trích xuất file giữa File 1 và File 2.
    - **59 phút** ngày 26/10 (06:08 → 07:08): Mất kết nối SCADA.
    - *Xử lý*: Giữ nguyên tính trung thực của dữ liệu gốc, không tự ý nội suy bù giờ.
    """)
    
    st.warning("""
    **2. Trùng Lặp Mốc Thời Gian Trong Event/Trigger Logs**
    - `aps_stat_trig`, `apu_stat_trig`, `aps_ctrl_trig`, `apu_ctrl_trig` có các mốc thời gian/mili-giây trùng nhau.
    - *Giải thích*: Đây là bản chất vật lý của thanh ghi PLC ghi nhận đồng thời nhiều bit sự kiện (multi-register event logging).
    """)

with col2:
    st.warning("""
    **3. Cờ Lỗi Cảm Biến Nhiệt Độ -20.0°C (Sensor Fault Flag)**
    - Xuất hiện 1 điểm duy nhất tại `2025-10-04 08:41:00` trong `aps_stat_60s.parquet` (cột `tamb_c`).
    - *Giải thích*: Mã lỗi hở mạch điện trở PT100.
    - *Xử lý*: Đã tạo cờ `is_sensor_fault = True`, giữ nguyên giá trị thô để phục vụ chẩn đoán.
    """)
    
    st.warning("""
    **4. Bức Xạ Âm Ban Đêm Trong Weather & Power Reports**
    - Cảm biến pyranometer ghi nhận giá trị âm nhỏ ($-0.1$ đến $-4.0\,\text{W/m}^2$) vào ban đêm.
    - *Giải thích*: Dòng tối (dark current) và phát xạ nhiệt hồng ngoại ban đêm của đầu đo nhiệt điện.
    - *Xử lý*: Bảo toàn cột gốc `radiation_w_m2`, tạo cột dẫn xuất `radiation_clipped_w_m2 = max(rad, 0)`.
    """)

st.info("💡 **Kết luận chất lượng**: 100% dữ liệu đã sẵn sàng cho mô hình hóa và phân tích chuyên sâu mà không có bất kỳ lỗi hư hỏng logic nào.")
