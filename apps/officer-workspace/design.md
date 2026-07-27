# Dokumentasi Reka Bentuk UI/UX — MARA AI-ETC (Officer Workspace)

Dokumen ini merekodkan struktur UI/UX sedia ada secara terperinci (termasuk versi Desktop dan Mobile) hasil daripada analisis kod sumber sebenar di dalam `apps/officer-workspace/` dan dokumen seni [...]

---

## 1. Ringkasan Keseluruhan

Aplikasi **MARA AI-ETC (Officer Workspace)** adalah sebuah Platform AI Agentic bagi pegawai keusahawanan MARA (Majlis Amanah Rakyat) — bukan sebuah chatbot biasa.

Walaupun antaramuka ini digunakan secara langsung oleh Pegawai MARA, **tujuan utama dan nadi kepada seluruh platform ini adalah untuk memberi perkhidmatan dan mempercepatkan pemprosesan permohonan[...]

Aplikasi frontend ini dibina menggunakan **React 19 + TypeScript 5.9**, **Vite 7**, **React Router 7**, **Tailwind CSS 4**, dan sistem reka bentuk **`@openhands/ui`**.

### 1.1 Konteks Domain & Kitaran Hayat Permohonan Usahawan MARA
Sistem ini direka untuk memendekkan kitaran masa pemprosesan permohonan usahawan (dari beberapa hari kepada beberapa jam) melalui automasi tugasan berpengetahuan tinggi (*knowledge-heavy tasks*):
- **Intake & Muat Naik Dokumen Usahawan:** Pegawai memuat naik dokumen yang dihantar oleh usahawan (Kad Pengenalan, Penyata Akaun Bank, Penyata Kewangan Syarikat, Kertas Kerja / Rancangan Perniaga[...]
- **Analisis & Pengekstrakan AI:** Ejen AI mengekstrak angka kewangan, menyemak kelayakan usahawan berdasarkan dasar/polisi MARA, dan menilai risiko perniagaan.
- **Pintu Kawalan Manusia (*Human-in-the-Loop*):** Pegawai menyemak ketepatan analisis AI berbanding dokumen asal usahawan, membuat pembetulan data jika perlu, dan meluluskan atau menolak permohon[...]
- **Penghasilan Laporan Jawatankuasa:** Sistem menjana draf laporan kelulusan pembiayaan usahawan yang lengkap dengan bukti sitasi untuk dibentangkan kepada Jawatankuasa Kelulusan MARA.

### Senarai Halaman (Pages / Routes)

| Route Path | Nama Halaman | Fungsi Utama |
| :--- | :--- | :--- |
| `/login` | **LoginPage** | Gerbang log masuk utama. Menyediakan pilihan log masuk SSO rasmi (Keycloak) dan log masuk pantas mod pembangunan (*mock / dev mode*). |
| `/` | **WorkspacePage** | Ruang kerja utama pegawai yang memaparkan antaramuka dwipanel: senarai tugasan (*Task Panel*) dan ruang sembang interaktif bersama AI Agent (*Chat Panel*) untuk mengana[...]
| `/dashboard` | **DashboardPage** | Pandangan keseluruhan portfolio (*Portfolio Overview*) pembiayaan keusahawanan yang memaparkan metrik utama, statistik aliran kerja aktif, kelulusan tertunda, [...] |
| `/review` | **ReviewConsolePage** | Konsol semakan dan kelulusan (*Human-in-the-Loop Gates*). Tempat pegawai menyemak output ejen AI terhadap fail pemohon usahawan, bukti dokumen (*citations*), [...] |
| `/admin` | **AdminConsolePage** | Konsol pentadbir bagi pengurusan pengguna, peranan, konfigurasi profil ejen AI, dan tetapan sistem. |

---

## 2. Senarai Features

Berikut adalah senarai keseluruhan ciri (*features*) yang terdapat di dalam sistem:

1. **Pengesahan & Kawalan Laluan (*Authentication & Route Guard*):**
   - Menggunakan `oidc-client-ts` untuk pengesahan Keycloak SSO.
   - Komponen `AuthGuard` memantau sesi pengguna dan menguruskan parameter panggilan balik OIDC (`code`/`state`).
   - Sokongan log masuk pantas mod pembangunan (*Mock / Dev Mode*) melalui simpanan `sessionStorage`.
2. **Navigasi Sisi Tetap (*Sidebar Navigation*):**
   - Navigasi ke 4 modul utama (Workspace, Dashboard, Review Console, Admin Console) beserta paparan peranan pengguna dan butang log keluar.
3. **Ruang Kerja Interaktif (*AI Workspace - Chat & Tasks*):**
   - **Task Panel:** Senarai tugasan pemprosesan usahawan semasa, ditapis mengikut status dengan penunjuk cip (*active* dan *awaiting approval*).
   - **Chat Panel:** Sembang interaktif bersama ejen AI untuk mengarahkan tugasan baru (cth: *"Assess the loan application from Ahmad bin Abdullah"*) atau menyemak analisis dokumen usahawan.
4. **Metrik & Statistik Portfolio Usahawan (*Dashboard Stats & Monitoring*):**
... (file truncated for brevity in this commit)
