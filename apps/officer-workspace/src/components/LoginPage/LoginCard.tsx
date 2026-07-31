import { Icon } from '@openhands/ui';
import { login, loginMock } from '../../services/auth';
import styles from './LoginPage.module.css';

export function LoginCard() {
  return (
    <div className={styles.loginColumn}>
      <div className={styles.loginCard}>
        <div className={styles.brandRow}>
          <div className={styles.iconBadge}>
            <img src="/favicon.png" alt="Logo MARA AI-ETC" />
          </div>
          <div>
            <p className={styles.brandName}>MARA AI-ETC</p>
            <p className={styles.brandRole}>Officer Workspace</p>
          </div>
        </div>

      <h1 className={styles.heading}>Log masuk pegawai</h1>
      <p className={styles.description}>
        Sila log masuk untuk mengakses ruang kerja pemprosesan permohonan usahawan.
      </p>

      {/* Primary CTA — Portal Pemohon */}
      <a href="/applicant" className={`${styles.button} ${styles.primaryButton}`}>
        <span className={styles.buttonLabel}>Portal Pemohon Usahawan (Hantar Permohonan)</span>
        <span className={styles.buttonIcon}>
          <Icon icon="ArrowRight" size={16} />
        </span>
      </a>

      {/* Divider */}
      <div className={styles.divider}>
        <div className={styles.dividerLine} />
        <span className={styles.dividerLabel}>Akses Pegawai</span>
        <div className={styles.dividerLine} />
      </div>

      {/* SSO Button */}
      <button
        onClick={login}
        className={`${styles.button} ${styles.secondaryButton}`}
      >
        <span className={styles.buttonIcon}>
          <Icon icon="Lock" size={16} />
        </span>
        <span className={styles.buttonLabel}>Sign in with SSO (Keycloak Server)</span>
      </button>

      {/* Dev-only Mock button */}
      <button
        onClick={loginMock}
        className={`${styles.button} ${styles.tertiaryButton}`}
      >
        <span className={styles.buttonIcon}>
          <Icon icon="Flask" size={14} />
        </span>
        <span className={styles.buttonLabel}>Log Masuk Pegawai (Mod Mock)</span>
        <span className={styles.devBadge}>DEV</span>
      </button>

      {/* Milestone 0 */}
      <div className={styles.milestoneCard}>
        <span className={styles.milestoneIcon}>
          <Icon icon="ShieldCheck" size={16} />
        </span>
        <div>
          <p className={styles.milestoneTitle}>Milestone 0</p>
          <p className={styles.milestoneSubtitle}>
            Officer Workspace · Human-in-the-Loop Gates aktif
          </p>
        </div>
        </div>
      </div>
    </div>
  );
}
