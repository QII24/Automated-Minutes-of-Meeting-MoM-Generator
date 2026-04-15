from flask import Flask, render_template, request, jsonify
import whisper
import os
import uuid
import google.generativeai as genai

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==========================================
# 1. KONFIGURASI LLM (GEMINI AI)
# ==========================================
API_KEY = "AIzaSyBYLnoYiE1ANCafBl3WNkC6IQU2MaLTXDM" # <-- Ganti pakai API Key kamu
genai.configure(api_key=API_KEY)
llm_model = genai.GenerativeModel("gemini-1.5-flash")

# ==========================================
# 2. STATE KONFIGURASI GLOBAL (WHISPER)
# ==========================================
current_config = {
    "model_size": "small",
    "language": "id",
    "prompt": "Ini adalah rekaman rapat notulensi menggunakan bahasa Indonesia."
}

model = None

def load_whisper_model(size):
    global model
    print(f"\n[SYSTEM] Memuat ulang model Whisper ukuran '{size}'... (Mohon tunggu)")
    model = whisper.load_model(size)
    print(f"[SYSTEM] Model '{size}' berhasil dimuat!\n")

load_whisper_model(current_config["model_size"])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(current_config)

@app.route('/api/config', methods=['POST'])
def update_config():
    global current_config
    new_config = request.json
    
    if new_config.get('model_size') and new_config['model_size'] != current_config['model_size']:
        try:
            load_whisper_model(new_config['model_size'])
        except Exception as e:
            return jsonify({"status": "error", "message": f"Gagal memuat model: {str(e)}"}), 500
            
    current_config.update(new_config)
    return jsonify({"status": "success", "config": current_config})

# ==========================================
# 3. ENDPOINT TRANSKRIPSI (VOICE TO TEXT)
# ==========================================
@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({"error": "Tidak ada file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "File kosong"}), 400
        
    filename = f"rekaman_{uuid.uuid4().hex}.webm"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # PENGATURAN ANTI-HALUSINASI (Cegah ngelantur)
        result = model.transcribe(
            filepath, 
            language=current_config['language'] if current_config['language'] != 'auto' else None,
            fp16=False,
            condition_on_previous_text=False,
            initial_prompt=current_config['prompt'],
            no_speech_threshold=0.6,       # Abaikan jika sebagian besar noise
            logprob_threshold=-1.0,        # Batas percaya diri model
            compression_ratio_threshold=2.4 # Cegah pengulangan kata
        )
        
        teks_hasil = result["text"].strip()
        
        if os.path.exists(filepath):
            os.remove(filepath)
            
        if not teks_hasil:
            return jsonify({"text": ""})

        return jsonify({"text": teks_hasil})
        
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": str(e)}), 500

# ==========================================
# 4. ENDPOINT LLM UNTUK MERANGKUM NOTULENSI (MoM)
# ==========================================
@app.route('/summarize', methods=['POST'])
def summarize_meeting():
    data = request.json
    raw_text = data.get('text', '')
    
    if not raw_text or len(raw_text) < 10:
        return jsonify({"error": "Teks terlalu pendek untuk dirangkum."}), 400
        
    # PROMPT UPDATE: Memaksa Gemini membuat format TABEL
    prompt_instruksi = f"""
    Kamu adalah asisten sekretaris profesional. Tugasmu mengubah teks transkripsi rapat yang berantakan berikut menjadi Minutes of Meeting (MoM).
    
    Wajib gunakan format Markdown di bawah ini:
    
    ### 📝 MINUTES OF MEETING (MoM)
    **📌 Topik Rapat:** (Tebak topik utama dari pembahasan)
    **💡 Ringkasan:** (Poin-poin singkat)
    
    ### 🎯 Action Items (Delegasi Tugas)
    Buatlah dalam bentuk TABEL dengan kolom berikut. Jika ada info yang tidak disebutkan (misal: deadlinenya tidak ada), tulis saja "Tidak disebutkan" atau tumpuk/gabungkan saja tebakan dari konteks yang ada.
    
    | Siapa (PIC) | Apa (Tugas/Action Item) | Kapan (Deadline) |
    |---|---|---|
    | ... | ... | ... |
    
    ---
    Teks Transkripsi Rapat:
    "{raw_text}"
    """
    
    try:
        response = llm_model.generate_content(prompt_instruksi)
        return jsonify({"summary": response.text})
    except Exception as e:
        return jsonify({"error": "Gagal menghasilkan ringkasan AI."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)