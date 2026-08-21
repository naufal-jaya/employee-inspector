# SafeIndustrial — PPE Compliance Monitor (Pose-Aware)

Deteksi kepatuhan APD (Alat Pelindung Diri) dari **satu foto / satu frame**
area kerja konstruksi, menggunakan YOLOv8 yang di-fine-tune plus model pose,
dengan **verifikasi berbasis keypoint** untuk memastikan APD benar-benar
*dipakai* (bukan hanya dibawa), deteksi *fall* (jatuh), dan skoring dampak
ekonomi. Satu request masuk → satu hasil keluar, sinkron, sesuai batasan MVP
kompetisi.

> Proyek ini dikembangkan untuk **COMPFEST AI Innovation Challenge 2026** —
> tema *"AI for the Backbone of the Economy"*, area **Smart Manufacturing**
> (keselamatan kerja). Seluruh pekerjaan dilakukan selama periode lomba
> (17 Juni – 25 Agustus 2026).

## Arsitektur

```
Frontend (static HTML/JS, nginx)          -->   Backend (FastAPI)
  • Tab Image     (upload 1 foto)                 1. Decode image
  • Tab Video     (upload 1 video)                2. YOLOv8-pose  : persons + 17 keypoints
  • Tab Live Cam  (getUserMedia, auto ~1 detik)   3. YOLOv8 (fine-tuned) : PPE objects
      │                                              Hardhat, Safety Vest, Person
      │ POST /api/analyze | /api/analyze-video       4. Pose verification: worn vs carried
      ▼                                              5. Fall detection (shoulder→hip vector)
  JSON + annotated image/video                      6. Compliance + risk + economic scoring
      │                                             7. Draw boxes + encode
      ▼                                          JSON + annotated image/video
```

Semua proses terjadi dalam **satu request-response sinkron** — tidak ada job
queue, background worker, streaming, atau auto-logging, sesuai batasan MVP
kompetisi. Tab *Live Camera* menganalisis otomatis (±1 detik) dan menggambar
box langsung di feed, namun tiap request tetap satu frame ke endpoint yang
sama (sinkron & stateless).

## Inovasi (pembeda dari deteksi APD konvensional)

1. **Pose-aware PPE verification** — alih-alih hanya mendeteksi "ada helm",
   sistem memverifikasi helm **dipakai di kepala** (dekat keypoint hidung/
   telinga) dan rompi **dipakai di torso** (dekat bahu/pinggul). Helm yang
   terdeteksi tapi digendong di tangan masuk kategori `carried` dan dihitung
   sebagai pelanggaran.
2. **Fallback aman (`uncertain`)** — jika keypoint tidak dapat diandalkan
   (pekerja membelakangi kamera, jarak jauh, keypoint confidence rendah),
   sistem tidak pernah menuduh secara salah: verifikasi ditandai `uncertain`
   dan memakai logika penampakan lama.
3. **Deteksi jatuh (Fall-Detected)** — berdasarkan orientasi vektor
   bahu→pinggul (bukan rasio aspek box, yang rawan salah-positif), sehingga
   pekerja yang jatuh/tergeletak ditandai sebagai hazard.
4. **Economic risk scoring** — skor risiko 0–100 yang merangkum pelanggaran
   dan hazard menjadi satu angka, memperkuat narasi dampak ekonomi
   (*"Backbone of the Economy"*) tanpa klaim angka finansial yang berlebihan.

## Dataset & Fine-tuning

**Model dasar (person/pose):** `yolov8n-pose.pt` (COCO, 17 keypoint) — model
pretrained yang dipakai untuk mendeteksi orang + keypoint. Tidak di-fine-tune.

**Model APD (fine-tuned):** `best.pt`, di-fine-tune dari `yolov8n.pt`
(pretrained COCO) ke domain APD konstruksi memakai dataset publik **"worker"**
(Roboflow Universe, `safetyeyefinetuningdata/worker-6qxik`, v2, lisensi
CC BY 4.0 — 8.551 gambar):

```
nc: 3
names: ['Hardhat', 'Safety Vest', 'Person']
```

**Preprocessing dataset (dilakukan di Roboflow):**
- Auto-orientation (pembuangan orientasi EXIF)
- Resize ke 640×640 (stretch)
- Augmentasi: flip horizontal/vertikal (50%), rotasi 90° searah, crop acak
  0–30%, rotasi acak ±15°, brightness ±20%, Gaussian blur 0–2.5px,
  salt & pepper ~2%.

**Cara fine-tuning (offline, selama lomba):**

```bash
cd backend/training
# Pastikan backend/training/data/data.yaml (format YOLOv8) tersedia
pip install ultralytics
python train.py --data ./data/data.yaml --epochs 100 --imgsz 640

# Salin hasil terbaik ke lokasi yang dipakai backend saat runtime
cp runs/detect/ppe_finetune/weights/best.pt ../model/weights/best.pt
```

> Training dijalankan manual/offline, **bukan** dipanggil API saat runtime.
> Inference tetap memakai parameter statis sesuai ketentuan MVP.
> `auto_annotate.py` (di `backend/training/`) dipakai saat pengembangan untuk
> auto-labeling / balancing dataset; tidak dipanggil saat runtime.

### Mengganti ke domain lain (mis. food-hygiene / gudang)

Karena mesin verifikasi bersifat **domain-agnostic**, yang perlu diubah hanya:
1. Dataset training (`data.yaml` + kelas baru) lalu retrain `best.pt`.
2. `PPE_SCHEMA` dan `PPE_BODY_REGION` di `backend/compliance/rules.py`
   (peta kelas APD → region tubuh, mis. `Hairnet → head`, `Apron → torso`).

Arsitektur, API contract, verifikasi pose, dan frontend tidak berubah.

## Menjalankan

```bash
# Build memerlukan internet (menarik base image + instal dependencies
# pip/apt). Setelah container terbentuk, runtime berjalan OFFLINE:
# semua model weights sudah ter-commit, tidak ada unduhan saat startup.
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (docs otomatis di `/docs`)

## API Contract

### `POST /api/analyze` — analisis satu gambar

Multipart form-data, field `image` (file). Query param opsional `light=true`
mengabaikan `annotated_image` base64 agar lebih cepat (frontend menggambar
box sendiri dari JSON).

Response:

```json
{
  "summary": {
    "total_objects": 5,
    "person_count": 2,
    "compliant_persons": 1,
    "safety_score": 50.0,
    "violations_count": 1,
    "hazard_count": 1,
    "risk_score": 45.0
  },
  "hazards": [
    { "class_name": "Fall-Detected", "confidence": 0.9, "bbox": [10, 20, 200, 300] }
  ],
  "all_objects": [
    { "class_name": "Hardhat", "confidence": 0.92, "confidence_percent": "92.0%",
      "bbox": [120, 45, 310, 480], "category": "compliant_ppe" }
  ],
  "results": [
    {
      "person_id": 1,
      "track_id": -1,
      "person_bbox": [120, 45, 310, 480],
      "person_confidence": 0.95,
      "detected_ppe": ["Safety Vest"],
      "worn_ppe": ["Safety Vest"],
      "carried_ppe": ["Hardhat"],
      "missing_ppe": ["Hardhat"],
      "compliance_status": "Non-compliant",
      "risk_level": "High",
      "verification": "carried",
      "recommendation": "Pegawai #1: tidak menggunakan Hardhat (dibawa tapi tidak dipakai: Hardhat). Segera tegur..."
    }
  ],
  "annotated_image": "data:image/jpeg;base64,..."
}
```

### `POST /api/analyze-video` — analisis video (per-frame + tracking)

Multipart form-data, field `video`. Mengembalikan **dua video** hasil anotasi
(H.264) dengan tingkat kepercayaan berbeda, serta `temporal_summary` agregasi
per `track_id` (detik patuh/melanggar, laju kepatuhan, pelanggaran utama).
Tetap satu input → satu output yang sinkron & stateless, sesuai batasan MVP.

Response:

```json
{
  "video_url_high_conf": "/api/video/<uuid>_high.mp4",
  "video_url_low_conf": "/api/video/<uuid>_low.mp4",
  "fps": 25.0,
  "temporal_summary": [
    {
      "track_id": 1,
      "total_seconds_visible": 10.5,
      "compliant_seconds": 8.0,
      "violation_seconds": 2.5,
      "compliance_rate": 76.2,
      "primary_violation": "Hardhat"
    }
  ]
}
```

- `video_url_high_conf`: video anotasi dengan filter kepercayaan tinggi (≥50%)
  — hanya deteksi yang sangat yakin, cocok untuk laporan final.
- `video_url_low_conf`: video anotasi dengan sensitivitas penuh (≥20%)
  — menampilkan semua deteksi termasuk yang kurang yakin, cocok untuk review.

### `GET /health` — status model

```json
{ "status": "ok", "model_loaded": true }
```

## Struktur Proyek

```
employee-inspector/
├── docker-compose.yml
├── backend/
│   ├── main.py                  # FastAPI: /api/analyze, /api/analyze-video
│   ├── model/
│   │   ├── detector.py          # dual model (pose + PPE), fall detection
│   │   └── weights/             # best.pt, yolov8n.pt, yolov8n-pose.pt (committed)
│   ├── compliance/
│   │   ├── rules.py             # worn/carried/uncertain + implicit deduction
│   │   └── economics.py         # risk score 0-100
│   ├── training/                # train.py, dataset worker (3 kelas)
│   └── tests/                   # unit test geometri pose & ekonomi
└── frontend/
    ├── index.html / app.js / style.css / nginx.conf
```

## Batasan MVP (sesuai ketentuan lomba)

- Frontend: input tunggal → output AI (1 foto, 1 video, atau frame webcam
  — tab Live Camera menganalisis otomatis ±1 detik, tetap satu frame per
  request). Tanpa dashboard lanjutan, otentikasi, atau halaman riwayat.
- Backend: pemrosesan sinkron, tanpa background job / message queue /
  pipeline logging otomatis.
- Model: parameter statis saat demo (tanpa auto-tuning / feedback loop).
- Reproduksibilitas: seluruh model weights ter-commit sehingga **runtime
  berjalan offline** (tidak ada unduhan saat startup). Build image
  membutuhkan internet untuk instalasi dependencies.
