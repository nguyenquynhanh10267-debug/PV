"""
plotting.py
===========
Thư viện vẽ biểu đồ tương tác Plotly chuẩn hóa cho các mô-đun EDA Solar PV.
"""

from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import COLORS, PLOTLY_TEMPLATE


def plot_timeseries_dual_axis(
    df: pd.DataFrame,
    x_col: str,
    y1_cols: List[str],
    y2_cols: List[str],
    y1_names: Optional[List[str]] = None,
    y2_names: Optional[List[str]] = None,
    title: str = "Time Series Plot",
    y1_title: str = "Primary Axis",
    y2_title: str = "Secondary Axis",
    y1_colors: Optional[List[str]] = None,
    y2_colors: Optional[List[str]] = None,
    event_markers: Optional[pd.DataFrame] = None
) -> go.Figure:
    """Vẽ biểu đồ chuỗi thời gian 2 trục Y với hover tooltips và range slider."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Vẽ trục Y1 (Chính)
    for i, col in enumerate(y1_cols):
        name = y1_names[i] if y1_names and i < len(y1_names) else col
        color = y1_colors[i] if y1_colors and i < len(y1_colors) else None
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                name=name,
                mode="lines",
                line=dict(color=color, width=2) if color else dict(width=2),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}<extra></extra>"
            ),
            secondary_y=False
        )
        
    # Vẽ trục Y2 (Phụ)
    for j, col in enumerate(y2_cols):
        name = y2_names[j] if y2_names and j < len(y2_names) else col
        color = y2_colors[j] if y2_colors and j < len(y2_colors) else None
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                name=name,
                mode="lines",
                line=dict(color=color, width=2, dash="dot") if color else dict(width=2, dash="dot"),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}<extra></extra>"
            ),
            secondary_y=True
        )
        
    # Thêm Event Markers nếu có
    if event_markers is not None and not event_markers.empty and "timestamp" in event_markers.columns:
        fig.add_trace(
            go.Scatter(
                x=event_markers["timestamp"],
                y=event_markers.get("y_val", [0]*len(event_markers)),
                mode="markers",
                marker=dict(symbol="x", size=10, color="red"),
                name="Sự cố / Trip",
                text=event_markers.get("label", ["Event"]*len(event_markers)),
                hovertemplate="<b>SỰ CỐ:</b> %{text}<br>Thời gian: %{x}<extra></extra>"
            ),
            secondary_y=False
        )
        
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1D3557")),
        template=PLOTLY_TEMPLATE,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(showgrid=True, gridcolor="#F0F0F0")
    )
    fig.update_yaxes(title_text=y1_title, secondary_y=False, showgrid=True, gridcolor="#F0F0F0")
    fig.update_yaxes(title_text=y2_title, secondary_y=True, showgrid=False)
    return fig


def plot_scatter_correlation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Correlation Scatter Plot",
    x_title: str = "X Axis",
    y_title: str = "Y Axis",
    color_col: Optional[str] = None,
    color_title: Optional[str] = None
) -> go.Figure:
    """Vẽ biểu đồ phân tán kiểm tra tương quan vật lý."""
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        title=title,
        labels={x_col: x_title, y_col: y_title, color_col: color_title or color_col},
        template=PLOTLY_TEMPLATE,
        opacity=0.6
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1D3557")),
        margin=dict(l=40, r=40, t=50, b=40)
    )
    return fig


def plot_inverter_ranking_bar(
    df_ranking: pd.DataFrame,
    metric_col: str = "energy_mwh",
    title: str = "Xếp Hạng Sản Lượng Inverter",
    metric_title: str = "Sản lượng (MWh)",
    top_n: int = 20
) -> go.Figure:
    """Vẽ biểu đồ cột xếp hạng Inverter (Top N hoặc Toàn bộ)."""
    sub_df = df_ranking.head(top_n) if top_n > 0 else df_ranking
    
    fig = px.bar(
        sub_df,
        x="inverter_id",
        y=metric_col,
        color=metric_col,
        color_continuous_scale="Blues",
        title=title,
        labels={"inverter_id": "Inverter", metric_col: metric_title},
        template=PLOTLY_TEMPLATE
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1D3557")),
        xaxis=dict(tickangle=-45),
        margin=dict(l=40, r=40, t=50, b=80)
    )
    return fig


def plot_pq_capability_diagram(
    df_10s: pd.DataFrame,
    p_col: str = "pl1_kw",
    q_col: str = "ql1_kvar",
    title: str = "P-Q Capability Diagram"
) -> go.Figure:
    """Vẽ biểu đồ khả năng phát công suất phản kháng P vs Q."""
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=df_10s[p_col],
            y=df_10s[q_col],
            mode="markers",
            marker=dict(size=4, color="#457B9D", opacity=0.5),
            name="Điểm vận hành (P, Q)",
            hovertemplate="P: %{x:.1f} kW<br>Q: %{y:.1f} kVar<extra></extra>"
        )
    )
    
    # Vẽ trục tọa độ 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1D3557")),
        xaxis_title="Công suất tác dụng P (kW)",
        yaxis_title="Công suất phản kháng Q (kVar)",
        template=PLOTLY_TEMPLATE,
        margin=dict(l=40, r=40, t=50, b=40)
    )
    return fig


def plot_pareto_chart(
    df_counts: pd.DataFrame,
    category_col: str,
    count_col: str,
    title: str = "Pareto Chart"
) -> go.Figure:
    """Vẽ biểu đồ Pareto cho các mã lỗi / cảnh báo."""
    df_sorted = df_counts.sort_values(count_col, ascending=False).reset_index(drop=True)
    df_sorted["cumulative_pct"] = (df_sorted[count_col].cumsum() / df_sorted[count_col].sum()) * 100.0
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=df_sorted[category_col],
            y=df_sorted[count_col],
            name="Số lần xuất hiện",
            marker_color="#E63946"
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_sorted[category_col],
            y=df_sorted["cumulative_pct"],
            name="Tỷ lệ tích lũy (%)",
            mode="lines+markers",
            line=dict(color="#1D3557", width=2)
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1D3557")),
        template=PLOTLY_TEMPLATE,
        xaxis=dict(tickangle=-30),
        margin=dict(l=40, r=40, t=50, b=60)
    )
    fig.update_yaxes(title_text="Số lần xuất hiện", secondary_y=False)
    fig.update_yaxes(title_text="Tỷ lệ tích lũy (%)", secondary_y=True, range=[0, 105])
    return fig


def add_event_marker_line(
    fig: go.Figure,
    event_timestamp: Any,
    label: str = "ERROR",
    line_color: str = "#E63946",
    line_dash: str = "dash"
) -> go.Figure:
    """Thêm vạch sự kiện thẳng đứng lên biểu đồ Plotly một cách an toàn, tương thích mọi phiên bản Timestamp."""
    try:
        ts_dt = pd.to_datetime(event_timestamp).to_pydatetime()
    except Exception:
        ts_dt = event_timestamp

    fig.add_shape(
        type="line",
        x0=ts_dt,
        x1=ts_dt,
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line=dict(color=line_color, width=2, dash=line_dash)
    )
    fig.add_annotation(
        x=ts_dt,
        y=1.02,
        xref="x",
        yref="paper",
        text=label,
        showarrow=False,
        font=dict(color=line_color, size=11, family="Arial"),
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor=line_color,
        borderwidth=1
    )
    return fig

