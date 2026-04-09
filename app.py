from flask import Flask, render_template, request, jsonify
import whisper
import os

# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Pastikan folder 'uploads' ada untuk menyimpan file audio rekaman sementara
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Load model Whisper (Base) sekali di awal agar transkripsi selanjutnya lebih cepat
print("Memuat model Whisper... (Proses ini mungkin memakan waktu beberapa detik)")
model = whisper.load_model("base")
print("Model Whisper berhasil dimuat!")

@app.route('/')
def index():
    # Mengarahkan user ke tampilan utama (UI)
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    # 1. Validasi apakah ada file audio yang diterima dari browser
    if 'file' not in request.files:
        return jsonify({"error": "Tidak ada file yang diunggah"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "File tidak dipilih"}), 400
        
    # 2. Simpan file audio (dari microphone) ke folder uploads
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        # 3. Proses transkripsi menggunakan Whisper
        # PENTING: Kunci language='id' agar tidak halusinasi menjadi huruf Jepang/Mandarin
        # jika ada suara hening (silence) atau noise dari microphone
        result = model.transcribe(filepath, language='id')
        
        # 4. Kirim teks hasilnya kembali ke browser
        return jsonify({"text": result["text"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Menjalankan server pada port 5000
    app.run(debug=True)