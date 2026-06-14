import yt_dlp
import os
import sys
import subprocess
import re
from IPython.display import clear_output  # 引入 Kaggle 原生的畫面清除工具

youtube_url = 'https://www.youtube.com/live/rLc76TEh3gA'
output_dir = '/kaggle/working/'

downloaded_m4a_path = None
video_duration_seconds = 0

def my_hook(d):
    global downloaded_m4a_path, video_duration_seconds
    if d['status'] == 'downloading':
        # 下載時也改用 clear_output，確保即時看得見進度
        clear_output(wait=True)
        print(f"🚀 啟動 第一階段：yt-dlp 下載任務...")
        print(f" ⏳ 1/2 [下載中]: {d.get('_percent_str', '0%')} | 速度: {d.get('_speed_str', 'N/A')}")
    elif d['status'] == 'finished':
        downloaded_m4a_path = d['filename']
        video_duration_seconds = d.get('info_dict', {}).get('duration', 0)
        clear_output(wait=True)
        print(f"🚀 啟動 第一階段：yt-dlp 下載任務...")
        print(f" 🟢 1/2 [下載完成]: 檔案已儲存")

# Step 1: 下載原生 m4a
ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best', 
    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  
    'ignoreerrors': True,         
    'progress_hooks': [my_hook],  
    'verbose': False,
}

print("🚀 啟動 第一階段：yt-dlp 下載任務...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([youtube_url])

# Step 2: 獨立調用 FFmpeg 並用 Jupyter 機制即時刷新進度
if downloaded_m4a_path and os.path.exists(downloaded_m4a_path):
    output_mp3_path = os.path.splitext(downloaded_m4a_path)[0] + '.mp3'
    
    cmd = [
        'ffmpeg', '-y', '-i', downloaded_m4a_path, 
        '-acodec', 'libmp3lame', '-ab', '192k', 
        '-progress', 'pipe:1', '-loglevel', 'quiet', output_mp3_path
    ]
    
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
                
                # 為了避免頻繁刷新導致畫面閃爍，只有百分比改變時才重新繪製
                if percentage != last_percentage:
                    last_percentage = percentage
                    bar = '█' * (percentage // 5) + '-' * (20 - (percentage // 5))
                    
                    # 關鍵：強制清除 Kaggle 目前 Cell 的輸出，並立即印出最新進度
                    clear_output(wait=True)
                    print(f"🚀 啟動 第二階段：獨立調用 FFmpeg 進行 MP3 轉碼...")
                    print(f" ⏳ 2/2 [轉碼中]: |{bar}| {percentage}% ({time_str} / 影片總長: {video_duration_seconds}秒)")
                
    process.wait()
    
    if os.path.exists(output_mp3_path):
        os.remove(downloaded_m4a_path)
        clear_output(wait=True)
        print("\n🎉 全部任務完成！M4A 暫存檔已清除，MP3 檔案已成功生成！")
    else:
        print("\n❌ 轉碼失敗，未生成 MP3 檔案。")
else:
    print("\n❌ 下載失敗，無法進行轉碼。")
