# HỆ THỐNG EDA WEB INTERACTIVE NHÀ MÁY ĐIỆN MẶT TRỜI TRUNG NAM

Hệ thống Phân tích Khám phá Dữ liệu Tương tác (Interactive Exploratory Data Analysis Platform) xây dựng bằng **Streamlit** và **Plotly**, khai thác toàn bộ **13 dataset Parquet** đã qua tiền xử lý chuẩn mực.

---

## 1. Khởi Chạy Ứng Dụng (Quick Start)

Mở terminal tại thư mục gốc `c:\PV` và chạy lệnh:

```powershell
streamlit run eda/app.py
```

Ứng dụng sẽ tự động mở giao diện trực quan trên trình duyệt tại địa chỉ: `http://localhost:8501`.

---

## 2. Cấu Trúc Các Trang Phân Tích (Multi-Page Navigation)

```text
Trang Chủ (app.py)          -> Executive KPI Summary & Điều hướng tổng quan
├── 01_Overview.py          -> VIEW A: Tổng quan 27 ngày (Xu hướng Daily/Hourly, Công suất đỉnh)
├── 02_Generation.py        -> Module 01: Công suất AC/DC, Bức xạ vs Công suất, Xếp hạng 102 Inverter
├── 03_Environment_Thermal.py -> Module 02: Nhiệt độ Cuộn kháng AC, IGBT, MBA, Mặt pin, Cách điện DC Riso
├── 04_Electrical.py        -> Module 03: Động học 10s Điện áp 3 pha, Dòng điện, Lệch pha VU, P-Q diagram
├── 05_Events_Faults.py     -> Module 04: Pareto mã lỗi, Sự cố trip, Phân bố sự kiện theo giờ, Timeline
├── 06_Reliability.py       -> Module 05: Số chu kỳ đóng cắt Contactor AC/DC 4 APU, Đánh giá hao mòn
├── 07_Energy.py            -> Module 06: Đối soát sản lượng Công tơ MWh vs Tích phân công suất 1 phút
├── 08_Data_Quality.py      -> Báo cáo kiểm toán chất lượng dữ liệu và minh bạch các cảnh báo
└── 09_Dataset_Overview.py  -> Bản đồ ma trận toàn bộ 13 dataset Parquet và phạm vi ứng dụng
```

---

## 3. Ba Khung Nhìn Thời Gian Chuẩn Hóa (3 Temporal Views)

* **VIEW A — 27-Day Overview**: Tổng hợp dữ liệu theo **Ngày (Daily)** hoặc **Giờ (Hourly)** để đánh giá xu hướng vĩ mô toàn chu kỳ 27 ngày.
* **VIEW B — Single Day Deep-Dive**: Chọn bất kỳ ngày nào trong dải `01/10/2025` đến `27/10/2025` để xem chi tiết độ phân giải gốc (**1 phút** đối với công suất/nhiệt độ, **10 giây** đối với động học điện lực). Kèm thanh trượt **Hour Range Slider** để thu hẹp khoảng giờ quan sát (ví dụ: `06:00 → 18:00`).
* **VIEW C — Custom Date Range**: Chọn ngày bắt đầu và ngày kết thúc tự do (ví dụ: `2025-10-05 → 2025-10-08`).

---

## 4. Khả Năng Lọc & Xếp Hạng Biến Tần (Inverter Drill-Down)

* Tại trang **02 Generation**, thanh Sidebar cho phép:
  - Chọn **ALL (Toàn nhà máy)** để xem tổng công suất 102 Inverter.
  - Chọn từng Inverter cụ thể (ví dụ: `block_1_inv_1`, `block_24_inv_5`...) để xem đặc tuyến AC/DC và hiệu suất riêng biệt.
  - Bảng xếp hạng tự động phân loại **Top 10 Inverter tốt nhất** và **Bottom 10 Inverter kém nhất** theo sản lượng MWh.

---

## 5. Cam Kết Bảo Toàn Dữ Liệu

1. **Zero Mutation**: Không ghi đè hoặc chỉnh sửa bất kỳ file nào trong `data/processed/`.
2. **True Physics**: Giữ nguyên tính trung thực của dữ liệu (bảo toàn dòng tối bức xạ âm ban đêm, cờ lỗi cảm biến $-20^\circ\text{C}$, không tự tiện nội suy bù giờ).
