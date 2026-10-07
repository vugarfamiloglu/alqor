/*
 * Alqor Studio — əmrlər, menyu sətri, kontekst menyuları, əmr palitrası.
 *
 *   Əmrlər.qeyd("fayl.saxla", { ad, ikon, qısayol: "Ctrl+S", işlə, aktiv })
 *   MenyuSətri.qur(el, [{ ad: "Fayl", hərf: "F", elementlər: ["fayl.saxla", "-", …] }])
 *   KontekstMenyu.göstər(x, y, ["redaktə.kəs", "-", { ad, alt: [...] }])
 *   Palitra.aç(">")      // əmrlər · "" fayllar · ":" sətir · "@" simvollar
 *
 * Menyu elementi: əmr adı (mətn), "-" (ayırıcı) və ya obyekt
 * { ad, ikon, qısayol, işlə, aktiv, seçilib, alt }.
 */
"use strict";

// ══ Əmrlər ═══════════════════════════════════════════════════════════
const Əmrlər = (() => {
  const siyahı = new Map();
  const KOD = { Equal: "=", Minus: "-", Slash: "/", Backquote: "`", Period: ".",
    Comma: ",", BracketLeft: "[", BracketRight: "]", Backslash: "\\", Semicolon: ";",
    Quote: "'", Space: "Space", Enter: "Enter", Escape: "Esc", Delete: "Delete",
    Backspace: "Backspace", Tab: "Tab" };
  const OX = { ArrowUp: "Up", ArrowDown: "Down", ArrowLeft: "Left", ArrowRight: "Right" };

  function açar(h) {
    let k;
    if (/^F\d{1,2}$/.test(h.key)) k = h.key;
    else if (OX[h.key]) k = OX[h.key];
    else if (/^Key[A-Z]$/.test(h.code)) k = h.code.slice(3);
    else if (/^Digit\d$/.test(h.code)) k = h.code.slice(5);
    else if (/^Numpad(Add|Subtract)$/.test(h.code)) k = h.code === "NumpadAdd" ? "=" : "-";
    else k = KOD[h.code] || KOD[h.key];
    if (!k) return null;
    return [(h.ctrlKey || h.metaKey) && "Ctrl", h.altKey && "Alt", h.shiftKey && "Shift", k]
      .filter(Boolean).join("+");
  }

  const göstər = (q) => (q || "").replace(/\bUp\b/g, "↑").replace(/\bDown\b/g, "↓")
    .replace(/\bLeft\b/g, "←").replace(/\bRight\b/g, "→");

  return {
    siyahı,
    qeyd(id, t) { siyahı.set(id, { id, ...t }); return this; },
    al: (id) => siyahı.get(id),
    aktivdir(id) { const ə = siyahı.get(id); return !!ə && (!ə.aktiv || ə.aktiv()); },
    işlət(id, ...a) {
      const ə = siyahı.get(id);
      if (!ə || (ə.aktiv && !ə.aktiv())) return false;
      Promise.resolve().then(() => ə.işlə(...a)).catch((x) => window.xəta?.(x));
      return true;
    },
    /** Klaviatura hadisəsinə uyğun əmr (yoxdursa null). */
    qısayolla(h) {
      const a = açar(h);
      if (!a) return null;
      for (const ə of siyahı.values()) {
        const q = Array.isArray(ə.qısayol) ? ə.qısayol : [ə.qısayol];
        if (q.includes(a) && (!ə.aktiv || ə.aktiv())) return ə.id;
      }
      return null;
    },
    göstər,
  };
})();

// ══ Menyu göstəricisi (açılan, kontekst, alt menyu) ══════════════════
const Menyu = (() => {
  let açıqlar = [];             // [{el, elementlər, seçili}]
  let bağlananda = null;

  function həll(e) {
    if (e === "-") return { ayırıcı: true };
    if (typeof e === "string") {
      const ə = Əmrlər.al(e);
      if (!ə) return null;
      return { ad: ə.ad, ikon: ə.ikon, qısayol: ə.qısayol, seçilib: ə.seçilib,
        aktiv: ə.aktiv, işlə: () => Əmrlər.işlət(e), əmr: e };
    }
    return e;
  }

  function sətir(e, i) {
    if (e.ayırıcı) return '<div class="m-ayırıcı" role="separator"></div>';
    const aktiv = !e.aktiv || e.aktiv();
    const seç = typeof e.seçilib === "function" ? e.seçilib() : e.seçilib;
    const q = Array.isArray(e.qısayol) ? e.qısayol[0] : e.qısayol;
    const ikon = seç ? İkon("işarə") : (e.ikon ? İkon(e.ikon) : '<span class="ikon boş"></span>');
    return `<div class="m-element${aktiv ? "" : " sönük"}${e.alt ? " alt-var" : ""}" role="menuitem" ` +
      `data-i="${i}" aria-disabled="${!aktiv}"${e.əmr ? ` data-emr="${e.əmr}"` : ""}>` +
      `${ikon}<span class="m-ad">${qaçMenyu(e.ad)}</span>` +
      `<span class="m-qısayol">${e.alt ? İkon("ox", 14) : qaçMenyu(Əmrlər.göstər(q))}</span></div>`;
  }

  function qaçMenyu(s) {
    return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function aç(x, y, elementlər, { səviyyə = 0, sağdan = null, onBağla = null } = {}) {
    while (açıqlar.length > səviyyə) açıqlar.pop().el.remove();
    if (səviyyə === 0) bağlananda = onBağla;
    const n = elementlər.map(həll).filter(Boolean)
      .filter((e, i, a) => !(e.ayırıcı && (i === 0 || a[i - 1].ayırıcı || i === a.length - 1)));
    const el = document.createElement("div");
    el.className = "menyu-qutu";
    el.setAttribute("role", "menu");
    el.innerHTML = n.map(sətir).join("");
    document.body.append(el);
    const r = el.getBoundingClientRect();
    const W = innerWidth, H = innerHeight;
    let sol = x, üst = y;
    if (sol + r.width > W - 4) sol = sağdan !== null ? Math.max(4, sağdan - r.width) : Math.max(4, W - r.width - 4);
    if (üst + r.height > H - 4) üst = Math.max(4, H - r.height - 4);
    el.style.left = `${sol}px`;
    el.style.top = `${üst}px`;
    const qeyd = { el, elementlər: n, seçili: -1 };
    açıqlar.push(qeyd);

    el.addEventListener("mousemove", (h) => {
      const s = h.target.closest(".m-element");
      if (!s) return;
      const i = +s.dataset.i;
      if (qeyd.seçili !== i) seç(açıqlar.indexOf(qeyd), i, true);
    });
    el.addEventListener("mousedown", (h) => h.preventDefault());
    el.addEventListener("click", (h) => {
      const s = h.target.closest(".m-element");
      if (s) icra(açıqlar.indexOf(qeyd), +s.dataset.i);
    });
    return el;
  }

  function seç(səviyyə, i, siçan = false) {
    const q = açıqlar[səviyyə];
    if (!q) return;
    q.seçili = i;
    for (const s of q.el.querySelectorAll(".m-element")) s.classList.toggle("seçili", +s.dataset.i === i);
    const e = q.elementlər[i];
    while (açıqlar.length > səviyyə + 1) açıqlar.pop().el.remove();
    if (e?.alt && (siçan || true)) {
      const s = q.el.querySelector(`[data-i="${i}"]`);
      const r = s.getBoundingClientRect();
      const alt = typeof e.alt === "function" ? e.alt() : e.alt;
      aç(r.right - 2, r.top - 4, alt, { səviyyə: səviyyə + 1, sağdan: r.left + 2 });
    }
  }

  function icra(səviyyə, i) {
    const e = açıqlar[səviyyə]?.elementlər[i];
    if (!e || e.ayırıcı || (e.aktiv && !e.aktiv())) return;
    if (e.alt) { seç(səviyyə, i); seç(səviyyə + 1, 0); return; }
    bağla();
    e.işlə?.();
  }

  function bağla() {
    while (açıqlar.length) açıqlar.pop().el.remove();
    const b = bağlananda;
    bağlananda = null;
    b?.();
  }

  function addım(q, i, istiqamət) {
    const n = q.elementlər.length;
    for (let k = 1; k <= n; k++) {
      const j = (i + istiqamət * k + n * 2) % n;
      const e = q.elementlər[j];
      if (!e.ayırıcı && (!e.aktiv || e.aktiv())) return j;
    }
    return i;
  }

  /** Klaviatura — açıq menyu varsa idarə edir və true qaytarır. */
  function düymə(h) {
    if (!açıqlar.length) return false;
    const s = açıqlar.length - 1, q = açıqlar[s];
    const a = h.key;
    if (a === "Escape") {
      if (s > 0) açıqlar.pop().el.remove(); else bağla();
    } else if (a === "ArrowDown") seç(s, addım(q, q.seçili, 1));
    else if (a === "ArrowUp") seç(s, addım(q, q.seçili < 0 ? 0 : q.seçili, -1));
    else if (a === "ArrowRight" && q.elementlər[q.seçili]?.alt) seç(s + 1, 0);
    else if (a === "ArrowLeft" && s > 0) açıqlar.pop().el.remove();
    else if ((a === "ArrowLeft" || a === "ArrowRight") && MenyuSətri.açıqdır()) {
      MenyuSətri.qonşu(a === "ArrowRight" ? 1 : -1);
    } else if (a === "Enter" || a === " ") { if (q.seçili >= 0) icra(s, q.seçili); }
    h.preventDefault();
    h.stopPropagation();
    return true;
  }

  document.addEventListener("mousedown", (h) => {
    if (açıqlar.length && !h.target.closest(".menyu-qutu") && !h.target.closest(".menyu-sətri .m-başlıq")) bağla();
  }, true);
  window.addEventListener("blur", () => bağla());
  window.addEventListener("resize", () => bağla());

  return { aç, bağla, düymə, açıqdır: () => açıqlar.length > 0, seç };
})();

const KontekstMenyu = {
  göstər(x, y, elementlər) { Menyu.aç(x, y, elementlər); },
};

// ══ Menyu sətri ══════════════════════════════════════════════════════
const MenyuSətri = (() => {
  let el = null, menyular = [], açıq = -1;

  function qur(qab, m) {
    el = qab;
    menyular = m;
    el.innerHTML = m.map((x, i) =>
      `<button class="m-başlıq" data-i="${i}" aria-haspopup="true" title="Alt+${x.hərf}">` +
      `${x.ad.replace(new RegExp(`(${x.hərf})`, "iu"), "<u>$1</u>")}</button>`).join("");
    el.addEventListener("mousedown", (h) => {
      const b = h.target.closest(".m-başlıq");
      if (!b) return;
      h.preventDefault();
      if (açıq === +b.dataset.i) Menyu.bağla(); else göstər(+b.dataset.i);
    });
    el.addEventListener("mouseover", (h) => {
      const b = h.target.closest(".m-başlıq");
      if (b && açıq >= 0 && açıq !== +b.dataset.i) göstər(+b.dataset.i);
    });
  }

  function göstər(i, seç = false) {
    const b = el.querySelector(`[data-i="${i}"]`);
    for (const x of el.querySelectorAll(".m-başlıq")) x.classList.toggle("açıq", x === b);
    açıq = i;
    const r = b.getBoundingClientRect();
    Menyu.aç(r.left, r.bottom, menyular[i].elementlər, {
      onBağla: () => {
        açıq = -1;
        for (const x of el.querySelectorAll(".m-başlıq")) x.classList.remove("açıq");
      } });
    if (seç) Menyu.seç(0, 0);
  }

  function hərflə(h) {
    if (!h.altKey || h.ctrlKey || h.metaKey || h.shiftKey) return false;
    const k = /^Key[A-Z]$/.test(h.code) ? h.code.slice(3) : null;
    const i = menyular.findIndex((m) => m.hərf.toUpperCase() === k);
    if (i < 0) return false;
    h.preventDefault();
    göstər(i, true);
    return true;
  }

  return {
    qur, göstər, hərflə,
    açıqdır: () => açıq >= 0,
    qonşu(d) { if (açıq >= 0) göstər((açıq + d + menyular.length) % menyular.length, true); },
  };
})();

// ══ Əmr palitrası ════════════════════════════════════════════════════
const Palitra = (() => {
  let qab = null, giriş = null, siyahı = null, maddələr = [], seçili = 0, rejim = ">";
  const mənbələr = { fayllar: () => [], simvollar: async () => [], sətrəKeç: () => {} };

  function qur() {
    qab = document.createElement("div");
    qab.className = "palitra";
    qab.hidden = true;
    qab.innerHTML = '<div class="palitra-qutu" role="dialog" aria-label="Əmr palitrası">' +
      '<input class="palitra-giriş" spellcheck="false" autocomplete="off">' +
      '<div class="palitra-siyahı" role="listbox"></div>' +
      '<div class="palitra-ipucu">› əmrlər · fayl adı · : sətir · @ simvol</div></div>';
    document.body.append(qab);
    giriş = qab.querySelector("input");
    siyahı = qab.querySelector(".palitra-siyahı");
    giriş.addEventListener("input", yenilə);
    giriş.addEventListener("keydown", (h) => {
      if (h.key === "ArrowDown" || h.key === "ArrowUp") {
        h.preventDefault();
        seçili = (seçili + (h.key === "ArrowDown" ? 1 : -1) + maddələr.length) % Math.max(1, maddələr.length);
        çək();
      } else if (h.key === "Enter") { h.preventDefault(); icra(seçili); }
      else if (h.key === "Escape") { h.preventDefault(); bağla(); }
    });
    qab.addEventListener("mousedown", (h) => { if (h.target === qab) bağla(); });
    siyahı.addEventListener("click", (h) => {
      const s = h.target.closest("[data-i]");
      if (s) icra(+s.dataset.i);
    });
  }

  function uyğun(sorğu, mətn) {
    if (!sorğu) return 1;
    const s = sorğu.toLocaleLowerCase("az"), m = mətn.toLocaleLowerCase("az");
    if (m.includes(s)) return 2 + (m.startsWith(s) ? 1 : 0);
    let i = 0;
    for (const c of m) if (c === s[i]) i++;
    return i === s.length ? 1 : 0;
  }

  async function yenilə() {
    const m = giriş.value;
    let r = ">";
    if (m.startsWith(">")) r = ">";
    else if (m.startsWith(":")) r = ":";
    else if (m.startsWith("@")) r = "@";
    else r = "";
    rejim = r;
    const sorğu = (r ? m.slice(1) : m).trim();
    let n = [];
    if (r === ">") {
      n = [...Əmrlər.siyahı.values()].filter((ə) => !ə.gizli && (!ə.aktiv || ə.aktiv()))
        .map((ə) => ({ ad: ə.ad, ikon: ə.ikon, əlavə: Əmrlər.göstər(Array.isArray(ə.qısayol) ? ə.qısayol[0] : ə.qısayol),
          işlə: () => Əmrlər.işlət(ə.id), xal: uyğun(sorğu, ə.ad + " " + (ə.qrup || "")) }));
    } else if (r === ":") {
      const s = parseInt(sorğu, 10);
      n = [{ ad: s ? `${s}-ci sətrə keç` : "Sətir nömrəsini yazın", ikon: "keç-sətir",
        işlə: () => s && mənbələr.sətrəKeç(s), xal: 1 }];
    } else if (r === "@") {
      const simvollar = await mənbələr.simvollar();
      if (giriş.value !== m) return;
      n = simvollar.map((x) => ({ ad: x.ad, ikon: x.ikon || "struktur", əlavə: x.əlavə || "",
        işlə: x.işlə, xal: uyğun(sorğu, x.ad) }));
    } else {
      n = mənbələr.fayllar().map((y) => ({ ad: y.split("/").pop(), əlavə: y, ikon: "fayl",
        işlə: () => mənbələr.faylıAç(y), xal: uyğun(sorğu, y) }));
    }
    maddələr = n.filter((x) => x.xal > 0).sort((a, b) => b.xal - a.xal).slice(0, 80);
    seçili = 0;
    çək();
  }

  function çək() {
    siyahı.innerHTML = maddələr.length ? maddələr.map((x, i) =>
      `<div class="palitra-element${i === seçili ? " seçili" : ""}" data-i="${i}" role="option">` +
      `${İkon(x.ikon || "növbəti")}<span>${qaç(x.ad)}</span><span class="sönük">${qaç(x.əlavə || "")}</span></div>`).join("")
      : '<div class="palitra-boş">Heç nə tapılmadı</div>';
    siyahı.querySelector(".seçili")?.scrollIntoView({ block: "nearest" });
  }

  function icra(i) {
    const x = maddələr[i];
    if (!x) return;
    bağla();
    x.işlə?.();
  }

  function aç(prefiks = ">") {
    if (!qab) qur();
    qab.hidden = false;
    giriş.value = prefiks;
    giriş.focus();
    giriş.setSelectionRange(prefiks.length, prefiks.length);
    yenilə();
  }

  function bağla() {
    if (!qab || qab.hidden) return;
    qab.hidden = true;
    if (typeof R !== "undefined") R.fokus();
  }

  return { aç, bağla, mənbələr, açıqdır: () => qab && !qab.hidden };
})();
