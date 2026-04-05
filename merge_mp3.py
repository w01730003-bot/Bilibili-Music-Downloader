import os
import subprocess
import sys

def merge_mp3s(input_dir, output_filename):
    os.chdir(input_dir)
    
    files = [f for f in os.listdir('.') if f.endswith('.mp3') and not f.startswith('【完整合并版】') and f != output_filename]
    files.sort()
    
    if not files:
        print("没有找到 MP3 文件。")
        return

    print(f"检测到以下文件准备合并:\n" + "\n".join(files))
    
    with open('list.txt', 'w', encoding='utf-8') as f:
        for file in files:
            safe_name = file.replace("'", "'\\''")
            f.write(f"file '{safe_name}'\n")
    
    output_path = os.path.join(input_dir, output_filename)
    command = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', 
        '-i', 'list.txt', '-c', 'copy', output_filename
    ]
    
    try:
        print(f"\n[>>>] 正在合并为: {output_filename}...")
        subprocess.run(command, check=True)
        print(f"\n[√] 合并成功！文件保存在: {output_path}")
        
        os.remove('list.txt')
        
        print("\n[>>>] 正在清理原分段文件...")
        for file in files:
            try:
                os.remove(file)
                print(f"  [-] 已删除: {file}")
            except Exception as e:
                print(f"  [x] 删除 {file} 失败: {e}")
    except Exception as e:
        print(f"[x] 合并失败: {e}")

if __name__ == "__main__":
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    music_base_dir = os.path.join(desktop_path, "B站音乐")
    
    if not os.path.exists(music_base_dir):
        print(f"[x] 未找到目录: {music_base_dir}")
        sys.exit(1)

    sub_dirs = [d for d in os.listdir(music_base_dir) if os.path.isdir(os.path.join(music_base_dir, d))]
    if not sub_dirs:
        print("[!] B站音乐目录下没有子文件夹。")
        sys.exit(1)

    print("\n--- 请选择要合并音频的文件夹 ---")
    for i, d in enumerate(sub_dirs):
        print(f"{i + 1}. {d}")
    
    choice = input("请输入编号: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(sub_dirs):
            selected_dir = os.path.join(music_base_dir, sub_dirs[idx])
            
            default_name = f"【完整合并版】{sub_dirs[idx]}.mp3"
            output_name = input(f"请输入合并后的文件名 (直接回车默认为 '{default_name}'): ").strip()
            if not output_name:
                output_name = default_name
            if not output_name.endswith('.mp3'):
                output_name += '.mp3'
                
            merge_mp3s(selected_dir, output_name)
        else:
            print("[x] 输入编号无效。")
    except ValueError:
        print("[x] 请输入数字编号。")
