#!/usr/bin/env node
"use strict";
/**
 * Every pre-reveal clue, for every puzzle, must not contain that puzzle's
 * ticker or company name. The functions are extracted from template.html.
 */
const fs = require("fs");
const path = require("path");
const ROOT = path.dirname(__filename);
const html = fs.readFileSync(path.join(ROOT, "template.html"), "utf8");
const data = JSON.parse(fs.readFileSync(path.join(ROOT, "gamedata.json"), "utf8"));

function extractFunction(src, name) {
  const start = src.search(new RegExp("function\\s+" + name + "\\s*\\("));
  if (start < 0) return null;
  let i = src.indexOf("{", start);
  let depth = 0, quote = null, escape = false, lineComment = false, blockComment = false;
  for (; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (lineComment) { if (c === "\n") lineComment = false; continue; }
    if (blockComment) { if (c === "*" && n === "/") { blockComment = false; i++; } continue; }
    if (quote) {
      if (escape) { escape = false; continue; }
      if (c === "\\") { escape = true; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === "/" && n === "/") { lineComment = true; i++; continue; }
    if (c === "/" && n === "*") { blockComment = true; i++; continue; }
    if (c === '"' || c === "'" || c === "`") { quote = c; continue; }
    if (c === "{") depth++;
    else if (c === "}") { depth--; if (depth === 0) return src.slice(start, i + 1); }
  }
  throw new Error("unclosed function " + name);
}
function grabConst(name) {
  const key = "const " + name + " = ";
  const start = html.indexOf(key);
  if (start < 0) throw new Error("missing const " + name);
  let i = start + key.length, depth = 0, quote = null, escape = false;
  for (; i < html.length; i++) {
    const c = html[i];
    if (quote) {
      if (escape) { escape = false; continue; }
      if (c === "\\") { escape = true; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") { quote = c; continue; }
    if (c === "{" || c === "[") depth++;
    else if (c === "}" || c === "]") depth--;
    else if (c === ";" && depth === 0) return html.slice(start, i + 1);
  }
  throw new Error("unclosed const " + name);
}

const names = ["secL", "factClue", "whereClue", "emojiStr", "shapeArch", "biggestWeek", "formatWeek", "moveClue", "sizeClue", "sectorClue", "headlineClue", "yearClue", "laterClues", "clueRungs"];
const fns = names.map(n => {
  const src = extractFunction(html, n);
  if (!src) throw new Error("missing function " + n);
  return src;
}).join("\n");
const consts = ["SECTOR_LABEL", "SECTOR_PLAIN", "SIZE_CLUE", "WHERE_CLUE"].map(grabConst).join("\n");

const factory = new Function("universe", "const U = universe;\n" + consts + "\n" + fns + `
  let mode = "casual";
  let current = null;
  function puzzle(){ return current; }
  function answer(){ return current.answer; }
  function isBossDay(){ return !!current._boss; }
  function texts(){
    const out = [];
    for (const m of ["casual", "degen"]) {
      mode = m;
      for (const rung of clueRungs()) out.push(rung.text || "", rung.compact || "");
    }
    return out;
  }
  return { set(p){ current = p; }, texts };
`);

function leaks(text, tk, name) {
  if (!text) return null;
  const tick = new RegExp("\\b" + tk.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i");
  if (tick.test(text)) return tk;
  if (name && text.toLowerCase().includes(name.toLowerCase())) return name;
  return null;
}

const api = factory(data.universe);
const bad = [];
let headlines = 0;
const puzzles = data.puzzles.concat((data.bosses || []).map(b => Object.assign({_boss: true}, b)));
for (const p of puzzles) {
  const u = data.universe[p.answer] || {};
  const name = u.name || "";
  if (p.headline && p.headline.clue) headlines++;
  api.set(p);
  for (const text of api.texts()) {
    const hit = leaks(text, p.answer, name);
    if (hit) bad.push({ tk: p.answer, hit, text });
  }
  const w = (function biggest() {
    const ys = p.closes || [];
    if (ys.length < 2) return null;
    let bi = 1, best = ys[1] / ys[0] - 1;
    for (let i = 2; i < ys.length; i++) {
      const r = ys[i] / ys[i - 1] - 1;
      if (Math.abs(r) > Math.abs(best)) { best = r; bi = i; }
    }
    return p.dates[bi];
  })();
  api.set(p);
  const move = api.texts().find(t => /the week of /.test(t) || /Flat the week of /.test(t));
  if (w && move && !move.includes(String(new Date(w + "T12:00:00").getFullYear()))) {
    bad.push({ tk: p.answer, hit: "year", text: move });
  }
}
const shareTextSrc = extractFunction(html, "shareTextFrom");
const drawSrc = extractFunction(html, "drawShareCard");
if (!shareTextSrc || !drawSrc) {
  bad.push({ tk: "share", hit: "missing", text: "shareTextFrom or drawShareCard" });
} else {
  const leakRe = /\banswer\s*\(|\.name\b|ticker|company/i;
  if (leakRe.test(shareTextSrc)) bad.push({ tk: "shareTextFrom", hit: "source", text: "share text builder touches an answer field" });
  if (leakRe.test(drawSrc)) bad.push({ tk: "drawShareCard", hit: "source", text: "image draw touches an answer field" });
  if (!/function\s+drawShareCard\s*\(\s*canvas\s*,\s*card\s*\)/.test(drawSrc))
    bad.push({ tk: "drawShareCard", hit: "params", text: drawSrc.slice(0, 60) });
  const shareApi = new Function(shareTextSrc + "\n" + drawSrc + "\nreturn { shareTextFrom, drawShareCard };")();
  function mockCanvas() {
    const ctx = new Proxy({
      createLinearGradient() { return { addColorStop() {} }; }
    }, {
      get(t, k) { if (k in t) return t[k]; return function () { return ctx; }; },
      set() { return true; }
    });
    return { width: 0, height: 0, getContext() { return ctx; } };
  }
  function safeCard(fields) {
    return new Proxy(fields, {
      get(t, k) {
        if (k === "answer" || k === "name" || k === "ticker" || k === "company" || k === "story")
          throw new Error("answer field " + String(k));
        return t[k];
      }
    });
  }
  for (const p of puzzles) {
    const u = data.universe[p.answer] || {};
    const card = safeCard({
      closes: p.closes, squares: ["r", "y", "g"], id: p.id, boss: !!p._boss,
      res: "3/6", solved: true, mode: "Casual", modeLabel: "🎓 Casual",
      streak: 2, practice: false, replay: false, link: "chartedgame.com"
    });
    let text = "";
    try { text = shareApi.shareTextFrom(card); }
    catch (e) { bad.push({ tk: p.answer, hit: "shareText", text: String(e) }); continue; }
    const hit = leaks(text, p.answer, u.name || "");
    if (hit) bad.push({ tk: p.answer, hit, text });
    if (!text.includes("solved in 3/6") || !text.includes("chartedgame.com") || !text.includes("🟩"))
      bad.push({ tk: p.answer, hit: "shape", text });
  }
  const lost = shareApi.shareTextFrom(safeCard({
    closes: [1, 2], squares: ["r"], id: 4, boss: false, res: "X/6", solved: false,
    mode: "Degen", modeLabel: "💎 Degen", streak: 0, link: "chartedgame.com"
  }));
  if (lost.includes("solved in") || !lost.includes("X/6")) bad.push({ tk: "loss", hit: "shape", text: lost });
  try {
    shareApi.drawShareCard(mockCanvas(), safeCard({
      closes: [10, 12, 9, 14], squares: ["r", "y", "g"], id: 7, boss: false,
      res: "3/6", solved: true, mode: "Degen", streak: 4, link: "chartedgame.com"
    }));
  } catch (e) {
    bad.push({ tk: "draw", hit: "throw", text: String(e) });
  }
}
const rollSrc = ["nextRollover", "countdownLabel"].map(n => extractFunction(html, n)).join("\n");
const roll = new Function(rollSrc + "\nreturn { nextRollover, countdownLabel };")();
const at = new Date(2026, 10, 16, 15, 30, 0);
const mid = roll.nextRollover(at);
if (mid.getFullYear() !== 2026 || mid.getMonth() !== 10 || mid.getDate() !== 17 || mid.getHours() !== 0 || mid.getMinutes() !== 0)
  bad.push({ tk: "rollover", hit: "midnight", text: String(mid) });
if (roll.countdownLabel(at) !== "Next chart in 8h 30m")
  bad.push({ tk: "rollover", hit: "label", text: roll.countdownLabel(at) });
const icsSrc = ["nextEightAM", "icsPad", "icsStampLocal", "icsStampUTC", "remindICS"].map(n => extractFunction(html, n)).join("\n");
const ics = new Function(icsSrc + "\nreturn remindICS;")()(at);
if (!ics.includes("SUMMARY:CHARTED – new chart is up") || !ics.includes("URL:https://chartedgame.com") || !ics.includes("RRULE:FREQ=DAILY"))
  bad.push({ tk: "ics", hit: "body", text: ics });
// 15:30 local is past 8:00, so the floating daily event starts tomorrow at 08:00. No Z.
if (!/DTSTART:20261117T080000\r/.test(ics) || /DTSTART:[^\r\n]*Z/.test(ics))
  bad.push({ tk: "ics", hit: "start", text: ics });
if (bad.length) {
  console.error(JSON.stringify(bad.slice(0, 8), null, 2));
  process.exit(1);
}
process.stdout.write("clues ok · " + puzzles.length + " puzzles · " + headlines + " headlines\n");
if (process.argv[2] === "sample") {
  for (const id of process.argv.slice(3)) {
    const p = puzzles.find(x => x.answer === id);
    console.log("\n== " + id + (p._boss ? " boss" : "") + " ==");
    api.set(p);
    const shown = api.texts();
    const half = shown.length / 2;
    console.log("casual:");
    for (let k = 0; k < half; k += 2) console.log("  " + (k / 2 + 1) + ". " + shown[k]);
    console.log("degen:");
    for (let k = half; k < shown.length; k += 2) console.log("  " + ((k - half) / 2 + 1) + ". " + shown[k]);
  }
}
