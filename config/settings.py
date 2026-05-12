"""
系统配置文件
"""

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': 'logs/rotation_strategy.log',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}