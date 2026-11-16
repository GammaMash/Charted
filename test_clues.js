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

const names = ["secL", "factClue", "whereClue", "emojiStr", "shapeArch", "biggestWeek", "formatWeek", "moveClue", "sizeClue", "sectorClue", "headlineClue", "laterClues", "clueRungs"];
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
