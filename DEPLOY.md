# 中层干部测评系统 - 离线部署指南

## 1. 准备工作（在有网的电脑上操作）

1. **安装 Python 3.9+**：
   - 确保开发机安装了 Python，并且添加到环境变量。

2. **下载所有依赖包到 `packages` 文件夹**：
   在项目根目录（即 `requirements.txt` 所在目录）打开 CMD，运行以下命令：
   ```cmd
   mkdir packages
   pip download -d ./packages -r requirements.txt
   ```
   *这将下载所有必要的 .whl 文件到 `packages` 文件夹中。*

3. **下载 Python 安装包**：
   - 去 Python 官网下载 Windows 版本的安装包（例如 `python-3.9.13-amd64.exe`）。
   - 将其放入项目文件夹，方便在服务器上安装。

4. **打包项目**：
   - 将整个 `leader` 文件夹拷贝到 U 盘。

---

## 2. 服务器部署（在离线服务器上操作）

### 第一步：安装环境
1. **安装 Python**：
   - 运行 `python-3.xxxx.exe`。
   - **关键**：勾选 **"Add Python to PATH"**（添加到环境变量）。
   - 点击 "Install Now" 完成安装。
   - 打开 CMD 输入 `python --version` 确认安装成功。

### 第二步：离线安装依赖
1. 打开 CMD，进入项目目录（例如 `D:\cadre\leader`）。
2. 运行以下命令进行离线安装：
   ```cmd
   pip install --no-index --find-links=./packages -r requirements.txt
   ```

### 第三步：启动系统
1. 双击运行 `run_server.bat`。
2. 看到以下提示即表示启动成功：
   ```
   -------------------------------------------------------
    中层干部测评系统已启动 (Waitress Server)
    访问地址: http://192.168.x.x:1111
   -------------------------------------------------------
   ```

3. **防火墙设置**：
   - 如果其他电脑无法通过 IP 访问，请检查服务器防火墙，确保 **TCP 1111 端口** 已开放（入站规则）。

---

## 3. 文件清单核对

部署包应包含以下内容：
- [ ] `app.py`, `server.py`, `init_db.py` 等源码文件
- [ ] `templates/` (文件夹)
- [ ] `static/` (文件夹)
- [ ] `packages/` (文件夹，内含 .whl 依赖包)
- [ ] `requirements.txt`
- [ ] `run_server.bat`
- [ ] `evaluation.db` (数据库文件)
- [ ] `python-3.xx.exe` (Python 安装包)
