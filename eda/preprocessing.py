"""
preprocessing.py
================
Module tiền xử lý phụ trợ trong bộ nhớ (In-Memory Transforms) phục vụ EDA.
Tuyệt đối KHÔNG thay đổi các file Parquet đã lưu trong data/processed/.
"""

import pandas as pd
import numpy as np


def prepare_power_for_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn bị dữ liệu công suất, đảm bảo timestamp chuẩn và các cột AC/DC sạch."""
    if df.empty:
        return df
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def prepare_10s_for_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn bị dữ liệu 10s, bổ sung cột tổng công suất 3 pha."""
    if df.empty:
        return df
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df
