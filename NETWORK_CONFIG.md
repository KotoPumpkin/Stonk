# Stonk - 跨机器网络连接配置指南

本文档说明如何在两台不同的计算机上运行 Stonk 服务器和客户端。

---

## 一、快速开始

### 1.1 默认配置（本地测试）

在**同一台电脑**上运行服务器和客户端：
- 服务器绑定到 `0.0.0.0:8765`（所有网络接口）
- 客户端连接到 `127.0.0.1:8765`（本地回环）

无需修改任何配置，直接运行即可。

### 1.2 跨机器配置

在**不同电脑**上运行服务器和客户端：

| 设备 | 角色 | 需要运行的程序 |
|------|------|---------------|
| 电脑 A | 服务器端 | `start_admin.bat` 或 `start_admin.ps1` |
| 电脑 B | 客户端 | 修改配置后运行 `start_client.bat` 或 `start_client.ps1` |

---

## 二、服务器端配置（电脑 A）

### 2.1 启动服务器

服务器默认绑定到所有网络接口 (`0.0.0.0`)，无需修改配置。

```batch
# Windows CMD
start_admin.bat
```

```powershell
# PowerShell
.\start_admin.ps1
```

### 2.2 获取服务器 IP 地址

**Windows 系统：**
```cmd
ipconfig
```

找到类似以下的信息：
```
无线局域网适配器 WLAN:
   IPv4 地址 . . . . . . . . . . . : 192.168.1.100
```

记下这个 IP 地址（例如 `192.168.1.100`）。

### 2.3 配置防火墙（重要！）

确保服务器电脑的防火墙允许端口 8765 的入站连接。

**方法一：使用 Windows Defender 防火墙 GUI**
1. 打开"Windows Defender 防火墙"
2. 点击"高级设置"
3. 点击"入站规则" -> "新建规则"
4. 选择"端口" -> "TCP"
5. 输入端口号：`8765`
6. 选择"允许连接"
7. 命名规则为 "Stonk Server"

**方法二：使用 PowerShell（管理员权限）**
```powershell
New-NetFirewallRule -DisplayName "Stonk Server" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow
```

---

## 三、客户端配置（电脑 B）

### 3.1 方法一：修改启动脚本（推荐）

编辑 `start_client.bat`，取消注释并修改服务器地址：

```batch
set STONK_SERVER_HOST=192.168.1.100
set STONK_SERVER_PORT=8765
```

或者编辑 `start_client.ps1`：

```powershell
$env:STONK_SERVER_HOST = "192.168.1.100"
$env:STONK_SERVER_PORT = "8765"
```

### 3.2 方法二：使用环境变量

**CMD:**
```cmd
set STONK_SERVER_HOST=192.168.1.100
set STONK_SERVER_PORT=8765
start_client.bat
```

**PowerShell:**
```powershell
$env:STONK_SERVER_HOST = "192.168.1.100"
$env:STONK_SERVER_PORT = "8765"
.\start_client.ps1
```

### 3.3 方法三：在登录界面输入

启动客户端后，在登录界面的"地址"输入框中直接输入服务器 IP 地址。

---

## 四、连接测试

### 4.1 从客户端测试服务器连通性

在客户端电脑上打开命令提示符：

```cmd
telnet 192.168.1.100 8765
```

如果连接成功（屏幕变黑或显示空白），说明网络通畅。

或使用 PowerShell：
```powershell
Test-NetConnection -ComputerName 192.168.1.100 -Port 8765
```

如果 `TcpTestSucceeded` 显示为 `True`，说明连接正常。

### 4.2 启动客户端

运行修改后的启动脚本：

```batch
start_client.bat
```

在登录界面确认：
- 地址：应显示你设置的服务器 IP
- 端口：应显示 8765
- 点击"连接"按钮
- 状态应变为"已连接"（绿色）

---

## 五、常见问题排查

### Q1: 客户端显示"无法连接到服务器"

**可能原因：**
1. 服务器未启动
2. 防火墙阻止连接
3. IP 地址错误
4. 不在同一网络

**解决方法：**
1. 确认服务器已启动并显示 "WebSocket server started on ws://0.0.0.0:8765"
2. 检查服务器防火墙规则
3. 重新运行 `ipconfig` 确认 IP 地址
4. 确保两台电脑在同一局域网（同一 WiFi 或有线网络）

### Q2: 连接后很快断开

**可能原因：**
1. 网络不稳定
2. 服务器心跳超时

**解决方法：**
1. 检查网络连接质量
2. 查看服务器日志是否有异常

### Q3: 只能本机连接，其他机器无法连接

**可能原因：**
服务器绑定了 `127.0.0.1` 而非 `0.0.0.0`

**解决方法：**
检查 `shared/constants.py` 中的配置：
```python
SERVER_HOST: Final[str] = "0.0.0.0"  # 必须是 0.0.0.0
```

### Q4: 跨网段/外网连接

如需在不同网段或通过互联网连接：

1. **端口转发**：在路由器上配置端口转发，将外部请求转发到服务器内网 IP
2. **公网 IP**：需要服务器有公网 IP 或使用内网穿透工具
3. **安全考虑**：建议通过 VPN 连接，不建议直接暴露到公网

---

## 六、配置文件参考

### 服务器配置 (server/config.py)
```python
HOST = "0.0.0.0"  # 绑定所有网络接口
PORT = 8765
```

### 客户端配置 (client/config.py)
```python
# 可通过环境变量覆盖
SERVER_ADDRESS = os.environ.get("STONK_SERVER_HOST", "127.0.0.1")
SERVER_PORT_NUM = int(os.environ.get("STONK_SERVER_PORT", 8765))
```

---

## 七、网络拓扑示例

```
┌─────────────────┐         ┌─────────────────┐
│    电脑 A       │         │    电脑 B       │
│   (服务器端)     │         │   (客户端)      │
│                 │         │                 │
│  start_admin    │◄───────►│  start_client   │
│  0.0.0.0:8765   │  网络   │  192.168.1.100  │
│  IP: 192.168.1.100│         │                 │
└─────────────────┘         └─────────────────┘
```

---

**最后更新**: 2026-03-12
