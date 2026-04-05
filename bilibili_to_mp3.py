import os
import sys
from yt_dlp import YoutubeDL

def download_bilibili_audio(video_url, base_dir, category='Downloads', browser_name='edge'):
    save_path = os.path.join(base_dir, category)
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': {
            'default': os.path.join(save_path, '%(title)s.%(ext)s'),
            'playlist': os.path.join(save_path, '%(playlist_title)s', '[%(playlist_index)02d] %(title)s.%(ext)s'),
        },
        'cookiesfrombrowser': (browser_name,), 
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'noplaylist': False,
        'quiet': False,
        'ignoreerrors': True,
    }

    print(f"\n[>>>] [当前分类: {category}] 开始下载: {video_url}")
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"[√] 成功！音频已存储在对应的归档目录中。\n")
    except Exception as e:
        print(f"[x] 下载过程中出现错误: {e}")

def select_category(base_dir):
    categories = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    print("\n--- 现有分类 ---")
    for i, cat in enumerate(categories):
        print(f"{i + 1}. {cat}")
    print(f"{len(categories) + 1}. 新建分类")
    
    choice = input("请选择分类编号 (直接回车默认使用 'Downloads'): ").strip()
    if not choice:
        return 'Downloads'
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(categories):
            return categories[idx]
        elif idx == len(categories):
            new_cat = input("请输入新分类名称: ").strip()
            return new_cat if new_cat else 'Downloads'
    except ValueError:
        pass
    return 'Downloads'

if __name__ == "__main__":
    print("=" * 45)
    print("      Bilibili 视频转 MP3 自动化归档工具     ")
    print("=" * 45)
    
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    music_base_dir = os.path.join(desktop_path, "B站音乐")
    if not os.path.exists(music_base_dir):
        os.makedirs(music_base_dir)

    category = select_category(music_base_dir)

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.isfile(arg) and arg.endswith('.txt'):
                print(f"[>>>] 检测到列表文件 {arg}，开始批量下载...")
                with open(arg, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip().startswith('http')]
                for url in urls:
                    download_bilibili_audio(url, music_base_dir, category)
            else:
                download_bilibili_audio(arg, music_base_dir, category)
    else:
        while True:
            url_input = input("请输入 B站链接 或 .txt 路径 (输入 'q' 退出): ").strip()
            if url_input.lower() == 'q':
                break
            if os.path.isfile(url_input) and url_input.endswith('.txt'):
                with open(url_input, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip().startswith('http')]
                for url in urls:
                    download_bilibili_audio(url, music_base_dir, category)
            elif url_input:
                download_bilibili_audio(url_input, music_base_dir, category)
