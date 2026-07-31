import { Icon } from '@openhands/ui';
import styles from './LoginPage.module.css';

const features = [
  {
    icon: 'FileText',
    title: 'Pengekstrakan dokumen automatik',
    desc: '7 ejen AI mengekstrak dan menyemak dokumen usahawan — IC, penyata bank, kertas kerja perniagaan.',
  },
  {
    icon: 'ShieldCheck',
    title: 'Pematuhan polisi MARA',
    desc: 'Semakan automatik terhadap syarat kelayakan, taraf bumiputera, dan garis panduan pembiayaan.',
  },
  {
    icon: 'GraphUp',
    title: 'Penilaian risiko masa nyata',
    desc: 'Kesan risiko kredit dan perniagaan lebih awal dengan bendera keseriusan low hingga critical.',
  },
  {
    icon: 'ClipboardCheck',
    title: 'Kawalan manusia penuh',
    desc: 'Pegawai kekal membuat keputusan akhir — Approve, Reject, atau Correct pada setiap pintu kelulusan.',
  },
];

export function BrandPanel() {
  return (
    <div className={styles.brandPanel}>
      <div className={styles.brandPanelContent}>
        <div className={styles.brandHeader}>
          <div className={styles.logoBox}>
            <img src="/favicon.png" alt="Logo MARA AI-ETC" />
          </div>
          <div>
            <div className={styles.brandTitle}>MARA AI-ETC</div>
            <div className={styles.brandSubtitle}>Officer workspace</div>
          </div>
        </div>

        <div className={styles.featureList}>
          {features.map(({ icon, title, desc }) => (
            <div key={title} className={styles.featureItem}>
              <div className={styles.featureIconBox}>
                <Icon icon={icon} size={16} />
              </div>
              <div>
                <p className={styles.featureTitle}>{title}</p>
                <p className={styles.featureDesc}>{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className={styles.brandFooter}>
        Platform AI agentic — Majlis Amanah Rakyat &copy; 2026
      </p>
    </div>
  );
}
