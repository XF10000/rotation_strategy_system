#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证完整报告的脚本，检查所有技术指标子图是否正确集成
"""
import json
import re
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_all_data_injection(html_content):
    """检查所有数据注入代码是否存在"""
    logger.info("检查 所有数据注入:")
    
    # 检查所有数据准备代码
    data_patterns = [
        r"const klinePoints = stockData\.kline",
        r"const tradePoints = stockData\.trades",
        r"const bbUpperPoints = stockData\.bb_upper",
        r"const bbLowerPoints = stockData\.bb_lower",
        r"const bbMiddlePoints = stockData\.bb_middle",
        r"const rsiPoints = stockData\.rsi",
        r"const macdPoints = stockData\.macd",
        r"const macdSignalPoints = stockData\.macd_signal",
        r"const macdHistogramPoints = stockData\.macd_histogram"
    ]
    
    all_passed = True
    for pattern in data_patterns:
        if re.search(pattern, html_content):
            logger.info(f"  ✅ {pattern.split('=')[0].strip()} 存在")
        else:
            logger.error(f"  ❌ {pattern.split('=')[0].strip()} 缺失")
            all_passed = False
    
    return all_passed


def check_all_series_config(html_content):
    """检查所有系列配置是否正确"""
    logger.info("检查 所有系列配置:")
    
    # 检查K线系列
    if "name: 'K线'" in html_content and "type: 'candlestick'" in html_content:
        logger.info("  ✅ K线系列配置正确")
    else:
        logger.error("  ❌ K线系列配置缺失")
        return False
    
    # 检查布林带系列
    bb_patterns = ["name: '布林上轨'", "name: '布林中轨'", "name: '布林下轨'"]
    for pattern in bb_patterns:
        if pattern in html_content:
            logger.info(f"  ✅ {pattern} 存在")
        else:
            logger.error(f"  ❌ {pattern} 缺失")
            return False
    
    # 检查RSI系列
    if "name: 'RSI'" in html_content:
        logger.info("  ✅ RSI系列配置正确")
    else:
        logger.error("  ❌ RSI系列配置缺失")
        return False
    
    # 检查MACD系列
    macd_patterns = ["name: 'MACD'", "name: 'MACD信号线'", "name: 'MACD柱状图'"]
    for pattern in macd_patterns:
        if pattern in html_content:
            logger.info(f"  ✅ {pattern} 存在")
        else:
            logger.error(f"  ❌ {pattern} 缺失")
            return False
    
    # 检查交易点系列
    trade_patterns = ["name: '买入点'", "name: '卖出点'"]
    for pattern in trade_patterns:
        if pattern in html_content:
            logger.info(f"  ✅ {pattern} 存在")
        else:
            logger.error(f"  ❌ {pattern} 缺失")
            return False
    
    return True


def check_all_grid_config(html_content):
    """检查所有网格配置是否正确"""
    logger.info("检查 所有网格配置:")
    
    # 查找grid配置
    grid_pattern = r"grid:\s*\[[^\]]*\]"
    grid_match = re.search(grid_pattern, html_content, re.DOTALL)
    
    if not grid_match:
        logger.error("  ❌ 网格配置缺失")
        return False
    
    grid_config = grid_match.group(0)
    
    # 检查是否有4个grid配置
    grid_count = len(re.findall(r"\{[^}]*left:[^}]*\}", grid_config))
    if grid_count >= 4:
        logger.info(f"  ✅ 网格配置正确 ({grid_count} 个子图)")
        return True
    else:
        logger.error(f"  ❌ 网格配置不足 (只有 {grid_count} 个子图)")
        return False


def check_all_axes_config(html_content):
    """检查所有坐标轴配置是否正确"""
    logger.info("检查 所有坐标轴配置:")
    
    # 查找xAxis配置
    xaxis_pattern = r"xAxis:\s*\[[^\]]*\]"
    xaxis_match = re.search(xaxis_pattern, html_content, re.DOTALL)
    
    if not xaxis_match:
        logger.error("  ❌ xAxis配置缺失")
        return False
    
    xaxis_config = xaxis_match.group(0)
    
    # 检查是否有4个xAxis配置
    xaxis_count = len(re.findall(r"type: 'time'", xaxis_config))
    if xaxis_count >= 4:
        logger.info(f"  ✅ xAxis配置正确 ({xaxis_count} 个坐标轴)")
    else:
        logger.error(f"  ❌ xAxis配置不足 (只有 {xaxis_count} 个坐标轴)")
        return False
    
    # 查找yAxis配置
    yaxis_pattern = r"yAxis:\s*\[[^\]]*\]"
    yaxis_match = re.search(yaxis_pattern, html_content, re.DOTALL)
    
    if not yaxis_match:
        logger.error("  ❌ yAxis配置缺失")
        return False
    
    yaxis_config = yaxis_match.group(0)
    
    # 检查是否有4个yAxis配置
    yaxis_count = len(re.findall(r"scale: true", yaxis_config))
    if yaxis_count >= 4:
        logger.info(f"  ✅ yAxis配置正确 ({yaxis_count} 个坐标轴)")
        return True
    else:
        logger.error(f"  ❌ yAxis配置不足 (只有 {yaxis_count} 个坐标轴)")
        return False


def check_legend_config(html_content):
    """检查图例配置是否包含所有指标"""
    logger.info("检查 图例配置:")
    
    # 查找legend配置
    legend_pattern = r"legend:\s*\{[^}]*\}"
    legend_match = re.search(legend_pattern, html_content, re.DOTALL)
    
    if not legend_match:
        logger.error("  ❌ 图例配置缺失")
        return False
    
    legend_config = legend_match.group(0)
    
    # 检查是否包含所有图例项
    all_legend_items = ['K线', '布林上轨', '布林中轨', '布林下轨', 'RSI', 'MACD', 'MACD信号线', 'MACD柱状图', '买入点', '卖出点']
    missing_items = []
    
    for item in all_legend_items:
        if item in legend_config:
            logger.info(f"  ✅ 图例包含{item}")
        else:
            missing_items.append(item)
    
    if missing_items:
        logger.error(f"  ❌ 图例缺少: {', '.join(missing_items)}")
        return False
    
    return True


def main():
    """主验证函数"""
    # 查找最新的HTML报告
    reports_dir = Path("reports")
    html_files = list(reports_dir.glob("integrated_backtest_report_*.html"))
    
    if not html_files:
        logger.error("未找到HTML报告文件")
        return False
    
    # 选择最新的报告
    latest_report = max(html_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"验证报告: {latest_report}")
    
    # 读取HTML内容
    try:
        with open(latest_report, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        logger.error(f"读取HTML文件失败: {e}")
        return False
    
    # 执行各项检查
    checks = [
        check_all_data_injection,
        check_all_series_config,
        check_all_grid_config,
        check_all_axes_config,
        check_legend_config
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check in checks:
        if check(html_content):
            passed_checks += 1
        logger.info("")
    
    logger.info(f"验证结果: {passed_checks}/{total_checks} 项通过")
    
    if passed_checks == total_checks:
        logger.info("✅ 所有验证通过，完整报告集成成功！")
        return True
    else:
        logger.error("❌ 部分验证失败，请检查上述错误信息")
        return False

if __name__ == "__main__":
    main()
