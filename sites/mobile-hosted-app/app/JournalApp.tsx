"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { JournalSection, type JournalDraft, type JournalRecord } from "./GuanxiangApp";

const JOURNAL_KEY = "guanxiang-observation-key-v1";
const JOURNAL_OPEN_KEY = "guanxiang-open-journal-record-v1";

function observationKey(): string {
  const existing = window.localStorage.getItem(JOURNAL_KEY);
  if (existing) return existing;
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  const value = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  window.localStorage.setItem(JOURNAL_KEY, value);
  return value;
}

function journalHeaders(): HeadersInit {
  return { "Content-Type": "application/json", "X-Guanxiang-Key": observationKey() };
}

export function JournalApp() {
  const [records, setRecords] = useState<JournalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const request = await fetch("/api/journal", { headers: journalHeaders(), cache: "no-store" });
        const payload = await request.json() as { records?: JournalRecord[]; error?: string };
        if (!request.ok) throw new Error(payload.error || "观事簿暂时无法打开。");
        if (!cancelled) setRecords(payload.records ?? []);
      } catch (caught) {
        if (!cancelled) setMessage(caught instanceof Error ? caught.message : "观事簿暂时无法打开。");
      } finally { if (!cancelled) setLoading(false); }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  function openObservation(record: JournalRecord) {
    sessionStorage.setItem(JOURNAL_OPEN_KEY, JSON.stringify(record));
    window.location.href = "/#result";
  }

  async function updateObservation(id: string, draft: JournalDraft) {
    setMessage("");
    try {
      const request = await fetch("/api/journal", { method: "PATCH", headers: journalHeaders(), body: JSON.stringify({ id, ...draft }) });
      const payload = await request.json() as { record?: JournalRecord; error?: string };
      if (!request.ok || !payload.record) throw new Error(payload.error || "复盘暂时没有保存成功。");
      setRecords((current) => current.map((record) => record.id === id ? payload.record! : record));
      setMessage("复盘已经保存。新的现实证据，已经回到这次判断之中。");
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "复盘暂时没有保存成功。"); }
  }

  async function deleteObservation(id: string) {
    if (!window.confirm("这条观象与复盘将被永久删除，且无法恢复。确定删除吗？")) return;
    setMessage("");
    try {
      const request = await fetch(`/api/journal?id=${encodeURIComponent(id)}`, { method: "DELETE", headers: journalHeaders() });
      const payload = await request.json() as { error?: string };
      if (!request.ok) throw new Error(payload.error || "暂时无法删除。");
      setRecords((current) => current.filter((record) => record.id !== id));
      setMessage("这条记录已经永久删除，无法恢复。");
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "暂时无法删除。"); }
  }

  function exportJournal() {
    const blob = new Blob([JSON.stringify({ product: "观象", records }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "观象-观事簿.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return <>
    <header className="site-header info-header"><Link className="wordmark" href="/">观象</Link><nav><Link href="/">回到观象</Link><Link href="/#inquiry">再问一事</Link></nav><small>观事簿</small></header>
    <main className="scroll-canvas journal-page"><JournalSection records={records} loading={loading} message={message} hasUnsavedResult={false} onOpen={openObservation} onUpdate={updateObservation} onDelete={deleteObservation} onExport={exportJournal} onSaveCurrent={() => {}} /></main>
    <footer className="site-footer"><b>观象</b><span>事后再看，才知所见是否准确</span><nav><a href="/guide">如何使用</a><a href="/about">方法与边界</a><a href="/privacy">隐私说明</a></nav></footer>
  </>;
}
