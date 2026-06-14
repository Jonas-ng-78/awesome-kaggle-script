!pip install yt_dlp

import yt_dlp
import os
import sys
import subprocess
import re
from IPython.display import clear_output

youtube_url = 'https://www.youtube.com/live/rLc76TEh3gA'
output_dir = '/kaggle/working/'

# ----------------------------------------------------
# 🔍 自動檢查硬體環境 (是否有可用的 NVIDIA GPU)
# ----------------------------------------------------
try:
    # 嘗試呼叫 nvidia-smi 指令，如果成功代表有 GPU 環境
    subprocess.check_output(['nvidia-smi'])
    has_gpu = True
    device_name = "CUDA / GPU 加速模式"
except (subprocess.CalledProcessError, FileNotFoundError):
    has_gpu = False
    device_name = "標準 CPU 模式"

print(f"🖥️ 偵測到運行環境：{device_name}")

# ----------------------------------------------------
# 📥 第一階段：yt-dlp 下載回呼函式
# ----------------------------------------------------
downloaded_m4a_path = None
video_duration_seconds = 0

def my_hook(d):
    global downloaded_m4a_path, video_duration_seconds
    if d['status'] == 'downloading':
        clear_output(wait=True)
        print(f"🖥️ 運行環境：{device_name}")
        print(f"🚀 第一階段：yt-dlp 快速下載中...")
        print(f" ⏳ [下載中]: {d.get('_percent_str', '0%')} | 速度: {d.get('_speed_str', 'N/A')}")
    elif d['status'] == 'finished':
        downloaded_m4a_path = d['filename']
        video_duration_seconds = d.get('info_dict', {}).get('duration', 0)
        clear_output(wait=True)
        print(f"🚀 第一階段：下載完成！")

# 執行下載原生 m4a 格式
ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best', 
    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  
    'ignoreerrors': True,         
    'progress_hooks': [my_hook],  
    'verbose': False,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([youtube_url])

# ----------------------------------------------------
# ⚡ 第二階段：動態配置 FFmpeg 參數並執行轉碼
# ----------------------------------------------------
if downloaded_m4a_path and os.path.exists(downloaded_m4a_path):
    output_mp3_path = os.path.splitext(downloaded_m4a_path)[0] + '.mp3'
    
    # 基礎 FFmpeg 指令
    cmd = ['ffmpeg', '-y']
    
    # 根据硬体检测結果，動態注入最佳化參數
    if has_gpu:
        # 有 GPU：開啟最大多線程並優化快取時戳定位，加速大檔案讀取
        cmd += [
            '-threads', '0', 
            '-input_format', 'm4a',
            '-fflags', '+fastseek+genpts'
        ]
    else:
        # 只有 CPU：使用安全的預設多線程
        cmd += ['-threads', 'auto']
        
    # 結合輸入檔案與編碼設定
    cmd += [
        '-i', downloaded_m4a_path, 
        '-acodec', 'libmp3lame', 
        '-b:a', '192k', 
        '-progress', 'pipe:1', 
        '-loglevel', 'quiet', 
        output_mp3_path
    ]
    
    # 啟動進程
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    last_percentage = -1
    for line in process.stdout:
        if 'time=' in line:
            time_str = line.split('=')[1].strip()
            match = re.match(r'(\d+):(\d+):(\d+)', time_str)
            if match and video_duration_seconds > 0:
                hours, minutes, seconds = map(int, match.groups())
                current_seconds = hours * 3600 + minutes * 60 + seconds
                percentage = min(100, int((current_seconds / video_duration_seconds) * 100))
                
                if percentage != last_percentage:
                    last_percentage = percentage
                    bar = '█' * (percentage // 5) + '-' * (20 - (percentage // 5))
                    
                    clear_output(wait=True)
                    print(f"🚀 第二階段：FFmpeg 轉碼中 ({device_name})...")
                    print(f" ⏳ [轉碼中]: |{bar}| {percentage}% ({time_str} / 總長: {video_duration_seconds}秒)")
                
    process.wait()
    
    # 清理與善後
    if os.path.exists(output_mp3_path):
        os.remove(downloaded_m4a_path) # 移除暫存的 m4a 節省 Kaggle 空間
        clear_output(wait=True)
        print(f"\n🎉 全部任務完成！在【{device_name}】下成功生成 MP3 檔案！")
    else:
        print("\n❌ 轉碼失敗。")
else:
    print("\n❌ 下載失敗。")
