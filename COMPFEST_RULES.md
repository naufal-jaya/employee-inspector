# AIC Compfest — Ketentuan Lomba

## Tema

**"AI for the Backbone of the Economy"**

Tema ini bertujuan menggali potensi AI dalam mentransformasi rantai nilai bisnis di Indonesia. Setiap produk melewati tiga tahap utama sebelum sampai ke konsumen: **diproduksi → didistribusikan → dijual**. Di setiap titik tersebut, pelaku industri dan perdagangan Indonesia menghadapi tantangan nyata seperti inefisiensi produksi, tingginya biaya logistik, dan meningkatnya ekspektasi konsumen digital.

Peserta didorong mengembangkan solusi berbasis AI yang mencakup tiga area utama rantai pasok pasca-produksi primer:

1. **Smart Manufacturing** (Pabrik) — penerapan AI di proses pengolahan dan operasi pabrik.
2. **Smart Logistics** (Gudang & Distribusi) — penerapan AI di pergerakan barang.
3. **Smart Commerce** (Toko & Pasar) — penerapan AI di sisi konsumen, sales operasional, serta transaksi komersial.

---

## 1. Ketentuan Produk

- Proyek yang dilombakan merupakan inovasi di bidang AI for Backbone Economy dengan memanfaatkan teknologi Artificial Intelligence.
- Proyek yang dilombakan merupakan karya orisinal tim.
- Proyek yang dilombakan hanya dikerjakan selama perlombaan berlangsung, yaitu pada **17 Juni – 25 Agustus 2026 pukul 23.55 WIB**.
- Proyek yang dikerjakan saat penyisihan **wajib dilanjutkan** sebagai proyek yang dikerjakan saat tahap Final.
- **Dilarang** melanjutkan proyek yang sudah pernah dikerjakan di luar periode penyisihan, baik yang sudah selesai maupun yang belum.

### Batasan Ruang Lingkup MVP

Untuk menjaga fokus pengembangan dan memudahkan proses penilaian reprodusibilitas lokal, ruang lingkup proyek yang dikumpulkan pada tahap penyisihan **WAJIB HANYA SAMPAI** pada batasan berikut:

**1. Frontend (FE) / Antarmuka**
UI wajib hanya berfokus pada alur interaksi inti, yaitu menerima input tunggal dari pengguna dan menampilkan output dari AI. Peserta **tidak perlu** membangun fitur pelengkap seperti dashboard analitik tingkat lanjut, sistem otentikasi yang kompleks, atau halaman riwayat penggunaan.

**2. Backend (BE) & Integrasi**
Arsitektur backend wajib hanya sampai pada pemrosesan interaksi sinkron. Peserta **tidak perlu** mengimplementasikan background jobs, pipeline pencatatan data otomatis (automated data logging), atau infrastruktur database terdistribusi. Fokuskan agar API/sistem lokal dapat dijalankan sesuai panduan di README.md menggunakan `docker compose`.

**3. Model AI & Algoritma**
Implementasi AI wajib hanya berfokus pada fungsionalitas inferensi utama (core inference) dengan parameter yang bersifat statis pada saat demonstrasi berjalan. Peserta **tidak diminta** untuk menyertakan sistem pembaruan otomatis (auto-tuning), skrip pengujian massal (bulk testing scripts), atau mekanisme loop umpan balik otomatis pada repository tahap penyisihan ini.

---

## 2. Ketentuan Deliverables

- Setiap tim diwajibkan untuk melakukan **commit dan push melalui GitHub** ke repository tim yang memiliki visibility **public** setiap membuat perubahan.
- Batas commit dan push terakhir ke repository GitHub yang boleh dilakukan adalah **sebelum 25 Agustus 2026 pukul 23.55 WIB**.
- Deadline pengumpulan semua berkas penyisihan adalah **25 Agustus 2026 pukul 23.55 WIB** dan submisi dilakukan melalui situs **COMPFEST**.
- Dataset yang digunakan boleh berasal dari **sumber publik** yang telah tersedia sebelumnya dan juga boleh dari **data sintetik**. Namun, penggunaan model (baik karya pihak di luar peserta maupun bukan), arsitektur sistem, hingga fitur harus dilakukan dan dijelaskan **bersamaan preprocessing-nya** selama periode lomba.
- Diperbolehkan untuk menggunakan **model API** dan **pre-trained model**. Model **wajib di-fine-tune** sesuai dengan inovasi fitur per tim.

---

## Quick-reference checklist

- [ ] Single input → single AI output flow only (no history page, no advanced dashboard, no complex auth)
- [ ] Backend is synchronous only — no background jobs, no auto-logging pipeline, no distributed DB
- [ ] Runs locally via `docker compose` per README.md instructions
- [ ] Model inference is static at demo time — no auto-tuning, no bulk test scripts, no auto feedback loop in the penyisihan repo
- [ ] Project only built within 17 Jun – 25 Aug 2026 window — no pre-existing/continued outside work
- [ ] Penyisihan project must be continued into Final stage (no swapping projects)
- [ ] GitHub repo is public, with commits/pushes made throughout development
- [ ] Last commit/push before 25 Aug 2026, 23:55 WIB
- [ ] Final submission via COMPFEST site before 25 Aug 2026, 23:55 WIB
- [ ] Dataset: public source or synthetic — documented
- [ ] Any pre-trained model/API used is fine-tuned to the team's specific feature innovation, with preprocessing explained