"""
CSV配置加载器
从Input文件夹的CSV文件中加载回测配置
"""

import logging
import os
from typing import Any, Dict

import pandas as pd

from config.path_manager import get_path_manager

logger = logging.getLogger(__name__)

def load_secrets(csv_path: str = 'config/secrets.csv') -> Dict[str, Any]:
    """
    从CSV文件加载敏感配置（如API Token）
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        Dict[str, Any]: 敏感配置字典
    """
    try:
        if not os.path.exists(csv_path):
            logger.warning(f"敏感配置文件不存在: {csv_path}，将尝试从环境变量或Backtest_settings.csv读取")
            return {}
        
        # 读取CSV文件
        df = pd.read_csv(csv_path, encoding='utf-8')
        logger.info(f"成功读取敏感配置文件: {csv_path}")
        
        # 转换为字典格式
        secrets = {}
        for _, row in df.iterrows():
            param_name = str(row['Parameter']).strip()
            param_value = row['Value']
            
            # 跳过注释行
            if param_name.startswith('#'):
                continue
            
            secrets[param_name] = param_value
            logger.debug(f"加载敏感配置: {param_name} = ***")
        
        logger.info(f"敏感配置加载完成，共 {len(secrets)} 项")
        return secrets
        
    except Exception as e:
        logger.error(f"加载敏感配置失败: {str(e)}")
        return {}

def load_portfolio_config(csv_path: str = 'Input/portfolio_config.csv') -> Dict[str, float]:
    """
    从CSV文件加载投资组合配置
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        Dict: 初始持仓配置 {股票代码: 权重}
    """
    try:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"投资组合配置文件不存在: {csv_path}")
        
        # 读取CSV文件，处理BOM
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        logger.info(f"成功读取投资组合配置文件: {csv_path}")
        
        # 转换为initial_holdings格式
        initial_holdings = {}
        total_weight = 0
        
        for _, row in df.iterrows():
            code = str(row['Stock_number']).strip()
            weight = float(row['Initial_weight'])
            
            if code.upper() == 'CASH':
                initial_holdings['cash'] = weight
            else:
                initial_holdings[code] = weight
            
            total_weight += weight
            logger.debug(f"加载持仓: {code} = {weight:.2%}")
        
        # 验证权重总和
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"权重总和不等于1.0: {total_weight:.3f}")
        else:
            logger.info(f"权重验证通过，总和: {total_weight:.3f}")
        
        return initial_holdings
        
    except Exception as e:
        logger.error(f"加载投资组合配置失败: {str(e)}")
        raise

def load_backtest_settings(csv_path: str = 'Input/Backtest_settings.csv') -> Dict[str, Any]:
    """
    从CSV文件加载回测设置
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        Dict: 回测设置参数
    """
    try:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"回测设置文件不存在: {csv_path}")
        
        # 读取CSV文件
        df = pd.read_csv(csv_path, encoding='utf-8')
        logger.info(f"成功读取回测设置文件: {csv_path}")
        
        # 转换为字典格式
        settings = {}
        
        for _, row in df.iterrows():
            param_name = str(row['Parameter']).strip()
            param_value = row['Value']
            
            # 根据参数名进行类型转换
            if param_name == 'total_capital':
                settings['total_capital'] = int(param_value)
            elif param_name in ['start_date', 'end_date']:
                # 处理日期格式，将/转换为-
                date_str = str(param_value).strip().replace('/', '-')
                settings[param_name] = date_str
            elif param_name == 'rotation_percentage':
                settings['rotation_percentage'] = float(param_value)
            # 检查参数是否与比率或阈值相关，如果是，则转换为浮点数
            elif ('ratio' in param_name or 'threshold' in param_name or 'limit' in param_name):
                settings[param_name] = float(param_value)
            else:
                # NaN → None，避免 float NaN 污染字符串配置项
                if isinstance(param_value, float) and pd.isna(param_value):
                    settings[param_name] = None
                else:
                    settings[param_name] = param_value

            logger.debug(f"加载设置: {param_name} = {param_value}")
        
        # 验证必要参数
        required_params = ['total_capital', 'start_date', 'end_date']
        for param in required_params:
            if param not in settings:
                raise ValueError(f"缺少必要参数: {param}")
        
        logger.info("回测设置加载完成")
        return settings
        
    except Exception as e:
        logger.error(f"加载回测设置失败: {str(e)}")
        raise

def create_csv_config() -> Dict[str, Any]:
    """
    创建基于CSV文件的完整回测配置
    
    Returns:
        Dict: 完整的回测配置
    """
    try:
        # 加载投资组合配置
        initial_holdings = load_portfolio_config()
        
        # 加载回测设置
        backtest_settings = load_backtest_settings()
        
        # 导入默认参数
        from config.backtest_configs import DEFAULT_COST_CONFIG, DEFAULT_STRATEGY_PARAMS

        # 合并策略参数（CSV中的参数会覆盖默认值）
        strategy_params = DEFAULT_STRATEGY_PARAMS.copy()
        # 将所有从backtest_settings加载的参数（除了基本信息）都放入strategy_params
        for key, value in backtest_settings.items():
            if key not in ['total_capital', 'start_date', 'end_date']:
                strategy_params[key] = value
        
        # 读取数据源配置（NaN → 默认值）
        data_source = backtest_settings.get('data_source') or 'akshare'
        backup_data_source = backtest_settings.get('backup_data_source') or None
        data_fetch_strategy = backtest_settings.get('data_fetch_strategy') or 'simple'

        # 如果backup_data_source是空字符串或'none'，设为None
        if backup_data_source and str(backup_data_source).lower() in ['none', '', 'null']:
            backup_data_source = None

        # 加载敏感配置（优先级：secrets.csv > Backtest_settings.csv > 环境变量）
        secrets = load_secrets()
        tushare_token = secrets.get('tushare_token')

        # 如果secrets.csv中没有token，尝试从Backtest_settings.csv读取
        if not tushare_token or tushare_token == '' or (isinstance(tushare_token, float) and pd.isna(tushare_token)):
            tushare_token = backtest_settings.get('tushare_token')
            if isinstance(tushare_token, float) and pd.isna(tushare_token):
                tushare_token = None

        # 如果仍然没有token，尝试从环境变量读取
        if not tushare_token or tushare_token == '':
            import os
            tushare_token = os.getenv('TUSHARE_TOKEN')
            if tushare_token:
                logger.info("从环境变量 TUSHARE_TOKEN 加载 Tushare token")
        
        # 创建完整配置
        config = {
            'name': 'CSV配置',
            'description': '从CSV文件加载的投资组合和回测配置',
            'total_capital': backtest_settings['total_capital'],
            'initial_holdings': initial_holdings,
            'start_date': backtest_settings['start_date'],
            'end_date': backtest_settings['end_date'],
            'strategy_params': strategy_params,  # 包含所有策略相关参数
            'cost_config': DEFAULT_COST_CONFIG.copy(),
            # 数据源配置
            'data_source': data_source,
            'backup_data_source': backup_data_source,
            'tushare_token': tushare_token,
            'data_fetch_strategy': data_fetch_strategy
        }
        
        logger.info("CSV配置创建成功")
        logger.info(f"总资金: {config['total_capital']:,}")
        logger.info(f"回测期间: {config['start_date']} 至 {config['end_date']}")
        logger.info(f"股票数量: {len([k for k in initial_holdings.keys() if k != 'cash'])}")
        logger.info(f"轮动比例: {strategy_params['rotation_percentage']:.1%}")
        logger.info(f"📊 数据源: {config['data_source']}" + 
                   (f" (备用: {config['backup_data_source']})" if config['backup_data_source'] else ""))
        
        return config
        
    except Exception as e:
        logger.error(f"创建CSV配置失败: {str(e)}")
        raise

def validate_csv_config() -> bool:
    """
    验证CSV配置文件的有效性
    
    Returns:
        bool: 配置是否有效
    """
    try:
        # 检查文件是否存在
        pm = get_path_manager()
        portfolio_file = pm.get_portfolio_config_path()
        settings_file = pm.get_backtest_settings_path()

        if not portfolio_file.exists():
            logger.error(f"投资组合配置文件不存在: {portfolio_file}")
            return False

        if not settings_file.exists():
            logger.error(f"回测设置文件不存在: {settings_file}")
            return False
        
        # 尝试加载配置
        config = create_csv_config()
        
        # 验证权重总和
        total_weight = sum(config['initial_holdings'].values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"权重总和异常: {total_weight:.3f}")
            return False
        
        logger.info("CSV配置验证通过")
        return True
        
    except Exception as e:
        logger.error(f"CSV配置验证失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 测试代码
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🔧 CSV配置加载器测试")
    print("=" * 50)
    
    try:
        # 验证配置
        if validate_csv_config():
            print("✅ 配置文件验证通过")
            
            # 加载配置
            config = create_csv_config()
            
            print(f"\n📊 配置详情:")
            print(f"配置名称: {config['name']}")
            print(f"总资金: {config['total_capital']:,} 元")
            print(f"回测期间: {config['start_date']} 至 {config['end_date']}")
            print(f"轮动比例: {config['strategy_params']['rotation_percentage']:.1%}")
            
            print(f"\n💼 投资组合:")
            for code, weight in config['initial_holdings'].items():
                if code == 'cash':
                    print(f"  现金: {weight:.1%}")
                else:
                    print(f"  {code}: {weight:.1%}")
            
            print("\n✅ CSV配置加载测试完成")
        else:
            print("❌ 配置文件验证失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
