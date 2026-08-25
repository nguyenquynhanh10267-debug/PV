"""
09_Dataset_Overview.py
======================
Trang Tổng Quan & Bản Đồ Sử Dụng Toàn Bộ 13 Dataset (Dataset Matrix & Coverage).
"""

import streamlit as st
import pandas as pd

from data_loader import load_dataset_summary

st.set_page_config(page_title="Dataset Coverage - Solar PV", page_icon="🗺️", layout="wide")
st.title("🗺️ Bản Đồ & Mục Đích Sử Dụng 13 Dataset Parquet (Dataset Matrix)")

st.markdown("""
Trang này cung cấp cái nhìn toàn diện trả lời cho câu hỏi:  
**"Toàn bộ 13 dataset này có đặc điểm gì, nằm ở đâu và được sử dụng trong mô-đun nào?"**
""")

# Bảng ma trận 13 dataset
DATASET_MATRIX = [
    {
        "Dataset": "power_report.parquet",
        "Nhóm": "A. Power / Generation",
        "Số dòng": "36,954",
        "Số cột": "208",
        "Tần suất": "1 phút",
        "Loại hình": "Continuous",
        "Biến chính": "102 cặp AC/DC kW, Bức xạ W/m²",
        "Mô-đun sử dụng": "EDA 01, EDA 02, EDA 03, EDA 06",
        "Vai trò": "Xương sống công suất toàn trạm"
    },
    {
        "Dataset": "energy_report.parquet",
        "Nhóm": "B. Energy",
        "Số dòng": "634",
        "Số cột": "104",
        "Tần suất": "1 giờ",
        "Loại hình": "Cumulative",
        "Biến chính": "103 cột Inverter MWh",
        "Mô-đun sử dụng": "EDA 01, EDA 06",
        "Vai trò": "Đối soát sản lượng công tơ thương phẩm"
    },
    {
        "Dataset": "weather_report.parquet",
        "Nhóm": "C. Weather / Environment",
        "Số dòng": "21,672",
        "Số cột": "71",
        "Tần suất": "1 giờ (T10) / 1 phút (T9)",
        "Loại hình": "Continuous",
        "Biến chính": "Bức xạ POA, Nhiệt độ mặt pin Tmodule",
        "Mô-đun sử dụng": "EDA 01, EDA 02",
        "Vai trò": "Chuẩn đối sánh tài nguyên & tính PR"
    },
    {
        "Dataset": "aps_stat_60s.parquet",
        "Nhóm": "C. Weather / Environment",
        "Số dòng": "37,469",
        "Số cột": "13",
        "Tần suất": "1 phút",
        "Loại hình": "Continuous",
        "Biến chính": "Tamb, Ttrans, Riso, Cleak",
        "Mô-đun sử dụng": "EDA 02",
        "Vai trò": "Môi trường trạm & an toàn cách điện DC"
    },
    {
        "Dataset": "apu_stat_60s.parquet",
        "Nhóm": "D. Inverter Thermal",
        "Số dòng": "149,868",
        "Số cột": "10",
        "Tần suất": "1 phút",
        "Loại hình": "Continuous",
        "Biến chính": "Tind cuộn kháng, TL1..L3 IGBT",
        "Mô-đun sử dụng": "EDA 02, EDA 03",
        "Vai trò": "Giám sát sức khỏe nhiệt biến tần"
    },
    {
        "Dataset": "apu_stat_10s.parquet",
        "Nhóm": "E. High-Frequency",
        "Số dòng": "963,659",
        "Số cột": "24",
        "Tần suất": "10 giây",
        "Loại hình": "Continuous",
        "Biến chính": "3-Phase V, I, f, P, Q, Vdc",
        "Mô-đun sử dụng": "EDA 03",
        "Vai trò": "Kính hiển vi chất lượng điện & động học 10s"
    },
    {
        "Dataset": "aps_energy.parquet",
        "Nhóm": "B. Energy",
        "Số dòng": "37,471",
        "Số cột": "18",
        "Tần suất": "1 phút",
        "Loại hình": "Cumulative",
        "Biến chính": "Win/Wout APS & APU 1..4 kWh",
        "Mô-đun sử dụng": "EDA 06",
        "Vai trò": "Đánh giá tỷ lệ điện năng tự dùng trạm"
    },
    {
        "Dataset": "apu_energy.parquet",
        "Nhóm": "B. Energy",
        "Số dòng": "149,910",
        "Số cột": "28",
        "Tần suất": "1 phút",
        "Loại hình": "Cumulative",
        "Biến chính": "CH1..12 Pos/Neg Ah (4 APU)",
        "Mô-đun sử dụng": "EDA 06",
        "Vai trò": "Đo dòng điện tích lũy 12 chuỗi pin CMB"
    },
    {
        "Dataset": "aps_ctrl_trig.parquet",
        "Nhóm": "F. Event / Control",
        "Số dòng": "3,075",
        "Số cột": "24",
        "Tần suất": "Event-driven",
        "Loại hình": "Discrete Event",
        "Biến chính": "Trạng thái quạt, bơm, máy hút ẩm",
        "Mô-đun sử dụng": "EDA 04",
        "Vai trò": "Nhật ký điều khiển hệ thống làm mát"
    },
    {
        "Dataset": "aps_stat_trig.parquet",
        "Nhóm": "F. Event / Fault",
        "Số dòng": "2,734",
        "Số cột": "22",
        "Tần suất": "Event-driven",
        "Loại hình": "Discrete Event",
        "Biến chính": "OpState, Error1..8, Warning1..8",
        "Mô-đun sử dụng": "EDA 04",
        "Vai trò": "Nhật ký cảnh báo & lỗi trạm APS"
    },
    {
        "Dataset": "apu_ctrl_trig.parquet",
        "Nhóm": "F. Event / Control",
        "Số dòng": "275,287",
        "Số cột": "19",
        "Tần suất": "Event-driven",
        "Loại hình": "Discrete Event",
        "Biến chính": "Pset, Qset, Vislset, VdcMax",
        "Mô-đun sử dụng": "EDA 04",
        "Vai trò": "Nhật ký setpoint điều khiển APU"
    },
    {
        "Dataset": "apu_stat_trig.parquet",
        "Nhóm": "F. Event / Fault",
        "Số dòng": "4,872",
        "Số cột": "24",
        "Tần suất": "Event-driven",
        "Loại hình": "Discrete Event",
        "Biến chính": "OpState, Plim, Qlim, Error1..8",
        "Mô-đun sử dụng": "EDA 04",
        "Vai trò": "Nhật ký sự cố & giới hạn động APU"
    },
    {
        "Dataset": "aps_switching_cycles.parquet",
        "Nhóm": "G. Reliability",
        "Số dòng": "275",
        "Số cột": "16",
        "Tần suất": "Ca / Ngày",
        "Loại hình": "Snapshot",
        "Biến chính": "Contactor AC/DC APU 1..4",
        "Mô-đun sử dụng": "EDA 05",
        "Vai trò": "Đánh giá hao mòn chu kỳ đóng cắt"
    }
]

df_matrix = pd.DataFrame(DATASET_MATRIX)
st.dataframe(df_matrix, use_container_width=True)

st.markdown("---")
st.subheader("💡 Cam Kết Toàn Vẹn Kiến Trúc")
st.markdown("""
- **100% (13/13) Dataset** đều được tích hợp đầy đủ trong các trang phân tích.
- **Không có bất kỳ dữ liệu thô nào bị thay đổi hay sửa đổi trong `data/processed/`**.
- Mọi phép tính toán dẫn xuất đều diễn ra trong bộ nhớ phục vụ hiển thị trực quan.
""")
