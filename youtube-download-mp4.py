import yt_dlp
import os
import sys
import subprocess
import glob
from IPython.display import clear_output

# 這裡填入你想下載的 YouTube 影片或 Shorts 網址
youtube_url = 'https://www.youtube.com/live/P5QPtqcoS7A' 
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
# 📥 紀錄下載前資料夾的狀態，用來比對新檔案
# ----------------------------------------------------
files_before = set(os.listdir(output_dir))

# ----------------------------------------------------
# 📥 第一階段：yt-dlp 下載回呼函式
# ----------------------------------------------------
def my_hook(d):
    if d['status'] == 'downloading':
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
    ydl.download([youtube_url])

# ----------------------------------------------------
# 🚨 第二階段：動態掃描實體檔案 (全面防範特殊字元檔名變更)
# ----------------------------------------------------
clear_output(wait=True)
print(f"🖥️ 運行環境：{device_name}\n")

# 找出下載後新增加的 .mp4 檔案
files_after = set(os.listdir(output_dir))
new_files = files_after - files_before
downloaded_mp4_files = [f for f in new_files if f.endswith('.mp4')]

if downloaded_mp4_files:
    # 找到了新生成的 mp4 檔案
    final_file_name = downloaded_mp4_files[0]
    real_output_path = os.path.join(output_dir, final_file_name)
    
    print(f"🎉 全部任務完成！已成功生成 MP4 影片！")
    print(f"📁 檔案名稱: {final_file_name}")
    print(f"📍 儲存路徑: {real_output_path}")
else:
    # 如果新增檔案裡沒找到，最後做一次通配符全盤掃描（雙重保險）
    all_mp4_in_dir = glob.glob(os.path.join(output_dir, "*.mp4"))
    if all_mp4_in_dir:
        print(f"🎉 全部任務完成！已成功確認 MP4 影片存在於工作區！")
        print(f"📁 檔案路徑: {all_mp4_in_dir[0]}")
    else:
        print(f"❌ 下載失敗！")
        print(f"⚠️ 原因可能為：影片網址錯誤、影片已被刪除、設為私有影片，或網路連線中斷。")
