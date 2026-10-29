/*
 * Alqor — JavaScript icra mühiti.
 *
 * `alqor qur --hədəf js|veb` kompilyatorunun çıxışı bu faylın üzərində
 * işləyir. Semantika Python interpretatoru (`alqor/icraci.py`) ilə
 * eynidir və `sinaq/test_js.py` hər iki icranı müqayisə edir.
 *
 * Dəyər modeli:
 *   tam      → BigInt         onluq   → number
 *   mətn     → string         məntiq  → boolean       boş → null
 *   siyahı   → Array          lüğət   → Lüğət (Map)   dəst → Dəst
 *   kortej   → Kortej         diapazon → Diapazon
 *   sinif nümunəsi → Nümunə (sahələr Map-də)
 *   funksiya → JS funksiyası; adlı arqumentlər sonuncu `Adlı` obyektidir
 */
"use strict";

const $ = (function () {

// ═══════════════════════════════════════════════════════════════════════
//  Xətalar
// ═══════════════════════════════════════════════════════════════════════

const XETA_AGACI = {
  "Atılan": null, "Xəta": "Atılan", "ArqumentXətası": "Xəta",
  "TipXətası": "ArqumentXətası", "DəyərXətası": "ArqumentXətası",
  "DiapazonXətası": "ArqumentXətası", "ÇevrilməXətası": "Xəta",
  "RiyaziXəta": "Xəta", "BölməXətası": "RiyaziXəta",
  "DaşmaXətası": "RiyaziXəta", "KolleksiyaXətası": "Xəta",
  "İndeksXətası": "KolleksiyaXətası", "AçarXətası": "KolleksiyaXətası",
  "BoşKolleksiyaXətası": "KolleksiyaXətası", "GirişÇıxışXətası": "Xəta",
  "FaylTapılmadıXətası": "GirişÇıxışXətası",
  "İcazəXətası": "GirişÇıxışXətası", "ŞəbəkəXətası": "Xəta",
  "BağlantıXətası": "ŞəbəkəXətası", "VaxtBitdiXətası": "ŞəbəkəXətası",
  "HTTPXətası": "ŞəbəkəXətası", "FormatXətası": "Xəta",
  "JSONXətası": "FormatXətası", "CSVXətası": "FormatXətası",
  "TOMLXətası": "FormatXətası", "YAMLXətası": "FormatXətası",
  "XMLXətası": "FormatXətası", "SıxmaXətası": "FormatXətası",
  "KodlaşdırmaXətası": "FormatXətası", "KonfiqXətası": "Xəta",
  "ŞifrələməXətası": "Xəta", "JWTXətası": "ŞifrələməXətası",
  "VerilənlərXətası": "Xəta", "MəhdudiyyətXətası": "VerilənlərXətası",
  "BoşDəyərXətası": "Xəta", "VaxtXətası": "Xəta",
  "ParalellikXətası": "Xəta", "KanalXətası": "ParalellikXətası", "DalanXətası": "ParalellikXətası",
  "VahidXətası": "TipXətası", "MüqaviləXətası": "Xəta", "ÖnŞərtXətası": "MüqaviləXətası",
  "SonŞərtXətası": "MüqaviləXətası", "GözləntiXətası": "Xəta", "NəticəXətası": "Xəta",
  "KritikXəta": "Atılan",
  "YaddaşBitdiXətası": "KritikXəta", "StekDaşmaXətası": "KritikXəta",
  "İddiaXətası": "KritikXəta", "DaxiliXəta": "KritikXəta",
};

class AlqorXəta extends Error {
  constructor(tip, mesaj, kod, dəyər) {
    super(mesaj);
    this.tip = tip;
    this.mesaj = mesaj;
    this.kod = kod || "";
    this.dəyər = dəyər === undefined ? null : dəyər;
  }
  toString() { return this.tip + ": " + this.mesaj; }
}

function xəta(tip, mesaj, kod) { return new AlqorXəta(tip, mesaj, kod); }

function xətaUyğun(atılan, tutulan) {
  let c = atılan;
  while (c != null) {
    if (c === tutulan) return true;
    c = XETA_AGACI[c];
  }
  return false;
}

/** `dayan(kod)` — proqramı bitirir, `tut` onu tutmur. */
class Dayanma { constructor(kod) { this.kod = kod; } }

/** JS-in öz xətalarını Alqor xətasına çevirir. */
function xətaya(e) {
  if (e instanceof AlqorXəta || e instanceof Dayanma) return e;
  if (e instanceof RangeError && /call stack/i.test(e.message))
    return xəta("StekDaşmaXətası",
      "çağırış dərinliyi " + STEK_HƏDDİ + " həddini aşdı — sonsuz rekursiya?",
      "ALQ-R010");
  if (e instanceof ReferenceError) {
    const m = /^(\S+) is not defined|Cannot access '([^']+)'/.exec(e.message);
    const ad = m ? (m[1] || m[2]) : "?";
    return xəta("ArqumentXətası", "`" + adAç(ad) + "` təyin edilməyib",
      "ALQ-T022");
  }
  return xəta("DaxiliXəta", String(e && e.message || e));
}

function adAç(ad) { return ad.endsWith("$") ? ad.slice(0, -1) : ad; }

// ═══════════════════════════════════════════════════════════════════════
//  Dəyər tipləri
// ═══════════════════════════════════════════════════════════════════════

const YOX = Symbol("yox");

class Adlı {
  constructor(o) { this.o = o; }
}

class Kortej {
  constructor(e) { this.e = e; }
  [Symbol.iterator]() { return this.e[Symbol.iterator](); }
}

/** Lüğət/dəst açarı: dəyər bərabərliyi Python-dakı kimi işləsin. */
function açar(x) {
  switch (typeof x) {
    case "string": case "bigint": case "boolean": return x;
    case "number":
      return Number.isInteger(x) ? BigInt(x) : x;
  }
  if (x === null) return null;
  if (x instanceof Kortej) return "\u0000k" + x.e.map(açarMətn).join("\u0001");
  if (x instanceof SDəyər && x.sahələr.size)
    return "\u0000e" + x.sadalama.id + ":" + x.ad + ":" +
      [...x.sahələr.values()].map(açarMətn).join("\u0001");
  if (Array.isArray(x) || x instanceof Lüğət || x instanceof Dəst)
    throw xəta("TipXətası", "`" + tip(x) + "` lüğət açarı ola bilməz",
      "ALQ-T001");
  return x;
}

function açarMətn(x) {
  const a = açar(x);
  if (typeof a === "string") return "s" + a;
  if (typeof a === "bigint") return "t" + a;
  if (typeof a === "number") return "o" + a;
  if (typeof a === "boolean") return "m" + a;
  if (a === null) return "b";
  return "i" + obyektId(a);
}

const _idlər = new WeakMap();
let _növbətiId = 1;
function obyektId(o) {
  let i = _idlər.get(o);
  if (i === undefined) { i = _növbətiId++; _idlər.set(o, i); }
  return i;
}

class Lüğət {
  constructor() { this.m = new Map(); }
  get size() { return this.m.size; }
  al(k) { const c = this.m.get(açar(k)); return c === undefined ? YOX : c[1]; }
  var(k) { return this.m.has(açar(k)); }
  qoy(k, v) {
    const a = açar(k), c = this.m.get(a);
    if (c) c[1] = v; else this.m.set(a, [k, v]);
  }
  sil(k) {
    const a = açar(k), c = this.m.get(a);
    if (!c) return YOX;
    this.m.delete(a);
    return c[1];
  }
  *açarlar() { for (const c of this.m.values()) yield c[0]; }
  *dəyərlər() { for (const c of this.m.values()) yield c[1]; }
  *cütlər() { for (const c of this.m.values()) yield c; }
  [Symbol.iterator]() { return this.açarlar(); }
  static cütlərdən(cütlər) {
    const l = new Lüğət();
    for (const [k, v] of cütlər) l.qoy(k, v);
    return l;
  }
}

class Dəst {
  constructor(el) {
    this.m = new Map();
    if (el) for (const x of el) this.əlavə(x);
  }
  get size() { return this.m.size; }
  əlavə(x) { const a = açar(x); if (!this.m.has(a)) this.m.set(a, x); }
  var(x) {
    try { return this.m.has(açar(x)); } catch (e) { return false; }
  }
  sil(x) { this.m.delete(açar(x)); }
  [Symbol.iterator]() { return this.m.values(); }
}

class Diapazon {
  constructor(b, s, a, xaric) {
    this.b = b; this.s = s; this.xaric = !!xaric;
    if (a === null || a === undefined) a = s >= b ? 1n : -1n;
    if (typeof a !== "bigint") a = tamƏdəd(a, "addım");
    if (a === 0n)
      throw xəta("ArqumentXətası", "diapazon addımı 0 ola bilməz", "ALQ-R002");
    this.a = a;
  }
  *[Symbol.iterator]() {
    const { b, s, a } = this;
    if (a > 0n) {
      const h = this.xaric ? s : s + 1n;
      for (let i = b; i < h; i += a) yield i;
    } else {
      const h = this.xaric ? s : s - 1n;
      for (let i = b; i > h; i += a) yield i;
    }
  }
  uzunluq() {
    const { b, s, a } = this;
    const h = a > 0n ? (this.xaric ? s : s + 1n) : (this.xaric ? s : s - 1n);
    if (a > 0n) return h > b ? (h - b + a - 1n) / a : 0n;
    return b > h ? (b - h - a - 1n) / -a : 0n;
  }
  ehtiva(x) {
    if (typeof x === "number" && Number.isInteger(x)) x = BigInt(x);
    if (typeof x !== "bigint") return false;
    const { b, a } = this;
    if ((x - b) % a !== 0n) return false;
    const i = (x - b) / a;
    return i >= 0n && i < this.uzunluq();
  }
}

class Bayt {
  constructor(u8) { this.u = u8; }
}

/** `generator funksiya` nəticəsi — tənbəl iterator. */
class Gen {
  constructor(it) { this.it = it; this.bitdi = false; }
  next() {
    if (this.bitdi) return { done: true, value: undefined };
    const r = this.it.next();
    if (r.done) this.bitdi = true;
    return r;
  }
  [Symbol.iterator]() { return this; }
}

/**
 * `asinxron funksiya` nəticəsi. Python icraçısında olduğu kimi gövdə
 * yalnız `gözlə` (və ya `paralel`) ilə işə düşür.
 */
class Gələcək {
  constructor(f, ad) {
    this.f = f; this.ad = ad || "gələcək";
    this.hal = 0;          // 0 başlamayıb, 1 uğurlu, 2 xəta
    this.d = null;
  }
  başlat() {
    if (this.hal === 0) {
      try { this.d = this.f(); this.hal = 1; }
      catch (e) {
        if (e instanceof Dayanma) throw e;
        this.d = xətaya(e); this.hal = 2;
      }
    }
    return this;
  }
  al() {
    this.başlat();
    if (this.hal === 2) throw this.d;
    return gözlə(this.d);
  }
}

class LəğvNişanı {
  constructor() { this.ləğv = false; }
}

class Element {
  constructor(ad, atributlar, uşaqlar) {
    this.ad = ad; this.atributlar = atributlar || new Lüğət();
    this.uşaqlar = uşaqlar || [];
    // Ağacı hansı komponent nümunəsi yaradıb (`pəncərə` yenidən göstərir)
    this.komponent = null;
  }
}

/**
 * Yerli obyekt: JS-də yazılmış modul tipləri (`Pəncərə`, `httpCavabı`).
 * `c` — metod cədvəli: {ad: (obyekt, ...arqumentlər) => dəyər}.
 */
class Yerli {
  constructor(tipAdı, c, d) { this.tipAdı = tipAdı; this.c = c; this.d = d || {}; }
}

class Modul {
  constructor(ad, üzvlər, çağırışçı) {
    this.ad = ad;
    this.üzvlər = üzvlər instanceof Map ? üzvlər : new Map(Object.entries(üzvlər || {}));
    this.çağırışçı = çağırışçı || null;
  }
}

class TipAlias { constructor(ad, tip) { this.ad = ad; this.tip = tip; } }

// ── Siniflər ────────────────────────────────────────────────────────────

class Sinif {
  constructor(o) {
    this.ad = o.ad;
    this.baza = o.baza || null;
    this.quruluş = o.quruluş || "sinif";
    this.mücərrəd = !!o.mücərrəd;
    this.son = !!o.son;
    this.interfeyslər = o.interfeyslər || [];
    this.metodlar = new Map();
    this.statiklər = new Map();
    this.statikMetodlar = new Set();
    this.quruculər = new Map();
    this.xassələr = [];           // [ad, standart thunk | null, tip]
    this.hesablananlar = new Map();
    this.tənbəllər = new Set();
    this.yazıcılar = new Map();
    this.mücərrədlər = new Set();
  }
  tap(növ, ad) {
    for (let s = this; s; s = s.baza) {
      const f = s[növ].get(ad);
      if (f !== undefined) return f;
    }
    return undefined;
  }
  metod(ad) { return this.tap("metodlar", ad); }
  statikTap(ad) {
    for (let s = this; s; s = s.baza)
      if (s.statiklər.has(ad)) return [true, s.statiklər.get(ad)];
    return [false, null];
  }
  bütünXassələr() {
    const z = [];
    for (let s = this; s; s = s.baza) z.push(s);
    const n = [];
    for (let i = z.length - 1; i >= 0; i--) n.push(...z[i].xassələr);
    return n;
  }
  altdır(d) {
    for (let s = this; s; s = s.baza) if (s === d) return true;
    return false;
  }
}

class Nümunə {
  constructor(s) { this.s = s; this.f = new Map(); this.k = null; }
}

class Üst { constructor(n, s) { this.n = n; this.s = s; } }
class QurucuIst { constructor(s, ad) { this.s = s; this.ad = ad; } }

// ── Sadalama ────────────────────────────────────────────────────────────

let _sadalamaId = 1;
class Sadalama {
  constructor(ad) {
    this.ad = ad; this.id = _sadalamaId++;
    this.variantlar = new Map(); this.sıra = []; this.metodlar = new Map();
  }
}

class SDəyər {
  constructor(sadalama, ad, sıra, dəyər, sahələr) {
    this.sadalama = sadalama; this.ad = ad; this.sıra = sıra;
    this.dəyər = dəyər === undefined ? null : dəyər;
    this.sahələr = sahələr || new Map();
  }
}

class VariantQ {
  constructor(sadalama, ad, sıra, parametrlər) {
    this.sadalama = sadalama; this.ad = ad; this.sıra = sıra;
    this.p = parametrlər;
  }
  yarat(args) {
    const [poz, adlı] = arqAyır(args);
    const s = new Map();
    this.p.forEach((p, i) => {
      if (i < poz.length) s.set(p, poz[i]);
      else if (adlı && p in adlı) s.set(p, adlı[p]);
      else s.set(p, null);
    });
    return new SDəyər(this.sadalama, this.ad, this.sıra, null, s);
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  Funksiyalar və çağırış
// ═══════════════════════════════════════════════════════════════════════

const STEK_HƏDDİ = 1000;
const V = { d: 0, gecikmiş: [] };

function stek() {
  V.d--;
  throw xəta("StekDaşmaXətası",
    "çağırış dərinliyi " + STEK_HƏDDİ + " həddini aşdı — sonsuz rekursiya?",
    "ALQ-R010");
}

function ad(f, a, növ, pSay) {
  f.$ad = a; f.$n = növ || "funksiya";
  if (pSay !== undefined) f.$pSay = pSay;
  return f;
}

/** Daxili funksiya: arqument sayını yoxlayır, `Adlı`-nı ayırır. */
function D(a, min, max, f, adlıQəbul) {
  const w = function (...args) {
    let adlı = null;
    if (args.length && args[args.length - 1] instanceof Adlı)
      adlı = args.pop().o;
    const n = args.length;
    if (n < min || (max !== null && max !== undefined && n > max)) {
      const g = max === min ? String(min)
        : min + "–" + (max === null || max === undefined ? "∞" : max);
      throw xəta("ArqumentXətası",
        "`" + a + "` " + g + " arqument gözləyir, " + n + " verilib",
        "ALQ-T003");
    }
    if (adlıQəbul) return f(adlı || {}, ...args);
    return f(...args);
  };
  return ad(w, a, "daxili");
}

function arqAyır(args) {
  if (args.length && args[args.length - 1] instanceof Adlı) {
    const a = args.slice(0, -1);
    return [a, Object.assign(Object.create(null), args[args.length - 1].o)];
  }
  return [args, null];
}

/**
 * Parametr bağlama — `_parametrləri_bağla` ilə eyni qaydalar.
 * spec: {ad, p: [ad...], st: [standartVar...], v: variadic ad | null,
 *        k: [yalnız adlı...], kst: [...], kv: adlı variadic ad | null}
 * Qaytarır: [p..., k..., v, kv] (çatışmayan standartlar YOX).
 */
function bağla(args, S) {
  let adlı = null;
  let n = args.length;
  if (n && args[n - 1] instanceof Adlı) {
    adlı = Object.assign(Object.create(null), args[n - 1].o);
    n--;
  }
  const p = S.p, np = p.length;
  if (n > np && S.v === null)
    throw xəta("ArqumentXətası",
      "`" + S.ad + "` ən çox " + np + " mövqeli arqument qəbul edir, " +
      n + " verilib", "ALQ-T003");
  const r = new Array(np);
  for (let i = 0; i < np; i++) {
    if (i < n) r[i] = args[i];
    else if (adlı && p[i] in adlı) { r[i] = adlı[p[i]]; delete adlı[p[i]]; }
    else if (S.st[i]) r[i] = YOX;
    else throw xəta("ArqumentXətası",
      "`" + S.ad + "` üçün `" + p[i] + "` arqumenti verilməyib", "ALQ-T003");
  }
  for (let i = 0; i < S.k.length; i++) {
    const k = S.k[i];
    if (adlı && k in adlı) { r.push(adlı[k]); delete adlı[k]; }
    else if (S.kst[i]) r.push(YOX);
    else throw xəta("ArqumentXətası",
      "`" + S.ad + "` üçün `" + k + "` adlı arqumenti məcburidir", "ALQ-T003");
  }
  if (S.v !== null) r.push(n > np ? args.slice(np, n) : []);
  if (S.kv !== null) {
    const l = new Lüğət();
    if (adlı) for (const k of Object.keys(adlı)) l.qoy(k, adlı[k]);
    r.push(l);
    adlı = null;
  }
  if (adlı) {
    const qalan = Object.keys(adlı).sort();
    if (qalan.length)
      throw xəta("ArqumentXətası",
        "`" + S.ad + "` naməlum adlı arqument: " + qalan.join(", "), "ALQ-T004");
  }
  return r;
}

/** Ümumi çağırış: `f(...)`. */
function ç(f, ...args) {
  if (typeof f === "function") return f(...args);
  return çağırQeyri(f, args);
}

function çağırQeyri(f, args) {
  if (f instanceof Sinif) return yarat(f, null, args);
  if (f instanceof Üst) {
    const baza = f.s.baza;
    if (!baza) throw xəta("TipXətası",
      "`üst(...)` baza sinfi olmayan sinifdə işlənib", "ALQ-P012");
    const q = qurucuTap(baza, "");
    if (!q) return null;
    return q.apply(f.n, args);
  }
  if (f instanceof QurucuIst) return yarat(f.s, f.ad, args);
  if (f instanceof VariantQ) return f.yarat(args);
  if (f instanceof Modul && f.çağırışçı) return f.çağırışçı(...args);
  if (f instanceof Nümunə) {
    const m = f.s.metod("çağır");
    if (m) return m.apply(f, args);
  }
  if (f instanceof _XətaSinfi) return f.yarat(args);
  throw xəta("TipXətası", "`" + tip(f) + "` çağırıla bilməz", "ALQ-T008");
}

/** Metod çağırışı: `obyekt.ad(...)`. */
function çm(o, a, ...args) {
  if (o instanceof Nümunə && o.aktyor && o.aktyor.emal === 0) return ç(nümunəÜzvü(o, a), ...args);
  if (o instanceof Nümunə) {
    if (o.f.has(a)) return ç(o.f.get(a), ...args);
    const s = o.s;
    if (s.hesablananlar.size || s.baza) {
      const h = s.tap("hesablananlar", a);
      if (h !== undefined) return ç(hesablananOxu(o, a, h), ...args);
    }
    const m = s.metod(a);
    if (m !== undefined) return m.apply(o, args);
    return ç(nümunəÜzvü(o, a), ...args);
  }
  if (o === null || o === undefined)
    throw xəta("BoşDəyərXətası", "`boş` dəyərdə `" + a + "` üzvü yoxdur",
      "ALQ-R004");
  const c = cədvəl(o);
  if (c !== null) {
    const g = genişlətmələr.get(tipKökü(o));
    if (g && g.has(a)) return g.get(a).apply(o, args);
    const f = c[a];
    if (f !== undefined) {
      if (args.length && args[args.length - 1] instanceof Adlı)
        return f(o, ...args.slice(0, -1), args[args.length - 1].o);
      return f(o, ...args);
    }
  }
  return ç(üzv(o, a), ...args);
}

function yarat(s, qurucuAdı, args) {
  if (s.mücərrəd)
    throw xəta("TipXətası",
      "`" + s.ad + "` mücərrəd sinifdir — ondan obyekt yaradıla bilməz",
      "ALQ-T052");
  const n = new Nümunə(s);
  if (s.quruluş === "aktyor") n.aktyor = { poçt: [], emal: 0 };
  for (const [a, st, t] of s.bütünXassələr())
    n.f.set(a, st ? genişlət(st(), t) : standartDəyər(t));
  const q = qurucuTap(s, qurucuAdı || "");
  if (q && n.aktyor) {
    // Aktyorun qurucusu onun daxilində işləyir: `özü.metod()` birbaşadır
    n.aktyor.emal++;
    try { q.apply(n, args); } finally { n.aktyor.emal--; }
  } else if (q) q.apply(n, args);
  else if (args.length) {
    const [poz, adlı] = arqAyır(args);
    if (s.quruluş === "struktur" && adlı && !poz.length)
      for (const k of Object.keys(adlı)) n.f.set(k, adlı[k]);
    else throw xəta("ArqumentXətası",
      "`" + s.ad + "` sinfində qurucu yoxdur, amma arqument verilib",
      "ALQ-T003");
  }
  return n;
}

function qurucuTap(s, a) {
  for (let c = s; c; c = c.baza) if (c.quruculər.has(a)) return c.quruculər.get(a);
  return null;
}

function standartDəyər(t) {
  switch (t) {
    case "tam": return 0n;
    case "onluq": return 0;
    case "mətn": return "";
    case "məntiq": return false;
    case "siyahı": return [];
    case "lüğət": return new Lüğət();
    case "dəst": return new Dəst();
    case "bayt": return new Bayt(new Uint8Array(0));
  }
  return null;
}

function genişlət(v, t) {
  return (t === "onluq" || t === "onluq?") && typeof v === "bigint" ? Number(v) : v;
}

/** Struktur dəyər tipidir — mənimsətmədə kopyalanır. */
function kp(v) {
  if (v instanceof Nümunə && v.s.quruluş === "struktur") {
    const y = new Nümunə(v.s);
    y.f = new Map(v.f);
    return y;
  }
  return v;
}

function yeni(T, qurucuAdı, ...args) {
  if (T instanceof TipAlias) T = T.tip;
  if (T instanceof Sinif) return yarat(T, qurucuAdı, args);
  if (typeof T === "function" || T instanceof _XətaSinfi) return ç(T, ...args);
  throw xəta("TipXətası", "`yeni` sinif gözləyir, `" + tip(T) + "` gəlib",
    "ALQ-T002");
}

/** Sinif elanı: kompilyatorun verdiyi təsvirdən `Sinif` qurur. */
function sinif(o, qur) {
  if (o.baza !== null && o.baza !== undefined) {
    let b = o.baza;
    if (b instanceof TipAlias) b = b.tip;
    if (!(b instanceof Sinif))
      throw xəta("TipXətası", "`" + o.bazaAdı + "` sinif deyil", "ALQ-T002");
    if (b.son)
      throw xəta("TipXətası",
        "`" + b.ad + "` `son` sinifdir, miras alına bilməz", "ALQ-T055");
    o.baza = b;
  }
  const s = new Sinif(o);
  for (const q of o.qarışıqlar || []) {
    if (q instanceof Sinif) {
      for (const [k, v] of q.metodlar) s.metodlar.set(k, v);
      for (const [k, v] of q.statiklər) s.statiklər.set(k, v);
      s.xassələr.push(...q.xassələr);
    }
  }
  qur(s);
  if (!o.mücərrəd && o.quruluş !== "interfeys" && o.quruluş !== "qarışıq") {
    const tələb = new Set();
    for (let c = s; c; c = c.baza) for (const a of c.mücərrədlər) tələb.add(a);
    const ç_ = [...tələb].filter(a => s.metod(a) === undefined).sort();
    if (ç_.length)
      throw xəta("TipXətası",
        "`" + s.ad + "` mücərrəd metodları tətbiq etmir: " + ç_.join(", "),
        "ALQ-T053");
  }
  if (o.quruluş === "obyekt") return yarat(s, null, []);
  return s;
}

function metodAd(f, a) { return ad(f, a, "funksiya"); }

function sadalama(a, variantlar, metodlar) {
  const e = new Sadalama(a);
  let növbəti = 0n;
  variantlar.forEach((v, i) => {
    let d = null;
    if (v.d) { d = v.d(); if (typeof d === "bigint") növbəti = d + 1n; }
    else if (v.auto) { d = növbəti; növbəti += 1n; }
    if (v.p) e.variantlar.set(v.ad, new VariantQ(e, v.ad, BigInt(i), v.p));
    else e.variantlar.set(v.ad, new SDəyər(e, v.ad, BigInt(i), d,
      new Map(v.s || [])));
    e.sıra.push(v.ad);
  });
  for (const [k, f] of Object.entries(metodlar || {})) e.metodlar.set(k, f);
  return e;
}

// ── Üst ─────────────────────────────────────────────────────────────────

function üstMetod(S, özü, a) {
  const b = S.baza;
  if (!b) throw xəta("TipXətası", "baza sinif yoxdur", "ALQ-T012");
  const m = b.metod(a);
  if (m === undefined)
    throw xəta("ArqumentXətası", "baza sinifdə `" + a + "` metodu yoxdur",
      "ALQ-T006");
  return bağlı(m, özü, a);
}

function bağlı(m, özü, a) {
  return ad((...args) => m.apply(özü, args), a || m.$ad, "funksiya");
}

// ═══════════════════════════════════════════════════════════════════════
//  Tip adları və mətnə çevirmə
// ═══════════════════════════════════════════════════════════════════════

function tip(x) {
  if (x === null || x === undefined) return "heç";
  switch (typeof x) {
    case "boolean": return "məntiq";
    case "bigint": return "tam";
    case "number": return "onluq";
    case "string": return "mətn";
    case "function": return "funksiya";
  }
  if (Array.isArray(x)) {
    if (x.length) {
      const iç = new Set(x.map(tip));
      return iç.size === 1 ? "siyahı[" + [...iç][0] + "]" : "siyahı[istənilən]";
    }
    return "siyahı";
  }
  if (x instanceof Lüğət) {
    if (x.size) {
      const a = new Set([...x.açarlar()].map(tip));
      const d = new Set([...x.dəyərlər()].map(tip));
      if (a.size === 1 && d.size === 1)
        return "lüğət[" + [...a][0] + ", " + [...d][0] + "]";
    }
    return "lüğət";
  }
  if (x instanceof Dəst) return "dəst";
  if (x instanceof Kortej) return "kortej[" + x.e.map(tip).join(", ") + "]";
  if (x instanceof Diapazon) return "diapazon";
  if (x instanceof Nümunə) return x.s.ad;
  if (x instanceof Sinif) return "sinif[" + x.ad + "]";
  if (x instanceof SDəyər) return x.sadalama.ad;
  if (x instanceof Sadalama) return "sadalama[" + x.ad + "]";
  if (x instanceof Modul) return "modul[" + x.ad + "]";
  if (x instanceof Gen) return "generator";
  if (x instanceof Element) return "element";
  if (x instanceof Gələcək) return "gələcək";
  if (x instanceof LəğvNişanı) return "ləğvNişanı";
  if (x instanceof Bayt) return "bayt";
  if (x instanceof VariantQ || x instanceof QurucuIst ||
      x instanceof _XətaSinfi) return "funksiya";
  if (x instanceof Naxış) return "naxış";
  if (x instanceof Yerli) return x.tipAdı;
  return "istənilən";
}

function tipKökü(x) { const t = tip(x); const i = t.indexOf("["); return i < 0 ? t : t.slice(0, i); }

// ── Onluq ədədlərin Python `repr`-i ─────────────────────────────────────

function onluqRepr(x) {
  if (x !== x) return "nan";
  if (x === Infinity) return "inf";
  if (x === -Infinity) return "-inf";
  if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
  const [m, e] = x.toExponential().split("e");
  let exp = parseInt(e, 10);
  const mənfi = m[0] === "-";
  const rəqəmlər = m.replace("-", "").replace(".", "");
  let s;
  if (exp >= -4 && exp < 16) {
    if (exp >= 0) {
      if (rəqəmlər.length <= exp + 1)
        s = rəqəmlər + "0".repeat(exp + 1 - rəqəmlər.length) + ".0";
      else s = rəqəmlər.slice(0, exp + 1) + "." + rəqəmlər.slice(exp + 1);
    } else {
      s = "0." + "0".repeat(-exp - 1) + rəqəmlər;
    }
  } else {
    const mant = rəqəmlər.length > 1 ? rəqəmlər[0] + "." + rəqəmlər.slice(1) : rəqəmlər;
    s = mant + "e" + (exp < 0 ? "-" : "+") + String(Math.abs(exp)).padStart(2, "0");
  }
  return (mənfi ? "-" : "") + s;
}

function onluqMətn(x) {
  if (x !== x) return "ƏdədDeyil";
  if (x === Infinity) return "sonsuz";
  if (x === -Infinity) return "-sonsuz";
  if (Number.isInteger(x) && Math.abs(x) < 1e16)
    return (Object.is(x, -0) ? "-" : "") + BigInt(x).toString() + ".0";
  return onluqRepr(x);
}

function mətnə(x) {
  if (x === null || x === undefined) return "boş";
  switch (typeof x) {
    case "string": return x;
    case "boolean": return x ? "doğru" : "yanlış";
    case "bigint": return x.toString();
    case "number": return onluqMətn(x);
    case "function":
      return "<" + (x.$n || "funksiya") + " " + (x.$ad || x.name || "<anonim>") + ">";
  }
  if (Array.isArray(x)) return "[" + x.map(dm).join(", ") + "]";
  if (x instanceof Kortej)
    return x.e.length === 1 ? "(" + dm(x.e[0]) + ",)" : "(" + x.e.map(dm).join(", ") + ")";
  if (x instanceof Dəst) {
    if (!x.size) return "dəst()";
    return "{" + dəstSırası(x).map(dm).join(", ") + "}";
  }
  if (x instanceof Lüğət) {
    if (!x.size) return "{}";
    const h = [];
    for (const [k, v] of x.cütlər()) h.push(dm(k) + ": " + dm(v));
    return "{" + h.join(", ") + "}";
  }
  if (x instanceof Element) return elementHTML(x);
  if (x instanceof Nümunə) {
    const m = x.s.metod("mətnƏt");
    if (m !== undefined) return mətnə(m.call(x));
    const h = [];
    for (const [k, v] of x.f) h.push(k + ": " + dm(v));
    return x.s.ad + "(" + h.join(", ") + ")";
  }
  if (x instanceof SDəyər) {
    if (x.sahələr.size) {
      const h = [];
      for (const [k, v] of x.sahələr) h.push(k + "=" + pyRepr(v));
      return x.ad + "(" + h.join(", ") + ")";
    }
    return x.ad;
  }
  if (x instanceof Diapazon) {
    const a = (x.a === 1n || x.a === -1n) ? "" : " addım " + x.a;
    return x.b + (x.xaric ? "..<" : "..") + x.s + a;
  }
  if (x instanceof Sinif) return "<" + x.quruluş + " " + x.ad + ">";
  if (x instanceof Sadalama) return "<sadalama " + x.ad + ">";
  if (x instanceof Modul) return "<modul " + x.ad + ">";
  if (x instanceof Gen) return "<generator" + (x.bitdi ? " (bitdi)" : "") + ">";
  if (x instanceof Bayt) return 'b"' + new TextDecoder().decode(x.u) + '"';
  if (x instanceof VariantQ) return "<variant " + x.sadalama.ad + "." + x.ad + ">";
  if (x instanceof _XətaSinfi) return "<xəta " + x.ad + ">";
  if (x instanceof Gələcək) return "<gələcək " + x.ad + ">";
  if (x instanceof TipAlias) return "<tip " + x.ad + ">";
  if (x instanceof Yerli) return x.c.$mətn ? x.c.$mətn(x) : "<" + x.tipAdı + ">";
  return String(x);
}

/** Kolleksiya daxilində mətnlər dırnaqda göstərilir. */
function dm(x) {
  if (typeof x === "string")
    return '"' + x.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
  return mətnə(x);
}

/** Python-un `repr()`-i (cəbri sadalama sahələri üçün). */
function pyRepr(x) {
  if (x === null || x === undefined) return "None";
  if (x === true) return "True";
  if (x === false) return "False";
  if (typeof x === "string") {
    const q = x.includes("'") && !x.includes('"') ? '"' : "'";
    return q + x.replace(/\\/g, "\\\\").replace(new RegExp(q, "g"), "\\" + q)
      .replace(/\n/g, "\\n").replace(/\t/g, "\\t") + q;
  }
  if (typeof x === "number") return onluqRepr(x);
  if (Array.isArray(x)) return "[" + x.map(pyRepr).join(", ") + "]";
  if (x instanceof Kortej)
    return x.e.length === 1 ? "(" + pyRepr(x.e[0]) + ",)" : "(" + x.e.map(pyRepr).join(", ") + ")";
  if (x instanceof Lüğət) {
    const h = [];
    for (const [k, v] of x.cütlər()) h.push(pyRepr(k) + ": " + pyRepr(v));
    return "{" + h.join(", ") + "}";
  }
  if (x instanceof Nümunə) return "<" + x.s.ad + " nümunəsi>";
  return mətnə(x);
}

/** Kiçik mənfi olmayan tam ədədlər Python-da sıralı görünür. */
function dəstSırası(d) {
  const el = [...d];
  if (el.every(x => typeof x === "bigint" && x >= 0n && x < 1000000n))
    return el.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  return el;
}

// ── HTML ────────────────────────────────────────────────────────────────

const TƏK_TEQLƏR = new Set(["br", "img", "input", "hr", "meta", "link",
  "area", "base", "col", "embed", "source", "track", "wbr"]);
const ATRIBUT_XƏRİTƏSİ = {
  "sinif": "class", "üslub": "style", "dəyər": "value",
  "yerTutucu": "placeholder", "növ": "type", "başlıq": "title",
  "mənbə": "src", "ünvan": "href", "alt": "alt", "ad": "name",
  "id": "id", "açar": "key", "hədəf": "target", "en": "width",
  "hündürlük": "height", "söndürülüb": "disabled",
  "oxunan": "readonly", "tələbolunan": "required",
  "seçilib": "checked", "maksimum": "max", "minimum": "min",
};
const HADİSƏ_ATRIBUTLARI = new Set(["klik", "ikiKlik", "dəyişdi",
  "göndərildi", "fokus", "fokusGetdi", "düyməBasma", "düyməBuraxma",
  "siçanÜstdə", "siçanÇıxdı", "sürükləndi", "buraxıldı", "sürüşdü",
  "basıldı", "quraşdırıldı"]);

function htmlQaç(m) {
  return m.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function çağırılandır(x) {
  return typeof x === "function" || x instanceof Sinif ||
    x instanceof VariantQ || x instanceof QurucuIst;
}

function elementHTML(e) {
  if (e.ad === "") return e.uşaqlar.map(uşaqHTML).join("");
  let atr = "";
  for (const [a, d] of e.atributlar.cütlər()) {
    if (HADİSƏ_ATRIBUTLARI.has(a) || çağırılandır(d)) continue;
    const h = ATRIBUT_XƏRİTƏSİ[a] || a;
    if (d === true) atr += " " + h;
    else if (d === false || d === null) continue;
    else atr += " " + h + '="' + htmlQaç(mətnə(d)) + '"';
  }
  if (TƏK_TEQLƏR.has(e.ad)) return "<" + e.ad + atr + ">";
  return "<" + e.ad + atr + ">" + e.uşaqlar.map(uşaqHTML).join("") + "</" + e.ad + ">";
}

function uşaqHTML(u) {
  if (u instanceof Element) return elementHTML(u);
  if (typeof u === "string") return htmlQaç(u);
  if (Array.isArray(u)) return u.map(uşaqHTML).join("");
  if (u instanceof Kortej) return u.e.map(uşaqHTML).join("");
  if (u === null || u === undefined || u === false) return "";
  if (u === true) return "doğru";
  return htmlQaç(mətnə(u));
}

function elementMətn(e) {
  return e.uşaqlar.map(u => u instanceof Element ? elementMətn(u)
    : typeof u === "string" ? u : mətnə(u)).join("");
}

function jsxAtributlar(hissələr) {
  const l = new Lüğət();
  for (const h of hissələr) {
    if (h.y) {
      const d = h.d;
      if (d instanceof Lüğət) for (const [k, v] of d.cütlər()) l.qoy(mətnə(k), v);
      else if (d instanceof Nümunə) for (const [k, v] of d.f) l.qoy(k, v);
      else throw xəta("TipXətası",
        "`{...}` yayması lüğət və ya obyekt gözləyir, `" + tip(d) + "` gəlib",
        "ALQ-T001");
    } else l.qoy(h.a, h.d);
  }
  return l;
}

function jsxUşaqlar(uşaqlar) {
  const n = [];
  for (const d of uşaqlar) {
    if (d === null || d === false) continue;
    if (Array.isArray(d) || d instanceof Kortej) {
      for (const x of (Array.isArray(d) ? d : d.e))
        if (x !== null && x !== false) n.push(x);
    } else n.push(d);
  }
  return n;
}

function jsx(a, hədəf, atributlar, uşaqlar) {
  const atr = jsxAtributlar(atributlar);
  const uş = jsxUşaqlar(uşaqlar);
  if (hədəf === undefined) return new Element(a, atr, uş);
  if (hədəf instanceof Sinif) {
    const q = qurucuTap(hədəf, "");
    let n;
    if (q && q.$pSay) {
      const o = Object.create(null);
      for (const [k, v] of atr.cütlər()) o[k] = v;
      n = yarat(hədəf, null, [new Adlı(o)]);
    } else {
      n = yarat(hədəf, null, []);
      for (const [k, v] of atr.cütlər()) n.f.set(k, v);
    }
    if (uş.length && !n.f.has("uşaqlar")) n.f.set("uşaqlar", uş);
    const g = hədəf.metod("göstər");
    if (g === undefined)
      throw xəta("TipXətası",
        "`" + hədəf.ad + "` komponentində `göstər()` metodu yoxdur", "ALQ-T053");
    const r = g.call(n);
    if (r instanceof Element) r.komponent = n;
    return r;
  }
  if (typeof hədəf === "function") {
    const o = Object.create(null);
    for (const [k, v] of atr.cütlər()) o[k] = v;
    if (uş.length && !("uşaqlar" in o)) o["uşaqlar"] = uş;
    return hədəf(new Adlı(o));
  }
  throw xəta("TipXətası",
    "`<" + a + " />` sinif və ya funksiya olmalıdır, `" + tip(hədəf) + "` gəlib",
    "ALQ-T008");
}

// ═══════════════════════════════════════════════════════════════════════
//  Azərbaycan əlifbası
// ═══════════════════════════════════════════════════════════════════════

const KICIK = "abcçdeəfgğhxıijkqlmnoöprsştuüvyz";
const BOYUK = "ABCÇDEƏFGĞHXIİJKQLMNOÖPRSŞTUÜVYZ";
const _KM = new Map([...KICIK].map((h, i) => [h, i]));
const _BM = new Map([...BOYUK].map((h, i) => [h, i]));
const SAITLER = new Set("aeəıioöuüAEƏIİOÖUÜ");
const QALIN = new Set("aıouAIOU");
const INCE = new Set("eəiöüEƏİÖÜ");

function böyüyə(s) {
  let r = "";
  for (const c of s) { const i = _KM.get(c); r += i !== undefined ? BOYUK[i] : c.toUpperCase(); }
  return r;
}
function kiçiyə(s) {
  let r = "";
  for (const c of s) { const i = _BM.get(c); r += i !== undefined ? KICIK[i] : c.toLowerCase(); }
  return r;
}
function hərfdir(c) { return _KM.has(c) || _BM.has(c); }
function rəqəmdir(c) { return c >= "0" && c <= "9" && c.length === 1; }
function başBöyük(s) {
  if (!s) return s;
  const a = [...s];
  return böyüyə(a[0]) + kiçiyə(a.slice(1).join(""));
}
function hərSözBöyük(s) {
  let r = "", yeni = true;
  for (const c of s) {
    if (hərfdir(c)) { r += yeni ? böyüyə(c) : kiçiyə(c); yeni = false; }
    else { r += c; yeni = true; }
  }
  return r;
}

/** az-AZ sıralaması (elifba.sıralama_açarı). */
function mətnMüqayisə(a, b) {
  const x = [...a], y = [...b];
  const n = Math.min(x.length, y.length);
  for (let i = 0; i < n; i++) {
    const p = hərfAçarı(x[i]), q = hərfAçarı(y[i]);
    if (p[0] !== q[0]) return p[0] < q[0] ? -1 : 1;
    if (p[1] !== q[1]) return p[1] < q[1] ? -1 : 1;
  }
  if (x.length !== y.length) return x.length < y.length ? -1 : 1;
  for (let i = 0; i < n; i++) {
    const p = hərfAçarı(x[i])[2], q = hərfAçarı(y[i])[2];
    if (p !== q) return p < q ? -1 : 1;
  }
  return 0;
}
function hərfAçarı(c) {
  let i = _KM.get(c);
  if (i !== undefined) return [1, i, 0];
  i = _BM.get(c);
  if (i !== undefined) return [1, i, 1];
  return [0, c.codePointAt(0), 0];
}

const LATIN = { "ə": "e", "Ə": "E", "ı": "i", "I": "I", "i": "i", "İ": "I",
  "ö": "o", "Ö": "O", "ü": "u", "Ü": "U", "ç": "c", "Ç": "C", "ş": "s",
  "Ş": "S", "ğ": "g", "Ğ": "G" };
function latınla(s) { let r = ""; for (const c of s) r += LATIN[c] || c; return r; }

// ═══════════════════════════════════════════════════════════════════════
//  Ədədlər
// ═══════════════════════════════════════════════════════════════════════

function ədəddir(x) { return typeof x === "bigint" || typeof x === "number"; }

function tamƏdəd(x, a) {
  if (typeof x !== "bigint")
    throw xəta("TipXətası",
      "`" + a + "` tam ədəd gözləyir, `" + tip(x) + "` gəlib", "ALQ-T004");
  return x;
}
function mətnYoxla(x, a) {
  if (typeof x !== "string")
    throw xəta("TipXətası",
      "`" + a + "` mətn gözləyir, `" + tip(x) + "` gəlib", "ALQ-T004");
  return x;
}

function N(x) { return typeof x === "bigint" ? Number(x) : x; }
function ix(x) { return typeof x === "bigint" ? Number(x) : x; }

/** Python `int(str)` qaydası. */
function tamOxu(s, əsas) {
  s = s.trim();
  əsas = əsas === undefined ? 10 : Number(əsas);
  const rəq = "0123456789abcdefghijklmnopqrstuvwxyz".slice(0, əsas);
  let t = s.replace(/_/g, "");
  let mənfi = false;
  if (t[0] === "+" || t[0] === "-") { mənfi = t[0] === "-"; t = t.slice(1); }
  if (əsas === 16 && /^0x/i.test(t)) t = t.slice(2);
  if (əsas === 2 && /^0b/i.test(t)) t = t.slice(2);
  if (əsas === 8 && /^0o/i.test(t)) t = t.slice(2);
  if (!t.length || /^_|_$|__/.test(s) || ![...t.toLowerCase()].every(c => rəq.includes(c)))
    return null;
  let n = 0n;
  const B = BigInt(əsas);
  for (const c of t.toLowerCase()) n = n * B + BigInt(rəq.indexOf(c));
  return mənfi ? -n : n;
}

/** Python `float(str)` qaydası. */
function onluqOxu(s) {
  const t = s.trim().replace(/_/g, "");
  if (/^[+-]?(inf|infinity)$/i.test(t)) return t[0] === "-" ? -Infinity : Infinity;
  if (/^[+-]?nan$/i.test(t)) return NaN;
  if (!/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(t)) return null;
  return Number(t);
}

function trunc(x) {
  if (!isFinite(x))
    throw xəta("ÇevrilməXətası", "sonsuz və ya ƏdədDeyil tam ədədə çevrilmir",
      "ALQ-R005");
  return BigInt(Math.trunc(x));
}

/**
 * Onluq ədədin dəqiq yuvarlaqlaşdırılması (yarıdan cütə), Python-un
 * `f"{x:.Nf}"` və `round(x, N)` nəticəsi ilə eyni.
 */
function sabitNöqtə(x, r) {
  if (!isFinite(x)) return onluqRepr(x);
  if (r < 0) r = 0;
  const mənfi = x < 0 || Object.is(x, -0);
  const [m, e] = dəqiqParçala(Math.abs(x));
  // x = m * 2^e;  x * 10^r = m * 10^r * 2^e
  let say, qalıq = 0n, məxrəc = 1n;
  const P = 10n ** BigInt(r);
  if (e >= 0) say = m * P * (1n << BigInt(e));
  else {
    məxrəc = 1n << BigInt(-e);
    const sur = m * P;
    say = sur / məxrəc; qalıq = sur % məxrəc;
  }
  if (qalıq * 2n > məxrəc || (qalıq * 2n === məxrəc && say % 2n === 1n)) say += 1n;
  let s = say.toString();
  if (r > 0) {
    s = s.padStart(r + 1, "0");
    s = s.slice(0, -r) + "." + s.slice(-r);
  }
  return (mənfi && (say !== 0n || Object.is(x, -0) || x < 0) ? "-" : "") + s;
}

function dəqiqParçala(x) {
  const b = new DataView(new ArrayBuffer(8));
  b.setFloat64(0, x);
  const hi = b.getUint32(0), lo = b.getUint32(4);
  const ex = (hi >>> 20) & 0x7ff;
  let m = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo);
  if (ex === 0) return [m, -1074];
  m |= 1n << 52n;
  return [m, ex - 1075];
}

function pyRound(x, r) {
  if (typeof x === "bigint") {
    if (r === undefined || r === null || r >= 0n) return x;
    const P = 10n ** -r;
    let q = x / P, q2 = x % P;
    if (q2 < 0n) { q2 += P; q -= 1n; }
    if (q2 * 2n > P || (q2 * 2n === P && q % 2n !== 0n)) q += 1n;
    return q * P;
  }
  if (r === undefined || r === null || r === 0n) {
    if (r === 0n) return Number(sabitNöqtə(x, 0));
    return BigInt(sabitNöqtə(x, 0).replace("-0", "0"));
  }
  return Number(sabitNöqtə(x, Number(r)));
}

// ── Operatorlar ─────────────────────────────────────────────────────────

const OP_METOD = { "+": "topla", "-": "çıx", "*": "vur", "/": "böl",
  "%": "qalıq", "**": "qüvvət" };

function opYoxdur(op, a, b) {
  return xəta("TipXətası",
    "`" + op + "` operatoru `" + tip(a) + "` və `" + tip(b) +
    "` tiplərinə tətbiq edilmir", "ALQ-T008");
}

// ── Ölçü vahidləri (§ 3.8) — alqor/vahidler.py-nin təkrarı ─────────────

const VAHİDLƏR = {
  mm: [0.001, [1, 0, 0, 0]], sm: [0.01, [1, 0, 0, 0]], dm: [0.1, [1, 0, 0, 0]],
  m: [1.0, [1, 0, 0, 0]], km: [1000.0, [1, 0, 0, 0]], "düym": [0.0254, [1, 0, 0, 0]],
  fut: [0.3048, [1, 0, 0, 0]], mil: [1609.344, [1, 0, 0, 0]],
  ha: [10000.0, [2, 0, 0, 0]], ml: [0.000001, [3, 0, 0, 0]], l: [0.001, [3, 0, 0, 0]],
  mq: [0.000001, [0, 1, 0, 0]], q: [0.001, [0, 1, 0, 0]], kq: [1.0, [0, 1, 0, 0]],
  ton: [1000.0, [0, 1, 0, 0]],
  ms: [0.001, [0, 0, 1, 0]], san: [1.0, [0, 0, 1, 0]], "dəq": [60.0, [0, 0, 1, 0]],
  saat: [3600.0, [0, 0, 1, 0]], "gün": [86400.0, [0, 0, 1, 0]], "həftə": [604800.0, [0, 0, 1, 0]],
  B: [1.0, [0, 0, 0, 1]], KB: [1024.0, [0, 0, 0, 1]], MB: [1048576.0, [0, 0, 0, 1]],
  GB: [1073741824.0, [0, 0, 0, 1]], TB: [1099511627776.0, [0, 0, 0, 1]],
};
const ÜST = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "-": "⁻" };
const ÜSTDƏN = Object.fromEntries(Object.entries(ÜST).map(([a, b]) => [b, a]));
const vahiddir = a => Object.prototype.hasOwnProperty.call(VAHİDLƏR, a);

function vahidBirləşdir(...siyahılar) {
  const sıra = [];
  for (const s of siyahılar) for (const [a, n] of s) {
    const x = sıra.find(y => y[0] === a);
    if (x) x[1] += n; else sıra.push([a, n]);
  }
  return sıra.filter(x => x[1] !== 0);
}
const vahidQüvvət = (v, n) => vahidBirləşdir(v.map(([a, k]) => [a, k * n]));
function vahidƏmsal(v) { let e = 1.0; for (const [a, n] of v) e *= Math.pow(VAHİDLƏR[a][0], n); return e; }
function vahidÖlçü(v) {
  const ö = [0, 0, 0, 0];
  for (const [a, n] of v) VAHİDLƏR[a][1].forEach((x, i) => { ö[i] += x * n; });
  return ö.join(",");
}
function vahidMətn(v) {
  const yaz = (a, n) => n === 1 ? a : a + [...String(n)].map(c => ÜST[c]).join("");
  const s = v.filter(x => x[1] > 0).map(([a, n]) => yaz(a, n));
  const m = v.filter(x => x[1] < 0).map(([a, n]) => yaz(a, -n));
  let r = s.join("·") || (m.length ? "1" : "");
  if (m.length) r += "/" + m.join("·");
  return r;
}
function vahidTəhlil(mətn) {
  const s = mətn.replace(/ /g, "");
  if (!s) throw xəta("VahidXətası", "vahid boşdur", "ALQ-T084");
  const h = [];
  s.split("/").forEach((qisim, i) => {
    if (i > 1) throw xəta("VahidXətası", "`" + mətn + "` — yalnız bir `/` ola bilər", "ALQ-T084");
    if (qisim === "1" && i === 0) return;
    for (const p of qisim.replace(/\*/g, "·").split("·")) {
      let ad = [...p], üst = "";
      while (ad.length && ÜSTDƏN[ad[ad.length - 1]] !== undefined) üst = ÜSTDƏN[ad.pop()] + üst;
      ad = ad.join("");
      const k = ad.indexOf("^");
      if (k >= 0) { üst = ad.slice(k + 1); ad = ad.slice(0, k); }
      if (!vahiddir(ad)) throw xəta("VahidXətası", "`" + ad + "` naməlum vahiddir", "ALQ-T084");
      if (üst && !/^-?\d+$/.test(üst)) throw xəta("VahidXətası", "`" + p + "` — qüvvət tam ədəd olmalıdır", "ALQ-T084");
      const n = üst ? parseInt(üst, 10) : 1;
      h.push([ad, i === 1 ? -n : n]);
    }
  });
  return vahidBirləşdir(h);
}

const KƏMİYYƏT = {
  $mətn: k => mətnə(k.d.v) + " " + vahidMətn(k.d.vahid),
  dəyər: k => k.d.v,
  vahid: k => vahidMətn(k.d.vahid),
  çevir: (k, h) => kəmiyyətiÇevir(k, h),
};
const kəmiyyətdir = x => x instanceof Yerli && x.c === KƏMİYYƏT;
function kəmiyyət(v, vahid) {
  return vahid.length ? new Yerli("kəmiyyət", KƏMİYYƏT, { v, vahid }) : v;
}
/** `5 km` literalı */
function vahidli(v, mətn) { return kəmiyyət(v, vahidTəhlil(mətn)); }
const nisbət = (mənbə, hədəf) => vahidMətn(mənbə) === vahidMətn(hədəf) ? null : vahidƏmsal(mənbə) / vahidƏmsal(hədəf);
const VAHİD_ƏMƏLLƏRİ = { "+": "toplanmır", "-": "çıxılmır", "%": "bölünmür", "<": "müqayisə olunmur",
  ">": "müqayisə olunmur", "<=": "müqayisə olunmur", ">=": "müqayisə olunmur", "<=>": "müqayisə olunmur" };
const ƏMƏLLƏR = { "+": add, "-": sub, "*": mul, "/": div, "%": mod, "**": pow };

function kəmiyyətSadələşdir(n, v) {
  if (!v.length) return n;
  if (vahidÖlçü(v) === "0,0,0,0") return mul(n, vahidƏmsal(v));
  return kəmiyyət(n, v);
}

function kəmiyyətHesabla(op, a, b) {
  const ka = kəmiyyətdir(a), kb = kəmiyyətdir(b);
  const va = ka ? a.d.vahid : [], vb = kb ? b.d.vahid : [];
  const ad_ = v => vahidMətn(v) || "ədəd";
  if (VAHİD_ƏMƏLLƏRİ[op]) {
    if (!(ka && kb) || vahidÖlçü(va) !== vahidÖlçü(vb))
      throw xəta("VahidXətası", "`" + ad_(va) + "` və `" + ad_(vb) + "` " + VAHİD_ƏMƏLLƏRİ[op] + " — ölçülər uyğun deyil", "ALQ-T084");
    const r = nisbət(vb, va);
    const bd = r === null ? b.d.v : mul(b.d.v, r);
    if (op === "<=>") return cmp3(a.d.v, bd);
    if (op[0] === "<" || op[0] === ">") return cmp(op, a.d.v, bd);
    return kəmiyyət(ƏMƏLLƏR[op](a.d.v, bd), va);
  }
  const x = ka ? a.d.v : a, y = kb ? b.d.v : b;
  if (op === "*") return kəmiyyətSadələşdir(mul(x, y), vahidBirləşdir(va, vb));
  if (op === "/") return kəmiyyətSadələşdir(div(x, y), vahidBirləşdir(va, vahidQüvvət(vb, -1)));
  if (op === "**" && ka && !kb && typeof b === "bigint")
    return kəmiyyətSadələşdir(pow(x, b), vahidQüvvət(va, Number(b)));
  throw xəta("VahidXətası", "`" + op + "` operatoru `" + tip(a) + "` və `" + tip(b) + "` üçün tətbiq edilmir", "ALQ-T084");
}

function kəmiyyətBərabər(a, b) {
  if (!kəmiyyətdir(a) || !kəmiyyətdir(b) || vahidÖlçü(a.d.vahid) !== vahidÖlçü(b.d.vahid)) return false;
  return N(a.d.v) * vahidƏmsal(a.d.vahid) === N(b.d.v) * vahidƏmsal(b.d.vahid);
}

function kəmiyyətiÇevir(d, h) {
  const v = vahidTəhlil(h);
  if (!kəmiyyətdir(d)) {
    if (!ədəddir(d)) throw xəta("VahidXətası", "`" + tip(d) + "` vahidə çevrilmir", "ALQ-T084");
    return kəmiyyət(d, v);
  }
  if (vahidÖlçü(d.d.vahid) !== vahidÖlçü(v))
    throw xəta("VahidXətası", "`" + vahidMətn(d.d.vahid) + "` `" + vahidMətn(v) + "` vahidinə çevrilmir — ölçülər uyğun deyil", "ALQ-T084");
  const r = nisbət(d.d.vahid, v);
  return kəmiyyət(r === null ? d.d.v : mul(d.d.v, r), v);
}

function yüklənmiş(op, a, b) {
  if (kəmiyyətdir(a) || kəmiyyətdir(b)) return [kəmiyyətHesabla(op, a, b)];
  if (a instanceof Nümunə) {
    const m = a.s.metod(OP_METOD[op]);
    if (m !== undefined) return [m.call(a, b)];
  }
  return null;
}

function add(a, b) {
  const ta = typeof a, tb = typeof b;
  if (ta === "bigint" && tb === "bigint") return a + b;
  if (ta === "number" && tb === "number") return a + b;
  if (ta === "string") {
    if (tb !== "string")
      throw xəta("TipXətası", "`mətn` və `" + tip(b) + "` toplanmır", "ALQ-T008");
    return a + b;
  }
  if (ədəddir(a) && ədəddir(b)) return N(a) + N(b);
  const y = yüklənmiş("+", a, b); if (y) return y[0];
  if (Array.isArray(a)) {
    if (!Array.isArray(b))
      throw xəta("TipXətası", "`siyahı` və `" + tip(b) + "` toplanmır", "ALQ-T008");
    return a.concat(b);
  }
  throw opYoxdur("+", a, b);
}

function sub(a, b) {
  const ta = typeof a, tb = typeof b;
  if (ta === "bigint" && tb === "bigint") return a - b;
  if (ta === "number" && tb === "number") return a - b;
  if (ədəddir(a) && ədəddir(b)) return N(a) - N(b);
  const y = yüklənmiş("-", a, b); if (y) return y[0];
  if (a instanceof Dəst) return dəstOp("-", a, b);
  throw opYoxdur("-", a, b);
}

function mul(a, b) {
  const ta = typeof a, tb = typeof b;
  if (ta === "bigint" && tb === "bigint") return a * b;
  if (ta === "number" && tb === "number") return a * b;
  if (ədəddir(a) && ədəddir(b)) return N(a) * N(b);
  const y = yüklənmiş("*", a, b); if (y) return y[0];
  if (ta === "string") {
    if (tb !== "bigint")
      throw xəta("TipXətası", "mətn yalnız tam ədədə vurula bilər", "ALQ-T008");
    return b > 0n ? a.repeat(Number(b)) : "";
  }
  if (Array.isArray(a) && tb === "bigint") {
    const r = [];
    for (let i = 0n; i < b; i++) r.push(...a);
    return r;
  }
  throw opYoxdur("*", a, b);
}

function div(a, b) {
  if (ədəddir(a) && ədəddir(b)) {
    if (b == 0) {
      if (typeof a === "number" || typeof b === "number")
        return a > 0 ? Infinity : a < 0 ? -Infinity : NaN;
      throw xəta("BölməXətası", "sıfıra bölmək olmaz", "ALQ-R001");
    }
    return N(a) / N(b);
  }
  const y = yüklənmiş("/", a, b); if (y) return y[0];
  throw opYoxdur("/", a, b);
}

function idiv(a, b) {
  if (ədəddir(a) && ədəddir(b)) {
    if (b == 0) throw xəta("BölməXətası", "sıfıra bölmək olmaz", "ALQ-R001");
    if (typeof a === "bigint" && typeof b === "bigint") return a / b;
    const n = Math.floor(Math.abs(N(a)) / Math.abs(N(b)));
    return trunc((a >= 0) === (b >= 0) ? n : -n);
  }
  throw opYoxdur("~/", a, b);
}

function mod(a, b) {
  if (ədəddir(a) && ədəddir(b)) {
    if (b == 0) throw xəta("BölməXətası", "sıfıra bölmək olmaz", "ALQ-R001");
    if (typeof a === "bigint" && typeof b === "bigint") return a % b;
    const r = N(a) % N(b);
    return typeof a === "number" ? r : trunc(r);
  }
  const y = yüklənmiş("%", a, b); if (y) return y[0];
  throw opYoxdur("%", a, b);
}

function pow(a, b) {
  if (typeof a === "bigint" && typeof b === "bigint") {
    if (b >= 0n) return a ** b;
    if (a === 0n) throw xəta("BölməXətası", "sıfıra bölmək olmaz", "ALQ-R001");
    return Math.pow(Number(a), Number(b));
  }
  if (ədəddir(a) && ədəddir(b)) {
    const r = Math.pow(N(a), N(b));
    if (r !== r && N(a) < 0)
      throw xəta("RiyaziXəta", "mənfi ədədin kəsr qüvvəti kompleks ədəddir", "ALQ-R001");
    return r;
  }
  const y = yüklənmiş("**", a, b); if (y) return y[0];
  throw opYoxdur("**", a, b);
}

function bit(op, a, b) {
  if (a instanceof Dəst && (op === "|" || op === "&" || op === "^"))
    return dəstOp(op, a, b);
  if (typeof a === "number" || typeof b === "number") {
    if (ədəddir(a) && ədəddir(b))
      throw xəta("TipXətası", "bit əməliyyatları tam ədəd tələb edir", "ALQ-T008");
  }
  if (typeof a !== "bigint" || typeof b !== "bigint") throw opYoxdur(op, a, b);
  switch (op) {
    case "&": return a & b;
    case "|": return a | b;
    case "^": return a ^ b;
    case "<<": return a << b;
    case ">>": return a >> b;
    case ">>>": { const M = 1n << 64n; return (((a % M) + M) % M) >> b; }
  }
}

function dəstOp(op, a, b) {
  if (!(b instanceof Dəst))
    throw xəta("TipXətası", "dəst əməliyyatı dəst tələb edir", "ALQ-T008");
  const r = new Dəst();
  if (op === "|") { for (const x of a) r.əlavə(x); for (const x of b) r.əlavə(x); }
  else if (op === "&") { for (const x of a) if (b.var(x)) r.əlavə(x); }
  else if (op === "-") { for (const x of a) if (!b.var(x)) r.əlavə(x); }
  else { for (const x of a) if (!b.var(x)) r.əlavə(x); for (const x of b) if (!a.var(x)) r.əlavə(x); }
  return r;
}

function neg(x) {
  if (typeof x === "bigint" || typeof x === "number") return -x;
  if (kəmiyyətdir(x)) return kəmiyyət(neg(x.d.v), x.d.vahid);
  if (x instanceof Nümunə) {
    const m = x.s.metod("əks");
    if (m !== undefined) return m.call(x);
  }
  throw xəta("TipXətası", "`-` `" + tip(x) + "` tipinə tətbiq edilmir", "ALQ-T008");
}

function bnot(x) {
  if (typeof x !== "bigint") throw xəta("TipXətası", "`~` tam ədəd tələb edir", "ALQ-T008");
  return ~x;
}

/** Şərt `məntiq` olmalıdır. */
function ş(x) {
  if (x === true || x === false) return x;
  throw xəta("TipXətası", "şərt `məntiq` tipi olmalıdır, `" + tip(x) + "` gəlib",
    "ALQ-T007");
}

// ── Bərabərlik və müqayisə ──────────────────────────────────────────────

function eq(a, b) {
  if (kəmiyyətdir(a) || kəmiyyətdir(b)) return kəmiyyətBərabər(a, b);
  if (a === b) return typeof a !== "number" || a === a;
  const ta = typeof a, tb = typeof b;
  if (ta === "bigint" || ta === "number") {
    if (tb === "bigint" || tb === "number") return N(a) === N(b);
    return false;
  }
  if (a === null || b === null || a === undefined || b === undefined) return false;
  if (ta !== "object" || tb !== "object") return false;
  if (a instanceof Nümunə) {
    const m = a.s.metod("bərabərdir");
    if (m !== undefined) return m.call(a, b) === true;
    if (a.s.quruluş === "struktur" && b instanceof Nümunə && b.s === a.s)
      return mapEq(a.f, b.f);
    return false;
  }
  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (!eq(a[i], b[i])) return false;
    return true;
  }
  if (a instanceof Kortej) {
    if (!(b instanceof Kortej) || a.e.length !== b.e.length) return false;
    for (let i = 0; i < a.e.length; i++) if (!eq(a.e[i], b.e[i])) return false;
    return true;
  }
  if (a instanceof Lüğət) {
    if (!(b instanceof Lüğət) || a.size !== b.size) return false;
    for (const [k, v] of a.cütlər()) {
      const d = b.al(k);
      if (d === YOX || !eq(v, d)) return false;
    }
    return true;
  }
  if (a instanceof Dəst) {
    if (!(b instanceof Dəst) || a.size !== b.size) return false;
    for (const x of a) if (!b.var(x)) return false;
    return true;
  }
  if (a instanceof SDəyər) {
    return b instanceof SDəyər && a.sadalama === b.sadalama && a.ad === b.ad &&
      mapEq(a.sahələr, b.sahələr);
  }
  if (a instanceof Element) {
    return b instanceof Element && a.ad === b.ad && eq(a.atributlar, b.atributlar) &&
      eq(a.uşaqlar, b.uşaqlar);
  }
  if (a instanceof Bayt) {
    return b instanceof Bayt && a.u.length === b.u.length && a.u.every((x, i) => x === b.u[i]);
  }
  return false;
}

function mapEq(a, b) {
  if (a.size !== b.size) return false;
  for (const [k, v] of a) if (!b.has(k) || !eq(v, b.get(k))) return false;
  return true;
}

function ne(a, b) { return !eq(a, b); }

function müqayisə(a, b) {
  if (a instanceof Nümunə) {
    const m = a.s.metod("müqayisə");
    if (m !== undefined) {
      const n = m.call(a, b);
      return typeof n === "bigint" ? Number(n) : n;
    }
  }
  const ta = typeof a, tb = typeof b;
  if (ta === "string" && tb === "string") return mətnMüqayisə(a, b);
  if ((ta === "bigint" || ta === "number") && (tb === "bigint" || tb === "number")) {
    if (ta === tb) return a < b ? -1 : a > b ? 1 : 0;
    const x = N(a), y = N(b);
    return x < y ? -1 : x > y ? 1 : 0;
  }
  return null;
}

function müqXəta(a, b) {
  return xəta("TipXətası", "`" + tip(a) + "` və `" + tip(b) + "` müqayisə edilmir",
    "ALQ-T008");
}

function dəstMüq(op, a, b) {
  const alt = [...a].every(x => b.var(x));
  const üst = [...b].every(x => a.var(x));
  if (op === "<=") return alt;
  if (op === ">=") return üst;
  if (op === "<") return alt && a.size < b.size;
  return üst && a.size > b.size;
}

function cmp(op, a, b) {
  if (kəmiyyətdir(a) || kəmiyyətdir(b)) return kəmiyyətHesabla(op, a, b);
  if (typeof a === "bigint" && typeof b === "bigint") {
    switch (op) {
      case "<": return a < b; case ">": return a > b;
      case "<=": return a <= b; case ">=": return a >= b;
    }
  }
  if (a instanceof Dəst && b instanceof Dəst) return dəstMüq(op, a, b);
  const n = müqayisə(a, b);
  if (n === null || n !== n) {
    if (n !== n && ədəddir(a)) return false;
    throw müqXəta(a, b);
  }
  switch (op) {
    case "<": return n < 0; case ">": return n > 0;
    case "<=": return n <= 0; case ">=": return n >= 0;
  }
}
function lt(a, b) { return cmp("<", a, b); }
function gt(a, b) { return cmp(">", a, b); }
function le(a, b) { return cmp("<=", a, b); }
function ge(a, b) { return cmp(">=", a, b); }
function cmp3(a, b) {
  if (kəmiyyətdir(a) || kəmiyyətdir(b)) return kəmiyyətHesabla("<=>", a, b);
  const n = müqayisə(a, b);
  if (n === null) throw müqXəta(a, b);
  return BigInt(n);
}

/** Sıralama açarı: ədədlər < mətnlər < digər. */
function sıraMüq(a, b) {
  const sa = sıraSinfi(a), sb = sıraSinfi(b);
  if (sa !== sb) return sa < sb ? -1 : 1;
  if (sa === 0) { const x = typeof a === "boolean" ? (a ? 1 : 0) : a;
    const y = typeof b === "boolean" ? (b ? 1 : 0) : b;
    return x < y ? -1 : x > y ? 1 : 0; }
  if (sa === 1) {
    const x = [...a].map(c => hərfAçarı(c)), y = [...b].map(c => hərfAçarı(c));
    const n = Math.min(x.length, y.length);
    for (let i = 0; i < n; i++) {
      if (x[i][0] !== y[i][0]) return x[i][0] < y[i][0] ? -1 : 1;
      if (x[i][1] !== y[i][1]) return x[i][1] < y[i][1] ? -1 : 1;
    }
    return x.length === y.length ? 0 : x.length < y.length ? -1 : 1;
  }
  if (a instanceof Kortej && b instanceof Kortej) {
    const n = Math.min(a.e.length, b.e.length);
    for (let i = 0; i < n; i++) { const r = sıraMüq(a.e[i], b.e[i]); if (r) return r; }
    return a.e.length - b.e.length;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    const n = Math.min(a.length, b.length);
    for (let i = 0; i < n; i++) { const r = sıraMüq(a[i], b[i]); if (r) return r; }
    return a.length - b.length;
  }
  return obyektId(a) - obyektId(b);
}
function sıraSinfi(x) {
  const t = typeof x;
  if (t === "bigint" || t === "number" || t === "boolean") return 0;
  if (t === "string") return 1;
  return 2;
}

// ═══════════════════════════════════════════════════════════════════════
//  Üzv, indeks, dilim
// ═══════════════════════════════════════════════════════════════════════

function hesablananOxu(o, a, h) {
  for (let s = o.s; s; s = s.baza) {
    if (s.hesablananlar.has(a)) {
      if (s.tənbəllər.has(a)) {
        if (!o.k) o.k = new Map();
        if (!o.k.has(a)) o.k.set(a, h.call(o));
        return o.k.get(a);
      }
      break;
    }
  }
  return h.call(o);
}

function nümunəÜzvü(o, a) {
  if (o.aktyor && o.aktyor.emal === 0) {
    const m = o.s.metod(a);
    if (m !== undefined) return ad((...args) => aktyoraGöndər(o, m, a, args), a, "funksiya");
    // Xassəni oxumazdan əvvəl gözləyən mesajlar emal olunur
    poçtuBoşalt(o, null);
  }
  if (o.f.has(a)) return o.f.get(a);
  const s = o.s;
  const h = s.tap("hesablananlar", a);
  if (h !== undefined) return hesablananOxu(o, a, h);
  const m = s.metod(a);
  if (m !== undefined) return bağlı(m, o, a);
  const [v, d] = s.statikTap(a);
  if (v) return d;
  throw xəta("ArqumentXətası", "`" + s.ad + "` tipində `" + a + "` üzvü yoxdur",
    "ALQ-T006");
}

function üzv(o, a, təhlükəsiz) {
  if (o === null || o === undefined) {
    if (təhlükəsiz) return null;
    throw xəta("BoşDəyərXətası", "`boş` dəyərdə `" + a + "` üzvü yoxdur", "ALQ-R004");
  }
  if (o instanceof Nümunə) return nümunəÜzvü(o, a);
  if (o instanceof Modul) {
    if (o.üzvlər.has(a)) return o.üzvlər.get(a);
    throw xəta("ArqumentXətası", "`" + o.ad + "` modulunda `" + a + "` yoxdur", "ALQ-M002");
  }
  if (o instanceof Sinif) {
    const [v, d] = o.statikTap(a);
    if (v) return d;
    if (o.quruculər.has(a)) return new QurucuIst(o, a);
    throw xəta("ArqumentXətası", "`" + o.ad + "` sinfində statik `" + a + "` yoxdur",
      "ALQ-T006");
  }
  if (o instanceof Üst) return üstMetod(o.s, o.n, a);
  if (o instanceof Sadalama) {
    if (o.variantlar.has(a)) return o.variantlar.get(a);
    if (o.metodlar.has(a)) return o.metodlar.get(a);
    const m = sadalamaMetodu(o, a);
    if (m) return m;
    throw xəta("ArqumentXətası", "`" + o.ad + "` sadalamasında `" + a + "` yoxdur",
      "ALQ-T061");
  }
  if (o instanceof SDəyər) {
    if (o.sahələr.has(a)) return o.sahələr.get(a);
    if (o.sadalama.metodlar.has(a)) return bağlı(o.sadalama.metodlar.get(a), o, a);
    const m = sdəyərMetodu(o, a);
    if (m) return m;
    throw xəta("ArqumentXətası", "`" + o.ad + "` variantında `" + a + "` yoxdur",
      "ALQ-T006");
  }
  if (o instanceof Element && (a === "ad" || a === "atributlar" || a === "uşaqlar"))
    return o[a];
  // Funksiyanın adı — bəzəyicilər üçün (`f.ad`)
  if (a === "ad" && typeof o === "function") return o.$ad || o.name || "<anonim>";
  if (o instanceof Kortej && /^\d+$/.test(a)) {
    const i = Number(a);
    if (i >= o.e.length)
      throw xəta("İndeksXətası", "kortejdə " + i + " indeksi yoxdur", "ALQ-R002");
    return o.e[i];
  }
  const g = genişlətmələr.get(tipKökü(o));
  if (g && g.has(a)) return bağlı(g.get(a), o, a);
  const c = cədvəl(o);
  if (c !== null && c[a] !== undefined) {
    const f = c[a];
    return ad((...args) => {
      if (args.length && args[args.length - 1] instanceof Adlı)
        return f(o, ...args.slice(0, -1), args[args.length - 1].o);
      return f(o, ...args);
    }, a, "metod");
  }
  throw xəta("ArqumentXətası", "`" + tip(o) + "` tipində `" + a + "` üzvü yoxdur",
    "ALQ-T006");
}

// ── Aktyorlar (§ 9.12) ──────────────────────────────────────────────────

const AKTYORLAR = [], XƏTALI_MESAJLAR = [];

/** Mesajı poçta qoyur; nəticə — tənbəl `Gələcək`. */
function aktyoraGöndər(o, m, a, args) {
  const mesaj = { m, args, bitdi: false, nəticə: null, xəta: null, gözlənildi: false };
  if (!o.aktyor.poçt.length && !AKTYORLAR.includes(o)) AKTYORLAR.push(o);
  o.aktyor.poçt.push(mesaj);
  return new Gələcək(() => {
    mesaj.gözlənildi = true;
    poçtuBoşalt(o, mesaj);
    if (mesaj.xəta) throw mesaj.xəta;
    return mesaj.nəticə;
  }, o.s.ad + "." + a);
}

/** Mesajları gəliş sırası ilə emal edir (`qədər` daxil). */
function poçtuBoşalt(o, qədər) {
  const p = o.aktyor;
  while (p.poçt.length && !(qədər && qədər.bitdi)) {
    const m = p.poçt.shift();
    p.emal++;
    try {
      let d = m.m.apply(o, m.args);
      if (d instanceof Gələcək) d = d.al();
      m.nəticə = d;
    } catch (e0) {
      const e = xətaya(e0);
      if (e instanceof Dayanma || e0 instanceof Yayılan) throw e0;
      m.xəta = e;
      XƏTALI_MESAJLAR.push(m);
    } finally {
      p.emal--;
      m.bitdi = true;
    }
  }
}

/** Proqramın sonu: qalan mesajlar emal olunur; heç kimin gözləmədiyi
 *  mesajdakı xəta tutulmamış xəta kimi atılır. */
function aktyorlarıBoşalt() {
  while (AKTYORLAR.length) poçtuBoşalt(AKTYORLAR.shift(), null);
  for (const m of XƏTALI_MESAJLAR) if (!m.gözlənildi) throw m.xəta;
}

// ── Kanal (§ 9.13) ──────────────────────────────────────────────────────

function kanalAl(k) {
  const d = k.d;
  if (d.n.length) return [true, d.n.shift()];
  if (d.bağlı) return [false, null];
  throw xəta("DalanXətası", "kanal boşdur və ona göndərən yoxdur — dalan", "ALQ-R018");
}

const KANAL = {
  $mətn: k => "<kanal " + k.d.n.length + " element" + (k.d.bağlı ? ", bağlı" : "") + ">",
  göndər: (k, x) => {
    if (k.d.bağlı) throw xəta("KanalXətası", "bağlanmış kanala göndərmək olmaz", "ALQ-R019");
    k.d.n.push(x);
    return null;
  },
  al: k => kanalAl(k)[1],
  cəhdAl: k => k.d.n.length ? k.d.n.shift() : null,
  bağla: k => { k.d.bağlı = true; return null; },
  bağlıdır: k => k.d.bağlı,
  boşdur: k => !k.d.n.length,
  uzunluq: k => BigInt(k.d.n.length),
};

function* kanalDövrü(k) {
  for (;;) {
    const [var_, x] = kanalAl(k);
    if (!var_) return;
    yield x;
  }
}

function üzvQoy(o, a, v) {
  if (o instanceof Nümunə && o.aktyor && o.aktyor.emal === 0) poçtuBoşalt(o, null);
  if (o instanceof Nümunə) {
    const y = o.s.tap("yazıcılar", a);
    if (y !== undefined) { y.call(o, v); return; }
    if (o.s.tap("hesablananlar", a) !== undefined)
      throw xəta("ArqumentXətası", "`" + a + "` yalnız oxunan xassədir", "ALQ-T020");
    o.f.set(a, v);
    return;
  }
  if (o instanceof Sinif) { o.statiklər.set(a, v); return; }
  if (o instanceof Modul) { o.üzvlər.set(a, v); return; }
  throw xəta("ArqumentXətası", "`" + tip(o) + "` tipinin üzvü dəyişdirilə bilməz",
    "ALQ-T021");
}

function uzunluqPy(o) {
  if (typeof o === "string") return [...o].length;
  return o.length;
}

function ind(o, i) {
  if (Array.isArray(o)) {
    if (typeof i !== "bigint")
      throw xəta("TipXətası", "indeks tam ədəd olmalıdır, `" + tip(i) + "` gəlib", "ALQ-T009");
    const n = o.length;
    let j = Number(i);
    if (j < 0) j += n;
    if (j < 0 || j >= n)
      throw xəta("İndeksXətası", "indeks " + i + " diapazondan kənardır (uzunluq " + n + ")",
        "ALQ-R002");
    return o[j];
  }
  if (o instanceof Lüğət) {
    const d = o.al(i);
    if (d !== YOX) return d;
    throw xəta("AçarXətası", "lüğətdə `" + mətnə(i) + "` açarı yoxdur", "ALQ-R003");
  }
  if (o instanceof Nümunə) {
    const m = o.s.metod("al");
    if (m !== undefined) return m.call(o, i);
  }
  if (typeof o === "string" || o instanceof Kortej || o instanceof Bayt) {
    if (typeof i !== "bigint")
      throw xəta("TipXətası", "indeks tam ədəd olmalıdır, `" + tip(i) + "` gəlib", "ALQ-T009");
    const a = typeof o === "string" ? [...o] : o instanceof Kortej ? o.e : o.u;
    const n = a.length;
    let j = Number(i);
    if (j < 0) j += n;
    if (j < 0 || j >= n)
      throw xəta("İndeksXətası", "indeks " + i + " diapazondan kənardır (uzunluq " + n + ")",
        "ALQ-R002");
    return o instanceof Bayt ? BigInt(a[j]) : a[j];
  }
  throw xəta("TipXətası", "`" + tip(o) + "` indekslənə bilməz", "ALQ-T009");
}

function indQoy(o, i, v) {
  if (o instanceof Nümunə) {
    const m = o.s.metod("qoy");
    if (m !== undefined) { m.call(o, i, v); return; }
  }
  if (o instanceof Lüğət) { o.qoy(i, v); return; }
  if (Array.isArray(o)) {
    const n = o.length;
    let j = typeof i === "bigint" ? Number(i) : NaN;
    if (j < 0) j += n;
    if (!(j >= 0 && j < n))
      throw xəta("İndeksXətası", "indeks " + mətnə(i) + " diapazondan kənardır (uzunluq " + n + ")",
        "ALQ-R002");
    o[j] = v;
    return;
  }
  if (typeof o === "string")
    throw xəta("TipXətası", "`mətn` dəyişməzdir — simvolu dəyişmək olmaz", "ALQ-T021");
  throw xəta("TipXətası", "`" + tip(o) + "` indekslə dəyişdirilə bilməz", "ALQ-T009");
}

function dilim(o, b, s, xaric) {
  let a;
  if (Array.isArray(o)) a = o;
  else if (typeof o === "string") a = [...o];
  else if (o instanceof Kortej) a = o.e;
  else if (o instanceof Bayt) a = [...o.u];
  else throw xəta("TipXətası", "`" + tip(o) + "` dilimlənə bilməz", "ALQ-T009");
  const n = a.length;
  const sonVar = s !== null && s !== undefined;
  if (b === null || b === undefined) b = 0n;
  if (!sonVar) s = BigInt(n);
  if (typeof b !== "bigint" || typeof s !== "bigint")
    throw xəta("TipXətası", "dilim hədləri tam ədəd olmalıdır", "ALQ-T009");
  let x = Number(b), y = Number(s);
  if (x < 0) x += n;
  if (y < 0) y += n;
  if (sonVar && !xaric) y += 1;
  const r = a.slice(Math.max(0, x), Math.min(n, y));
  if (typeof o === "string") return r.join("");
  if (o instanceof Kortej) return new Kortej(r);
  if (o instanceof Bayt) return new Bayt(Uint8Array.from(r));
  return r;
}

/** Python-un `s[b:e]` dilimi (metodlar üçün). */
function pyDilim(a, b, e) {
  const n = a.length;
  let x = b === null || b === undefined ? 0 : Number(b);
  let y = e === null || e === undefined ? n : Number(e);
  if (x < 0) x = Math.max(0, x + n);
  if (y < 0) y = Math.max(0, y + n);
  return a.slice(Math.min(x, n), Math.min(y, n));
}

// ═══════════════════════════════════════════════════════════════════════
//  İterasiya
// ═══════════════════════════════════════════════════════════════════════

function iter(x) {
  if (Array.isArray(x)) return x;
  if (typeof x === "string") return x;
  if (x instanceof Diapazon || x instanceof Gen || x instanceof Dəst) return x;
  if (x instanceof Lüğət) return [...x.açarlar()];
  if (x instanceof Kortej) return x.e;
  if (x instanceof Bayt) return [...x.u].map(BigInt);
  if (x instanceof Nümunə) {
    const m = x.s.metod("iterator");
    if (m !== undefined) return iter(m.call(x));
    const u = x.s.metod("uzunluq"), a = x.s.metod("al");
    if (u !== undefined && a !== undefined) {
      const n = u.call(x);
      return (function* () { for (let i = 0n; i < n; i++) yield ind(x, i); })();
    }
  }
  if (x instanceof Sadalama) return x.sıra.map(a => x.variantlar.get(a));
  if (x instanceof Element) return x.uşaqlar;
  if (x instanceof Yerli && x.c === KANAL) return kanalDövrü(x);
  throw xəta("TipXətası", "`" + tip(x) + "` üzərində dövr qurulmur", "ALQ-T009");
}

function siyahıya(x) { return Array.isArray(x) ? x.slice() : [...iter(x)]; }

/** Dağıtma: `dəyişən a, b = ...` */
function dağıt(v, say, qalan) {
  let el;
  try { el = siyahıya(v); }
  catch (e) { throw xəta("TipXətası", "`" + tip(v) + "` dağıtıla bilməz", "ALQ-T001"); }
  if (qalan < 0) {
    if (el.length !== say)
      throw xəta("ArqumentXətası", say + " ad gözlənilirdi, " + el.length + " dəyər var",
        "ALQ-T001");
    return el;
  }
  if (el.length < say - 1)
    throw xəta("ArqumentXətası", "dağıtma üçün element çatmır", "ALQ-T001");
  const sonra = say - 1 - qalan;
  const r = el.slice(0, qalan);
  r.push(el.slice(qalan, el.length - sonra));
  r.push(...el.slice(el.length - sonra));
  return r;
}

function diapazon(b, s, a, xaric) {
  for (const [ad_, d] of [["başlanğıc", b], ["son", s]]) {
    if (typeof d !== "bigint" && !(typeof d === "string" && [...d].length === 1))
      throw xəta("TipXətası", "diapazonun " + ad_ + " hissəsi tam ədəd olmalıdır, `" +
        tip(d) + "` gəlib", "ALQ-T001");
  }
  if (typeof b === "string") b = BigInt(b.codePointAt(0));
  if (typeof s === "string") s = BigInt(s.codePointAt(0));
  return new Diapazon(b, s, a, xaric);
}

function addımla(d, a) {
  if (d instanceof Diapazon) return new Diapazon(d.b, d.s, a, d.xaric);
  return d;
}

// ═══════════════════════════════════════════════════════════════════════
//  Tip yoxlama və çevirmə
// ═══════════════════════════════════════════════════════════════════════

const SADƏ_TİPLƏR = {
  "tam": x => typeof x === "bigint",
  "onluq": x => typeof x === "number",
  "mətn": x => typeof x === "string",
  "simvol": x => typeof x === "string" && x.length <= 2,
  "məntiq": x => typeof x === "boolean",
  "bayt": x => x instanceof Bayt,
  "siyahı": x => Array.isArray(x),
  "lüğət": x => x instanceof Lüğət,
  "dəst": x => x instanceof Dəst,
  "kortej": x => x instanceof Kortej,
  "istənilən": () => true,
  "heç": x => x === null,
};

/**
 * Tip təsviri: {a: "tam", i: ixtiyari, h: () => hədəf} və ya {v: [...]}.
 */
function tipUyğun(x, t) {
  if (t.v) return t.v.some(s => tipUyğun(x, s));
  if (!t.a) return false;
  if (x === null || x === undefined) return t.a === "heç" || t.a === "boş" || !!t.i;
  const s = SADƏ_TİPLƏR[t.a];
  if (s) return s(x);
  let h;
  try { h = t.h(); } catch (e) { return false; }
  if (h instanceof TipAlias) return tipUyğun(x, h.tip);
  if (h instanceof Sinif) {
    if (x instanceof Nümunə) return x.s.altdır(h) || x.s.interfeyslər.includes(h.ad);
    return false;
  }
  if (h instanceof Sadalama) return x instanceof SDəyər && x.sadalama === h;
  if (h instanceof _XətaSinfi) return x instanceof Nümunə && x.s.ad === h.ad;
  return false;
}

function çevir(x, h) {
  if (vahiddir(h) && (kəmiyyətdir(x) || ədəddir(x))) return kəmiyyətiÇevir(x, h);
  switch (h) {
    case "tam":
      if (typeof x === "boolean") return x ? 1n : 0n;
      if (typeof x === "bigint") return x;
      if (typeof x === "number") return trunc(x);
      if (typeof x === "string") {
        const n = tamOxu(x);
        if (n === null) throw xəta("ÇevrilməXətası", '"' + x + '" tam ədədə çevrilə bilmir', "ALQ-R005");
        return n;
      }
      break;
    case "onluq":
      if (typeof x === "boolean") return x ? 1 : 0;
      if (ədəddir(x)) return N(x);
      if (typeof x === "string") {
        const n = onluqOxu(x);
        if (n === null) throw xəta("ÇevrilməXətası", '"' + x + '" onluq ədədə çevrilə bilmir', "ALQ-R005");
        return n;
      }
      break;
    case "mətn": return mətnə(x);
    case "məntiq":
      if (typeof x === "boolean") return x;
      if (typeof x === "string") {
        const k = kiçiyə(x.trim());
        if (["doğru", "dogru", "true", "1"].includes(k)) return true;
        if (["yanlış", "yanlis", "false", "0"].includes(k)) return false;
      }
      throw xəta("ÇevrilməXətası", "məntiqi tipə açıq çevirmə tələb olunur", "ALQ-R005");
    case "siyahı": return siyahıya(x);
    case "dəst": return new Dəst(iter(x));
  }
  throw xəta("ÇevrilməXətası", "`" + tip(x) + "` → `" + h + "` çevrilməsi mümkün deyil",
    "ALQ-T014");
}

function üzvlük(e, k) {
  if (k instanceof Nümunə) {
    const m = k.s.metod("ehtiva");
    if (m !== undefined) return m.call(k, e) === true;
  }
  if (k instanceof Lüğət) { try { return k.var(e); } catch (x) { return false; } }
  if (k instanceof Dəst) return k.var(e);
  if (Array.isArray(k)) return k.some(x => eq(x, e));
  if (k instanceof Kortej) return k.e.some(x => eq(x, e));
  if (typeof k === "string") {
    if (typeof e !== "string")
      throw xəta("TipXətası", "`içindədir` mətndə mətn gözləyir", "ALQ-T008");
    return k.includes(e);
  }
  if (k instanceof Diapazon) return k.ehtiva(e);
  throw xəta("TipXətası", "`içindədir` `" + tip(k) + "` tipinə tətbiq edilmir", "ALQ-T008");
}

function açMəcburi(x) {
  if (x === null || x === undefined)
    throw xəta("BoşDəyərXətası", "`!` operatoru `boş` dəyərə tətbiq edildi", "ALQ-R004");
  return x;
}

/** `nəticə?` — Xəta nümunəsini yuxarı ötürür. */
class Yayılan { constructor(d) { this.d = d; } }
function yay(x) {
  if (x instanceof Nümunə && x.s.ad === "Xəta") throw new Yayılan(x);
  return x;
}

function gözlə(x) {
  if (x instanceof Gələcək) return x.al();
  if (Array.isArray(x) && x.some(d => d instanceof Gələcək)) {
    for (const d of x) if (d instanceof Gələcək) d.başlat();
    return x.map(gözlə);
  }
  if (x instanceof Kortej && x.e.some(d => d instanceof Gələcək)) {
    for (const d of x.e) if (d instanceof Gələcək) d.başlat();
    return new Kortej(x.e.map(gözlə));
  }
  return x;
}

// ── Xəta obyekti (`tut x`) ──────────────────────────────────────────────

function xətaObyekti(x) {
  if (x.dəyər !== null) return x.dəyər;
  const s = new Sinif({ ad: x.tip });
  const n = new Nümunə(s);
  n.f.set("mesaj", x.mesaj);
  n.f.set("kod", x.kod || null);
  n.f.set("tip", x.tip);
  return n;
}

function at(d) {
  if (d instanceof Nümunə) {
    const m = d.f.has("mesaj") ? mətnə(d.f.get("mesaj")) : "";
    return new AlqorXəta(d.s.ad, m, "", d);
  }
  if (d instanceof AlqorXəta) return d;
  return new AlqorXəta("Xəta", mətnə(d), "", d);
}

class _XətaSinfi {
  constructor(ad_) { this.ad = ad_; }
  yarat(args) {
    const [poz, adlı] = arqAyır(args);
    const n = new Nümunə(new Sinif({ ad: this.ad }));
    n.f.set("mesaj", poz.length ? mətnə(poz[0]) : "");
    n.f.set("tip", this.ad);
    n.f.set("kod", adlı && "kod" in adlı ? adlı.kod : null);
    n.f.set("səbəb", adlı && "səbəb" in adlı ? adlı.səbəb : null);
    if (adlı) for (const k of Object.keys(adlı)) if (!n.f.has(k)) n.f.set(k, adlı[k]);
    return n;
  }
}

// ── Naxış uyğunlaşdırma köməkçiləri ─────────────────────────────────────

function naxışDiapazon(v, b, s, xaric) {
  if (!ədəddir(v)) return false;
  return le(b, v) && (xaric ? lt(v, s) : le(v, s));
}

function naxışKortej(v, n) {
  const a = Array.isArray(v) ? v : v instanceof Kortej ? v.e : null;
  return a !== null && a.length === n ? a : null;
}

function naxışSiyahı(v, n, qalan) {
  if (!Array.isArray(v)) return null;
  if (qalan) return v.length >= n ? v : null;
  return v.length === n ? v : null;
}

function naxışObyekt(v, yol, hədəf) {
  if (!yol.length) return true;
  if (v instanceof SDəyər)
    return v.ad === yol[yol.length - 1] || (yol.length >= 2 &&
      v.sadalama.ad === yol[yol.length - 2] && v.ad === yol[yol.length - 1]);
  if (v instanceof Nümunə) {
    let h;
    try { h = hədəf(); } catch (e) { return false; }
    return h instanceof Sinif && v.s.altdır(h);
  }
  return false;
}

const ATLA = Symbol("atla");
function sdSahə(v, i) {
  if (!(v instanceof SDəyər)) return ATLA;
  const s = [...v.sahələr.values()];
  return i < s.length ? s[i] : YOX;
}

// ═══════════════════════════════════════════════════════════════════════
//  Format (şablon mətnlərində `{x:.2f}`)
// ═══════════════════════════════════════════════════════════════════════

function formatla(d, f) {
  if (!f) return mətnə(d);
  try {
    if (f.endsWith(",az")) {
      const n = N(d);
      const ə = Number.isInteger(n) ? qruplaşdır(sabitNöqtə(n, 0), ",")
        : qruplaşdır(sabitNöqtə(n, 2), ",");
      return ə.replace(/,/g, "\u00a0").replace(".", ",");
    }
    if (/^\.\d+$/.test(f)) {
      const n = typeof d === "boolean" ? (d ? 1 : 0) : N(d);
      if (typeof n !== "number") return mətnə(d);
      return sabitNöqtə(n, parseInt(f.slice(1), 10));
    }
    if (["x", "X", "b", "o"].includes(f) && ədəddir(d))
      return pyFormat(typeof d === "number" ? trunc(d) : d, f);
    const r = pyFormat(d, f);
    return r === null ? mətnə(d) : r;
  } catch (e) {
    if (e instanceof AlqorXəta) return mətnə(d);
    throw e;
  }
}

function qruplaşdır(s, ayırıcı) {
  const m = /^(-?)(\d+)(.*)$/.exec(s);
  if (!m) return s;
  return m[1] + m[2].replace(/\B(?=(\d{3})+(?!\d))/g, ayırıcı) + m[3];
}

/** Python format mini-dili: [[doldur]düzləndir][işarə][#][0][en][,_][.dəqiqlik][tip] */
function pyFormat(d, spec) {
  const m = /^(?:(.)?([<>=^]))?([+\- ])?(#)?(0)?(\d+)?([,_])?(?:\.(\d+))?([bcdeEfFgGnosxX%])?$/u.exec(spec);
  if (!m) return null;
  let [, doldur, düz, işarə, alt, sıfır, en, qrup, dəq, t] = m;
  en = en ? parseInt(en, 10) : 0;
  const p = dəq !== undefined ? parseInt(dəq, 10) : null;
  if (sıfır && !düz) { doldur = "0"; düz = "="; }
  doldur = doldur || " ";
  let s, ədədi = ədəddir(d) || typeof d === "boolean";
  if (typeof d === "boolean" && !t) ədədi = false;
  if (!ədədi) {
    if (t && t !== "s") return null;
    s = mətnə(d);
    if (p !== null) s = [...s].slice(0, p).join("");
    return yerləşdir(s, en, doldur, düz || "<", "");
  }
  let x = typeof d === "boolean" ? (d ? 1n : 0n) : d;
  let mənfi = typeof x === "bigint" ? x < 0n : (x < 0 || Object.is(x, -0));
  const mütləq = typeof x === "bigint" ? (mənfi ? -x : x) : Math.abs(x);
  if (!t) t = typeof x === "bigint" ? "d" : (p !== null ? "g" : "");
  let gövdə, ön = "";
  switch (t) {
    case "d": case "n":
      if (typeof x !== "bigint") return null;
      gövdə = mütləq.toString(); break;
    case "b": case "o": case "x": case "X":
      if (typeof x !== "bigint") return null;
      gövdə = mütləq.toString({ b: 2, o: 8, x: 16, X: 16 }[t]);
      if (t === "X") gövdə = gövdə.toUpperCase();
      if (alt) ön = "0" + (t === "X" ? "X" : t);
      break;
    case "c": gövdə = String.fromCodePoint(Number(mütləq)); break;
    case "f": case "F": gövdə = sabitNöqtə(N(mütləq), p === null ? 6 : p);
      if (!isFinite(N(mütləq))) gövdə = t === "F" ? gövdə.toUpperCase() : gövdə;
      break;
    case "%": gövdə = sabitNöqtə(N(mütləq) * 100, p === null ? 6 : p) + "%"; break;
    case "e": case "E": gövdə = eksp(N(mütləq), p === null ? 6 : p);
      if (t === "E") gövdə = gövdə.toUpperCase(); break;
    case "g": case "G": gövdə = ümumi(N(mütləq), p === null ? 6 : p, !!alt);
      if (t === "G") gövdə = gövdə.toUpperCase(); break;
    case "": gövdə = onluqRepr(mütləq); break;
    default: return null;
  }
  if (qrup) {
    const [tam_, ...q] = gövdə.split(".");
    gövdə = (t === "b" || t === "o" || t === "x" || t === "X")
      ? tam_.replace(/\B(?=([0-9a-fA-F]{4})+(?![0-9a-fA-F]))/g, qrup)
      : qruplaşdır(tam_, qrup);
    if (q.length) gövdə += "." + q.join(".");
  }
  let iş = mənfi ? "-" : işarə === "+" ? "+" : işarə === " " ? " " : "";
  if (mənfi && /^0(\.0*)?%?$/.test(gövdə) && typeof x === "number" && !Object.is(x, -0) && x > -0.5e-300) iş = "-";
  return yerləşdir(gövdə, en, doldur, düz || ">", iş + ön);
}

function yerləşdir(s, en, doldur, düz, ön) {
  const uz = [...ön].length + [...s].length;
  if (uz >= en) return ön + s;
  const boş = en - uz;
  if (düz === "<") return ön + s + doldur.repeat(boş);
  if (düz === ">") return doldur.repeat(boş) + ön + s;
  if (düz === "=") return ön + doldur.repeat(boş) + s;
  const sol = Math.floor(boş / 2);
  return doldur.repeat(sol) + ön + s + doldur.repeat(boş - sol);
}

function eksp(x, p) {
  if (!isFinite(x)) return onluqRepr(x);
  let s = x.toExponential(p);
  // JS yarımı yuxarı yuvarlaqlaşdırır; Python dəqiq — fərq çox nadirdir
  let [m, e] = s.split("e");
  const n = parseInt(e, 10);
  return m + "e" + (n < 0 ? "-" : "+") + String(Math.abs(n)).padStart(2, "0");
}

function ümumi(x, p, alt) {
  if (!isFinite(x)) return onluqRepr(x);
  if (p === 0) p = 1;
  if (x === 0) return alt ? "0." + "0".repeat(p - 1) : "0";
  const e = parseInt(x.toExponential(p - 1).split("e")[1], 10);
  let s;
  if (e >= -4 && e < p) {
    s = sabitNöqtə(x, p - 1 - e);
    if (!alt && s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
  } else {
    s = eksp(x, p - 1);
    if (!alt) s = s.replace(/\.?0+e/, "e");
  }
  return s;
}

// ═══════════════════════════════════════════════════════════════════════
//  Daxili tiplərin metodları
// ═══════════════════════════════════════════════════════════════════════

const genişlətmələr = new Map();
function genişlətmə(t, a, f) {
  if (!genişlətmələr.has(t)) genişlətmələr.set(t, new Map());
  genişlətmələr.get(t).set(a, f);
}

function doğrudur(f, ...a) { return ç(f, ...a) === true; }

function kəsSimvol(s, c, sol, sağ) {
  const a = [...s];
  const set = c === undefined || c === null ? null : new Set(c);
  const boşluq = x => /\s/.test(x);
  const at_ = x => set ? set.has(x) : boşluq(x);
  let i = 0, j = a.length;
  if (sol) while (i < j && at_(a[i])) i++;
  if (sağ) while (j > i && at_(a[j - 1])) j--;
  return a.slice(i, j).join("");
}

function pyBöl(s, ayırıcı, maks) {
  maks = maks === undefined || maks === null ? -1 : Number(maks);
  if (ayırıcı === undefined || ayırıcı === null) {
    const r = [];
    let t = s.replace(/^\s+/, "");
    while (t.length) {
      if (maks >= 0 && r.length === maks) { r.push(t.replace(/\s+$/, "")); break; }
      const m = /\s+/.exec(t);
      if (!m) { r.push(t); break; }
      r.push(t.slice(0, m.index));
      t = t.slice(m.index + m[0].length);
    }
    return r;
  }
  if (ayırıcı === "") throw xəta("DəyərXətası", "boş ayırıcı", "ALQ-R005");
  const h = s.split(ayırıcı);
  if (maks >= 0 && h.length > maks + 1)
    return [...h.slice(0, maks), h.slice(maks).join(ayırıcı)];
  return h;
}

function mərkəz(s, n, c) {
  n = Number(n); c = c === undefined ? " " : c;
  const uz = [...s].length;
  if (n <= uz) return s;
  const marg = n - uz;
  const sol = Math.floor(marg / 2) + (marg & n & 1);
  return c.repeat(sol) + s + c.repeat(marg - sol);
}

function indeksYoxla(a, i) {
  const n = a.length;
  let j = Number(tamƏdəd(i, "sil"));
  if (j < 0) j += n;
  if (j < 0 || j >= n)
    throw xəta("İndeksXətası", "indeks " + i + " diapazondan kənardır (uzunluq " + n + ")",
      "ALQ-R002");
  return j;
}

function utf8(s) { return new TextEncoder().encode(s); }

function base64Kodla(u8) {
  let s = "";
  for (const b of u8) s += String.fromCharCode(b);
  return typeof btoa === "function" ? btoa(s) : Buffer.from(u8).toString("base64");
}
function base64Aç(m) {
  const s = typeof atob === "function" ? atob(m) : Buffer.from(m, "base64").toString("latin1");
  return Uint8Array.from(s, c => c.charCodeAt(0));
}

const MƏTN = {
  "uzunluq": s => BigInt([...s].length),
  "baytUzunluğu": s => BigInt(utf8(s).length),
  "böyüyə": s => böyüyə(s),
  "kiçiyə": s => kiçiyə(s),
  "başBöyük": s => başBöyük(s),
  "hərSözBöyük": s => hərSözBöyük(s),
  "kəs": (s, c) => kəsSimvol(s, c, true, true),
  "başKəs": (s, c) => kəsSimvol(s, c, true, false),
  "sonKəs": (s, c) => kəsSimvol(s, c, false, true),
  "əvəz": (s, a, b) => s.split(a).join(b),
  "əvəzİlk": (s, a, b) => { const i = s.indexOf(a); return i < 0 ? s : s.slice(0, i) + b + s.slice(i + a.length); },
  "böl": (s, a, m) => pyBöl(s, a, m),
  "sətirlər": s => s.split("\n"),
  "simvollar": s => [...s],
  "sözlər": s => pyBöl(s),
  "baytlar": s => [...utf8(s)].map(BigInt),
  "birləşdir": (s, k) => siyahıya(k).map(mətnə).join(s),
  "ehtiva": (s, a) => s.includes(a),
  "başlayır": (s, a) => s.startsWith(a),
  "bitir": (s, a) => s.endsWith(a),
  "tap": (s, a) => { const i = s.indexOf(a); return i < 0 ? null : BigInt([...s.slice(0, i)].length); },
  "sonTap": (s, a) => { const i = s.lastIndexOf(a); return i < 0 ? null : BigInt([...s.slice(0, i)].length); },
  "hamısınıTap": (s, a) => { const r = []; if (!a) return r; let i = s.indexOf(a);
    while (i >= 0) { r.push(BigInt([...s.slice(0, i)].length)); i = s.indexOf(a, i + a.length); } return r; },
  "say": (s, a) => { if (a === "") return BigInt([...s].length + 1); return BigInt(s.split(a).length - 1); },
  "dilim": (s, b, e) => pyDilim([...s], b, e).join(""),
  "təkrar": (s, n) => { tamƏdəd(n, "təkrar"); return n > 0n ? s.repeat(Number(n)) : ""; },
  "tərs": s => [...s].reverse().join(""),
  "doldur": (s, n, c) => s + (c === undefined ? " " : c).repeat(Math.max(0, Number(n) - [...s].length)),
  "solDoldur": (s, n, c) => (c === undefined ? " " : c).repeat(Math.max(0, Number(n) - [...s].length)) + s,
  "sağDoldur": (s, n, c) => s + (c === undefined ? " " : c).repeat(Math.max(0, Number(n) - [...s].length)),
  "mərkəz": (s, n, c) => mərkəz(s, n, c),
  "boşdur": s => s.length === 0,
  "yalnızBoşluq": s => s.length > 0 && /^\s+$/.test(s),
  "rəqəmdir": s => s.length > 0 && [...s].every(rəqəmdir),
  "hərfdir": s => s.length > 0 && [...s].every(hərfdir),
  "müqayisə": (s, d) => BigInt(mətnMüqayisə(s, d)),
  "müqayisəHərfsiz": (s, d) => BigInt(mətnMüqayisə(kiçiyə(s), kiçiyə(d))),
  "normalizasiya": s => s.normalize("NFC"),
  "latınla": s => latınla(s),
  "URLKodla": s => encodeURIComponent(s).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase()),
  "URLAç": s => decodeURIComponent(s),
  "base64Kodla": s => base64Kodla(utf8(s)),
  "base64Aç": s => new TextDecoder().decode(base64Aç(s)),
  "HTMLQaç": s => htmlQaç(s),
  "formatla": (s, ...a) => {
    let n = s;
    a.forEach((d, i) => { const m = mətnə(d); n = n.replace("{}", () => m); n = n.split("{" + i + "}").join(m); });
    return n;
  },
  "mətnƏt": s => s,
  "klonla": s => s,
  "tamƏt": s => { const n = tamOxu(s); if (n === null) throw xəta("ÇevrilməXətası", '"' + s + '" tam ədəd deyil', "ALQ-R005"); return n; },
  "saitdir": s => [...s].length === 1 && SAITLER.has(s),
  "samitdir": s => [...s].length === 1 && hərfdir(s) && !SAITLER.has(s),
  "qalınSait": s => [...s].length === 1 && QALIN.has(s),
  "incəSait": s => [...s].length === 1 && INCE.has(s),
};

function sıralaAçarla(a, f) {
  const c = a.map(x => [f ? ç(f, x) : x, x]);
  c.sort((p, q) => sıraMüq(p[0], q[0]));
  return c.map(p => p[1]);
}

function ilkMin(a, böyük) {
  let ən = a[0];
  for (let i = 1; i < a.length; i++) {
    const r = sıraMüq(a[i], ən);
    if (böyük ? r > 0 : r < 0) ən = a[i];
  }
  return ən;
}

function cəmlə(a, başlanğıc) {
  let s = başlanğıc === undefined ? 0n : başlanğıc;
  for (const x of a) {
    if (!ədəddir(x))
      throw xəta("TipXətası", "ədəd gözlənilirdi, `" + tip(x) + "` gəlib", "ALQ-T004");
    s = add(s, x);
  }
  return s;
}

const SİYAHI = {
  "əlavə": (s, x) => { s.push(x); return null; },
  "əlavəHamısı": (s, k) => { s.push(...siyahıya(k)); return null; },
  "daxilEt": (s, j, x) => {
    let i = Number(j); const n = s.length;
    if (i < 0) i = Math.max(0, i + n); if (i > n) i = n;
    s.splice(i, 0, x); return null;
  },
  "sil": (s, i) => s.splice(indeksYoxla(s, i), 1)[0],
  "silDəyər": (s, d) => { const j = s.findIndex(x => eq(x, d)); if (j < 0) return false; s.splice(j, 1); return true; },
  "silHamısı": (s, d) => { const q = s.filter(x => !eq(x, d)); s.length = 0; s.push(...q); return null; },
  "sonunuSil": s => {
    if (!s.length) throw xəta("BoşKolleksiyaXətası", "boş siyahıdan element silinmir", "ALQ-R014");
    return s.pop();
  },
  "təmizlə": s => { s.length = 0; return null; },
  "sırala": (s, f) => {
    const q = f === undefined || f === null ? sıralaAçarla(s)
      : s.slice().sort((a, b) => Number(ç(f, a, b)));
    s.length = 0; s.push(...q); return null;
  },
  "sıralaAçar": (s, f) => { const q = sıralaAçarla(s, f); s.length = 0; s.push(...q); return null; },
  "qarışdır": s => { for (let i = s.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [s[i], s[j]] = [s[j], s[i]]; } return null; },
  "tərsinəÇevir": s => { s.reverse(); return null; },
  "sıralanmış": (s, f) => sıralaAçarla(s, f === null ? undefined : f),
  "tərs": s => s.slice().reverse(),
  "dilim": (s, b, e) => pyDilim(s, b, e),
  "çevir": (s, f) => s.map(x => ç(f, x)),
  "filtr": (s, f) => s.filter(x => ç(f, x) === true),
  "yığ": (s, b, f) => { let n = b; for (const x of s) n = ç(f, n, x); return n; },
  "yığSağdan": (s, b, f) => { let n = b; for (const x of s.slice().reverse()) n = ç(f, n, x); return n; },
  "düzlə": s => { const r = []; for (const x of s) Array.isArray(x) ? r.push(...x) : r.push(x); return r; },
  "düzləÇevir": (s, f) => SİYAHI["düzlə"](s.map(x => ç(f, x))),
  "təkrarsız": s => { const r = []; for (const x of s) if (!r.some(y => eq(x, y))) r.push(x); return r; },
  "birləşdir": (s, d) => s.concat(siyahıya(d)),
  "qrupla": (s, f) => { const l = new Lüğət(); for (const x of s) { const k = ç(f, x); const c = l.al(k);
    if (c === YOX) l.qoy(k, [x]); else c.push(x); } return l; },
  "hissələrə": (s, n) => { const r = []; const m = Number(n); for (let j = 0; j < s.length; j += m) r.push(s.slice(j, j + m)); return r; },
  "pəncərə": (s, n) => { const r = []; const m = Number(n); for (let j = 0; j <= s.length - m; j++) r.push(s.slice(j, j + m)); return r; },
  "zip": (s, d) => { const b = siyahıya(d); const n = Math.min(s.length, b.length);
    const r = []; for (let j = 0; j < n; j++) r.push(new Kortej([s[j], b[j]])); return r; },
  "nömrələ": s => s.map((x, j) => new Kortej([BigInt(j), x])),
  "uzunluq": s => BigInt(s.length),
  "boşdur": s => s.length === 0,
  "ehtiva": (s, d) => s.some(x => eq(x, d)),
  "tap": (s, f) => { for (const x of s) if (ç(f, x) === true) return x; return null; },
  "tapİndeks": (s, f) => { for (let j = 0; j < s.length; j++) if (ç(f, s[j]) === true) return BigInt(j); return null; },
  "indeks": (s, d) => { const j = s.findIndex(x => eq(x, d)); return j < 0 ? null : BigInt(j); },
  "sonİndeks": (s, d) => { for (let j = s.length - 1; j >= 0; j--) if (eq(s[j], d)) return BigInt(j); return null; },
  "say": (s, d) => BigInt(s.filter(x => eq(x, d)).length),
  "sayŞərt": (s, f) => BigInt(s.filter(x => ç(f, x) === true).length),
  "hamısı": (s, f) => s.every(x => ç(f, x) === true),
  "hərHansı": (s, f) => s.some(x => ç(f, x) === true),
  "heçBiri": (s, f) => !s.some(x => ç(f, x) === true),
  "ilk": s => s.length ? s[0] : null,
  "son": s => s.length ? s[s.length - 1] : null,
  "minimum": s => s.length ? ilkMin(s, false) : null,
  "maksimum": s => s.length ? ilkMin(s, true) : null,
  "cəm": s => s.length ? cəmlə(s) : 0n,
  "orta": s => {
    if (!s.length) throw xəta("BoşKolleksiyaXətası", "boş siyahının ortası yoxdur", "ALQ-R014");
    return div(cəmlə(s), BigInt(s.length));
  },
  "hərBiri": (s, f) => { for (const x of s) ç(f, x); return null; },
  "klonla": s => s.slice(),
  "al": (s, j, st) => {
    if (typeof j === "bigint") { const n = BigInt(s.length); if (-n <= j && j < n) return s[Number(j < 0n ? j + n : j)]; }
    return st === undefined ? null : st;
  },
  "mətnƏt": s => mətnə(s),
  "siyahıyaÇevir": s => s.slice(),
};

const LÜĞƏT = {
  "al": (l, a, st) => { const d = l.al(a); return d === YOX ? (st === undefined ? null : st) : d; },
  "qoy": (l, a, d) => { l.qoy(a, d); return null; },
  "sil": (l, a) => { const d = l.sil(a); return d === YOX ? null : d; },
  "təmizlə": l => { l.m.clear(); return null; },
  "ehtiva": (l, a) => l.var(a),
  "ehtivaDəyər": (l, d) => [...l.dəyərlər()].some(x => eq(x, d)),
  "uzunluq": l => BigInt(l.size),
  "boşdur": l => l.size === 0,
  "açarlar": l => [...l.açarlar()],
  "dəyərlər": l => [...l.dəyərlər()],
  "cütlər": l => [...l.cütlər()].map(c => new Kortej([c[0], c[1]])),
  "birləşdir": (l, d) => { const r = new Lüğət(); for (const [k, v] of l.cütlər()) r.qoy(k, v);
    for (const [k, v] of d.cütlər()) r.qoy(k, v); return r; },
  "çevir": (l, f) => { const r = new Lüğət(); for (const [a, d] of [...l.cütlər()]) {
    const c = ç(f, a, d);
    const e = Array.isArray(c) ? c : c instanceof Kortej ? c.e : null;
    if (e && e.length === 2) r.qoy(e[0], e[1]); else r.qoy(a, c); } return r; },
  "filtr": (l, f) => { const r = new Lüğət(); for (const [a, d] of l.cütlər()) if (ç(f, a, d) === true) r.qoy(a, d); return r; },
  "hərBiri": (l, f) => { for (const [a, d] of [...l.cütlər()]) ç(f, a, d); return null; },
  "alVəYaQoy": (l, a, f) => { if (!l.var(a)) l.qoy(a, ç(f)); return l.al(a); },
  "yenilə": (l, a, f) => {
    if (!l.var(a)) throw xəta("AçarXətası", "`" + mətnə(a) + "` açarı yoxdur", "ALQ-R003");
    l.qoy(a, ç(f, l.al(a))); return l.al(a);
  },
  "tərsÇevir": l => { const r = new Lüğət(); for (const [a, d] of l.cütlər()) r.qoy(d, a); return r; },
  "klonla": l => { const r = new Lüğət(); for (const [a, d] of l.cütlər()) r.qoy(a, d); return r; },
  "mətnƏt": l => mətnə(l),
};

const DƏST = {
  "əlavə": (s, x) => { s.əlavə(x); return null; },
  "sil": (s, x) => { s.sil(x); return null; },
  "ehtiva": (s, x) => s.var(x),
  "uzunluq": s => BigInt(s.size),
  "boşdur": s => s.size === 0,
  "təmizlə": s => { s.m.clear(); return null; },
  "birləşmə": (s, d) => dəstOp("|", s, d),
  "kəsişmə": (s, d) => dəstOp("&", s, d),
  "fərq": (s, d) => dəstOp("-", s, d),
  "simmetrikFərq": (s, d) => dəstOp("^", s, d),
  "altDəstdir": (s, d) => dəstMüq("<=", s, d),
  "üstDəstdir": (s, d) => dəstMüq(">=", s, d),
  "kəsişmir": (s, d) => ![...s].some(x => d.var(x)),
  "siyahıyaÇevir": s => sıralaAçarla([...s]),
  "çevir": (s, f) => new Dəst([...s].map(x => ç(f, x))),
  "filtr": (s, f) => new Dəst([...s].filter(x => ç(f, x) === true)),
  "klonla": s => new Dəst(s),
  "mətnƏt": s => mətnə(s),
};

const BİRLƏR = ["", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz"];
const ONLAR = ["", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan"];
const SIRA = { 1: "birinci", 2: "ikinci", 3: "üçüncü", 4: "dördüncü", 5: "beşinci",
  6: "altıncı", 7: "yeddinci", 8: "səkkizinci", 9: "doqquzuncu", 10: "onuncu" };
function sıraSayı(n) { return SIRA[Number(n)] || n + "-ci"; }
function yazıyla(n) {
  n = BigInt(n);
  if (n === 0n) return "sıfır";
  if (n < 0n) return "mənfi " + yazıyla(-n);
  const h = [];
  if (n >= 1000n) { const m = n / 1000n; h.push((m === 1n ? "" : yazıyla(m) + " ") + "min"); n %= 1000n; }
  if (n >= 100n) { const y = Number(n / 100n); h.push((y === 1 ? "" : BİRLƏR[y] + " ") + "yüz"); n %= 100n; }
  if (n >= 10n) { h.push(ONLAR[Number(n / 10n)]); n %= 10n; }
  if (n > 0n) h.push(BİRLƏR[Number(n)]);
  return h.filter(Boolean).join(" ").trim();
}

const TAM = {
  "mətnƏt": n => mətnə(n),
  "mütləq": n => n < 0n ? -n : n,
  "işarə": n => n === 0n ? 0n : n > 0n ? 1n : -1n,
  "cütdür": n => n % 2n === 0n,
  "təkdir": n => n % 2n !== 0n,
  "kvadrat": n => n * n,
  "onluğaÇevir": n => Number(n),
  "ikilik": n => (n < 0n ? "-" : "") + (n < 0n ? -n : n).toString(2),
  "onaltılıq": n => (n < 0n ? "-" : "") + (n < 0n ? -n : n).toString(16),
  "sıraSayı": n => sıraSayı(n),
  "yazıyla": n => yazıyla(n),
};

const ONLUQ = {
  "mətnƏt": n => mətnə(n),
  "mütləq": n => Math.abs(n),
  "yuvarlaqlaşdır": (n, r) => (r && r !== 0n) ? pyRound(n, r) : pyRound(n),
  "aşağıYuvarlaq": n => trunc(Math.floor(n)),
  "yuxarıYuvarlaq": n => trunc(Math.ceil(n)),
  "kəs": n => trunc(n),
  "tamƏt": n => trunc(n),
  "tamdır": n => Number.isInteger(n),
  "sonludur": n => isFinite(n),
  "ədəddir": n => n === n,
};

const MƏNTİQ = {
  "mətnƏt": b => b ? "doğru" : "yanlış",
  "tamƏt": b => b ? 1n : 0n,
};

const KORTEJ = {
  "uzunluq": t => BigInt(t.e.length),
  "siyahıyaÇevir": t => t.e.slice(),
  "mətnƏt": t => mətnə(t),
  "ehtiva": (t, d) => t.e.some(x => eq(x, d)),
};

const DİAPAZON = {
  "siyahıyaÇevir": d => [...d],
  "uzunluq": d => d.uzunluq(),
  "ehtiva": (d, x) => d.ehtiva(x),
  "mətnƏt": d => mətnə(d),
  "çevir": (d, f) => [...d].map(x => ç(f, x)),
  "filtr": (d, f) => [...d].filter(x => ç(f, x) === true),
  "cəm": d => cəmlə([...d]),
};

const GENERATOR = {
  "növbəti": g => { const r = g.next();
    if (r.done) throw xəta("KolleksiyaXətası", "generator bitdi — daha dəyər yoxdur", "ALQ-R014");
    return r.value; },
  "bitdi": g => g.bitdi,
  "bağla": g => { if (g.it.return) g.it.return(); g.bitdi = true; return null; },
  "siyahıyaÇevir": g => [...g],
  "ilk": (g, n) => { const r = []; if (n <= 0n) return r; for (const x of g) { r.push(x); if (BigInt(r.length) >= n) break; } return r; },
  "çevir": (g, f) => new Gen((function* () { for (const x of g) yield ç(f, x); })()),
  "filtr": (g, f) => new Gen((function* () { for (const x of g) if (ç(f, x) === true) yield x; })()),
  "atla": (g, n) => new Gen((function* () { let i = 0n; for (const x of g) { if (i < n) { i++; continue; } yield x; } })()),
  "tap": (g, f) => { for (const x of g) if (ç(f, x) === true) return x; return null; },
  "hərBiri": (g, f) => { for (const x of g) ç(f, x); return null; },
  "cəm": g => cəmlə([...g]),
  "uzunluq": g => { let n = 0n; for (const _ of g) n++; return n; },
};

const BAYT = {
  "uzunluq": b => BigInt(b.u.length),
  "mətnƏt": b => new TextDecoder().decode(b.u),
  "siyahıyaÇevir": b => [...b.u].map(BigInt),
  "base64Kodla": b => base64Kodla(b.u),
};

const ELEMENT = {
  "HTML": e => elementHTML(e),
  "mətn": e => elementMətn(e),
  "mətnƏt": e => elementHTML(e),
  "tap": (e, t) => { const tap = x => { if (x.ad === t) return x;
    for (const u of x.uşaqlar) if (u instanceof Element) { const r = tap(u); if (r) return r; } return null; };
    return tap(e); },
  "atribut": (e, a, st) => { const d = e.atributlar.al(a); return d === YOX ? (st === undefined ? null : st) : d; },
  "uzunluq": e => BigInt(e.uşaqlar.length),
  "uşaqSayı": e => BigInt(e.uşaqlar.length),
  "boşdur": e => e.uşaqlar.length === 0,
};

const GƏLƏCƏK = {
  "al": g => g.al(),
  "başlat": g => g.başlat(),
  "bitdi": g => g.hal !== 0,
  "uğurludur": g => g.hal === 1,
  "mətnƏt": g => mətnə(g),
};

const LƏĞV = {
  "ləğvEt": n => { n.ləğv = true; return null; },
  "ləğvolunub": n => n.ləğv,
  "gözlə": () => null,
  "yoxla": n => { if (n.ləğv) throw xəta("Xəta", "əməliyyat ləğv edildi", "ALQ-R021"); return null; },
};

class Naxış { constructor(r) { this.r = r; } }

const NAXIŞ = {
  "uyğundur": (n, s) => yenidən(n.r).test(s),
  "tap": (n, s) => { const m = yenidən(n.r).exec(s); return m ? m[0] : null; },
  "hamısınıTap": (n, s) => hamısınıTap(n.r, s),
  "əvəz": (n, s, y) => s.replace(qlobal(n.r), pyƏvəz(y)),
  "böl": (n, s) => pyReBöl(n.r, s),
};

function cədvəl(o) {
  switch (typeof o) {
    case "string": return MƏTN;
    case "bigint": return TAM;
    case "number": return ONLUQ;
    case "boolean": return MƏNTİQ;
  }
  if (Array.isArray(o)) return SİYAHI;
  if (o instanceof Lüğət) return LÜĞƏT;
  if (o instanceof Dəst) return DƏST;
  if (o instanceof Kortej) return KORTEJ;
  if (o instanceof Diapazon) return DİAPAZON;
  if (o instanceof Gen) return GENERATOR;
  if (o instanceof Bayt) return BAYT;
  if (o instanceof Element) return ELEMENT;
  if (o instanceof Gələcək) return GƏLƏCƏK;
  if (o instanceof LəğvNişanı) return LƏĞV;
  if (o instanceof Naxış) return NAXIŞ;
  if (o instanceof Yerli) return o.c;
  return null;
}

function sadalamaMetodu(e, a) {
  if (a === "hamısı") return D("hamısı", 0, 0, () => e.sıra.map(x => e.variantlar.get(x)));
  if (a === "adla") return D("adla", 1, 1, x => e.variantlar.has(x) ? e.variantlar.get(x) : null);
  if (a === "dəyərlə") return D("dəyərlə", 1, 1, d => {
    for (const x of e.sıra) { const v = e.variantlar.get(x); if (v instanceof SDəyər && eq(v.dəyər, d)) return v; }
    return null; });
  if (a === "sayı") return D("sayı", 0, 0, () => BigInt(e.sıra.length));
  return null;
}

function sdəyərMetodu(v, a) {
  if (a === "sıra") return D("sıra", 0, 0, () => v.sıra);
  if (a === "dəyər") return D("dəyər", 0, 0, () => v.dəyər);
  if (a === "adı") return D("adı", 0, 0, () => v.ad);
  if (a === "mətnƏt") return D("mətnƏt", 0, 0, () => v.ad);
  return null;
}

// ── Requlyar ifadələr (Python `re` → JS RegExp) ─────────────────────────

function reQur(n, bayraqlar) {
  let f = "u";
  bayraqlar = bayraqlar || "";
  if (bayraqlar.includes("i")) f += "i";
  if (bayraqlar.includes("m")) f += "m";
  if (bayraqlar.includes("s")) f += "s";
  let m = n.replace(/\(\?P</g, "(?<").replace(/\(\?P=(\w+)\)/g, "\\k<$1>")
    .replace(/\\A/g, "^").replace(/\\Z/g, "$");
  if (bayraqlar.includes("x")) m = m.replace(/\\#/g, "\u0000").replace(/#.*$/gm, "")
    .replace(/\s+/g, "").replace(/\u0000/g, "\\#");
  try { return new RegExp(m, f); }
  catch (e) { throw xəta("FormatXətası", "naxış səhvdir: " + e.message, "ALQ-R005"); }
}
function yenidən(r) { r.lastIndex = 0; return r; }
function qlobal(r) { return new RegExp(r.source, r.flags.includes("g") ? r.flags : r.flags + "g"); }
function hamısınıTap(r, s) {
  const g = qlobal(r), n = [];
  let m;
  while ((m = g.exec(s)) !== null) {
    if (m[0] === "") g.lastIndex++;
    if (m.length === 1) n.push(m[0]);
    else if (m.length === 2) n.push(m[1] === undefined ? "" : m[1]);
    else n.push(new Kortej(m.slice(1).map(x => x === undefined ? "" : x)));
  }
  return n;
}
function pyƏvəz(y) { return y.replace(/\$/g, "$$$$").replace(/\\(\d+)/g, "$$$1").replace(/\\g<(\w+)>/g, "$$<$1>"); }
function pyReBöl(r, s) {
  const g = qlobal(r), n = [];
  let son = 0, m;
  while ((m = g.exec(s)) !== null) {
    if (m[0] === "") { if (m.index === s.length) break; g.lastIndex++; if (m.index === 0) continue; }
    n.push(s.slice(son, m.index));
    for (const x of m.slice(1)) n.push(x === undefined ? null : x);
    son = m.index + m[0].length;
  }
  n.push(s.slice(son));
  return n;
}

// ═══════════════════════════════════════════════════════════════════════
//  Giriş/çıxış platforması
// ═══════════════════════════════════════════════════════════════════════

const nodedir = typeof process !== "undefined" && process.versions && process.versions.node;
const P = {
  arqumentlər: [],
  yaz: s => { if (nodedir) process.stdout.write(s + "\n"); else console.log(s); },
  yazSətirsiz: s => { if (nodedir) process.stdout.write(s); else console.log(s); },
  yazXəta: s => { if (nodedir) process.stderr.write(s + "\n"); else console.error(s); },
  oxu: null,
};

if (nodedir) {
  const fs = require("fs");
  process.stdout.on("error", e => { if (e.code === "EPIPE") process.exit(0); throw e; });
  let bufer = "", bitdi = false;
  P.oxu = () => {
    while (!bufer.includes("\n") && !bitdi) {
      const b = Buffer.alloc(65536);
      let n = 0;
      try { n = fs.readSync(0, b, 0, b.length, null); }
      catch (e) { if (e.code === "EAGAIN") continue; if (e.code === "EOF") n = 0; else throw e; }
      if (n === 0) bitdi = true;
      else bufer += b.toString("utf8", 0, n);
    }
    if (!bufer.length && bitdi) return null;
    const i = bufer.indexOf("\n");
    let s;
    if (i < 0) { s = bufer; bufer = ""; }
    else { s = bufer.slice(0, i); bufer = bufer.slice(i + 1); }
    return s.replace(/\r$/, "");
  };
  P.oxuHamısı = () => { let s = bufer; bufer = "";
    if (!bitdi) { try { s += fs.readFileSync(0, "utf8"); } catch (e) { } bitdi = true; } return s; };
} else {
  P.oxu = () => { const s = typeof prompt === "function" ? prompt("") : null; return s; };
  P.oxuHamısı = () => "";
}

// ═══════════════════════════════════════════════════════════════════════
//  Qlobal funksiyalar
// ═══════════════════════════════════════════════════════════════════════

const g = Object.create(null);

function oxu(soruş) {
  if (soruş) P.yazSətirsiz(mətnə(soruş));
  const s = P.oxu();
  if (s === null || s === undefined)
    throw xəta("GirişÇıxışXətası", "girişin sonu — oxunacaq məlumat qalmadı", "ALQ-R009");
  return s;
}

g["yaz"] = D("yaz", 0, null, (...a) => { P.yaz(a.map(mətnə).join(" ")); return null; });
g["yazSətirsiz"] = D("yazSətirsiz", 0, null, (...a) => { P.yazSətirsiz(a.map(mətnə).join(" ")); return null; });
g["yazXəta"] = D("yazXəta", 0, null, (...a) => { P.yazXəta(a.map(mətnə).join(" ")); return null; });
g["oxu"] = D("oxu", 0, 1, s => oxu(s));
g["oxuTam"] = D("oxuTam", 0, 2, (s, təkrar) => {
  for (;;) {
    const m = oxu(s);
    const n = tamOxu(m);
    if (n !== null) return n;
    if (təkrar === false) throw xəta("ÇevrilməXətası", '"' + m + '" tam ədəd deyil', "ALQ-R005");
    P.yaz("Düzgün tam ədəd daxil edin.");
  }
});
g["oxuOnluq"] = D("oxuOnluq", 0, 1, s => {
  for (;;) {
    const n = onluqOxu(oxu(s).replace(",", "."));
    if (n !== null) return n;
    P.yaz("Düzgün ədəd daxil edin.");
  }
});
g["oxuMəntiq"] = D("oxuMəntiq", 0, 1, s => {
  for (;;) {
    const c = kiçiyə(oxu(s).trim());
    if (["hə", "he", "bəli", "beli", "doğru", "dogru", "h", "b"].includes(c)) return true;
    if (["yox", "xeyr", "yanlış", "yanlis", "y", "x"].includes(c)) return false;
    P.yaz("`hə` və ya `yox` yazın.");
  }
});
g["oxuHamısı"] = D("oxuHamısı", 0, 0, () => P.oxuHamısı());
g["tip"] = D("tip", 1, 1, x => tip(x));
g["tamƏt"] = D("tamƏt", 1, 3, (x, st, əsas) => {
  if (typeof x === "boolean") return x ? 1n : 0n;
  if (typeof x === "bigint") return x;
  if (typeof x === "number" && isFinite(x)) return BigInt(Math.trunc(x));
  const n = typeof x === "string" ? tamOxu(x, əsas) : null;
  if (n !== null) return n;
  if (st !== undefined && st !== null) return st;
  throw xəta("ÇevrilməXətası", '"' + mətnə(x) + '" tam ədədə çevrilə bilmir', "ALQ-R005");
});
g["onluqƏt"] = D("onluqƏt", 1, 2, (x, st) => {
  if (typeof x === "boolean") return x ? 1 : 0;
  if (ədəddir(x)) return N(x);
  const n = typeof x === "string" ? onluqOxu(x.replace(",", ".")) : null;
  if (n !== null) return n;
  if (st !== undefined && st !== null) return st;
  throw xəta("ÇevrilməXətası", '"' + mətnə(x) + '" ədədə çevrilə bilmir', "ALQ-R005");
});
g["mətnƏt"] = D("mətnƏt", 1, 1, x => mətnə(x));
g["məntiqƏt"] = D("məntiqƏt", 1, 1, x => çevir(x, "məntiq"));
g["simvolƏt"] = D("simvolƏt", 1, 1, k => String.fromCodePoint(Number(tamƏdəd(k, "simvolƏt"))));
g["kodƏt"] = D("kodƏt", 1, 1, s => BigInt(mətnYoxla(s, "kodƏt").codePointAt(0)));

function uzunluq(x) {
  if (x instanceof Nümunə) {
    const m = x.s.metod("uzunluq");
    if (m !== undefined) return m.call(x);
  }
  if (typeof x === "string") return BigInt([...x].length);
  if (Array.isArray(x)) return BigInt(x.length);
  if (x instanceof Lüğət || x instanceof Dəst) return BigInt(x.size);
  if (x instanceof Kortej) return BigInt(x.e.length);
  if (x instanceof Diapazon) return x.uzunluq();
  if (x instanceof Bayt) return BigInt(x.u.length);
  if (x instanceof Yerli && x.c === KANAL) return BigInt(x.d.n.length);
  throw xəta("TipXətası", "`" + tip(x) + "` tipinin uzunluğu yoxdur", "ALQ-T006");
}
g["uzunluq"] = D("uzunluq", 1, 1, uzunluq);
g["Kanal"] = D("Kanal", 0, 1, () => new Yerli("Kanal", KANAL, { n: [], bağlı: false }), true);
g["boşdur"] = D("boşdur", 1, 1, x => x === null || uzunluq(x) === 0n);
g["cəm"] = D("cəm", 1, 2, (k, b) => cəmlə(siyahıya(k), b));
g["minimum"] = D("minimum", 1, null, (...a) => {
  const k = a.length === 1 ? siyahıya(a[0]) : a;
  if (!k.length) throw xəta("BoşKolleksiyaXətası", "boş kolleksiyada minimum yoxdur", "ALQ-R014");
  return ilkMin(k, false);
});
g["maksimum"] = D("maksimum", 1, null, (...a) => {
  const k = a.length === 1 ? siyahıya(a[0]) : a;
  if (!k.length) throw xəta("BoşKolleksiyaXətası", "boş kolleksiyada maksimum yoxdur", "ALQ-R014");
  return ilkMin(k, true);
});
g["sırala"] = D("sırala", 1, 2, (k, f) => sıralaAçarla(siyahıya(k), f === null ? undefined : f));
g["tərs"] = D("tərs", 1, 1, k => siyahıya(k).reverse());
g["nömrələ"] = D("nömrələ", 1, 1, k => siyahıya(k).map((x, i) => new Kortej([BigInt(i), x])));
g["zip"] = D("zip", 1, null, (...k) => {
  const s = k.map(siyahıya);
  const n = Math.min(...s.map(x => x.length));
  const r = [];
  for (let i = 0; i < n; i++) r.push(new Kortej(s.map(x => x[i])));
  return r;
});
g["diapazon"] = D("diapazon", 1, 3, (...a) => {
  if (a.length === 1) return new Diapazon(0n, tamƏdəd(a[0], "diapazon"), null, true);
  if (a.length === 2) return new Diapazon(a[0], a[1], null, true);
  return new Diapazon(a[0], a[1], a[2], true);
});
g["siyahı"] = D("siyahı", 0, 1, k => k === undefined || k === null ? [] : siyahıya(k));
g["dəst"] = D("dəst", 0, null, (...a) => (a.length === 1 &&
  (Array.isArray(a[0]) || a[0] instanceof Kortej || a[0] instanceof Dəst || a[0] instanceof Diapazon))
  ? new Dəst(iter(a[0])) : new Dəst(a));
g["lüğət"] = D("lüğət", 0, 1, k => {
  if (k === undefined || k === null) return new Lüğət();
  if (k instanceof Lüğət) return LÜĞƏT["klonla"](k);
  return Lüğət.cütlərdən(siyahıya(k).map(c => siyahıya(c)));
});
g["kortej"] = D("kortej", 0, 1, k => new Kortej(k === undefined || k === null ? [] : siyahıya(k)));

function klonlaDərin(x) {
  if (Array.isArray(x)) return x.map(klonlaDərin);
  if (x instanceof Lüğət) { const r = new Lüğət(); for (const [a, d] of x.cütlər()) r.qoy(a, klonlaDərin(d)); return r; }
  if (x instanceof Dəst) return new Dəst(x);
  return x;
}
g["klonla"] = D("klonla", 1, 1, x => {
  if (x instanceof Nümunə) { const y = new Nümunə(x.s); y.f = new Map(x.f); return y; }
  return klonlaDərin(x);
});
g["çap"] = D("çap", 1, null, (...a) => { for (const x of a) P.yaz(tip(x) + " = " + mətnə(x)); return null; });
g["ölç"] = D("ölç", 1, 1, f => {
  const b = indiMs();
  const n = ç(f);
  P.yaz("⏱ " + (indiMs() - b).toFixed(3) + " ms");
  return n;
});
g["panika"] = D("panika", 0, 1, m => { throw xəta("KritikXəta", mətnə(m === undefined ? "" : m) || "panika", "ALQ-R008"); });
g["dayan"] = D("dayan", 0, 1, k => { throw new Dayanma(k === undefined ? 0n : tamƏdəd(k, "dayan")); });
g["eynidir"] = D("eynidir", 2, 2, (a, b) => a === b || (ədəddir(a) && ədəddir(b) && typeof a === typeof b && a == b));
g["heş"] = D("heş", 1, 1, x => {
  if (x instanceof Nümunə) return BigInt(obyektId(x));
  const s = açarMətn(x);
  let h = 0n;
  for (const c of s) h = (h * 31n + BigInt(c.codePointAt(0))) & 0xffffffffffffn;
  return h;
});
g["LəğvNişanı"] = D("LəğvNişanı", 0, 1, () => new LəğvNişanı());
g["Gələcək"] = D("Gələcək", 1, 1, f => new Gələcək(() => ç(f)));

for (const a of Object.keys(XETA_AGACI)) if (a !== "Atılan") g[a] = new _XətaSinfi(a);

function indiMs() {
  if (typeof performance !== "undefined") return performance.now();
  return Date.now();
}

// ═══════════════════════════════════════════════════════════════════════
//  Standart modullar
// ═══════════════════════════════════════════════════════════════════════

function riyaziArq(x, a) {
  if (!ədəddir(x) && typeof x !== "boolean")
    throw xəta("TipXətası", "`" + a + "` ədəd gözləyir, `" + tip(x) + "` gəlib", "ALQ-T004");
  return N(typeof x === "boolean" ? (x ? 1 : 0) : x);
}
function R(a, f) { return D(a, 1, 1, x => { const r = f(riyaziArq(x, a));
  if (r !== r && riyaziArq(x, a) === riyaziArq(x, a))
    throw xəta("RiyaziXəta", "riyazi tətbiq sahəsindən kənar dəyər", "ALQ-R001");
  return r; }); }

function ƏBOB(a, b) { a = a < 0n ? -a : a; b = b < 0n ? -b : b; while (b) [a, b] = [b, a % b]; return a; }
function sadədir(n) {
  if (n < 2n) return false;
  if (n < 4n) return true;
  if (n % 2n === 0n) return false;
  for (let i = 3n; i * i <= n; i += 2n) if (n % i === 0n) return false;
  return true;
}

function sıralıƏdədlər(k) {
  return siyahıya(k).slice().sort((a, b) => { const x = N(a), y = N(b); return x < y ? -1 : x > y ? 1 : 0; });
}

function dispersiya(k) {
  const s = siyahıya(k);
  if (!s.length) return 0;
  const o = N(div(cəmlə(s), BigInt(s.length)));
  let c = 0;
  for (const x of s) c += (N(x) - o) ** 2;
  return c / s.length;
}

const modullar = Object.create(null);

modullar["riyaziyyat"] = () => new Modul("riyaziyyat", {
  "Pİ": Math.PI, "PI": Math.PI, "E": Math.E, "TAU": 2 * Math.PI,
  "QIZILNİSBƏT": (1 + Math.sqrt(5)) / 2, "SONSUZ": Infinity, "ƏDƏDDEYİL": NaN,
  "mütləq": D("mütləq", 1, 1, x => typeof x === "bigint" ? (x < 0n ? -x : x) : Math.abs(riyaziArq(x, "mütləq"))),
  "işarə": D("işarə", 1, 1, x => typeof x === "bigint" ? (x === 0n ? 0n : x > 0n ? 1n : -1n)
    : (x === 0 ? 0n : x > 0 ? 1n : -1n)),
  "kök": D("kök", 1, 1, x => { const v = riyaziArq(x, "kök"); return v >= 0 ? Math.sqrt(v) : NaN; }),
  "kubKök": D("kubKök", 1, 1, x => Math.cbrt(riyaziArq(x, "kubKök"))),
  "qüvvət": D("qüvvət", 2, 2, (a, b) => pow(a, b)),
  "eksp": R("eksp", Math.exp),
  "loq": D("loq", 1, 2, (x, b) => {
    const v = riyaziArq(x, "loq");
    if (v <= 0) throw xəta("RiyaziXəta", "riyazi tətbiq sahəsindən kənar dəyər", "ALQ-R001");
    return b === undefined ? Math.log(v) : Math.log(v) / Math.log(riyaziArq(b, "loq"));
  }),
  "loq10": R("loq10", x => { if (x <= 0) return NaN; return Math.log10(x); }),
  "loq2": R("loq2", x => { if (x <= 0) return NaN; return Math.log2(x); }),
  "loqƏsas": D("loqƏsas", 2, 2, (x, b) => Math.log(riyaziArq(x, "loqƏsas")) / Math.log(riyaziArq(b, "loqƏsas"))),
  "yuvarlaqlaşdır": D("yuvarlaqlaşdır", 1, 2, (x, r) => (r && r !== 0n) ? pyRound(x, r) : pyRound(x)),
  "aşağıYuvarlaq": D("aşağıYuvarlaq", 1, 1, x => typeof x === "bigint" ? x : trunc(Math.floor(riyaziArq(x, "aşağıYuvarlaq")))),
  "yuxarıYuvarlaq": D("yuxarıYuvarlaq", 1, 1, x => typeof x === "bigint" ? x : trunc(Math.ceil(riyaziArq(x, "yuxarıYuvarlaq")))),
  "kəs": D("kəs", 1, 1, x => typeof x === "bigint" ? x : trunc(riyaziArq(x, "kəs"))),
  "min": D("min", 1, null, (...a) => ilkMin(a, false)),
  "maks": D("maks", 1, null, (...a) => ilkMin(a, true)),
  "məhdudla": D("məhdudla", 3, 3, (x, a, b) => ilkMin([a, ilkMin([b, x], false)], true)),
  "sin": R("sin", Math.sin), "kos": R("kos", Math.cos), "tan": R("tan", Math.tan),
  "arksin": R("arksin", Math.asin), "arkkos": R("arkkos", Math.acos), "arktan": R("arktan", Math.atan),
  "arktan2": D("arktan2", 2, 2, (a, b) => Math.atan2(riyaziArq(a, "arktan2"), riyaziArq(b, "arktan2"))),
  "hipsin": R("hipsin", Math.sinh), "hipkos": R("hipkos", Math.cosh), "hiptan": R("hiptan", Math.tanh),
  "dərəcəyə": R("dərəcəyə", x => x * 180 / Math.PI),
  "radiana": R("radiana", x => x * Math.PI / 180),
  "ƏBOB": D("ƏBOB", 2, null, (...a) => a.reduce((x, y) => ƏBOB(tamƏdəd(x, "ƏBOB"), tamƏdəd(y, "ƏBOB")))),
  "ƏKOB": D("ƏKOB", 2, null, (...a) => a.reduce((x, y) => { const g_ = ƏBOB(x, y); if (g_ === 0n) return 0n;
    const r = x * y / g_; return r < 0n ? -r : r; })),
  "faktorial": D("faktorial", 1, 1, n => {
    tamƏdəd(n, "faktorial");
    if (n < 0n) throw xəta("DəyərXətası", "faktorial mənfi ədəd üçün təyin olunmayıb", "ALQ-R005");
    let r = 1n; for (let i = 2n; i <= n; i++) r *= i; return r;
  }),
  "sadədir": D("sadədir", 1, 1, n => sadədir(n)),
  "sadəBölənlər": D("sadəBölənlər", 1, 1, n => {
    const r = []; let d = 2n;
    while (d * d <= n) { while (n % d === 0n) { r.push(d); n /= d; } d++; }
    if (n > 1n) r.push(n); return r;
  }),
  "modul": D("modul", 2, 2, (a, b) => {
    if (typeof a === "bigint" && typeof b === "bigint") {
      if (b === 0n) throw xəta("BölməXətası", "sıfıra bölmək olmaz", "ALQ-R001");
      const r = a % b; return r !== 0n && (r < 0n) !== (b < 0n) ? r + b : r;
    }
    const x = N(a), y = N(b); const r = x % y; return r !== 0 && (r < 0) !== (y < 0) ? r + y : r;
  }),
  "modQüvvət": D("modQüvvət", 3, 3, (a, b, m) => {
    let r = 1n; a = ((a % m) + m) % m;
    while (b > 0n) { if (b & 1n) r = r * a % m; a = a * a % m; b >>= 1n; }
    return r;
  }),
  "ədəddirmi": D("ədəddirmi", 1, 1, x => ədəddir(x)),
  "sonludur": D("sonludur", 1, 1, x => isFinite(N(x))),
  "tamdır": D("tamdır", 1, 1, x => Number.isInteger(N(x))),
  "orta": D("orta", 1, 1, k => { const s = siyahıya(k); return s.length ? div(cəmlə(s), BigInt(s.length)) : 0; }),
  "median": D("median", 1, 1, k => {
    const s = sıralıƏdədlər(k), n = s.length;
    if (!n) throw xəta("BoşKolleksiyaXətası", "boş kolleksiyanın medianı yoxdur", "ALQ-R014");
    return n % 2 ? N(s[(n - 1) / 2]) : div(add(s[n / 2 - 1], s[n / 2]), 2n);
  }),
  "moda": D("moda", 1, 1, k => {
    const s = siyahıya(k);
    if (!s.length) throw xəta("BoşKolleksiyaXətası", "boş kolleksiyanın modası yoxdur", "ALQ-R014");
    const say = new Lüğət();
    for (const x of s) { const c = say.al(x); say.qoy(x, c === YOX ? 1 : c + 1); }
    let ən = null, n = 0;
    for (const [x, c] of say.cütlər()) if (c > n) { ən = x; n = c; }
    return ən;
  }),
  "dispersiya": D("dispersiya", 1, 1, dispersiya),
  "standartKənarlaşma": D("standartKənarlaşma", 1, 1, k => Math.sqrt(dispersiya(k))),
});

function yerliƏdəd(n, rəqəm) {
  const x = N(n);
  if (rəqəm === undefined || rəqəm === null) rəqəm = Number.isInteger(x) ? 0 : 2;
  const s = qruplaşdır(sabitNöqtə(x, Number(rəqəm)), ",");
  const [t, k] = s.split(".");
  return k !== undefined ? t.replace(/,/g, "\u00a0") + "," + k : t.replace(/,/g, "\u00a0");
}

function şəkilçi(söz, ş_) {
  const saitlər = [...kiçiyə(söz)].filter(c => SAITLER.has(c));
  const qalın = saitlər.length > 0 && QALIN.has(saitlər[saitlər.length - 1]);
  const c = { "lar": qalın ? "lar" : "lər", "lər": qalın ? "lar" : "lər",
    "da": qalın ? "da" : "də", "dan": qalın ? "dan" : "dən", "a": qalın ? "a" : "ə" };
  return söz + (c[ş_] || ş_);
}

modullar["mətn"] = () => new Modul("mətn", {
  "formatla": D("formatla", 1, null, (s, ...a) => MƏTN["formatla"](s, ...a)),
  "yerliƏdəd": D("yerliƏdəd", 1, 2, yerliƏdəd),
  "yerliPul": D("yerliPul", 1, 1, n => yerliƏdəd(n, 2) + " ₼"),
  "yerliFaiz": D("yerliFaiz", 1, 1, n => yerliƏdəd(N(n) * 100, 1) + " %"),
  "yazıylaƏdəd": D("yazıylaƏdəd", 1, 1, yazıyla),
  "sıraSayı": D("sıraSayı", 1, 1, sıraSayı),
  "saitdir": D("saitdir", 1, 1, c => SAITLER.has(c)),
  "samitdir": D("samitdir", 1, 1, c => hərfdir(c) && !SAITLER.has(c)),
  "qalınSait": D("qalınSait", 1, 1, c => QALIN.has(c)),
  "incəSait": D("incəSait", 1, 1, c => INCE.has(c)),
  "şəkilçi": D("şəkilçi", 2, 2, şəkilçi),
  "böyüyə": D("böyüyə", 1, 1, böyüyə),
  "kiçiyə": D("kiçiyə", 1, 1, kiçiyə),
  "müqayisə": D("müqayisə", 2, 2, (a, b) => BigInt(mətnMüqayisə(a, b))),
  "əlifba": KICIK,
});

// Toxumlanan təsadüfi generator (mulberry32) — `toxum(n)` təkrarlana bilsin
let _toxum = null;
function təsadüfi() {
  if (_toxum === null) return Math.random();
  _toxum = (_toxum + 0x6D2B79F5) | 0;
  let t = _toxum;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function təsadüfiTam(a, b) {
  const n = b - a + 1n;
  if (n <= 0n) throw xəta("DəyərXətası", "boş diapazon", "ALQ-R005");
  if (n <= 9007199254740991n) return a + BigInt(Math.floor(təsadüfi() * Number(n)));
  return a + BigInt(Math.floor(təsadüfi() * 2 ** 53)) % n;
}

modullar["təsadüfi"] = () => new Modul("təsadüfi", {
  "tam": D("tam", 2, 2, (a, b) => təsadüfiTam(tamƏdəd(a, "tam"), tamƏdəd(b, "tam"))),
  "onluq": D("onluq", 0, 2, (a, b) => { const x = a === undefined ? 0 : N(a), y = b === undefined ? 1 : N(b);
    return x + (y - x) * təsadüfi(); }),
  "məntiq": D("məntiq", 0, 0, () => təsadüfi() < 0.5),
  "seç": D("seç", 1, 1, k => { const s = siyahıya(k);
    if (!s.length) throw xəta("BoşKolleksiyaXətası", "boş kolleksiyadan seçmək olmaz", "ALQ-R014");
    return s[Math.floor(təsadüfi() * s.length)]; }),
  "seçN": D("seçN", 2, 2, (k, n) => { const s = siyahıya(k).slice(); const r = [];
    if (Number(n) > s.length) throw xəta("DəyərXətası", "nümunə kolleksiyadan böyükdür", "ALQ-R005");
    for (let i = 0; i < Number(n); i++) r.push(s.splice(Math.floor(təsadüfi() * s.length), 1)[0]); return r; }),
  "qarışdır": D("qarışdır", 1, 1, s => { for (let i = s.length - 1; i > 0; i--) {
    const j = Math.floor(təsadüfi() * (i + 1)); [s[i], s[j]] = [s[j], s[i]]; } return null; }),
  "mətn": D("mətn", 1, 1, n => { let r = ""; for (let i = 0n; i < n; i++) r += KICIK[Math.floor(təsadüfi() * KICIK.length)]; return r; }),
  "UUID": D("UUID", 0, 0, () => "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = Math.floor(təsadüfi() * 16); return (c === "x" ? r : (r & 3) | 8).toString(16); })),
  "toxum": D("toxum", 1, 1, n => { _toxum = Number(BigInt.asIntN(32, BigInt(n))); return null; }),
});

const AYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust",
  "sentyabr", "oktyabr", "noyabr", "dekabr"];
const GÜNLƏR = ["bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə",
  "şənbə", "bazar"];

function iki(n) { return String(n).padStart(2, "0"); }
function vaxtFormatla(f, möhür) {
  const t = möhür ? new Date(N(möhür) * 1000) : new Date();
  return f.replace("YYYY", t.getFullYear()).replace("MM", iki(t.getMonth() + 1))
    .replace("DD", iki(t.getDate())).replace("HH", iki(t.getHours()))
    .replace("mm", iki(t.getMinutes())).replace("ss", iki(t.getSeconds()));
}
function yat(ms) {
  if (typeof SharedArrayBuffer !== "undefined" && typeof Atomics !== "undefined" && Atomics.wait) {
    try { Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms); return; } catch (e) { }
  }
  const son = Date.now() + ms;
  while (Date.now() < son) { }
}

modullar["vaxt"] = () => new Modul("vaxt", {
  "möhür": D("möhür", 0, 0, () => BigInt(Math.floor(Date.now() / 1000))),
  "möhürMs": D("möhürMs", 0, 0, () => BigInt(Date.now())),
  "indi": D("indi", 0, 0, () => vaxtFormatla("YYYY-MM-DDTHH:mm:ss")),
  "bugün": D("bugün", 0, 0, () => vaxtFormatla("YYYY-MM-DD")),
  "formatla": D("formatla", 1, 2, vaxtFormatla),
  "azərbaycanca": D("azərbaycanca", 0, 0, () => { const t = new Date();
    return t.getDate() + " " + AYLAR[t.getMonth()] + " " + t.getFullYear() + ", " + GÜNLƏR[(t.getDay() + 6) % 7]; }),
  "ayAdı": D("ayAdı", 1, 1, n => AYLAR[Number(n) - 1]),
  "ayAdıBaş": D("ayAdıBaş", 1, 1, n => başBöyük(AYLAR[Number(n) - 1])),
  "günAdı": D("günAdı", 1, 1, n => GÜNLƏR[Number(n) - 1]),
  "ayAdları": D("ayAdları", 0, 0, () => AYLAR.slice()),
  "günAdları": D("günAdları", 0, 0, () => GÜNLƏR.slice()),
  "gözlə": D("gözlə", 1, 1, ms => { yat(N(ms)); return null; }),
  "gözləSaniyə": D("gözləSaniyə", 1, 1, s => { yat(N(s) * 1000); return null; }),
  "ölç": D("ölç", 0, 0, () => indiMs() / 1000),
  "limitlə": D("limitlə", 2, 2, (ms, g_) => gözlə(g_)),
});

// ── json ────────────────────────────────────────────────────────────────

function jsonDəyər(x) {
  if (x === null) return null;
  if (typeof x === "number") return Number.isInteger(x) && !/[.eE]/.test(String(x)) ? BigInt(x) : x;
  if (Array.isArray(x)) return x.map(jsonDəyər);
  if (typeof x === "object") {
    const l = new Lüğət();
    for (const k of Object.keys(x)) l.qoy(k, jsonDəyər(x[k]));
    return l;
  }
  return x;
}

/** Tam ədədləri itirmədən JSON oxuyan sadə parser. */
function jsonOxu(m) {
  let i = 0;
  const xəta_ = (msg) => { const s = m.slice(0, i).split("\n").length;
    return xəta("JSONXətası", "JSON formatı pozulub (sətir " + s + "): " + msg, "ALQ-R005"); };
  const boşluq = () => { while (i < m.length && " \t\n\r".includes(m[i])) i++; };
  function dəyər() {
    boşluq();
    const c = m[i];
    if (c === "{") {
      i++; const l = new Lüğət(); boşluq();
      if (m[i] === "}") { i++; return l; }
      for (;;) {
        boşluq(); if (m[i] !== '"') throw xəta_("Expecting property name enclosed in double quotes");
        const k = mətn_(); boşluq();
        if (m[i] !== ":") throw xəta_("Expecting ':' delimiter");
        i++; l.qoy(k, dəyər()); boşluq();
        if (m[i] === ",") { i++; continue; }
        if (m[i] === "}") { i++; return l; }
        throw xəta_("Expecting ',' delimiter");
      }
    }
    if (c === "[") {
      i++; const a = []; boşluq();
      if (m[i] === "]") { i++; return a; }
      for (;;) {
        a.push(dəyər()); boşluq();
        if (m[i] === ",") { i++; continue; }
        if (m[i] === "]") { i++; return a; }
        throw xəta_("Expecting ',' delimiter");
      }
    }
    if (c === '"') return mətn_();
    if (m.startsWith("true", i)) { i += 4; return true; }
    if (m.startsWith("false", i)) { i += 5; return false; }
    if (m.startsWith("null", i)) { i += 4; return null; }
    const r = /^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/.exec(m.slice(i));
    if (r) { i += r[0].length; return r[2] || r[3] ? Number(r[0]) : BigInt(r[0]); }
    throw xəta_("Expecting value");
  }
  function mətn_() {
    const b = i; i++;
    while (i < m.length && m[i] !== '"') { if (m[i] === "\\") i++; i++; }
    if (i >= m.length) throw xəta_("Unterminated string");
    i++;
    try { return JSON.parse(m.slice(b, i)); } catch (e) { throw xəta_("Invalid string"); }
  }
  const n = dəyər(); boşluq();
  if (i < m.length) throw xəta_("Extra data");
  return n;
}

function jsonHazırla(x) {
  if (x instanceof Nümunə) { const o = new Map(); for (const [k, v] of x.f) o.set(k, jsonHazırla(v)); return o; }
  if (x instanceof SDəyər) return x.ad;
  if (x instanceof Lüğət) { const o = new Map(); for (const [k, v] of x.cütlər()) o.set(typeof k === "string" ? k : mətnə(k), jsonHazırla(v)); return o; }
  if (Array.isArray(x)) return x.map(jsonHazırla);
  if (x instanceof Kortej) return x.e.map(jsonHazırla);
  if (x instanceof Dəst) return [...x].map(jsonHazırla);
  if (x instanceof Diapazon) return [...x];
  return x;
}

function jsonYaz(x, gözəl) {
  const qaç = s => JSON.stringify(s);
  const yaz = (v, d) => {
    if (v === null || v === undefined) return "null";
    if (v === true) return "true";
    if (v === false) return "false";
    if (typeof v === "bigint") return v.toString();
    if (typeof v === "number") return v !== v ? "NaN" : v === Infinity ? "Infinity" : v === -Infinity ? "-Infinity" : onluqRepr(v);
    if (typeof v === "string") return qaç(v);
    const ara = gözəl ? "\n" + "  ".repeat(d + 1) : "";
    const son = gözəl ? "\n" + "  ".repeat(d) : "";
    if (Array.isArray(v)) {
      if (!v.length) return "[]";
      return "[" + ara + v.map(e => yaz(e, d + 1)).join(gözəl ? "," + ara : ", ") + son + "]";
    }
    if (v instanceof Map) {
      if (!v.size) return "{}";
      return "{" + ara + [...v].map(([k, e]) => qaç(k) + ": " + yaz(e, d + 1)).join(gözəl ? "," + ara : ", ") + son + "}";
    }
    return qaç(mətnə(v));
  };
  return yaz(jsonHazırla(x), 0);
}

modullar["json"] = () => new Modul("json", {
  "oxu": D("oxu", 1, 1, m => jsonOxu(mətnYoxla(m, "oxu"))),
  "yaz": D("yaz", 1, 1, x => jsonYaz(x, false)),
  "yazGözəl": D("yazGözəl", 1, 1, x => jsonYaz(x, true)),
  "faylOxu": D("faylOxu", 1, 1, y => jsonOxu(faylOxu(y))),
  "faylYaz": D("faylYaz", 2, 2, (y, x) => faylYaz(y, jsonYaz(x, true))),
});

modullar["naxış"] = () => new Modul("naxış", {
  "qur": D("qur", 1, 2, (n, b) => new Naxış(reQur(n, b))),
  "uyğundur": D("uyğundur", 2, 2, (n, s) => reQur(n).test(s)),
  "tap": D("tap", 2, 2, (n, s) => { const m = reQur(n).exec(s); return m ? m[0] : null; }),
  "hamısınıTap": D("hamısınıTap", 2, 2, (n, s) => hamısınıTap(reQur(n), s)),
  "əvəz": D("əvəz", 3, 3, (n, s, y) => s.replace(qlobal(reQur(n)), pyƏvəz(y))),
  "böl": D("böl", 2, 2, (n, s) => pyReBöl(reQur(n), s)),
});

function platforma() {
  if (!nodedir) return "veb";
  const p = process.platform;
  return p === "darwin" ? "macos" : p === "win32" ? "windows" : p;
}

modullar["sistem"] = () => new Modul("sistem", {
  "arqumentlər": D("arqumentlər", 0, 0, () => P.arqumentlər.slice()),
  "mühit": D("mühit", 1, 2, (a, s) => { const v = nodedir ? process.env[a] : undefined;
    return v === undefined ? (s === undefined ? null : s) : v; }),
  "mühitQoy": D("mühitQoy", 2, 2, (a, d) => { if (nodedir) process.env[a] = d; return null; }),
  "platforma": D("platforma", 0, 0, platforma),
  "memarlıq": D("memarlıq", 0, 0, () => nodedir ? process.arch.replace("x64", "x86_64") : "veb"),
  "nüvəSayı": D("nüvəSayı", 0, 0, () => BigInt(nodedir ? require("os").cpus().length
    : (typeof navigator !== "undefined" && navigator.hardwareConcurrency) || 1)),
  "istifadəçi": D("istifadəçi", 0, 0, () => nodedir ? (process.env.USERNAME || process.env.USER || "") : ""),
  "hostAdı": D("hostAdı", 0, 0, () => nodedir ? require("os").hostname() : "localhost"),
  "dayan": D("dayan", 0, 1, k => { throw new Dayanma(k === undefined ? 0n : k); }),
});

modullar["jurnal"] = () => new Modul("jurnal", {
  "sazlama": D("sazlama", 1, null, (...a) => jurnalYaz("SAZLAMA", a)),
  "debaq": D("debaq", 1, null, (...a) => jurnalYaz("SAZLAMA", a)),
  "info": D("info", 1, null, (...a) => jurnalYaz("İNFO", a)),
  "xəbərdarlıq": D("xəbərdarlıq", 1, null, (...a) => jurnalYaz("XƏBƏRDARLIQ", a)),
  "xəta": D("xəta", 1, null, (...a) => jurnalYaz("XƏTA", a)),
  "kritik": D("kritik", 1, null, (...a) => jurnalYaz("KRİTİK", a)),
});
function jurnalYaz(s, a) {
  const t = new Date();
  P.yazXəta("[" + iki(t.getHours()) + ":" + iki(t.getMinutes()) + ":" + iki(t.getSeconds()) + "] " +
    s + ": " + a.map(mətnə).join(" "));
  return null;
}

function hamısı(k) {
  const s = siyahıya(k);
  for (const x of s) if (x instanceof Gələcək) x.başlat();
  return s.map(gözlə);
}
modullar["paralel"] = () => new Modul("paralel", {
  "hamısı": D("hamısı", 1, 1, hamısı),
  "hamısıNəticə": D("hamısıNəticə", 1, 1, k => siyahıya(k).map(x => {
    try { return new Kortej([true, gözlə(x)]); }
    catch (e) { const y = xətaya(e); if (y instanceof Dayanma) throw y; return new Kortej([false, y.mesaj]); }
  })),
  "ilkBitən": D("ilkBitən", 1, 1, k => gözlə(siyahıya(k)[0])),
  "ilkUğurlu": D("ilkUğurlu", 1, 1, k => {
    let son = null;
    for (const x of siyahıya(k)) {
      try { return gözlə(x); }
      catch (e) { son = xətaya(e); if (son instanceof Dayanma) throw son; }
    }
    if (son) throw son;
    throw xəta("Xəta", "heç bir əməliyyat uğurlu olmadı", "ALQ-R021");
  }),
  "məhdud": D("məhdud", 2, 2, (n, k) => hamısı(k)),
  "çevir": D("çevir", 2, 2, (k, f) => hamısı(siyahıya(k).map(x => ç(f, x)))),
}, D("paralel", 1, null, (...a) => new Kortej(hamısı(a))));

// ── fayl / qovluq / yol (yalnız node) ───────────────────────────────────

function fsLazım() {
  if (!nodedir) throw xəta("GirişÇıxışXətası", "fayl əməliyyatları brauzerdə mövcud deyil", "ALQ-R009");
  return require("fs");
}
function faylOxu(y) {
  const fs = fsLazım();
  try { return fs.readFileSync(y, "utf8"); }
  catch (e) {
    if (e.code === "ENOENT") throw xəta("FaylTapılmadıXətası", '"' + y + '" faylı tapılmadı', "ALQ-R009");
    if (e.code === "EACCES") throw xəta("İcazəXətası", '"' + y + '" faylını oxumaq icazəsi yoxdur', "ALQ-R012");
    throw xəta("GirişÇıxışXətası", String(e.message), "ALQ-R009");
  }
}
function faylYaz(y, m) {
  const fs = fsLazım();
  try { fs.writeFileSync(y, mətnə(m), "utf8"); }
  catch (e) {
    if (e.code === "EACCES") throw xəta("İcazəXətası", '"' + y + '" faylına yazmaq icazəsi yoxdur', "ALQ-R012");
    throw xəta("GirişÇıxışXətası", String(e.message), "ALQ-R009");
  }
  return null;
}
function yolM() { fsLazım(); return require("path"); }

modullar["fayl"] = () => new Modul("fayl", {
  "oxu": D("oxu", 1, 1, faylOxu),
  "yaz": D("yaz", 2, 2, faylYaz),
  "əlavəEt": D("əlavəEt", 2, 2, (y, m) => { fsLazım().appendFileSync(y, mətnə(m), "utf8"); return null; }),
  "oxuSətirlər": D("oxuSətirlər", 1, 1, y => faylOxu(y).split("\n")),
  "oxuBayt": D("oxuBayt", 1, 1, y => new Bayt(new Uint8Array(fsLazım().readFileSync(y)))),
  "yazBayt": D("yazBayt", 2, 2, (y, b) => { fsLazım().writeFileSync(y, b instanceof Bayt ? b.u
    : Uint8Array.from(siyahıya(b).map(Number))); return null; }),
  "vardır": D("vardır", 1, 1, y => { try { return fsLazım().statSync(y).isFile(); } catch (e) { return false; } }),
  "sil": D("sil", 1, 1, y => { try { fsLazım().unlinkSync(y); } catch (e) { } return null; }),
  "kopyala": D("kopyala", 2, 2, (a, b) => { fsLazım().copyFileSync(a, b); return null; }),
  "köçür": D("köçür", 2, 2, (a, b) => { fsLazım().renameSync(a, b); return null; }),
  "adDəyiş": D("adDəyiş", 2, 2, (a, b) => { fsLazım().renameSync(a, b); return null; }),
  "ölçü": D("ölçü", 1, 1, y => BigInt(fsLazım().statSync(y).size)),
});

modullar["qovluq"] = () => new Modul("qovluq", {
  "yarat": D("yarat", 1, 1, y => { try { fsLazım().mkdirSync(y); } catch (e) { if (e.code !== "EEXIST") throw e; } return null; }),
  "yaratDərin": D("yaratDərin", 1, 1, y => { fsLazım().mkdirSync(y, { recursive: true }); return null; }),
  "sil": D("sil", 1, 1, y => { fsLazım().rmdirSync(y); return null; }),
  "silDərin": D("silDərin", 1, 1, y => { try { fsLazım().rmSync(y, { recursive: true, force: true }); } catch (e) { } return null; }),
  "vardır": D("vardır", 1, 1, y => { try { return fsLazım().statSync(y).isDirectory(); } catch (e) { return false; } }),
  "siyahı": D("siyahı", 0, 1, y => sıralaAçarla(fsLazım().readdirSync(y === undefined ? "." : y))),
  "cari": D("cari", 0, 0, () => process.cwd()),
  "dəyiş": D("dəyiş", 1, 1, y => { process.chdir(y); return null; }),
  "ev": D("ev", 0, 0, () => require("os").homedir()),
  "müvəqqəti": D("müvəqqəti", 0, 0, () => require("os").tmpdir()),
});

modullar["yol"] = () => new Modul("yol", {
  "birləşdir": D("birləşdir", 1, null, (...p) => yolM().join(...p).replace(/\\/g, "/")),
  "mütləq": D("mütləq", 1, 1, p => yolM().resolve(p)),
  "qovluq": D("qovluq", 1, 1, p => yolM().dirname(p)),
  "fayl": D("fayl", 1, 1, p => yolM().basename(p)),
  "ad": D("ad", 1, 1, p => { const b = yolM().basename(p); const e = yolM().extname(b); return e ? b.slice(0, -e.length) : b; }),
  "uzantı": D("uzantı", 1, 1, p => yolM().extname(p)),
  "normalizə": D("normalizə", 1, 1, p => yolM().normalize(p).replace(/\\/g, "/")),
  "nisbi": D("nisbi", 2, 2, (a, b) => yolM().relative(a, b).replace(/\\/g, "/")),
  "ayırıcı": "/",
});

// ── konsol ──────────────────────────────────────────────────────────────

const RƏNGLƏR = { "qara": 30, "qırmızı": 31, "yaşıl": 32, "sarı": 33, "mavi": 34,
  "bənövşəyi": 35, "firuzəyi": 36, "ağ": 37, "boz": 90 };
const terminaldır = () => !!(nodedir && process.stdout.isTTY);
//  Brauzerdə ANSI kodları mənasızdır — rəngsiz mətn
function boya(m, ...kodlar) {
  m = mətnə(m);
  if (!kodlar.length || !nodedir || process.env.NO_COLOR) return m;
  return "\x1b[" + kodlar.join(";") + "m" + m + "\x1b[0m";
}
function rəngKodu(a, sahə) {
  a = kiçiyə(mətnə(a));
  if (!(a in RƏNGLƏR))
    throw xəta("ArqumentXətası", "`" + a + "` " + sahə + " rəngi yoxdur. İcazəli: " +
      Object.keys(RƏNGLƏR).join(", "), "ALQ-R013");
  return RƏNGLƏR[a];
}
function konsolOxu(s) {
  if (s) P.yazSətirsiz(s);
  const c = P.oxu();
  if (c === null || c === undefined)
    throw xəta("GirişÇıxışXətası", "girişin sonu — oxunacaq məlumat qalmadı", "ALQ-R009");
  return c;
}
function adlıVəYa(adlı, ad, v) { return adlı && adlı[ad] !== undefined ? adlı[ad] : v; }
function seçimSiyahısı(s) {
  const l = s instanceof Kortej ? s.e.slice() : Array.isArray(s) ? s.slice() : null;
  if (!l || !l.length)
    throw xəta("ArqumentXətası", "seçimlər boş olmayan siyahı olmalıdır", "ALQ-R013");
  return l;
}
function seçimləriGöstər(sual, l) {
  if (sual !== null && sual !== undefined && mətnə(sual)) P.yaz(mətnə(sual));
  l.forEach((e, i) => P.yaz("  " + (i + 1) + ") " + mətnə(e)));
}
const BƏLİ = ["hə", "he", "bəli", "beli", "h", "b", "doğru", "dogru"];
const XEYR = ["yox", "xeyr", "y", "x", "yanlış", "yanlis"];
const konsolRəqəm = s => /^[0-9]+$/.test(s);

function irəliləyiş(cəmi, m) {
  const o = { cəmi: Math.max(1, N(cəmi)), mətn: m === undefined ? "" : mətnə(m), cari: 0, bitib: false };
  const sətir = () => {
    const n = Math.min(1, o.cari / o.cəmi), dolu = yuvarlaCüt(n * 28);
    return (o.mətn ? o.mətn + " " : "") + "█".repeat(dolu) + "░".repeat(28 - dolu) + " " +
      String(yuvarlaCüt(n * 100)).padStart(3) + "% (" + o.cari + "/" + o.cəmi + ")";
  };
  const çək = () => { if (terminaldır()) P.yazSətirsiz("\r" + sətir()); };
  let ü;
  const yenilə = n => { o.cari = Math.max(0, Math.min(o.cəmi, N(n))); çək(); return ü; };
  ü = new Modul("irəliləyiş", {
    "yenilə": D("yenilə", 1, 1, yenilə),
    "artır": D("artır", 0, 1, a => yenilə(o.cari + (a === undefined ? 1 : N(a)))),
    "bitir": D("bitir", 0, 1, m_ => {
      if (o.bitib) return null;
      o.bitib = true; o.cari = o.cəmi;
      if (terminaldır()) P.yazSətirsiz("\r\x1b[K");
      P.yaz(m_ === undefined || m_ === null ? sətir() : mətnə(m_));
      return null;
    }),
    "cari": D("cari", 0, 0, () => BigInt(o.cari)),
    "cəmi": D("cəmi", 0, 0, () => BigInt(o.cəmi)),
    "mətnƏt": D("mətnƏt", 0, 0, sətir),
  });
  return ü;
}

function fırlanan(m) {
  const o = { mətn: m === undefined ? "" : mətnə(m), işləyir: true };
  let ü;
  ü = new Modul("fırlanan", {
    "mətnDəyiş": D("mətnDəyiş", 1, 1, m_ => { o.mətn = mətnə(m_); return ü; }),
    "dayandır": D("dayandır", 0, 1, m_ => {
      if (!o.işləyir) return null;
      o.işləyir = false;
      P.yaz(m_ === undefined || m_ === null ? o.mətn : mətnə(m_));
      return null;
    }),
    "işləyir": D("işləyir", 0, 0, () => o.işləyir),
  });
  return ü;
}

function konsolCədvəl(b, s) {
  const hamısı = [siyahıya(b).map(mətnə)].concat(siyahıya(s).map(r => siyahıya(r).map(mətnə)));
  const say = Math.max(...hamısı.map(r => r.length));
  for (const r of hamısı) while (r.length < say) r.push("");
  const uz = x => [...x].length;
  const enlər = [];
  for (let i = 0; i < say; i++) enlər.push(Math.max(...hamısı.map(r => uz(r[i]))));
  hamısı.forEach((r, j) => {
    P.yaz(r.map((h, i) => h + " ".repeat(enlər[i] - uz(h))).join(" │ ").replace(/\s+$/, ""));
    if (j === 0) P.yaz(enlər.map(e => "─".repeat(e)).join("─┼─"));
  });
  return null;
}

//  Python round(): yarımda cüt tərəfə
function yuvarlaCüt(x) { const f = Math.floor(x); return x - f === 0.5 ? (f % 2 ? f + 1 : f) : Math.round(x); }

const sadəBoya = (a, k) => D(a, 1, 1, m => boya(m, k));
modullar["konsol"] = () => new Modul("konsol", {
  "qırmızı": sadəBoya("qırmızı", 31), "yaşıl": sadəBoya("yaşıl", 32),
  "sarı": sadəBoya("sarı", 33), "mavi": sadəBoya("mavi", 34),
  "boz": sadəBoya("boz", 90), "qalın": sadəBoya("qalın", 1),
  "altXətt": sadəBoya("altXətt", 4),
  "rəng": D("rəng", 1, 4, (adlı, m, ön, arxa, qalın) => {
    ön = adlıVəYa(adlı, "ön", ön); arxa = adlıVəYa(adlı, "arxa", arxa);
    qalın = adlıVəYa(adlı, "qalın", qalın);
    const k = [];
    if (qalın) k.push(1);
    if (ön !== undefined && ön !== null) k.push(rəngKodu(ön, "ön"));
    if (arxa !== undefined && arxa !== null) k.push(rəngKodu(arxa, "arxa") + 10);
    return boya(m, ...k);
  }, true),
  "təmizlə": D("təmizlə", 0, 0, () => { if (terminaldır()) P.yazSətirsiz("\x1b[2J\x1b[H"); return null; }),
  "kursor": D("kursor", 1, 2, (s, c) => { if (terminaldır())
    P.yazSətirsiz("\x1b[" + N(s) + ";" + (c === undefined ? 1 : N(c)) + "H"); return null; }),
  "ölçü": D("ölçü", 0, 0, () => new Kortej([
    BigInt(nodedir && process.stdout.columns || 80), BigInt(nodedir && process.stdout.rows || 24)])),
  "terminaldır": D("terminaldır", 0, 0, terminaldır),
  "soruş": D("soruş", 0, 2, (adlı, s, st) => {
    s = mətnə(adlıVəYa(adlı, "sual", s === undefined ? "" : s));
    st = adlıVəYa(adlı, "standart", st);
    const var_ = st !== undefined && st !== null;
    if (var_) s = (s ? s : "") + "[" + mətnə(st) + "] ";
    const c = konsolOxu(s);
    if (!c.trim() && var_) return mətnə(st);
    return c;
  }, true),
  "parolSoruş": D("parolSoruş", 0, 1, s => konsolOxu(mətnə(s === undefined ? "Parol: " : s))),
  "təsdiqlə": D("təsdiqlə", 1, 2, (adlı, s, st) => {
    st = adlıVəYa(adlı, "standart", st);
    const var_ = st !== undefined && st !== null;
    const ipucu = !var_ ? "(hə/yox)" : st ? "(HƏ/yox)" : "(hə/YOX)";
    for (;;) {
      const c = kiçiyə(konsolOxu(mətnə(s) + " " + ipucu + " ").trim());
      if (!c && var_) return !!st;
      if (BƏLİ.includes(c)) return true;
      if (XEYR.includes(c)) return false;
      P.yaz("`hə` və ya `yox` yazın.");
    }
  }, true),
  "seç": D("seç", 2, 2, (s, seçimlər) => {
    const l = seçimSiyahısı(seçimlər);
    seçimləriGöstər(s, l);
    for (;;) {
      const c = konsolOxu("Seçin (1–" + l.length + "): ").trim();
      if (konsolRəqəm(c) && Number(c) >= 1 && Number(c) <= l.length) return l[Number(c) - 1];
      for (const e of l) if (c && kiçiyə(mətnə(e)) === kiçiyə(c)) return e;
      P.yaz("1 ilə " + l.length + " arasında nömrə yazın.");
    }
  }),
  "çoxSeç": D("çoxSeç", 2, 2, (s, seçimlər) => {
    const l = seçimSiyahısı(seçimlər);
    seçimləriGöstər(s, l);
    for (;;) {
      const c = konsolOxu("Nömrələr (məs. 1,3; boş — heç biri): ").trim();
      if (!c) return [];
      const h = c.replace(/,/g, " ").split(/\s+/).filter(x => x);
      if (h.every(x => konsolRəqəm(x) && Number(x) >= 1 && Number(x) <= l.length)) {
        const görülən = [];
        for (const x of h) if (!görülən.includes(Number(x))) görülən.push(Number(x));
        return görülən.map(n => l[n - 1]);
      }
      P.yaz("1 ilə " + l.length + " arasında nömrələr yazın.");
    }
  }),
  "cədvəl": D("cədvəl", 2, 2, konsolCədvəl),
  "irəliləyiş": D("irəliləyiş", 1, 2, irəliləyiş),
  "fırlanan": D("fırlanan", 0, 1, fırlanan),
  "arqumentlər": D("arqumentlər", 0, 0, () => {
    throw xəta("ArqumentXətası", "`konsol.arqumentlər` JS hədəfində dəstəklənmir", "ALQ-M002");
  }),
});

const _modulKeş = Object.create(null);
function modul(a) {
  if (_modulKeş[a]) return _modulKeş[a];
  const f = modullar[a];
  if (!f) throw xəta("ArqumentXətası", "`" + a + "` modulu tapılmadı", "ALQ-M001");
  return (_modulKeş[a] = f());
}

for (const a of Object.keys(modullar)) {
  Object.defineProperty(g, a, { get: () => modul(a), enumerable: true, configurable: true });
}

/** Əlavə modul (vidjet, pəncərə, http) icra mühitinə qoşulur. */
function modulQeyd(a, f) {
  modullar[a] = f;
  delete _modulKeş[a];
  if (!a.includes("."))
    Object.defineProperty(g, a, { get: () => modul(a), enumerable: true, configurable: true });
}

// ── Sorğu (§ 4.13) ──────────────────────────────────────────────────────

/** `sırala a, b azalan`: sabit sıralama, hər açar öz istiqaməti ilə. */
function sorğuSırala(R, K, azalan) {
  const c = R.map((r, i) => [K[i], r]);
  c.sort((p, q) => {
    for (let i = 0; i < azalan.length; i++) {
      const n = sıraMüq(p[0][i], q[0][i]);
      if (n) return azalan[i] ? -n : n;
    }
    return 0;
  });
  return c.map(p => p[1]);
}

function sorğuQrupla(G, k, el) {
  let q = G.al(k);
  if (q === YOX) { q = []; G.qoy(k, q); }
  q.push(el);
}

function sorğuFərqli(N) {
  const görülən = new Set(), t = [];
  for (const x of N) {
    const a = açar(x);
    if (!görülən.has(a)) { görülən.add(a); t.push(x); }
  }
  return t;
}

/** `ilk n` / `atla n` */
function sorğuKəs(a, n, növ) {
  if (typeof n !== "bigint" || n < 0n)
    throw xəta("TipXətası", "`" + növ + "` mənfi olmayan tam ədəd gözləyir, `" + mətnə(n) + "` gəlib", "ALQ-T083");
  const k = Number(n);
  return növ === "ilk" ? a.slice(0, k) : a.slice(k);
}

/** `f(**lüğət)` — adlı arqumentlər və lüğətlər birləşir. */
function adlıYay(...hissələr) {
  const o = {};
  for (const h of hissələr) {
    if (h instanceof Lüğət) {
      for (const [k, v] of h.cütlər()) {
        if (typeof k !== "string")
          throw xəta("TipXətası", "`**` yalnız mətn açarlı lüğətə tətbiq olunur, `lüğət` verilib", "ALQ-T081");
        o[k] = v;
      }
    } else if (h !== null && typeof h === "object" && Object.getPrototypeOf(h) === Object.prototype) {
      Object.assign(o, h);
    } else {
      throw xəta("TipXətası", "`**` yalnız mətn açarlı lüğətə tətbiq olunur, `" + tip(h) + "` verilib", "ALQ-T081");
    }
  }
  return new Adlı(o);
}

/** Qlobal ad və ya `null` — bəzəyici axtarışı üçün. */
function qadVarsa(a) {
  const d = g[a];
  return d === undefined ? null : d;
}

// ── Bəzəyicilər (§ 5.11) ────────────────────────────────────────────────

/** `@a @b f` → `a(b(f))`; `null` bəzəyicilər (tapılmayan adlar) ötürülür. */
function bəzə(d, bəzəyicilər) {
  for (let i = bəzəyicilər.length - 1; i >= 0; i--)
    if (bəzəyicilər[i] !== null) d = ç(bəzəyicilər[i], d);
  return d;
}

/** `@ad(arq)` — əvvəl `ad(arq)` çağırılır. */
function bəzəyici(d, arq) {
  return d === null ? null : ç(d, ...arq());
}

/** Bəzəyiciyə ötürülən metod: birinci arqument `özü`-dür. */
function sərbəstMetod(f, a) {
  return ad(function (...args) {
    if (!args.length || args[0] instanceof Adlı)
      throw xəta("ArqumentXətası",
        "`" + a + "` metodu `özü` arqumenti olmadan çağırıldı", "ALQ-R022");
    return f.apply(args[0], args.slice(1));
  }, a, "funksiya");
}

/** Bəzənmiş metod: obyekt üzərindən çağırılanda `özü` ilk arqumentdir. */
function bəzənmişMetod(h, a) {
  return ad(function (...args) { return ç(h, this, ...args); }, a, "funksiya");
}

/** Qlobal ad (kompilyator yerli elan tapmayanda). */
function qad(a) {
  const d = g[a];
  if (d === undefined)
    throw xəta("ArqumentXətası", "`" + a + "` təyin edilməyib", "ALQ-T022");
  return d;
}

function idxalElement(m, a, element) {
  if (!m.üzvlər.has(element))
    throw xəta("ArqumentXətası", "`" + a + "` modulunda `" + element + "` ixracı yoxdur", "ALQ-M002");
  return m.üzvlər.get(element);
}

// ── Fayl modulları (paketlənmiş) ────────────────────────────────────────

const _fayllar = Object.create(null);
const _faylKeş = Object.create(null);
function faylQeyd(açar_, ad_, f) { _fayllar[açar_] = [ad_, f]; }
function faylModul(açar_) {
  if (_faylKeş[açar_]) return _faylKeş[açar_];
  const q = _fayllar[açar_];
  if (!q) throw xəta("ArqumentXətası", '"' + açar_ + '" modul faylı tapılmadı', "ALQ-M001");
  const [ad_, f] = q;
  const m = new Modul(ad_, new Map());
  _faylKeş[açar_] = m;
  f(m);
  return m;
}

// ═══════════════════════════════════════════════════════════════════════
//  Proqramın icrası
// ═══════════════════════════════════════════════════════════════════════

/**
 * Proqramı işlədir. Qaytarır: çıxış kodu. `seçimlər.yaz/oxu` ilə giriş
 * və çıxışı yönləndirmək olar (sınaqlar və brauzer üçün).
 */
function işlət(proqram, seçimlər) {
  seçimlər = seçimlər || {};
  if (seçimlər.yaz) { P.yaz = seçimlər.yaz; P.yazSətirsiz = seçimlər.yazSətirsiz || seçimlər.yaz; }
  if (seçimlər.yazXəta) P.yazXəta = seçimlər.yazXəta;
  if (seçimlər.oxu) P.oxu = seçimlər.oxu;
  if (seçimlər.arqumentlər) P.arqumentlər = seçimlər.arqumentlər;
  V.d = 0;
  try {
    const əsas = proqram();
    if (typeof əsas === "function") {
      const arq = əsas.$pSay ? [P.arqumentlər.slice()] : [];
      let n = əsas(...arq);
      if (n instanceof Gələcək) n = n.al();
      aktyorlarıBoşalt();
      if (typeof n === "bigint") return Number(n);
    }
    aktyorlarıBoşalt();
    return 0;
  } catch (e0) {
    if (e0 instanceof Yayılan) return 0;
    const e = xətaya(e0);
    if (e instanceof Dayanma) return Number(e.kod);
    if (seçimlər.xəta) seçimlər.xəta(e);
    else P.yazXəta("✖ " + (e.kod || "ALQ-R000") + "  " + e.tip + ": " + e.mesaj);
    return 1;
  }
}


// ── Kompilyator köməkçiləri ─────────────────────────────────────────────

function inc(x, d) {
  if (typeof x === "bigint") return x + d;
  if (typeof x === "number") return x + Number(d);
  throw xəta("TipXətası", "`" + (d > 0n ? "++" : "--") + "` ədəd gözləyir, `" +
    tip(x) + "` gəlib", "ALQ-T008");
}
function sabitXəta(a) {
  throw xəta("ArqumentXətası", "`" + a + "` sabitdir, dəyişdirilə bilməz", "ALQ-T020");
}
function qQoy(a, v) {
  if (!(a in g)) throw xəta("ArqumentXətası", "`" + a + "` təyin edilməyib", "ALQ-T022");
  Object.defineProperty(g, a, { value: v, writable: true, enumerable: true, configurable: true });
  return v;
}
function xətaAt(t, m, k) { throw xəta(t, m, k); }
function çevirT(x, h) {
  try { return çevir(x, h); }
  catch (e) { if (e instanceof AlqorXəta) return null; throw e; }
}
function boru(v, f) { return ç(f, v); }
function təhlükəsiz(f) {
  try { return f(); }
  catch (e) { if (e instanceof AlqorXəta || e instanceof ReferenceError) return null; throw e; }
}
function resursBağla(d) {
  if (d instanceof Nümunə) {
    const m = d.s.metod("bağla");
    if (m !== undefined) { m.call(d); return; }
  }
  if (d instanceof Gen) GENERATOR["bağla"](d);
}
function gecikmişləri(a) {
  for (let i = a.length - 1; i >= 0; i--) {
    try { a[i](); } catch (e) { if (!(e instanceof AlqorXəta)) throw e; }
  }
}
function təkrarSay(n) {
  if (typeof n !== "bigint")
    throw xəta("TipXətası", "`təkrarla` tam ədəd gözləyir, `" + tip(n) + "` gəlib", "ALQ-T001");
  return n;
}
function lüğətLit(cütlər) {
  const l = new Lüğət();
  for (const [k, v] of cütlər) {
    if (k === YOX) {
      if (!(v instanceof Lüğət)) throw xəta("TipXətası", "`...` lüğətdə lüğət gözləyir", "ALQ-T001");
      for (const [a, d] of v.cütlər()) l.qoy(a, d);
    } else l.qoy(k, v);
  }
  return l;
}
function yaddaşla(f) {
  const keş = new Map();
  const w = function (...args) {
    if (args.length && args[args.length - 1] instanceof Adlı) return f.apply(this, args);
    const a = args.map(x => (x === null || typeof x !== "object" && typeof x !== "function")
      ? typeof x + ":" + String(x) : "#" + obyektId(x)).join("\u0001");
    if (keş.has(a)) return keş.get(a);
    const n = f.apply(this, args);
    keş.set(a, n);
    return n;
  };
  return ad(w, f.$ad, f.$n, f.$pSay);
}

/** Sınaqlar arasında vəziyyəti sıfırlayır. */
function sıfırla() {
  genişlətmələr.clear();
  for (const k of Object.keys(_modulKeş)) delete _modulKeş[k];
  for (const k of Object.keys(_faylKeş)) delete _faylKeş[k];
  _toxum = null;
  V.d = 0;
  AKTYORLAR.length = 0;
  XƏTALI_MESAJLAR.length = 0;
}

return {
  sıfırla, inc, sabitXəta, qQoy, xətaAt, çevirT, boru, təhlükəsiz, resursBağla, gecikmişləri,
  təkrarSay, lüğətLit, yaddaşla, ATLA,
  // tiplər
  AlqorXəta, Dayanma, Adlı, Kortej, Lüğət, Dəst, Diapazon, Bayt, Gen, Gələcək,
  Element, Modul, Sinif, Nümunə, Üst, TipAlias, Sadalama, SDəyər, YOX, Yayılan,
  // xətalar
  xəta, xətaya, xətaUyğun, xətaObyekti, at, stek, V, STEK_HƏDDİ,
  // funksiyalar
  ad, D, bağla, ç, çm, yarat, yeni, adlıYay, vahidli, sorğuSırala, sorğuQrupla, sorğuFərqli, sorğuKəs, qadVarsa, bəzə, bəzəyici, sərbəstMetod, bəzənmişMetod, kp, genişlət, standartDəyər, sinif, sadalama,
  metodAd, üstMetod, bağlı, qurucuTap,
  // operatorlar
  add, sub, mul, div, idiv, mod, pow, bit, neg, bnot, ş, eq, ne, lt, gt, le, ge, cmp3,
  // üzv/indeks
  üzv, üzvQoy, ind, indQoy, dilim, iter, siyahıya, dağıt, diapazon, addımla,
  // tiplər
  tip, tipUyğun, çevir, üzvlük, açMəcburi, yay, gözlə, mətnə, formatla,
  // naxışlar
  naxışDiapazon, naxışKortej, naxışSiyahı, naxışObyekt, sdSahə,
  // JSX
  jsx,
  // modullar
  g, qad, modul, idxalElement, faylQeyd, faylModul, genişlətmə,
  // icra
  işlət, P,
  // əlavə modullar üçün daxili köməkçilər
  Yerli, modulQeyd, Gələcək, Bayt, pyFormat, onluqRepr, böyüyə, kiçiyə, latınla,
  htmlQaç, çağırılandır, elementHTML, KICIK, jsonHazırla, jsonYaz, jsonOxu, nodedir,
};
})();

if (typeof module !== "undefined" && module.exports) module.exports = $;
