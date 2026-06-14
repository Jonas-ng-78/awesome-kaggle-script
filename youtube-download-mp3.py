import yt_dlp
import os
import sys
import subprocess
import re
from IPython.display import clear_output

youtube_url = 'https://www.youtube.com/live/xxxxxx'
output_dir = '/kaggle/working/'

# ----------------------------------------------------
# 🔍 自動檢查硬體環境 (是否有可用的 NVIDIA GPU)
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
# 📥 第一階段：yt-dlp 下載回呼函式
# ----------------------------------------------------
downloaded_m4a_path = None
output_mp3_path = None
video_duration_seconds = 0

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
        # 雙重確保 filename 有被寫入
        if 'filename' in d:
            downloaded_m4a_path = d['filename']
        video_duration_seconds = d.get('info_dict', {}).get('duration', 0)
        clear_output(wait=True)
        print(f"🚀 第一階段：下載完成！正在準備轉碼...")

# 執行下載原生 m4a 格式
ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best', 
    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  
    'ignoreerrors': True,         # 避免因播放清單中單一錯誤導致整體崩潰
    'progress_hooks': [my_hook],  
    'verbose': False,
}

print("🚀 啟動音訊下載任務...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        # 事前解析影片資訊，提早預測最終生成的 m4a 與 mp3 路徑以作防防呆準備
        info = ydl.extract_info(youtube_url, download=False)
        if info:
            filename = ydl.prepare_filename(info)
            downloaded_m4a_path = os.path.splitext(filename)[0] + '.m4a'
            output_mp3_path = os.path.splitext(filename)[0] + '.mp3'
            video_duration_seconds = info.get('duration', 0)
    except Exception:
        pass # 解析失敗時交由後續的檔案存在性檢查來攔截錯誤
        
    ydl.download([youtube_url])

# ----------------------------------------------------
# ⚡ 第二階段：動態配置 FFmpeg 參數並執行轉碼
# ----------------------------------------------------
# 如果第一階段因為錯誤被跳過，downloaded_m4a_path 將不會存在，便會直接跳到最後的失敗提示
if downloaded_m4a_path and os.path.exists(downloaded_m4a_path):
    if not output_mp3_path:
        output_mp3_path = os.path.splitext(downloaded_m4a_path)[0] + '.mp3'
    
    # 基礎 FFmpeg 指令
    cmd = ['ffmpeg', '-y']
    
    # 根據硬體檢測結果，動態注入最佳化參數
    if has_gpu:
        cmd += [
            '-threads', '0', 
            '-input_format', 'm4a',
            '-fflags', '+fastseek+genpts'
        ]
    else:
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
    
    # 轉碼結束後的善後與嚴格的實體檔案驗證
    if output_mp3_path and os.path.exists(output_mp3_path):
        if os.path.exists(downloaded_m4a_path):
            os.remove(downloaded_m4a_path) # 成功後移除暫存的 m4a
        clear_output(wait=True)
        print(f"🖥️ 運行環境：{device_name}\n")
        print(f"🎉 全部任務完成！在【{device_name}】下成功生成 MP3 檔案！")
        print(f"📁 檔案路徑: {output_mp3_path}")
    else:
        clear_output(wait=True)
        print(f"🖥️ 運行環境：{device_name}\n")
        print("\n❌ 轉碼失敗，未能生成 MP3 檔案。")
else:
    # 這裡精準攔截了網址無效、被刪除、或封鎖導致的下載失敗
    clear_output(wait=True)
    print(f"🖥️ 運行環境：{device_name}\n")
    print(f"❌ 下載失敗！")
    print(f"⚠️ 原因可能為：影片網址錯誤、影片已被刪除、設為私有影片、或需要登入帳號認證。")
    print(f"💡 建議：請先檢查該 YouTube 網址在瀏覽器是否能正常播放。")
