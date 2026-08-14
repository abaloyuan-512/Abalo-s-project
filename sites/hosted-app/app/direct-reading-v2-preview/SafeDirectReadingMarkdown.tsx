import React from "react";

type Block =
  | { kind: "heading"; level: 2 | 3; text: string }
  | { kind: "quote"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "paragraph"; text: string };

export function parseSafeMarkdown(source: string): Block[] {
  const blocks: Block[] = [];
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  let paragraph: string[] = [];
  let list: string[] = [];
  const flush = () => {
    if (paragraph.length) blocks.push({ kind: "paragraph", text: paragraph.join(" ").trim() });
    if (list.length) blocks.push({ kind: "list", items: [...list] });
    paragraph = [];
    list = [];
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    const heading = /^(##|###)\s+(.+)$/.exec(line);
    if (heading) {
      flush();
      blocks.push({ kind: "heading", level: heading[1].length as 2 | 3, text: heading[2] });
      continue;
    }
    const item = /^[-*]\s+(.+)$/.exec(line);
    if (item) {
      if (paragraph.length) flush();
      list.push(item[1]);
      continue;
    }
    const quote = /^>\s?(.+)$/.exec(line);
    if (quote) {
      flush();
      blocks.push({ kind: "quote", text: quote[1] });
      continue;
    }
    if (list.length) flush();
    paragraph.push(line);
  }
  flush();
  return blocks;
}

export default function SafeDirectReadingMarkdown({ source }: { source: string }) {
  return (
    <article aria-label="Direct Reading V2 解卦正文">
      {parseSafeMarkdown(source).map((block, index) => {
        if (block.kind === "heading") {
          return block.level === 2
            ? <h2 key={index}>{block.text}</h2>
            : <h3 key={index}>{block.text}</h3>;
        }
        if (block.kind === "quote") return <blockquote key={index}>{block.text}</blockquote>;
        if (block.kind === "list") return <ul key={index}>{block.items.map((item, itemIndex) => <li key={itemIndex}>{item}</li>)}</ul>;
        return <p key={index}>{block.text}</p>;
      })}
    </article>
  );
}
