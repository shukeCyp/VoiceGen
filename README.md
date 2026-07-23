# VoiceGen · 多人配音工具

基于 **pywebview + Vue 3** 的桌面配音工具。使用小米 MiMo `mimo-v2.5-tts-voiceclone` 做音色克隆，支持多角色、多音色、语速设置、表格导入导出，最终合并为一首 **MP3**。

## 使用教程

- 图文教程：[`docs/使用教程.md`](docs/使用教程.md)
- 示意短视频：[`docs/assets/tutorial-preview.mp4`](docs/assets/tutorial-preview.mp4)（概念演示，非真实录屏）

## 功能

- **多人配音表格**：每行可选角色名、音色、原文、配音文本、语速、风格提示
- **多语言**：源语言 / 目标语言可选（中英日韩西法等 20+）
- **直译**：用 `mimo-v2.5-pro` 忠实翻译到目标语言
- **本土化翻译**：用大模型做 L10n（文化梗、口语、目标市场习惯），而非机械对译
- **本地音色库**：`voices/` 文件夹中的音频自动出现在下拉列表
- **语速**：每行独立设置，合成后用 `ffmpeg atempo` 精确变速（0.5x–2.0x）
- **表格导入/导出**：CSV / JSON（含 `tts_text` 译文列）
- **一键生成**：优先读「配音文本」，否则回退原文；VoiceClone 合成后拼成 MP3
- **API 配置**：Token Plan 密钥本地保存（`data/config.json`），也可读环境变量 `MIMO_API_KEY`

## 技术栈

| 层 | 技术 |
|---|---|
| 桌面壳 | Python 3 + [pywebview](https://pywebview.flowrl.com/) |
| 前端 | Vue 3 + Vite |
| TTS | MiMo `mimo-v2.5-tts-voiceclone` |
| 翻译 / 本土化 | MiMo `mimo-v2.5-pro`（同一 Base URL） |
| 默认 Base URL | `https://token-plan-cn.xiaomimimo.com/v1` |
| 音频处理 | 本地 `ffmpeg` / `ffprobe` |

## 目录结构

```text
VoiceGen/
├── main.py                 # 启动入口
├── requirements.txt
├── backend/                # Python 后端与 JS Bridge
│   ├── api.py
│   ├── mimo_tts.py
│   ├── voices.py
│   ├── audio_utils.py
│   └── ...
├── frontend/               # Vue 前端
│   ├── src/App.vue
│   └── ...
├── voices/                 # ★ 放置参考音色（wav/mp3 等）
├── output/                 # 生成的 MP3 与分段 wav
└── data/                   # 本地配置与项目缓存（勿提交密钥）
```

## 环境要求

- Python 3.10+
- Node.js 18+（仅构建前端需要）
- [ffmpeg](https://ffmpeg.org/) 已安装并在 PATH 中
- MiMo Token Plan API Key（`tp-...`）

## Windows 单文件打包（GitHub Actions / 本地）

### GitHub Actions

仓库已配置工作流 [`.github/workflows/build-windows.yml`](.github/workflows/build-windows.yml)：

1. 在 GitHub 打开 **Actions → Build Windows EXE → Run workflow**，或推送 `v*` 标签  
2. 流程会：`npm run build` 前端 → PyInstaller **单文件** → 产物 **`多人配音工具.exe`**  
3. 在对应 Run 的 Artifacts 下载；打 tag 时会附加到 Release  

运行时数据（`voices/`、`output/`、`data/`）写在 **exe 同目录**，请把参考音色放在 exe 旁的 `voices/` 文件夹。  
本机需已安装 **WebView2**（Windows 10/11 一般自带）。  
**ffmpeg / ffprobe 已内置进 Windows 安装包**，无需再单独安装；开发环境若无系统 ffmpeg，可执行：

```bash
python scripts/download_ffmpeg_windows.py
```

日志在 `data/log/voicegen-YYYY-MM-DD.log`，保留 7 天。

### 本地打包（Windows）

```bat
cd frontend
npm ci && npm run build
cd ..
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean voicegen.spec
:: 产物: dist\多人配音工具.exe
```

## 快速开始

### 1. 安装 Python 依赖

```bash
cd /Users/chaiyapeng/Downloads/VoiceGen
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 构建前端

```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. 配置 API Key

任选其一：

```bash
export MIMO_API_KEY="tp-你的密钥"
```

或启动后在应用内 **设置** 中填写（写入 `data/config.json`）。

### 4. 放入音色

将参考音频复制到：

```text
voices/
  旁白.wav
  男主.wav
  女主.mp3
```

文件名（不含扩展名）即音色名称。

### 5. 启动

```bash
python main.py
```

开发模式（热更新前端）：

```bash
# 终端 1
cd frontend && npm run dev

# 终端 2
python main.py --dev
# 或 python main.py --dev http://127.0.0.1:5173
```

打开 DevTools：

```bash
python main.py --debug
```

## 表格格式

### CSV 表头

导出（含「导出模板」）默认使用中文表头：

```csv
角色,音色,原文,配音文本,语速,风格,启用
旁白,旁白,故事从一个雨夜开始。,,1.0,,true
男主,男主,你终于来了。,,1.1,沉稳有力,true
```

| 列 | 说明 |
|---|---|
| `角色` | 角色显示名 |
| `音色` | 对应 `voices/` 中文件名（无扩展名） |
| `原文` | 源语言原文 |
| `配音文本` | 配音用文本（译文 / 本土化结果）；空则回退原文 |
| `语速` | 语速，默认 `1.0` |
| `风格` | 可选风格提示；空则用全局默认 |
| `启用` | 是否参与生成 |

导入仍兼容英文表头：`speaker,voice,text,tts_text,speed,style,enabled`。

### JSON

```json
{
  "version": 2,
  "source_lang": "zh-CN",
  "target_lang": "en-US",
  "rows": [
    {
      "speaker": "旁白",
      "voice": "旁白",
      "text": "你好。",
      "tts_text": "Hello.",
      "speed": 1.0,
      "enabled": true
    }
  ]
}
```

## 翻译与本土化

1. 在侧栏选择 **源语言** / **目标语言**
2. 填写「原文」列
3. 点击 **直译** 或 **本土化翻译**（`mimo-v2.5-pro`）
4. 结果写入「配音文本」列，可手改后再生成 MP3

| 模式 | 行为 |
|---|---|
| 直译 | 忠实含义，通顺可朗读 |
| 本土化 | 按目标市场习惯改写习语/梗/称谓等，更像本地口播 |

「检测 API」会同时校验 TTS 模型与 `mimo-v2.5-pro` 是否对该 Key 可用。

## 生成流程

1. 预检 MiMo `/models`，确认 `mimo-v2.5-tts-voiceclone` 可用  
2. 对每一行：取 `tts_text`（无则 `text`）→ 读取本地参考音频 → `POST /chat/completions` → wav  
3. 风格提示中自动附带目标语言说明  
4. 按该行语速做 `atempo` 变速  
5. 按顺序拼接，句间插入可配置静音  
6. 输出立体声 48 kHz MP3 到 `output/dubbing_时间戳.mp3`

## 注意事项

- API Key **不要**提交到 Git；`data/config.json` 已在 `.gitignore` 中
- 参考音频 Base64 有 **10MB** 上限，样本不宜过大
- Token Plan 密钥需使用 token-plan 节点；按量 `sk-` 密钥需改用 `https://api.xiaomimimo.com/v1`
- 生成依赖网络与账号额度；单行失败默认继续后续行

## License

MIT（项目脚手架；MiMo API 使用遵循小米官方条款）
