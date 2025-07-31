import json
import os

def check_bb_data():
    # 查找最新的报告文件
    reports_dir = 'reports'
    files = os.listdir(reports_dir)
    html_reports = [f for f in files if f.startswith('integrated_backtest_report') and f.endswith('.html')]
    
    if not html_reports:
        print('未找到HTML报告文件')
        return
    
    # 按时间排序，获取最新的报告
    html_reports.sort(reverse=True)
    latest_report = html_reports[0]
    report_path = os.path.join(reports_dir, latest_report)
    
    print(f'检查报告文件: {latest_report}')
    
    # 读取报告文件
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找K线数据
    start_marker = 'const klineData = '
    end_marker = '};\n'
    
    start_pos = content.find(start_marker)
    if start_pos == -1:
        print('未找到K线数据')
        return
    
    # 提取数据部分
    data_start = start_pos + len(start_marker)
    data_end = content.find(end_marker, data_start) + len(end_marker) - 2  # -2 to remove ;\n
    
    if data_end == -1:
        print('数据结束标记未找到')
        return
    
    data_str = content[data_start:data_end]
    
    try:
        kline_data = json.loads(data_str)
        print(f'成功解析K线数据，包含 {len(kline_data)} 只股票')
        
        # 检查第一只股票的布林带数据
        first_stock = list(kline_data.keys())[0]
        stock_data = kline_data[first_stock]
        
        print(f'\n股票 {first_stock} 数据:')
        print(f'  K线数据点数: {len(stock_data.get("kline", []))}')
        print(f'  布林带上轨点数: {len(stock_data.get("bb_upper", []))}')
        print(f'  布林带中轨点数: {len(stock_data.get("bb_middle", []))}')
        print(f'  布林带下轨点数: {len(stock_data.get("bb_lower", []))}')
        
        # 显示前几个数据点
        if stock_data.get('bb_upper'):
            print(f'\n前5个布林带上轨数据点:')
            for i, point in enumerate(stock_data['bb_upper'][:5]):
                print(f'  {i+1}: {point}')
                
        if stock_data.get('bb_middle'):
            print(f'\n前5个布林带中轨数据点:')
            for i, point in enumerate(stock_data['bb_middle'][:5]):
                print(f'  {i+1}: {point}')
                
        if stock_data.get('bb_lower'):
            print(f'\n前5个布林带下轨数据点:')
            for i, point in enumerate(stock_data['bb_lower'][:5]):
                print(f'  {i+1}: {point}')
                
    except json.JSONDecodeError as e:
        print(f'JSON解析错误: {e}')
        # 显示部分数据用于调试
        print(f'数据片段: {data_str[:200]}')

if __name__ == '__main__':
    check_bb_data()
