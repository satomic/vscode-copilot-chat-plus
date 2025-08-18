from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from datetime import datetime, timezone
from utils.es_utils import ElasticsearchManager
from utils.log_utils import logger
from config import (
    SERVER_HOST, 
    SERVER_PORT, 
    SAVE_DIR, 
    INDEX_NAME_LINECHANGES, 
    MAPPING_FILE_LINECHANGES,
    TOKEN_TIME_WINDOW_MINUTES
)

# 确保保存目录存在
os.makedirs(SAVE_DIR, exist_ok=True)

# 初始化 Elasticsearch 管理器
es_manager = None
es_available = False

def compute_minute_token(timestamp: str) -> str:
    """
    根据timestamp计算token，严格按照提供的TypeScript算法实现
    function computeMinuteToken(timestamp: string): string {
      try {
        const minutePart = timestamp.slice(0, 16);
        let hash = 0x811c9dc5;
        for (let i = 0; i < minutePart.length; i++) {
          hash ^= minutePart.charCodeAt(i);
          hash = (hash >>> 0) * 0x01000193;
        }
        return (hash >>> 0).toString(16).padStart(8, '0');
      } catch {
        return '00000000';
      }
    }
    """
    try:
        # Extract the first 16 chars of ISO string: 'YYYY-MM-DDTHH:MM'
        minute_part = timestamp[:16]
        
        # FNV-1a 32-bit hash with JavaScript-like floating point behavior
        hash_val = 0x811c9dc5
        for char in minute_part:
            hash_val = hash_val ^ ord(char)
            # 模拟JavaScript的浮点乘法然后截断
            # JavaScript中所有数字运算都是浮点数，可能导致精度差异
            hash_val = int((float(hash_val) * 0x01000193)) & 0xFFFFFFFF
        
        # JavaScript: (hash >>> 0).toString(16).padStart(8, '0')
        return format(hash_val, '08x')
    except Exception:
        return '00000000'

def validate_token(timestamp: str, provided_token: str) -> bool:
    """
    验证提供的token是否与timestamp计算出的token匹配（不考虑时间窗口）
    """
    expected_token = compute_minute_token(timestamp)
    return expected_token == provided_token

def validate_token_against_current_time(timestamp: str, provided_token: str) -> bool:
    """
    验证token是否与当前时间的分钟匹配（允许一定的时间窗口）
    """
    try:
        # 解析ISO格式的时间戳 (例如: "2025-08-15T01:46:38.820Z")
        # 移除Z后缀并解析
        clean_timestamp = timestamp.replace('Z', '+00:00')
        provided_time = datetime.fromisoformat(clean_timestamp)
        
        # 获取当前UTC时间
        current_time = datetime.now(timezone.utc)
        
        # 计算时间差（分钟）
        time_diff = abs((current_time - provided_time).total_seconds() / 60)
        
        # 允许5分钟的时间窗口
        if time_diff > TOKEN_TIME_WINDOW_MINUTES:
            logger.warning(f"Token时间差过大: {time_diff:.1f}分钟")
            return False
        
        # 验证token是否正确
        expected_token = compute_minute_token(timestamp)
        return expected_token == provided_token
        
    except Exception as e:
        logger.error(f"时间验证错误: {e}")
        return False

def validate_token(timestamp: str, provided_token: str) -> bool:
    """
    验证提供的token是否与timestamp计算出的token匹配
    """
    expected_token = compute_minute_token(timestamp)
    return expected_token == provided_token

class JSONHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # 获取客户端IP地址
        client_ip = self.client_address[0]
        
        # 健康检查端点
        if self.path == '/' or self.path == '/health':
            logger.info(f"Health check request from {client_ip}")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_status = {
                "status": "healthy",
                "version": "1.0.0",
                "elasticsearch": "available" if es_available else "unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.wfile.write(json.dumps(health_status).encode())
        else:
            logger.warning(f"404 Not Found request from {client_ip} for path: {self.path}")
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
    
    def do_POST(self):
        # 获取客户端IP地址
        client_ip = self.client_address[0]
        
        # 记录接收到POST请求，包含源IP
        logger.info(f"Received POST request from {client_ip}")
        
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')

            # 解析 JSON
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid JSON format")
                return

            # Token 验证逻辑
            if 'token' not in data:
                # 没有token字段，要求提供token
                logger.warning(f"No token provided from {client_ip}")
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"Token required for authentication")
                return
            elif 'timestamp' not in data:
                # 有token但没有timestamp
                logger.warning(f"Token provided but no timestamp found from {client_ip}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Timestamp required when token is provided")
                return
            else:
                # 有token且有timestamp，进行验证
                timestamp = data['timestamp']
                provided_token = data['token']
                
                # 使用包含时间窗口的验证
                if not validate_token_against_current_time(timestamp, provided_token):
                    logger.warning(f"Token validation failed from {client_ip}")
                    logger.warning(f"  Timestamp: {timestamp}")
                    logger.warning(f"  Provided token: {provided_token}")
                    logger.warning(f"  Expected token: {compute_minute_token(timestamp)}")
                    
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b"Invalid token or timestamp too old")
                    return
                else:
                    logger.info(f"Token validation successful from {client_ip}")

            # 生成文件名
            filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json"
            filepath = os.path.join(SAVE_DIR, filename)

            # 保存到文件
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 写入到 Elasticsearch (如果可用)
            if es_available and es_manager:
                try:
                    # 确保数据有必要的字段，如果没有 id 字段，使用时间戳生成
                    if 'id' not in data:
                        data['id'] = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    
                    es_manager.write_to_es(INDEX_NAME_LINECHANGES, data)
                    logger.info(f"Data written to Elasticsearch index: {INDEX_NAME_LINECHANGES} from {client_ip}")
                except Exception as e:
                    logger.error(f"Failed to write to Elasticsearch from {client_ip}: {e}")
                    # 即使写入 ES 失败，也不阻止响应

            # 返回成功响应
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Saved to {filename}".encode())
            logger.info(f"Successfully processed request from {client_ip}, saved to {filename}")

        except Exception as e:
            logger.error(f"Server error from {client_ip}: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Server error: {e}".encode())

    def log_message(self, format, *args):
        # 禁用默认日志输出
        return

def initialize_elasticsearch():
    """初始化 Elasticsearch 索引"""
    global es_manager, es_available
    
    try:
        logger.info("Initializing Elasticsearch...")
        
        # 创建 Elasticsearch 管理器
        es_manager = ElasticsearchManager()
        
        # 检查并创建索引
        indexes = {INDEX_NAME_LINECHANGES: MAPPING_FILE_LINECHANGES}
        es_manager.check_and_create_indexes(indexes)
        
        es_available = True
        logger.info("Elasticsearch initialization completed")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {e}")
        logger.warning("Server will continue without Elasticsearch functionality")
        es_available = False
        return False

if __name__ == "__main__":
    # 初始化 Elasticsearch
    initialize_elasticsearch()
    
    server = HTTPServer((SERVER_HOST, SERVER_PORT), JSONHandler)
    logger.info(f"Server listening on http://{SERVER_HOST}:{SERVER_PORT}")
    if es_available:
        logger.info(f"Elasticsearch integration enabled - data will be stored in index: {INDEX_NAME_LINECHANGES}")
    else:
        logger.warning("Elasticsearch integration disabled - data will only be stored in files")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server.")
        server.server_close()