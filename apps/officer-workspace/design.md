# Dokumentasi Reka Bentuk UI/UX — MARA AI-ETC (Officer Workspace)

Dokumen ini merekodkan struktur UI/UX sedia ada secara terperinci (termasuk versi Desktop dan Mobile) hasil daripada analisis kod sumber sebenar di dalam `apps/officer-workspace/` dan dokumen seni bina sistem. Dokumen ini bertujuan untuk dijadikan panduan dan rujukan rasmi bagi proses redesign menggunakan antaramuka moden (seperti `@openhands/ui` atau sistem reka bentuk lain), dengan mematuhi sepenuhnya segala batasan dan peraturan yang ditetapkan dalam `AGENTS.md`.

---

## 1. Ringkasan Keseluruhan

Aplikasi **MARA AI-ETC (Officer Workspace)** adalah sebuah Platform AI Agentic bagi pegawai keusahawanan MARA (Majlis Amanah Rakyat) — bukan sebuah chatbot biasa. 

Walaupun antaramuka ini digunakan secara langsung oleh Pegawai MARA, **tujuan utama dan nadi kepada seluruh platform ini adalah untuk memberi perkhidmatan dan mempercepatkan pemprosesan permohonan Usahawan MARA** (seperti pinjaman perniagaan, geran keusahawanan, pembiayaan projek, dan bimbingan korporat). Pegawai memuat naik dokumen pemohon usahawan, AI agents melakukan pengekstrakan/analisis/draf, dan pegawai manusia membuat keputusan kelulusan, penolakan, atau pembetulan pada pintu kawalan (*human-in-the-loop gates*).

Aplikasi frontend ini dibina menggunakan **React 19 + TypeScript 5.9**, **Vite 7**, **React Router 7**, **Tailwind CSS 4**, dan sistem reka bentuk **`@openhands/ui`**.

### 1.1 Konteks Domain & Kitaran Hayat Permohonan Usahawan MARA
Sistem ini direka untuk memendekkan kitaran masa pemprosesan permohonan usahawan (dari beberapa hari kepada beberapa jam) melalui automasi tugasan berpengetahuan tinggi (*knowledge-heavy tasks*):
- **Intake & Muat Naik Dokumen Usahawan:** Pegawai memuat naik dokumen yang dihantar oleh usahawan (Kad Pengenalan, Penyata Akaun Bank, Penyata Kewangan Syarikat, Kertas Kerja / Rancangan Perniagaan).
- **Analisis & Pengekstrakan AI:** Ejen AI mengekstrak angka kewangan, menyemak kelayakan usahawan berdasarkan dasar/polisi MARA, dan menilai risiko perniagaan.
- **Pintu Kawalan Manusia (*Human-in-the-Loop*):** Pegawai menyemak ketepatan analisis AI berbanding dokumen asal usahawan, membuat pembetulan data jika perlu, dan meluluskan atau menolak permohonan.
- **Penghasilan Laporan Jawatankuasa:** Sistem menjana draf laporan kelulusan pembiayaan usahawan yang lengkap dengan bukti sitasi untuk dibentangkan kepada Jawatankuasa Kelulusan MARA.

### Senarai Halaman (Pages / Routes)

| Route Path | Nama Halaman | Fungsi Utama |
| :--- | :--- | :--- |
| `/login` | **LoginPage** | Gerbang log masuk utama. Menyediakan pilihan log masuk SSO rasmi (Keycloak) dan log masuk pantas mod pembangunan (*mock / dev mode*). |
| `/` | **WorkspacePage** | Ruang kerja utama pegawai yang memaparkan antaramuka dwipanel: senarai tugasan (*Task Panel*) dan ruang sembang interaktif bersama AI Agent (*Chat Panel*) untuk menganalisa fail usahawan. |
| `/dashboard` | **DashboardPage** | Pandangan keseluruhan portfolio (*Portfolio Overview*) pembiayaan keusahawanan yang memaparkan metrik utama, statistik aliran kerja aktif, kelulusan tertunda, bendera risiko, dan prestasi ejen AI. |
| `/review` | **ReviewConsolePage** | Konsol semakan dan kelulusan (*Human-in-the-Loop Gates*). Tempat pegawai menyemak output ejen AI terhadap fail pemohon usahawan, bukti dokumen (*citations*), dan membuat keputusan (*Approve / Reject / Correct*). |
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
   - 5 kad statistik utama: Total Workflows, Active Workflows, Pending Approval, Blocked Workflows, dan Risk Flags.
   - **Active Workflows List:** Senarai ringkas aliran kerja pemohon usahawan yang sedang berjalan atau menunggu kelulusan.
   - **Pending Summary:** Ringkasan tugasan tertunda beserta masa, ejen bertugas, dan pegawai yang dipertanggungjawabkan.
   - **Risk Flags Summary:** Pemantauan risiko perniagaan/kredit usahawan mengikut tahap keseriusan (*low, medium, high, critical*).
   - **Agent Performance Table:** Pemantauan metrik operasi ejen AI (latensi, kos, keyakinan purata, jumlah diproses).
5. **Konsol Semakan & Pintu Kelulusan (*Human-in-the-Loop Review Console*):**
   - Penapisan semakan berasaskan tab (*Pending* vs *Resolved*).
   - **Low Confidence Warning:** Amaran automatik untuk medan berskor keyakinan rendah (`< 85%`) bagi mencegah kesalahan kelulusan data usahawan.
   - **Extracted Fields Preview:** Paparan medan yang diekstrak dengan penunjuk sumber (*OCR / PDF Text Layer*) dan skor keyakinan berserta warna.
   - **Citations & Region Tracking:** Rujukan terus ke ID dokumen usahawan, nombor halaman, dan koordinat kotak sempadan (*bounding box*).
   - **Tindakan Kelulusan 3-Cabang:** Sokongan untuk *Approve*, *Reject* (wajib alasan), dan *Correct*.
   - **Correction Form:** Modul pembetulan data di mana nilai asal ejen dipertahankan secara berasingan sementara nilai baru pegawai disimpan sebagai rekod bertribut demi integriti audit.
6. **Konsol Pentadbiran Sistem (*Admin Console*):**
   - **User Management Tab:** Jadual pengurusan pengguna (Pegawai MARA), peranan, cawangan, status MFA, dan log masuk terakhir.
   - **Role Config Tab:** Paparan kad peranan, bilangan keahlian, dan hak akses (*grants*).
   - **Agent Config Tab:** Konfigurasi profil ejen AI, tahap autonomi (*Bounded, Guided, Exploratory*), model LLM (*Haiku, Sonnet, Opus*), dan kebenaran rangkaian.
   - **System Settings Tab:** Konfigurasi parameter sistem (pembatas kadar, had kos, penjejakan audit, mod penyelenggaraan).

### 2.1 Peranan 7 Ejen AI Dalam Penilaian Usahawan MARA
Sistem ini beroperasi dengan tenaga kerja 7 Ejen AI khusus (*True Agents*) yang berkolaborasi dalam menilai permohonan usahawan:
1. **Document Agent:** Pakar pengekstrakan maklumat dari fail berstruktur/tidak berstruktur yang dihantar usahawan (IC, penyata bank, resit, laporan kewangan).
2. **Compliance Agent:** Pakar semakan pematuhan syarat kelayakan MARA (cth: taraf bumiputera, had umur, pendaftaran SSM, pematuhan garis panduan pembiayaan).
3. **Finance Agent:** Pakar analisis penyata kewangan usahawan, mengira nisbah kecairan, aliran tunai (*cash flow*), dan kemampuan bayaran balik pinjaman.
4. **Risk Agent:** Pakar penilaian risiko kredit, risiko pasaran, dan pengesanan amaran awal (*red flags*) dalam perniagaan usahawan.
5. **Market Agent:** Pakar kajian viabiliti industri dan pasaran perniagaan yang dijalankan oleh usahawan.
6. **Recommendation Agent:** Menyintesiskan temuan dari semua ejen untuk menghasilkan draf cadangan kelulusan/penolakan pinjaman/geran berserta sitasi bukti.
7. **Planner Agent:** Mengurus dan merancang urutan langkah kerja pemprosesan permohonan mengikut templat standard MARA.

---

## 3. Fungsi Setiap Button/Action

Jadual di bawah merekodkan setiap elemen interaktif yang wujud di dalam kod sumber:

| Nama / Label Button | Lokasi (Page / Component) | Apa Yang Berlaku Bila Diklik | Versi Paparan |
| :--- | :--- | :--- | :--- |
| **⚡ Log Masuk Pegawai (Mod Pembangunan / Mock)** | `LoginPage.tsx` | Memanggil `loginMock()` — mencipta sesi pegawai mock di `sessionStorage` dan navigasi ke `/`. | Desktop & Mobile |
| **Sign in with SSO (Keycloak Server)** | `LoginPage.tsx` | Memanggil `login()` — melencongkan penyemak imbas ke server Keycloak SSO rasmi. | Desktop & Mobile |
| **Workspace / Dashboard / Review / Admin** | `AppLayout.tsx` | Navigasi laluan React Router (`<NavLink>`) ke modul yang dipilih. | Desktop & Mobile |
| **Logout** | `AppLayout.tsx` | Memanggil `logout()` — memadam sesi mock (jika di mod dev) atau melog keluar dari Keycloak SSO dan kembali ke `/login`. | Desktop & Mobile |
| **Task Item Click** | `TaskPanel.tsx` | *Interaksi item tugasan.* Buat masa ini statik/placeholder untuk memilih atau membuka perincian tugas pemprosesan fail usahawan. | Desktop & Mobile |
| **Send (Chat Button)** | `ChatPanel.tsx` | Menghantar mesej arahan pegawai kepada AI Agent (buat masa ini statik dengan data mock). | Desktop & Mobile |
| **Enter (Input KeyDown)** | `ChatPanel.tsx` | Halangan penghantaran baris baru jika *Enter* ditekan tanpa *Shift*, sebagai persiapan hantar mesej. | Desktop & Mobile |
| **Tab: Pending / Resolved** | `ReviewConsolePage.tsx` | Menukar tab penapisan permintaan kelulusan (`<Tabs.Item>`). | Desktop & Mobile |
| **View source document →** | `FieldPreview.tsx` | Butang pautan untuk membuka dokumen asal usahawan berdasarkan sitasi halaman & *bounding box* (⚠️ *perlu sambungan ke pemapar PDF*). | Desktop & Mobile |
| **Approve** | `ApprovalCard.tsx` | Memanggil `handleApprove()` — menukar status kepada `'approved'` berserta alasan (jika ada). | Desktop & Mobile |
| **Reject** | `ApprovalCard.tsx` | Memanggil `handleReject()` — menukar status kepada `'rejected'` (alasan adalah wajib mengikut spesifikasi). | Desktop & Mobile |
| **Correct** | `ApprovalCard.tsx` | Memanggil `setShowCorrection(true)` — menukarkan paparan kad kepada borang pembetulan (`CorrectionForm`). | Desktop & Mobile |
| **Submit Corrections** | `CorrectionForm.tsx` | Memanggil `handleSubmit()` — merekodkan senarai medan yang diubah (`FieldCorrection[]`) dan menukar status kepada `'corrected'`. | Desktop & Mobile |
| **Cancel** | `CorrectionForm.tsx` | Memanggil `onCancel()` — menutup borang pembetulan dan kembali ke paparan tindakan asal. | Desktop & Mobile |
| **Tab: Users / Roles / Agents / Settings** | `AdminConsolePage.tsx` | Menukar paparan modul pentadbiran sistem (`<Tabs.Item>`). | Desktop & Mobile |

> *Nota: Semua butang wujud di kedua-dua paparan Desktop dan Mobile kerana tiada elemen yang disembunyikan menggunakan kelas responsive (`hidden / block`).*

---

## 4. Layout & Struktur Visual (Desktop)

Secara keseluruhan, aplikasi ini dibina dengan susunan **Fixed Sidebar + Topbar + Main Content Area**:

```
+-----------------------------------------------------------------------+
|  SIDEBAR (w-56, Fixed)  |  HEADER (Topbar - Title & Subtitle)         |
|  - Brand Logo / Title   +---------------------------------------------+
|  - NavLinks (4 modul)   |  MAIN CONTENT AREA (flex-1, overflow-auto)  |
|  - Footer / Logout      |  - Module Specific Content (Grid / Flex)    |
+-----------------------------------------------------------------------+
```

### Hierarki Komponen (*Parent-Child Hierarchy*)

1. **LoginPage (`/login`):**
   - Standalone flex container (`min-h-screen items-center justify-center`).
   - `Card (max-w-md)` -> Header Title -> Description -> Action Buttons -> Milestone Footer.
2. **WorkspacePage (`/`):**
   - `AppLayout` -> `Flex Container (gap-4, h-full)`
     - `TaskPanel (aside w-72)` -> Status Chips -> `Scrollable` -> `TaskItem[]`
     - `ChatPanel (flex-1)` -> Header -> `Scrollable (MessageBubble[])` -> Bottom Input Bar
3. **DashboardPage (`/dashboard`):**
   - `AppLayout` -> `Space-Y-6 Container`
     - `Grid (grid-cols-5)` -> `StatCard` (x5)
     - `Grid (grid-cols-2)` -> `WorkflowList` | `PendingSummary` (Approvals + Risk Flags)
     - `AgentMetrics` -> Performance Table
4. **ReviewConsolePage (`/review`):**
   - `AppLayout` -> Pending Count Chip -> `Tabs` (Pending / Resolved)
     - `ApprovalCard[]` -> Header Info -> Question Box -> Confidence Warning Chip -> `FieldPreview[]` -> Divider -> Action Buttons / `CorrectionForm`
5. **AdminConsolePage (`/admin`):**
   - `AppLayout` -> `Tabs` (Users / Roles / Agents / System Settings)
     - `UserManagementTab` (Table) | `RoleConfigTab` (Card Grid) | `AgentConfigTab` (Card Grid) | `SystemSettingsTab` (List)

---

## 5. Layout & Struktur Visual (Mobile)

### Hasil Analisis Kod Sebenars (*Actual Codebase Analysis*)
Semakan mendalam terhadap keseluruhan kod sumber dalam `apps/officer-workspace/src/**` mendapati bahawa aplikasi ini dibangunkan mengikut paradigma **Desktop-First / Fixed Layout** semasa Milestone 0. 

- **Tiada Breakpoint Responsive:** Tiada penggunaan awalan kelas responsive Tailwind (seperti `sm:`, `md:`, `lg:`, `xl:`) pada mana-mana komponen susun atur, jadual, atau grid.
- **Tiada Komponen Khusus Mobile:** Tiada implementasi *Hamburger Menu*, *Bottom Navigation Bar*, *Off-canvas Drawer*, atau *Collapsible Sidebar*.
- **Kesan Terhadap Skrin Kecil:**
  1. **Sidebar (`AppLayout`):** Kekal selebar `w-56` (224px) di sebelah kiri, memakan ruang skrin mobile secara kekal.
  2. **Grid Dashboard (`grid-cols-5` & `grid-cols-2`):** Memaksa 5 kad statistik dan 2 kolum senarai dimampatkan (*squished*) ke dalam lebar skrin yang kecil atau melimpah secara mendatar (*horizontal overflow*).
  3. **Jadual Data (`overflow-x-auto`):** Jadual di *Agent Performance* dan *User Management* memerlukan skrol mendatar secara manual.
  4. **Workspace (`TaskPanel`):** Kekal selebar `w-72` di sebelah kiri ChatPanel, menyebabkan ruang sembang menjadi teramat sempit.

### Cadangan Adaptasi untuk Redesign
Bagi mematuhi amalan terbaik UI/UX moden tanpa melanggar `AGENTS.md`, fasa redesign perlu memperkenalkan reka bentuk responsif berikut:
- **< 768px (Mobile / Portrait Tablet):**
  - Tukarkan Sidebar tetap (`w-56`) kepada **Bottom Navigation Bar** atau **Hamburger Drawer Menu**.
  - Tukarkan `grid-cols-5` (Stat Cards) dan `grid-cols-2` (Dashboard) kepada **`grid-cols-1`** (susunan vertikal).
  - Dalam **Workspace**, gunakan sistem tab atau *toggle* untuk bertukar antara *Task List* dan *Chat Panel*, bukan memaparkannya bersebelahan.
  - Tukarkan jadual lebar kepada struktur **Card List / Stacked Cards**.

---

## 6. Pages

Terdapat tepat **5 halaman utama** di dalam projek ini:

| Nama Page | Route Path | Fungsi Utama | Komponen Utama | Paparan Desktop vs Mobile (Sedia Ada) |
| :--- | :--- | :--- | :--- | :--- |
| **LoginPage** | `/login` | Pengesahan pegawai (Keycloak SSO / Mock Dev). | `login`, `loginMock` | Center card. Di mobile, kad memenuhi ruang dengan padding `p-4`. |
| **WorkspacePage** | `/` | Ruang kerja interaktif pegawai memproses fail usahawan (Chat AI + Tugas). | `AppLayout`, `TaskPanel`, `ChatPanel` | Dwipanel bersebelahan. Di mobile, terhimpit secara mendatar (*needs mobile tab/drawer*). |
| **DashboardPage** | `/dashboard` | Pemantauan portfolio pembiayaan usahawan & prestasi ejen. | `StatCard`, `WorkflowList`, `PendingSummary`, `AgentMetrics` | Grid 5 kolum & 2 kolum. Di mobile, kad terhimpit atau skrol mendatar. |
| **ReviewConsolePage** | `/review` | Semakan output ejen terhadap fail usahawan & keputusan HIL. | `Tabs`, `ApprovalCard`, `FieldPreview`, `CorrectionForm` | Senarai kad vertikal. Di mobile, butang tindakan terhimpit dalam satu baris. |
| **AdminConsolePage** | `/admin` | Pengurusan pengguna, peranan, ejen AI & sistem. | `Tabs`, `UserManagementTab`, `RoleConfigTab`, etc. | Tab berbilang modul dengan jadual/grid. Di mobile, jadual memerlukan skrol mendatar. |

---

## 7. Dashboard(s)

Terdapat **1 Dashboard utama** (`DashboardPage` di `/dashboard`).

- **Tujuan / Fungsi:** Memberikan gambaran keseluruhan (*Portfolio Overview*) mengenai status permohonan pembiayaan/geran usahawan yang diproses oleh AI, bilangan kelulusan yang menunggu tindakan pegawai manusia, bendera risiko perniagaan usahawan, dan kesihatan/prestasi operasi ejen AI.
- **Pengguna Sasaran:** Pegawai Keusahawanan MARA, Penyelia Pegawai, dan Pengurus Cawangan/Negeri yang memantau throughput portfolio.
- **Tingkah Laku Paparan (Desktop vs Mobile):**
  - Di **Desktop**: Dipaparkan secara teratur dengan 5 kad statistik di baris atas, diikuti oleh grid 2 kolum (Aliran Kerja Aktif di kiri, Ringkasan Tertunda & Risiko di kanan), dan jadual prestasi ejen di bahagian bawah.
  - Di **Mobile**: Oleh kerana ketiadaan media queries (`grid-cols-1`), susunan 5 kolum dan 2 kolum ini dikekalkan, menyebabkan kandungan terhimpit (*squished*). Dalam fasa redesign, ia wajar ditukarkan kepada susunan satu kolum bersusun vertikal.

---

## 8. Workspace — Content Breakdown

Modul Workspace (`/`) adalah tempat pegawai berinteraksi dengan AI untuk menguruskan fail permohonan usahawan:

| Nama Seksyen / Widget | Jenis | Fungsi | Catatan Redesign / Versi Mobile |
| :--- | :--- | :--- | :--- |
| **Task Panel** | Sidebar List (`aside w-72`) | Memaparkan senarai tugas pemprosesan fail usahawan. Dilengkapi penunjuk cip status (*active / awaiting*). Setiap item memaparkan tajuk permohonan, cip status, nama ejen, dan masa. | Di mobile, lebar tetap 72 (288px) memakan hampir seluruh skrin. Wajar diubah menjadi *slide-over drawer* atau *collapsible panel*. |
| **Chat Panel** | Interactive Chat Bar (`flex-1`) | Ruang sembang bersama AI Agent untuk mengarahkan penilaian kelayakan pinjaman/geran usahawan. Memaparkan gelembung mesej (`MessageBubble`), dan bar input di bawah. | Di mobile, perlu mengambil alih 100% lebar skrin apabila aktif. |

---

## 9. Dashboard — Content Breakdown

| Nama Widget / Card | Jenis | Data yang Dipaparkan | Fungsi | Versi Mobile / Redesign |
| :--- | :--- | :--- | :--- | :--- |
| **StatCards (x5)** | Numeric Cards | Total Workflows, Active Workflows, Pending Approval, Blocked Workflows, Risk Flags. | Memberikan status metrik pantas portfolio usahawan dengan warna amaran (*warning/danger*). | Wajar ditukarkan kepada grid 2 kolum atau 1 kolum di skrin kecil. |
| **WorkflowList** | List / Table view | Tajuk workflow, nama pemohon (Usahawan), peringkat (*stage*), ejen ditugaskan, dan lencana status. | Memantau aliran kerja permohonan usahawan yang aktif secara masa nyata. | Wajar dimampatkan sebagai *stacked card list* di mobile. |
| **PendingSummary** | List Card | Senarai kelulusan tertunda: tajuk workflow pemohon, soalan kelulusan, masa tertunda, ejen, & penugasan. | Membolehkan pegawai mengenalpasti fail usahawan yang paling lama tertunda. | Senarai vertikal (sedia ada sesuai untuk mobile, cuma perlu pelarasan padding). |
| **Risk Flags** | List Card | Deskripsi risiko perniagaan/kredit usahawan, lencana keseriusan (*low/medium/high/critical*), nama ejen, & ID workflow. | Menyorot amaran risiko (cth: hutang tinggi, dokumen tidak sah) yang dikesan AI. | Senarai vertikal dengan lencana keseriusan di sudut kanan atas. |
| **Agent Performance** | Data Table | Nama ejen, jumlah diproses, purata latensi (s), jumlah kos ($), purata keyakinan (%). | Mengaudit kecekapan, latensi, dan ketepatan setiap ejen AI MARA. | Di mobile, jadual ini mempunyai `overflow-x-auto` (skrol mendatar). Wajar diubah ke *Card view*. |

---

## 10. Review Console — Content Breakdown

Modul ini adalah jantung kepada prinsip *Human-in-the-Loop* (HIL) di mana pegawai mengesahkan analisis AI ke atas dokumen perniagaan/kewangan usahawan:

| Nama Konten / Seksyen | Jenis | Fungsi | Versi Mobile / Redesign |
| :--- | :--- | :--- | :--- |
| **Filter Tabs** | Tabs | Menapis senarai permintaan kelulusan kepada tab *Pending* dan *Resolved*. | Tab mendatar sesuai untuk mobile. |
| **ApprovalCard Header** | Card Header | Memaparkan nama ejen, lencana status, ID workflow, ID dokumen usahawan, masa, dan kotak soalan kelulusan. | Susunan teks perlu diubah ke *stack vertical* di skrin kecil. |
| **Confidence Warning** | Alert Chip | Cip merah amaran jika terdapat medan yang diekstrak di bawah ambang keyakinan (`< 85%`). | Kekal sebagai cip amaran visual. |
| **FieldPreview List** | Data Cards | Memaparkan setiap medan diekstrak dari dokumen usahawan (cth: pendapatan, no akaun): nama medan, cip keyakinan, sumber (*OCR / PDF Text Layer*), sitasi halaman, koordinat *bounding box*, dan pautan dokumen. | Di mobile, koordinat sitasi dan butang pautan wajar disusun di bawah nilai medan. |
| **Reason Input** | Text Input | Kotak input untuk memasukkan alasan kelulusan (pilihan untuk Approve, **wajib** untuk Reject). | Lebar penuh (`w-full`) di kedua-dua desktop dan mobile. |
| **Action Buttons** | Button Group | 3 butang utama: **Approve** (primary), **Reject** (secondary), **Correct** (tertiary). | Di mobile, 3 butang ini wajar disusun bertindih vertikal (`flex-col`) atau sebagai *fixed bottom sheet*. |
| **CorrectionForm** | Edit Form | Borang khas apabila butang *Correct* diklik. Membolehkan pegawai mengubah nilai medan yang salah diekstrak dari dokumen usahawan tanpa memadam data asal ejen. | Di mobile, input medan dan butang *Submit / Cancel* wajar disusun secara vertikal. |

---

## 11. Admin — Content Breakdown

| Nama Panel / Setting | Jenis | Fungsi | Versi Mobile / Redesign |
| :--- | :--- | :--- | :--- |
| **UserManagementTab** | Data Table | Senarai pengguna (Pegawai MARA): Nama, Email, Peranan (*Role*), Cawangan (*Branch*), Status MFA (*Enrolled / Not enrolled*), Status akaun, dan log masuk terakhir. | Menggunakan `overflow-x-auto`. Untuk mobile, wajar ditukar kepada senarai kad pengguna (*User Cards*). |
| **RoleConfigTab** | Card List | Memaparkan peranan pentadbiran (*Super Admin, Branch Manager, Officer, Auditor*), bilangan ahli, dan senarai hak akses (*grants*). | Kad bersusun vertikal (sudah sesuai untuk mobile). |
| **AgentConfigTab** | Card Grid | Konfigurasi profil 7 ejen AI MARA. Memaparkan lencana autonomi, ambang keyakinan, model LLM (*Haiku, Sonnet, Opus*), keperluan pintu kelulusan, kebenaran rangkaian, dan senarai *tools*. | Grid 4 kolum metrik dalam kad wajar diubah kepada 2 kolum di skrin mobile. |
| **SystemSettingsTab** | Settings List | Pengurusan parameter sistem (Toggle & Value tags): *Audit Logging, Strict Compliance Mode, Max LLM Cost, Default Model Tier, Auto-Archive, Maintenance Mode*. | Senarai baris dengan teks di kiri dan *toggle/badge* di kanan (sedia ada sesuai untuk mobile). |

---

## 12. Perbandingan Ringkas Desktop vs Mobile

Jadual berikut membandingkan susunan sedia ada dengan kelemahan / keperluan adaptasi mobile:

| Page / Section | Desktop Layout (Sedia Ada) | Mobile Layout (Sedia Ada - Ketiadaan Media Query) | Perbezaan Utama & Catatan Redesign |
| :--- | :--- | :--- | :--- |
| **Navigation Sidebar** | Fixed left sidebar (`w-56`). | Kekal `w-56`, memakan 50-60% lebar skrin telefon. | **Perlu Redesign:** Ubah ke Bottom Nav Bar atau Hamburger Drawer untuk skrin `< 768px`. |
| **Workspace (`/`)** | Dwipanel: TaskPanel (`w-72`) di kiri, ChatPanel (`flex-1`) di kanan. | Kedua-dua panel terhimpit secara mendatar, ChatPanel menjadi sangat sempit. | **Perlu Redesign:** Gunakan sistem Tab/Toggle untuk memaparkan satu panel pada satu masa di mobile. |
| **Dashboard (`/dashboard`)**| Grid 5 kolum (Stat Cards) & Grid 2 kolum (Workflows + Summary). | Kad terhimpit dalam 5 kolum dan 2 kolum, teks terpotong / overflow. | **Perlu Redesign:** Gunakan `grid-cols-1` (atau 2 kolum untuk Stat Cards) pada resolusi mobile. |
| **Review Console (`/review`)**| Kad kelulusan dengan senarai medan dan butang tindakan sebaris. | Butang *Approve / Reject / Correct* sebaris melimpah atau terhimpit. | **Perlu Redesign:** Butang tindakan disusun bertindih secara vertikal (`flex-col`) di mobile. |
| **Admin Console (`/admin`)** | Tab modul dengan jadual lebar (*User Management* & *Agent Metrics*). | Jadual terpotong dan memerlukan skrol mendatar (`overflow-x-auto`). | **Perlu Redesign:** Transformasi jadual kepada paparan senarai kad (*Card List*) untuk mobile. |

---

## 13. Rujukan Peraturan Project (daripada AGENTS.md)

Bahagian ini meringkaskan peraturan rasmi daripada `AGENTS.md` supaya pembangun yang merujuk dokumen ini memahami batas hak akses tanpa perlu membuka semula fail sumber.

### ❌ Senarai "TIDAK BOLEH DISENTUH" (*Strictly Read-Only / Out of Bounds*)
Anda dilarang sama sekali mengedit, memadam, atau mengubah fail/kod di dalam direktori berikut:
1. `agents/` — Logik domain ejen AI.
2. `services/` — Perkhidmatan backend (Supervisor, Publishing, Voice, Audit).
3. `tools/` — Implementasi alat (OCR, PDF parser, RAG, database, calculation).
4. `workflows/` — Templat aliran kerja LangGraph.
5. `shared/` — Skema kontrak dan infrastruktur dikongsi.
6. `infrastructure/` — Definisi deployment (Docker, Kubernetes, Terraform).
7. `configs/` — Konfigurasi persekitaran.
8. `openhands/` — Substrat runtime OpenHands yang dilindungi (*upstream-derived*).
9. `.github/workflows/` — CI/CD pipelines.
10. `packages/openhands-ui/` — **READ-ONLY**. Anda hanya dibenarkan *mengguna* (`import`) komponen dari sini. Jangan ubah fail di dalamnya atau membina komponen warisan/satelit berasingan jika ia tiada.

### ✅ Senarai "BOLEH DIUBAH / DISENTUH" (*Write Scope*)
1. **`apps/officer-workspace/src/**`** — Skuad anda mempunyai hak akses penuh untuk membina dan mengubah komponen, halaman, dan gaya UI di dalam folder ini.
2. `apps/officer-workspace/package.json`, `tsconfig.json`, `vite.config.ts` — Hanya boleh diubah jika tugasan benar-benar memerlukan penambahan kebergantungan (*dependency*) atau perubahan konfigurasi binaan.

### ⚠️ Syarat & Batasan Domain Wajib Dipatuhi (Berdasarkan `AGENTS.md`)
1. **Pintu Kelulusan 3-Cabang (§10.5):** UI kelulusan **WAJIB** mempunyai 3 tindakan: **Approve**, **Reject**, dan **Correct**. Tindakan *Correct* adalah berbeza daripada edit-dan-lulus; pembetulan direkodkan secara berasingan daripada output asal ejen AI.
2. **Dua Bentuk Sitasi Berbeza:**
   - **`Citation` (Dokumen Pemohon Usahawan):** Mengandungi `document_id` + `page` + `bounding_box`. Wajib menyokong akses satu klik ke kawasan tepat dokumen asal.
   - **`PolicyCitation` (Polisi / Undang-undang MARA):** Mengandungi `document_id` + `version` + `locator` (klausa/seksyen) + `relevance` + `superseded_on`. **Tiada page atau bounding box.** Versi polisi wajib dipaparkan!
3. **Empat Status Pematuhan (Compliance Status):** Wajib menyokong paparan untuk `pass`, `fail`, `exception`, dan **`no_policy_found`** (penemuan jujur bahawa tiada polisi berkaitan ditemui di dalam korpus).
4. **Sitasi Lapuk (*Stale Citations*):** Jika `PolicyCitation.superseded_on` wujud, ia bermaksud polisi telah digantikan. **Jangan paparkannya sebagai ralat (error)**, sebaliknya tandakan sebagai amaran visual bahawa polisi tersebut telah digantikan dan biarkan pegawai membuat penilaian.
5. **Kontrak Data Backend:** Jangan reka bentuk kontrak atau skema data AI sendiri secara tekaan. Rujuk fail `shared/schemas/` (documents, approval, compliance, knowledge) atau gunakan data mock yang bertanda jelas di dalam `src/mocks/`.

---

## 14. Cadangan Penambahbaikan UI/UX Khusus Untuk Konteks Usahawan MARA

Sebagai panduan tambahan kepada pasukan yang akan melakukan fasa *redesign*, aspek-aspek domain keusahawanan berikut amat disyorkan untuk disepadukan ke dalam antaramuka UI/UX baru (dengan syarat tidak melanggar kontrak data atau peraturan `AGENTS.md`):

1. **Komponen Paparan Ringkasan Pemohon / Usahawan (*Applicant Profile Banner / Widget*):**
   - Dalam antaramuka `ReviewConsolePage` dan `WorkspacePage` sedia ada, maklumat dipaparkan berfokuskan kepada ID workflow atau ID dokumen. 
   - **Cadangan Redesign:** Wujudkan satu komponen kad ringkasan di bahagian atas (*Header Card / Profile Strip*) yang memaparkan profil jelas Usahawan MARA (cth: Nama Syarikat / Pemohon, No. Pendaftaran SSM, Jenis Permohonan Pembiayaan/Geran, Cawangan MARA, dan Jumlah Dipohon). Ini memberi konteks kemanusiaan dan perniagaan yang lebih kuat kepada pegawai sebelum meluluskan maklumat.
2. **Sokongan Dwi-Bahasa (*Bilingual Display - BM & English*):**
   - Dokumen yang dimuat naik oleh usahawan MARA (resit, kertas kerja, penyata) serta nota polisi MARA sering kali menggunakan Bahasa Malaysia atau dwi-bahasa (*code-switching*).
   - **Cadangan Redesign:** Pastikan tipografi, jarak label (*label width*), dan komponen gelembung sembang di dalam UI baru mampu menampung kepanjangan perkataan Bahasa Malaysia dengan kemas (tanpa terpotong atau melimpah), serta menyokong pemaparan sitasi polisi dwi-bahasa.
3. **Penyurihan Keselamatan Data Usahawan (*PDPA & Data Sensitivity Indicators*):**
   - Data kewangan peribadi usahawan, penyata bank, dan laporan kredit adalah bertaraf sulit dan tertakluk kepada Akta Perlindungan Data Peribadi (PDPA).
   - **Cadangan Redesign:** Sertakan lencana/indikator visual (seperti *icon gembok / "Sulit - PDPA Protected"* atau penunjuk bahawa pemprosesan dokumen dilakukan menerusi laluan rangkaian terisolasi *Isolated / Non-Egress*) pada fail dokumen pemohon di dalam konsol semakan bagi meningkatkan kepekaan pegawai terhadap keselamatan data usahawan.

---
*Dokumen ini dijanakan dan dikemaskini berdasarkan analisis statik kod sumber di dalam `apps/officer-workspace/` dan dokumen visi keusahawanan MARA bagi tujuan perancangan redesign UI/UX.*
