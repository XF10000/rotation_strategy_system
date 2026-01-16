"""
绩效分析器
计算各种回测绩效指标和风险指标
"""

import logging
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    绩效分析器
    
    功能：
    1. 计算收益率指标
    2. 计算风险指标
    3. 计算交易指标
    4. 基准对比分析
    """
    
    def __init__(self):
        """初始化绩效分析器"""
        logger.info("绩效分析器初始化完成")
    
    def calculate_returns(self, portfolio_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算收益率指标
        
        Args:
            portfolio_df: 投资组合历史数据
            
        Returns:
            收益率指标字典
        """
        if portfolio_df.empty:
            return {}
        
        # 确保数据按日期排序
        if 'date' in portfolio_df.columns:
            portfolio_df = portfolio_df.sort_values('date')
            start_date = portfolio_df['date'].iloc[0]
            end_date = portfolio_df['date'].iloc[-1]
        else:
            # 如果date是索引
            portfolio_df = portfolio_df.sort_index()
            start_date = portfolio_df.index[0]
            end_date = portfolio_df.index[-1]
        
        initial_value = portfolio_df['total_value'].iloc[0]
        final_value = portfolio_df['total_value'].iloc[-1]
        
        # 总收益率
        total_return = (final_value - initial_value) / initial_value
        
        # 计算时间跨度
        days = (end_date - start_date).days
        years = days / 365.25
        
        # 年化收益率
        annual_return = (final_value / initial_value) ** (1/years) - 1 if years > 0 else 0
        
        # 计算周收益率序列
        portfolio_df['prev_value'] = portfolio_df['total_value'].shift(1)
        portfolio_df['weekly_return'] = (portfolio_df['total_value'] - portfolio_df['prev_value']) / portfolio_df['prev_value']
        weekly_returns = portfolio_df['weekly_return'].dropna()
        
        # 平均周收益率
        avg_weekly_return = weekly_returns.mean()
        
        # 收益率波动率（年化）
        weekly_volatility = weekly_returns.std()
        annual_volatility = weekly_volatility * np.sqrt(52) if not np.isnan(weekly_volatility) else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'avg_weekly_return': avg_weekly_return,
            'annual_volatility': annual_volatility,
            'days': days,
            'years': years
        }
    
    def calculate_risk_metrics(self, portfolio_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算风险指标
        
        Args:
            portfolio_df: 投资组合历史数据
            
        Returns:
            风险指标字典
        """
        if portfolio_df.empty:
            return {}
        
        # 确保数据按日期排序
        if 'date' in portfolio_df.columns:
            portfolio_df = portfolio_df.sort_values('date')
        else:
            # 如果date是索引
            portfolio_df = portfolio_df.sort_index()
        
        initial_value = portfolio_df['total_value'].iloc[0]
        
        # 计算累积收益率
        portfolio_df['cumulative_return'] = portfolio_df['total_value'] / initial_value
        
        # 计算回撤
        portfolio_df['running_max'] = portfolio_df['cumulative_return'].expanding().max()
        portfolio_df['drawdown'] = (portfolio_df['cumulative_return'] - portfolio_df['running_max']) / portfolio_df['running_max']
        
        # 最大回撤
        max_drawdown = portfolio_df['drawdown'].min()
        
        # 最大回撤持续期
        drawdown_periods = []
        in_drawdown = False
        drawdown_start = None
        
        for i, dd in enumerate(portfolio_df['drawdown']):
            if dd < 0 and not in_drawdown:
                # 开始回撤
                in_drawdown = True
                drawdown_start = i
            elif dd >= 0 and in_drawdown:
                # 结束回撤
                in_drawdown = False
                if drawdown_start is not None:
                    drawdown_periods.append(i - drawdown_start)
        
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        
        # 计算周收益率
        portfolio_df['prev_value'] = portfolio_df['total_value'].shift(1)
        portfolio_df['weekly_return'] = (portfolio_df['total_value'] - portfolio_df['prev_value']) / portfolio_df['prev_value']
        weekly_returns = portfolio_df['weekly_return'].dropna()
        
        # VaR (Value at Risk) - 95%置信度
        var_95 = weekly_returns.quantile(0.05) if not weekly_returns.empty else 0
        
        # 下行风险（负收益的标准差）
        negative_returns = weekly_returns[weekly_returns < 0]
        downside_risk = negative_returns.std() if not negative_returns.empty else 0
        
        # 年化下行风险
        annual_downside_risk = downside_risk * np.sqrt(52) if not np.isnan(downside_risk) else 0
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'var_95': var_95,
            'downside_risk': downside_risk,
            'annual_downside_risk': annual_downside_risk
        }
    
    def calculate_sharpe_ratio(self, portfolio_df: pd.DataFrame, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率
        
        Args:
            portfolio_df: 投资组合历史数据
            risk_free_rate: 无风险利率（年化）
            
        Returns:
            夏普比率
        """
        returns_metrics = self.calculate_returns(portfolio_df)
        
        if not returns_metrics:
            return 0
        
        annual_return = returns_metrics['annual_return']
        annual_volatility = returns_metrics['annual_volatility']
        
        if annual_volatility == 0:
            return 0
        
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
        return sharpe_ratio
    
    def calculate_sortino_ratio(self, portfolio_df: pd.DataFrame, risk_free_rate: float = 0.03) -> float:
        """
        计算索提诺比率
        
        Args:
            portfolio_df: 投资组合历史数据
            risk_free_rate: 无风险利率（年化）
            
        Returns:
            索提诺比率
        """
        returns_metrics = self.calculate_returns(portfolio_df)
        risk_metrics = self.calculate_risk_metrics(portfolio_df)
        
        if not returns_metrics or not risk_metrics:
            return 0
        
        annual_return = returns_metrics['annual_return']
        annual_downside_risk = risk_metrics['annual_downside_risk']
        
        if annual_downside_risk == 0:
            return 0
        
        sortino_ratio = (annual_return - risk_free_rate) / annual_downside_risk
        return sortino_ratio
    
    def calculate_trading_metrics(self, transaction_df: pd.DataFrame, 
                                portfolio_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算交易相关指标
        
        Args:
            transaction_df: 交易记录
            portfolio_df: 投资组合历史
            
        Returns:
            交易指标字典
        """
        if transaction_df.empty:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'turnover_rate': 0
            }
        
        # 基础交易统计
        total_trades = len(transaction_df)
        buy_trades = len(transaction_df[transaction_df['type'] == 'BUY'])
        sell_trades = len(transaction_df[transaction_df['type'] == 'SELL'])
        
        # 计算换手率
        if not portfolio_df.empty:
            avg_portfolio_value = portfolio_df['total_value'].mean()
            total_trade_value = transaction_df['gross_amount'].sum()
            
            # 计算时间跨度
            if 'date' in portfolio_df.columns:
                days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
            else:
                days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
            years = days / 365.25
            
            # 年化换手率
            turnover_rate = (total_trade_value / avg_portfolio_value) / years if years > 0 else 0
        else:
            turnover_rate = 0
        
        # 交易频率
        if not portfolio_df.empty:
            weeks = len(portfolio_df)
            trade_frequency = total_trades / weeks if weeks > 0 else 0
        else:
            trade_frequency = 0
        
        return {
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'turnover_rate': turnover_rate,
            'trade_frequency': trade_frequency,
            'avg_trade_size': transaction_df['gross_amount'].mean() if not transaction_df.empty else 0
        }
    
    def calculate_benchmark_comparison(self, portfolio_df: pd.DataFrame, 
                                    benchmark_df: pd.DataFrame) -> Dict[str, float]:
        """
        与基准进行对比分析
        
        Args:
            portfolio_df: 投资组合历史
            benchmark_df: 基准历史
            
        Returns:
            对比指标字典
        """
        if portfolio_df.empty or benchmark_df.empty:
            return {}
        
        # 确保日期对齐
        if 'date' in portfolio_df.columns:
            portfolio_df = portfolio_df.set_index('date')
        if 'date' in benchmark_df.columns:
            benchmark_df = benchmark_df.set_index('date')
        
        # 找到共同的日期范围
        common_dates = portfolio_df.index.intersection(benchmark_df.index)
        
        if len(common_dates) == 0:
            return {}
        
        portfolio_aligned = portfolio_df.loc[common_dates]
        benchmark_aligned = benchmark_df.loc[common_dates]
        
        # 计算收益率
        portfolio_returns = portfolio_aligned['total_value'].pct_change().dropna()
        benchmark_returns = benchmark_aligned['total_value'].pct_change().dropna()
        
        # 超额收益
        excess_returns = portfolio_returns - benchmark_returns
        
        # 信息比率
        if excess_returns.std() != 0:
            information_ratio = excess_returns.mean() / excess_returns.std()
        else:
            information_ratio = 0
        
        # Beta系数
        if benchmark_returns.var() != 0:
            beta = np.cov(portfolio_returns, benchmark_returns)[0, 1] / benchmark_returns.var()
        else:
            beta = 0
        
        # Alpha（年化）
        portfolio_annual = (1 + portfolio_returns.mean()) ** 52 - 1
        benchmark_annual = (1 + benchmark_returns.mean()) ** 52 - 1
        alpha = portfolio_annual - beta * benchmark_annual
        
        # 跟踪误差（年化）
        tracking_error = excess_returns.std() * np.sqrt(52)
        
        return {
            'alpha': alpha,
            'beta': beta,
            'information_ratio': information_ratio,
            'tracking_error': tracking_error,
            'excess_return': excess_returns.mean() * 52  # 年化超额收益
        }
    
    def generate_performance_report(self, portfolio_df: pd.DataFrame,
                                  transaction_df: pd.DataFrame,
                                  benchmark_df: pd.DataFrame = None) -> Dict:
        """
        生成完整的绩效报告
        
        Args:
            portfolio_df: 投资组合历史
            transaction_df: 交易记录
            benchmark_df: 基准数据（可选）
            
        Returns:
            完整绩效报告
        """
        report = {}
        
        # 收益率指标
        report['returns'] = self.calculate_returns(portfolio_df)
        
        # 风险指标
        report['risk'] = self.calculate_risk_metrics(portfolio_df)
        
        # 风险调整收益指标
        report['risk_adjusted'] = {
            'sharpe_ratio': self.calculate_sharpe_ratio(portfolio_df),
            'sortino_ratio': self.calculate_sortino_ratio(portfolio_df)
        }
        
        # 交易指标
        report['trading'] = self.calculate_trading_metrics(transaction_df, portfolio_df)
        
        # 基准对比（如果提供）
        if benchmark_df is not None:
            report['benchmark'] = self.calculate_benchmark_comparison(portfolio_df, benchmark_df)
        
        return report
    
    def print_performance_summary(self, report: Dict):
        """
        打印绩效摘要
        
        Args:
            report: 绩效报告
        """
        print("\n" + "="*60)
        print("📊 回测绩效报告")
        print("="*60)
        
        # 收益率指标
        if 'returns' in report:
            returns = report['returns']
            print(f"\n📈 收益率指标:")
            print(f"   总收益率: {returns.get('total_return', 0):.2%}")
            print(f"   年化收益率: {returns.get('annual_return', 0):.2%}")
            print(f"   年化波动率: {returns.get('annual_volatility', 0):.2%}")
            print(f"   回测天数: {returns.get('days', 0):.0f} 天")
        
        # 风险指标
        if 'risk' in report:
            risk = report['risk']
            print(f"\n⚠️ 风险指标:")
            print(f"   最大回撤: {risk.get('max_drawdown', 0):.2%}")
            print(f"   最大回撤持续期: {risk.get('max_drawdown_duration', 0):.0f} 周")
            print(f"   VaR(95%): {risk.get('var_95', 0):.2%}")
            print(f"   年化下行风险: {risk.get('annual_downside_risk', 0):.2%}")
        
        # 风险调整收益
        if 'risk_adjusted' in report:
            risk_adj = report['risk_adjusted']
            print(f"\n🎯 风险调整收益:")
            print(f"   夏普比率: {risk_adj.get('sharpe_ratio', 0):.3f}")
            print(f"   索提诺比率: {risk_adj.get('sortino_ratio', 0):.3f}")
        
        # 交易指标
        if 'trading' in report:
            trading = report['trading']
            print(f"\n💼 交易指标:")
            print(f"   总交易次数: {trading.get('total_trades', 0):.0f}")
            print(f"   买入次数: {trading.get('buy_trades', 0):.0f}")
            print(f"   卖出次数: {trading.get('sell_trades', 0):.0f}")
            print(f"   年化换手率: {trading.get('turnover_rate', 0):.2%}")
            print(f"   交易频率: {trading.get('trade_frequency', 0):.3f} 次/周")
            print(f"   平均交易规模: {trading.get('avg_trade_size', 0):,.0f} 元")
        
        # 基准对比
        if 'benchmark' in report:
            benchmark = report['benchmark']
            print(f"\n📊 基准对比:")
            print(f"   Alpha: {benchmark.get('alpha', 0):.2%}")
            print(f"   Beta: {benchmark.get('beta', 0):.3f}")
            print(f"   信息比率: {benchmark.get('information_ratio', 0):.3f}")
            print(f"   跟踪误差: {benchmark.get('tracking_error', 0):.2%}")
            print(f"   年化超额收益: {benchmark.get('excess_return', 0):.2%}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    # 测试代码
    import pandas as pd

    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='W-FRI')
    
    # 模拟投资组合数据
    np.random.seed(42)
    initial_value = 1000000
    returns = np.random.normal(0.002, 0.02, len(dates))  # 周收益率
    values = [initial_value]
    
    for ret in returns:
        values.append(values[-1] * (1 + ret))
    
    portfolio_df = pd.DataFrame({
        'date': dates,
        'total_value': values[1:],
        'cash': np.random.uniform(50000, 200000, len(dates))
    })
    
    # 模拟交易数据
    transaction_df = pd.DataFrame({
        'date': dates[:10],
        'type': ['BUY', 'SELL'] * 5,
        'stock_code': ['601088', '000807'] * 5,
        'shares': [1000] * 10,
        'price': np.random.uniform(20, 40, 10),
        'gross_amount': np.random.uniform(20000, 40000, 10),
        'transaction_cost': np.random.uniform(100, 200, 10)
    })
    
    # 创建绩效分析器
    analyzer = PerformanceAnalyzer()
    
    # 生成绩效报告
    report = analyzer.generate_performance_report(portfolio_df, transaction_df)
    
    # 打印报告
    analyzer.print_performance_summary(report)