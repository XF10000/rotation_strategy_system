"""
检查配置中的价值比阈值
"""

from config.csv_config_loader import load_backtest_settings

# 加载配置
config = load_backtest_settings('Input/Backtest_settings_regression_test.csv')

print("=" * 80)
print("配置中的价值比阈值")
print("=" * 80)

print(f"\n所有配置项:")
for key, value in sorted(config.items()):
    if 'value' in key.lower() or 'ratio' in key.lower() or 'threshold' in key.lower():
        print(f"   {key}: {value}")

print(f"\n关键阈值:")
print(f"   value_ratio_sell_threshold: {config.get('value_ratio_sell_threshold', '未设置')}")
print(f"   value_ratio_buy_threshold: {config.get('value_ratio_buy_threshold', '未设置')}")

print("\n" + "=" * 80)
