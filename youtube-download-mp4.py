!pip install yt_dlp

import yt_dlp
import os
import sys
import subprocess
from IPython.display import clear_output

# 這裡填入你想下載的 YouTube 影片或 Shorts 網址
youtube_url = 'https://www.youtube.com/watch?v=xxxxxx' 
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
# 📥 第一階段：yt-dlp 下載回呼函式 (用來抓取真實檔名)
# ----------------------------------------------------
real_output_path = None  # 用來儲存最終預計生成的檔案路徑

def my_hook(d):
    global real_output_path
    if d['status'] == 'downloading':
        # 紀錄 yt-dlp 最終要合併輸出的真實完整路徑
        if 'filename' in d:
            real_output_path = d['filename']
            
        clear_output(wait=True)
        print(f"🖥️ 運行環境：{device_name}")
        print(f"🚀 正在下載最高畫質影像與音訊中...")
        print(f" ⏳ [下載中]: {d.get('_percent_str', '0%')} | 速度: {d.get('_speed_str', 'N/A')} | 剩餘時間: {d.get('_eta_str', 'N/A')}")
        
    elif d['status'] == 'finished':
        clear_output(wait=True)
        print(f"🚀 下載完成！正在準備合併/轉碼...")

# 動態配置 FFmpeg 合併時的硬體加速參數
ffmpeg_args = ['-threads', '0'] if has_gpu else ['-threads', 'auto']
if has_gpu:
    ffmpeg_args += ['-fflags', '+fastseek+genpts']

ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  
    
    # 這裡保留 True 是為了防止下載播放清單時因為一兩部影片壞掉而導致整個程式崩潰
    'ignoreerrors': True,         
    'progress_hooks': [my_hook],  
    'verbose': False,
    'postprocessor_args': {
        'ffmpeg': ffmpeg_args,
        'ffmpeg_i': ffmpeg_args
    }
}

print("🚀 啟動最高畫質 MP4 下載任務...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    # 我們可以透過 extract_info 先拿到影片資訊，順便雙重驗證真實檔名
    try:
        info = ydl.extract_info(youtube_url, download=False)
        if info:
            # 預估最終合併後的 mp4 檔名
            filename = ydl.prepare_filename(info)
            real_output_path = os.path.splitext(filename)[0] + '.mp4'
    except Exception:
        pass # 如果在解析階段就失敗，交給後面檢查檔案是否存在處理
        
    # 正式執行下載
    ydl.download([youtube_url])

# ----------------------------------------------------
# 🚨 第二階段：嚴格檢查檔案是否存在
# ----------------------------------------------------
clear_output(wait=True)
print(f"🖥️ 運行環境：{device_name}\n")

# 檢查檔案是否真實存在於 Kaggle 的 working 目錄中
if real_output_path and os.path.exists(real_output_path):
    print(f"🎉 全部任務完成！已成功在右側生成 MP4 影片！")
    print(f"📁 檔案路徑: {real_output_path}")
else:
    print(f"❌ 下載失敗！")
    print(f"⚠️ 原因可能為：影片網址錯誤、影片已被刪除、設為私有影片、或需要登入帳號認證。")
    print(f"💡 建議：請先檢查該 YouTube 網址在瀏覽器是否能正常播放。")
