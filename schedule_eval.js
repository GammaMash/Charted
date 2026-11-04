#!/usr/bin/env node
"use strict";
/**
 * Evaluate the schedule in template.html. The functions there are the only
 * implementation — this file extracts and calls them, it does not reimplement
 * BATCH4, the lap shuffle, or Sunday bosses.
 *
 *   node schedule_eval.js simulate 1000     # calendar-day puzzle for 1000 days from EPOCH
 *   node schedule_eval.js query < dates     # one YYYY-MM-DD per line; replay path (ARCHIVE_DATE)
 *   node schedule_eval.js match 1000        # replay path === frozen-clock path for every day
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
  let depth = 0;
  let quote = null;
  let escape = false;
  let lineComment = false;
  let blockComment = false;
  for (; i < src.length; i++) {
    const c = src[i];
    const n = src[i + 1];
    if (lineComment) {
      if (c === "\n") lineComment = false;
      continue;
    }
    if (blockComment) {
      if (c === "*" && n === "/") { blockComment = false; i++; }
      continue;
    }
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
    else if (c === "}") {
      depth--;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error("unclosed function " + name);
}

function must(re, label) {
  const m = html.match(re);
  if (!m) throw new Error(label + " not found in template.html");
  return m;
}

const epoch = must(/const EPOCH = "(\d{4}-\d{2}-\d{2})"/, "EPOCH")[1];
const bossEpoch = must(/const BOSS_EPOCH = "(\d{4}-\d{2}-\d{2})"/, "BOSS_EPOCH")[1];
const b4 = must(/const BATCH4 = \{start:"(\d{4}-\d{2}-\d{2})", from:(\d+)\}/, "BATCH4");

const required = ["shuffledLap", "daysSinceEpoch", "dayNumber", "todaysPuzzleIndex", "isBossDay", "bossIndex"];
const fns = required.map(name => {
  const src = extractFunction(html, name);
  if (!src) throw new Error("function " + name + " not found in template.html");
  return src;
}).join("\n");
const gameNow = extractFunction(html, "gameNow") || "function gameNow(){ return new Date(); }";
const archiveDateFrom = extractFunction(html, "archiveDateFrom")
  || "function archiveDateFrom(){ return null; }";

const factory = new Function("puzzles", "bosses", `
  const EPOCH = ${JSON.stringify(epoch)};
  const BOSS_EPOCH = ${JSON.stringify(bossEpoch)};
  const BATCH4 = {start:${JSON.stringify(b4[1])}, from:${Number(b4[2])}};
  const PUZ = puzzles;
  const BOSSES = bosses;
  const DEV = false;
  const DEVBOSS = -1;
  let ARCHIVE_DATE = null;
  ${gameNow}
  ${archiveDateFrom}
  ${fns}
  return {
    todaysPuzzleIndex, isBossDay, bossIndex, dayNumber, archiveDateFrom,
    setArchive(d){ ARCHIVE_DATE = d; }
  };
`);

function iso(dt) {
  return dt.getFullYear() + "-" + String(dt.getMonth() + 1).padStart(2, "0") + "-" + String(dt.getDate()).padStart(2, "0");
}
function parseISO(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}
function addDays(dt, n) {
  const x = new Date(dt.getFullYear(), dt.getMonth(), dt.getDate() + n);
  return x;
}

function withNow(dateKey, fn) {
  const RealDate = Date;
  const [y, m, d] = dateKey.split("-").map(Number);
  const frozen = new RealDate(y, m - 1, d, 12, 0, 0, 0);
  function MockDate(...args) {
    if (!new.target) return RealDate();
    if (args.length === 0) return new RealDate(frozen.getTime());
    return new RealDate(...args);
  }
  MockDate.now = () => frozen.getTime();
  MockDate.parse = RealDate.parse;
  MockDate.UTC = RealDate.UTC;
  MockDate.prototype = RealDate.prototype;
  global.Date = MockDate;
  try { return fn(); }
  finally { global.Date = RealDate; }
}

function rowFrom(api, dateKey) {
  const boss = api.isBossDay();
  const idx = api.todaysPuzzleIndex();
  const bidx = api.bossIndex();
  const puz = boss ? data.bosses[bidx] : data.puzzles[idx];
  if (!puz) throw new Error("no puzzle for " + dateKey + " boss=" + boss + " idx=" + idx + " bidx=" + bidx);
  const u = data.universe[puz.answer];
  return {
    d: dateKey,
    i: idx,
    boss: boss,
    b: bidx,
    t: puz.answer,
    name: u ? u.name : puz.answer,
    day: api.dayNumber(),
    closes: puz.closes,
    dates: puz.dates
  };
}

function eachDate(n) {
  const out = [];
  let d = parseISO(epoch);
  for (let i = 0; i < n; i++) {
    out.push(iso(d));
    d = addDays(d, 1);
  }
  return out;
}

const api = factory(data.puzzles, data.bosses || []);
const cmd = process.argv[2];

if (cmd === "simulate") {
  const n = Number(process.argv[3] || 1000);
  const rows = eachDate(n).map(key => withNow(key, () => {
    api.setArchive(null);
    const r = rowFrom(api, key);
    delete r.closes;
    delete r.dates;
    delete r.name;
    return r;
  }));
  process.stdout.write(JSON.stringify(rows));
} else if (cmd === "query") {
  const dates = fs.readFileSync(0, "utf8").trim().split(/\s+/).filter(Boolean);
  const rows = dates.map(key => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(key)) throw new Error("bad date " + key);
    const dt = parseISO(key);
    dt.setHours(0, 0, 0, 0);
    api.setArchive(dt);
    return rowFrom(api, key);
  });
  process.stdout.write(JSON.stringify(rows));
} else if (cmd === "match") {
  // Replay (ARCHIVE_DATE set, clock frozen on a different day) must equal
  // the puzzle that date played when it was "today".
  const n = Number(process.argv[3] || 1000);
  const anchor = eachDate(n)[n - 1];
  const bad = [];
  for (const key of eachDate(n)) {
    const clock = withNow(key, () => {
      api.setArchive(null);
      return { i: api.todaysPuzzleIndex(), boss: api.isBossDay(), b: api.bossIndex(), day: api.dayNumber() };
    });
    const replay = withNow(anchor, () => {
      const dt = parseISO(key);
      dt.setHours(0, 0, 0, 0);
      api.setArchive(dt);
      return { i: api.todaysPuzzleIndex(), boss: api.isBossDay(), b: api.bossIndex(), day: api.dayNumber() };
    });
    if (JSON.stringify(clock) !== JSON.stringify(replay)) bad.push({ key, clock, replay });
  }
  if (bad.length) {
    console.error(JSON.stringify(bad.slice(0, 5), null, 2));
    process.exit(1);
  }
  process.stdout.write("match ok " + n + "\n");
} else if (cmd === "accept") {
  // archiveDateFrom is the game's own gate for ?d=. Today and the future must lose.
  const now = parseISO("2026-11-04");
  now.setHours(15, 0, 0, 0);
  const cases = [
    ["2026-11-03", true],
    ["2026-11-04", false],
    ["2026-11-05", false],
    ["2026-07-20", true],
    ["2026-07-19", false],
    ["2026-02-31", false],
    ["nope", false],
    ["", false],
    [null, false]
  ];
  for (const [raw, ok] of cases) {
    const got = api.archiveDateFrom(raw, now);
    if (Boolean(got) !== ok) {
      console.error("accept fail", JSON.stringify(raw), got && got.toString());
      process.exit(1);
    }
  }
  const sundayEvening = parseISO("2026-11-01");
  sundayEvening.setHours(18, 0, 0, 0);
  if (api.archiveDateFrom("2026-11-01", sundayEvening)) {
    console.error("sunday still in progress was accepted");
    process.exit(1);
  }
  process.stdout.write("accept ok\n");
} else if (cmd === "consts") {
  process.stdout.write(JSON.stringify({
    epoch, bossEpoch, batch4: b4[1], batch4From: Number(b4[2]),
    puzzles: data.puzzles.length, bosses: (data.bosses || []).length
  }));
} else {
  console.error("usage: schedule_eval.js simulate|query|match|consts");
  process.exit(2);
}
