/*
 * Alqor Studio — yerləşdirilən (dockable) və üzən (floating) panellər.
 *
 * Hər panel üç zonadan birində (sol, sağ, alt) nişan kimi durur və ya
 * üzən pəncərədir. Panelin nişanını sürükləyib başqa zonaya və ya
 * redaktorun üstünə (→ üzən pəncərə) buraxmaq olar; nişanın kontekst
 * menyusu da eyni şeyi edir. Düzülüş brauzerdə yadda saxlanılır.
 *
 *   Dok.qeyd("cixis", { başlıq: "Çıxış", ikon: "terminal", el, yer: "alt" })
 *   Dok.aç("cixis")      Dok.gizlət("cixis")      Dok.köçür("cixis", "sağ")
 *   Dok.on("göstərildi", (id) => …)   // "gizləndi", "köçdü"
 */
"use strict";

const Dok = (() => {
  const ZONALAR = ["sol", "sağ", "alt"];
  const panellər = new Map();         // id → {id, başlıq, ikon, el, yer, sıra, görünür, üzən}
  const vəz = { aktiv: {}, açıq: { sol: true, sağ: true, alt: true } };
  const dinləyicilər = {};
  let zIndeks = 40;
  let qurulub = false;

  const zona = (z) => document.querySelector(`.dok[data-dok="${z}"]`);
  const yay = (ad, ...a) => (dinləyicilər[ad] || []).forEach((f) => f(...a));

  function saxla() {
    const p = {};
    for (const x of panellər.values()) {
      p[x.id] = { yer: x.yer, sıra: x.sıra, görünür: x.görünür, üzən: x.üzən };
    }
    try { localStorage.setItem("alqor-studio:düzülüş", JSON.stringify({ p, ...vəz })); } catch (_) { /* */ }
  }

  function bərpa() {
    let d = null;
    try { d = JSON.parse(localStorage.getItem("alqor-studio:düzülüş")); } catch (_) { /* */ }
    if (!d) return;
    for (const [id, x] of Object.entries(d.p || {})) {
      const p = panellər.get(id);
      if (!p) continue;
      if (ZONALAR.includes(x.yer) || x.yer === "üzən") p.yer = x.yer;
      if (typeof x.sıra === "number") p.sıra = x.sıra;
      if (typeof x.görünür === "boolean") p.görünür = x.görünür;
      if (x.üzən) p.üzən = x.üzən;
    }
    Object.assign(vəz.aktiv, d.aktiv || {});
    Object.assign(vəz.açıq, d.açıq || {});
  }

  function zonadakılar(z) {
    return [...panellər.values()].filter((p) => p.yer === z && p.görünür)
      .sort((a, b) => a.sıra - b.sıra);
  }

  // ── Çəkmə ────────────────────────────────────────────────────────
  function çək() {
    for (const z of ZONALAR) {
      const el = zona(z);
      const ps = zonadakılar(z);
      if (!ps.some((p) => p.id === vəz.aktiv[z])) vəz.aktiv[z] = ps[0]?.id;
      const görünür = ps.length > 0 && vəz.açıq[z];
      el.hidden = !görünür;
      const bölücü = document.querySelector(`.bölücü[data-bolucu="${{ sol: "yan", sağ: "sag", alt: "alt" }[z]}"]`);
      if (bölücü) bölücü.hidden = !görünür;
      el.classList.toggle("boş", ps.length === 0);
      const nişanlar = el.querySelector(".dok-nişanlar");
      nişanlar.innerHTML = ps.map((p) =>
        `<button class="dok-nişan${p.id === vəz.aktiv[z] ? " aktiv" : ""}" data-panel="${p.id}" ` +
        `draggable="true" role="tab" title="${p.başlıq} — sürükləyib başqa yerə qoymaq olar">` +
        `${İkon(p.ikon, 14)}<span class="dn-ad">${p.başlıq}</span>${p.say ? `<span class="say">${p.say}</span>` : ""}</button>`).join("") +
        '<span class="boşluq"></span>' +
        `<button class="dok-düymə" data-dok-menyu="${z}" title="Panel seçimləri">⋯</button>` +
        `<button class="dok-düymə" data-dok-gizlət="${z}" title="Paneli gizlət">${İkon("gizlət", 14)}</button>`;
      const gövdə = el.querySelector(".dok-gövdə");
      for (const p of ps) {
        if (p.el.parentElement !== gövdə) gövdə.append(p.el);
        p.el.hidden = p.id !== vəz.aktiv[z];
      }
    }
    // Üzən pəncərələr
    const qab = document.getElementById("uzenler");
    for (const p of panellər.values()) {
      let w = qab.querySelector(`.üzən[data-panel-uzen="${p.id}"]`);
      if (p.yer !== "üzən" || !p.görünür) { w?.remove(); continue; }
      if (!w) w = üzənQur(p);
      const gövdə = w.querySelector(".üzən-gövdə");
      if (p.el.parentElement !== gövdə) gövdə.append(p.el);
      p.el.hidden = false;
    }
    // Gizli panellər görünməz yerdə saxlanılır (DOM-da qalsın)
    const anbar = document.getElementById("panel-anbari");
    for (const p of panellər.values()) {
      if (!p.görünür) { if (p.el.parentElement !== anbar) anbar.append(p.el); p.el.hidden = true; }
    }
    fəaliyyətiÇək();
  }

  function fəaliyyətiÇək() {
    const f = document.getElementById("fealiyyet");
    if (!f) return;
    const sıra = [...panellər.values()].filter((p) => !p.zolaqsız)
      .sort((a, b) => (a.zolaq ?? 50) - (b.zolaq ?? 50));
    f.innerHTML = sıra.map((p) =>
      `<button class="f-düymə${açıqdır(p.id) ? " aktiv" : ""}" data-fealiyyet="${p.id}" ` +
      `title="${p.başlıq}${p.qısayol ? ` (${Əmrlər.göstər(p.qısayol)})` : ""}">${İkon(p.ikon, 22)}` +
      `${p.say ? `<span class="f-say">${p.say}</span>` : ""}</button>`).join("");
  }

  function üzənQur(p) {
    const w = document.createElement("div");
    w.className = "üzən";
    w.dataset.panelUzen = p.id;
    const ü = p.üzən || {};
    const en = Math.min(ü.w || 420, innerWidth - 40), hün = Math.min(ü.h || 320, innerHeight - 80);
    w.style.left = `${Math.max(0, Math.min(ü.x ?? (innerWidth - en) / 2, innerWidth - 120))}px`;
    w.style.top = `${Math.max(0, Math.min(ü.y ?? 120, innerHeight - 60))}px`;
    w.style.width = `${en}px`;
    w.style.height = `${hün}px`;
    w.style.zIndex = ++zIndeks;
    w.innerHTML = `<div class="üzən-başlıq" draggable="false">${İkon(p.ikon, 14)}<b>${p.başlıq}</b>` +
      '<span class="boşluq"></span>' +
      `<button class="dok-düymə" data-yerlesdir="${p.id}" title="Yenidən yerləşdir">${İkon("yerləşdir", 14)}</button>` +
      `<button class="dok-düymə" data-uzen-bagla="${p.id}" title="Bağla">${İkon("bağla", 14)}</button></div>` +
      '<div class="üzən-gövdə"></div>';
    document.getElementById("uzenler").append(w);
    w.addEventListener("pointerdown", () => { w.style.zIndex = ++zIndeks; });
    const başlıq = w.querySelector(".üzən-başlıq");
    başlıq.addEventListener("pointerdown", (h) => {
      if (h.target.closest("button")) return;
      h.preventDefault();
      başlıq.setPointerCapture(h.pointerId);
      const x0 = h.clientX - w.offsetLeft, y0 = h.clientY - w.offsetTop;
      document.body.classList.add("sürüklənir");
      const hərəkət = (e) => {
        w.style.left = `${Math.max(-w.offsetWidth + 80, Math.min(innerWidth - 80, e.clientX - x0))}px`;
        w.style.top = `${Math.max(0, Math.min(innerHeight - 30, e.clientY - y0))}px`;
      };
      başlıq.addEventListener("pointermove", hərəkət);
      başlıq.addEventListener("pointerup", () => {
        başlıq.removeEventListener("pointermove", hərəkət);
        document.body.classList.remove("sürüklənir");
        yaddaYaz(p, w);
      }, { once: true });
    });
    başlıq.addEventListener("dblclick", () => köçür(p.id, p.sonZona || "sağ"));
    new ResizeObserver(() => yaddaYaz(p, w)).observe(w);
    return w;
  }

  function yaddaYaz(p, w) {
    if (!w.isConnected) return;
    p.üzən = { x: w.offsetLeft, y: w.offsetTop, w: w.offsetWidth, h: w.offsetHeight };
    saxla();
  }

  // ── Əməllər ──────────────────────────────────────────────────────
  function açıqdır(id) {
    const p = panellər.get(id);
    if (!p || !p.görünür) return false;
    if (p.yer === "üzən") return true;
    return vəz.açıq[p.yer] && vəz.aktiv[p.yer] === id;
  }

  function aç(id, { fokus = false } = {}) {
    const p = panellər.get(id);
    if (!p) return;
    const əvvəl = p.görünür;
    p.görünür = true;
    if (p.yer === "üzən") {
      çək();
      const w = document.querySelector(`.üzən[data-panel-uzen="${id}"]`);
      if (w) w.style.zIndex = ++zIndeks;
    } else {
      vəz.aktiv[p.yer] = id;
      vəz.açıq[p.yer] = true;
      çək();
    }
    saxla();
    if (!əvvəl) yay("göstərildi", id);
    yay("aktiv", id);
    if (fokus) p.el.querySelector("input, [tabindex], button")?.focus();
  }

  function gizlət(id) {
    const p = panellər.get(id);
    if (!p || !p.görünür) return;
    p.görünür = false;
    çək();
    saxla();
    yay("gizləndi", id);
  }

  function dəyiş(id) {
    if (açıqdır(id)) {
      const p = panellər.get(id);
      if (p.yer === "üzən" || p.bağlanır) gizlət(id);
      else { vəz.açıq[p.yer] = false; çək(); saxla(); }
    } else aç(id, { fokus: true });
  }

  function köçür(id, yer, indeks = null) {
    const p = panellər.get(id);
    if (!p) return;
    if (p.yer !== "üzən") p.sonZona = p.yer;
    p.yer = yer;
    p.görünür = true;
    if (yer !== "üzən") {
      const ps = zonadakılar(yer).filter((x) => x !== p);
      ps.splice(indeks ?? ps.length, 0, p);
      ps.forEach((x, i) => { x.sıra = i; });
      vəz.aktiv[yer] = id;
      vəz.açıq[yer] = true;
    }
    çək();
    saxla();
    yay("köçdü", id, yer);
  }

  function üzəndir(id, x = null, y = null) {
    const p = panellər.get(id);
    if (!p) return;
    if (x !== null) p.üzən = { ...(p.üzən || {}), x: Math.max(0, x - 60), y: Math.max(0, y - 12) };
    köçür(id, "üzən");
  }

  function zonanıDəyiş(z, aç = !vəz.açıq[z]) {
    vəz.açıq[z] = aç;
    if (aç && !zonadakılar(z).length) {
      // Boş zona — standart panelini geri gətir
      for (const p of panellər.values()) if (p.əsasYer === z && !p.görünür) { p.görünür = true; p.yer = z; }
    }
    çək();
    saxla();
  }

  function sıfırla() {
    for (const p of panellər.values()) {
      p.yer = p.əsasYer;
      p.sıra = p.əsasSıra;
      p.görünür = p.əsasGörünür;
      p.üzən = null;
    }
    vəz.açıq = { sol: true, sağ: true, alt: true };
    vəz.aktiv = {};
    document.getElementById("uzenler").innerHTML = "";
    çək();
    saxla();
    for (const p of panellər.values()) yay("köçdü", p.id, p.yer);
  }

  function panelMenyusu(id) {
    const p = panellər.get(id);
    const yerlər = [["sol", "Sola yerləşdir", "yan-panel"], ["sağ", "Sağa yerləşdir", "sağ-panel"],
      ["alt", "Aşağıya yerləşdir", "alt-panel"]];
    return [
      ...yerlər.map(([z, ad, ikon]) => ({ ad, ikon, aktiv: () => p.yer !== z, işlə: () => köçür(id, z) })),
      { ad: "Üzən pəncərə et", ikon: "üzən", aktiv: () => p.yer !== "üzən", işlə: () => üzəndir(id) },
      "-",
      { ad: `"${p.başlıq}" panelini bağla`, ikon: "bağla", işlə: () => gizlət(id) },
      { ad: "Düzülüşü sıfırla", ikon: "sıfırla", işlə: sıfırla },
    ];
  }

  // ── Hadisələr ────────────────────────────────────────────────────
  function hadisələriQur() {
    document.addEventListener("click", (h) => {
      const n = h.target.closest(".dok-nişan");
      if (n) { aç(n.dataset.panel); return; }
      const g = h.target.closest("[data-dok-gizlət]");
      if (g) { zonanıDəyiş(g.dataset.dokGizlət, false); return; }
      const m = h.target.closest("[data-dok-menyu]");
      if (m) {
        const z = m.dataset.dokMenyu;
        const r = m.getBoundingClientRect();
        const aktiv = vəz.aktiv[z];
        KontekstMenyu.göstər(r.left, r.bottom, [
          ...[...panellər.values()].filter((p) => !p.görünür).map((p) => ({
            ad: `${p.başlıq} panelini aç`, ikon: p.ikon, işlə: () => köçür(p.id, z) })),
          "-",
          ...(aktiv ? panelMenyusu(aktiv) : []),
        ]);
        return;
      }
      const y = h.target.closest("[data-yerlesdir]");
      if (y) { const p = panellər.get(y.dataset.yerlesdir); köçür(p.id, p.sonZona || p.əsasYer || "sağ"); return; }
      const b = h.target.closest("[data-uzen-bagla]");
      if (b) { gizlət(b.dataset.uzenBagla); return; }
      const f = h.target.closest("[data-fealiyyet]");
      if (f) dəyiş(f.dataset.fealiyyet);
    });
    document.addEventListener("contextmenu", (h) => {
      const n = h.target.closest(".dok-nişan, .üzən-başlıq, [data-fealiyyet]");
      if (!n) return;
      h.preventDefault();
      const id = n.dataset.panel || n.dataset.fealiyyet || n.parentElement.dataset.panelUzen;
      KontekstMenyu.göstər(h.clientX, h.clientY, panelMenyusu(id));
    });

    // Sürüklə-burax: nişan → zona və ya üzən
    let sürüklənən = null, düşdü = false;
    document.addEventListener("dragstart", (h) => {
      const n = h.target.closest?.(".dok-nişan");
      if (!n) return;
      sürüklənən = n.dataset.panel;
      düşdü = false;
      h.dataTransfer.setData("application/x-alqor-panel", sürüklənən);
      h.dataTransfer.effectAllowed = "move";
      document.body.classList.add("panel-sürüklə");
    });
    document.addEventListener("dragover", (h) => {
      if (!sürüklənən) return;
      const z = h.target.closest?.(".dok, .dok-hədəf");
      for (const x of document.querySelectorAll(".dok.üstündə, .dok-hədəf.üstündə")) if (x !== z) x.classList.remove("üstündə");
      if (z) { z.classList.add("üstündə"); h.preventDefault(); h.dataTransfer.dropEffect = "move"; }
      else if (h.target.closest?.(".mərkəz")) { h.preventDefault(); h.dataTransfer.dropEffect = "move"; }
    });
    document.addEventListener("drop", (h) => {
      if (!sürüklənən) return;
      const z = h.target.closest?.(".dok, .dok-hədəf");
      const id = sürüklənən;
      if (z) {
        h.preventDefault();
        düşdü = true;
        const yer = z.dataset.dok || z.dataset.hedefDok;
        let indeks = null;
        const n = h.target.closest(".dok-nişan");
        if (n && n.dataset.panel !== id) {
          indeks = zonadakılar(yer).findIndex((p) => p.id === n.dataset.panel);
          const r = n.getBoundingClientRect();
          if (h.clientX > r.left + r.width / 2) indeks++;
        }
        köçür(id, yer, indeks);
      } else if (h.target.closest?.(".mərkəz")) {
        h.preventDefault();
        düşdü = true;
        üzəndir(id, h.clientX, h.clientY);
      }
    });
    document.addEventListener("dragend", () => {
      document.body.classList.remove("panel-sürüklə");
      for (const x of document.querySelectorAll(".üstündə")) x.classList.remove("üstündə");
      sürüklənən = null;
    });
  }

  return {
    ZONALAR,
    qeyd(id, t) {
      const p = { id, sıra: panellər.size, görünür: true, ...t };
      p.əsasYer = p.yer; p.əsasSıra = p.sıra; p.əsasGörünür = p.görünür;
      panellər.set(id, p);
      return this;
    },
    qur() {
      if (!qurulub) hadisələriQur();
      qurulub = true;
      bərpa();
      çək();
    },
    aç, gizlət, dəyiş, köçür, üzəndir, açıqdır, sıfırla, zonanıDəyiş,
    zonaAçıqdır: (z) => vəz.açıq[z] && zonadakılar(z).length > 0,
    panel: (id) => panellər.get(id),
    panellər: () => [...panellər.values()],
    say(id, n) {
      const p = panellər.get(id);
      if (!p || p.say === n) return;
      p.say = n || "";
      for (const b of document.querySelectorAll(`[data-panel="${id}"], [data-fealiyyet="${id}"]`)) {
        let s = b.querySelector(".say, .f-say");
        if (!n) { s?.remove(); continue; }
        if (!s) { s = document.createElement("span"); s.className = b.dataset.panel ? "say" : "f-say"; b.append(s); }
        s.textContent = n;
      }
    },
    panelMenyusu,
    on(ad, f) { (dinləyicilər[ad] ||= []).push(f); },
  };
})();
