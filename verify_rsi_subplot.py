"""
验证RSI子图是否正确集成到HTML报告中的脚本
"""
import re
import json
import logging
from datetime import datetime
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_js_config(html_content):
    """从HTML中提取ECharts配置"""
    # 查找option配置
    option_match = re.search(r'const option\s*=\s*\{([^}]+)\};', html_content, re.DOTALL)
    if not option_match:
        logger.error("未找到ECharts配置")
        return None
    
    return option_match.group(1)

def verify_rsi_data(html_content):
    """验证RSI数据是否正确注入"""
    # 查找RSI数据注入部分
    rsi_data_match = re.search(r'// 准备RSI数据[\s\S]*?const rsiPoints\s*=\s*stockData\.rsi\s*\|\|\s*\[\];', html_content)
    if rsi_data_match:
        logger.info("✅ RSI数据注入代码存在")
        return True
    else:
        logger.error("❌ 未找到RSI数据注入代码")
        return False

def verify_rsi_series(html_content):
    """验证RSI系列配置是否正确"""
    # 查找RSI系列配置
    rsi_series_match = re.search(r'//\s*RSI子图系列[\s\S]*?name:\s*[\'\"]RSI[\'\"]', html_content)
    if rsi_series_match:
        logger.info("✅ RSI系列配置存在")
        
        # 检查必要的配置项
        series_config = rsi_series_match.group(0)
        checks = [
            ("xAxisIndex: 2", "xAxisIndex配置"),
            ("yAxisIndex: 2", "yAxisIndex配置"),
            ("gridIndex: 2", "gridIndex配置"),
            ("type: 'line'", "图表类型配置"),
            ("symbol: 'none'", "符号配置"),
            ("smooth: true", "平滑配置")
        ]
        
        for check, desc in checks:
            if check in series_config:
                logger.info(f"  ✅ {desc}正确")
            else:
                logger.error(f"  ❌ {desc}缺失")
                return False
        
        return True
    else:
        logger.error("❌ 未找到RSI系列配置")
        return False

def verify_rsi_grid(html_content):
    """验证RSI网格配置是否正确"""
    # 查找grid配置
    grid_match = re.search(r'grid:\s*\[[\s\S]*?\]', html_content)
    if grid_match:
        grid_config = grid_match.group(0)
        # 检查是否有三个grid配置
        grid_configs = re.findall(r'\{[^}]*\}', grid_config)
        if len(grid_configs) >= 3:
            third_grid = grid_configs[2]
            if "top: '80%'" in third_grid and "height: '15%'" in third_grid:
                logger.info("✅ RSI网格配置正确")
                return True
            else:
                logger.error("❌ RSI网格配置不正确")
                return False
        else:
            logger.error("❌ 网格配置数量不足")
            return False
    else:
        logger.error("❌ 未找到网格配置")
        return False

def verify_rsi_axes(html_content):
    """验证RSI坐标轴配置是否正确"""
    # 查找yAxis配置
    yaxis_match = re.search(r'yAxis:\s*\[[\s\S]*?\]', html_content)
    if yaxis_match:
        yaxis_config = yaxis_match.group(0)
        # 检查是否有第三个yAxis配置（RSI）
        yaxis_configs = re.findall(r'\{[^}]*\}', yaxis_config)
        if len(yaxis_configs) >= 3:
            third_yaxis = yaxis_configs[2]
            if "gridIndex: 2" in third_yaxis and "min: 0" in third_yaxis and "max: 100" in third_yaxis:
                logger.info("✅ RSI坐标轴配置正确")
                return True
            else:
                logger.error("❌ RSI坐标轴配置不正确")
                return False
        else:
            logger.error("❌ yAxis配置数量不足")
            return False
    else:
        logger.error("❌ 未找到yAxis配置")
        return False

def verify_legend(html_content):
    """验证图例是否包含RSI"""
    legend_match = re.search(r'legend:\s*\{[^}]*data:\s*\[([^\]]+)\]', html_content)
    if legend_match:
        legend_data = legend_match.group(1)
        if "'RSI'" in legend_data or '"RSI"' in legend_data:
            logger.info("✅ 图例包含RSI")
            return True
        else:
            logger.error("❌ 图例不包含RSI")
            return False
    else:
        logger.error("❌ 未找到图例配置")
        return False

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
    
    # 执行各项验证
    checks = [
        ("RSI数据注入", lambda: verify_rsi_data(html_content)),
        ("RSI系列配置", lambda: verify_rsi_series(html_content)),
        ("RSI网格配置", lambda: verify_rsi_grid(html_content)),
        ("RSI坐标轴配置", lambda: verify_rsi_axes(html_content)),
        ("图例配置", lambda: verify_legend(html_content))
    ]
    
    results = []
    for check_name, check_func in checks:
        logger.info(f"\n检查 {check_name}:")
        result = check_func()
        results.append(result)
    
    # 输出总结
    passed = sum(results)
    total = len(results)
    logger.info(f"\n\n验证结果: {passed}/{total} 项通过")
    
    if passed == total:
        logger.info("🎉 所有验证通过，RSI子图已正确集成！")
        return True
    else:
        logger.error("❌ 部分验证失败，请检查上述错误信息")
        return False

if __name__ == "__main__":
    main()
