// ═══════════════════════════════════════════════════════════════════════
//  `pəncərə` modulu — brauzerdə və Node.js-də (başsız)
//
//  Python-dakı `pencere.py` ilə eyni model: komponentin `göstər()`
//  nəticəsi HTML-ə çevrilir, hadisə idarəediciləri reyestrə yazılır
//  (`data-a-klik="n1h3"`). Fərq: server yoxdur — brauzerdə hadisə birbaşa
//  bu icra mühitində işləyir, sonra kök yenidən göstərilir və DOM yamaqla
//  (`yamaq()`, fokus və yazılan dəyər qorunur) yenilənir.
//
//  Node.js-də pəncərə açılmır (Python-un başsız rejimi kimi):
//  `pəncərə.sınaq` sürücüsü və dialoq cavabları işləyir.
// ═══════════════════════════════════════════════════════════════════════

(function ($) {
"use strict";

const { Element, Nümunə, Kortej, Lüğət, Yerli, D, xəta, mətnə, tip } = $;
const brauzerdir = typeof document !== "undefined" && !$.nodedir;

// Alqor atributu → [DOM hadisəsi, ASCII şəkilçi] — pencere.HADİSƏLƏR
const HADİSƏLƏR = {
  "klik": ["click", "klik"], "ikiKlik": ["dblclick", "ikiklik"],
  "dəyişdi": ["change", "deyisdi"], "yazıldı": ["input", "yazildi"],
  "göndərildi": ["submit", "gonderildi"], "fokus": ["focusin", "fokus"],
  "fokusGetdi": ["focusout", "fokusgetdi"], "düyməBasma": ["keydown", "duymebasma"],
  "düyməBuraxma": ["keyup", "duymeburaxma"], "siçanÜstdə": ["mouseover", "sicanustde"],
  "siçanÇıxdı": ["mouseout", "sicancixdi"], "sürükləndi": ["dragstart", "suruklendi"],
  "buraxıldı": ["drop", "buraxildi"], "sürüşdü": ["scroll", "surusdu"],
  "basıldı": ["pointerdown", "basildi"],
};
const TƏK_TEQLƏR = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input",
  "link", "meta", "source", "track", "wbr"]);
const ATRIBUTLAR = {
  "sinif": "class", "üslub": "style", "kimlik": "id", "növ": "type",
  "dəyər": "value", "ad": "name", "yer": "placeholder",
  "başlıq": "title", "mənbə": "src", "ünvan": "href",
  "alternativ": "alt", "sıra": "tabindex", "söndürülmüş": "disabled",
  "oxunaqlı": "readonly", "tələb": "required", "seçilmiş": "selected",
  "işarələnmiş": "checked", "en": "width", "hündürlük": "height",
  "hədəf": "target", "rol": "role",
};

function qaç(m) {
  return m.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
const çağırılan = d => typeof d === "function" || $.çağırılandır(d);

// ── Reyestr və HTML ─────────────────────────────────────────────────────

class Reyestr {
  constructor() { this.c = new Map(); this.say = 0; this.nəsil = 0; }
  sıfırla() { this.c.clear(); this.say = 0; this.nəsil++; }
  yaz(f) { const a = "n" + this.nəsil + "h" + (++this.say); this.c.set(a, f); return a; }
  al(a) { return this.c.get(a); }
}

function HTMLə(d, r) {
  if (d === null || d === undefined || d === false) return "";
  if (d === true) return "doğru";
  if (d instanceof Element) return elementHTML(d, r);
  if (Array.isArray(d)) return d.map(u => HTMLə(u, r)).join("");
  if (d instanceof Kortej) return d.e.map(u => HTMLə(u, r)).join("");
  if (typeof d === "string") return qaç(d);
  return qaç(mətnə(d));
}

function elementHTML(e, r) {
  if (e.ad === "") return e.uşaqlar.map(u => HTMLə(u, r)).join("");
  let atr = "";
  for (const [ad, d] of e.atributlar.cütlər()) {
    if (Object.prototype.hasOwnProperty.call(HADİSƏLƏR, ad)) {
      if (d === null || d === undefined) continue;
      if (!çağırılan(d))
        throw xəta("TipXətası", "`" + ad + "` atributu funksiya olmalıdır, `" + tip(d) +
          "` gəlib", "ALQ-T008");
      atr += " data-a-" + HADİSƏLƏR[ad][1] + '="' + r.yaz(d) + '"';
      continue;
    }
    if (çağırılan(d)) continue;
    const h = ATRIBUTLAR[ad] || ad;
    if (d === true) atr += " " + h;
    else if (d === false || d === null || d === undefined) continue;
    else atr += " " + h + '="' + qaç(mətnə(d)) + '"';
  }
  if (TƏK_TEQLƏR.has(e.ad)) return "<" + e.ad + atr + ">";
  return "<" + e.ad + atr + ">" + e.uşaqlar.map(u => HTMLə(u, r)).join("") + "</" + e.ad + ">";
}

// ── Adlı arqumentlər ────────────────────────────────────────────────────

/** Alqor çağırışını (mövqeli + adlı) parametr siyahısına bağlayır. */
function bağla(ad, parametrlər, standartlar, args) {
  let adlı = null;
  if (args.length && args[args.length - 1] instanceof $.Adlı) adlı = args.pop().o;
  if (args.length > parametrlər.length)
    throw xəta("ArqumentXətası", "`" + ad + "` ən çox " + parametrlər.length +
      " arqument qəbul edir, " + args.length + " verilib", "ALQ-T003");
  const d = args.slice();
  if (adlı) for (const k of Object.keys(adlı)) {
    const i = parametrlər.indexOf(k);
    if (i < 0) throw xəta("ArqumentXətası", "`" + ad + "` naməlum adlı arqument: " + k, "ALQ-T004");
    d[i] = adlı[k];
  }
  for (let i = 0; i < parametrlər.length; i++) {
    if (d[i] === undefined) {
      if (standartlar[i] === undefined)
        throw xəta("ArqumentXətası", "`" + ad + "` üçün `" + parametrlər[i] +
          "` arqumenti verilməyib", "ALQ-T003");
      d[i] = standartlar[i];
    }
  }
  return d;
}
function DA(ad, parametrlər, standartlar, f) {
  return $.ad((...args) => f(...bağla(ad, parametrlər, standartlar, args)), ad, "daxili");
}
function sadəObyekt(x) {
  if (x === null || typeof x !== "object") return false;
  const p = Object.getPrototypeOf(x);
  return p === null || p === Object.prototype;
}
/** Yerli obyektin metodu: `(o, ...args)` — sonuncu arqument adlı obyekt ola bilər. */
function M(ad, parametrlər, standartlar, f) {
  return (o, ...args) => {
    if (args.length && sadəObyekt(args[args.length - 1]))
      args[args.length - 1] = new $.Adlı(args[args.length - 1]);
    return f(o, ...bağla(ad, parametrlər, standartlar, args));
  };
}
const siyahıya = d => Array.isArray(d) ? d.slice() : d instanceof Kortej ? d.e.slice() : [d];

// ═══════════════════════════════════════════════════════════════════════
//  Tətbiq
// ═══════════════════════════════════════════════════════════════════════

const T = {
  pəncərələr: [],
  aktiv: null,
  dialoqCavabları: [],
  dialoqJurnalı: [],
  başsız: !brauzerdir,
};
const açıqlar = () => T.pəncərələr.filter(p => p.d.açıq);

// ── Menyu ───────────────────────────────────────────────────────────────

const MENYU_C = { $mətn: m => "<menyu " + m.d.ad + ">" };
const ELEMENT_C = { $mətn: m => "<menyu elementi " + m.d.ad + ">" };

function qısayolNormal(q) {
  const h = String(q).split("+").map(x => x.trim().toLowerCase()).filter(x => x);
  const sıra = { "ctrl": 0, "control": 0, "cmd": 1, "meta": 1, "alt": 2, "shift": 3 };
  const dəy = h.filter(x => x in sıra).sort((a, b) => sıra[a] - sıra[b])
    .map(d => d === "control" ? "ctrl" : d === "cmd" ? "meta" : d);
  return dəy.concat(h.filter(x => !(x in sıra))).join("+");
}

function menyuHTML(menyular, r) {
  if (!menyular.length) return "";
  const n = [];
  for (const m of menyular) {
    const el = [];
    for (const e of m.d.elementlər) {
      const x = e.d;
      if (x.ayırıcı) { el.push('<li class="ayırıcı"></li>'); continue; }
      const sinif = ["element"];
      let atr = "";
      if (x.söndürülmüş || x.klik === null || x.klik === undefined) sinif.push("sönük");
      else {
        atr = ' data-a-klik="' + r.yaz(x.klik) + '" data-a-ad="' + qaç(x.ad) + '"';
        if (x.qısayol) atr += ' data-a-qisayol="' + qaç(qısayolNormal(x.qısayol)) + '"';
      }
      let işarə = "";
      if (x.işarələnmiş !== null && x.işarələnmiş !== undefined)
        işarə = x.işarələnmiş ? '<span class="işarə">✓</span>' : '<span class="işarə"></span>';
      const qısa = x.qısayol ? '<span class="qısayol">' + qaç(x.qısayol) + "</span>" : "";
      el.push('<li class="' + sinif.join(" ") + '"' + atr + ">" + işarə +
        '<span class="mətn">' + qaç(x.ad) + "</span>" + qısa + "</li>");
    }
    n.push('<div class="menyu"><button class="başlıq">' + qaç(m.d.ad) +
      '</button><ul class="açılan">' + el.join("") + "</ul></div>");
  }
  return n.join("");
}

// ── Pəncərə ─────────────────────────────────────────────────────────────

function məzmunuÇevir(p) {
  const s = p.d;
  let d = s.məzmun;
  if (s.komponent !== null) {
    const n = s.komponent;
    const g = n.s.metod("göstər");
    if (g === undefined)
      throw xəta("TipXətası", "`" + n.s.ad + "` komponentində `göstər()` metodu yoxdur", "ALQ-T053");
    n.k = null;                      // tənbəl hesablananların keşi köhnədir
    d = g.call(n);
  } else if (çağırılan(d)) d = $.ç(d);
  return HTMLə(d, s.reyestr);
}
function kökHTML(p) { p.d.reyestr.sıfırla(); return məzmunuÇevir(p); }

function hadisəniİşlət(p, açar, dəyər) {
  const s = p.d;
  const f = s.reyestr.al(açar);
  if (f === undefined)
    return { html: kökHTML(p), menyu: menyuHTML(s.menyular, s.reyestr), başlıq: s.başlıq, köhnə: true };
  if (dəyər === null || dəyər === undefined) $.ç(f);
  else $.ç(f, dəyər);
  if (!s.açıq) return { bağlı: true };
  return { html: kökHTML(p), menyu: menyuHTML(s.menyular, s.reyestr), başlıq: s.başlıq };
}

function bağlaP(p) {
  const s = p.d;
  if (!s.açıq) return;
  if (s.bağlananda !== null) $.ç(s.bağlananda);
  s.açıq = false;
  if (brauzerdir && T.aktiv === p) {
    const digər = açıqlar();
    T.aktiv = digər.length ? digər[digər.length - 1] : null;
    if (T.aktiv) brauzerdəGöstər(T.aktiv, true);
    else bağlandıSəhifəsi();
  }
}

const PƏNCƏRƏ_C = {
  $mətn: p => "<pəncərə " + p.d.başlıq + ">",
  "başlıq": (p, m) => {
    if (m === undefined || m === null) return p.d.başlıq;
    p.d.başlıq = mətnə(m);
    if (brauzerdir && T.aktiv === p) document.title = p.d.başlıq;
    return p;
  },
  "məzmun": M("məzmun", ["dəyər"], [undefined], (p, d) => {
    const s = p.d;
    s.məzmun = d; s.komponent = null;
    if (d instanceof Element && d.komponent) s.komponent = d.komponent;
    else if (d instanceof Nümunə) {
      if (d.s.metod("göstər") === undefined)
        throw xəta("TipXətası", "`" + d.s.ad + "` komponent deyil — `göstər()` metodu yoxdur",
          "ALQ-T053");
      s.komponent = d;
    }
    return p;
  }),
  "menyu": M("menyu", ["menyular"], [undefined], (p, m) => {
    p.d.menyular = siyahıya(m).filter(x => x instanceof Yerli && x.c === MENYU_C);
    return p;
  }),
  "üslub": M("üslub", ["CSS"], [undefined], (p, c) => { p.d.üslub = mətnə(c); return p; }),
  "ölç": M("ölç", ["en", "hündürlük"], [undefined, undefined], (p, e, h) => {
    p.d.en = e; p.d.hündürlük = h; return p; }),
  "mərkəzə": p => p,
  "ölçüsüSabit": p => p,
  "bağlananda": M("bağlananda", ["idarəedici"], [undefined], (p, f) => { p.d.bağlananda = f; return p; }),
  "göstər": p => {
    if (!p.d.açıq) {
      p.d.açıq = true;
      if (brauzerdir) { T.aktiv = p; brauzerdəGöstər(p, true); }
    }
    return p;
  },
  "bağla": p => { bağlaP(p); return null; },
  "açıqdır": p => p.d.açıq,
  "yenilə": p => { if (brauzerdir && T.aktiv === p) brauzerdəGöstər(p, false); else kökHTML(p); return p; },
  "gözlə": () => null,
  "ünvan": () => brauzerdir ? String(location.href) : "",
};

function yeniPəncərə(başlıq, en, hündürlük) {
  const p = new Yerli("Pəncərə", PƏNCƏRƏ_C, {
    başlıq: mətnə(başlıq), en, hündürlük, məzmun: null, komponent: null,
    menyular: [], reyestr: new Reyestr(), açıq: false, üslub: "", bağlananda: null,
  });
  T.pəncərələr.push(p);
  return p;
}

// ── Brauzer: DOM-a göstərmə ─────────────────────────────────────────────

const B = globalThis;
function brauzerdəGöstər(p, tam) {
  const kök = document.getElementById("alqor-kök");
  const menyu = document.getElementById("alqor-menyu");
  let üslub = document.getElementById("alqor-pəncərə-üslubu");
  if (!üslub) {
    üslub = document.createElement("style");
    üslub.id = "alqor-pəncərə-üslubu";
    document.head.appendChild(üslub);
  }
  if (üslub.textContent !== p.d.üslub) üslub.textContent = p.d.üslub;
  let html;
  try { html = kökHTML(p); }
  catch (e) { xətanıGöstər(e); return; }
  if (kök) {
    if (tam || typeof B.$alqorYamaq !== "function") kök.innerHTML = html;
    else B.$alqorYamaq(kök, html);
  }
  if (menyu) {
    const m = menyuHTML(p.d.menyular, p.d.reyestr);
    menyu.innerHTML = m; menyu.hidden = !m;
  }
  document.title = p.d.başlıq;
}
function xətaMətni(e) {
  const x = $.xətaya(e);
  if (x instanceof $.AlqorXəta) return "✖ " + (x.kod || "ALQ-R000") + "  " + x.tip + ": " + x.mesaj;
  return String(x && x.stack || x);
}
function xətanıGöstər(e) {
  const kök = document.getElementById("alqor-kök");
  if (kök) kök.innerHTML = '<pre id="alqor-xəta">' + qaç(xətaMətni(e)) + "</pre>";
}
function bağlandıSəhifəsi() {
  const kök = document.getElementById("alqor-kök");
  if (kök) kök.innerHTML = '<p style="padding:16px">Pəncərə bağlandı.</p>';
  const menyu = document.getElementById("alqor-menyu");
  if (menyu) { menyu.innerHTML = ""; menyu.hidden = true; }
}

/** Brauzer skripti hadisəni bura göndərir (pencere.py-dəki `/_alqor/hadise`). */
function brauzerHadisəsi(id, dəyər) {
  const p = T.aktiv;
  if (!p) return { bağlı: true };
  try {
    const n = hadisəniİşlət(p, id, dəyər);
    if (n.bağlı && T.aktiv && T.aktiv !== p) {
      const q = T.aktiv;
      return { html: kökHTML(q), menyu: menyuHTML(q.d.menyular, q.d.reyestr), başlıq: q.d.başlıq };
    }
    if (n.bağlı && T.aktiv === null) return { bağlı: true };
    if (n.html !== undefined && T.aktiv !== p) {     // hadisədə yeni pəncərə açılıb
      const q = T.aktiv;
      return { html: kökHTML(q), menyu: menyuHTML(q.d.menyular, q.d.reyestr), başlıq: q.d.başlıq,
        üslub: q.d.üslub };
    }
    n.üslub = p.d.üslub;
    return n;
  } catch (e) {
    if (e instanceof $.Dayanma) return { bağlı: true };
    return { xəta: xətaMətni(e) };
  }
}

// ── Dialoqlar ───────────────────────────────────────────────────────────

function cavabGötür(növ, mesaj, standart) {
  T.dialoqJurnalı.push([növ, mesaj]);
  if (T.dialoqCavabları.length) return T.dialoqCavabları.shift();
  return standart;
}
const bm = (b, m) => (mətnə(b) + " " + mətnə(m)).trim();
function brauzerMesajı(b, m) { b = mətnə(b); m = mətnə(m); return m ? b + "\n\n" + m : b; }

function dəstəkYox(ad) {
  return () => {
    throw xəta("GirişÇıxışXətası", "`dialoq." + ad + "` brauzerdə dəstəklənmir — fayl " +
      "sistemi yalnız desktop tətbiqində (`alqor işlət`) əlçatandır", "ALQ-R009");
  };
}
function faylDialoqu(ad, növ, standart, mesaj) {
  return (...a) => {
    if (brauzerdir) return dəstəkYox(ad)();
    const c = cavabGötür(növ, mesaj ? mesaj(...a) : "", standart);
    return c;
  };
}

const dialoq = () => new $.Modul("pəncərə.dialoq", {
  "təsdiqlə": DA("təsdiqlə", ["başlıq", "mesaj"], [undefined, ""], (b, m) => {
    if (!brauzerdir) return !!cavabGötür("təsdiqlə", bm(b, m), false);
    T.dialoqJurnalı.push(["təsdiqlə", bm(b, m)]);
    return !!B.confirm(brauzerMesajı(b, m));
  }),
  "xəbərdarlıq": DA("xəbərdarlıq", ["başlıq", "mesaj"], [undefined, ""], (b, m) => {
    if (!brauzerdir) { cavabGötür("xəbərdarlıq", bm(b, m), null); return null; }
    T.dialoqJurnalı.push(["xəbərdarlıq", bm(b, m)]); B.alert(brauzerMesajı(b, m)); return null;
  }),
  "məlumat": DA("məlumat", ["başlıq", "mesaj"], [undefined, ""], (b, m) => {
    if (!brauzerdir) { cavabGötür("məlumat", bm(b, m), null); return null; }
    T.dialoqJurnalı.push(["məlumat", bm(b, m)]); B.alert(brauzerMesajı(b, m)); return null;
  }),
  "xəta": DA("xəta", ["başlıq", "mesaj"], [undefined, ""], (b, m) => {
    if (!brauzerdir) { cavabGötür("xəta", bm(b, m), null); return null; }
    T.dialoqJurnalı.push(["xəta", bm(b, m)]); B.alert(brauzerMesajı(b, m)); return null;
  }),
  "soruş": DA("soruş", ["başlıq", "mesaj", "standart"], [undefined, "", ""], (b, m, s) => {
    if (!brauzerdir) return cavabGötür("soruş", bm(b, m), null);
    T.dialoqJurnalı.push(["soruş", bm(b, m)]);
    const c = B.prompt(brauzerMesajı(b, m), s === null ? "" : mətnə(s));
    return c === null || c === undefined ? null : c;
  }),
  "faylAç": DA("faylAç", ["süzgəclər", "qovluq"], [null, null],
    faylDialoqu("faylAç", "faylAç", null)),
  "faylAçHamısı": DA("faylAçHamısı", ["süzgəclər", "qovluq"], [null, null], (...a) => {
    const c = faylDialoqu("faylAçHamısı", "faylAçHamısı", [])(...a);
    return Array.isArray(c) ? c.slice() : c instanceof Kortej ? c.e.slice() : [];
  }),
  "faylSaxla": DA("faylSaxla", ["standartAd", "süzgəclər", "qovluq"], ["", null, null],
    faylDialoqu("faylSaxla", "faylSaxla", null, ad => ad ? mətnə(ad) : "")),
  "qovluqSeç": DA("qovluqSeç", ["qovluq"], [null], faylDialoqu("qovluqSeç", "qovluqSeç", null)),
  "rəngSeç": DA("rəngSeç", ["standart"], ["#3366cc"], (s) => {
    const st = s ? mətnə(s) : "#3366cc";
    if (!brauzerdir) return cavabGötür("rəngSeç", st, null);
    T.dialoqJurnalı.push(["rəngSeç", st]);
    const c = B.prompt("Rəng (#rrggbb)", st);
    return c ? c : null;
  }),
});

function bildiriş(b, m) {
  T.dialoqJurnalı.push(["bildiriş", bm(b, m)]);
  if (!brauzerdir) return null;
  const q = document.createElement("div");
  q.className = "alqor-bildiriş";
  q.setAttribute("role", "status");
  q.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:200;max-width:320px;" +
    "padding:12px 16px;border-radius:8px;background:#1f2937;color:#fff;" +
    "box-shadow:0 8px 24px rgba(0,0,0,.25);font:14px/1.4 system-ui,sans-serif";
  const s = document.createElement("strong");
  s.textContent = mətnə(b);
  q.appendChild(s);
  if (mətnə(m)) { q.appendChild(document.createElement("br")); q.appendChild(document.createTextNode(mətnə(m))); }
  document.body.appendChild(q);
  setTimeout(() => q.remove(), 4000);
  return null;
}

// ═══════════════════════════════════════════════════════════════════════
//  Sınaq sürücüsü — pencere.Sürücü
// ═══════════════════════════════════════════════════════════════════════

function teqsiz(HTML) {
  const n = [];
  let teqdə = false;
  for (const c of HTML) {
    if (c === "<") { teqdə = true; n.push(" "); }
    else if (c === ">") teqdə = false;
    else if (!teqdə) n.push(c);
  }
  let m = n.join("");
  for (const [a, b] of [["&lt;", "<"], ["&gt;", ">"], ["&quot;", '"'], ["&#39;", "'"], ["&amp;", "&"]])
    m = m.split(a).join(b);
  return m.split(/\s+/).filter(x => x).join(" ");
}
const kiçikLatın = s => $.latınla(s).toLowerCase();
function uyğundur(h, m) {
  if (!m) return false;
  if (h === m) return true;
  return kiçikLatın(h) === kiçikLatın(m);
}
function başlayır(m, h) {
  if (!m || !h) return false;
  for (const [a, b] of [[m, h], [kiçikLatın(m), kiçikLatın(h)]]) {
    const ca = [...a], cb = [...b];
    if (a.startsWith(b) && (ca.length === cb.length || ca[cb.length] === " ")) return true;
  }
  return false;
}
function teqAtributu(teq, ad) {
  const n = ad + '="';
  const i = teq.indexOf(" " + n);
  if (i < 0) return "";
  const baş = i + n.length + 1;
  const son = teq.indexOf('"', baş);
  return son > 0 ? teq.slice(baş, son) : "";
}
function teqiTap(HTML, atribut, açar) {
  const i = HTML.indexOf(atribut + '="' + açar + '"');
  if (i < 0) return "";
  const baş = HTML.lastIndexOf("<", i), son = HTML.indexOf(">", i);
  return baş >= 0 && son > 0 ? HTML.slice(baş, son + 1) : "";
}
function atributTap(HTML, atribut, hədəf) {
  const n = atribut + '="';
  let yer = 0, başlanğıc = null;
  for (;;) {
    const i = HTML.indexOf(n, yer);
    if (i < 0) break;
    const baş = i + n.length, son = HTML.indexOf('"', baş);
    const açar = HTML.slice(baş, son);
    yer = son;
    if (hədəf === null) return açar;
    const tb = HTML.lastIndexOf("<", i), ts = HTML.indexOf(">", son);
    if (tb < 0 || ts < 0) continue;
    const teq = HTML.slice(tb, ts + 1);
    const ad = teq.slice(1).split(" ")[0].split(">")[0];
    const ms = HTML.indexOf("</" + ad + ">", ts);
    const mətn = teqsiz(ms > 0 ? HTML.slice(ts + 1, ms) : "");
    if (uyğundur(hədəf, mətn)) return açar;
    for (const a of ["data-a-ad", "id", "title", "name", "value"])
      if (uyğundur(hədəf, teqAtributu(teq, a))) return açar;
    if (başlanğıc === null && başlayır(mətn, hədəf)) başlanğıc = açar;
  }
  return başlanğıc;
}

function sürücü(p) {
  if (!p.d.açıq) p.d.açıq = true;
  const s = new Yerli("Sürücü", SÜRÜCÜ_C, { p, HTML: "" });
  s.d.HTML = kökHTML(p);
  return s;
}
function sMenyu(s) { return menyuHTML(s.d.p.d.menyular, s.d.p.d.reyestr); }
function açarTap(s, şəkilçi, hədəf) {
  for (const H of [s.d.HTML, sMenyu(s)]) {
    const a = atributTap(H, "data-a-" + şəkilçi, hədəf);
    if (a) return a;
  }
  return null;
}
function sİşlət(s, açar, dəyər) {
  hadisəniİşlət(s.d.p, açar, dəyər);
  s.d.HTML = kökHTML(s.d.p);
}
const nişanMətn = n => n === undefined || n === null ? null : mətnə(n);

const SÜRÜCÜ_C = {
  $mətn: () => "<sürücü>",
  "yenilə": s => { s.d.HTML = kökHTML(s.d.p); return s; },
  "HTML": s => s.d.HTML,
  "səhifə": s => "<!DOCTYPE html>\n<html lang=\"az\"><head><meta charset=\"UTF-8\"><title>" +
    qaç(s.d.p.d.başlıq) + "</title></head><body><main id=\"alqor-kök\">" + s.d.HTML +
    "</main></body></html>",
  "menyu": s => sMenyu(s),
  "başlıq": s => s.d.p.d.başlıq,
  "mətn": s => teqsiz(s.d.HTML),
  "ehtiva": (s, x) => s.d.HTML.includes(mətnə(x)),
  "açıqdır": s => s.d.p.d.açıq,
  "dialoqlar": () => T.dialoqJurnalı.map(d => d.slice()),
  "klik": M("klik", ["nişan", "dəyər"], [null, null], (s, nişan, dəyər) => {
    const hədəf = nişanMətn(nişan);
    let açar = açarTap(s, "klik", hədəf);
    if (açar === null && hədəf !== null) açar = atributTap(sMenyu(s), "data-a-klik", hədəf);
    if (açar !== null && dəyər === null)
      dəyər = teqAtributu(teqiTap(s.d.HTML + sMenyu(s), "data-a-klik", açar), "value") || null;
    if (açar === null) {
      for (const ş of ["deyisdi", "yazildi"]) {
        const a = açarTap(s, ş, hədəf);
        if (a === null) continue;
        const teq = teqiTap(s.d.HTML, "data-a-" + ş, a);
        açar = a;
        if (dəyər === null && (teq.includes('type="checkbox"') || teq.includes('type="radio"')))
          dəyər = !teq.includes(" checked");
        break;
      }
    }
    if (açar === null)
      throw xəta("ArqumentXətası", hədəf ? '"' + hədəf + '" üçün klik idarəedicisi tapılmadı'
        : "klik idarəedicisi yoxdur", "ALQ-R013");
    sİşlət(s, açar, dəyər);
    return s;
  }),
  "yaz": M("yaz", ["nişan", "dəyər"], [undefined, undefined], (s, nişan, dəyər) => {
    const h = mətnə(nişan);
    const açar = açarTap(s, "deyisdi", h) || açarTap(s, "yazildi", h);
    if (açar === null) throw xəta("ArqumentXətası", '"' + h + '" sahəsi tapılmadı', "ALQ-R013");
    sİşlət(s, açar, typeof dəyər === "boolean" ? dəyər : mətnə(dəyər));
    return s;
  }),
  "hadisə": M("hadisə", ["ad", "nişan", "dəyər"], [undefined, null, null], (s, ad, nişan, dəyər) => {
    const a = mətnə(ad);
    if (!Object.prototype.hasOwnProperty.call(HADİSƏLƏR, a))
      throw xəta("ArqumentXətası", "`" + a + "` hadisəsi yoxdur. İcazəli: " +
        Object.keys(HADİSƏLƏR).sort().join(", "), "ALQ-R013");
    const açar = açarTap(s, HADİSƏLƏR[a][1], nişanMətn(nişan));
    if (açar === null) throw xəta("ArqumentXətası", "`" + a + "` idarəedicisi tapılmadı", "ALQ-R013");
    sİşlət(s, açar, dəyər);
    return s;
  }),
  "bağla": s => { bağlaP(s.d.p); return s; },
};

// ═══════════════════════════════════════════════════════════════════════
//  Modul
// ═══════════════════════════════════════════════════════════════════════

const sınaq = () => new $.Modul("pəncərə.sınaq", {
  "aç": D("aç", 1, 1, p => {
    if (!(p instanceof Yerli) || p.c !== PƏNCƏRƏ_C)
      throw xəta("TipXətası", "`pəncərə.sınaq.aç` pəncərə gözləyir, `" + tip(p) + "` gəlib", "ALQ-T001");
    return sürücü(p);
  }),
  "cavablar": D("cavablar", 1, 1, c => { T.dialoqCavabları.push(...siyahıya(c)); return null; }),
  "jurnal": D("jurnal", 0, 0, () => T.dialoqJurnalı.map(d => d.slice())),
  "təmizlə": D("təmizlə", 0, 0, () => { T.dialoqJurnalı.length = 0; T.dialoqCavabları.length = 0; return null; }),
});

let _dialoq = null, _sınaq = null;
$.modulQeyd("pəncərə.dialoq", () => _dialoq || (_dialoq = dialoq()));
$.modulQeyd("pəncərə.sınaq", () => _sınaq || (_sınaq = sınaq()));
$.modulQeyd("pəncərə", () => new $.Modul("pəncərə", {
  "Pəncərə": DA("Pəncərə", ["başlıq", "en", "hündürlük"], ["Alqor", 800n, 600n], yeniPəncərə),
  "menyu": DA("menyu", ["ad", "elementlər"], [undefined, null], (ad, el) =>
    new Yerli("pəncərəMenyusu", MENYU_C, { ad: mətnə(ad),
      elementlər: (el === null ? [] : siyahıya(el)).filter(e => e instanceof Yerli && e.c === ELEMENT_C) })),
  "element": DA("element", ["ad", "qısayol", "klik", "söndürülmüş", "işarələnmiş"],
    [undefined, "", null, false, null], (ad, q, k, s, i) =>
      new Yerli("menyuElementi", ELEMENT_C, { ad: mətnə(ad), qısayol: mətnə(q), klik: k,
        söndürülmüş: !!s, işarələnmiş: i, ayırıcı: false })),
  "ayırıcı": D("ayırıcı", 0, 0, () => new Yerli("menyuElementi", ELEMENT_C,
    { ad: "", qısayol: "", klik: null, söndürülmüş: false, işarələnmiş: null, ayırıcı: true })),
  "bildiriş": DA("bildiriş", ["başlıq", "mesaj"], [undefined, ""], bildiriş),
  "işlət": D("işlət", 0, 0, () => null),
  "dayandır": D("dayandır", 0, 0, () => {
    for (const p of T.pəncərələr) p.d.açıq = false;
    if (brauzerdir) { T.aktiv = null; bağlandıSəhifəsi(); }
    return null;
  }),
  "pəncərələr": D("pəncərələr", 0, 0, () => açıqlar()),
  "aparıcı": D("aparıcı", 0, 0, () => brauzerdir ? "brauzer" : "başsız"),
  "başsızdır": D("başsızdır", 0, 0, () => !brauzerdir),
  "dialoq": $.modul("pəncərə.dialoq"),
  "sınaq": $.modul("pəncərə.sınaq"),
}));

$.UI = { hadisə: brauzerHadisəsi, xətanıGöstər, xətaMətni };
})($);
