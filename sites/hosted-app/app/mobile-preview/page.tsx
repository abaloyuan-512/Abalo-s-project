import type { Metadata } from "next";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "观象 · 移动端预览",
  description: "以 430 × 932 手机屏幕尺寸预览观象完整流程。",
};

export default function MobilePreviewPage() {
  return (
    <main className={styles.previewStage}>
      <header className={styles.previewHeader}>
        <p className={styles.eyebrow}>移动端预览</p>
        <h1>观象 · 430 × 932</h1>
        <p>下方黑色边框以内，才是手机屏幕中的实际内容。</p>
      </header>

      <section
        className={styles.phoneFrame}
        data-testid="phone-frame"
        aria-label="观象 430 × 932 手机屏幕预览"
      >
        <iframe
          className={styles.deviceScreen}
          data-testid="device-screen"
          src="/?mobile-preview=1"
          title="观象移动端完整流程"
        />
      </section>
    </main>
  );
}
