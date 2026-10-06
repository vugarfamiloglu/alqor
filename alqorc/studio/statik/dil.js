/*
 * Alqor Studio — Alqor dilinin rəngləndiricisi (tokenləşdirici).
 *
 * Kompilyatorun lekseri ilə eyni qaydalar (sadələşdirilmiş):
 *   • açar sözlər, tip adları, kontekstli sözlər — `/api/klaviatura`-dan
 *   • mətnlər: "…", """…""", x"…" (xam), b"…" (bayt), {…} interpolyasiya
 *   • şərhlər: //, /* … *\/ (iç-içə), /// sənəd şərhi
 *   • ədədlər: 42, 3.14, 1_000, 0xFF, 0b1010, 1.5e3
 *   • JSX: <teq atr="…" atr={ifadə}>uşaqlar</teq>, <Komponent />
 *
 * Nəticə: [başlanğıc, son, sinif] üçlüklərinin siyahısı.
 */
"use strict";

const AlqorDil = (() => {
  let AÇARLAR = new Set();
  let LİTERALLAR = new Set(["doğru", "yanlış", "boş", "sonsuz", "ƏdədDeyil"]);
  let TİPLƏR = new Set();
  let KONTEKSTLİ = new Set();
  let ASCII = {};

  // İfadəni bitirən literallar — bunlardan sonra `<` müqayisədir
  const İFADƏ_BİTİRƏN = new Set(["doğru", "yanlış", "boş", "özü", "üst",
    "sonsuz", "ƏdədDeyil"]);

  const AD_BAŞI = /[\p{L}_]/u;
  const AD_DAVAMI = /[\p{L}\p{N}_]/u;
  const RƏQƏM = /[0-9]/;

  function qur(cədvəl) {
    AÇARLAR = new Set(cədvəl.açarSözlər || []);
    LİTERALLAR = new Set(cədvəl.literallar || [...LİTERALLAR]);
    TİPLƏR = new Set(cədvəl.tiplər || []);
    KONTEKSTLİ = new Set(cədvəl.kontekstli || []);
    ASCII = cədvəl.ascii || {};
  }

  function tokenlər(m) {
    const n = m.length;
    const t = [];
    let i = 0;
    let sonİfadəBitirir = false;   // əvvəlki token ifadəni bitirirmi
    let əvvəlkiNöqtə = false;      // `.`-dan sonra — üzv adı

    function əlavə(baş, son, sinif) {
      if (son > baş) t.push([baş, son, sinif]);
    }

    function şərh(baş) {
      if (m.startsWith("/*", baş)) {
        let d = 0, j = baş;
        while (j < n) {
          if (m.startsWith("/*", j)) { d++; j += 2; }
          else if (m.startsWith("*/", j)) { d--; j += 2; if (d === 0) break; }
          else j++;
        }
        əlavə(baş, j, "şərh");
        return j;
      }
      let j = m.indexOf("\n", baş);
      if (j < 0) j = n;
      əlavə(baş, j, m.startsWith("///", baş) ? "şərh sənəd" : "şərh");
      return j;
    }

    function mətn(baş) {
      let j = baş;
      const xam = m[j] === "x";
      if (m[j] === "x" || m[j] === "b") j++;
      const üçlü = m.startsWith('"""', j);
      j += üçlü ? 3 : 1;
      let parça = baş;
      while (j < n) {
        const c = m[j];
        if (üçlü && m.startsWith('"""', j)) { j += 3; əlavə(parça, j, "mətn"); return j; }
        if (!üçlü && c === '"') { j++; əlavə(parça, j, "mətn"); return j; }
        if (!üçlü && c === "\n") { əlavə(parça, j, "mətn"); return j; }
        if (!xam && c === "\\") {
          əlavə(parça, j, "mətn");
          əlavə(j, Math.min(n, j + 2), "qaçış");
          j += 2; parça = j; continue;
        }
        if (!xam && c === "{") {
          əlavə(parça, j, "mətn");
          əlavə(j, j + 1, "interp");
          j = kod(j + 1, "}");
          if (m[j] === "}") { əlavə(j, j + 1, "interp"); j++; }
          parça = j; continue;
        }
        j++;
      }
      əlavə(parça, n, "mətn");
      return n;
    }

    function ədəd(baş) {
      let j = baş;
      if (m[j] === "0" && /[xXbBoO]/.test(m[j + 1] || "")) {
        j += 2;
        while (j < n && /[0-9a-fA-F_]/.test(m[j])) j++;
      } else {
        while (j < n && /[0-9_]/.test(m[j])) j++;
        if (m[j] === "." && RƏQƏM.test(m[j + 1] || "")) {
          j++;
          while (j < n && /[0-9_]/.test(m[j])) j++;
        }
        if (/[eE]/.test(m[j] || "") && /[0-9+-]/.test(m[j + 1] || "")) {
          j += 2;
          while (j < n && RƏQƏM.test(m[j])) j++;
        }
      }
      əlavə(baş, j, "ədəd");
      return j;
    }

    function ad(baş) {
      let j = baş + 1;
      while (j < n && AD_DAVAMI.test(m[j])) j++;
      const s = m.slice(baş, j);
      let sinif = "ad";
      if (əvvəlkiNöqtə) sinif = "üzv";
      else if (s === "özü" || s === "üst") sinif = "özü";
      else if (LİTERALLAR.has(s)) sinif = "literal";
      else if (AÇARLAR.has(s)) sinif = "açar";
      else if (TİPLƏR.has(s)) sinif = "tip";
      else if (ASCII[s] !== undefined) sinif = "açar ascii";
      else if (KONTEKSTLİ.has(s) && /^\s*$/.test(sətirBaşı(baş))
               && (/^[ \t]+[\p{L}_]/u.test(m.slice(j, j + 3))
                   || /^[ \t]*(\n|$)/.test(m.slice(j, j + 2))
                   || (s === "göstər" && m[j] === "("))) sinif = "kontekst";
      else if (/^\p{Lu}/u.test(s)) sinif = "sinifAdı";
      if ((sinif === "ad" || sinif === "üzv") && m[j] === "(") sinif += " çağırış";
      əlavə(baş, j, sinif);
      sonİfadəBitirir = !(sinif.startsWith("açar") || sinif === "kontekst")
        || İFADƏ_BİTİRƏN.has(s);
      return j;
    }

    function sətirBaşı(baş) {
      const b = m.lastIndexOf("\n", baş - 1) + 1;
      return m.slice(b, baş);
    }

    // ── JSX ──────────────────────────────────────────────────────────
    function jsxTeqAdı(j) {
      const b = j;
      while (j < n && (AD_DAVAMI.test(m[j]) || m[j] === "." || m[j] === "-")) j++;
      return [b, j];
    }

    function jsx(baş) {
      // `<` + ad və ya `<>` (parça)
      let j = baş + 1;
      if (m[j] === ">") {
        əlavə(baş, j + 1, "teq");
        return jsxUşaqlar(j + 1);
      }
      const [ab, as] = jsxTeqAdı(j);
      əlavə(baş, ab, "teq");
      əlavə(ab, as, /^\p{Lu}/u.test(m.slice(ab, as)) ? "teq komp" : "teq ad");
      j = as;
      while (j < n) {
        while (j < n && /\s/.test(m[j])) j++;
        if (m.startsWith("/>", j)) { əlavə(j, j + 2, "teq"); return j + 2; }
        if (m[j] === ">") { əlavə(j, j + 1, "teq"); return jsxUşaqlar(j + 1); }
        if (m[j] === "{") {
          əlavə(j, j + 1, "interp");
          j = kod(j + 1, "}");
          if (m[j] === "}") { əlavə(j, j + 1, "interp"); j++; }
          continue;
        }
        if (AD_BAŞI.test(m[j] || "")) {
          const b = j;
          while (j < n && (AD_DAVAMI.test(m[j]) || m[j] === "-")) j++;
          əlavə(b, j, "atribut");
          continue;
        }
        if (m[j] === "=") { əlavə(j, j + 1, "op"); j++; continue; }
        if (m[j] === '"') {
          let k = m.indexOf('"', j + 1);
          if (k < 0) k = n - 1;
          əlavə(j, k + 1, "mətn");
          j = k + 1; continue;
        }
        if (j >= n) break;
        j++;   // naməlum simvol — keçirik
      }
      return j;
    }

    function jsxUşaqlar(j) {
      let mətnBaşı = j;
      while (j < n) {
        const c = m[j];
        if (c === "<" && m[j + 1] === "/") {
          əlavə(mətnBaşı, j, "jsxMətn");
          let k = m.indexOf(">", j);
          if (k < 0) k = n - 1;
          əlavə(j, j + 2, "teq");
          əlavə(j + 2, k, "teq ad");
          əlavə(k, k + 1, "teq");
          return k + 1;
        }
        if (c === "<" && (AD_BAŞI.test(m[j + 1] || "") || m[j + 1] === ">")) {
          əlavə(mətnBaşı, j, "jsxMətn");
          j = jsx(j);
          mətnBaşı = j; continue;
        }
        if (c === "{") {
          əlavə(mətnBaşı, j, "jsxMətn");
          əlavə(j, j + 1, "interp");
          j = kod(j + 1, "}");
          if (m[j] === "}") { əlavə(j, j + 1, "interp"); j++; }
          mətnBaşı = j; continue;
        }
        j++;
      }
      əlavə(mətnBaşı, n, "jsxMətn");
      return n;
    }

    // ── Kod ──────────────────────────────────────────────────────────
    function kod(j, bitir) {
      let dərinlik = 0;
      while (j < n) {
        const c = m[j];
        if (c === " " || c === "\t" || c === "\r") { j++; continue; }
        if (c === "\n") { j++; continue; }
        if (c === "/" && (m[j + 1] === "/" || m[j + 1] === "*")) { j = şərh(j); continue; }
        if (c === '"' || ((c === "x" || c === "b") && m[j + 1] === '"'
            && !AD_DAVAMI.test(m[j - 1] || ""))) {
          j = mətn(j); sonİfadəBitirir = true; əvvəlkiNöqtə = false; continue;
        }
        if (c === "`") {
          let k = m.indexOf("`", j + 1);
          const sətirSonu = m.indexOf("\n", j);
          if (k < 0 || (sətirSonu >= 0 && sətirSonu < k)) k = j;
          əlavə(j, k + 1, "mətn");
          j = k + 1; sonİfadəBitirir = true; continue;
        }
        if (RƏQƏM.test(c)) {
          j = ədəd(j); sonİfadəBitirir = true; əvvəlkiNöqtə = false; continue;
        }
        if (AD_BAŞI.test(c)) {
          j = ad(j); əvvəlkiNöqtə = false; continue;
        }
        if (c === "<" && !sonİfadəBitirir &&
            (AD_BAŞI.test(m[j + 1] || "") || m[j + 1] === ">")) {
          j = jsx(j); sonİfadəBitirir = true; əvvəlkiNöqtə = false; continue;
        }
        if (bitir === "}" && c === "}" && dərinlik === 0) return j;
        if (c === "{") dərinlik++;
        else if (c === "}") dərinlik--;
        əvvəlkiNöqtə = c === "." || (c === "?" && m[j + 1] === ".");
        if (c === "?" && m[j + 1] === ".") { əlavə(j, j + 2, "op"); j += 2; continue; }
        əlavə(j, j + 1, /[()[\]{},;:]/.test(c) ? "ayırıcı" : "op");
        sonİfadəBitirir = c === ")" || c === "]" || c === "}" || c === "!";
        j++;
      }
      return j;
    }

    kod(0, null);
    return t;
  }

  // Mövqedəki tokenin sinfi (ikili axtarış)
  function sinif(toks, mövqe) {
    let a = 0, b = toks.length - 1;
    while (a <= b) {
      const o = (a + b) >> 1;
      const [s, e] = toks[o];
      if (mövqe < s) b = o - 1;
      else if (mövqe >= e) a = o + 1;
      else return toks[o][2];
    }
    return "";
  }

  function koddur(toks, mövqe) {
    const s = sinif(toks, mövqe);
    return !/mətn|şərh|qaçış|jsxMətn/.test(s);
  }

  return {
    qur, tokenlər, sinif, koddur,
    get ascii() { return ASCII; },
    get açarlar() { return AÇARLAR; },
  };
})();
