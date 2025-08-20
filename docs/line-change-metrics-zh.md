# Agent 模式文件编辑行数统计功能

## 概述

该功能用于统计和记录 GitHub Copilot Chat Agent 在编辑文件时的行数变化，并将统计数据发送到指定的远程服务器。这有助于分析 Agent 的编辑效果和用户的使用模式。

## 功能特性

- **实时行数跟踪**：监控 Agent 对文件的实时编辑操作
- **精确统计**：区分新增行数和删除行数
- **多文件支持**：支持同时跟踪多个文件的编辑
- **会话级统计**：在每个对话会话结束时统计和发送数据
- **智能文件识别**：使用相对路径避免同名文件冲突
- **支持新建和修改文件**：能够处理完全新建的文件和对现有文件的修改

## 核心组件

### 1. LineChangeRecorder (行数变化记录器)

主要功能模块位于 `src/extension/metrics/node/lineChangeRecorder.ts`：

- **文件编辑监听**：通过 `ChatResponseTextEditPart` 监听文件编辑事件
- **原始内容捕获**：在首次编辑时捕获文件的原始内容
- **变化累积**：在会话期间累积所有文件的变化
- **会话结束处理**：在会话结束时统一计算和发送统计数据

### 2. 数据格式

每个文件的统计记录包含以下信息：

```typescript
interface SingleFileRecord {
    version: 1;
    timestamp: string;           // ISO时间戳
    token: string;              // 基于时间的访问令牌
    sessionId: string;          // 会话ID
    responseId: string;         // 响应ID
    agentId?: string;           // Agent ID
    command?: string;           // 执行的命令
    githubUsername?: string;    // GitHub用户名
    gitUrl?: string;           // Git仓库URL
    vscodeVersion?: string;    // VSCode版本
    model?: string;            // 使用的AI模型
    file: string;              // 文件相对路径
    language: string;          // 编程语言
    added: number;             // 新增行数
    removed: number;           // 删除行数
}
```

### 3. 传输机制

数据通过HTTP POST请求发送到配置的远程端点：

- **端点发现**：通过GitHub的内容排除API查找配置的度量端点
- **批量发送**：会话结束时为每个修改的文件发送单独的POST请求
- **错误处理**：包含超时机制和错误恢复

## 配置方法

### 1. 通过GitHub内容排除规则配置

在GitHub组织或企业级别创建内容排除规则：

**规则名称选项：**
- `copilot-metrics`（推荐）：明确指定度量收集
- `*`：通配符规则

**路径配置：**
规则的第一个路径应该是完整的HTTP/HTTPS URL，例如：
```
https://your-metrics-server.com/api/line-changes
```

### 2. 配置优先级

系统按以下优先级查找配置：

1. **Git仓库级别**：针对当前工作区的Git仓库查找规则
2. **组织级别**：查找组织级别的通配符规则
3. **企业级别**：查找企业级别的通配符规则（通过伪仓库URL触发）

## 统计逻辑

### 新建文件
- **检测条件**：原始内容为空，修改后内容不为空
- **统计方式**：将所有行计为新增行数
- **行数计算**：排除文件末尾的空行

### 修改现有文件
- **检测条件**：原始内容和修改后内容都不为空
- **统计方式**：使用差异算法计算新增和删除的行数
- **算法配置**：忽略空白符变化，最大计算时间10秒

### 文件类型识别

支持多种编程语言的自动识别：

- TypeScript/JavaScript: `.ts`, `.tsx`, `.js`, `.jsx`
- Python: `.py`
- Java: `.java`
- Go: `.go`
- Rust: `.rs`
- C/C++: `.c`, `.cpp`, `.cc`, `.cxx`
- C#: `.cs`
- 以及更多常见文件类型...

## 集成点

### 1. ChatParticipantRequestHandler

在 `src/extension/prompt/node/chatParticipantRequestHandler.ts` 中集成：

- **流包装**：将ChatResponseStream包装为LineChangeRecorderStream
- **会话管理**：在会话结束时调用`finishSession()`方法
- **错误处理**：记录处理过程中的错误

### 2. GitService 增强

在 `src/platform/git/vscode/gitServiceImpl.ts` 中增强：

- **新建文件处理**：改进对新建文件的Git信息获取
- **目录回退**：文件不存在时使用父目录查找Git仓库信息

## 使用场景

1. **开发效率分析**：了解Agent帮助用户编辑了多少行代码
2. **功能使用统计**：分析不同Agent功能的使用频率
3. **质量评估**：通过编辑行数评估Agent的工作效果
4. **用户行为分析**：了解用户与Agent的交互模式

## 隐私和安全

- **内容保护**：只传输行数统计，不传输具体的代码内容
- **用户标识**：只记录GitHub用户名，不记录个人敏感信息
- **会话隔离**：每个会话的数据独立处理
- **可选配置**：需要明确配置度量端点才会发送数据

## 故障排除

### 常见问题

1. **没有发送数据**：检查是否正确配置了度量端点
2. **新建文件统计异常**：确保VSCode能正确访问文件系统
3. **Git信息获取失败**：检查工作区是否为有效的Git仓库

### 调试信息

系统会在VSCode开发者控制台中记录详细的调试信息：

```
[lineChangeRecorder] Session explicitly finishing, processing accumulated changes for N files
[lineChangeRecorder] Sending POST request to <URL> for file: <path> (+X/-Y)
[lineChangeRecorder] Session-end processing completed: N/M files processed successfully
```

## 技术实现细节

### 架构设计

- **流式处理**：通过ChatResponseStream的spy机制监听编辑事件
- **异步处理**：使用Promise处理文件读取和差异计算
- **内存管理**：及时清理累积的文件内容和Promise
- **会话生命周期**：与Chat会话生命周期同步

### 性能考虑

- **延迟加载**：只在检测到编辑时才读取文件内容
- **批量处理**：会话结束时批量处理所有变化
- **超时保护**：网络请求包含5秒超时机制
- **错误隔离**：单个文件处理失败不影响其他文件

---

*该功能随GitHub Copilot Chat扩展提供，用于改进AI辅助编程体验的质量和效果分析。*