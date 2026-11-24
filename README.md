```markdown
# secure-chat 安全聊天系统
安全聊天系统前后端统一规范 v1.0

> 本文档为项目 README + 接口约定文档，所有成员开发、联调、提交代码都以此为准。

## 技术栈约定
- 前端：`Vue 3 + Vite + TypeScript`
- 后端：`Python + FastAPI`
- 数据库：开发阶段 `SQLite`，最终可切换 `MySQL`
- 实时通信：`WebSocket over TLS（WSS）`
- 身份状态：JWT 存放于 `HttpOnly + Secure Cookie`，禁止 localStorage 存 token
- 证书：基础版实现**服务器单向 TLS**；双向 mTLS 作为可选增强功能

## 统一架构
```
Vue 浏览器客户端
        |
 HTTPS / WSS
        |
FastAPI 后端
        |
SQLite / MySQL
        |
用户、会话、消息、证书信息
```
> 重要约束：前端不直接访问数据库，不自行判断用户权限；**所有认证、授权、数据校验全部由后端完成**。

前后端同域名同端口部署示例：
```
[https://localhost:8443](https://localhost:8443)
wss://localhost:8443/ws/chat
```
同域下浏览器会自动携带安全 Cookie 进入 WebSocket 连接，无需把 JWT 放在 URL 参数里。

## 项目目录与分工归属
```
secure-chat/
  frontend/                # 前端成员负责
    src/
      api/                 # REST 接口调用
      views/               # 登录、注册、聊天、证书页面
      components/          # 可复用组件
      stores/              # 用户状态、聊天状态
      types/               # 前后端共享数据类型
  backend/                 # 后端成员负责
    app/
      main.py              # 程序入口
      api/                 # REST 路由
      websocket/           # WSS 聊天连接
      services/            # 业务逻辑
      models/              # 数据库模型
      schemas/             # 请求与响应数据结构
      security/            # JWT、密码、TLS、证书
  certs/                   # 证书成员负责
  scripts/                 # 启动、签发证书、测试脚本
  docs/                    # 架构、接口、测试、报告材料
```
> 分工原则：前端主要修改 `frontend/`；后端主要修改 `backend/`；证书相关人员修改 `certs/`、`scripts/`；不允许未经沟通大范围重构他人负责目录。

## 数据格式总规范
所有 REST 接口：JSON、UTF-8、**camelCase 字段名**

✅ 成功响应模板
```json
{
  "success": true,
  "data": {}
}
```

❌ 失败响应模板
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PASSWORD",
    "message": "用户名或密码错误"
  }
}
```
> 安全要求：后端**禁止直接返回 Python 异常栈、数据库报错、JWT 密钥、证书路径给前端**。

### 预设错误码表
| HTTP 状态码 | 错误码                | 含义                         |
| ----------- | --------------------- | ---------------------------- |
| 400         | `VALIDATION_ERROR`    | 输入格式错误                 |
| 401         | `UNAUTHORIZED`        | 未登录、会话失效或认证失败   |
| 403         | `FORBIDDEN`           | 已登录但是无权限访问资源     |
| 404         | `NOT_FOUND`           | 用户、会话、消息等资源不存在 |
| 409         | `USERNAME_EXISTS`     | 用户名已被注册               |
| 422         | `INVALID_CERTIFICATE` | 证书无效、过期、不受信任     |
| 500         | `INTERNAL_ERROR`      | 服务端内部错误               |

## REST 接口定义
### 认证模块
#### 注册
`POST /api/auth/register`
请求体
```json
{
  "username": "alice",
  "password": "ExamplePassword123!",
  "displayName": "Alice"
}
```
成功返回
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "alice",
    "displayName": "Alice"
  }
}
```
注册规则
- 用户名：3-20 位，仅字母、数字、下划线
- 密码：最少8位，必须包含字母+数字
- 密码后端使用 `bcrypt` / `argon2` 哈希存储，**严禁明文存储**

#### 登录
`POST /api/auth/login`
请求体
```json
{
  "username": "alice",
  "password": "ExamplePassword123!"
}
```
后端成功后设置 Cookie
```
Set-Cookie: accessToken=...; HttpOnly; Secure; SameSite=Lax; Path=/
```
响应
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "alice",
      "displayName": "Alice",
      "role": "user"
    }
  }
}
```

#### 获取当前登录用户信息
`GET /api/auth/me`
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "alice",
    "displayName": "Alice",
    "role": "user",
    "certificateStatus": "valid"
  }
}
```
> 前端规范：JWT 不在 localStorage 存放，用户状态统一通过本接口拉取。

#### 登出
`POST /api/auth/logout`
后端清除 accessToken Cookie；前端清空页面状态，跳转登录页。

### 聊天相关 REST 接口
#### 获取在线用户列表
`GET /api/users/online`
```json
{
  "success": true,
  "data": [
    {
      "id": 2,
      "username": "bob",
      "displayName": "Bob",
      "online": true
    }
  ]
}
```

#### 获取私聊历史消息
`GET /api/messages/private/{userId}?page=1&pageSize=30`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 101,
        "senderId": 1,
        "receiverId": 2,
        "content": "你好",
        "createdAt": "2026-11-24T10:30:00+08:00",
        "signatureStatus": "verified"
      }
    ],
    "page": 1,
    "pageSize": 30,
    "total": 1
  }
}
```
权限规则：后端校验会话权限，用户只能读取自己参与的私聊记录。

## WebSocket 消息规范
连接地址：`wss://localhost:8443/ws/chat`
> 连接前置校验：后端校验 Cookie 内 JWT，认证通过才建立长连接；未登录直接拒绝握手。

所有 WebSocket 消息统一外层结构：
```json
{
  "type": "消息类型",
  "requestId": "前端生成 UUID",
  "payload": {}
}
```

### 前端发送私聊消息
```json
{
  "type": "privateMessage",
  "requestId": "fd5afc1a-6969-44da-95cf-41c8b8a8d01d",
  "payload": {
    "receiverId": 2,
    "content": "你好，Bob"
  }
}
```

### 后端推送给接收方（消息到达通知）
```json
{
  "type": "messageReceived",
  "requestId": "fd5afc1a-6969-44da-95cf-41c8b8a8d01d",
  "payload": {
    "id": 101,
    "senderId": 1,
    "senderName": "Alice",
    "receiverId": 2,
    "content": "你好，Bob",
    "createdAt": "2026-11-24T10:30:00+08:00",
    "signatureStatus": "verified"
  }
}
```

### 后端回复发送方（消息入库确认）
```json
{
  "type": "messageAccepted",
  "requestId": "fd5afc1a-6969-44da-95cf-41c8b8a8d01d",
  "payload": {
    "messageId": 101,
    "createdAt": "2026-11-24T10:30:00+08:00"
  }
}
```

### WebSocket 错误消息
```json
{
  "type": "error",
  "requestId": "fd5afc1a-6969-44da-95cf-41c8b8a8d01d",
  "payload": {
    "code": "UNAUTHORIZED",
    "message": "登录已失效，请重新登录"
  }
}
```

### WebSocket 强制规则
1. 单条消息最大长度：2000 字符
2. 前端渲染文本必须转义，禁止直接插入 HTML，防 XSS
3. **senderId 后端从 Cookie 身份解析，绝不信任前端上传的 senderId**
4. 每条消息校验：接收者存在、发送者登录状态合法、消息内容非空
5. 断连重连策略：前端间隔3s自动重连，最多重试3次

## TLS & 证书规范
### 基础版本：单向 TLS
- 浏览器校验服务器证书合法性
- 服务器不校验客户端证书
证书目录结构
```
certs/
  ca/
    ca.crt
    ca.key
  server/
    server.crt
    server.key
  client/
    alice.crt
    alice.key
```
基础版必须覆盖演示场景：
1. 使用可信服务器证书，客户端正常连接
2. 证书不受信任 / 证书错误：浏览器拒绝 TLS 连接
3. 证书过期：连接失败或明确告警
4. 未登录用户无法建立 WSS 聊天连接

### 增强版本：双向 TLS（mTLS）
- 客户端校验服务器证书
- 服务器校验客户端证书，且证书必须为本组 CA 签发
> 实现方式：在 TLS 握手层配置，**不要仅用前端页面上传证书模拟双向认证**

## 数据库最小表结构
```
users
- id
- username
- passwordHash
- displayName
- role
- certificateSerialNumber
- createdAt

messages
- id
- senderId
- receiverId
- content
- signature
- createdAt

userCertificates
- id
- userId
- serialNumber
- subject
- issuer
- notBefore
- notAfter
- status
```
时间规范：数据库底层存储 UTC 时间；接口返回带时区 ISO 8601 字符串，前端本地格式化展示。

## 接口变更规则
接口文档存放在 `docs/api.md`，修改接口前必须先更新文档，文档需要包含：
- 请求路径 + 请求方法
- 请求字段、类型、是否必填
- 成功响应样例
- 错误响应 + 对应错误码
- 接口权限要求
- 修改日期、修改人

> 禁止私自修改字段名；如需变更字段，需要前后端成员沟通确认后统一同步修改。

## 提交前最低自测清单
### ✅ 前端自检项
- [ ] 注册、登录、登出流程正常
- [ ] 未登录状态无法进入聊天页面
- [ ] WSS 连接可以正常建立、断连重连逻辑正常
- [ ] 后端返回的错误信息可以正确展示给用户

### ✅ 后端自检项
- [ ] 用户密码哈希存储，无明文密码
- [ ] 未登录用户无法访问受保护 REST / WSS 资源
- [ ] WebSocket 身份以 Cookie 为准，不采信前端 senderId
- [ ] 证书异常时 TLS 握手失败
- [ ] 异常捕获，不向外泄露堆栈、密钥、内部路径

## 核心设计思想
前端只负责页面渲染、组装合法请求；后端是唯一的权限判断中心；TLS 保障传输链路加密；CA 与证书模块用于通信身份认证。
```

直接全选复制，保存为 `README.md` 即可。
需要我再给一份独立精简版 `docs/api.md` 吗？