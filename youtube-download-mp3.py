import yt_dlp
import os
import sys
import subprocess
import re
from IPython.display import clear_output

youtube_url = 'https://www.youtube.com/live/P5QPtqcoS7A'
output_dir = '/kaggle/working/'

# ----------------------------------------------------
# 🔍 自動檢查硬體環境
# ----------------------------------------------------
try:
    subprocess.check_output(['nvidia-smi'])
    has_gpu = True
    device_name = "CUDA / GPU 加速模式"
except (subprocess.CalledProcessError, FileNotFoundError):
    has_gpu = False
    device_name = "標準 CPU 模式"

print(f"🖥️ 偵測到運行環境：{device_name}")

# ----------------------------------------------------
# 📥 第一階段：yt-dlp 下載
# ----------------------------------------------------
downloaded_m4a_path = None
output_mp3_path = None
video_duration_seconds = 0
download_failed = False
error_msg = ""

def my_hook(d):
    global downloaded_m4a_path, video_duration_seconds
    if d['status'] == 'downloading':
        if 'filename' in d:
            downloaded_m4a_path = d['filename']
        clear_output(wait=True)
        print(f"🖥️ 運行環境：{device_name}")
        print(f"🚀 第一階段：yt-dlp 快速下載中...")
        print(f" ⏳ [下載中]: {d.get('_percent_str', '0%')} | 速度: {d.get('_speed_str', 'N/A')}")
    elif d['status'] == 'finished':
        if 'filename' in d:
            downloaded_m4a_path = d['filename']
        video_duration_seconds = d.get('info_dict', {}).get('duration', 0)
        clear_output(wait=True)
        print(f"🚀 第一階段：下載完成！正在準備轉碼...")

ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best', 
    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  
    'ignoreerrors': False,         
    'progress_hooks': [my_hook],  
    'verbose': False,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        if info:
            filename = ydl.prepare_filename(info)
            downloaded_m4a_path = os.path.splitext(filename)[0] + '.m4a'
            output_mp3_path = os.path.splitext(filename)[0] + '.mp3'
            video_duration_seconds = info.get('duration', 0)
except Exception as e:
    download_failed = True
    error_msg = str(e)

# ----------------------------------------------------
# ⚡ 第二階段：FFmpeg 轉碼 (標準安全模式)
# ----------------------------------------------------
if not download_failed and downloaded_m4a_path and os.path.exists(downloaded_m4a_path):
    if not output_mp3_path:
        output_mp3_path = os.path.splitext(downloaded_m4a_path)[0] + '.mp3'
    
    # 使用最乾淨、最相容的 FFmpeg 參數，徹底移除 -threads 0 與 -input_format
    cmd = [
        'ffmpeg', '-y', 
        '-i', downloaded_m4a_path, 
        '-acodec', 'libmp3lame', 
        '-b:a', '192k', 
        '-progress', 'pipe:1', 
        '-loglevel', 'quiet', 
        output_mp3_path
    ]
    
    print(f"🚀 第二階段：啟動安全轉碼引擎...")
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        
        last_percentage = -1
        # 即時讀取管道，解析進度條
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
                        print(f"🚀 第二階段：FFmpeg 轉碼中...")
                        print(f" ⏳ [轉碼中]: |{bar}| {percentage}% ({time_str} / 總長: {video_duration_seconds}秒)")
        process.wait()
    except Exception:
        # 【防護網】如果上面的高級進度條解析在 Kaggle 環境崩潰，立即啟動底層靜默轉碼
        clear_output(wait=True)
        print(f"🚀 高級進度條受限，切換至底層核心轉碼 (大檔案大約需要 30 秒，請稍候)...")
        fallback_cmd = ['ffmpeg', '-y', '-i', downloaded_m4a_path, '-acodec', 'libmp3lame', '-b:a', '192k', output_mp3_path]
        subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 最終驗證
    if output_mp3_path and os.path.exists(output_mp3_path):
        if os.path.exists(downloaded_m4a_path):
            os.remove(downloaded_m4a_path) # 刪除暫存 m4a
        clear_output(wait=True)
        print(f"🖥️ 運行環境：{device_name}\n")
        print(f"🎉 全部任務完成！成功生成 MP3 檔案！")
        print(f"📁 檔案保存路徑: {output_mp3_path}")
    else:
        clear_output(wait=True)
        print(f"❌ 轉碼依然失敗。")
        # 嘗試印出錯誤原因
        if os.path.exists(downloaded_m4a_path):
            print("💡 暫存的 M4A 檔案其實存在，但 FFmpeg 拒絕將其轉換為 MP3。")
else:
    clear_output(wait=True)
    print(f"❌ 下載失敗！")
    if download_failed:
        print(f"⚠️ 錯誤訊息: {error_msg}")
