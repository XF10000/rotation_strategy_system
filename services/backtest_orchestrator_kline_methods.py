# 临时文件：包含要添加到BacktestOrchestrator的K线数据和基准计算方法

def _prepare_kline_data(self, portfolio_manager, transaction_history: List[Dict]) -> Dict[str, Any]:
    """准备K线数据（包含技术指标）- 确保时间轴完全对齐"""
    kline_data = {}
    
    self.logger.info(f"🔍 开始准备K线数据")
    self.logger.info(f"📊 股票数据总数: {len(self.stock_data)}")
    self.logger.info(f"📈 股票代码列表: {list(self.stock_data.keys())}")
    self.logger.info(f"📋 交易记录数量: {len(transaction_history)}")
    if transaction_history:
        self.logger.info(f"📝 交易记录示例: {transaction_history[0]}")
    
    # 过滤回测期间的数据
    start_date = pd.to_datetime(self.start_date)
    end_date = pd.to_datetime(self.end_date)
    
    for stock_code, data in self.stock_data.items():
        weekly_data = data['weekly']
        
        # 过滤K线数据到回测期间
        filtered_weekly_data = weekly_data[
            (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
        ]
        
        # 获取所有有效的时间戳（确保时间轴完全一致）
        valid_timestamps = []
        for idx in filtered_weekly_data.index:
            try:
                if hasattr(idx, 'timestamp'):
                    timestamp = int(idx.timestamp() * 1000)
                else:
                    timestamp = int(pd.to_datetime(idx).timestamp() * 1000)
                valid_timestamps.append((timestamp, idx))
            except Exception as e:
                self.logger.warning(f"时间戳转换失败: {e}, 索引: {idx}")
                continue
        
        # 准备所有数据数组
        kline_points = []
        rsi_data = []
        macd_data = []
        macd_signal_data = []
        macd_histogram_data = []
        bb_upper_data = []
        bb_middle_data = []
        bb_lower_data = []
        pvr_data = []  # 新增价值比数据
        
        # 为每个有效时间戳准备数据，确保所有指标都有对应的数据点
        for timestamp, idx in valid_timestamps:
            try:
                row = filtered_weekly_data.loc[idx]
                
                # K线数据（必须有效）- ECharts蜡烛图格式: [timestamp, open, close, low, high]
                kline_points.append([
                    timestamp,
                    float(row['open']),
                    float(row['close']),
                    float(row['low']),
                    float(row['high'])
                ])
                
                # 技术指标数据 - 直接使用当前行的值，不使用回退逻辑
                def safe_get_indicator_value(field_name, default_value):
                    """直接获取技术指标值，避免回退逻辑造成的平线问题"""
                    try:
                        if field_name not in filtered_weekly_data.columns:
                            return default_value
                        
                        current_value = row.get(field_name)
                        
                        # 如果当前值有效，直接返回
                        if current_value is not None and pd.notna(current_value):
                            return float(current_value)
                        
                        # 如果当前值无效，返回默认值而不是回退到历史值
                        # 这样可以避免造成平线效果
                        return default_value
                        
                    except Exception as e:
                        self.logger.debug(f"获取指标 {field_name} 失败: {e}")
                        return default_value
                
                # RSI数据 - 确保每个时间点都有数据
                rsi_value = safe_get_indicator_value('rsi', 50.0)
                rsi_data.append([timestamp, rsi_value])
                
                # MACD数据 - 确保每个时间点都有数据
                macd_dif_value = safe_get_indicator_value('macd', 0.0)
                macd_data.append([timestamp, macd_dif_value])
                
                macd_signal_value = safe_get_indicator_value('macd_signal', 0.0)
                macd_signal_data.append([timestamp, macd_signal_value])
                
                macd_hist_value = safe_get_indicator_value('macd_histogram', 0.0)
                macd_histogram_data.append([timestamp, macd_hist_value])
                
                # 布林带数据 - 确保每个时间点都有数据
                close_price = float(row['close'])
                bb_upper_value = safe_get_indicator_value('bb_upper', close_price * 1.02)
                bb_middle_value = safe_get_indicator_value('bb_middle', close_price)
                bb_lower_value = safe_get_indicator_value('bb_lower', close_price * 0.98)
                
                bb_upper_data.append([timestamp, bb_upper_value])
                bb_middle_data.append([timestamp, bb_middle_value])
                bb_lower_data.append([timestamp, bb_lower_value])
                
                # 价值比数据 - 使用当前价格和DCF估值直接计算
                close_price = float(row['close'])
                dcf_value = self.data_service.dcf_values.get(stock_code)
                if dcf_value and dcf_value > 0:
                    pvr_value = (close_price / dcf_value) * 100
                else:
                    pvr_value = 100.0  # 默认值，表示无DCF数据
                pvr_data.append([timestamp, pvr_value])
                    
            except Exception as e:
                self.logger.warning(f"处理K线数据点失败: {e}, 索引: {idx}")
                continue
        
        # 准备交易点数据 - 只包含该股票的交易
        trade_points = []
        stock_trade_count = 0
        
        for transaction in transaction_history:
            if transaction.get('stock_code') == stock_code:
                try:
                    trade_date = pd.to_datetime(transaction['date'])
                    
                    # 确保交易日期在回测期间内
                    if start_date <= trade_date <= end_date:
                        trade_points.append({
                            'timestamp': int(trade_date.timestamp() * 1000),
                            'price': float(transaction['price']),
                            'type': transaction['type'],
                            'shares': transaction.get('shares', 0),
                            'reason': transaction.get('reason', '')
                        })
                        stock_trade_count += 1
                        self.logger.info(f"添加交易点: {stock_code} {transaction['date']} {transaction['type']} {transaction['price']}")
                    else:
                        self.logger.warning(f"交易日期超出回测范围: {transaction['date']} (范围: {start_date} - {end_date})")
                except Exception as e:
                    self.logger.warning(f"处理交易点数据失败: {e}, 交易记录: {transaction}")
    
        self.logger.info(f"股票 {stock_code} 交易点数量: {stock_trade_count}")
        self.logger.info(f"股票 {stock_code} 技术指标数据量: RSI {len(rsi_data)}, MACD {len(macd_data)}, PVR {len(pvr_data)}")
        
        # 🆕 准备分红数据用于K线图标记
        dividend_points = []
        if stock_code in self.stock_data and 'weekly' in self.stock_data[stock_code]:
            weekly_data = self.stock_data[stock_code]['weekly']
            filtered_weekly_data = weekly_data[
                (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
            ]
            
            # 查找分红事件
            for timestamp, idx in valid_timestamps:
                try:
                    row = filtered_weekly_data.loc[idx]
                    
                    # 检查是否有分红事件
                    dividend_amount = row.get('dividend_amount', 0)
                    bonus_ratio = row.get('bonus_ratio', 0)
                    transfer_ratio = row.get('transfer_ratio', 0)
                    
                    if dividend_amount > 0 or bonus_ratio > 0 or transfer_ratio > 0:
                        # 构建分红事件数据
                        dividend_event = {
                            'timestamp': timestamp,
                            'date': idx.strftime('%Y-%m-%d'),
                            'dividend_amount': float(dividend_amount) if dividend_amount > 0 else 0,
                            'bonus_ratio': float(bonus_ratio) if bonus_ratio > 0 else 0,
                            'transfer_ratio': float(transfer_ratio) if transfer_ratio > 0 else 0,
                            'close_price': float(row['close'])
                        }
                        
                        # 确定分红事件类型和描述
                        event_types = []
                        if dividend_amount > 0:
                            event_types.append(f"现金分红{dividend_amount:.3f}元/股")
                        if bonus_ratio > 0:
                            event_types.append(f"送股{bonus_ratio:.3f}")
                        if transfer_ratio > 0:
                            event_types.append(f"转增{transfer_ratio:.3f}")
                        
                        dividend_event['description'] = "；".join(event_types)
                        dividend_event['type'] = 'dividend' if dividend_amount > 0 else ('bonus' if bonus_ratio > 0 else 'transfer')
                        
                        dividend_points.append(dividend_event)
                        
                except Exception as e:
                    self.logger.debug(f"处理分红数据失败: {e}, 索引: {idx}")
                    continue
        
        self.logger.info(f"股票 {stock_code} 分红事件数量: {len(dividend_points)}")

        kline_data[stock_code] = {
            'kline': kline_points,
            'trades': trade_points,
            'name': stock_code,  # 添加股票名称
            # 添加技术指标数据
            'rsi': rsi_data,
            'macd': {
                'dif': macd_data,
                'dea': macd_signal_data,
                'histogram': macd_histogram_data
            },
            # 添加布林带数据
            'bb_upper': bb_upper_data,
            'bb_middle': bb_middle_data,
            'bb_lower': bb_lower_data,
            # 添加价值比数据
            'pvr': pvr_data,
            # 🆕 添加分红数据
            'dividends': dividend_points
        }
    
    self.logger.info(f"🔍 _prepare_kline_data返回，总共{len(kline_data)}只股票")
    return kline_data
