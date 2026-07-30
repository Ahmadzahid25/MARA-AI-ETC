import { useState } from 'react';
import { Button, Chip, Input, Typography } from '@openhands/ui';
import {
  ApiError,
  createApplicantApplication,
  getApplicationStatus,
  loginApplicant,
  registerApplicant,
  uploadApplicationDocument,
  type V1ApplicationStatus,
  type V1ApplicationStatusOutput,
} from '../services/api';

type PortalView = 'overview' | 'application' | 'documents' | 'status';
type AuthMode = 'login' | 'register';
type DocumentType = 'SSM_CERTIFICATE' | 'BANK_STATEMENT' | 'IDENTITY_COPY';
type UploadState = 'pending' | 'uploading' | 'done' | 'error';

const DOCUMENTS: Array<{ type: DocumentType; label: string; help: string }> = [
  { type: 'SSM_CERTIFICATE', label: 'Sijil Pendaftaran SSM', help: 'Sijil pendaftaran perniagaan yang sah.' },
  { type: 'BANK_STATEMENT', label: 'Penyata Bank', help: 'Penyata akaun perniagaan bagi enam bulan terkini.' },
  { type: 'IDENTITY_COPY', label: 'Salinan Kad Pengenalan', help: 'Salinan kad pengenalan pemohon.' },
];

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return 'Tidak dapat menghubungi pelayan. Sila semak sambungan anda dan cuba lagi.';
  return 'Tindakan tidak berjaya. Sila cuba lagi.';
}

function statusLabel(status: V1ApplicationStatus): string {
  return ({
    DRAFT: 'Draf', SUBMITTED: 'Dihantar', PROCESSING: 'Sedang diproses',
    NEEDS_INFO: 'Maklumat diperlukan', UNDER_REVIEW: 'Dalam semakan',
    APPROVED: 'Diluluskan', REJECTED: 'Tidak diluluskan',
  })[status];
}

function statusColor(status: V1ApplicationStatus): 'gray' | 'green' | 'red' | 'primaryDark' {
  if (status === 'APPROVED') return 'green';
  if (status === 'REJECTED') return 'red';
  if (status === 'NEEDS_INFO') return 'gray';
  return 'primaryDark';
}

export function ApplicantPortalPage() {
  const [view, setView] = useState<PortalView>('overview');
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [status, setStatus] = useState<V1ApplicationStatusOutput | null>(null);

  const [applicantName, setApplicantName] = useState('');
  const [icNumber, setIcNumber] = useState('');
  const [phone, setPhone] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [ssmNumber, setSsmNumber] = useState('');
  const [sector, setSector] = useState('');
  const [scheme, setScheme] = useState('');
  const [amountRequested, setAmountRequested] = useState('');
  const [purpose, setPurpose] = useState('');
  const [files, setFiles] = useState<Partial<Record<DocumentType, File>>>({});
  const [uploadState, setUploadState] = useState<Record<DocumentType, UploadState>>({
    SSM_CERTIFICATE: 'pending', BANK_STATEMENT: 'pending', IDENTITY_COPY: 'pending',
  });

  const signedIn = token !== null;
  const uploadedCount = Object.values(uploadState).filter((value) => value === 'done').length;

  async function authenticate(event: React.FormEvent) {
    event.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const response = authMode === 'register'
        ? await registerApplicant({ full_name: fullName, email, password })
        : await loginApplicant({ email, password });
      setToken(response.access_token);
      if (authMode === 'register' && !applicantName) setApplicantName(fullName);
    } catch (error) {
      setAuthError(messageFor(error));
    } finally {
      setAuthLoading(false);
    }
  }

  async function submitApplication(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const result = await createApplicantApplication({
        applicant: { full_name: applicantName, ic_number: icNumber, phone, email, state: 'Selangor' },
        business: { business_name: businessName, ssm_number: ssmNumber, sector, years_operating: 0, monthly_revenue_avg: 0 },
        financing: { scheme, amount_requested: Number(amountRequested), purpose, tenure_months: 36 },
        documents: [],
      }, token);
      setApplicationId(result.application_id);
      setStatus({ application_id: result.application_id, status: result.status, stage_log: ['Permohonan diterima. Sila muat naik dokumen wajib untuk meneruskan semakan.'], updated_at: new Date().toISOString() });
      setView('documents');
    } catch (error) {
      setFormError(messageFor(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function uploadDocuments() {
    if (!applicationId || !token) return;
    setUploading(true);
    setUploadError(null);
    let failed = false;
    for (const document of DOCUMENTS) {
      const file = files[document.type];
      if (!file || uploadState[document.type] === 'done') continue;
      setUploadState((current) => ({ ...current, [document.type]: 'uploading' }));
      try {
        await uploadApplicationDocument(applicationId, document.type, file, token);
        setUploadState((current) => ({ ...current, [document.type]: 'done' }));
      } catch (error) {
        failed = true;
        setUploadState((current) => ({ ...current, [document.type]: 'error' }));
        setUploadError(messageFor(error));
      }
    }
    setUploading(false);
    if (!failed) await refreshStatus(applicationId);
  }

  async function refreshStatus(id = applicationId) {
    if (!id || !token) return;
    setLoadingStatus(true);
    setStatusError(null);
    try {
      const result = await getApplicationStatus(id, token);
      setStatus(result);
      setView('status');
    } catch (error) {
      setStatusError(messageFor(error));
    } finally {
      setLoadingStatus(false);
    }
  }

  const navItems: Array<{ id: PortalView; label: string; disabled?: boolean }> = [
    { id: 'overview', label: 'Ringkasan' },
    { id: 'application', label: 'Permohonan baharu', disabled: !signedIn },
    { id: 'documents', label: 'Dokumen', disabled: !applicationId },
    { id: 'status', label: 'Status permohonan', disabled: !applicationId },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-[#0D0D0F] dark:text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur-md dark:border-[#222328] dark:bg-[#131417]/90 md:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">M</div>
            <div><p className="text-sm font-semibold">MARA AI-ETC</p><p className="text-xs text-slate-500 dark:text-slate-400">Portal Permohonan</p></div>
          </div>
          <a href="/login" className="text-sm font-medium text-indigo-700 hover:underline dark:text-indigo-300">Log masuk pegawai</a>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl md:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="border-b border-slate-200 bg-white p-4 dark:border-[#222328] dark:bg-[#131417] md:min-h-[calc(100vh-61px)] md:border-b-0 md:border-r">
          <p className="mb-3 px-3 text-xs font-semibold uppercase text-slate-400">Permohonan saya</p>
          <nav className="flex gap-1 overflow-x-auto md:flex-col">
            {navItems.map((item) => <button key={item.id} type="button" disabled={item.disabled} onClick={() => setView(item.id)} className={`shrink-0 rounded-md px-3 py-2 text-left text-sm font-medium transition-colors ${view === item.id ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-[#222328]'} disabled:cursor-not-allowed disabled:opacity-40`}>{item.label}</button>)}
          </nav>
          {applicationId && <div className="mt-6 border-t border-slate-200 pt-4 dark:border-[#222328]"><p className="text-xs text-slate-500">ID permohonan</p><p className="mt-1 break-all font-mono text-xs font-semibold">{applicationId}</p></div>}
        </aside>

        <main className="min-w-0 p-4 md:p-8">
          {!signedIn ? <section className="mx-auto max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-[#222328] dark:bg-[#131417]">
            <p className="text-xs font-semibold uppercase text-indigo-600 dark:text-indigo-300">Akses pemohon</p>
            <Typography.H3 className="mt-2">{authMode === 'login' ? 'Log masuk untuk meneruskan' : 'Daftar akaun pemohon'}</Typography.H3>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Permohonan anda disimpan ke sistem hanya selepas pengesahan berjaya.</p>
            {authError && <Alert message={authError} />}
            <form className="mt-6 space-y-4" onSubmit={authenticate}>
              {authMode === 'register' && <Input label="Nama penuh" value={fullName} onChange={(event) => setFullName(event.target.value)} required />}
              <Input label="Alamat e-mel" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
              <Input label="Kata laluan" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
              <Button type="submit" variant="primary" className="w-full justify-center" disabled={authLoading}>{authLoading ? 'Memproses...' : authMode === 'login' ? 'Log masuk' : 'Daftar akaun'}</Button>
            </form>
            <button type="button" onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')} className="mt-4 text-sm font-medium text-indigo-700 hover:underline dark:text-indigo-300">{authMode === 'login' ? 'Belum mempunyai akaun? Daftar' : 'Sudah mempunyai akaun? Log masuk'}</button>
          </section> : <>
            {view === 'overview' && <Overview applicationId={applicationId} status={status} uploadedCount={uploadedCount} onStart={() => setView('application')} onStatus={() => refreshStatus()} />}
            {view === 'application' && <ApplicationForm error={formError} submitting={submitting} applicantName={applicantName} setApplicantName={setApplicantName} icNumber={icNumber} setIcNumber={setIcNumber} phone={phone} setPhone={setPhone} email={email} businessName={businessName} setBusinessName={setBusinessName} ssmNumber={ssmNumber} setSsmNumber={setSsmNumber} sector={sector} setSector={setSector} scheme={scheme} setScheme={setScheme} amountRequested={amountRequested} setAmountRequested={setAmountRequested} purpose={purpose} setPurpose={setPurpose} onSubmit={submitApplication} />}
            {view === 'documents' && <DocumentsPanel documents={DOCUMENTS} files={files} uploadState={uploadState} error={uploadError} uploading={uploading} canUpload={Boolean(applicationId)} onFile={(type: DocumentType, file: File | null) => setFiles((current) => ({ ...current, [type]: file ?? undefined }))} onUpload={uploadDocuments} />}
            {view === 'status' && <StatusPanel applicationId={applicationId} status={status} error={statusError} loading={loadingStatus} onRefresh={() => refreshStatus()} />}
          </>}
        </main>
      </div>
    </div>
  );
}

function Alert({ message }: { message: string }) { return <div role="alert" className="mt-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">{message}</div>; }

function Overview({ applicationId, status, uploadedCount, onStart, onStatus }: { applicationId: string | null; status: V1ApplicationStatusOutput | null; uploadedCount: number; onStart: () => void; onStatus: () => void }) {
  return <div className="space-y-6"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase text-indigo-600 dark:text-indigo-300">Dashboard pemohon</p><Typography.H2 className="mt-1">Permohonan pembiayaan</Typography.H2><p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Lengkapkan maklumat dan dokumen sebelum semakan pegawai MARA.</p></div><Button variant="primary" onClick={onStart}>{applicationId ? 'Permohonan baharu' : 'Mulakan permohonan'}</Button></div><div className="grid gap-4 sm:grid-cols-3"><Metric label="Status" value={status ? statusLabel(status.status) : 'Belum dimulakan'} /><Metric label="Dokumen lengkap" value={`${uploadedCount} / 3`} /><Metric label="Permohonan" value={applicationId ? '1 aktif' : 'Tiada'} /></div>{applicationId && status ? <section className="rounded-lg border border-slate-200 bg-white p-5 dark:border-[#222328] dark:bg-[#131417]"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">{applicationId}</p><p className="mt-1 text-sm text-slate-500">Dikemas kini {new Date(status.updated_at).toLocaleString('ms-MY')}</p></div><Chip color={statusColor(status.status)} variant="pill">{statusLabel(status.status)}</Chip><Button variant="secondary" onClick={onStatus}>Lihat status</Button></div></section> : <section className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center dark:border-[#3a3c42] dark:bg-[#131417]"><p className="font-medium">Tiada permohonan aktif</p><p className="mt-1 text-sm text-slate-500">Mulakan dengan borang permohonan pembiayaan.</p></section>}</div>;
}
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-[#222328] dark:bg-[#131417]"><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-2 text-lg font-semibold">{value}</p></div>; }

function ApplicationForm(props: any) { const { error, submitting, onSubmit, ...fields } = props; return <form onSubmit={onSubmit} className="mx-auto max-w-3xl space-y-5"><div><p className="text-xs font-semibold uppercase text-indigo-600 dark:text-indigo-300">Permohonan baharu</p><Typography.H2 className="mt-1">Maklumat pembiayaan</Typography.H2></div>{error && <Alert message={error} />}<FormSection title="Maklumat pemohon"><Input label="Nama penuh" value={fields.applicantName} onChange={(e) => fields.setApplicantName(e.target.value)} required /><Input label="No. kad pengenalan" value={fields.icNumber} onChange={(e) => fields.setIcNumber(e.target.value)} required /><Input label="No. telefon" value={fields.phone} onChange={(e) => fields.setPhone(e.target.value)} required /><Input label="E-mel" type="email" value={fields.email} disabled /></FormSection><FormSection title="Maklumat perniagaan"><Input label="Nama perniagaan" value={fields.businessName} onChange={(e) => fields.setBusinessName(e.target.value)} required /><Input label="No. pendaftaran SSM" value={fields.ssmNumber} onChange={(e) => fields.setSsmNumber(e.target.value)} required /><Input label="Sektor perniagaan" value={fields.sector} onChange={(e) => fields.setSector(e.target.value)} required /></FormSection><FormSection title="Butiran pembiayaan"><Input label="Skim pembiayaan" value={fields.scheme} onChange={(e) => fields.setScheme(e.target.value)} required /><Input label="Jumlah dimohon (RM)" type="number" min="1" value={fields.amountRequested} onChange={(e) => fields.setAmountRequested(e.target.value)} required /><Input label="Tujuan pembiayaan" value={fields.purpose} onChange={(e) => fields.setPurpose(e.target.value)} required /></FormSection><div className="flex justify-end"><Button variant="primary" type="submit" disabled={submitting}>{submitting ? 'Menghantar...' : 'Simpan dan teruskan ke dokumen'}</Button></div></form>; }
function FormSection({ title, children }: { title: string; children: React.ReactNode }) { return <section className="rounded-lg border border-slate-200 bg-white p-5 dark:border-[#222328] dark:bg-[#131417]"><Typography.H4 className="mb-4">{title}</Typography.H4><div className="grid gap-4 sm:grid-cols-2">{children}</div></section>; }
function DocumentsPanel({ documents, files, uploadState, error, uploading, canUpload, onFile, onUpload }: any) { const ready = documents.every((doc: { type: DocumentType }) => files[doc.type] || uploadState[doc.type] === 'done'); return <div className="mx-auto max-w-3xl"><p className="text-xs font-semibold uppercase text-indigo-600 dark:text-indigo-300">Dokumen sokongan</p><Typography.H2 className="mt-1">Muat naik dokumen wajib</Typography.H2><p className="mt-2 text-sm text-slate-500">Setiap dokumen dihantar terus ke sistem dan dipaparkan berjaya hanya selepas pelayan mengesahkan penerimaan.</p>{error && <Alert message={error} />}<div className="mt-6 space-y-3">{documents.map((doc: { type: DocumentType; label: string; help: string }) => <label key={doc.type} className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-[#222328] dark:bg-[#131417] sm:flex-row sm:items-center sm:justify-between"><div><p className="font-medium">{doc.label}</p><p className="mt-1 text-xs text-slate-500">{doc.help}</p>{files[doc.type] && <p className="mt-2 text-xs font-medium text-indigo-700 dark:text-indigo-300">{files[doc.type].name}</p>}</div><div className="flex items-center gap-3"><span className="text-xs text-slate-500">{uploadState[doc.type] === 'done' ? 'Diterima' : uploadState[doc.type] === 'error' ? 'Gagal' : ''}</span><input aria-label={`Pilih ${doc.label}`} type="file" disabled={uploading || uploadState[doc.type] === 'done'} onChange={(e) => onFile(doc.type, e.target.files?.[0] ?? null)} className="max-w-[190px] text-xs" /></div></label>)}</div><div className="mt-6 flex justify-end"><Button variant="primary" disabled={!canUpload || !ready || uploading} onClick={onUpload}>{uploading ? 'Memuat naik...' : 'Hantar dokumen'}</Button></div></div>; }
function StatusPanel({ applicationId, status, error, loading, onRefresh }: any) { return <div className="mx-auto max-w-3xl"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-indigo-600 dark:text-indigo-300">Jejak permohonan</p><Typography.H2 className="mt-1">Status semasa</Typography.H2></div><Button variant="secondary" onClick={onRefresh} disabled={loading}>{loading ? 'Memuat semula...' : 'Muat semula'}</Button></div>{error && <Alert message={error} />}{!status ? <div className="mt-6 rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">Status belum tersedia. Sila hantar permohonan terlebih dahulu.</div> : <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5 dark:border-[#222328] dark:bg-[#131417]"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 dark:border-[#222328]"><div><p className="font-mono text-xs text-slate-500">{applicationId}</p><p className="mt-1 text-sm text-slate-500">Dikemas kini {new Date(status.updated_at).toLocaleString('ms-MY')}</p></div><Chip color={statusColor(status.status)} variant="pill">{statusLabel(status.status)}</Chip></div><ol className="mt-5 space-y-4">{status.stage_log.map((entry: string, index: number) => <li key={`${entry}-${index}`} className="flex gap-3"><span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-indigo-600" /><p className="text-sm">{entry}</p></li>)}</ol></section>}</div>; }
