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
> pretrained (`yolov8s.pt`) untuk deteksi `Person` (threshold lebih rendah,
> `PERSON_CONFIDENCE=0.3`, agar orang dari samping/belakang/terhalang tetap
> tertangkap), lalu menggabungkan hasilnya dengan deteksi APD dari model
> fine-tuned. Model person bisa diganti lewat env `PERSON_MODEL_PATH`
> (mis. `yolov8n.pt` untuk lebih cepat, `yolov8m.pt` untuk lebih akurat).

## Dataset & Fine-tuning

Model dasar: `yolov8n.pt` (pretrained di COCO), di-fine-tune ke domain PPE
menggunakan **"Construction Site Safety Image Dataset"** (publik, Roboflow
Universe), dengan kelas:

```
Person, Hardhat, NO-Hardhat, Safety Vest, NO-Safety Vest, Mask, NO-Mask
```

Kelas `NO-*` dipakai sebagai sinyal pelanggaran eksplisit: jika model
mendeteksi `NO-Hardhat` di seorang worker, item itu langsung dianggap
missing (dan sinyal negatif selalu menang atas positif). Untuk item
**kritis** (`Hardhat`), kalau tidak ada bukti sama sekali (tidak terdeteksi
`Hardhat` maupun `NO-Hardhat`), item tetap dianggap missing — "tidak ada
bukti memakai = dianggap tidak memakai" — agar worker tanpa APD tidak
kepalang di-mark "Compliant" hanya karena model gagal melihatnya. Item
non-kritis (Mask, Safety Vest) tanpa sinyal dibiarkan netral supaya tidak
menuduh tanpa bukti.

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

`POST /api/analyze` — multipart form-data, field `image` (file, maksimal 25 MB, format JPEG/PNG/WebP; EXIF orientation otomatis dikoreksi).

Response:

```json
{
  "summary": {
    "total_objects": 5,
    "person_count": 2,
    "compliant_persons": 1,
    "safety_score": 50.0,
    "violations_count": 1
  },
  "all_objects": [
    {
      "class_name": "Person",
      "confidence": 0.91,
      "confidence_percent": "91.0%",
      "bbox": [120.0, 45.0, 310.0, 480.0],
      "category": "person"
    }
  ],
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

- `category` tiap objek: `person` | `compliant_ppe` | `hazard` (Fall-Detected / kelas `NO-*`) | `equipment`.
- `risk_level`: `Low` (APD lengkap), `Medium` (1 item non-kritis hilang), `High` (Hardhat hilang atau ≥2 item hilang).
- Error: `400` (bukan gambar / tidak bisa di-decode / melebihi 25 MB), `503` (model belum dimuat).

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
│       └── yolov8s.pt           # <- COCO pretrained, untuk deteksi Person
└── frontend/
    ├── index.html / app.js / style.css
```

## Batasan MVP (sesuai ketentuan lomba)

- Input tunggal (1 foto) → output tunggal, tidak ada fitur riwayat/dashboard.
- Backend memproses secara sinkron, tanpa background job / message queue.
- Parameter model statis saat demo (tidak ada auto-tuning saat runtime).
