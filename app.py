from flask import Flask, render_template, request, jsonify
import whisper
import os

# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Pastikan folder 'uploads' ada untuk menyimpan potongan audio
if not os.path.exists('uploads'):
    os.makedirs('uploads')

print("Memuat model AI Whisper... (Tunggu sebentar, ini makan waktu beberapa detik)")
# Catatan Skripsi: Kalau dirasa "base" masih kurang pintar, ubah "base" di bawah ini jadi "small"
model = whisper.load_model("small")
print("Model Whisper berhasil dimuat! Server Flask siap digunakan.")

@app.route('/')
def index():
    # Menampilkan halaman utama (index.html di dalam folder templates)
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    # 1. Cek apakah ada file audio yang dikirim dari browser
    if 'file' not in request.files:
        return jsonify({"error": "Tidak ada file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "File kosong"}), 400
        
    # 2. Simpan potongan audio (chunk) sementara
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        # 3. Proses Transkripsi Anti-Halusinasi
        result = model.transcribe(
            filepath, 
            language='id',
            fp16=False, # Menghilangkan warning warna merah di terminal
            condition_on_previous_text=False, # Mencegah AI mengulang kata halusinasi
            initial_prompt="Ini adalah rekaman rapat notulensi menggunakan bahasa Indonesia."
        )
        
        # 4. Hapus file audio setelah selesai diproses agar laptop tidak penuh
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # 5. Kirim teks hasil terjemahan kembali ke browser
        return jsonify({"text": result["text"].strip()})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Jalankan server
    app.run(debug=True)