"""
config.py
=========
Cấu hình trung tâm cho hệ thống EDA Web Interactive nhà máy điện mặt trời Trung Nam.
Bao gồm từ điển mã lỗi chuẩn Siemens SINACON PV (Operating Instructions) và ánh xạ phân tầng thiết bị.
"""

from pathlib import Path
from typing import Dict, List

# Thư mục dữ liệu
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "data" / "reports"
OUTPUTS_DIR = BASE_DIR / "eda" / "outputs"

# Tạo thư mục outputs nếu chưa có
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUTS_DIR / "csv").mkdir(parents=True, exist_ok=True)
(OUTPUTS_DIR / "reports").mkdir(parents=True, exist_ok=True)

# Khoảng thời gian khả dụng của dữ liệu
MIN_DATE_STR = "2025-10-01"
MAX_DATE_STR = "2025-10-27"
DEFAULT_SELECTED_DATE = "2025-10-04"

# Cấu hình phát hiện sự cố cấp trạm từ đa ngăn APU (Heuristic Tolerance Window)
APS_ERROR_WINDOW_SECONDS = 60

# Bảng màu chuẩn hóa cho Event, Error, Warning và Solar PV Theme
COLORS = {
    # Nhóm sự kiện & mã lỗi
    "apu_error": "#E63946",               # Đỏ tươi cho Lỗi APU (APU ERROR)
    "aps_error": "#780000",               # Đỏ sẫm / Dark Crimson cho Lỗi APS (APS ERROR)
    "four_apu_correlated": "#9B2226",     # Đỏ bầm cho Sự cố đồng thời 4 APU
    "warning": "#F4A261",                 # Cam hổ phách cho Cảnh báo (WARNING)
    "normal": "#2A9D8F",                  # Xanh ngọc cho Bình thường (NORMAL)

    # Các thông số vật lý
    "ac_power": "#FF9900",                # Cam mặt trời
    "dc_power": "#0066CC",                # Xanh dương đậm
    "radiation": "#FFCC00",               # Vàng rực rỡ
    "temperature": "#E63946",             # Đỏ nhiệt
    "ambient_temp": "#457B9D",            # Xanh biển
    "reactor_temp": "#9B2226",            # Đỏ bầm
    "igbt_temp": "#D62828",               # Đỏ tươi
    "efficiency": "#2A9D8F",              # Xanh ngọc
    "voltage_l1": "#E63946",              # Đỏ (Pha A)
    "voltage_l2": "#F4A261",              # Vàng (Pha B)
    "voltage_l3": "#2A9D8F",              # Xanh (Pha C)
    "frequency": "#6A4C93",               # Tím
    "active_power": "#1D3557",            # Xanh navy
    "reactive_power": "#457B9D",          # Xanh lơ
    "grid_gray": "#E0E0E0",
    "background": "#FFFFFF",
    "card_bg": "#F8F9FA"
}

# Template biểu đồ Plotly
PLOTLY_TEMPLATE = "plotly_white"

# ==============================================================================
# TỪ ĐIỂN MÃ LỖI CHUẨN TÀI LIỆU KỸ THUẬT SIEMENS (SINACON PV Operating Instructions)
# ==============================================================================

ERROR_CODES_APS = {
    1: "Modbus TCP value out of range",
    2: "Configuration corrupt",
    3: "APU 1/2 cooling fluid low",
    4: "APU 3/4 cooling fluid low",
    5: "No enable signal",
    6: "No supply voltage",
    7: "Medium voltage switch gear off",
    8: "DI Temperature not OK",
    9: "DI medium voltage transformer error",
    10: "APU 1/2 water pump switching cycles",
    11: "APU 3/4 water pump switching cycles",
    12: "APU 5/6 water pump switching cycles",
    13: "APU 1/2 air-to-air cooler switching cycles",
    14: "APU 3/4 air-to-air cooler switching cycles",
    15: "APU 5/6 air-to-air cooler switching cycles",
    16: "APU 1/2 water air cooler switching cycles",
    17: "APU 3/4 water air cooler switching cycles",
    18: "APU 5/6 water air cooler switching cycles",
    19: "Supply voltage low",
    20: "Modbus TCP timeout",
    21: "APU 1/2 insulation",
    22: "APU 3/4 insulation",
    23: "APU 5/6 insulation",
    24: "Medium voltage transformer temperature high",
    25: "APU 5/6 cooling fluid low",
    26: "Error count overrun",
    27: "APU 1/2 insulation monitor failed",
    28: "APU 3/4 insulation monitor failed",
    29: "APU 5/6 insulation monitor failed",
    30: "APU 1 Powerlink",
    31: "APU 2 Powerlink",
    32: "APU 3 Powerlink",
    33: "APU 4 Powerlink",
    34: "APU 5 Powerlink",
    35: "APU 6 Powerlink",
    36: "APU 1 type mismatch",
    37: "APU 2 type mismatch",
    38: "APU 3 type mismatch",
    39: "APU 4 type mismatch",
    40: "APU 5 type mismatch",
    41: "APU 6 type mismatch",
    42: "APS unlicensed",
    43: "Internal configuration not valid",
    44: "APU Update",
    45: "APMC - Battery missing/empty",
    46: "APU1/2 Insulation Monitoring (pos. ground)",
    47: "APU3/4 Insulation Monitoring (pos. ground)",
    48: "APU1/2 Insulation Monitoring (neg. ground)",
    49: "APU3/4 Insulation Monitoring (neg. ground)",
    50: "APU1/2 extern Insulation Monitoring",
    51: "APU3/4 extern Insulation Monitoring",
    53: "APU1/2 high Temperature",
    54: "APU3/4 high Temperature",
    55: "APU1/2 Island Fuses",
    56: "APU3/4 Island Fuses",
    57: "Humidity too high",
}


ERROR_CODES_APU = {
    1: "Overtemperature IGBT L1",
    2: "Overtemperature IGBT L2",
    3: "Overtemperature IGBT L3",
    4: "Overtemperature inductance",
    5: "Overvoltage Vdc pos. SW",
    6: "Overvoltage Vdc neg. SW",
    7: "Overvoltage Vdc total SW",
    8: "Undervoltage Vdc pos. SW",
    9: "Undervoltage Vdc neg. SW",
    10: "Undervoltage Vdc total SW",
    11: "Overcurrent Idc SW",
    12: "Overcurrent Iac L1 SW",
    13: "Overcurrent Iac L2 SW",
    14: "Overcurrent Iac L3 SW",
    16: "Grid rotation Error",
    17: "Overfrequency level 1",
    18: "Overfrequency level 2",
    19: "Overfrequency level 3",
    20: "Underfrequency level 1",
    21: "Underfrequency level 2",
    22: "Overvoltage VL1 level 1",
    23: "Overvoltage VL1 level 2",
    24: "Overvoltage VL1 level 3",
    25: "Overvoltage VL2 level 1",
    26: "Overvoltage VL2 level 2",
    27: "Overvoltage VL2 level 3",
    28: "Overvoltage VL3 level 1",
    29: "Overvoltage VL3 level 2",
    30: "Overvoltage VL3 level 3",
    31: "Undervoltage VL1 level 1",
    32: "Undervoltage VL1 level 2",
    33: "Undervoltage VL2 level 1",
    34: "Undervoltage VL2 level 2",
    35: "Undervoltage VL3 level 1",
    36: "Undervoltage VL3 level 2",
    37: "Driver L1",
    38: "Driver L2",
    39: "Driver L3",
    40: "Overcurrent Idc HW",
    41: "Overcurrent Iac L1 HW",
    42: "Overcurrent Iac L2 HW",
    43: "Overcurrent Iac L3 HW",
    44: "Overtemperature IGBT HW",
    46: "Supply error",
    47: "Supply error delayed",
    48: "Overvoltage Vdc neg. HW",
    49: "Undervoltage Vdc neg. HW",
    50: "Overvoltage Vdc pos. HW",
    51: "Undervoltage Vdc pos. HW",
    52: "Overvoltage Vdc total HW",
    53: "Supply error 15V neg. SW",
    54: "Supply error 15V pos. sum. SW",
    56: "Supply error 24V driver pos. SW",
    57: "Supply error 24V neg. SW",
    58: "Supply error 24V pos. SW",
    59: "Supply error 5V pos. SW",
    60: "AC switch",
    61: "DC switch",
    62: "Enable 24V",
    63: "Driver version L1",
    64: "Driver version L2",
    65: "Driver version L3",
    66: "CPLD version",
    67: "HW control card",
    68: "Model control card",
    69: "AC pre-charge",
    70: "DC pre-charge",
    71: "Sector synchronisation",
    72: "No sync. signal",
    73: "Wrong firmware version",
    74: "Wrong control mode",
    75: "Current sum error",
    76: "Driver L1 (booster)",
    77: "Driver L2 (booster)",
    78: "Driver L3 (booster)",
    79: "Overcurrent Idc HW",
    80: "Overcurrent Iac L1 HW",
    81: "Overcurrent Iac L2 HW",
    82: "Overcurrent Iac L3 HW",
    83: "PWM error",
    84: "Overvoltage Vdc neg. HW",
    85: "Undervoltage Vdc neg. HW",
    86: "Overvoltage Vdc pos. HW",
    87: "Undervoltage Vdc pos. HW",
    88: "Overvoltage Vdc total HW",
    89: "Overtemperature IGBT HW",
    90: "Overcurrent Booster HW",
    91: "Driver Chopper",
    92: "Supply error",
    93: "Supply error delayed",
    94: "Driver Booster",
    95: "No driver detected",
    96: "Overvoltage VL1 level 4",
    97: "Overvoltage VL2 level 4",
    98: "Overvoltage VL3 level 4",
    99: "Overvoltage mean level 1",
    100: "Overtemperature Control Card SW",
    101: "Wrong version control card",
    102: "Voltage measurement Island grid",
    103: "Unbalanced grid voltage",
    104: "Unbalanced phase angle",
    105: "Unbalanced grid current",
    106: "Overcurrent Idc SW pos",
    107: "Overcurrent Idc SW neg",
    108: "Undervoltage VL1 level 3",
    109: "Undervoltage VL2 level 3",
    110: "Undervoltage VL3 level 3",
    111: "Discharge Udc pos",
    112: "Discharge Udc neg",
    113: "Wrong Op mode for overcurrent test",
    114: "Wrong variant to Uac nom",
}


WARNING_CODES = {
    1: "APU 1/2 cooling fluid low",
    2: "APU 3/4 cooling fluid low",
    3: "Time synchronisation failed",
    4: "Modbus RTU (Display)",
    5: "AC surge arrester tripped",
    6: "DC surge arrester tripped",
    7: "APU 1/2 insulation monitor failed",
    8: "APU 3/4 insulation monitor failed",
    9: "APU 5/6 insulation monitor failed",
    10: "APU 1/2 insulation level 2",
    11: "APU 3/4 insulation level 2",
    12: "APU 5/6 insulation level 2",
    13: "APU 1/2 insulation level 1",
    14: "APU 3/4 insulation level 1",
    15: "APU 5/6 insulation level 1",
    22: "APU 1 error",
    23: "APU 2 error",
    24: "APU 3 error",
    25: "APU 4 error",
    29: "APU 1 Powerlink",
    30: "APU 2 Powerlink",
    31: "APU 3 Powerlink",
    32: "APU 4 Powerlink",
    35: "Power limit transformer",
    36: "Power limit ambient",
    37: "APU 1 error counter overrun",
    38: "APU 2 error counter overrun",
    39: "APU 3 error counter overrun",
    40: "APU 4 error counter overrun",
    43: "APU in manual mode",
    44: "Cooling in manual mode",
    45: "Heating in manual mode",
    46: "APU in service mode",
    47: "Log samples lost",
    48: "APU 1/2 current measurement",
    49: "APU 3/4 current measurement",
    51: "APU 1/2 Powerlink flicker",
    52: "APU 3/4 Powerlink flicker",
    54: "APU1/2 insulation monitoring (pos. ground)",
    55: "APU3/4 insulation monitoring (pos. ground)",
    56: "APU1/2 insulation monitoring (neg. ground)",
    57: "APU3/4 insulation monitoring (neg. ground)",
    58: "APU1/2 extern insulation monitoring",
    59: "APU3/4 extern insulation monitoring",
    60: "USB-device almost full",
    61: "USB-device full",
    62: "CMB update",
    63: "IMD update",
    64: "Max ModbusTCP master exceeded",
    65: "APU 1 disable",
    66: "APU 2 disable",
    67: "APU 3 disable",
    68: "APU 4 disable",
    69: "USB-Device failed",
}

# ==============================================================================
# TRẠNG THÁI VẬN HÀNH (OPSTATE MAP)
# ==============================================================================
OPSTATE_MAP = {
    0: "Chưa khởi tạo (Uninitialized)",
    10: "Dừng hoàn toàn (Stop)",
    20: "Chờ kết nối AC (Waiting for AC)",
    30: "Đồng bộ lưới điện AC (Grid Synchronisation)",
    40: "Nạp trước DC (DC Precharge)",
    50: "Tắt / Nghỉ ban đêm (Off)",
    60: "Chờ điều kiện vận hành (Standby)",
    70: "Đang xả điện áp DC (Discharging)",
    80: "Chế độ kiểm tra (Test Mode)",
    90: "Chế độ bảo trì thủ công (Manual / Service)",
    100: "Khởi động biến tần (Starting)",
    110: "Chờ đủ điện áp DC (Waiting for DC)",
    120: "Đang phát điện lên lưới (Feed-in / MPP Operation)",
    130: "Dừng sự cố / Ngắt bảo vệ (Protective Trip / Error)",
    140: "Tự động ngắt ban đêm (Night Shutdown)",
    150: "Khởi động lại sau sự cố (Restarting)",
    160: "Giảm tải công suất bảo vệ biến tần (Power Derating)",
    330: "Ngắt bảo vệ phần cứng (Hardware Trip 330)",
    20000: "Vận hành bình thường (Normal Operation)"
}

# Ánh xạ cảnh báo về đúng thiết bị phát sinh lỗi
WARNING_DEVICE_ROUTING = {
    22: "APU 1", 23: "APU 2", 24: "APU 3", 25: "APU 4",
    29: "APU 1", 30: "APU 2", 31: "APU 3", 32: "APU 4",
    37: "APU 1", 38: "APU 2", 39: "APU 3", 40: "APU 4",
    65: "APU 1", 66: "APU 2", 67: "APU 3", 68: "APU 4",
    5: "APS", 6: "APS", 35: "APS",
    3: "SYSTEM", 4: "SYSTEM", 36: "SYSTEM", 47: "SYSTEM", 57: "SYSTEM",
    60: "SYSTEM", 61: "SYSTEM", 64: "SYSTEM", 69: "SYSTEM"
}

# Ánh xạ mã lỗi APS chỉ đích danh APU
APS_ERROR_DEVICE_ROUTING = {
    30: "APU 1", 31: "APU 2", 32: "APU 3", 33: "APU 4",
    36: "APU 1", 37: "APU 2", 38: "APU 3", 39: "APU 4"
}
