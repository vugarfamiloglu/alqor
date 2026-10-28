// ═══════════════════════════════════════════════════════════════════════
//  `http` modulu — HTTP müştərisi (Python `modullar/http_.py` ilə eyni API)
//
//  Funksiyalar `Gələcək` qaytarır; `gözlə` sorğunu SİNXRON icra edir:
//    brauzer — sinxron XMLHttpRequest (CORS qaydaları brauzerindir)
//    Node.js — uşaq prosesdə `fetch` (execFileSync), nəticə JSON ilə gəlir
// ═══════════════════════════════════════════════════════════════════════

(function ($) {
"use strict";

const { Yerli, Lüğət, Kortej, Nümunə, D, xəta, mətnə, tip } = $;

const METODLAR = {
  "AL": "GET", "GÖNDƏR": "POST", "YENİLƏ": "PUT", "YAMAQ": "PATCH",
  "SİL": "DELETE", "BAŞLIQ": "HEAD", "SEÇİMLƏR": "OPTIONS",
  "GET": "GET", "POST": "POST", "PUT": "PUT", "PATCH": "PATCH",
  "DELETE": "DELETE", "HEAD": "HEAD", "OPTIONS": "OPTIONS",
};
const AGENT = "Alqor-http/2.4.0";
const hx = (t, m) => xəta(t, m, "ALQ-R010");

function urlYoxla(url) {
  if (typeof url !== "string")
    throw xəta("TipXətası", "URL mətn olmalıdır, `" + tip(url) + "` gəlib", "ALQ-T001");
  let u = null;
  try { u = new URL(url); } catch (e) { u = null; }
  if (!u || (u.protocol !== "http:" && u.protocol !== "https:") || !u.host)
    throw xəta("DəyərXətası", "`" + url + "` — yalnız http:// və https:// ünvanlarına icazə var",
      "ALQ-T001");
  return u.href;
}

function cütlər(d) {
  if (d === null || d === undefined) return [];
  if (d instanceof Lüğət) return [...d.cütlər()].map(([a, b]) => [mətnə(a), b]);
  if (d instanceof Nümunə) return [...d.f];
  throw xəta("TipXətası", "lüğət gözlənilirdi, `" + tip(d) + "` gəlib", "ALQ-T001");
}
const formaKodla = c => c.map(([a, b]) =>
  encodeURIComponent(a).replace(/%20/g, "+") + "=" + encodeURIComponent(mətnə(b)).replace(/%20/g, "+"))
  .join("&");

// ── Cavab ───────────────────────────────────────────────────────────────

function cavabMətni(c) {
  const növ = c.d.başlıqlar["content-type"] || "";
  let k = "utf-8";
  if (növ.includes("charset=")) k = növ.split("charset=").pop().split(";")[0].trim();
  try { return new TextDecoder(k).decode(c.d.gövdə); }
  catch (e) { return new TextDecoder("utf-8").decode(c.d.gövdə); }
}
const uğurlu = c => c.d.kod >= 200 && c.d.kod < 300;
const CAVAB_C = {
  $mətn: c => "<http cavabı " + c.d.kod + ">",
  "kod": c => BigInt(c.d.kod),
  "uğurlu": c => uğurlu(c),
  "yoxla": c => {
    if (!uğurlu(c)) {
      const p = [...cavabMətni(c)].slice(0, 200).join("");
      throw xəta("HTTPXətası", c.d.kod + " — " + c.d.url + (p ? ": " + p : ""), "ALQ-R010");
    }
    return c;
  },
  "mətn": c => cavabMətni(c),
  "json": c => {
    try { return $.jsonOxu(cavabMətni(c)); }
    catch (e) {
      const x = $.xətaya(e);
      throw xəta("JSONXətası", "cavab JSON deyil" + String(x.mesaj || "").replace(/^JSON formatı pozulub/, ""),
        "ALQ-R005");
    }
  },
  "bayt": c => new $.Bayt(c.d.gövdə),
  "başlıq": (c, a, s) => {
    const d = c.d.başlıqlar[mətnə(a).toLowerCase()];
    return d === undefined ? (s === undefined ? null : s) : d;
  },
  "başlıqlar": c => { const l = new Lüğət(); for (const k of Object.keys(c.d.başlıqlar)) l.qoy(k, c.d.başlıqlar[k]); return l; },
  "url": c => c.d.url,
};
const yeniCavab = (kod, başlıqlar, gövdə, url) =>
  new Yerli("httpCavabı", CAVAB_C, { kod, başlıqlar, gövdə, url });

// ── Sorğunun icrası ─────────────────────────────────────────────────────

function tamUrl(s) {
  if (!s.parametrlər.length) return s.url;
  return s.url + (s.url.includes("?") ? "&" : "?") + formaKodla(s.parametrlər);
}

const NODE_SKRİPTİ = `
let g = "";
process.stdin.on("data", d => g += d);
process.stdin.on("end", async () => {
  const s = JSON.parse(g);
  try {
    const c = await fetch(s.url, { method: s.metod, headers: s.başlıqlar,
      body: s.gövdə === null ? undefined : Buffer.from(s.gövdə, "base64"),
      redirect: s.yönləndir ? "follow" : "manual", signal: AbortSignal.timeout(s.vaxt) });
    const b = {};
    c.headers.forEach((v, k) => { b[k] = v; });
    const gövdə = Buffer.from(await c.arrayBuffer()).toString("base64");
    process.stdout.write(JSON.stringify({ kod: c.status, başlıqlar: b, gövdə, url: c.url || s.url }));
  } catch (e) {
    const vaxt = e && (e.name === "TimeoutError" || e.name === "AbortError");
    const səbəb = e && e.cause ? (e.cause.code || e.cause.message) : (e && e.message);
    process.stdout.write(JSON.stringify({ xəta: vaxt ? "vaxt" : "bağlantı", səbəb: String(səbəb) }));
  }
});`;

function icra(s) {
  const url = tamUrl(s);
  const başlıqlar = Object.assign({ "User-Agent": AGENT, "Accept-Encoding": "identity" }, s.başlıqlar);
  if ($.nodedir) {
    const cp = require("child_process");
    const giriş = JSON.stringify({ url, metod: s.metod, başlıqlar, yönləndir: s.yönləndir,
      vaxt: Math.round(s.vaxt * 1000),
      gövdə: s.gövdə === null ? null : Buffer.from(s.gövdə).toString("base64") });
    let ç;
    try {
      ç = cp.execFileSync(process.execPath, ["-e", NODE_SKRİPTİ],
        { input: giriş, maxBuffer: 1 << 30, timeout: Math.round(s.vaxt * 1000) + 5000 });
    } catch (e) {
      throw hx("VaxtBitdiXətası", s.url + ": " + fmtS(s.vaxt) + " s ərzində cavab gəlmədi");
    }
    const n = JSON.parse(ç.toString("utf8"));
    if (n.xəta === "vaxt")
      throw hx("VaxtBitdiXətası", s.url + ": " + fmtS(s.vaxt) + " s ərzində cavab gəlmədi");
    if (n.xəta) throw hx("BağlantıXətası", s.url + ": " + n.səbəb);
    return yeniCavab(n.kod, n.başlıqlar, new Uint8Array(Buffer.from(n.gövdə, "base64")), n.url);
  }
  if (typeof XMLHttpRequest === "undefined")
    throw hx("BağlantıXətası", "bu mühitdə HTTP sorğusu mümkün deyil");
  const x = new XMLHttpRequest();
  x.open(s.metod, url, false);
  x.overrideMimeType("text/plain; charset=x-user-defined");
  for (const k of Object.keys(başlıqlar)) {
    if (/^(user-agent|accept-encoding)$/i.test(k)) continue;   // brauzer qadağan edir
    try { x.setRequestHeader(k, başlıqlar[k]); } catch (e) { /* qadağan başlıq */ }
  }
  try { x.send(s.gövdə === null ? null : s.gövdə); }
  catch (e) { throw hx("BağlantıXətası", s.url + ": " + (e && e.message || "sorğu alınmadı")); }
  if (x.status === 0) throw hx("BağlantıXətası", s.url + ": bağlantı alınmadı (CORS və ya şəbəkə)");
  const t = x.responseText || "";
  const u8 = new Uint8Array(t.length);
  for (let i = 0; i < t.length; i++) u8[i] = t.charCodeAt(i) & 0xff;
  const b = {};
  for (const sətir of x.getAllResponseHeaders().trim().split(/[\r\n]+/)) {
    const i = sətir.indexOf(":");
    if (i > 0) b[sətir.slice(0, i).trim().toLowerCase()] = sətir.slice(i + 1).trim();
  }
  return yeniCavab(x.status, b, u8, x.responseURL || url);
}
const fmtS = v => $.pyFormat(v, "g");

// ── Sorğu ───────────────────────────────────────────────────────────────

function yeniSorğu(metod, url) {
  const m = METODLAR[mətnə(metod).toUpperCase()];
  if (m === undefined)
    throw xəta("DəyərXətası", "`" + mətnə(metod) + "` HTTP metodu deyil — AL, GÖNDƏR, YENİLƏ, YAMAQ, SİL",
      "ALQ-T001");
  return new Yerli("httpSorğusu", SORĞU_C, { metod: m, url: urlYoxla(url), başlıqlar: {},
    parametrlər: [], gövdə: null, vaxt: 30, yönləndir: true });
}
const kodla = m => new TextEncoder().encode(m);
function sJson(s, x) {
  s.d.gövdə = kodla($.jsonYaz(x, false));
  s.d.başlıqlar["Content-Type"] = "application/json; charset=utf-8";
  return s;
}
const SORĞU_C = {
  $mətn: s => "<http sorğusu " + s.d.metod + " " + s.d.url + ">",
  "başlıq": (s, a, d) => { s.d.başlıqlar[mətnə(a)] = mətnə(d); return s; },
  "parametr": (s, a, d) => { s.d.parametrlər.push([mətnə(a), mətnə(d)]); return s; },
  "gövdə": (s, x) => {
    if (x instanceof $.Bayt) {
      s.d.gövdə = x.u;
      if (!("Content-Type" in s.d.başlıqlar)) s.d.başlıqlar["Content-Type"] = "application/octet-stream";
    } else if (typeof x === "string") {
      s.d.gövdə = kodla(x);
      if (!("Content-Type" in s.d.başlıqlar)) s.d.başlıqlar["Content-Type"] = "text/plain; charset=utf-8";
    } else if (x === null) s.d.gövdə = null;
    else return sJson(s, x);
    return s;
  },
  "json": (s, x) => sJson(s, x),
  "forma": (s, l) => {
    s.d.gövdə = kodla(formaKodla(cütlər(l)));
    s.d.başlıqlar["Content-Type"] = "application/x-www-form-urlencoded";
    return s;
  },
  "vaxtLimiti": (s, ms) => { s.d.vaxt = Math.max(0.001, Number(ms) / 1000); return s; },
  "göndər": s => new $.Gələcək(() => icra(s.d), "http " + s.d.metod + " " + s.d.url),
  "url": s => tamUrl(s.d),
  "metod": s => s.d.metod,
};

function metod(m) {
  return $.ad((url, adlı) => {
    const k = adlı instanceof $.Adlı ? adlı.o : {};
    const s = yeniSorğu(m, url);
    for (const [a, d] of cütlər(k["başlıqlar"])) SORĞU_C["başlıq"](s, a, d);
    for (const [a, d] of cütlər(k["parametrlər"])) SORĞU_C["parametr"](s, a, d);
    if (k["json"] !== undefined && k["json"] !== null) sJson(s, k["json"]);
    else if (k["forma"] !== undefined && k["forma"] !== null) SORĞU_C["forma"](s, k["forma"]);
    else if (k["gövdə"] !== undefined && k["gövdə"] !== null) SORĞU_C["gövdə"](s, k["gövdə"]);
    if (k["vaxtLimiti"] !== undefined && k["vaxtLimiti"] !== null) SORĞU_C["vaxtLimiti"](s, k["vaxtLimiti"]);
    if (k["yönləndir"] !== undefined) s.d.yönləndir = k["yönləndir"] !== false;
    const icazəli = ["başlıqlar", "parametrlər", "json", "forma", "gövdə", "vaxtLimiti", "yönləndir"];
    for (const a of Object.keys(k))
      if (!icazəli.includes(a)) throw xəta("ArqumentXətası", "`http` naməlum adlı arqument: " + a, "ALQ-T004");
    return SORĞU_C["göndər"](s);
  }, m, "daxili");
}
const dəstəkYox = ad => D(ad, 0, null, () => {
  throw xəta("ArqumentXətası", "`http." + ad + "` JS hədəfində dəstəklənmir — Python icraçısı ilə " +
    "işlədin (`alqor işlət`)", "ALQ-M002");
});

$.modulQeyd("http", () => new $.Modul("http", {
  "al": metod("GET"), "göndər": metod("POST"), "yenilə": metod("PUT"),
  "yamaq": metod("PATCH"), "sil": metod("DELETE"), "başlıq": metod("HEAD"),
  "Sorğu": D("Sorğu", 2, 2, yeniSorğu),
  "faylYüklə": dəstəkYox("faylYüklə"), "faylGöndər": dəstəkYox("faylGöndər"),
  "vebSoket": dəstəkYox("vebSoket"),
}));
})($);
