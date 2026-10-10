// ═══════════════════════════════════════════════════════════════════════
//  `vidjet` modulu üçün Python semantikası köməkçiləri
//
//  `vidjet_cevir.py` vidjet.py / vidjet_elave.py funksiyalarını JS-ə
//  çevirir; çevrilmiş kod Python əməliyyatlarını bu `$...` köməkçiləri ilə
//  ifadə edir (doğruluq, `==`, `%`, dilim, metodlar, f-mətn formatı).
// ═══════════════════════════════════════════════════════════════════════

const { Lüğət, Dəst, Kortej, Element, Nümunə, Bayt } = $;

class $PyXəta extends Error {
  constructor(tip) { super(tip); this.tip = tip; }
}
function $pyXəta(tip) { return new $PyXəta(tip); }
function $alqorXəta(tip, mesaj, yer, kod) { return $.xəta(tip, mesaj, kod || null); }
function $xətaUyğun(e, tip) { return e instanceof $PyXəta && e.tip === tip; }

const $mətnə = x => $.mətnə(x);
const $böyüyə = s => $.böyüyə(s);
const $KICIK = $.KICIK;

function $ədədi(x) { return typeof x === "bigint" || typeof x === "number" || typeof x === "boolean"; }
function $tamə(x) { return typeof x === "boolean" ? (x ? 1n : 0n) : x; }

// ── Doğruluq və məntiq ───────────────────────────────────────────────────

function $t(x) {
  if (x === null || x === undefined || x === false) return false;
  if (x === true) return true;
  switch (typeof x) {
    case "bigint": return x !== 0n;
    case "number": return x !== 0;
    case "string": return x.length > 0;
    case "function": return true;
  }
  if (Array.isArray(x)) return x.length > 0;
  if (x instanceof Kortej) return x.e.length > 0;
  if (x instanceof Lüğət || x instanceof Dəst || x instanceof Set || x instanceof Map) return x.size > 0;
  if (x instanceof Element) return x.uşaqlar.length > 0;
  return true;
}
function $or(a, b) { return $t(a) ? a : b(); }
function $and(a, b) { return $t(a) ? b() : a; }

// ── Mətnə çevirmə ────────────────────────────────────────────────────────

function $str(x) {
  if (typeof x === "string") return x;
  if (x === null || x === undefined) return "None";
  if (x === true) return "True";
  if (x === false) return "False";
  if (typeof x === "bigint") return x.toString();
  if (typeof x === "number") return $.onluqRepr(x);
  return $.mətnə(x);
}
function $repr(x) {
  if (typeof x === "string") return "'" + x.replace(/\\/g, "\\\\").replace(/'/g, "\\'") + "'";
  return $str(x);
}
function $fmt(x, spec) {
  if (!spec) return $str(x);
  const r = $.pyFormat(typeof x === "boolean" ? (x ? 1n : 0n) : x, spec);
  if (r === null) throw $pyXəta("ValueError");
  return r;
}

// ── Ədədlər ──────────────────────────────────────────────────────────────

function $int(x) {
  if (typeof x === "boolean") return x ? 1n : 0n;
  if (typeof x === "bigint") return x;
  if (typeof x === "number") {
    if (!isFinite(x)) throw $pyXəta("ValueError");
    return BigInt(Math.trunc(x));
  }
  if (typeof x === "string") {
    const s = x.trim().replace(/_/g, "");
    if (/^[+-]?\d+$/.test(s)) return BigInt(s);
  }
  throw $pyXəta("ValueError");
}
function $float(x) {
  if (typeof x === "number") return x;
  if (typeof x === "bigint") return Number(x);
  if (typeof x === "boolean") return x ? 1 : 0;
  if (typeof x === "string") {
    const s = x.trim().replace(/_/g, "").toLowerCase();
    if (/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/.test(s)) return parseFloat(s);
    if (/^[+-]?(inf|infinity)$/.test(s)) return s[0] === "-" ? -Infinity : Infinity;
    if (/^[+-]?nan$/.test(s)) return NaN;
  }
  throw $pyXəta("ValueError");
}
function $abs(x) {
  x = $tamə(x);
  if (typeof x === "bigint") return x < 0n ? -x : x;
  return Math.abs(x);
}
function $round(x, n) {
  if (n === undefined) return BigInt(Math.round(Number(x)));
  const k = 10 ** Number(n);
  return Math.round(Number(x) * k) / k;
}
function $ədədOp(a, b, tam, onluq) {
  a = $tamə(a); b = $tamə(b);
  if (typeof a === "bigint" && typeof b === "bigint") return tam(a, b);
  return onluq(Number(a), Number(b));
}
function $add(a, b) {
  if (typeof a === "string" && typeof b === "string") return a + b;
  if (Array.isArray(a) && Array.isArray(b)) return a.concat(b);
  if ($ədədi(a) && $ədədi(b)) return $ədədOp(a, b, (x, y) => x + y, (x, y) => x + y);
  throw $pyXəta("TypeError");
}
function $sub(a, b) { return $ədədOp(a, b, (x, y) => x - y, (x, y) => x - y); }
function $mul(a, b) {
  if (typeof a === "string" && (typeof b === "bigint")) return b > 0n ? a.repeat(Number(b)) : "";
  if (Array.isArray(a) && typeof b === "bigint") {
    const r = []; for (let i = 0n; i < b; i++) r.push(...a); return r;
  }
  return $ədədOp(a, b, (x, y) => x * y, (x, y) => x * y);
}
function $div(a, b) {
  if (Number($tamə(b)) === 0) throw $pyXəta("ZeroDivisionError");
  return Number($tamə(a)) / Number($tamə(b));
}
function $fdiv(a, b) {
  return $ədədOp(a, b, (x, y) => {
    if (y === 0n) throw $pyXəta("ZeroDivisionError");
    const q = x / y;
    return (x % y !== 0n && ((x < 0n) !== (y < 0n))) ? q - 1n : q;
  }, (x, y) => Math.floor(x / y));
}
function $mod(a, b) {
  return $ədədOp(a, b, (x, y) => {
    if (y === 0n) throw $pyXəta("ZeroDivisionError");
    const r = x % y;
    return (r !== 0n && ((r < 0n) !== (y < 0n))) ? r + y : r;
  }, (x, y) => x - y * Math.floor(x / y));
}
function $pow(a, b) {
  return $ədədOp(a, b, (x, y) => y >= 0n ? x ** y : Number(x) ** Number(y), (x, y) => x ** y);
}
function $neg(x) { x = $tamə(x); return -x; }

// ── Müqayisə ─────────────────────────────────────────────────────────────

function $eq(a, b) {
  if (a === b) return true;
  if ($ədədi(a) && $ədədi(b)) return Number($tamə(a)) === Number($tamə(b));
  if (a === null || b === null || a === undefined || b === undefined) return false;
  if (Array.isArray(a) && Array.isArray(b))
    return a.length === b.length && a.every((x, i) => $eq(x, b[i]));
  if (typeof a === "object" && typeof b === "object") return $.eq(a, b);
  return false;
}
function $müq(a, b) {
  if ($ədədi(a) && $ədədi(b)) {
    a = $tamə(a); b = $tamə(b);
    return a < b ? -1 : a > b ? 1 : 0;
  }
  if (typeof a === "string" && typeof b === "string") return a < b ? -1 : a > b ? 1 : 0;
  if (Array.isArray(a) && Array.isArray(b)) {
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
      if (!$eq(a[i], b[i])) return $müq(a[i], b[i]);
    }
    return a.length - b.length;
  }
  throw $pyXəta("TypeError");
}
const $lt = (a, b) => $müq(a, b) < 0;
const $gt = (a, b) => $müq(a, b) > 0;
const $le = (a, b) => $müq(a, b) <= 0;
const $ge = (a, b) => $müq(a, b) >= 0;
function $max(...a) { let m = a[0]; for (const x of a.slice(1)) if ($gt(x, m)) m = x; return m; }
function $min(...a) { let m = a[0]; for (const x of a.slice(1)) if ($lt(x, m)) m = x; return m; }

function $in(a, b) {
  if (typeof b === "string") return b.includes(a);
  if (Array.isArray(b)) return b.some(x => $eq(x, a));
  if (b instanceof Kortej) return b.e.some(x => $eq(x, a));
  if (b instanceof Set) return b.has(a);
  if (b instanceof Lüğət || b instanceof Dəst) return b.var(a);
  if (b instanceof Element) return b.uşaqlar.some(x => $eq(x, a));
  throw $pyXəta("TypeError");
}

// ── Kolleksiyalar ────────────────────────────────────────────────────────

function $it(x) {
  if (Array.isArray(x)) return x;
  if (typeof x === "string") return [...x];
  if (x instanceof Kortej) return x.e;
  if (x instanceof Lüğət) return [...x.açarlar()];
  if (x instanceof Set || x instanceof Dəst) return [...x];
  if (x instanceof Element) return x.uşaqlar;
  if (x !== null && x !== undefined && typeof x[Symbol.iterator] === "function") return [...x];
  throw $pyXəta("TypeError");
}
function $len(x) {
  if (typeof x === "string") return BigInt([...x].length);
  if (x instanceof Lüğət || x instanceof Dəst || x instanceof Set) return BigInt(x.size);
  return BigInt($it(x).length);
}
function $range(a, b, c) {
  if (b === undefined) { b = a; a = 0n; }
  c = c === undefined ? 1n : c;
  const r = [];
  if (c > 0n) for (let i = a; i < b; i += c) r.push(i);
  else for (let i = a; i > b; i += c) r.push(i);
  return r;
}
function $enumerate(x, başla) {
  return $it(x).map((d, i) => [BigInt(i) + başla, d]);
}
const $list = x => x === undefined ? [] : [...$it(x)];
const $set = x => new Set(x === undefined ? [] : $it(x));
const $any = x => $it(x).some($t);
const $all = x => $it(x).every($t);
function $sum(x, s) { let r = s === undefined ? 0n : s; for (const d of $it(x)) r = $add(r, d); return r; }
const $sorted = x => $list(x).sort($müq);
const $reversed = x => $list(x).reverse();
const $chr = n => String.fromCodePoint(Number(n));
function $callable(x) { return typeof x === "function" || $.çağırılandır(x); }

function $dict(cütlər) {
  const l = new Lüğət();
  for (const [k, v] of cütlər) l.qoy(k, v);
  return l;
}
function $dictƏt(x) { return x === undefined ? new Lüğət() : $dict($items(x)); }
function $dictFromkeys(x) { return $dict($it(x).map(k => [k, null])); }
function $items(x) {
  if (x instanceof Lüğət) return [...x.cütlər()].map(c => [c[0], c[1]]);
  if (x instanceof Nümunə) return [...x.f].map(c => [c[0], c[1]]);
  return $it(x).map(c => $it(c));
}

function $isinstance(x, tiplər) {
  for (const t of tiplər) {
    switch (t) {
      case "int": if (typeof x === "bigint" || typeof x === "boolean") return true; break;
      case "float": if (typeof x === "number") return true; break;
      case "str": if (typeof x === "string") return true; break;
      case "bool": if (typeof x === "boolean") return true; break;
      case "list": if (Array.isArray(x)) return true; break;
      case "tuple": if (Array.isArray(x) || x instanceof Kortej) return true; break;
      case "dict": if (x instanceof Lüğət) return true; break;
      case "set": if (x instanceof Set || x instanceof Dəst) return true; break;
      case "Element": if (x instanceof Element) return true; break;
      case "Nümunə": if (x instanceof Nümunə) return true; break;
      case "bytes": if (x instanceof Bayt) return true; break;
    }
  }
  return false;
}

function $indeks(n, i) {
  let k = Number($tamə(i));
  if (k < 0) k += n;
  if (k < 0 || k >= n) throw $pyXəta("IndexError");
  return k;
}
function $ind(o, i) {
  if (Array.isArray(o)) return o[$indeks(o.length, i)];
  if (typeof o === "string") { const s = [...o]; return s[$indeks(s.length, i)]; }
  if (o instanceof Kortej) return o.e[$indeks(o.e.length, i)];
  if (o instanceof Lüğət) {
    const d = o.al(i);
    if (d === $.YOX) throw $pyXəta("KeyError");
    return d;
  }
  if (o instanceof Element) return o.uşaqlar[$indeks(o.uşaqlar.length, i)];
  throw $pyXəta("TypeError");
}
function $setInd(o, i, v) {
  if (Array.isArray(o)) { o[$indeks(o.length, i)] = v; return; }
  if (o instanceof Lüğət) { o.qoy(i, v); return; }
  throw $pyXəta("TypeError");
}
function $dilim(o, a, b) {
  const s = typeof o === "string" ? [...o] : $it(o);
  const n = s.length;
  const h = (x, st) => {
    if (x === null || x === undefined) return st;
    let k = Number($tamə(x));
    if (k < 0) k = Math.max(0, k + n);
    return Math.min(k, n);
  };
  const r = s.slice(h(a, 0), h(b, n));
  return typeof o === "string" ? r.join("") : r;
}
function $açıl(x, n) {
  const a = $list(x);
  if (a.length !== n) throw $pyXəta("ValueError");
  return a;
}

function $attr(o, a) {
  if (o instanceof Element) {
    if (a === "ad" || a === "atributlar" || a === "uşaqlar" || a === "komponent") return o[a];
  }
  if (o instanceof Nümunə) {
    if (a === "sahələr") return $dict($items(o));
    if (a === "sinif") return o.s;
  }
  throw $pyXəta("AttributeError");
}

// ── Metodlar ─────────────────────────────────────────────────────────────

const $BOŞLUQ = /^[\s\x1c-\x1f\x85]+|[\s\x1c-\x1f\x85]+$/g;

function $m(o, a, ...x) {
  if (typeof o === "string") {
    switch (a) {
      case "join": return $it(x[0]).map(s => {
        if (typeof s !== "string") throw $pyXəta("TypeError");
        return s; }).join(o);
      case "split":
        if (x[0] === undefined || x[0] === null) return o.split(/\s+/).filter(s => s);
        return o.split(x[0]);
      case "strip":
        if (x[0] !== undefined) { let s = o; while (s && x[0].includes(s[0])) s = s.slice(1);
          while (s && x[0].includes(s[s.length - 1])) s = s.slice(0, -1); return s; }
        return o.replace($BOŞLUQ, "");
      case "lstrip":
        if (x[0] !== undefined) { let s = o; while (s && x[0].includes(s[0])) s = s.slice(1); return s; }
        return o.replace(/^\s+/, "");
      case "rstrip": return o.replace(/\s+$/, "");
      case "lower": return o.toLowerCase();
      case "upper": return o.toUpperCase();
      case "replace": return o.split(x[0]).join(x[1]);
      case "startswith": return (Array.isArray(x[0]) ? x[0] : [x[0]]).some(p => o.startsWith(p));
      case "endswith": return (Array.isArray(x[0]) ? x[0] : [x[0]]).some(p => o.endsWith(p));
      case "count": return BigInt(o.split(x[0]).length - 1);
      case "find": return BigInt(o.indexOf(x[0]));
      case "isalnum": return o.length > 0 && /^[\p{L}\p{N}]+$/u.test(o);
      case "isdigit": return o.length > 0 && /^\p{Nd}+$/u.test(o);
      case "isalpha": return o.length > 0 && /^\p{L}+$/u.test(o);
      case "islower": return /\p{Ll}/u.test(o) && !/\p{Lu}/u.test(o);
      case "isupper": return /\p{Lu}/u.test(o) && !/\p{Ll}/u.test(o);
    }
  } else if (Array.isArray(o)) {
    switch (a) {
      case "append": o.push(x[0]); return null;
      case "extend": o.push(...$it(x[0])); return null;
      case "insert": o.splice(Number(x[0]), 0, x[1]); return null;
      case "pop": return x.length ? o.splice($indeks(o.length, x[0]), 1)[0] : o.pop();
      case "copy": return o.slice();
      case "count": return BigInt(o.filter(d => $eq(d, x[0])).length);
      case "index": { const i = o.findIndex(d => $eq(d, x[0]));
        if (i < 0) throw $pyXəta("ValueError"); return BigInt(i); }
    }
  } else if (o instanceof Lüğət) {
    switch (a) {
      case "items": return $items(o);
      case "keys": return [...o.açarlar()];
      case "values": return [...o.dəyərlər()];
      case "get": { const d = o.al(x[0]); return d === $.YOX ? (x[1] === undefined ? null : x[1]) : d; }
      case "setdefault": if (!o.var(x[0])) o.qoy(x[0], x[1] === undefined ? null : x[1]); return o.al(x[0]);
      case "update": for (const [k, v] of $items(x[0])) o.qoy(k, v); return null;
      case "copy": return $dict($items(o));
      case "pop": { const d = o.sil(x[0]);
        if (d === $.YOX) { if (x.length > 1) return x[1]; throw $pyXəta("KeyError"); } return d; }
    }
  } else if (o instanceof Set) {
    switch (a) {
      case "add": o.add(x[0]); return null;
      case "update": for (const d of $it(x[0])) o.add(d); return null;
    }
  } else if (typeof o === "number") {
    if (a === "is_integer") return Number.isInteger(o);
  }
  throw $pyXəta("AttributeError");
}

// ── Element və digər ─────────────────────────────────────────────────────

function $El(ad, atr, uşaqlar) {
  return new Element(ad, atr instanceof Lüğət ? atr : $dict(atr ? $items(atr) : []),
    uşaqlar ? $list(uşaqlar) : []);
}

const $math = {
  cos: x => Math.cos(Number(x)), sin: x => Math.sin(Number(x)),
  sqrt: x => Math.sqrt(Number(x)), floor: x => BigInt(Math.floor(Number(x))),
  ceil: x => BigInt(Math.ceil(Number(x))), atan2: (a, b) => Math.atan2(Number(a), Number(b)),
};

/** `calendar.Calendar(0).monthdayscalendar(il, ay)` — həftələr (B.e-dən). */
function $ayHəftələri(il, ay) {
  const i = Number(il), a = Number(ay);
  const ilkGün = (new Date(Date.UTC(i, a - 1, 1)).getUTCDay() + 6) % 7;
  const günSayı = new Date(Date.UTC(i, a, 0)).getUTCDate();
  const həftələr = [];
  let h = new Array(ilkGün).fill(0n);
  for (let g = 1; g <= günSayı; g++) {
    h.push(BigInt(g));
    if (h.length === 7) { həftələr.push(h); h = []; }
  }
  if (h.length) { while (h.length < 7) h.push(0n); həftələr.push(h); }
  return həftələr;
}

// ── `işarəliMətn` — senedci.md_html + html.oxu qarşılığı ────────────────

function $htmlQaç(m) {
  return m.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}
function $sətirdaxili(m) {
  return $htmlQaç(m).replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}
/** senedci.md_html(mətn, əsl_başlıqlar=True) */
function $mdHTML(mətn) {
  const s = [];
  const sətirlər = mətn.split("\n");
  let abzas = [], siyahı = false;
  const abzasıBağla = () => {
    if (abzas.length) { s.push("<p>" + $sətirdaxili(abzas.join(" ")) + "</p>"); abzas = []; }
  };
  const siyahınıBağla = () => { if (siyahı) { s.push("</ul>"); siyahı = false; } };
  for (let i = 0; i < sətirlər.length; i++) {
    const sətir = sətirlər[i];
    if (sətir.startsWith("```")) {
      abzasıBağla(); siyahınıBağla();
      const kod = [];
      i++;
      while (i < sətirlər.length && !sətirlər[i].startsWith("```")) kod.push(sətirlər[i++]);
      s.push("<pre><code>" + $htmlQaç(kod.join("\n")) + "</code></pre>");
    } else if (sətir.startsWith("#")) {
      abzasıBağla(); siyahınıBağla();
      const qalan = sətir.replace(/^#+/, "");
      const h = Math.min(6, sətir.length - qalan.length);
      s.push("<h" + h + ">" + $sətirdaxili($m(qalan, "strip")) + "</h" + h + ">");
    } else if ($m($m(sətir, "lstrip"), "startswith", ["- ", "* "])) {
      abzasıBağla();
      if (!siyahı) { s.push("<ul>"); siyahı = true; }
      s.push("<li>" + $sətirdaxili($m(sətir, "lstrip").slice(2)) + "</li>");
    } else if (!$m(sətir, "strip")) {
      abzasıBağla(); siyahınıBağla();
    } else {
      siyahınıBağla();
      abzas.push($m(sətir, "strip"));
    }
  }
  abzasıBağla(); siyahınıBağla();
  return s.join("\n");
}
/** md_html çıxışı (atributsuz teqlər) → Element uşaqları — html.oxu kimi. */
function $markdown(mətn) {
  const html = $mdHTML(mətn);
  const kök = new Element("#", new Lüğət(), []);
  const yığın = [kök];
  const açıl = t => t.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'").replace(/&amp;/g, "&");
  const re = /<(\/?)([a-z0-9]+)>/g;
  let son = 0, t;
  while ((t = re.exec(html)) !== null) {
    if (t.index > son) yığın[yığın.length - 1].uşaqlar.push(açıl(html.slice(son, t.index)));
    if (t[1]) {
      for (let i = yığın.length - 1; i > 0; i--)
        if (yığın[i].ad === t[2]) { yığın.length = i; break; }
    } else {
      const e = new Element(t[2], new Lüğət(), []);
      yığın[yığın.length - 1].uşaqlar.push(e);
      yığın.push(e);
    }
    son = re.lastIndex;
  }
  if (son < html.length) yığın[yığın.length - 1].uşaqlar.push(açıl(html.slice(son)));
  return kök.uşaqlar;
}
function işarəliMətn(icraçı, mətn = "") {
  return _E("div", $dict([["class", P + "markdown"]]), $markdown(_m(mətn, icraçı)));
}

// ── Modulun qeydiyyatı ───────────────────────────────────────────────────

/** Alqor çağırışı (mövqeli + adlı) → Python funksiyası; `üslub:` də. */
function $sarğı(ad, f, parametrlər) {
  const say = parametrlər.length + 1;
  return $.ad(function (...args) {
    let adlı = null;
    if (args.length && args[args.length - 1] instanceof $.Adlı) adlı = args.pop().o;
    if (args.length > say)
      throw $.xəta("ArqumentXətası", "`" + ad + "` 0–" + say + " arqument gözləyir, " +
        args.length + " verilib", "ALQ-T003");
    const d = args.slice();
    let üslub = args.length === say ? d.pop() : null;
    while (d.length < parametrlər.length) d.push(undefined);
    if (adlı) {
      for (const k of Object.keys(adlı)) {
        if (k === "üslub") { üslub = adlı[k]; continue; }
        const i = parametrlər.indexOf(k);
        if (i < 0)
          throw $.xəta("ArqumentXətası", "`" + ad + "` naməlum adlı arqument: " + k, "ALQ-T004");
        d[i] = adlı[k];
      }
    }
    const e = f(null, ...d);
    if (üslub === null || üslub === undefined || !(e instanceof Element)) return e;
    const [iç, çöl] = üslub_css(üslub, null);
    let hədəf = e;
    if (!$in(e.ad, FORM_TEQLƏRİ)) {
      const idarə = _əsas_idarə(e);
      if (idarə !== null && idarə !== undefined) hədəf = idarə;
    }
    _stil_əlavə(hədəf, iç);
    _stil_əlavə(e, çöl);
    return e;
  }, ad, "daxili");
}

function $standartAd(ad) {
  const t = [...ad].filter(c => $KICIK.includes(c) || $m(c, "isalnum") || c === "_").join("");
  return t || "element";
}
function $kataloqTap(ad) { return $KATALOQ.find(m => m["ad"] === ad); }

function $vidjetQeyd() {
  const üzvlər = {};
  for (const [ad, f, parametrlər] of $VİDJETLƏR) üzvlər[ad] = $sarğı(ad, f, parametrlər);
  const D = $.D;
  üzvlər["kataloq"] = D("kataloq", 0, 1, k => {
    k = k === undefined || k === null ? null : _m(k, null);
    if (k && !$KATEQORİYALAR.includes(k))
      throw $.xəta("ArqumentXətası", "`" + k + "` kateqoriyası yoxdur. İcazəli: " +
        $KATEQORİYALAR.join(", "), "ALQ-R013");
    return $KATALOQ.filter(m => !k || m["kateqoriya"] === k).map(m =>
      $dict(Object.entries(m).map(([a, d]) => [a, Array.isArray(d) ? d.slice() : d])));
  });
  üzvlər["kateqoriyalar"] = D("kateqoriyalar", 0, 0, () => $KATEQORİYALAR.slice());
  üzvlər["skelet"] = D("skelet", 1, 2, (ad, dəyişən) => {
    const a = _m(ad, null), m = $kataloqTap(a);
    if (!m) {
      const yaxın = $KATALOQ.map(x => x["ad"]).filter(x => a && x.includes(a));
      const kömək = yaxın.length ? " Oxşarlar: " + yaxın.slice(0, 5).join(", ") : "";
      throw $.xəta("ArqumentXətası", "`" + a + "` vidjeti yoxdur." + kömək, "ALQ-R013");
    }
    const d = _m(dəyişən === undefined ? "" : dəyişən, null) || $standartAd(a);
    const h = [];
    if (m["vəziyyət"]) h.push(m["vəziyyət"].split("{ad}").join(d));
    if (m["skelet"]) h.push(m["skelet"].split("{ad}").join(d));
    return h.join("\n\n");
  });
  üzvlər["nümunə"] = D("nümunə", 1, 2, (ad, dəyişən) => {
    const a = _m(ad, null), m = $kataloqTap(a);
    if (!m) throw $.xəta("ArqumentXətası", "`" + a + "` vidjeti yoxdur", "ALQ-R013");
    const d = _m(dəyişən === undefined ? "" : dəyişən, null) || $standartAd(a);
    return m["nümunə"].split("{ad}").join(d);
  });
  üzvlər["üslub"] = D("üslub", 0, 0, () => $ÜSLUB);
  üzvlər["üslublar"] = D("üslublar", 0, 0, () => $El("style", null, [$ÜSLUB]));
  üzvlər["səhifə"] = $sarğıSadə("səhifə", ["başlıq", "məzmun", "dil", "əlavəÜslub"],
    (başlıq = "Alqor", məzmun = null, dil = "az", əlavəÜslub = null) => {
      const baş = [
        $El("meta", $dict([["charset", "UTF-8"]])),
        $El("meta", $dict([["name", "viewport"], ["content", "width=device-width,initial-scale=1"]])),
        $El("title", null, [_m(başlıq, null, "Alqor")]),
        $El("style", null, [$ƏSAS_ÜSLUB + $ÜSLUB]),
      ];
      if (əlavəÜslub !== null) baş.push($El("style", null, [_m(əlavəÜslub, null)]));
      return $El("html", $dict([["lang", _m(dil, null, "az")]]), [
        $El("head", null, baş), $El("body", $dict([["class", P + "gövdə"]]), _uşaqlar(məzmun))]);
    });
  $.modulQeyd("vidjet", () => new $.Modul("vidjet", üzvlər));
}

/** Adlı arqumentli sadə funksiya (üslubsuz). */
function $sarğıSadə(ad, parametrlər, f) {
  return $.ad(function (...args) {
    let adlı = null;
    if (args.length && args[args.length - 1] instanceof $.Adlı) adlı = args.pop().o;
    const d = args.slice();
    while (d.length < parametrlər.length) d.push(undefined);
    if (adlı) for (const k of Object.keys(adlı)) {
      const i = parametrlər.indexOf(k);
      if (i < 0) throw $.xəta("ArqumentXətası", "`" + ad + "` naməlum adlı arqument: " + k, "ALQ-T004");
      d[i] = adlı[k];
    }
    return f(...d);
  }, ad, "daxili");
}
