#!/usr/bin/env python3
"""
鹿鼎公策略 · 可视化诊断报告
读取回测输出的快照 CSV，生成交互式图表 HTML 报告
"""
import argparse
import glob
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 股票代码 → 名称映射
STOCK_NAMES = {
    '601088': '中国神华', '601225': '陕西煤业', '600985': '淮北矿业',
    '002738': '中矿资源', '002466': '天齐锂业', '002460': '赣锋锂业',
    '000933': '神火股份', '000807': '云铝股份', '600079': '人福医药',
    '603345': '安井食品', '601898': '中煤能源', '000333': '美的集团',
    '000651': '格力电器',
}


def _stock_label(code: str) -> str:
    """股票代码 → 显示标签：名称(代码)"""
    name = STOCK_NAMES.get(str(code).zfill(6), '')
    return f'{name}({code})' if name else str(code)


def load_latest_snapshot():
    """加载最新的每周持仓快照"""
    pattern = 'reports/weekly_snapshots_*.csv'
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"❌ 未找到快照文件: {pattern}")
        sys.exit(1)
    path = files[-1]
    print(f"📂 加载快照: {path}")
    df = pd.read_csv(path, dtype={'股票代码': str})
    df['日期'] = pd.to_datetime(df['日期'])
    return df


# ---- 图表生成函数 ----

def chart_portfolio_vs_benchmark(df: pd.DataFrame) -> go.Figure:
    """图表1：策略净值 vs 基准净值"""
    # 策略：每周总资产（取每周期第一条记录的 total_value）
    weekly = df.groupby('日期')['总资产'].first().reset_index()
    initial = weekly['总资产'].iloc[0]
    weekly['策略净值'] = weekly['总资产'] / initial

    # 基准：每只股票初始股数 × 每周价格 + 初始现金
    first_week = df[df['日期'] == df['日期'].min()]
    initial_shares = {}
    for _, r in first_week.iterrows():
        if r['持仓股数'] > 0:
            initial_shares[r['股票代码']] = r['持仓股数']
    initial_cash = first_week['总现金'].iloc[0]

    benchmark_vals = []
    for date, grp in df.groupby('日期'):
        val = initial_cash
        for code, shares in initial_shares.items():
            row = grp[grp['股票代码'] == code]
            if not row.empty:
                val += shares * row['当前价格'].iloc[0]
        benchmark_vals.append({'日期': date, '总资产': val})
    bench_df = pd.DataFrame(benchmark_vals)
    bench_df['基准净值'] = bench_df['总资产'] / initial

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weekly['日期'], y=weekly['策略净值'],
                             mode='lines', name='鹿鼎公策略',
                             line=dict(color='#1f77b4', width=2.5)))
    fig.add_trace(go.Scatter(x=bench_df['日期'], y=bench_df['基准净值'],
                             mode='lines', name='买入持有基准',
                             line=dict(color='#7f7f7f', width=2, dash='dash')))

    fig.update_layout(
        title='策略 vs 基准 — 净值走势',
        yaxis_title='净值 (起点=1.0)',
        hovermode='x unified',
        legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01),
    )
    return fig


def chart_cash_utilization(df: pd.DataFrame) -> go.Figure:
    """图表2：现金占比 + 股票市值占比"""
    weekly = df.groupby('日期').agg(
        总资产=('总资产', 'first'),
        总现金=('总现金', 'first'),
    ).reset_index()
    weekly['现金占比'] = weekly['总现金'] / weekly['总资产'] * 100
    weekly['股票占比'] = 100 - weekly['现金占比']

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weekly['日期'], y=weekly['股票占比'],
                             mode='lines', name='股票仓位占比',
                             line=dict(color='#2ca02c', width=2),
                             fill='tozeroy', fillcolor='rgba(44,160,44,0.15)'))
    fig.add_trace(go.Scatter(x=weekly['日期'], y=weekly['现金占比'],
                             mode='lines', name='现金占比',
                             line=dict(color='#d62728', width=2),
                             fill='tozeroy', fillcolor='rgba(214,39,40,0.1)'))
    fig.add_hline(y=20, line_dash='dot', line_color='gray',
                  annotation_text='现金警戒线(20%)')

    fig.update_layout(
        title='资金利用率 — 现金 vs 股票仓位占比',
        yaxis_title='占比 (%)',
        hovermode='x unified',
    )
    return fig


def chart_deviation_heatmap(df: pd.DataFrame) -> go.Figure:
    """图表3：仓位占有率热力图 — 当前仓位 / per_stock_cap (%)"""
    df = df.copy()
    df['仓位占上限%'] = (df['持仓市值'] / df['per_stock_cap'] * 100).clip(0, 120)

    pivot = df.pivot_table(index='日期', columns='股票代码',
                           values='仓位占上限%', aggfunc='first')
    pivot = pivot.fillna(0)
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)

    colorscale = [
        [0.0, '#053061'],
        [0.25, '#4393c3'],
        [0.42, '#f7f7f7'],
        [0.67, '#f4a582'],
        [0.83, '#ca0020'],
        [1.0, '#67001f'],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values.T,
        x=pivot.index,
        y=pivot.columns.tolist(),
        colorscale=colorscale,
        zmin=0,
        zmax=120,
        showscale=True,
        colorbar=dict(
            title='仓位占上限%',
            tickvals=[0, 30, 50, 80, 100, 120],
            ticktext=['0%', '30%', '50%', '80%', '100%', '120%'],
        ),
        hovertemplate='%{y} %{x|%Y-%m-%d}<br>仓位: %{z:.0f}% <extra></extra>',
    ))
    fig.update_layout(
        title='仓位占有率热力图 — 各股票仓位占单票上限的百分比',
        xaxis_title='日期',
        yaxis_title='股票代码',
        height=500,
    )
    return fig


def chart_position_composition(df: pd.DataFrame) -> go.Figure:
    """图表4：仓位构成堆叠面积图"""
    weekly_positions = df.pivot_table(
        index='日期', columns='股票代码', values='持仓市值', aggfunc='first'
    ).fillna(0)

    # 全部展示（13只股票可容纳）
    totals = weekly_positions.sum().sort_values(ascending=False)
    plot_df = weekly_positions[totals.index]

    fig = go.Figure()
    for col in plot_df.columns:
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[col],
            mode='lines', name=col,
            stackgroup='one',
            hovertemplate='%{x|%Y-%m-%d}<br>%{y:,.0f}',
        ))
    fig.update_layout(
        title='仓位构成 — 各股票持仓市值堆叠图',
        yaxis_title='持仓市值 (元)',
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.15),
    )
    return fig


def chart_value_ratio_trajectories(df: pd.DataFrame) -> go.Figure:
    """图表5：价值比轨迹 + 区间分界线"""
    pivot = df.pivot_table(index='日期', columns='股票代码',
                           values='价值比', aggfunc='first')

    # 轮换线型和颜色，增加区分度
    dashes = ['solid', 'dash', 'dot', 'dashdot', 'longdash', 'longdashdot']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
              '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8', '#ffbb78']

    fig = go.Figure()
    for i, code in enumerate(pivot.columns):
        series = pivot[code].dropna()
        if series.empty:
            continue
        c = colors[i % len(colors)]
        d = dashes[i % len(dashes)]
        fig.add_trace(go.Scatter(
            x=series.index, y=series,
            mode='lines', name=code,
            line=dict(width=1.8, dash=d, color=c),
        ))
        # 曲线末端标注公司名
        fig.add_annotation(
            x=series.index[-1], y=series.iloc[-1],
            text=code, showarrow=False,
            xanchor='left', xshift=6,
            font=dict(size=10, color=c),
            yshift=0,
        )

    # 区间分界线（灰色虚线，不与公司彩色曲线争视觉）
    for y_val, label in [(0.70, '极度低估上限(0.70)'), (0.80, '低估上限(0.80)'),
                          (1.10, '合理上限(1.10)'), (1.30, '合理偏高上限(1.30)')]:
        fig.add_hline(y=y_val, line_dash='dash', line_color='#999', opacity=0.6,
                      annotation_text=label, annotation_font_size=10)

    fig.update_layout(
        title='价值比轨迹 — 每只股票的 Price/DCF 变化',
        yaxis_title='价值比 (价格/DCF)',
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.2),
    )
    return fig


def _load_kline_data(kline_json_path: str = None, code_labels: dict = None):
    """从 kline_data JSON 加载完整的 K 线 + 指标数据（与 integrated report 同源）"""
    import json as _json
    if kline_json_path is None:
        files = sorted(glob.glob('reports/kline_indicators_*.json'))
        if not files:
            return {}
        kline_json_path = files[-1]
    with open(kline_json_path, 'r', encoding='utf-8') as f:
        raw = _json.load(f)

    if code_labels is None:
        code_labels = {}

    def _to_series(arr):
        if not arr:
            return pd.Series(dtype=float)
        df = pd.DataFrame(arr, columns=['ts', 'val'])
        df['date'] = pd.to_datetime(df['ts'], unit='ms')
        return df.set_index('date')['val']

    result = {}
    for raw_code, sd in raw.items():
        label = code_labels.get(raw_code, raw_code)

        # K 线: [ts, open, close, low, high] → DataFrame
        kline_arr = sd.get('kline', [])
        if kline_arr:
            kline_df = pd.DataFrame(kline_arr, columns=['ts', 'open', 'close', 'low', 'high'])
            kline_df['date'] = pd.to_datetime(kline_df['ts'], unit='ms')
            kline_df = kline_df.set_index('date')
        else:
            kline_df = pd.DataFrame()

        # 交易点
        trades_list = sd.get('trades', [])
        if trades_list:
            trades_df = pd.DataFrame(trades_list)
            trades_df['date'] = pd.to_datetime(trades_df['timestamp'], unit='ms')
        else:
            trades_df = pd.DataFrame()

        # 指标 DataFrame
        ind_df = pd.DataFrame({
            'bb_upper': _to_series(sd.get('bb_upper', [])),
            'bb_mid': _to_series(sd.get('bb_middle', [])),
            'bb_lower': _to_series(sd.get('bb_lower', [])),
            'rsi': _to_series(sd.get('rsi', [])),
            'pvr': _to_series(sd.get('pvr', [])),
            'macd_dif': _to_series(sd.get('macd', {}).get('dif', [])),
            'macd_dea': _to_series(sd.get('macd', {}).get('dea', [])),
            'macd_hist': _to_series(sd.get('macd', {}).get('histogram', [])),
        }).dropna()

        result[label] = {'kline': kline_df, 'trades': trades_df, 'ind': ind_df}
    return result


def chart_trading_timeline(df_snapshot: pd.DataFrame, kline_data: dict = None,
                           trades_path: str = None):
    """图表7：逐只股票 — 4 行子图（K线+BB / PVR / RSI / MACD），共享时间轴，同步缩放"""
    import glob as _glob
    if kline_data is None:
        kline_data = {}

    csv_trades = pd.DataFrame()
    if trades_path:
        csv_trades = pd.read_csv(trades_path)
    else:
        files = sorted(_glob.glob('reports/detailed_trading_records_*.csv'))
        if files:
            csv_trades = pd.read_csv(files[-1])
    if not csv_trades.empty:
        csv_trades = csv_trades.rename(columns={'交易类型': 'type', '交易价格': 'price',
                                                '交易股票数量': 'shares', '股票名称': 'stock_name',
                                                '交易原因': 'reason'})
        csv_trades['日期'] = pd.to_datetime(csv_trades['日期'])
        csv_trades['label'] = csv_trades['stock_name']

    all_stocks = df_snapshot.groupby('股票代码')['持仓市值'].max().sort_values(ascending=False).index.tolist()

    figs = []
    for code in all_stocks:
        kd = kline_data.get(code, {})
        kline_df = kd.get('kline', pd.DataFrame())
        trades_df = kd.get('trades', pd.DataFrame())
        ind_df = kd.get('ind', pd.DataFrame())
        snap = df_snapshot[df_snapshot['股票代码'] == code].sort_values('日期')
        has_kline = not kline_df.empty
        has_ind = not ind_df.empty

        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.44, 0.17, 0.19, 0.20],
            subplot_titles=(code, None, None, None),
        )

        # ----- Row 1: K线 + BB + 交易标记 -----
        if has_kline:
            is_up = kline_df['close'] >= kline_df['open']
            # 影线
            hl_x, hl_y = [], []
            for idx, row in kline_df.iterrows():
                hl_x.extend([idx, idx, idx])
                hl_y.extend([row['low'], row['high'], float('nan')])
            fig.add_trace(go.Scatter(
                x=hl_x, y=hl_y, mode='lines', name='影线',
                line=dict(color='#666', width=0.6),
                showlegend=False, connectgaps=False,
            ), row=1, col=1)
            # 实体
            for mask, color in [(is_up, '#d73027'), (~is_up, '#2ca02c')]:
                if not mask.any():
                    continue
                sub = kline_df[mask]
                bx, by = [], []
                for idx, row in sub.iterrows():
                    bx.extend([idx, idx, idx])
                    by.extend([row['open'], row['close'], float('nan')])
                fig.add_trace(go.Scatter(
                    x=bx, y=by, mode='lines', name='K线',
                    line=dict(color=color, width=3),
                    showlegend=False, connectgaps=False,
                ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=snap['日期'], y=snap['当前价格'],
                mode='lines', name='价格',
                line=dict(color='#333', width=1.5),
            ), row=1, col=1)
        # BB
        if has_ind:
            for bb_col, dash, alpha in [('bb_upper', 'dash', 0.3), ('bb_mid', 'dot', 0.2), ('bb_lower', 'dash', 0.3)]:
                if bb_col in ind_df.columns:
                    fig.add_trace(go.Scatter(
                        x=ind_df.index, y=ind_df[bb_col],
                        mode='lines', line=dict(color='#888', width=0.7, dash=dash),
                        opacity=alpha, showlegend=False,
                    ), row=1, col=1)
        # 交易标记
        trade_source = trades_df if not trades_df.empty else csv_trades
        if not trade_source.empty:
            t = trade_source
            if 'label' in t.columns:
                t = t[t['label'] == code]
            if 'date' not in t.columns and '日期' in t.columns:
                t = t.rename(columns={'日期': 'date'})
            if not t.empty and 'type' in t.columns and 'date' in t.columns:
                buys = t[t['type'].isin(['BUY', '买入'])]
                sells = t[t['type'].isin(['SELL', '卖出'])]
                price_col = 'price' if 'price' in t.columns else '交易价格'
                shares_col = next((c for c in ['shares', '交易股票数量'] if c in t.columns), None)
                reason_col = next((c for c in ['reason', '交易原因'] if c in t.columns), None)
                buy_hover = '<b>买入</b> %{text}股 @%{y:.2f}<br>%{customdata}<extra></extra>' if reason_col else '<b>买入</b> %{text}股 @%{y:.2f}<extra></extra>'
                sell_hover = '<b>卖出</b> %{text}股 @%{y:.2f}<br>%{customdata}<extra></extra>' if reason_col else '<b>卖出</b> %{text}股 @%{y:.2f}<extra></extra>'
                if not buys.empty:
                    fig.add_trace(go.Scatter(
                        x=buys['date'], y=buys[price_col],
                        mode='markers', name='买入',
                        marker=dict(symbol='triangle-up', size=8, color='#d73027', line=dict(width=1, color='white')),
                        text=buys[shares_col].astype(int).astype(str) if shares_col else None,
                        customdata=buys[reason_col] if reason_col else None,
                        hovertemplate=buy_hover,
                        showlegend=False,
                    ), row=1, col=1)
                if not sells.empty:
                    fig.add_trace(go.Scatter(
                        x=sells['date'], y=sells[price_col],
                        mode='markers', name='卖出',
                        marker=dict(symbol='triangle-down', size=8, color='#2ca02c', line=dict(width=1, color='white')),
                        text=sells[shares_col].astype(int).astype(str) if shares_col else None,
                        customdata=sells[reason_col] if reason_col else None,
                        hovertemplate=sell_hover,
                        showlegend=False,
                    ), row=1, col=1)

        # ----- Row 2: PVR -----
        if has_ind and 'pvr' in ind_df.columns:
            fig.add_trace(go.Scatter(
                x=ind_df.index, y=ind_df['pvr'],
                mode='lines', name='PVR',
                line=dict(color='#17becf', width=1.5),
                showlegend=False,
            ), row=2, col=1)
            fig.add_hline(y=100, line_dash='dot', line_color='#999', opacity=0.6, row=2, col=1)

        # ----- Row 3: RSI -----
        if has_ind and 'rsi' in ind_df.columns:
            fig.add_trace(go.Scatter(
                x=ind_df.index, y=ind_df['rsi'],
                mode='lines', name='RSI',
                line=dict(color='#9467bd', width=1.3),
                showlegend=False,
            ), row=3, col=1)
            for lvl, clr in [(70, '#d62728'), (30, '#2ca02c')]:
                fig.add_hline(y=lvl, line_dash='dot', line_color=clr, opacity=0.5, row=3, col=1)

        # ----- Row 4: MACD -----
        if has_ind and 'macd_dif' in ind_df.columns:
            hist_colors = ['#d73027' if v >= 0 else '#2ca02c' for v in ind_df['macd_hist']]
            fig.add_trace(go.Bar(
                x=ind_df.index, y=ind_df['macd_hist'],
                marker_color=hist_colors, showlegend=False,
            ), row=4, col=1)
            for col_name, color, dash in [('macd_dif', '#1f77b4', None), ('macd_dea', '#ff7f0e', 'dash')]:
                if col_name in ind_df.columns:
                    fig.add_trace(go.Scatter(
                        x=ind_df.index, y=ind_df[col_name],
                        mode='lines', line=dict(color=color, width=1, dash=dash),
                        showlegend=False,
                    ), row=4, col=1)
            fig.add_hline(y=0, line_color='#aaa', line_width=0.5, row=4, col=1)

        fig.update_layout(
            height=600,
            margin=dict(l=45, r=10, t=30, b=25),
            showlegend=False,
            hovermode='x',
        )
        fig.update_yaxes(title_text='价格', row=1, col=1)
        fig.update_yaxes(title_text='PVR%', row=2, col=1)
        fig.update_yaxes(title_text='RSI', row=3, col=1, range=[0, 100])
        fig.update_yaxes(title_text='MACD', row=4, col=1)
        fig.update_xaxes(title_text='日期', row=4, col=1)

        figs.append(fig)
    return figs


def chart_zone_transitions(df: pd.DataFrame) -> go.Figure:
    """图表7：各估值区间的股票数量变化"""
    zone_order = ['极度低估', '低估', '合理', '合理偏高', '高估']
    zone_colors = {
        '极度低估': '#006837', '低估': '#66bd63',
        '合理': '#ffffbf', '合理偏高': '#fdae61', '高估': '#d73027',
    }
    counts = df.groupby(['日期', '估值区间']).size().unstack(fill_value=0)
    for z in zone_order:
        if z not in counts.columns:
            counts[z] = 0
    counts = counts[zone_order]

    fig = go.Figure()
    for z in zone_order:
        fig.add_trace(go.Scatter(
            x=counts.index, y=counts[z],
            mode='lines', name=z,
            stackgroup='one',
            line=dict(width=0.5, color=zone_colors[z]),
            fillcolor=zone_colors[z],
        ))
    fig.update_layout(
        title='估值区间分布变化 — 每周处于各区间的股票数量',
        yaxis_title='股票数量',
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.15),
    )
    return fig


# ---- 主报告生成 ----

def generate_report(snapshot_path: str = None, kline_json_path: str = None,
                    output_path: str = None):
    """生成完整的可视化诊断报告"""
    if snapshot_path:
        df = pd.read_csv(snapshot_path)
        df['日期'] = pd.to_datetime(df['日期'])
    else:
        df = load_latest_snapshot()

    # 统一处理：确保股票代码为6位字符串（防止 000333 → 333）
    df['股票代码'] = df['股票代码'].astype(str).str.zfill(6)

    # 构建代码→标签映射（用于匹配 kline indicators）
    code_labels = {str(c).zfill(6): _stock_label(c) for c in df['股票代码'].unique()}
    # 替换为可读名称
    df['股票代码'] = df['股票代码'].map(lambda c: _stock_label(c))

    # 加载 kline 完整数据（OHLC + BB + RSI + MACD + PVR，来自 integrated report 同源）
    kline_all = _load_kline_data(kline_json_path, code_labels)

    if output_path is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'reports/visual_diagnosis_{ts}.html'
        # 清理旧报告（保留最新3份）
        old_files = sorted(glob.glob('reports/visual_diagnosis_*.html'))
        for f in old_files[:-3]:
            os.remove(f)

    print("📊 生成图表中...")

    fig1 = chart_portfolio_vs_benchmark(df)
    fig2 = chart_cash_utilization(df)
    fig3 = chart_deviation_heatmap(df)
    fig4 = chart_position_composition(df)
    fig5 = chart_value_ratio_trajectories(df)
    fig6 = chart_zone_transitions(df)
    fig7_list = chart_trading_timeline(df, kline_all)

    # plotly.js 加载策略（CDN仅首次，后续不重复嵌入）
    HTML_NOLIB = dict(full_html=False, include_plotlyjs=False)
    HTML_CDN = dict(full_html=False, include_plotlyjs='cdn')

    # 组合 HTML
    html_parts = ['<html><head><meta charset="utf-8">',
                  '<title>鹿鼎公策略 · 可视化诊断报告</title>',
                  '<style>',
                  'body { font-family: "Helvetica Neue", Arial, sans-serif; ',
                  '       margin: 20px; background: #f8f9fa; color: #212529; }',
                  'h1 { color: #1f77b4; }',
                  'h2 { color: #333; border-bottom: 2px solid #1f77b4; ',
                  '     padding-bottom: 5px; margin-top: 40px; }',
                  '.stats { display: flex; gap: 15px; flex-wrap: wrap; margin: 20px 0; }',
                  '.stat-card { background: white; border-radius: 8px; padding: 15px 25px; ',
                  '             box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 140px; }',
                  '.stat-card .label { font-size: 0.85em; color: #666; }',
                  '.stat-card .value { font-size: 1.6em; font-weight: bold; ',
                  '                   color: #1f77b4; }',
                  '.stat-card .value.positive { color: #28a745; }',
                  '.stat-card .value.warning { color: #dc3545; }',
                  '.chart-container { background: white; border-radius: 8px; ',
                  '                   padding: 15px; margin: 15px 0; ',
                  '                   box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
                  '.grid-2 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }',
                  '@media (max-width: 1100px) { .grid-2 { grid-template-columns: 1fr 1fr; } }',
                  '@media (max-width: 700px) { .grid-2 { grid-template-columns: 1fr; } }',
                  '</style></head><body>']

    # 标题 + 核心指标卡片
    weekly = df.groupby('日期')['总资产'].first()
    total_return = (weekly.iloc[-1] / weekly.iloc[0] - 1) * 100
    start_date = df['日期'].min().strftime('%Y-%m-%d')
    end_date = df['日期'].max().strftime('%Y-%m-%d')
    avg_cash = df.groupby('日期')['总现金'].first().mean()
    avg_total = df.groupby('日期')['总资产'].first().mean()
    avg_cash_pct = avg_cash / avg_total * 100
    n_holdings = df[df['持仓股数'] > 0].groupby('日期')['股票代码'].nunique().mean()

    html_parts.append(f'''
    <h1>🦌 鹿鼎公策略 · 可视化诊断报告</h1>
    <p>回测期间: {start_date} → {end_date}</p>
    <div class="stats">
        <div class="stat-card">
            <div class="label">策略总收益率</div>
            <div class="value positive">{total_return:.1f}%</div>
        </div>
        <div class="stat-card">
            <div class="label">平均现金占比</div>
            <div class="value {"warning" if avg_cash_pct > 30 else "positive"}">{avg_cash_pct:.1f}%</div>
        </div>
        <div class="stat-card">
            <div class="label">平均持仓标的数</div>
            <div class="value">{n_holdings:.1f} 只</div>
        </div>
        <div class="stat-card">
            <div class="label">数据点</div>
            <div class="value">{len(df)}</div>
        </div>
    </div>
    ''')

    # 各图表
    html_parts.append('<h2>1. 策略走势 vs 买入持有基准</h2>')
    html_parts.append('<div class="chart-container">')
    html_parts.append(fig1.to_html(**HTML_CDN))
    html_parts.append('</div>')

    html_parts.append('<h2>2. 资金利用率</h2>')
    html_parts.append('<div class="chart-container">')
    html_parts.append(fig2.to_html(**HTML_NOLIB))
    html_parts.append('</div>')

    html_parts.append('<h2>3. 仓位占有率热力图（深红=满仓 / 白色=半仓 / 深蓝=空仓）</h2>')
    html_parts.append('<div class="chart-container">')
    html_parts.append(fig3.to_html(**HTML_NOLIB))
    html_parts.append('</div>')

    html_parts.append('<h2>4. 仓位构成</h2>')
    html_parts.append('<div class="chart-container">')
    html_parts.append(fig4.to_html(**HTML_NOLIB))
    html_parts.append('</div>')

    html_parts.append('<h2>5. 价值比轨迹</h2>')
    html_parts.append('<div class="chart-container">')
    html_parts.append(fig5.to_html(**HTML_NOLIB))
    html_parts.append('</div>')

    html_parts.append('<h2>6. 估值区间分布</h2>')
    html_parts.append('<div class="chart-container">')
    html_parts.append(fig6.to_html(**HTML_NOLIB))
    html_parts.append('</div>')

    html_parts.append('<h2>7. 周K线图 — 逐只股票（K线+布林带 / PVR / RSI / MACD）</h2>')
    html_parts.append('<div class="grid-2">')
    for fig in fig7_list:
        html_parts.append('<div class="chart-container" style="padding:5px;">')
        html_parts.append(fig.to_html(**HTML_NOLIB))
        html_parts.append('</div>')
    html_parts.append('</div>')

    html_parts.append('</body></html>')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))

    print(f"✅ 可视化报告已生成: {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='生成鹿鼎公策略可视化诊断报告')
    parser.add_argument('-s', '--snapshot', help='快照CSV路径 (默认自动查找最新)')
    parser.add_argument('-k', '--kline', help='K线指标JSON路径 (默认自动查找最新)')
    parser.add_argument('-o', '--output', help='输出HTML路径')
    args = parser.parse_args()
    generate_report(args.snapshot, args.kline, args.output)
