from flask import Flask, render_template, request, jsonify
import whisper
import os
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs('uploads', exist_ok=True)

# 1. State Konfigurasi Global
current_config = {
    "model_size": "small",
    "language": "id",
    "prompt": "Ini adalah rekaman rapat notulensi menggunakan bahasa Indonesia."
}

model = None

# 2. Fungsi dinamis untuk memuat model
def load_whisper_model(size):
    global model
    print(f"\n[SYSTEM] Memuat ulang model Whisper ukuran '{size}'... (Mohon tunggu)")
    model = whisper.load_model(size)
    print(f"[SYSTEM] Model '{size}' berhasil dimuat!\n")

# Load model awal saat server nyala
load_whisper_model(current_config["model_size"])

@app.route('/')
def index():
    return render_template('index.html')

# --- ENDPOINT KONFIGURASI ---
@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(current_config)

@app.route('/api/config', methods=['POST'])
def update_config():
    global current_config
    new_config = request.json
    
    # Jika ukuran model diubah oleh user, muat ulang modelnya
    if new_config.get('model_size') and new_config['model_size'] != current_config['model_size']:
        try:
            load_whisper_model(new_config['model_size'])
        except Exception as e:
            return jsonify({"status": "error", "message": f"Gagal memuat model: {str(e)}"}), 500
            
    # Update konfigurasi saat ini
    current_config.update(new_config)
    return jsonify({"status": "success", "config": current_config})

# --- ENDPOINT TRANSKRIPSI ---
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

    file_size = os.path.getsize(filepath)
    if file_size < 5000:
        print("[DEBUG] PERINGATAN: File sangat kecil.")

    try:
        # 3. Gunakan konfigurasi dinamis saat transkripsi
        result = model.transcribe(
            filepath, 
            language=current_config['language'] if current_config['language'] != 'auto' else None,
            fp16=False,
            condition_on_previous_text=False,
            initial_prompt=current_config['prompt']
        )
        
        teks_hasil = result["text"].strip()
        
        if os.path.exists(filepath):
            os.remove(filepath)
            
        if not teks_hasil:
            return jsonify({"text": "Tidak ada suara yang terdeteksi."})

        return jsonify({"text": teks_hasil})
        
    except Exception as e:
        print(f"[DEBUG] ERROR WHISPER: {str(e)}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)