# ============================
# 1. 確保環境套件正確
# ============================
!pip install -q accelerate safetensors librosa

import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import os
import librosa
import gc 

# ============================
# 2. 設定裝置與型態
# ============================
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
print(f"目前使用的裝置為: {device}")

# ============================
# 3. 載入模型與處理器
# ============================
model_id = "openai/whisper-large-v3"
print("正在載入 Whisper 模型... (請稍候)")

model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
).to(device)

processor = AutoProcessor.from_pretrained(model_id)
print("模型載入成功！")

# ============================
# 4. 設定路徑并檢查
# ============================
audio_path = "/kaggle/input/datasets/jng9678/my-audio-files/YTDown_YouTube_Get-Certified-Google-Cloud-Fundamentals-_Media_rLc76TEh3gA_009_128k.mp3"
output_txt_path = "/kaggle/working/transcript.txt"

if not os.path.exists(audio_path):
    raise FileNotFoundError(f"找不到您的音訊檔案，請檢查路徑: {audio_path}")

# ============================
# 5. 載入音訊 (4小時檔案，讀取需要 1-2 分鐘)
# ============================
print("正在載入並重採樣超長音訊檔案（16kHz），請稍候...")
speech, sr = librosa.load(audio_path, sr=16000)
print(f"音訊載入成功！總長度約 {len(speech)/sr/60:.2f} 分鐘")

# ============================
# 6. 「真・即時串流」手動切片解碼與寫入
# ============================
print("\n--- 辨識開始（每處理完 30 秒會立刻印出並存檔）---")

# 初始化清空檔案
with open(output_txt_path, "w", encoding="utf-8") as f:
    f.write("")

chunk_size = 30 * sr  
total_samples = len(speech)

# 開啟追加模式
with open(output_txt_path, "a", encoding="utf-8") as f:
    for i in range(0, total_samples, chunk_size):
        chunk = speech[i : i + chunk_size]
        
        # 計算當前時間戳
        start_sec = i // sr
        end_sec = min((i + chunk_size) // sr, total_samples // sr)
        start_time = f"{start_sec//60:02d}:{start_sec%60:02d}"
        end_time = f"{end_sec//60:02d}:{end_sec%60:02d}"
        
        # 特徵提取並移至 GPU
        input_features = processor(chunk, sampling_rate=16000, return_tensors="pt").input_features
        input_features = input_features.to(device, dtype=torch_dtype)
        
        # 模型推理
        with torch.no_grad():
            generated_ids = model.generate(
                input_features
                # 已移除 max_new_tokens，直接沿用模型預設的最佳上限
            )
        
        # 解碼文字
        text_segment = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # 組合輸出格式
        log_line = f"[{start_time} -> {end_time}] {text_segment}\n"
        
        # 螢幕與檔案同步即時輸出
        print(log_line, end="")
        f.write(log_line)
        f.flush()
        
        # 4 小時長音訊防爆顯存機制
        if (i // chunk_size) % 10 == 0:
            torch.cuda.empty_cache()
            gc.collect()

print("\n--- 辨識完全結束！所有內容已安全儲存在 transcript.txt ---")
