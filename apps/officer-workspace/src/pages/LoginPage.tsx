import { Button } from '@openhands/ui';
import { login } from '../services/auth';

const FEATURES = [
  {
    icon: (
      <svg className="h-5 w-5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: "Pengekstrakan dokumen automatik",
    desc: "7 ejen AI mengekstrak dan menyemak dokumen usahawan — IC, penyata bank, kertas kerja perniagaan.",
  },
  {
    icon: (
      <svg className="h-5 w-5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    title: "Pematuhan polisi MARA",
    desc: "Semakan automatik terhadap syarat kelayakan, taraf bumiputera, dan garis panduan pembiayaan.",
  },
  {
    icon: (
      <svg className="h-5 w-5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    title: "Penilaian risiko masa nyata",
    desc: "Kesan risiko kredit dan perniagaan lebih awal dengan bendera keseriusan low hingga critical.",
  },
  {
    icon: (
      <svg className="h-5 w-5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    title: "Kawalan manusia penuh",
    desc: "Pegawai kekal membuat keputusan akhir — Approve, Reject, atau Correct pada setiap pintu kelulusan.",
  },
];

export function LoginPage() {
  return (
    <div className="flex min-h-screen w-full bg-white text-slate-900">
      {/* Left branding panel */}
      <div className="relative hidden w-1/2 flex-col justify-center gap-10 bg-gradient-to-br from-emerald-950 via-slate-900 to-slate-900 px-14 py-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white">
            <svg className="h-5 w-5 text-emerald-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">MARA AI-ETC</p>
            <p className="text-xs text-slate-400">Officer Workspace</p>
          </div>
        </div>

        <div className="space-y-8">
          {FEATURES.map(({ icon, title, desc }) => (
            <div key={title} className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10">
                {icon}
              </div>
              <div>
                <p className="text-sm font-semibold">{title}</p>
                <p className="mt-1 max-w-sm text-sm leading-relaxed text-slate-300">
                  {desc}
                </p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-xs text-slate-500">
          Platform AI Agentic — Majlis Amanah Rakyat © 2026
        </p>
      </div>

      {/* Right auth panel */}
      <div className="flex w-full flex-col items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-900">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold leading-tight">MARA AI-ETC</p>
              <p className="text-xs text-slate-400">Officer Workspace</p>
            </div>
          </div>

          <h1 className="text-2xl font-semibold text-slate-900">
            Log masuk pegawai
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Sila log masuk untuk mengakses ruang kerja pemprosesan permohonan usahawan.
          </p>

          <div className="mt-6 space-y-3">
            <Button
              variant="primary"
              onClick={login}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-800 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-900"
            >
              <span>Sign in with SSO (Keycloak Server)</span>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Button>
          </div>

          <div className="mt-8 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium text-slate-500">Milestone 0</p>
            <p className="mt-0.5 text-xs text-slate-400">
              Officer Workspace · Human-in-the-Loop Gates aktif
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
