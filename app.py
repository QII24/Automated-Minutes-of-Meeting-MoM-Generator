from flask import Flask, render_template, request, jsonify
import whisper
import os
import uuid

# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Pastikan folder 'uploads' ada
os.makedirs('uploads', exist_ok=True)

print("Memuat model AI Whisper... (Tunggu sebentar, ini makan waktu beberapa detik)")
# Menggunakan model "small" sesuai kebutuhan skripsimu
model = whisper.load_model("small")
print("Model Whisper berhasil dimuat! Server Flask siap digunakan.")

@app.route('/')
def index():
    # Menampilkan halaman utama
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    # 1. Cek apakah browser mengirim file
    if 'file' not in request.files:
        print("[DEBUG] ERROR: Tidak ada file dari browser!")
        return jsonify({"error": "Tidak ada file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("[DEBUG] ERROR: Nama file kosong!")
        return jsonify({"error": "File kosong"}), 400
        
    # 2. Simpan file audio dengan nama unik agar tidak bentrok
    filename = f"rekaman_{uuid.uuid4().hex}.webm"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 3. Sistem Detektif: Cek ukuran file
    file_size = os.path.getsize(filepath)
    print(f"\n[DEBUG] Audio masuk! Ukuran: {file_size} bytes")
    
    if file_size < 5000:
        print("[DEBUG] PERINGATAN: File sangat kecil, kemungkinan mic tidak merekam suara.")

    try:
        # 4. Proses Transkripsi Anti-Halusinasi
        result = model.transcribe(
            filepath, 
            language='id',
            fp16=False,
            condition_on_previous_text=False,
            initial_prompt="Ini adalah rekaman rapat notulensi menggunakan bahasa Indonesia."
        )
        
        teks_hasil = result["text"].strip()
        print(f"[DEBUG] Hasil AI: '{teks_hasil}'")
        
        # 5. Hapus file audio setelah selesai diproses
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # 6. Kirim hasil kembali ke browser
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