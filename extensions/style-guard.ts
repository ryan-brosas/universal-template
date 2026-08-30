/**
 * Pi style guard - optional output-style enforcement for assistant prose.
 *
 * House style: STE-inspired plain technical English with house constraints
 * (skills/house-writing-style in ~/.agents). This guard is an OPTIONAL adapter;
 * the portable baseline is the AGENTS.md kernel + scripts/style-lint.py.
 *
 * Modes (env PI_STYLE_GUARD):
 *   off      - disabled
 * * audit    - default: record deterministic violations of final assistant
 *              prose to ~/.pi/agent/style-guard-audit.jsonl; never mutates
 *   rewrite  - one rewrite pass maximum on high-confidence fixes, re-lint,
 *              send original if violations remain
 *
 * Only final assistant prose is considered: messages whose blocks are all
 * text/thinking (no tool calls). Protected spans (fenced code, inline code,
 * blockquotes, URLs) are masked before matching and never rewritten.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { appendFileSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const EM_DASH = /\u2014/g;
const FILLERS = /\b(genuinely|really|truly|actually)\b/gi;
const UTILIZE = /\butilize\b/gi;
const THROAT = /^\s*(it is important to note|it should be noted|it's worth noting)\b/gim;
const LANDING = /^\s*(in conclusion|to summarize|in summary|all in all|at the end of the day)\b/gim;
const INLINE_CODE = /`[^`\n]+`/g;
const URL = /https?:\/\/[^\s)>\]]+/g;

interface Violation {
  rule: string;
  index: number;
  excerpt: string;
}

function mask(text: string): string {
  return text.replace(INLINE_CODE, (m) => "\u0000".repeat(m.length))
             .replace(URL, (m) => "\u0000".repeat(m.length));
}

function lintBlock(block: string): Violation[] {
  const out: Violation[] = [];
  let fenced = false;
  for (const raw of block.split("\n")) {
    const line = raw.trim();
    if (line.startsWith("```") || line.startsWith("~~~")) {
      fenced = !fenced;
      continue;
    }
    if (fenced || !line || line.startsWith(">")) continue;
    const masked = mask(raw);
    const check = (re: RegExp, rule: string, g: boolean) => {
      const re2 = g ? re : new RegExp(re.source, re.flags.replace("g", "") + "g");
      let m: RegExpExecArray | null;
      re2.lastIndex = 0;
      while ((m = re2.exec(masked)) !== null) {
        if (m[0].includes("\u0000")) continue;
        out.push({ rule, index: m.index, excerpt: raw.slice(Math.max(0, m.index - 20), m.index + 40).trim() });
        if (!g) break;
      }
    };
    check(EM_DASH, "em-dash", true);
    check(FILLERS, "filler-intensifier", true);
    check(UTILIZE, "banned-word", true);
    check(THROAT, "throat-clearing", false);
    check(LANDING, "artificial-landing", false);
  }
  return out;
}

function fixBlock(block: string): string {
  // Apply only high-confidence fixes outside protected spans.
  const parts = block.split(/(`[^`\n]+`|https?:\/\/[^\s)>\]]+)/);
  return parts
    .map((part, i) => {
      if (i % 2 === 1) return part; // protected span (odd indexes)
      return part
        .replace(EM_DASH, ", ")
        .replace(/\b(genuinely|really|truly|actually)\s+/gi, "")
        .replace(/\butilize\b/gi, "use");
    })
    .join("");
}

function log(entry: Record<string, unknown>): void {
  try {
    const dir = join(homedir(), ".pi", "agent");
    mkdirSync(dir, { recursive: true });
    appendFileSync(join(dir, "style-guard-audit.jsonl"), JSON.stringify(entry) + "\n");
  } catch {
    // logging must never break the session
  }
}

export default function styleGuard(pi: ExtensionAPI): void {
  const mode = (process.env.PI_STYLE_GUARD ?? "audit").toLowerCase();
  if (mode === "off") return;

  pi.on("message_end", async (event) => {
    const message = event.message as {
      role?: string;
      content?: Array<{ type: string; text?: string }>;
    };
    if (!message || message.role !== "assistant" || !Array.isArray(message.content)) return;
    // Final prose only: no tool-call blocks in this message.
    if (!message.content.every((b) => b.type === "text" || b.type === "thinking")) return;

    const textBlocks = message.content
      .map((b, i) => ({ text: b.type === "text" && typeof b.text === "string" ? b.text : "", i }));

    if (mode === "audit") {
      for (const { text, i } of textBlocks) {
        if (!text) continue;
        for (const v of lintBlock(text)) {
          log({ ts: new Date().toISOString(), mode: "audit", rule: v.rule, block: i, excerpt: v.excerpt });
        }
      }
      return; // audit never mutates
    }

    if (mode === "rewrite") {
      let changed = false;
      const before = textBlocks.map(({ text }) => lintBlock(text).length);
      const fixedTexts = textBlocks.map(({ text }, k) => {
        if (!text || before[k] === 0) return text;
        const fixed = fixBlock(text); // one rewrite pass, no loop
        changed = true;
        return fixed;
      });
      if (!changed) return;
      const remaining = fixedTexts.reduce((n, t) => n + lintBlock(t).length, 0);
      for (const { text } of textBlocks) {
        if (text) log({ ts: new Date().toISOString(), mode: "rewrite", fixed: before[0], remaining });
        break;
      }
      if (remaining > 0) return; // violations remain: send the original untouched
      const content = message.content.map((b, k) =>
        b.type === "text" && typeof b.text === "string" ? { ...b, text: fixedTexts[k] } : b,
      );
      return { message: { ...message, content } };
    }
  });
}
