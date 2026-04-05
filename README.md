# B站音乐归档工具 (Bilibili Audio Downloader)

一个基于 `yt-dlp` 的 B 站视频音频提取与归档工具。支持批量下载、分类管理、MP3 转换。

## 功能列表

- **批量下载**：支持单个 URL、播放列表或通过 `.txt` 文件批量导入。
- **分类归档**：在下载前选择分类（如：说唱、相声、街头等），自动移动到对应文件夹。
- **MP3 转换**：自动提取 320kbps 高质量 MP3。
- **智能重命名**：按播放列表索引排序重命名。

## 快速开始

1. **依赖安装**：
   ```bash
   pip install -r requirements.txt
   ```
2. **运行脚本**：
   ```bash
   python bilibili_to_mp3.py
   ```
3. **输入选项**：
   - 粘贴 B 站链接。
   - 或拖入包含链接的 `.txt` 文件。

## 核心文件说明

- `bilibili_to_mp3.py`: 主下载逻辑（带分类管理）。
- `merge_mp3.py`: 合并多个音频文件的工具。
- `requirements.txt`: Python 依赖清单。
- `快速启动.bat`: Windows 便捷启动脚本。
