# VSCode Copilot Chat Plus

一个用于收集和分析 VSCode Copilot Chat 代码变更数据的 HTTP 服务器应用程序。该应用支持 Token 验证、数据持久化存储，并可选择性地将数据存储到 Elasticsearch 中进行进一步分析。

## 功能特性

- 🔐 **Token 验证**: 基于时间戳的安全验证机制
- 💾 **双重存储**: 同时支持文件存储和 Elasticsearch 存储
- 📊 **数据分析**: 收集代码变更、会话、响应等详细信息
- 🚀 **高可用性**: 即使 Elasticsearch 不可用，服务仍可正常运行
- 📝 **专业日志**: 使用标准 logging 模块，支持文件日志记录
- ⚙️ **配置化**: 集中的配置管理，便于部署和维护

## 技术栈

- **Python 3.x**: 核心开发语言
- **Elasticsearch**: 可选的数据存储和分析引擎
- **HTTP Server**: 内置 HTTP 服务器处理 POST 请求
- **JSON**: 数据交换格式

## 项目结构

```
vscode-copilot-chat-plus/
├── main.py                          # 主服务器文件
├── config.py                        # 配置文件
├── Dockerfile                       # Docker 镜像构建文件
├── .dockerignore                    # Docker 构建忽略文件
├── docker-compose.yml               # Docker Compose 配置（示例）
├── elasticsearch/
│   └── mapping/
│       └── linechanges_mapping.json # Elasticsearch 索引映射
├── utils/
│   ├── es_utils.py                  # Elasticsearch 工具类
│   ├── log_utils.py                 # 日志工具类
│   ├── time_utils.py                # 时间工具类
│   └── grafana_utils.py             # Grafana 工具类
├── datas/                           # 本地数据存储目录（自动创建）
├── logs/                            # 日志文件目录（自动创建）
└── README.md                        # 项目说明文档
```

## 安装与配置

### 方法一：Docker 部署（推荐）

#### 1. 拉取预构建镜像

```bash
# 拉取最新镜像
docker pull satomic/line-changes-recorder
```

#### 2. 运行容器

```bash
# 基本运行（仅文件存储）
docker run -itd \
  --network=host \
  --restart=always \
  --name line-changes-recorder \
  -v $(pwd)/data:/app/datas \
  -v $(pwd)/logs:/app/logs \
  satomic/line-changes-recorder
```

#### 4. 构建自定义镜像

如果需要修改代码并构建自己的镜像：

```bash
# 克隆项目
git clone https://github.com/satomic/vscode-copilot-chat-plus.git
cd vscode-copilot-chat-plus

# 构建镜像
docker build -t your-username/line-changes-recorder .

# 运行自定义镜像
docker run -itd \
  --network=host \
  --restart=always \
  --name line-changes-recorder \
  -p 5000:5000 \
  -v $(pwd)/data:/app/datas \
  -v $(pwd)/logs:/app/logs \
  your-username/line-changes-recorder
```

### 方法二：本地 Python 部署

#### 1. 环境要求

- Python 3.7+
- pip 包管理器
- Elasticsearch 7.x+ (可选)

#### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/satomic/vscode-copilot-chat-plus.git
cd vscode-copilot-chat-plus

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install elasticsearch
```

#### 3. 配置 Elasticsearch（可选）

如果你想使用 Elasticsearch 存储数据，请确保 Elasticsearch 服务正在运行：

```bash
# 使用 Docker 运行 Elasticsearch
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  elasticsearch:8.11.0
```

#### 4. 环境变量配置

可选的环境变量：

```bash
# Elasticsearch 连接地址（默认: http://localhost:9200）
export ELASTICSEARCH_URL="http://localhost:9200"

# 启用调试模式
export DEBUG="true"

# 日志路径（默认: logs）
export LOG_PATH="logs"
```

## 使用方法

### 启动服务器

```bash
python main.py
```

服务器将在 `http://0.0.0.0:5000` 上启动，并显示类似以下的日志信息：

```
2025-08-15 10:30:00,123 - [INFO] - Initializing Elasticsearch...
2025-08-15 10:30:00,234 - [INFO] - index already exists: linechanges
2025-08-15 10:30:00,235 - [INFO] - Elasticsearch initialization completed
2025-08-15 10:30:00,236 - [INFO] - Server listening on http://0.0.0.0:5000
2025-08-15 10:30:00,237 - [INFO] - Elasticsearch integration enabled - data will be stored in index: linechanges
```

### API 接口

#### GET / 或 GET /health

健康检查端点，用于检查服务状态。

**请求格式:**
```bash
curl http://localhost:5000/
# 或
curl http://localhost:5000/health
```

**响应示例:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "elasticsearch": "available",
  "timestamp": "2025-08-15T10:30:00.000Z"
}
```

#### POST /

接收代码变更数据的主要接口。

**请求格式:**
```bash
curl -X POST http://localhost:5000 \
  -H "Content-Type: application/json" \
  -d '{
    "id": "unique-id-123",
    "sessionId": "session-456",
    "responseId": "response-789",
    "timestamp": "2025-08-15T10:30:00.000Z",
    "token": "abcd1234",
    "githubUsername": "developer",
    "gitUrl": "https://github.com/user/repo",
    "vscodeVersion": "1.80.0",
    "model": "gpt-4",
    "file": "src/main.py",
    "language": "python",
    "added": 10,
    "removed": 5,
    "version": 1
  }'
```

**数据字段说明:**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `id` | string | 否 | 唯一标识符（如未提供会自动生成） |
| `sessionId` | string | 是 | 会话 ID |
| `responseId` | string | 是 | 响应 ID |
| `timestamp` | string | 是 | ISO 8601 时间戳 |
| `token` | string | 是 | 验证令牌 |
| `githubUsername` | string | 是 | GitHub 用户名 |
| `gitUrl` | string | 是 | Git 仓库地址 |
| `vscodeVersion` | string | 是 | VSCode 版本 |
| `model` | string | 是 | AI 模型名称 |
| `file` | string | 是 | 文件路径 |
| `language` | string | 是 | 编程语言 |
| `added` | integer | 是 | 新增行数 |
| `removed` | integer | 是 | 删除行数 |
| `version` | integer | 是 | 版本号 |

### Token 验证机制

应用程序使用基于时间戳的 Token 验证机制：

1. **Token 生成**: 使用 FNV-1a 哈希算法基于时间戳的前16个字符生成
2. **时间窗口**: 允许 5 分钟的时间差（可配置）
3. **安全性**: 防止重放攻击和过期请求

## 配置选项

在 `config.py` 中可以修改以下配置：

```python
# 服务器配置
SERVER_HOST = "0.0.0.0"          # 服务器地址
SERVER_PORT = 5000               # 服务器端口

# 数据存储配置
SAVE_DIR = "datas"               # 本地文件存储目录

# Elasticsearch 配置
INDEX_NAME_LINECHANGES = "linechanges"  # 索引名称
MAPPING_FILE_LINECHANGES = "elasticsearch/mapping/linechanges_mapping.json"

# Token 验证配置
TOKEN_TIME_WINDOW_MINUTES = 5    # 时间窗口（分钟）
```

## 数据存储

### 本地文件存储

所有接收到的数据都会以 JSON 格式存储在 `datas/` 目录中，文件名格式：
```
YYYYMMDD_HHMMSS_微秒.json
```

### Elasticsearch 存储

如果 Elasticsearch 可用，数据会同时存储到 `linechanges` 索引中，便于：
- 高级查询和聚合分析
- 数据可视化（配合 Kibana）
- 实时监控和告警

## 日志记录

应用程序使用专业的日志系统：

- **日志级别**: INFO, WARNING, ERROR
- **日志格式**: 时间戳 - [级别] - 消息
- **存储位置**: `logs/` 目录
- **文件命名**: `YYYY-MM-DD.log`

## 故障排除

### 常见问题

1. **Elasticsearch 连接失败**
   ```
   Failed to initialize Elasticsearch: ...
   ```
   - 检查 Elasticsearch 服务是否运行
   - 确认连接地址是否正确
   - 服务会继续运行，只是不会存储到 ES

2. **Token 验证失败**
   ```
   Token validation failed
   ```
   - 检查时间戳格式是否为 ISO 8601
   - 确认系统时间是否准确
   - 检查 Token 生成算法

3. **端口被占用**
   ```
   Address already in use
   ```
   - 修改 `config.py` 中的 `SERVER_PORT`
   - 或终止占用端口的进程

### Docker 相关问题

1. **容器无法启动**
   ```bash
   # 检查容器日志
   docker logs line-changes-recorder
   
   # 检查容器状态
   docker ps -a
   ```

2. **健康检查失败**
   ```bash
   # 手动测试健康检查
   curl http://localhost:5000/health
   
   # 进入容器调试
   docker exec -it line-changes-recorder /bin/bash
   ```

3. **数据持久化问题**
   ```bash
   # 确保挂载目录存在且有写权限
   mkdir -p ./data ./logs
   chmod 755 ./data ./logs
   
   # 检查挂载是否成功
   docker inspect line-changes-recorder | grep Mounts -A 20
   ```

4. **网络连接问题**
   ```bash
   # 检查容器网络
   docker network ls
   docker network inspect bridge
   
   # 测试容器间连接
   docker exec line-changes-recorder ping elasticsearch
   ```

### 调试模式

启用调试模式获取更多日志信息：

```bash
# 本地运行
export DEBUG=true
python main.py

# Docker 运行
docker run -d \
  --name line-changes-recorder \
  -p 5000:5000 \
  -e DEBUG=true \
  satomic/line-changes-recorder:latest
```

## 开发与贡献

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/satomic/vscode-copilot-chat-plus.git
cd vscode-copilot-chat-plus

# 创建开发环境
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # 如果有的话
```

### 代码结构

- `main.py`: 主服务器逻辑和 HTTP 请求处理
- `config.py`: 集中的配置管理
- `utils/`: 工具类模块
  - `es_utils.py`: Elasticsearch 操作
  - `log_utils.py`: 日志配置
  - `time_utils.py`: 时间处理
  - `grafana_utils.py`: Grafana 集成

## 许可证

请查看 [LICENSE](LICENSE) 文件了解许可证信息。

## 版本历史

- **v1.0.0**: 初始版本
  - 基本的 HTTP 服务器
  - Token 验证机制
  - Elasticsearch 集成
  - 专业日志系统
  - 配置化管理

---

如有问题或建议，请提交 [Issue](https://github.com/satomic/vscode-copilot-chat-plus/issues) 或 [Pull Request](https://github.com/satomic/vscode-copilot-chat-plus/pulls)。