import type { ReactNode } from "react";

export function InfoLayout({ eyebrow, title, lead, children }: { eyebrow: string; title: string; lead: string; children: ReactNode }) {
  return <>
    <header className="site-header info-header">
      <a className="wordmark" href="/">观象</a>
      <nav><a href="/guide">如何使用</a><a href="/about">方法与边界</a><a href="/privacy">隐私</a></nav>
      <small>确定性排盘 · 现实验证</small>
    </header>
    <main className="info-canvas">
      <article className="info-scroll">
        <a className="back-home" href="/">返回长卷</a>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="info-lead">{lead}</p>
        {children}
      </article>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span></footer>
  </>;
}
