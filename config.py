import os

# 应用版本号
APP_VERSION = "1.0.0"

# 服务器配置
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000

# 数据存储配置
SAVE_DIR = "datas"

# Elasticsearch 配置
INDEX_NAME_LINECHANGES = "linechanges"
MAPPING_FILE_LINECHANGES = "elasticsearch/mapping/linechanges_mapping.json"

# Token 验证配置
TOKEN_TIME_WINDOW_MINUTES = 5  # 允许的时间窗口（分钟）

# debug mode controlled by environment variable
def is_debug_enabled():
    """Check if debug mode is enabled via DEBUG environment variable"""
    # print("Checking if debug mode is enabled...")
    # print("DEBUG environment variable:", os.environ.get('DEBUG', ''))
    return os.environ.get('DEBUG', '').lower() in ['true', '1', 'yes']