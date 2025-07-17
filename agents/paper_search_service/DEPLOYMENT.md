# Paper Search Service - 部署指南

本文档提供了 Paper Search Service 的完整部署指南，包括开发环境和生产环境的部署方式。

## 📋 前置要求

### 系统要求
- Docker 20.10+ 和 Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 5GB 可用磁盘空间

### 配置要求
- 有效的 `config/config.yaml` 配置文件
- OpenRouter API Key（用于聊天功能）

## 🚀 快速部署

### 1. 检查项目结构

确保你的项目根目录包含以下结构：
```
nana/
├── config/
│   └── config.yaml           # 必需：配置文件
├── agents/
│   └── paper_search_service/ # 服务代码
├── tools/                    # 必需：工具模块
├── storage/                  # 必需：数据存储
└── logs/                     # 日志目录
```

### 2. 配置文件设置

复制并编辑配置文件：
```bash
cp config/config.template.yaml config/config.yaml
```

确保配置文件包含有效的 LLM 设置：
```yaml
llms:
  gemini-2.5-flash:
    base_url: https://openrouter.ai/api/v1
    api_key: "sk-or-v1-YOUR_ACTUAL_API_KEY"  # 替换为实际 API Key
    model: "google/gemini-2.0-flash-exp"
    cost:
      input: 0.35
      output: 0.70
```

### 3. 生产环境部署

```bash
cd agents/paper_search_service

# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 4. 开发环境部署

```bash
cd agents/paper_search_service

# 使用开发配置启动（包含热重载）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 或者后台运行
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 🔧 高级部署选项

### 本地开发（无 Docker）

如果你不想使用 Docker，可以直接运行：

```bash
cd agents/paper_search_service

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 20002 --reload
```

### 自定义端口

修改 `docker-compose.yml` 中的端口映射：
```yaml
services:
  paper-search-service:
    ports:
      - "YOUR_PORT:20002"  # 将 YOUR_PORT 替换为你想要的端口
```

### 环境变量配置

你可以通过环境变量覆盖默认设置：

```bash
# 设置自定义端口
export PORT=8080

# 设置日志级别
export LOG_LEVEL=DEBUG

# 启动服务
docker-compose up -d
```

## 🌐 反向代理配置

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:20002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Traefik 配置示例

```yaml
# docker-compose.yml 中添加 labels
services:
  paper-search-service:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.paper-search.rule=Host(`your-domain.com`)"
      - "traefik.http.services.paper-search.loadbalancer.server.port=20002"
```

## 📊 监控和维护

### 健康检查

服务提供了健康检查端点：
```bash
curl http://localhost:20002/health
```

响应示例：
```json
{"status": "healthy"}
```

### 查看日志

```bash
# 实时查看日志
docker-compose logs -f paper-search-service

# 查看最近 100 行日志
docker-compose logs --tail=100 paper-search-service
```

### 数据备份

重要的数据存储在以下位置：
- `storage/paper_search_agent/cache.json` - 论文缓存
- `storage/paper_search_agent/*/` - 论文分析结果

建议定期备份：
```bash
# 创建备份
tar -czf backup-$(date +%Y%m%d).tar.gz storage/

# 恢复备份
tar -xzf backup-YYYYMMDD.tar.gz
```

### 服务更新

```bash
# 停止服务
docker-compose down

# 拉取最新代码
git pull

# 重新构建和启动
docker-compose up -d --build
```

## 🐛 故障排除

### 常见问题

**1. 服务无法启动**
```bash
# 检查配置文件
cat config/config.yaml

# 检查端口占用
netstat -tlnp | grep 20002

# 查看详细错误
docker-compose logs paper-search-service
```

**2. API Key 错误**
- 确保 `config/config.yaml` 中的 API Key 是有效的
- 检查 API Key 格式：应该以 `sk-or-v1-` 开头

**3. 论文数据无法加载**
```bash
# 检查存储目录权限
ls -la storage/paper_search_agent/

# 运行脚本生成测试数据
cd agents/paper_search_service/scripts
python paper_search_agent.py
```

**4. 内存不足**
```bash
# 调整 Docker 内存限制
docker-compose.yml 中添加：
services:
  paper-search-service:
    deploy:
      resources:
        limits:
          memory: 2G
```

### 性能优化

1. **调整 worker 数量**：
   ```python
   # main.py 中修改
   uvicorn.run("main:app", workers=4)
   ```

2. **启用缓存**：
   - Redis 缓存配置
   - 静态文件缓存

3. **数据库优化**：
   - 考虑使用 PostgreSQL 替代文件存储
   - 添加数据库索引

## 🔒 安全注意事项

1. **API Key 保护**：
   - 不要在代码中硬编码 API Key
   - 使用环境变量或安全的配置管理

2. **网络安全**：
   - 使用 HTTPS
   - 配置防火墙规则
   - 定期更新依赖

3. **访问控制**：
   - 考虑添加身份验证
   - 限制 API 访问频率

## 📞 技术支持

如果遇到部署问题，请提供以下信息：
- 操作系统和版本
- Docker 版本
- 错误日志
- 配置文件（隐藏敏感信息）

---

部署成功后，访问 http://localhost:20002 开始使用 Paper Search Service！ 