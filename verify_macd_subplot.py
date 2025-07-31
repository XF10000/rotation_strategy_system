#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证MACD子图集成的脚本
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


def check_macd_data_injection(html_content):
    """检查MACD数据注入代码是否存在"""
    logger.info("检查 MACD数据注入:")
    
    # 检查MACD数据准备代码
    macd_data_patterns = [
        r"const macdPoints = stockData\.macd",
        r"const macdSignalPoints = stockData\.macd_signal",
        r"const macdHistogramPoints = stockData\.macd_histogram"
    ]
    
    for pattern in macd_data_patterns:
        if re.search(pattern, html_content):
            logger.info(f"  ✅ {pattern.split('=')[0].strip()} 存在")
        else:
            logger.error(f"  ❌ {pattern.split('=')[0].strip()} 缺失")
            return False
    
    return True


def check_macd_series_config(html_content):
    """检查MACD系列配置是否正确"""
    logger.info("检查 MACD系列配置:")
    
    # 查找MACD系列配置
    if "// MACD子图系列" in html_content and "name: 'MACD'" in html_content and "xAxisIndex: 3" in html_content:
        logger.info("  ✅ MACD系列配置存在")
        # 检查必要的配置项
        checks = [
            ("yAxisIndex: 3", "yAxisIndex配置"),
            ("gridIndex: 3", "gridIndex配置"),
            ("type: 'line'", "图表类型配置"),
            ("symbol: 'none'", "符号配置"),
            ("smooth: true", "平滑配置")
        ]
        
        for check, desc in checks:
            if check in html_content:
                logger.info(f"  ✅ {desc}正确")
            else:
                logger.error(f"  ❌ {desc}缺失")
                return False
    else:
        logger.error("  ❌ MACD系列配置缺失或不完整")
        return False
    
    return True


def check_macd_signal_series_config(html_content):
    """检查MACD信号线系列配置是否正确"""
    logger.info("检查 MACD信号线系列配置:")
    
    # 查找MACD信号线系列配置
    if "name: 'MACD信号线'" in html_content and "xAxisIndex: 3" in html_content:
        logger.info("  ✅ MACD信号线系列配置存在")
        # 检查必要的配置项
        checks = [
            ("yAxisIndex: 3", "yAxisIndex配置"),
            ("gridIndex: 3", "gridIndex配置"),
            ("type: 'line'", "图表类型配置"),
            ("symbol: 'none'", "符号配置"),
            ("smooth: true", "平滑配置")
        ]
        
        for check, desc in checks:
            if check in html_content:
                logger.info(f"  ✅ {desc}正确")
            else:
                logger.error(f"  ❌ {desc}缺失")
                return False
    else:
        logger.error("  ❌ MACD信号线系列配置缺失或不完整")
        return False
    
    return True


def check_macd_histogram_series_config(html_content):
    """检查MACD柱状图系列配置是否正确"""
    logger.info("检查 MACD柱状图系列配置:")
    
    # 查找MACD柱状图系列配置
    if "name: 'MACD柱状图'" in html_content and "xAxisIndex: 3" in html_content:
        logger.info("  ✅ MACD柱状图系列配置存在")
        # 检查必要的配置项
        checks = [
            ("yAxisIndex: 3", "yAxisIndex配置"),
            ("gridIndex: 3", "gridIndex配置"),
            ("type: 'bar'", "图表类型配置")
        ]
        
        for check, desc in checks:
            if check in html_content:
                logger.info(f"  ✅ {desc}正确")
            else:
                logger.error(f"  ❌ {desc}缺失")
                return False
    else:
        logger.error("  ❌ MACD柱状图系列配置缺失或不完整")
        return False
    
    return True


def check_macd_grid_config(html_content):
    """检查MACD网格配置是否正确"""
    logger.info("检查 MACD网格配置:")
    
    # 查找grid配置
    grid_pattern = r"grid:\s*\[[^\]]*\]"
    grid_match = re.search(grid_pattern, html_content, re.DOTALL)
    
    if not grid_match:
        logger.error("  ❌ 网格配置缺失")
        return False
    
    grid_config = grid_match.group(0)
    
    # 检查是否有第四个grid配置（索引3）
    if "gridIndex: 3" in html_content or len(re.findall(r"\{[^}]*left:[^}]*\}", grid_config)) >= 4:
        logger.info("  ✅ MACD网格配置正确")
        return True
    else:
        logger.error("  ❌ MACD网格配置缺失")
        return False


def check_macd_axes_config(html_content):
    """检查MACD坐标轴配置是否正确"""
    logger.info("检查 MACD坐标轴配置:")
    
    # 查找xAxis配置
    xaxis_pattern = r"xAxis:\s*\[[^\]]*\]"
    xaxis_match = re.search(xaxis_pattern, html_content, re.DOTALL)
    
    if not xaxis_match:
        logger.error("  ❌ xAxis配置缺失")
        return False
    
    xaxis_config = xaxis_match.group(0)
    
    # 检查是否有第四个xAxis配置（索引3）
    if "gridIndex: 3" in xaxis_config:
        logger.info("  ✅ MACD xAxis配置正确")
    else:
        logger.error("  ❌ MACD xAxis配置缺失")
        return False
    
    # 查找yAxis配置
    yaxis_pattern = r"yAxis:\s*\[[^\]]*\]"
    yaxis_match = re.search(yaxis_pattern, html_content, re.DOTALL)
    
    if not yaxis_match:
        logger.error("  ❌ yAxis配置缺失")
        return False
    
    yaxis_config = yaxis_match.group(0)
    
    # 检查是否有第四个yAxis配置（索引3）
    if "gridIndex: 3" in yaxis_config:
        logger.info("  ✅ MACD yAxis配置正确")
        return True
    else:
        logger.error("  ❌ MACD yAxis配置缺失")
        return False


def check_legend_config(html_content):
    """检查图例配置是否包含MACD"""
    logger.info("检查 图例配置:")
    
    # 查找legend配置
    legend_pattern = r"legend:\s*\{[^}]*\}"
    legend_match = re.search(legend_pattern, html_content, re.DOTALL)
    
    if not legend_match:
        logger.error("  ❌ 图例配置缺失")
        return False
    
    legend_config = legend_match.group(0)
    
    # 检查是否包含MACD相关图例项
    macd_legend_items = ['MACD', 'MACD信号线', 'MACD柱状图']
    missing_items = []
    
    for item in macd_legend_items:
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
    # 检查最新的backtest_report.html文件
    reports_dir = Path("reports/enhanced_main")
    latest_report = reports_dir / "backtest_report.html"
    
    if not latest_report.exists():
        # 如果最新的报告不存在，查找带时间戳的报告
        html_files = list(reports_dir.glob("backtest_report_*.html"))
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
        check_macd_data_injection,
        check_macd_series_config,
        check_macd_signal_series_config,
        check_macd_histogram_series_config,
        check_macd_grid_config,
        check_macd_axes_config,
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
        logger.info("✅ 所有验证通过，MACD子图集成成功！")
        return True
    else:
        logger.error("❌ 部分验证失败，请检查上述错误信息")
        return False

if __name__ == "__main__":
    main()
