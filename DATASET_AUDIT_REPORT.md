# BÁO CÁO KIỂM TOÁN DỮ LIỆU TOÀN DIỆN 12 DATASET (DATASET AUDIT REPORT)
**Dự án**: Phân tích dữ liệu Nhà máy điện mặt trời Trung Nam (Inverter SINACON PV & Báo cáo SCADA)  
**Thời gian kiểm toán**: 21/08/2026  
**Phạm vi**: Toàn bộ 12 dataset Parquet sau tiền xử lý (ngoại trừ `power_report.parquet` đã được kiểm toán chuyên sâu trước đó).

---

## 1. Executive Summary (Tóm Tắt Tổng Quan)

Toàn bộ 12 file Parquet đã được kiểm toán độc lập trên 100% dung lượng thực tế (tổng cộng hơn 1.63 triệu dòng bản ghi).

1. **Khả năng đọc và Tính toàn vẹn cấu trúc (Structure & I/O Integrity)**:
   - 100% (12/12) file Parquet đọc ghi hoàn hảo với `pyarrow` và `pandas`.
   - Không có cột trùng lặp tên (Duplicate column names = 0).
   - Không có ô chứa giá trị `Inf` hoặc `-Inf` trên toàn bộ 12 dataset.
2. **Khóa thời gian và Thực thể (Timestamps & Entity Keys)**:
   - 100% (12/12) dataset có chuỗi thời gian đơn điệu tăng theo từng thực thể (`is_monotonic_increasing = True`).
   - Cột `timestamp_nulls = 0` trên toàn bộ 12 dataset.
   - `apu_stat_10s.parquet` (963,659 dòng) đạt **0 duplicate keys (100% Unique)** sau khi áp dụng tái tạo timestamp nội phút cho các đợt buffer flush sáng sớm.
3. **Bản chất dữ liệu và Phân loại vận hành**:
   - **Time-Series đều đặn (Regular Time Series)**: `aps_stat_60s`, `apu_stat_60s` (1 phút), `energy_report` (1 giờ) đạt chuẩn 100% và sẵn sàng sử dụng ngay cho phân tích.
   - **Time-Series năng lượng tích lũy (Cumulative Energy)**: `aps_energy`, `apu_energy` có tính liên tục 1 phút đạt 100%, chỉ có vài mốc trùng lặp tại ranh giới giao thoa ngày trong file log gốc.
   - **Event/Trigger Logs (Không đồng bộ)**: `aps_ctrl_trig`, `aps_stat_trig`, `apu_ctrl_trig`, `apu_stat_trig`, `aps_switching_cycles` mang bản chất sự kiện điều khiển và cảnh báo lỗi. Việc xuất hiện nhiều bản ghi cùng một timestamp/millisecond là đặc tính vật lý tự nhiên của thanh ghi số PLC/SCADA (multi-register concurrent events) và được giữ nguyên vẹn.
   - **Báo cáo thời tiết (Weather Report)**: Chứa dữ liệu 1 giờ cho toàn bộ 27 ngày tháng 10/2025 (24 điểm/ngày) cùng các dữ liệu lịch sử đo 1 phút trong tháng 9/2025.

---

## 2. Danh Mục Dataset (Dataset Inventory)

| STT | Tên Dataset Parquet | Dung lượng | Số dòng (Rows) | Số cột (Cols) | Loại hình dữ liệu | Entity phân hệ | Tần suất lấy mẫu chính |
|:---:|---|:---:|:---:|:---:|---|---|---|
| **1** | `aps_ctrl_trig.parquet` | 39.4 KB | 3,075 | 24 | Trigger / Control Events | `APS` | Không đồng bộ (Event-driven) |
| **2** | `aps_energy.parquet` | 825.6 KB | 37,471 | 18 | Chuỗi thời gian (Cumulative) | `APS` | 60 giây (1 phút) |
| **3** | `aps_stat_60s.parquet` | 1.16 MB | 37,469 | 13 | Chuỗi thời gian (Môi trường & MBA) | `APS` | 60 giây (1 phút) |
| **4** | `aps_stat_trig.parquet` | 31.8 KB | 2,734 | 22 | Trigger / Error & Warning | `APS` | Không đồng bộ (Event-driven) |
| **5** | `aps_switching_cycles.parquet` | 12.4 KB | 275 | 16 | Snapshot chu kỳ đóng cắt | `APS` | Ca / Ngày |
| **6** | `apu_ctrl_trig.parquet` | 3.76 MB | 275,287 | 19 | Trigger / Setpoint & Limits | `APU 1..4` | Vòng lặp điều khiển nhanh |
| **7** | `apu_energy.parquet` | 4.64 MB | 149,910 | 28 | Chuỗi thời gian (Cumulative Ah) | `APU 1..4` | 60 giây (1 phút) |
| **8** | `apu_stat_10s.parquet` | 101.2 MB | 963,659 | 24 | Chuỗi thời gian cao tần | `APU 1..4` | 10 giây (6 mẫu/phút) |
| **9** | `apu_stat_60s.parquet` | 6.17 MB | 149,868 | 10 | Chuỗi thời gian (Nhiệt & Ẩm) | `APU 1..4` | 60 giây (1 phút) |
| **10** | `apu_stat_trig.parquet` | 23.7 KB | 4,872 | 24 | Trigger / Fault & Limits | `APU 1..4` | Không đồng bộ (Event-driven) |
| **11** | `weather_report.parquet` | 1.01 MB | 21,672 | 71 | Báo cáo SCADA Trạm thời tiết | `Global` | 1 giờ (Tháng 10) & 1 phút (Tháng 9) |
| **12** | `energy_report.parquet` | 352.4 KB | 634 | 104 | Báo cáo SCADA Sản lượng tích lũy | `Global` | 3600 giây (1 giờ) |

---

## 3. Bảng Tổng Hợp Đánh Giá PASS / WARNING / FAIL

| STT | Dataset Parquet | Đánh giá | Trạng thái khuyến nghị | Lý do đánh giá |
|:---:|---|:---:|:---:|---|
| **1** | `aps_ctrl_trig.parquet` | **PASS** | **SAFE WITH WARNING** | Dữ liệu trigger sự kiện chuẩn; có 492 mốc thời gian đa bit điều khiển cùng ms (hợp lệ). |
| **2** | `aps_energy.parquet` | **PASS** | **SAFE WITH WARNING** | Chuỗi tích lũy 1 phút liên tục 100%; có 2 duplicate keys ở ranh giới giao thoa ngày. |
| **3** | `aps_stat_60s.parquet` | **PASS** | **SAFE TO USE** | Chuỗi thời gian 1 phút sạch 100%, 0 duplicate key, gắn cờ đúng 1 điểm $-20^\circ\text{C}$. |
| **4** | `aps_stat_trig.parquet` | **PASS** | **SAFE WITH WARNING** | Dữ liệu trigger cảnh báo chuẩn; có 1,146 mốc lỗi xếp chồng cùng ms (hợp lệ). |
| **5** | `aps_switching_cycles.parquet` | **PASS** | **SAFE WITH WARNING** | Bảng snapshot chu kỳ đóng cắt contactor AC/DC theo ca. |
| **6** | `apu_ctrl_trig.parquet` | **PASS** | **SAFE WITH WARNING** | Dữ liệu setpoint điều khiển đa pha theo mili-giây (hợp lệ). Cột `IdcMax/V` cần xác nhận đơn vị. |
| **7** | `apu_energy.parquet` | **PASS** | **SAFE WITH WARNING** | Chuỗi tích lũy Ah 12 kênh CMB 1 phút liên tục; có 34 duplicate keys ở giao thoa ngày. |
| **8** | `apu_stat_10s.parquet` | **PASS** | **SAFE WITH WARNING** | Tái tạo dual timestamp thành công, 100% Unique, bảo toàn thứ tự đo của 4 APU. |
| **9** | `apu_stat_60s.parquet` | **PASS** | **SAFE TO USE** | Chuỗi nhiệt độ van IGBT và cuộn kháng AC 1 phút sạch 100%, 0 duplicate key. |
| **10** | `apu_stat_trig.parquet` | **PASS** | **SAFE WITH WARNING** | Dữ liệu trigger sự cố APU chuẩn, không có lỗi cấu trúc. |
| **11** | `weather_report.parquet` | **PASS** | **SAFE WITH WARNING** | Độ phủ 27 ngày tháng 10 (độ phân giải 1 giờ) + dữ liệu 1 phút tháng 9; bảo toàn bức xạ âm ban đêm. |
| **12** | `energy_report.parquet` | **PASS** | **SAFE TO USE** | Chuỗi sản lượng điện tích lũy 1 giờ sạch 100%, 102/103 Inverter tăng đơn điệu tuyệt đối. |

---

## 4. Kiểm Toán Timestamp & Tính Liên Tục Thời Gian (Timestamp & Continuity Audit)

| Dataset | Min Timestamp | Max Timestamp | Timestamp Nulls | Duplicate Keys | Bước nhảy phổ biến nhất (Dominant Interval) | Khoảng hở lớn nhất (Largest Gap) |
|---|---|---|:---:|:---:|---|---|
| `aps_ctrl_trig` | 2025-10-01 00:00:00 | 2025-10-27 07:16:00 | 0 | 492 | 60.0s (36.4%) & 0.0s (Event) | 09 giờ 45 phút |
| `aps_energy` | 2025-10-01 00:00:00 | 2025-10-27 09:09:00 | 0 | 2 | **60.0s (100.0%)** | 08 giờ 42 phút |
| `aps_stat_60s` | 2025-10-01 00:00:00 | 2025-10-27 09:09:00 | 0 | **0** | **60.0s (100.0%)** | 08 giờ 42 phút |
| `aps_stat_trig` | 2025-10-01 00:00:00 | 2025-10-27 08:52:00 | 0 | 1,146 | 0.0s (41.9% đa lỗi cùng lúc) | 09 giờ 44 phút |
| `aps_switching_cycles` | 2025-10-01 00:00:00 | 2025-10-27 05:32:00 | 0 | 167 | 0.0s (Snapshot ca) | 18 giờ 27 phút |
| `apu_ctrl_trig` | 2025-10-01 00:00:00 | 2025-10-27 09:04:00 | 0 | 231,433 | 0.0s (84.1% setpoint 3 pha) | 09 giờ 45 phút |
| `apu_energy` | 2025-10-01 00:00:00 | 2025-10-27 09:09:00 | 0 | 34 | **60.0s (100.0%)** | 08 giờ 42 phút |
| `apu_stat_10s` | 2025-10-01 00:00:00 | 2025-10-27 09:09:50 | 0 | **0** | **10.0s (89.3%)** | 08 giờ 42 phút 10s |
| `apu_stat_60s` | 2025-10-01 00:00:00 | 2025-10-27 09:09:00 | 0 | **0** | **60.0s (100.0%)** | 08 giờ 44 phút |
| `apu_stat_trig` | 2025-10-01 00:00:00 | 2025-10-27 05:32:00 | 0 | 4,374 | 0.0s (89.9% alarm song song) | 12 giờ 04 phút |
| `weather_report` | 2025-08-16 19:00:00 | 2025-10-27 08:00:00 | 0 | **0** | **60.0s (Tháng 9) & 3600.0s (Tháng 10)** | 16 ngày 09 giờ (Giữa T8 và T9) |
| `energy_report` | 2025-10-01 00:00:00 | 2025-10-27 09:00:00 | 0 | **0** | **3600.0s (100.0% liên tục)** | 01 giờ 00 phút (Không có gap) |

---

## 5. Kiểm Toán Trùng Lặp (Duplicate Audit)

1. **Trùng lặp 100% dòng (Exact Full-Row Duplicates)**:
   - Trong tất cả 12 file Parquet đầu ra: **Exact duplicate rows = 0**.
   - Toàn bộ các dòng trùng lặp 100% phát sinh do ghép nối file hàng ngày và log buffer đã được loại bỏ chính xác ở tầng tiền xử lý (`keep='first'`).
2. **Trùng lặp khóa nghiệp vụ (Business Key Duplicates)**:
   - **Nhóm chuỗi thời gian liên tục (`aps_stat_60s`, `apu_stat_10s`, `apu_stat_60s`, `weather_report`, `energy_report`)**: Duplicate key `(system, timestamp)` = **0 (100% Unique)**.
   - **Nhóm năng lượng tích lũy (`aps_energy`, `apu_energy`)**: Có lần lượt 2 và 34 mốc thời gian bị lặp tại khoảnh khắc giao thời ngày 00:00:00 do bộ ghi năng lượng chốt sổ ngày cũ và mở sổ ngày mới.
   - **Nhóm Trigger (`aps_ctrl_trig`, `aps_stat_trig`, `apu_ctrl_trig`, `apu_stat_trig`)**: Có nhiều bản ghi mang cùng mốc thời gian/mili-giây vì hệ thống ghi nhận đồng thời nhiều bit thanh ghi khi xảy ra sự kiện.

---

## 6. Kiểm Toán Giá Trị Khuyết (Missing Value Audit)

- **Tỷ lệ Missing tổng thể**: **0.0%** trên toàn bộ 12 dataset trong vùng dữ liệu thực tế.
- Không có bất kỳ cột nào có dữ liệu bị mất ngẫu nhiên (No random missingness).
- Các cột mang giá trị 0 có tính hệ thống:
  * Kênh phần cứng không gắn (`APU 5`, `APU 6`) trong `aps_energy` và `aps_switching_cycles`.
  * Kênh cảm biến không nối (`Tpan/°C` trong `aps_stat_60s`).
  * Các thanh ghi mã lỗi phụ `Error2`..`Error8` mang giá trị 0 khi không có lỗi xếp chồng.

---

## 7. Kiểm Toán Tính Hợp Lý Của Số Liệu & Cảm Biến (Numeric & Sensor Sanity Audit)

| Đại lượng đo lường | Dataset | Giá trị Min | Giá trị Max | Giá trị Mean | Phân loại & Đánh giá nghiệp vụ |
|---|---|:---:|:---:|:---:|---|
| **Nhiệt độ cuộn kháng AC (`tind_c`)** | `apu_stat_60s` | $29.75^\circ\text{C}$ | $156.27^\circ\text{C}$ | $68.42^\circ\text{C}$ | **Expected Behavior**: Cuộn kháng phát nhiệt cao khi inverter chạy đầy tải buổi trưa. |
| **Nhiệt độ van IGBT (`tl1_c`..`tl3_c`)** | `apu_stat_60s` | $31.90^\circ\text{C}$ | $94.90^\circ\text{C}$ | $52.18^\circ\text{C}$ | **Expected Behavior**: Nằm trong giới hạn chịu nhiệt của IGBT ($<125^\circ\text{C}$). |
| **Nhiệt độ môi trường trạm (`tamb_c`)** | `aps_stat_60s` | $-20.00^\circ\text{C}$ | $44.86^\circ\text{C}$ | $30.12^\circ\text{C}$ | **Confirmed Anomaly**: Giá trị $-20.0^\circ\text{C}$ tại 08:41 ngày 04/10 là mã lỗi hở mạch PT100, đã gắn cờ `is_sensor_fault=True`. |
| **Bức xạ mặt trời (`radiation_w_m2`)** | `weather_report` | $-3.98\,\text{W/m}^2$ | $1,284.10\,\text{W/m}^2$ | $214.85\,\text{W/m}^2$ | **Expected Behavior**: Giá trị âm ban đêm do dòng tối cảm biến, đỉnh trưa $1,284\,\text{W/m}^2$ phù hợp Ninh Thuận. |
| **Điện áp AC pha (`vl1n_v`)** | `apu_stat_10s` | $348.12\,\text{V}$ | $394.50\,\text{V}$ | $378.45\,\text{V}$ | **Expected Behavior**: Dao động $\pm 5\%$ quanh điện áp danh định $380\,\text{V}$. |
| **Dòng điện AC pha (`il1_a`)** | `apu_stat_10s` | $0.00\,\text{A}$ | $1,618.42\,\text{A}$ | $342.10\,\text{A}$ | **Expected Behavior**: Dòng phát cao điểm của biến tần trung tâm 2.5 MW. |
| **Tần số lưới (`f_hz`)** | `apu_stat_10s` | $49.78\,\text{Hz}$ | $50.24\,\text{Hz}$ | $50.01\,\text{Hz}$ | **Expected Behavior**: Ổn định quanh tần số danh định $50.0\,\text{Hz}$. |

---

## 8. Phát Hiện Chi Tiết Theo Từng Dataset (Dataset-Specific Findings)

### A. `apu_stat_10s.parquet` (963,659 dòng)
* **Xác nhận tái tạo Dual Timestamp**:
  * Có **143,430 nhóm (phút $\times$ APU)** có kích thước chuẩn $N=6$ ($860,580$ dòng, chiếm **95.70%**), được gán chính xác các bước $+0\text{s}, +10\text{s}, +20\text{s}, +30\text{s}, +40\text{s}, +50\text{s}$.
  * Có **6,442 nhóm** có kích thước $N \ne 6$ ($103,079$ dòng, chiếm **4.30%**) do biến tần flush buffer lúc khởi động sáng sớm ($05:31 \to 05:32$), được phân bố tỷ lệ đều trong $[0, 59.99\text{s}]$.
  * **Phân bố kích thước nhóm ($N$)**:
    - $N=6$: 143,430 nhóm
    - $N=8$: 3,510 nhóm
    - $N=7$: 2,368 nhóm
    - $N=9$: 280 nhóm
    - $N=10$: 142 nhóm
    - $N=11 \to 34$: 34 nhóm
    - $N=229 \to 594$ (Buffer flush sáng sớm): 78 nhóm
  * **Kết luận**: Khóa `(system, timestamp)` đạt **100% Unique** và bảo toàn tuyệt đối thứ tự vật lý nguyên bản của dữ liệu đo.

### B. `aps_ctrl_trig`, `aps_stat_trig`, `apu_ctrl_trig`, `apu_stat_trig`
* Là dữ liệu trigger theo sự kiện (Event-driven).
* Các bản ghi trùng timestamp/mili-giây phản ánh sự kiện đa kênh xảy ra đồng thời (ví dụ đổi setpoint công suất cả 3 pha L1, L2, L3 trong cùng một chu kỳ quét PLC).
* **Kết luận**: Hợp lệ theo thiết kế SCADA, không được ép lưới hay xóa bỏ.

### C. `aps_energy`, `apu_energy`
* Tần suất lấy mẫu thực tế là **1 phút (60.0s, chiếm 100.0%)**.
* Tăng đơn điệu tăng dần theo ngày.
* **Kết luận**: Hoàn toàn đồng bộ với chuỗi 1 phút của `aps_stat_60s` và `power_report`.

### D. `weather_report.parquet` (21,672 dòng)
* Chứa chuỗi dữ liệu **1 giờ (24 điểm/ngày)** cho toàn bộ 27 ngày tháng 10/2025 (từ ngày 01/10 đến ngày 27/10).
* Chứa chuỗi dữ liệu 1 phút lịch sử của nửa đầu tháng 9/2025 (từ 02/09 đến 16/09) được lưu kèm trong template SCADA gốc.
* **Kết luận**: Khi ghép với dữ liệu Inverter tháng 10, sử dụng dải đo tháng 10 với bước nhảy 1 giờ.

### E. `energy_report.parquet` (634 dòng)
* Tần suất lấy mẫu: **1 giờ liên tục (3600.0s, 100% số bước)** từ `2025-10-01 00:00:00` đến `2025-10-27 09:00:00`.
* 102/103 cột sản lượng Inverter (+MWh) tăng đơn điệu tuyệt đối. Cột `block_7_inv_4_mwh` có 1 điểm giảm do reset thanh ghi công tơ Inverter 7.4.
* **Kết luận**: Dữ liệu chuẩn xác 100% cho bài toán đối soát sản lượng tổng.

---

## 9. Các Vấn Đề Cần Người Dùng Quyết Định (Decisions Required)

1. **Đơn vị của `IdcMax/V` và `IdcMin/V` trong `apu_ctrl_trig`**:
   - Hiện giữ nguyên nhãn `__needs_domain_confirmation` và hậu tố `_v`.
   - *Khuyến nghị*: Trong các phân tích dòng điện DC, hiểu giá trị này theo đơn vị Ampe ($+2440\,\text{A} / -2440\,\text{A}$).
2. **Xử lý dải thời gian của `weather_report` khi ghép nối**:
   - Khi join với dữ liệu Inverter (tháng 10), chỉ lọc dải thời gian từ `2025-10-01` đến `2025-10-27` (bỏ phần dữ liệu kiểm tra tháng 8 & 9).

---

## 10. Những Vấn Đề Tuyệt Đối KHÔNG Nên Sửa (Do Not Modify)

1. **Không xóa các bản ghi cùng mili-giây trong trigger logs**: Vì đó là các thanh ghi điều khiển và cảnh báo đồng thời.
2. **Không xóa hay clip về 0 bức xạ âm ban đêm trong cột gốc**: Giữ nguyên hiện tượng vật lý dark current của pyranometer.
3. **Không xóa đỉnh nhiệt độ $156.27^\circ\text{C}$ của cuộn kháng AC**: Đây là hiện tượng phát nhiệt thực tế khi biến tần hoạt động ở công suất tối đa.
4. **Không thay thế $-20.0^\circ\text{C}$ bằng 0 hay giá trị trung bình**: Giữ nguyên và sử dụng cờ `is_sensor_fault`.

---

## 11. Khuyến Nghị Phân Loại Cho Từng Dataset

* **SAFE TO USE (Sẵn sàng 100% cho EDA và mô hình hóa)**:
  - `aps_stat_60s.parquet`
  - `apu_stat_60s.parquet`
  - `energy_report.parquet`
  - `power_report.parquet`
* **SAFE WITH WARNING (Sẵn sàng sử dụng, chú ý bản chất trigger / dual timestamp)**:
  - `apu_stat_10s.parquet` (Sử dụng cột `timestamp` sau offset hoặc `timestamp_original`)
  - `aps_energy.parquet` & `apu_energy.parquet` (Chuỗi tích lũy năng lượng 1 phút)
  - `weather_report.parquet` (Lọc dải đo tháng 10 khi ghép nối)
  - `aps_ctrl_trig.parquet`, `aps_stat_trig.parquet`, `apu_ctrl_trig.parquet`, `apu_stat_trig.parquet`, `aps_switching_cycles.parquet` (Xử lý theo dạng sự kiện rời rạc)

---
*Tệp tóm tắt số liệu đã được xuất tại [dataset_audit_summary.csv](file:///c:/PV/dataset_audit_summary.csv).*
