// Alqor icraçısı — WebAssembly paketi üçün JS qatı (asılılıqsız).
//
//   import { yüklə } from "./alqor.js";
//   const alqor = await yüklə("./alqor.wasm");
//   const n = alqor.işlət('yaz("Salam")', ["giriş sətri"]);
//   // n = { stdout: "Salam\n", stderr: "", kod: 0 }

const kodla = new TextEncoder();
const aç = new TextDecoder();

/** `.wasm` faylını (URL, ArrayBuffer və ya Uint8Array) yükləyir. */
export async function yüklə(mənbə) {
  let baytlar;
  if (typeof mənbə === "string" || mənbə instanceof URL) {
    if (typeof fetch === "function" && !String(mənbə).startsWith("file:")) {
      baytlar = await (await fetch(mənbə)).arrayBuffer();
    } else {
      const fs = await import("node:fs/promises");
      baytlar = await fs.readFile(mənbə instanceof URL ? mənbə : new URL(mənbə, import.meta.url));
    }
  } else {
    baytlar = mənbə;
  }
  const modul = await WebAssembly.compile(baytlar);
  const saat = typeof performance !== "undefined" ? performance : { now: () => Date.now() };
  const idxal = {
    alqor: {
      alqor_indi_ms: () => Date.now(),
      alqor_monoton_ms: () => saat.now(),
      alqor_qursaq_deq: () => -new Date().getTimezoneOffset(),
    },
  };
  // Hər icra təzə nüsxədə: yaddaş sızmır, əvvəlki proqramın vəziyyəti qalmır
  const nüsxə = () => new WebAssembly.Instance(modul, idxal).exports;

  function yaz(e, mətn) {
    const b = kodla.encode(mətn);
    const p = e.alqor_ayir(b.length);
    new Uint8Array(e.memory.buffer, p, b.length).set(b);
    return [p, b.length];
  }
  function oxu(e, p) {
    const n = e.alqor_netice_uzunlugu();
    return aç.decode(new Uint8Array(e.memory.buffer, p, n));
  }

  return {
    /** Mənbəni icra edir: { stdout, stderr, kod } */
    işlət(kod, giriş = []) {
      const e = nüsxə();
      try {
        const [m, mn] = yaz(e, kod);
        const [g, gn] = yaz(e, Array.isArray(giriş) ? giriş.map((s) => s + "\n").join("") : String(giriş));
        return JSON.parse(oxu(e, e.alqor_islet(m, mn, g, gn)));
      } catch (x) {
        // Brauzerin öz stek həddi (çox dərin rekursiya) və ya daxili xəta
        const stek = x instanceof RangeError;
        return {
          stdout: "",
          stderr: stek
            ? "✖ ALQ-R010  StekDaşmaXətası: brauzerin stek həddi aşıldı — sonsuz rekursiya?\n"
            : "✖ ALQ-R000  DaxiliXəta: " + String(x && x.message || x) + "\n",
          kod: 1,
        };
      }
    },
    versiya() {
      const e = nüsxə();
      return oxu(e, e.alqor_versiya());
    },
  };
}
