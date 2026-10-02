# dsh-pet 下载器

蓝色大肥鱼 dsh-pet 的 Windows 图形化下载/安装程序。分步向导：欢迎 → 版本与安装方式 → 安装位置 → AI 配置 → 选项 → 安装进度 → 完成。

- **版本**：Chat 版（默认）/ 无 Chat 版
- **安装方式**：绿色版 zip / 官方安装包 setup.exe
- **安装盘符**：默认 D 盘（不存在时回退首个非系统盘或用户目录）
- **AI 配置（可选）**：服务商下拉快速填入（DeepSeek 默认、智谱 GLM、Moonshot Kimi、阿里云百炼、硅基流动、OpenAI、自定义），写入 dsh-pet 的 `config.json` + 系统钥匙串
- **数据目录跟随安装位置**：写入数据根 marker，数据落在 `<安装目录>\data\`

## 两种发行形态

| 形态 | 说明 | 产物 |
|---|---|---|
| **离线自包含版**（推荐） | 内置两个 setup.exe（Chat + 无 Chat），**完全离线安装**，不依赖任何下载路径 | `dsh-pet-downloader-offline.zip`（~400MB） |
| **在线轻量版** | 不含 payload，运行时从在线源下载（默认官方 GitHub Releases） | `dsh-pet-downloader.exe`（~70MB） |

离线自包含版解压后目录结构：

```
dsh-pet-downloader/
├─ dsh-pet-downloader.exe
├─ _internal/
├─ payload/
│  ├─ manifest.json
│  ├─ dsh-pet-standalone-webm-chat-setup.exe
│  └─ dsh-pet-standalone-webm-setup.exe
└─ source.json          # 可选：在线源覆盖（离线时不用）
```

程序启动时自动探测 `payload/`：命中对应变体即离线安装，否则走在线源。

## 在线源覆盖（可选）

优先级：环境变量 `DSH_PET_SOURCE` > `source.json` > 向导第 2 步「在线下载源」 > 官方默认。

`source.json`（放在 exe 同目录，全部字段可省）：

```json
{
  "manifest_url": "https://example.com/dsh-pet/update.json",
  "release_base": "https://example.com/dsh-pet/releases/download/v1.0.7.0",
  "assets": {
    "dsh-pet-standalone-webm-chat-setup.exe": "https://example.com/mirror/chat-setup.exe"
  }
}
```

`DSH_PET_SOURCE` 可写同样的 JSON，或直接写一个 manifest URL。

## 开发运行

```powershell
python -m pip install -r requirements.txt
python app.py
```

## 测试

```powershell
python -m pytest -q
```

## 构建

```powershell
# 在线轻量版（单文件 exe）
powershell -ExecutionPolicy Bypass -File build.ps1
# 产物：dist\dsh-pet-downloader.exe

# 离线自包含版（onedir + payload → zip）
powershell -ExecutionPolicy Bypass -File build_offline.ps1
# 默认从 ..\dsh-pet\dist-onedir 取两个 setup.exe；也可 -PayloadDir 指定
# 产物：dist-offline\dsh-pet-downloader-offline.zip
```

## 结构

```
downloader/
├─ app.py                   入口（加载 QSS）
├─ assets/icon.ico          图标（自包含）
├─ core/site_config.py      版本 / 直链 / 网站 / marker 常量
├─ core/payload.py          离线载荷探测与 manifest
├─ core/source.py           在线源解析（env / source.json / 覆盖）
├─ core/releases.py         拉取 update.json（离线回退内嵌）
├─ core/downloader.py       urllib 下载（进度 / 取消）
├─ core/installer.py        解压 / 静默安装 / marker / 快捷方式 / 卸载脚本
├─ core/api_config.py       写 config.json + 钥匙串 + 连接测试
├─ core/ai_presets.py       服务商预设
├─ core/task.py             QThread 安装编排（离线 / 在线）
├─ ui/main_window.py        分步向导界面
├─ ui/style.qss             浅色现代蓝样式
├─ tests/                   核心单测
└─ build.ps1 / build_offline.ps1 / *.spec
```

## 版本同步

发新版 dsh-pet 时：更新 `core/site_config.py` 的 `VERSION` / `RELEASE_BASE` / `MIN_PORTABLE_DATA_VERSION`，重建两个产物；离线包需用对应版本的两个 setup.exe 重新构建并上传 Releases。
