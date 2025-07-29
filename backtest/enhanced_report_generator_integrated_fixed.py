import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

class IntegratedReportGenerator:
    """集成HTML模板的回测报告生成器 - 修复版"""
    
    def __init__(self):
        self.template_path = "reports/enhanced_main/backtest_report.html"
        # 确保模板文件存在
        if not os.path.exists(self.template_path):
            print(f"警告: HTML模板文件不存在: {self.template_path}")
            # 创建一个简单的默认模板
            self._create_default_template()
        
    def _create_default_template(self):
        """创建默认HTML模板"""
        os.makedirs(os.path.dirname(self.template_path), exist_ok=True)
        default_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>回测报告</title>
</head>
<body>
    <h1>回测报告</h1>
    <p>初始资金: ¥1,000,000</p>
    <p>最终资金: ¥1,000,000</p>
    <p>总收益率: 0.00%</p>
    <p>生成时间: 2025-01-01 00:00:00</p>
</body>
</html>
"""
        with open(self.template_path, 'w', encoding='utf-8') as f:
            f.write(default_template)
        
    def generate_report(self, backtest_results: Dict[str, Any], 
                       output_path: str = None) -> str:
        """
        生成集成的HTML回测报告
        
        Args:
            backtest_results: 回测结果数据
            output_path: 输出路径，如果为None则自动生成
            
        Returns:
            生成的报告文件路径
        """
        try:
            # 读取HTML模板
            with open(self.template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
            
            # 提取数据
            portfolio_history = backtest_results.get('portfolio_history', [])
            transactions = backtest_results.get('transactions', [])
            final_portfolio = backtest_results.get('final_portfolio', {})
            performance_metrics = backtest_results.get('performance_metrics', {})
            signal_analysis = backtest_results.get('signal_analysis', {})
            kline_data = backtest_results.get('kline_data', {})
            
            # 生成报告内容
            html_content = self._fill_template_safe(
                html_template,
                portfolio_history,
                transactions,
                final_portfolio,
                performance_metrics,
                signal_analysis,
                kline_data
            )
            
            # 确定输出路径
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"reports/integrated_backtest_report_{timestamp}.html"
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ 集成报告已生成: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 生成报告时出错: {str(e)}")
            # 生成一个简单的错误报告
            return self._generate_error_report(str(e), output_path)
    
    def _generate_error_report(self, error_msg: str, output_path: str = None) -> str:
        """生成错误报告"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"reports/error_report_{timestamp}.html"
        
        error_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>报告生成错误</title>
</head>
<body>
    <h1>报告生成错误</h1>
    <p>错误信息: {error_msg}</p>
    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>
"""
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(error_html)
            return output_path
        except:
            return ""
    
    def _fill_template_safe(self, template: str, portfolio_history: List,
                           transactions: List, final_portfolio: Dict,
                           performance_metrics: Dict, signal_analysis: Dict,
                           kline_data: Dict) -> str:
        """安全地填充HTML模板数据"""
        
        try:
            # 1. 基础指标替换
            template = self._replace_basic_metrics_safe(template, performance_metrics)
            
            # 2. 基准对比替换
            template = self._replace_benchmark_comparison_safe(template, performance_metrics)
            
            # 3. 最终持仓状态替换
            template = self._replace_final_portfolio_safe(template, final_portfolio)
            
            # 4. 交易统计替换
            template = self._replace_trading_stats_safe(template, transactions)
            
            # 5. 详细交易记录替换
            template = self._replace_transaction_details_safe(template, transactions, signal_analysis)
            
            # 6. 信号统计分析替换
            template = self._replace_signal_stats_safe(template, signal_analysis)
            
            # 7. K线数据替换
            template = self._replace_kline_data_safe(template, kline_data)
            
            # 8. 生成时间替换
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            template = template.replace("2025-07-26 17:54:46", current_time)
            
            return template
            
        except Exception as e:
            print(f"模板填充错误: {e}")
            return template
    
    def _replace_basic_metrics_safe(self, template: str, metrics: Dict) -> str:
        """安全地替换基础指标"""
        try:
            initial_capital = metrics.get('initial_capital', 1000000)
            final_value = metrics.get('final_value', initial_capital)
            total_return = metrics.get('total_return', 0)
            annual_return = metrics.get('annual_return', 0)
            max_drawdown = metrics.get('max_drawdown', 0)
            
            # 安全替换
            replacements = [
                ('¥1,000,000', f'¥{initial_capital:,.0f}'),
                ('¥1,680,939', f'¥{final_value:,.0f}'),
                ('68.09%', f'{total_return:.2f}%'),
                ('18.47%', f'{annual_return:.2f}%'),
                ('-21.56%', f'{max_drawdown:.2f}%')
            ]
            
            for old, new in replacements:
                template = template.replace(old, new)
            
            return template
        except Exception as e:
            print(f"基础指标替换错误: {e}")
            return template
    
    def _replace_benchmark_comparison_safe(self, template: str, metrics: Dict) -> str:
        """安全地替换基准对比数据"""
        try:
            # 获取真实的回测数据
            strategy_return = metrics.get('total_return', 0)
            strategy_annual = metrics.get('annual_return', 0)
            strategy_max_drawdown = metrics.get('max_drawdown', 0)
            strategy_final_value = metrics.get('final_value', 1000000)
            
            # 获取真实的基准数据
            benchmark_return = metrics.get('benchmark_return', 45.0)
            benchmark_annual = metrics.get('benchmark_annual_return', 12.0)
            benchmark_max_drawdown = metrics.get('benchmark_max_drawdown', -18.0)
            
            # 计算基准最终资金（基于初始资金和基准收益率）
            initial_capital = metrics.get('initial_capital', 1000000)
            benchmark_final_value = initial_capital * (1 + benchmark_return / 100)
            
            # 计算超额收益
            excess_return = strategy_return - benchmark_return
            excess_annual = strategy_annual - benchmark_annual
            excess_final_value = strategy_final_value - benchmark_final_value
            
            print(f"🔍 基准对比数据:")
            print(f"  策略收益率: {strategy_return:.2f}% vs 基准收益率: {benchmark_return:.2f}%")
            print(f"  策略年化: {strategy_annual:.2f}% vs 基准年化: {benchmark_annual:.2f}%")
            print(f"  策略最终资金: ¥{strategy_final_value:,.0f} vs 基准最终资金: ¥{benchmark_final_value:,.0f}")
            print(f"  超额收益: {excess_return:.2f}%")
            
            # 判断是跑赢还是跑输基准
            comparison_result = "跑赢基准" if excess_return > 0 else "跑输基准"
            comparison_class = "outperform" if excess_return > 0 else "underperform"
            
            # 替换对比结果摘要
            template = template.replace("对比结果: 跑赢基准", f"对比结果: {comparison_result}")
            template = template.replace('class="comparison-summary outperform"', f'class="comparison-summary {comparison_class}"')
            template = template.replace("策略相对买入持有基准超额收益: <strong>23.09%</strong>", 
                                      f"策略相对买入持有基准超额收益: <strong>{excess_return:.2f}%</strong>")
            template = template.replace("年化超额收益: <strong>6.47%</strong>", 
                                      f"年化超额收益: <strong>{excess_annual:.2f}%</strong>")
            
            # 替换基准对比表格中的数据
            table_replacements = [
                # 总收益率行
                ('67.71%', f'{strategy_return:.2f}%'),
                ('45.00%', f'{benchmark_return:.2f}%'),
                ('+23.09%', f'{excess_return:+.2f}%'),
                
                # 年化收益率行  
                ('15.70%', f'{strategy_annual:.2f}%'),
                ('12.00%', f'{benchmark_annual:.2f}%'),
                ('+6.47%', f'{excess_annual:+.2f}%'),
                
                # 最大回撤行
                ('-13.83%', f'{strategy_max_drawdown:.2f}%'),
                ('-18.00%', f'{benchmark_max_drawdown:.2f}%'),
                
                # 最终资金行
                ('¥1,673,393', f'¥{strategy_final_value:,.0f}'),
                ('¥1,450,000', f'¥{benchmark_final_value:,.0f}'),
                ('¥+230,939', f'¥{excess_final_value:+,.0f}'),
            ]
            
            for old_value, new_value in table_replacements:
                template = template.replace(old_value, new_value)
            
            return template
        except Exception as e:
            print(f"❌ 基准对比替换错误: {e}")
            return template
    
    def _replace_final_portfolio_safe(self, template: str, final_portfolio: Dict) -> str:
        """安全地替换最终持仓状态"""
        try:
            total_value = final_portfolio.get('total_value', 1000000)
            cash = final_portfolio.get('cash', 100000)
            stock_value = final_portfolio.get('stock_value', 900000)
            end_date = final_portfolio.get('end_date', '2025-07-25')
            positions = final_portfolio.get('positions', {})
            
            # 计算现金和股票占比
            cash_ratio = (cash / total_value * 100) if total_value > 0 else 0
            stock_ratio = (stock_value / total_value * 100) if total_value > 0 else 0
            
            print(f"🔍 最终持仓状态数据:")
            print(f"  结束日期: {end_date}")
            print(f"  总资产: ¥{total_value:,.2f}")
            print(f"  现金: ¥{cash:,.2f} ({cash_ratio:.1f}%)")
            print(f"  股票市值: ¥{stock_value:,.2f} ({stock_ratio:.1f}%)")
            print(f"  持仓明细: {positions}")
            
            # 替换基本信息
            replacements = [
                # 结束日期
                ('<span class="summary-value">2025-07-25</span>', f'<span class="summary-value">{end_date}</span>'),
                
                # 总资产
                ('¥2,029,250.36', f'¥{total_value:,.2f}'),
                
                # 现金
                ('¥125,391.80 (7.5%)', f'¥{cash:,.2f} ({cash_ratio:.1f}%)'),
                
                # 股票市值
                ('¥1,555,547.00 (92.5%)', f'¥{stock_value:,.2f} ({stock_ratio:.1f}%)')
            ]
            
            for old_value, new_value in replacements:
                template = template.replace(old_value, new_value)
            
            # 替换持仓明细表格 - 这个表格应该显示持仓明细，不是策略对比
            if positions:
                template = self._replace_position_details_table(template, positions, total_value)
            
            return template
        except Exception as e:
            print(f"❌ 持仓状态替换错误: {e}")
            return template
    
    def _replace_position_details_table(self, template: str, positions: Dict, total_value: float) -> str:
        """替换持仓明细表格 - 确保使用正确的表格"""
        try:
            # 生成持仓明细行
            position_rows = []
            for stock_code, shares in positions.items():
                if isinstance(shares, dict):
                    # 如果是字典格式，提取shares和current_price
                    actual_shares = shares.get('shares', 0)
                    current_price = shares.get('current_price', 0)
                else:
                    # 如果是简单数值格式，需要获取当前价格
                    actual_shares = shares
                    current_price = self._get_current_price(stock_code)
                
                if actual_shares > 0:
                    market_value = actual_shares * current_price
                    ratio = (market_value / total_value * 100) if total_value > 0 else 0
                    
                    row = f"""
                                <tr>
                                    <td>{stock_code}</td>
                                    <td>{actual_shares:,} 股</td>
                                    <td>¥{current_price:.2f}</td>
                                    <td>¥{market_value:,.2f}</td>
                                    <td>{ratio:.1f}%</td>
                                </tr>"""
                    position_rows.append(row)
            
            # 查找持仓明细表格的tbody（不是策略对比表格）
            # 寻找包含"股票代码"表头的表格
            stock_table_start = template.find('<th>股票代码</th>')
            if stock_table_start != -1:
                # 从表头开始向后找tbody
                tbody_start = template.find('<tbody>', stock_table_start)
                if tbody_start != -1:
                    tbody_end = template.find('</tbody>', tbody_start)
                    if tbody_end != -1:
                        new_tbody = '<tbody>\n' + '\n'.join(position_rows) + '\n                        </tbody>'
                        template = template[:tbody_start] + new_tbody + template[tbody_end + 8:]
                        print(f"✅ 持仓明细表格已更新，包含 {len(position_rows)} 个持仓")
                    else:
                        print("⚠️ 未找到持仓明细表格结束标签")
                else:
                    print("⚠️ 未找到持仓明细表格tbody标签")
            else:
                print("⚠️ 未找到持仓明细表格（股票代码表头）")
            
            return template
        except Exception as e:
            print(f"❌ 持仓明细表格替换错误: {e}")
            return template
    
    def _get_current_price(self, stock_code: str) -> float:
        """获取股票当前价格的辅助方法"""
        try:
            # 这里应该从数据源获取当前价格，暂时返回默认值
            price_map = {
                '601088': 38.43,  # 中国神华
                '600985': 13.27,  # 淮北矿业
                '002738': 39.01,  # 中矿资源
                '002916': 131.98, # 深南电路
                '600900': 28.75   # 长江电力
            }
            return price_map.get(stock_code, 10.0)
        except:
            return 10.0
    
    def _replace_trading_stats_safe(self, template: str, transactions: List) -> str:
        """安全地替换交易统计"""
        try:
            total_trades = len(transactions) if transactions else 0
            buy_count = sum(1 for t in transactions if t.get('type') == 'BUY') if transactions else 0
            sell_count = sum(1 for t in transactions if t.get('type') == 'SELL') if transactions else 0
            total_fees = sum(t.get('transaction_cost', t.get('fee', 0)) for t in transactions) if transactions else 0
            
            print(f"🔍 交易统计数据: 总交易={total_trades}, 买入={buy_count}, 卖出={sell_count}, 手续费={total_fees}")
            
            # 直接替换HTML模板中的固定数值
            template = template.replace('<div class="value">7</div>', f'<div class="value">{total_trades}</div>')
            template = template.replace('<div class="value">4</div>', f'<div class="value">{buy_count}</div>')
            template = template.replace('<div class="value">3</div>', f'<div class="value">{sell_count}</div>')
            template = template.replace('<div class="value">¥748.20</div>', f'<div class="value">¥{total_fees:.2f}</div>')
            
            # 计算手续费率
            if total_trades > 0:
                fee_rate = (total_fees / 1000000) * 100  # 相对于初始资金的百分比
                template = template.replace('<div class="value">0.0748%</div>', f'<div class="value">{fee_rate:.4f}%</div>')
            
            return template
        except Exception as e:
            print(f"❌ 交易统计替换错误: {e}")
            return template
    
    def _replace_transaction_details_safe(self, template: str, transactions: List, signal_analysis: Dict) -> str:
        """安全地替换详细交易记录"""
        try:
            if not transactions:
                return template
            
            # 生成真实的交易记录
            transaction_rows = []
            for transaction in transactions:
                date = transaction.get('date', '')
                trade_type = transaction.get('type', '')
                stock_code = transaction.get('stock_code', '')
                price = transaction.get('price', 0)
                shares = transaction.get('shares', 0)
                
                # 获取真实的技术指标数据
                technical_indicators = transaction.get('technical_indicators', {})
                signal_details = transaction.get('signal_details', {})
                dimension_status = signal_details.get('dimension_status', {})
                
                # 提取技术指标
                close_price = technical_indicators.get('close', price)
                ema_20w = technical_indicators.get('ema_20w', 0)
                rsi_14w = technical_indicators.get('rsi_14w', 50)
                macd_dif = technical_indicators.get('macd_dif', 0)
                macd_dea = technical_indicators.get('macd_dea', 0)
                bb_upper = technical_indicators.get('bb_upper', 0)
                bb_middle = technical_indicators.get('bb_middle', 0)
                bb_lower = technical_indicators.get('bb_lower', 0)
                volume = technical_indicators.get('volume', 0)
                volume_4w_avg = technical_indicators.get('volume_4w_avg', 1)
                
                # 计算量能倍数
                volume_ratio = volume / volume_4w_avg if volume_4w_avg > 0 else 0
                
                # 判断布林带位置
                if close_price >= bb_upper:
                    bb_position = "上轨之上"
                elif close_price <= bb_lower:
                    bb_position = "下轨之下"
                else:
                    bb_position = "轨道之间"
                
                # 获取信号状态
                trend_filter = dimension_status.get('trend_filter', '✗')
                rsi_signal = dimension_status.get('rsi_signal', '✗')
                macd_signal = dimension_status.get('macd_signal', '✗')
                bollinger_volume = dimension_status.get('bollinger_volume', '✗')
                
                # 计算满足的维度数
                satisfied_count = sum(1 for status in [trend_filter, rsi_signal, macd_signal, bollinger_volume] if status == '✓')
                confidence = signal_details.get('confidence', 0)
                reason = signal_details.get('reason', f'{trade_type}信号')
                
                row_class = 'buy-row' if trade_type == 'BUY' else 'sell-row'
                type_color = '#28a745' if trade_type == 'BUY' else '#dc3545'
                
                row = f"""
        <tr class='{row_class}'>
            <td>{date}</td>
            <td style="font-weight: bold; color: {type_color}">{trade_type}</td>
            <td><strong>{stock_code}</strong></td>
            <td>{price:.2f}</td>
            <td>{shares:,}</td>
            <td>{close_price:.2f}</td>
            <td>{ema_20w:.2f}</td>
            <td class="signal-check">{trend_filter}</td>
            <td>{rsi_14w:.2f}</td>
            <td class="signal-check">{rsi_signal}</td>
            <td>{macd_dif:.4f}</td>
            <td>{macd_dea:.2f}</td>
            <td class="signal-check">{macd_signal}</td>
            <td class="bb-position">{bb_position}</td>
            <td>{volume_ratio:.2f}x</td>
            <td class="signal-check">{bollinger_volume}</td>
            <td style="font-size: 10px; text-align: left; max-width: 150px;">{satisfied_count}/4<br>{reason}</td>
        </tr>"""
                transaction_rows.append(row)
            
            # 查找并替换交易记录表格
            tbody_start = template.find('<tbody>', template.find('transaction-table'))
            tbody_end = template.find('</tbody>', tbody_start)
            
            if tbody_start != -1 and tbody_end != -1:
                new_tbody = '<tbody>\n' + '\n'.join(transaction_rows) + '\n</tbody>'
                template = template[:tbody_start] + new_tbody + template[tbody_end + 8:]
            
            return template
        except Exception as e:
            print(f"交易记录替换错误: {e}")
            return template
    
    def _replace_signal_stats_safe(self, template: str, signal_analysis: Dict) -> str:
        """安全地替换信号统计分析"""
        try:
            if not signal_analysis:
                return template
            
            # 获取所有股票代码并去重排序
            stock_codes = sorted(list(set(signal_analysis.keys())))
            
            # 计算全局统计数据
            total_all_signals = 0
            total_buy_signals = 0
            total_sell_signals = 0
            dimension_stats = {'rsi': 0, 'macd': 0, 'bollinger': 0, 'ema': 0}
            
            # 生成股票卡片和统计数据
            signal_cards = []
            for stock_code in stock_codes:
                stock_signals = signal_analysis.get(stock_code, {})
                signals = stock_signals.get('signals', [])
                
                # 基础统计
                total_signals = len(signals)
                buy_signals = sum(1 for s in signals if s.get('type') == 'BUY')
                sell_signals = sum(1 for s in signals if s.get('type') == 'SELL')
                
                # 维度统计
                rsi_signals = sum(1 for s in signals if s.get('rsi_signal') == '✓')
                macd_signals = sum(1 for s in signals if s.get('macd_signal') == '✓')
                bb_signals = sum(1 for s in signals if s.get('bollinger_volume') == '✓')
                ema_signals = sum(1 for s in signals if s.get('trend_filter') == '✓')
                
                # 计算成功率
                rsi_rate = f"{(rsi_signals/total_signals*100):.1f}%" if total_signals > 0 else "0%"
                macd_rate = f"{(macd_signals/total_signals*100):.1f}%" if total_signals > 0 else "0%"
                bb_rate = f"{(bb_signals/total_signals*100):.1f}%" if total_signals > 0 else "0%"
                ema_rate = f"{(ema_signals/total_signals*100):.1f}%" if total_signals > 0 else "0%"
                
                # 累计全局统计
                total_all_signals += total_signals
                total_buy_signals += buy_signals
                total_sell_signals += sell_signals
                dimension_stats['rsi'] += rsi_signals
                dimension_stats['macd'] += macd_signals
                dimension_stats['bollinger'] += bb_signals
                dimension_stats['ema'] += ema_signals
                
                # 生成股票卡片
                card_html = f"""
                <div class="signal-card">
                    <div class="card-header">
                        <h4>{stock_code}</h4>
                        <div class="total-badge">{total_signals}个信号</div>
                    </div>
                    <div class="signal-summary">
                        <div class="summary-item buy">
                            <span class="summary-label">买入</span>
                            <span class="summary-value">{buy_signals}</span>
                        </div>
                        <div class="summary-item sell">
                            <span class="summary-label">卖出</span>
                            <span class="summary-value">{sell_signals}</span>
                        </div>
                    </div>
                    <div class="dimension-stats">
                        <div class="dimension-item">
                            <span class="dim-label">📈 趋势过滤</span>
                            <div class="dim-progress">
                                <div class="progress-bar" style="width: {(ema_signals/total_signals*100) if total_signals > 0 else 0}%"></div>
                                <span class="progress-text">{ema_signals}/{total_signals} ({ema_rate})</span>
                            </div>
                        </div>
                        <div class="dimension-item">
                            <span class="dim-label">📊 RSI信号</span>
                            <div class="dim-progress">
                                <div class="progress-bar" style="width: {(rsi_signals/total_signals*100) if total_signals > 0 else 0}%"></div>
                                <span class="progress-text">{rsi_signals}/{total_signals} ({rsi_rate})</span>
                            </div>
                        </div>
                        <div class="dimension-item">
                            <span class="dim-label">⚡ MACD信号</span>
                            <div class="dim-progress">
                                <div class="progress-bar" style="width: {(macd_signals/total_signals*100) if total_signals > 0 else 0}%"></div>
                                <span class="progress-text">{macd_signals}/{total_signals} ({macd_rate})</span>
                            </div>
                        </div>
                        <div class="dimension-item">
                            <span class="dim-label">🔔 布林带+量能</span>
                            <div class="dim-progress">
                                <div class="progress-bar" style="width: {(bb_signals/total_signals*100) if total_signals > 0 else 0}%"></div>
                                <span class="progress-text">{bb_signals}/{total_signals} ({bb_rate})</span>
                            </div>
                        </div>
                    </div>
                </div>"""
                signal_cards.append(card_html)
            
            # 生成全局统计摘要
            global_summary = f"""
            <div class="global-summary">
                <h3>📊 全局信号统计摘要</h3>
                <div class="summary-grid">
                    <div class="summary-card total">
                        <div class="summary-number">{total_all_signals}</div>
                        <div class="summary-title">总信号数</div>
                    </div>
                    <div class="summary-card buy">
                        <div class="summary-number">{total_buy_signals}</div>
                        <div class="summary-title">买入信号</div>
                    </div>
                    <div class="summary-card sell">
                        <div class="summary-number">{total_sell_signals}</div>
                        <div class="summary-title">卖出信号</div>
                    </div>
                    <div class="summary-card ratio">
                        <div class="summary-number">{(total_buy_signals/total_sell_signals):.1f}:1</div>
                        <div class="summary-title">买卖比例</div>
                    </div>
                </div>
                <div class="dimension-summary">
                    <div class="dim-summary-item">
                        <span class="dim-name">📈 趋势过滤器</span>
                        <span class="dim-count">{dimension_stats['ema']}/{total_all_signals}</span>
                        <span class="dim-rate">({(dimension_stats['ema']/total_all_signals*100):.1f}%)</span>
                    </div>
                    <div class="dim-summary-item">
                        <span class="dim-name">📊 RSI超买超卖</span>
                        <span class="dim-count">{dimension_stats['rsi']}/{total_all_signals}</span>
                        <span class="dim-rate">({(dimension_stats['rsi']/total_all_signals*100):.1f}%)</span>
                    </div>
                    <div class="dim-summary-item">
                        <span class="dim-name">⚡ MACD动能</span>
                        <span class="dim-count">{dimension_stats['macd']}/{total_all_signals}</span>
                        <span class="dim-rate">({(dimension_stats['macd']/total_all_signals*100):.1f}%)</span>
                    </div>
                    <div class="dim-summary-item">
                        <span class="dim-name">🔔 布林带+量能</span>
                        <span class="dim-count">{dimension_stats['bollinger']}/{total_all_signals}</span>
                        <span class="dim-rate">({(dimension_stats['bollinger']/total_all_signals*100):.1f}%)</span>
                    </div>
                </div>
            </div>"""
            
            # 创建完整的HTML内容
            cards_html = f"""
            {global_summary}
            <div class="signal-stats-grid">
                {''.join(signal_cards)}
            </div>
            
            <style>
            /* 全局摘要样式 */
            .global-summary {{
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                border-radius: 15px;
                padding: 25px;
                margin: 20px 0;
                color: white;
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            }}
            
            .global-summary h3 {{
                margin: 0 0 20px 0;
                text-align: center;
                font-size: 22px;
                font-weight: bold;
            }}
            
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-bottom: 25px;
            }}
            
            .summary-card {{
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                border: 2px solid transparent;
                transition: all 0.3s ease;
            }}
            
            .summary-card.total {{ border-color: #3498db; }}
            .summary-card.buy {{ border-color: #27ae60; }}
            .summary-card.sell {{ border-color: #e74c3c; }}
            .summary-card.ratio {{ border-color: #f39c12; }}
            
            .summary-number {{
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 8px;
            }}
            
            .summary-title {{
                font-size: 14px;
                opacity: 0.9;
            }}
            
            .dimension-summary {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }}
            
            .dim-summary-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: rgba(255,255,255,0.05);
                padding: 12px 15px;
                border-radius: 8px;
                border-left: 4px solid #3498db;
            }}
            
            .dim-name {{
                font-weight: bold;
                flex: 1;
            }}
            
            .dim-count {{
                font-weight: bold;
                margin-right: 10px;
            }}
            
            .dim-rate {{
                opacity: 0.8;
                font-size: 12px;
            }}
            
            /* 股票卡片样式 */
            .signal-stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            
            .signal-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                padding: 0;
                color: white;
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                overflow: hidden;
                transition: transform 0.3s ease;
            }}
            
            .signal-card:hover {{
                transform: translateY(-5px);
            }}
            
            .card-header {{
                background: rgba(0,0,0,0.2);
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }}
            
            .card-header h4 {{
                margin: 0;
                font-size: 20px;
                font-weight: bold;
            }}
            
            .total-badge {{
                background: rgba(255,255,255,0.3);
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            
            .signal-summary {{
                display: flex;
                padding: 15px 20px;
                gap: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }}
            
            .summary-item {{
                flex: 1;
                text-align: center;
                padding: 10px;
                border-radius: 8px;
            }}
            
            .summary-item.buy {{
                background: rgba(39, 174, 96, 0.3);
            }}
            
            .summary-item.sell {{
                background: rgba(231, 76, 60, 0.3);
            }}
            
            .summary-label {{
                display: block;
                font-size: 12px;
                opacity: 0.8;
                margin-bottom: 5px;
            }}
            
            .summary-value {{
                display: block;
                font-size: 24px;
                font-weight: bold;
            }}
            
            .dimension-stats {{
                padding: 20px;
            }}
            
            .dimension-item {{
                margin-bottom: 15px;
            }}
            
            .dimension-item:last-child {{
                margin-bottom: 0;
            }}
            
            .dim-label {{
                display: block;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 8px;
            }}
            
            .dim-progress {{
                position: relative;
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
                height: 25px;
                overflow: hidden;
            }}
            
            .progress-bar {{
                height: 100%;
                background: linear-gradient(90deg, #27ae60, #2ecc71);
                border-radius: 10px;
                transition: width 0.5s ease;
            }}
            
            .progress-text {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 12px;
                font-weight: bold;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            }}
            </style>"""
            
            # 查找并替换信号统计区域 - 更精确的替换逻辑
            stats_start = template.find("📊 信号统计分析")
            if stats_start != -1:
                # 找到包含信号统计分析的div开始位置
                section_start = template.rfind('<div class="analysis-section">', 0, stats_start)
                if section_start == -1:
                    # 如果没找到analysis-section，查找更通用的div
                    section_start = template.rfind('<div', 0, stats_start)
                
                if section_start != -1:
                    # 找到对应的结束标签 - 需要正确匹配div层级
                    div_count = 1
                    search_pos = section_start + 4  # 跳过开始的<div
                    
                    while div_count > 0 and search_pos < len(template):
                        next_div_start = template.find('<div', search_pos)
                        next_div_end = template.find('</div>', search_pos)
                        
                        if next_div_end == -1:
                            break
                        
                        if next_div_start != -1 and next_div_start < next_div_end:
                            div_count += 1
                            search_pos = next_div_start + 4
                        else:
                            div_count -= 1
                            search_pos = next_div_end + 6
                    
                    section_end = search_pos
                    
                    # 额外清理：查找并删除任何残留的旧格式信号卡片
                    remaining_template = template[section_end:]
                    
                    # 查找是否还有旧格式的信号卡片
                    old_card_pattern_start = remaining_template.find("<div class='signal-card'>")
                    if old_card_pattern_start != -1:
                        # 找到所有旧格式卡片的结束位置
                        old_cards_start = section_end + old_card_pattern_start
                        
                        # 查找最后一个旧格式卡片的结束位置
                        temp_pos = old_cards_start
                        last_card_end = old_cards_start
                        
                        while True:
                            card_start = template.find("<div class='signal-card'>", temp_pos)
                            if card_start == -1:
                                break
                            card_end = template.find("</div>", card_start)
                            if card_end == -1:
                                break
                            last_card_end = card_end + 6
                            temp_pos = last_card_end
                        
                        # 删除所有旧格式的信号卡片
                        template = template[:old_cards_start] + template[last_card_end:]
                        section_end = old_cards_start
                    
                    # 插入新的信号统计分析
                    new_section = f"""
            <div class="analysis-section">
                <h2>📊 信号统计分析</h2>
                {cards_html}
            </div>"""
                    template = template[:section_start] + new_section + template[section_end:]
                    print(f"✅ 信号统计分析已更新，包含 {len(signal_cards)} 个股票，已清理重复内容")
            
            # 最后再次检查并清理任何残留的旧格式信号统计
            # 删除任何残留的 <h4>股票代码 信号统计</h4> 格式
            import re
            old_signal_pattern = r'<h4>\d{6}\s+信号统计</h4>'
            template = re.sub(old_signal_pattern, '', template, flags=re.DOTALL)
            
            # 删除任何残留的旧格式signal-card（更精确的匹配）
            old_card_pattern = r"<div class='signal-card'>.*?</div>\s*(?=\s*<div|\s*</div>|\s*$)"
            template = re.sub(old_card_pattern, '', template, flags=re.DOTALL)
            
            # 删除多余的空行和空白div
            template = re.sub(r'\n\s*\n\s*\n', '\n\n', template)
            template = re.sub(r'<div>\s*</div>', '', template)
            
            return template
        except Exception as e:
            print(f"❌ 信号统计替换错误: {e}")
            return template
    
    def _replace_kline_data_safe(self, template: str, kline_data: Dict) -> str:
        """安全地替换K线数据"""
        try:
            print(f"🔍 K线数据检查: {list(kline_data.keys()) if kline_data else '无数据'}")
            
            if not kline_data:
                print("⚠️ 警告: K线数据为空，将使用空对象")
                kline_data = {}
            
            # 打印每个股票的数据情况
            for stock_code, stock_data in kline_data.items():
                kline_count = len(stock_data.get('kline', []))
                trade_count = len(stock_data.get('trades', []))
                print(f"📊 {stock_code}: K线数据{kline_count}条, 交易点{trade_count}个")
            
            # 将K线数据转换为JavaScript格式
            js_kline_data = json.dumps(kline_data, ensure_ascii=False, indent=2)
            
            # 查找并替换K线数据
            data_start = template.find('const klineData = {};')
            if data_start != -1:
                data_end = template.find(';', data_start) + 1
                new_js_data = f'const klineData = {js_kline_data};'
                template = template[:data_start] + new_js_data + template[data_end:]
                print("✅ K线数据已成功替换到模板中")
            else:
                print("❌ 未找到K线数据占位符")
            
            return template
        except Exception as e:
            print(f"❌ K线数据替换错误: {e}")
            return template

def create_integrated_report(backtest_results: Dict[str, Any], output_path: str = None) -> str:
    """
    便捷函数：创建集成的回测报告
    
    Args:
        backtest_results: 回测结果数据
        output_path: 输出路径
        
    Returns:
        生成的报告文件路径
    """
    generator = IntegratedReportGenerator()
    return generator.generate_report(backtest_results, output_path)