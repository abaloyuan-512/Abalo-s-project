"use client";

import { FormEvent, useState } from "react";

export function FeedbackForm() {
  const [kind, setKind] = useState("体验建议");
  const [content, setContent] = useState("");
  const [contact, setContact] = useState("");
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true); setStatus("");
    try {
      const response = await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, content, contact, page: window.location.pathname }) });
      const body = await response.json() as { error?: string };
      if (!response.ok) throw new Error(body.error || "反馈暂时没有送达。");
      setContent(""); setContact(""); setStatus("已经收到。谢谢你帮助观象变得更清楚。 ");
    } catch (error) { setStatus(error instanceof Error ? error.message : "反馈暂时没有送达。"); }
    finally { setSending(false); }
  }

  return <form className="feedback-form" onSubmit={submit}>
    <label><span>反馈属于</span><select value={kind} onChange={(event) => setKind(event.target.value)}><option>体验建议</option><option>内容纠错</option><option>排盘异常</option><option>其他</option></select></label>
    <label><span>请写下你看到的问题</span><textarea value={content} maxLength={2000} required onChange={(event) => setContent(event.target.value)} /></label>
    <label><span>联系方式（选填）</span><input value={contact} maxLength={160} onChange={(event) => setContact(event.target.value)} /></label>
    <button type="submit" disabled={sending}>{sending ? "正在送达" : "送出反馈"}</button>
    {status && <p role="status">{status}</p>}
  </form>;
}
