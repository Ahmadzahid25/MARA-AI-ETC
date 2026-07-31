import { useState } from 'react';
import { BrandPanel } from './BrandPanel';
import { LoginCard } from './LoginCard';
import styles from './LoginPage.module.css';

export function LoginPage() {
  const [showSplash, setShowSplash] = useState(true);
  const [splashFading, setSplashFading] = useState(false);

  const dismissSplash = () => {
    setSplashFading(true);
    setTimeout(() => setShowSplash(false), 500);
  };

  return (
    <>
      {showSplash && (
        <div
          className={`${styles.splashOverlay} ${splashFading ? styles.splashFadeOut : ''}`}
          onClick={dismissSplash}
        >
          <video
            src="/mara-ai-etc.mp4"
            autoPlay
            muted
            playsInline
            onEnded={dismissSplash}
            onError={() => setShowSplash(false)}
            className={styles.splashVideo}
          />
          <button
            onClick={(e) => {
              e.stopPropagation();
              dismissSplash();
            }}
            className={styles.skipButton}
          >
            Skip
          </button>
        </div>
      )}
      <div className={`${styles.container} ${!showSplash ? styles.visible : ''}`}>
        <BrandPanel />
        <LoginCard />
      </div>
    </>
  );
}
