# PPE Compliance Monitor — MVP

Deteksi kepatuhan APD (Alat Pelindung Diri) dari satu foto area kerja,
menggunakan YOLOv8 yang di-fine-tune pada dataset PPE publik, ditambah
lapisan rule-based untuk menentukan status kepatuhan, tingkat risiko, dan
rekomendasi tindakan per orang.

## Arsitektur

```
Frontend (static HTML/JS, nginx)   -->   Backend (FastAPI)
      upload 1 foto                        |
      tampilkan hasil                      | 1. Decode image
                                            | 2. YOLOv8 inference (sync)
                                            |    - fine-tuned model  -> semua objek/APD
                                            |    - COCO model        -> deteksi Person yang andal
                                            | 3. Rule engine: person <-> PPE association,
                                            |    compliance status, risk scoring
                                            | 4. Draw bounding boxes + encode base64
                                            v
                                      JSON + annotated image
```

Semua proses terjadi dalam **satu request-response sinkron** — tidak ada
job queue, background worker, atau auto-logging pipeline, sesuai batasan
MVP kompetisi.

> Catatan: model PPE hasil fine-tuning sangat kuat mendeteksi helm/rompi/masker
> tetapi lemah pada kelas `Person`. Karena itu backend memakai model COCO
> pretrained (`yolov8n.pt`) hanya untuk deteksi `Person`, lalu menggabungkan
> hasilnya dengan deteksi APD dari model fine-tuned.

## Dataset & Fine-tuning

Model dasar: `yolov8n.pt` (pretrained di COCO), di-fine-tune ke domain PPE
menggunakan **"Construction Site Safety Image Dataset"** (publik, Roboflow
Universe), dengan kelas:

```
Person, Hardhat, NO-Hardhat, Safety Vest, NO-Safety Vest, Mask, NO-Mask
```

Kelas `NO-*` dipakai langsung sebagai sinyal pelanggaran, sehingga rule
engine tidak perlu menebak "APD hilang" — cukup membaca hasil deteksi
eksplisit dari model.

### Cara fine-tuning

```bash
cd backend/training
# 1. Download dataset (format YOLOv8) dari Roboflow Universe,
#    letakkan di backend/training/data/ sehingga ada data.yaml di dalamnya

pip install ultralytics
python train.py --data ./data/data.yaml --epochs 50

# 2. Salin hasil terbaik ke lokasi yang dipakai backend saat runtime
cp runs/detect/ppe_finetune/weights/best.pt ../model/weights/best.pt
```

> Catatan: training dilakukan secara manual/offline selama periode lomba,
> **bukan** dipanggil oleh API saat runtime. Ini menjaga inference path
> tetap statis dan sinkron sesuai ketentuan MVP.

### Mengganti ke domain lain (mis. dapur MBG)

Kalau nanti beralih ke kelas APD dapur (Hairnet, Apron, Sarung Tangan,
dll), yang perlu diubah hanya:
1. Dataset training (`data.yaml` + kelas baru)
2. `PPE_SCHEMA` di `backend/compliance/rules.py`

Arsitektur, API contract, dan frontend tidak perlu berubah.

## Menjalankan

```bash
# pastikan backend/model/weights/best.pt sudah ada (hasil fine-tuning di atas)
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (docs otomatis di `/docs`)

## API Contract

`POST /api/analyze` — multipart form-data, field `image` (file).

Response:

```json
{
  "person_count": 2,
  "results": [
    {
      "person_id": 1,
      "person_bbox": [120.0, 45.0, 310.0, 480.0],
      "detected_ppe": ["Hardhat"],
      "missing_ppe": ["Safety Vest"],
      "compliance_status": "Non-compliant",
      "risk_level": "Medium",
      "recommendation": "Pegawai #1: tidak menggunakan Safety Vest. Segera tegur..."
    }
  ],
  "annotated_image": "data:image/jpeg;base64,..."
}
```

## Struktur Proyek

```
ppe-mvp/
├── docker-compose.yml
├── backend/
│   ├── main.py                 # FastAPI app, single /api/analyze endpoint
│   ├── model/detector.py        # YOLOv8 wrapper (fine-tuned PPE + COCO person)
│   ├── compliance/rules.py      # rule-based compliance + risk scoring
│   ├── training/train.py        # offline fine-tuning script
│   └── model/weights/
│       ├── best.pt              # <- hasil fine-tuning (APD)
│       └── yolov8n.pt           # <- COCO pretrained, untuk deteksi Person
└── frontend/
    ├── index.html / app.js / style.css
```

## Batasan MVP (sesuai ketentuan lomba)

- Input tunggal (1 foto) → output tunggal, tidak ada fitur riwayat/dashboard.
- Backend memproses secara sinkron, tanpa background job / message queue.
- Parameter model statis saat demo (tidak ada auto-tuning saat runtime).
