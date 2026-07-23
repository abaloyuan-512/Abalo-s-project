import type { ReactNode } from "react";
import Link from "next/link";

export function InfoLayout({ eyebrow, title, lead, children }: { eyebrow: string; title: string; lead: string; children: ReactNode }) {
  return <>
    <header className="site-header info-header">
      <Link className="wordmark" href="/">观象</Link>
      <nav><Link href="/guide">如何使用</Link><Link href="/about">方法与边界</Link><Link href="/privacy">隐私</Link></nav>
      <small>确定性排盘 · 个性化解读</small>
    </header>
    <main className="info-canvas">
      <article className="info-scroll">
        <Link className="back-home" href="/">返回长卷</Link>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="info-lead">{lead}</p>
        {children}
      </article>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span></footer>
  </>;
}
