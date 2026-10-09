/*
 * Alqor Studio — tətbiq: layihə, nişanlar, palet, icra, diaqnostika,
 * önbaxış. Server ilə əlaqə `/api/*` (nişan başlığı ilə).
 */
"use strict";

// ══ Server ilə əlaqə ═════════════════════════════════════════════════
const API = (() => {
  const url = new URL(location.href);
  let nişan = url.searchParams.get("t");
  try {
    if (nişan) sessionStorage.setItem("alqor-nişan", nişan);
    else nişan = sessionStorage.getItem("alqor-nişan");
  } catch (_) { /* yaddaş bağlıdır */ }
  if (url.searchParams.has("t")) {
    url.searchParams.delete("t");
    history.replaceState(null, "", url.pathname + url.search);
  }

  async function sorğu(üsul, yol, gövdə) {
    const c = await fetch(yol, {
      method: üsul,
      headers: { "X-Alqor-Token": nişan || "", "Content-Type": "application/json" },
      body: gövdə === undefined ? undefined : JSON.stringify(gövdə),
    });
    let d = {};
    try { d = await c.json(); } catch (_) { /* boş cavab */ }
    if (!c.ok) {
      const x = new Error(d.xəta || `HTTP ${c.status}`);
      x.kod = c.status;
      throw x;
    }
    return d;
  }
  return {
    get nişan() { return nişan; },
    al: (yol) => sorğu("GET", yol),
    göndər: (yol, gövdə = {}) => sorğu("POST", yol, gövdə),
  };
})();

// ══ Köməkçilər ═══════════════════════════════════════════════════════
const $ = (s, k = document) => k.querySelector(s);
const $$ = (s, k = document) => [...k.querySelectorAll(s)];
const qaç = (s) => String(s).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function yaddaş(açar, dəyər) {
  try {
    if (dəyər === undefined) return JSON.parse(localStorage.getItem("alqor-studio:" + açar));
    localStorage.setItem("alqor-studio:" + açar, JSON.stringify(dəyər));
  } catch (_) { return null; }
  return null;
}

function bildir(mətn, növ = "", müddət = 3600) {
  const b = document.createElement("div");
  b.className = "bildiriş " + növ;
  b.textContent = mətn;
  $("#bildirisler").append(b);
  setTimeout(() => b.remove(), müddət);
  $("#st-mesaj").textContent = mətn.length > 90 ? mətn.slice(0, 90) + "…" : mətn;
}

function xəta(x) { bildir(x.message || String(x), "xəta", 6000); }

function dialoq(başlıq, { mətn = "", standart = "", giriş = true, tamam = "Tamam" } = {}) {
  const d = $("#dialoq");
  $("#dialoq-basliq").textContent = başlıq;
  $("#dialoq-metn").textContent = mətn;
  $("#dialoq-metn").hidden = !mətn;
  const g = $("#dialoq-giris");
  g.hidden = !giriş;
  g.value = standart;
  $("#dialoq-tamam").textContent = tamam;
  return new Promise((həll) => {
    d.addEventListener("close", () => {
      həll(d.returnValue === "tamam" ? (giriş ? g.value.trim() : true) : null);
    }, { once: true });
    d.returnValue = "";
    g.onkeydown = (h) => {
      if (h.key === "Enter") { h.preventDefault(); d.close("tamam"); }
    };
    d.showModal();
    if (giriş) { g.focus(); g.select(); }
  });
}

// ══ Vəziyyət ═════════════════════════════════════════════════════════
const S = {
  məlumat: null,
  ağac: null,
  tablar: [],          // {yol, saxlanmış, v (redaktor vəziyyəti), diaq}
  aktiv: null,
  kataloq: null,
  seçiliQovluq: "",
  iş: null,            // {id, axın, debaq}
  önbaxışAçıq: false,
  nöqtələr: {},        // yol → [sətir] (dayanma nöqtələri)
  dbq: null,           // debaqda dayanma: {yığın, kadr, sahələr}
  dizayn: false,       // vizual dizayner açıqdır
  dzSeçili: null,      // seçilmiş düyünün yolu (JSON)
};

const R = new Redaktor($("#redaktor"));

// ══ Başlanğıc ════════════════════════════════════════════════════════
async function başla() {
  temaQur(yaddaş("tema") || (matchMedia("(prefers-color-scheme: light)").matches ? "işıqlı" : "qaranlıq"));
  ölçüləriBərpaEt();
  try {
    const [m, k, kat] = await Promise.all([
      API.al("/api/melumat"), API.al("/api/klaviatura"), API.al("/api/kataloq")]);
    S.məlumat = m;
    AlqorDil.qur(k);
    R.kompozisiya = k.kompozisiya;
    R.blokAçanlar = new Set((k.blokAçanlar || []).map((s) => s.split(" ")[0]));
    S.kataloq = kat;
    $("#layihe-adi").textContent = `— ${m.ad}`;
    $("#layihe-adi").title = m.kök;
    document.title = `${m.ad} — Alqor Studio`;
    $("#st-rejim").textContent = `tip: ${m.tipRejimi}`;
    hərfPaneliQur(k.hərflər);
    şablonlarıQur(m.şablonlar);
    paletiQur();
    if (!m.formatlayıcı) $("#dym-formatla").title = "Formatlayıcı (alqorfmt) hələ yoxdur";
  } catch (x) {
    document.body.innerHTML = `<p style="padding:24px">Studio serverinə qoşulmaq olmadı: ${qaç(x.message)}.<br>` +
      "Ünvanı `python alqorc.py studio` çap etdiyi kimi (nişanla) açın.</p>";
    return;
  }
  ayarlarıBərpaEt();
  R.çək();
  await ağacıYenilə();
  const açıqlar = yaddaş("tablar") || [];
  for (const yol of açıqlar) await faylıAç(yol, false).catch(() => {});
  const aktiv = yaddaş("aktiv");
  // `.alq` faylına iki klik — Studio həmin faylla açılır
  const ilk = new URLSearchParams(location.search).get("fayl");
  if (ilk && bütünFayllar().includes(ilk)) await faylıAç(ilk).catch(() => {});
  else if (aktiv && S.tablar.some((t) => t.yol === aktiv)) tabaKeç(aktiv);
  else if (S.tablar.length) tabaKeç(S.tablar[0].yol);
  xoşGəldin();
  setInterval(() => API.göndər("/api/nebz").catch(() => {}), 5000);
  API.göndər("/api/nebz").catch(() => {});
  window.addEventListener("pagehide", () => {
    fetch("/api/bagla", { method: "POST", keepalive: true,
      headers: { "X-Alqor-Token": API.nişan, "Content-Type": "application/json" }, body: "{}" });
  });
  window.addEventListener("beforeunload", (h) => {
    if (S.tablar.some(çirklidir)) { h.preventDefault(); h.returnValue = ""; }
  });
}

// ══ Tema, ölçülər, ayarlar ═══════════════════════════════════════════
function temaQur(t) {
  document.documentElement.dataset.tema = t;
  yaddaş("tema", t);
  if (S.kataloq) miniatürləriÇək();
  const ç = $("#onbaxis-cercive");
  if (ç && sonÖnbaxışÜnvanı && S.önbaxışAçıq) ç.src = önbaxışÜnvanı(sonÖnbaxışÜnvanı, true);
}

function ölçüləriBərpaEt() {
  const ö = yaddaş("ölçülər") || {};
  for (const [a, d] of Object.entries(ö)) document.documentElement.style.setProperty(a, d);
}

function ayarlarıBərpaEt() {
  const a = yaddaş("ayarlar") || {};
  if (a.ascii !== undefined) $("#ayar-ascii").checked = a.ascii;
  if (a.tərkib !== undefined) $("#ayar-terkib").checked = a.tərkib;
  R.ayarlar.ascii = $("#ayar-ascii").checked;
  R.ayarlar.tərkib = $("#ayar-terkib").checked;
}

function ayarlarıSaxla() {
  R.ayarlar.ascii = $("#ayar-ascii").checked;
  R.ayarlar.tərkib = $("#ayar-terkib").checked;
  yaddaş("ayarlar", { ascii: R.ayarlar.ascii, tərkib: R.ayarlar.tərkib });
}

function bölücüləriQur() {
  const xəritə = {
    yan: { dəyişən: "--yan-en", ox: "x", min: 160, işarə: 1 },
    sag: { dəyişən: "--sag-en", ox: "x", min: 220, işarə: -1 },
    alt: { dəyişən: "--alt-hündürlük", ox: "y", min: 60, işarə: -1 },
  };
  for (const b of $$(".bölücü")) {
    const m = xəritə[b.dataset.bolucu];
    b.addEventListener("pointerdown", (h) => {
      h.preventDefault();
      b.setPointerCapture(h.pointerId);
      b.classList.add("sürüklənir");
      document.body.classList.add("sürüklənir");
      const başla = m.ox === "x" ? h.clientX : h.clientY;
      const indiki = parseFloat(getComputedStyle(document.documentElement)
        .getPropertyValue(m.dəyişən)) || 200;
      const hərəkət = (e) => {
        const f = ((m.ox === "x" ? e.clientX : e.clientY) - başla) * m.işarə;
        const d = Math.max(m.min, indiki + f);
        document.documentElement.style.setProperty(m.dəyişən, `${d}px`);
      };
      const bit = () => {
        b.removeEventListener("pointermove", hərəkət);
        b.classList.remove("sürüklənir");
        document.body.classList.remove("sürüklənir");
        const ö = yaddaş("ölçülər") || {};
        ö[m.dəyişən] = getComputedStyle(document.documentElement).getPropertyValue(m.dəyişən).trim();
        yaddaş("ölçülər", ö);
      };
      b.addEventListener("pointermove", hərəkət);
      b.addEventListener("pointerup", bit, { once: true });
    });
  }
}

function hərfPaneliQur(hərflər) {
  const p = $("#herf-paneli");
  p.innerHTML = hərflər.map((h) => `<button type="button" data-herf="${h}">${h}</button>`).join("");
  p.addEventListener("mousedown", (h) => h.preventDefault());   // fokus redaktorda qalsın
  p.addEventListener("click", (h) => {
    const d = h.target.closest("[data-herf]");
    if (d && S.aktiv) R.daxilEt(d.dataset.herf);
  });
}

// ══ Fayl ağacı ═══════════════════════════════════════════════════════
async function ağacıYenilə() {
  try { S.ağac = await API.al("/api/agac"); } catch (x) { xəta(x); return; }
  const açıq = new Set(yaddaş("açıqQovluqlar") || []);
  const qur = (düyün) => {
    const u = düyün.uşaqlar.map((e) => {
      if (e.növ === "qovluq") {
        const a = açıq.has(e.yol);
        return `<li><div class="düyün qovluq${S.seçiliQovluq === e.yol ? " seçili" : ""}" data-yol="${qaç(e.yol)}" data-nov="qovluq" role="treeitem" aria-expanded="${a}">` +
          `<span class="işarə">${a ? "▾" : "▸"}</span><span class="ad">${qaç(e.ad)}</span>` +
          `<span class="əməllər"><button data-emel="adlandir" title="Adını dəyiş">✎</button>` +
          `<button data-emel="sil" title="Sil">✕</button></span></div>` +
          (a ? qur(e) : "") + "</li>";
      }
      const alqor = /\.(alqor|alq)$/.test(e.ad);
      return `<li><div class="düyün fayl${alqor ? " alqor" : ""}${S.aktiv === e.yol ? " seçili" : ""}" data-yol="${qaç(e.yol)}" data-nov="fayl" role="treeitem">` +
        `<span class="işarə">${alqor ? "◆" : "·"}</span><span class="ad">${qaç(e.ad)}</span>` +
        `<span class="əməllər"><button data-emel="adlandir" title="Adını dəyiş">✎</button>` +
        `<button data-emel="sil" title="Sil">✕</button></span></div></li>`;
    }).join("");
    return `<ul>${u}</ul>`;
  };
  $("#agac").innerHTML = S.ağac.uşaqlar.length ? qur(S.ağac)
    : '<p class="ipucu-mətni">Qovluq boşdur. Yeni fayl yaradın və ya xoş gəldin ekranından şablon seçin.</p>';
  xoşGəldin();
}

function bütünFayllar(düyün = S.ağac, n = []) {
  if (!düyün) return n;
  for (const e of düyün.uşaqlar) {
    if (e.növ === "qovluq") bütünFayllar(e, n); else n.push(e.yol);
  }
  return n;
}

$("#agac").addEventListener("click", async (h) => {
  const d = h.target.closest(".düyün");
  if (!d) return;
  const yol = d.dataset.yol;
  const əməl = h.target.closest("[data-emel]")?.dataset.emel;
  if (əməl === "adlandir") return adınıDəyiş(yol);
  if (əməl === "sil") return faylıSil(yol, d.dataset.nov);
  if (d.dataset.nov === "qovluq") {
    const açıq = new Set(yaddaş("açıqQovluqlar") || []);
    if (açıq.has(yol)) açıq.delete(yol); else açıq.add(yol);
    yaddaş("açıqQovluqlar", [...açıq]);
    S.seçiliQovluq = yol;
    ağacıYenilə();
  } else {
    S.seçiliQovluq = yol.includes("/") ? yol.slice(0, yol.lastIndexOf("/")) : "";
    faylıAç(yol).catch(xəta);
  }
});

async function yeniFayl(qovluq = S.seçiliQovluq) {
  const ad = await dialoq("Yeni fayl", { mətn: qovluq ? `Qovluq: ${qovluq}/` : "Layihənin kökündə",
    standart: "yeni.alq" });
  if (!ad) return null;
  const yol = (qovluq ? qovluq + "/" : "") + (/\.[\p{L}\p{N}]+$/u.test(ad) ? ad : ad + ".alq");
  try {
    await API.göndər("/api/fayl/yarat", { yol, növ: "fayl", mətn: "" });
    await ağacıYenilə();
    await faylıAç(yol);
    return yol;
  } catch (x) { xəta(x); return null; }
}

async function yeniQovluq() {
  const ad = await dialoq("Yeni qovluq", { standart: "qovluq" });
  if (!ad) return;
  const yol = (S.seçiliQovluq ? S.seçiliQovluq + "/" : "") + ad;
  try {
    await API.göndər("/api/fayl/yarat", { yol, növ: "qovluq" });
    const açıq = new Set(yaddaş("açıqQovluqlar") || []);
    açıq.add(yol);
    yaddaş("açıqQovluqlar", [...açıq]);
    S.seçiliQovluq = yol;
    await ağacıYenilə();
  } catch (x) { xəta(x); }
}

async function adınıDəyiş(yol) {
  const yeni = await dialoq("Adını dəyiş", { mətn: yol, standart: yol });
  if (!yeni || yeni === yol) return;
  try {
    const n = await API.göndər("/api/fayl/adlandir", { yol, yeni });
    for (const t of S.tablar) {
      if (t.yol === yol || t.yol.startsWith(yol + "/")) t.yol = n.yol + t.yol.slice(yol.length);
    }
    if (S.aktiv === yol || S.aktiv?.startsWith(yol + "/")) S.aktiv = n.yol + S.aktiv.slice(yol.length);
    tablarıÇək();
    await ağacıYenilə();
  } catch (x) { xəta(x); }
}

async function faylıSil(yol, növ) {
  const ok = await dialoq(`"${yol}" silinsin?`, {
    mətn: növ === "qovluq" ? "Qovluq bütün məzmunu ilə silinəcək." : "Bu əməl geri qaytarılmır.",
    giriş: false, tamam: "Sil" });
  if (!ok) return;
  try {
    await API.göndər("/api/fayl/sil", { yol });
    for (const t of [...S.tablar]) {
      if (t.yol === yol || t.yol.startsWith(yol + "/")) tabıBağla(t.yol, true);
    }
    await ağacıYenilə();
  } catch (x) { xəta(x); }
}

// ══ Nişanlar (tablar) ════════════════════════════════════════════════
const cari = () => S.tablar.find((t) => t.yol === S.aktiv) || null;
const çirklidir = (t) => (t.yol === S.aktiv ? R.mətn : t.v.mətn) !== t.saxlanmış;

async function faylıAç(yol, keç = true) {
  if (!S.tablar.some((t) => t.yol === yol)) {
    const d = await API.göndər("/api/fayl/oxu", { yol });
    S.tablar.push({ yol, saxlanmış: d.mətn, v: { mətn: d.mətn }, diaq: null, elementlər: [] });
    yaddaş("tablar", S.tablar.map((t) => t.yol));
  }
  if (keç) tabaKeç(yol);
}

function tabaKeç(yol) {
  const əvvəl = cari();
  if (əvvəl) əvvəl.v = R.vəziyyət();
  const t = S.tablar.find((x) => x.yol === yol);
  if (!t) return;
  S.aktiv = yol;
  yaddaş("aktiv", yol);
  R.yüklə(t.v.mətn, t.v);
  R.nöqtələriQoy(S.nöqtələr[yol]);
  S.dzSeçili = null;
  dizaynıPlanla(50);
  R.icraSətriniQoy(dbqSətri(yol));
  tablarıÇək();
  xoşGəldin();
  ağacSeçiminiYenilə();
  diaqnostikaNəticəsi(t.diaq);
  elementləriÇək(t.elementlər);
  planlaYoxla(50);
  // Başqa faylın komponent seçimi yeni fayla aid deyil
  komponentSeçiminiSıfırla();
  if (S.önbaxışAçıq) önbaxışıYenilə();
  X.mövqe = null;
  if (xüsusiyyətPaneliAçıqdır()) xüsusiyyətləriYüklə();
  if (typeof strukturuYenilə === "function") strukturuYenilə();
  R.fokus();
}

function ağacSeçiminiYenilə() {
  for (const d of $$(".düyün.fayl")) d.classList.toggle("seçili", d.dataset.yol === S.aktiv);
}

async function tabıBağla(yol, məcburi = false) {
  const t = S.tablar.find((x) => x.yol === yol);
  if (!t) return;
  if (!məcburi && çirklidir(t)) {
    const ok = await dialoq(`"${yol}" saxlanmayıb`, { mətn: "Dəyişikliklər itəcək. Bağlansın?",
      giriş: false, tamam: "Saxlamadan bağla" });
    if (!ok) return;
  }
  const i = S.tablar.indexOf(t);
  S.tablar.splice(i, 1);
  yaddaş("tablar", S.tablar.map((x) => x.yol));
  if (S.aktiv === yol) {
    S.aktiv = null;
    const n = S.tablar[Math.min(i, S.tablar.length - 1)];
    if (n) tabaKeç(n.yol);
    else { R.yüklə(""); diaqnostikaNəticəsi(null); elementləriÇək([]); }
  }
  tablarıÇək();
  xoşGəldin();
}

function tablarıÇək() {
  $("#tablar").innerHTML = S.tablar.map((t) => {
    const ad = t.yol.split("/").pop();
    return `<div class="tab${t.yol === S.aktiv ? " aktiv" : ""}${çirklidir(t) ? " çirkli" : ""}" ` +
      `data-yol="${qaç(t.yol)}" title="${qaç(t.yol)}" role="tab">${qaç(ad)}` +
      `<button class="bağla" data-bagla title="Bağla (Alt+W)"><span>×</span></button></div>`;
  }).join("");
}

$("#tablar").addEventListener("click", (h) => {
  const t = h.target.closest(".tab");
  if (!t) return;
  if (h.target.closest("[data-bagla]")) tabıBağla(t.dataset.yol);
  else tabaKeç(t.dataset.yol);
});
$("#tablar").addEventListener("auxclick", (h) => {
  const t = h.target.closest(".tab");
  if (t && h.button === 1) tabıBağla(t.dataset.yol);
});

async function saxla(t = cari(), səssiz = false) {
  if (!t) return false;
  const mətn = t.yol === S.aktiv ? R.mətn : t.v.mətn;
  try {
    await API.göndər("/api/fayl/yaz", { yol: t.yol, mətn });
    t.saxlanmış = mətn;
    tablarıÇək();
    if (!səssiz) bildir(`Saxlanıldı: ${t.yol}`, "uğur", 1800);
    if (S.önbaxışAçıq && t.yol === S.aktiv) önbaxışıYenilə(true);
    return true;
  } catch (x) { xəta(x); return false; }
}

function xoşGəldin() {
  $("#xos-geldin").hidden = S.tablar.length > 0;
  if (!S.tablar.length) {
    const f = bütünFayllar().filter((y) => /\.(alqor|alq)$/.test(y)).slice(0, 24);
    $("#son-fayllar").innerHTML = f.length
      ? f.map((y) => `<button data-ac="${qaç(y)}">${qaç(y)}</button>`).join("")
      : '<span class="sönük">Hələ .alq faylı yoxdur.</span>';
  }
}

$("#son-fayllar").addEventListener("click", (h) => {
  const b = h.target.closest("[data-ac]");
  if (b) faylıAç(b.dataset.ac).catch(xəta);
});

function şablonlarıQur(şablonlar) {
  const izah = {
    konsol: "oxu / yaz ilə terminal proqramı",
    veb: "`veb` modulu ilə server + vidjet səhifəsi",
    desktop: "komponent + vidjetlər + pəncərə",
  };
  $("#sablonlar").innerHTML = şablonlar.map((ş) =>
    `<button class="şablon" data-sablon="${ş.növ}"><b>${qaç(ş.ad)}</b>` +
    `<span class="sönük">${qaç(izah[ş.növ] || "")}</span></button>`).join("");
}

$("#sablonlar").addEventListener("click", async (h) => {
  const b = h.target.closest("[data-sablon]");
  if (!b) return;
  const ad = await dialoq("Yeni layihə", { mətn: "Layihə qovluğunun adı", standart: `${b.dataset.sablon}-layihəsi` });
  if (!ad) return;
  try {
    const n = await API.göndər("/api/sablon", { növ: b.dataset.sablon, ad });
    const açıq = new Set(yaddaş("açıqQovluqlar") || []);
    açıq.add(n.qovluq);
    yaddaş("açıqQovluqlar", [...açıq]);
    await ağacıYenilə();
    await faylıAç(n.fayl);
    bildir(`"${ad}" layihəsi yaradıldı`, "uğur");
  } catch (x) { xəta(x); }
});

// ══ Redaktor hadisələri ══════════════════════════════════════════════
R.on("dəyişdi", () => {
  const t = cari();
  if (!t) return;
  dizaynıPlanla();
  const ç = çirklidir(t);
  const el = $(`.tab[data-yol="${CSS.escape(t.yol)}"]`);
  if (el && el.classList.contains("çirkli") !== ç) el.classList.toggle("çirkli", ç);
  planlaYoxla();
});
R.on("kursor", (s, st) => { $("#st-kursor").textContent = `Sətir ${s}, Sütun ${st}`; });
R.on("saxla", () => saxla());

// ── Dil serveri (alqorls): tamamlama, imza ipucu ──
function lspMövqe(kursor) {
  const m = R.mətn;
  const baş = m.lastIndexOf("\n", kursor - 1) + 1;
  let sətir = 0;
  for (let i = m.indexOf("\n"); i >= 0 && i < baş; i = m.indexOf("\n", i + 1)) sətir++;
  return { sətir, sütun: kursor - baş };   // JS sətirləri UTF-16-dır — LSP ilə eyni
}
async function dilSorğusu(metod, kursor) {
  const t = cari();
  if (!t || !/\.(alqor|alq)$/.test(t.yol)) return null;
  const n = await API.göndər("/api/dil", { metod, yol: t.yol, mətn: R.mətn, ...lspMövqe(kursor) });
  return n.nəticə;
}
R.tamamlayıcı = (kursor) => dilSorğusu("tamamla", kursor);
R.imzaVerən = (kursor) => dilSorğusu("imza", kursor);
R.on("ikiKlik", (baş) => {
  // `vidjet.ad(` üzərində iki klik — çatışmayan kodu yaz
  const m = R.mətn;
  let b = baş;
  while (b > 0 && Redaktor.AD.test(m[b - 1])) b--;
  let s = baş;
  while (s < m.length && Redaktor.AD.test(m[s])) s++;
  const söz = m.slice(b, s);
  const vidjetSözü = söz === "vidjet" && /^\s*\.\s*[\p{L}_]/u.test(m.slice(s, s + 3));
  const vidjetAdı = /vidjet\s*\.\s*$/.test(m.slice(Math.max(0, b - 12), b)) && m[s] === "(";
  if (vidjetSözü || vidjetAdı) vidjetiTamamla(baş);
});
R.on("buraxıldı", (mövqe, ad) => vidjetiƏlavəEt(ad, mövqe));

// ══ Diaqnostika ══════════════════════════════════════════════════════
let yoxlamaTaymeri = 0;
let yoxlamaNömrəsi = 0;
function planlaYoxla(gecikmə = 450) {
  clearTimeout(yoxlamaTaymeri);
  yoxlamaTaymeri = setTimeout(yoxla, gecikmə);
}

async function yoxla() {
  const t = cari();
  if (!t) return;
  const n = ++yoxlamaNömrəsi;
  const mətn = R.mətn;
  if (!/\.(alqor|alq)$/.test(t.yol)) { diaqnostikaNəticəsi(null); return; }
  try {
    const [d, e] = await Promise.all([
      API.göndər("/api/yoxla", { mətn, ad: t.yol }),
      API.göndər("/api/vidjet/elementler", { mətn }),
    ]);
    if (n !== yoxlamaNömrəsi || cari() !== t) return;
    t.diaq = d;
    t.elementlər = e.elementlər;
    diaqnostikaNəticəsi(d);
    elementləriÇək(e.elementlər);
  } catch (x) { /* server məşğuldur — növbəti dəfə */ }
}

function diaqnostikaNəticəsi(d) {
  const siyahı = d ? d.diaqnostikalar : [];
  R.diaqnostikaQoy(siyahı);
  $("#st-ascii").textContent = `ASCII: ${d ? d.ascii : 0}`;
  $("#st-diaq").textContent = d ? `✖ ${d.xəta}  ⚠ ${d.xəbərdarlıq}` : "";
  Dok.say("problemler", siyahı.length || "");
  const işarə = { xəta: "✖", xəbərdarlıq: "⚠", məlumat: "ℹ" };
  $("#problemler").innerHTML = siyahı.length ? siyahı.map((p, i) =>
    `<li class="${p.səviyyə}" data-i="${i}"><span class="işarə">${işarə[p.səviyyə] || "•"}</span>` +
    `<span class="kod">${qaç(p.kod)}</span><span>${qaç(p.mesaj)}` +
    (p.qeyd ? ` <span class="qeyd">— ${qaç(p.qeyd)}</span>` : "") +
    (p.köməklər?.length ? `<br><span class="qeyd">kömək: ${qaç(p.köməklər.join(" · "))}</span>` : "") +
    `</span><span class="yer">${p.sətir}:${p.sütun}</span></li>`).join("")
    : `<li class="sönük">${d ? "✓ Problem yoxdur" : ""}</li>`;
}

$("#problemler").addEventListener("click", (h) => {
  const li = h.target.closest("li[data-i]");
  const t = cari();
  if (!li || !t?.diaq) return;
  const p = t.diaq.diaqnostikalar[+li.dataset.i];
  R.sətirəKeç(p.sətir, p.sütun, p.sətir === p.sonSətir ? Math.max(0, p.sonSütun - p.sütun) : 0);
});
$("#st-diaq").addEventListener("click", () => altPaneliAç("problemler"));

function növbətiProblem() {
  const t = cari();
  const s = t?.diaq?.diaqnostikalar || [];
  if (!s.length) return;
  const { sətir, sütun } = R.sətirSütun();
  const p = s.find((d) => d.sətir > sətir || (d.sətir === sətir && d.sütun > sütun)) || s[0];
  R.sətirəKeç(p.sətir, p.sütun);
  bildir(`${p.kod}: ${p.mesaj}${p.qeyd ? " — " + p.qeyd : ""}`, p.səviyyə === "xəta" ? "xəta" : "");
}

function altPaneliAç(ad) { Dok.aç(ad); }

// ══ Palet ════════════════════════════════════════════════════════════
function paletiQur() {
  const { kateqoriyalar, vidjetlər } = S.kataloq;
  const açıq = new Set(yaddaş("paletAçıq") || kateqoriyalar);
  $("#palet").innerHTML = kateqoriyalar.map((k) => {
    const v = vidjetlər.filter((x) => x.kateqoriya === k);
    return `<details class="kateqoriya" data-kateqoriya="${qaç(k)}"${açıq.has(k) ? " open" : ""}>` +
      `<summary>${qaç(S.kataloq.kateqoriyaAdları?.[k] || k)} <span class="say">${v.length}</span></summary>` +
      v.map((x) => `<div class="vidjet-elementi" draggable="true" data-vidjet="${qaç(x.ad)}" ` +
        `title="${qaç(x.nümunə)}"><b>${qaç(x.beynəlxalqAd || x.ad)}</b>` +
        (x.skeletVar ? '<span class="nişan-skelet" title="İki klik: vəziyyət + idarəedici yazılır">⚡ kod</span>' : "<span></span>") +
        (x.miniatür ? '<div class="miniatür" aria-hidden="true"></div>' : "") +
        `<small><code>vidjet.${qaç(x.ad)}</code> · ${qaç(x.izah)}</small></div>`).join("") + "</details>";
  }).join("");
  miniatürləriÇək();
}

/**
 * Hər vidjetin həqiqi görünüşü — Shadow DOM-da (Studio üslubu ilə
 * qarışmasın), vidjet üslubu ilə, kiçildilmiş. HTML serverdə `vidjet`
 * modulunun özü ilə qurulub, ona görə önbaxışdakı ilə eynidir.
 */
function miniatürləriÇək() {
  // Vidjet üslubunun dəyişənləri `:root`-dadır — Shadow DOM-da `:host`.
  // Qaranlıq rənglər OS-un yox, Studio-nun öz temasına görə seçilir.
  let css = (S.kataloq.üslub || "").replaceAll(":root", ":host");
  const qaranlıq = document.documentElement.dataset.tema === "qaranlıq";
  css = css.replace(/@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(:host\{[^}]*\})\}/,
    (_, iç) => (qaranlıq ? iç : ""));
  const üslub = `${css}
    :host{display:block;height:100%;background:var(--v-fon);color:var(--v-mətn)}
    .ç{position:absolute;left:8px;top:7px;transform:scale(.72);transform-origin:0 0;
       width:calc((100% - 16px) / .72);font:14px/1.5 system-ui,"Segoe UI",sans-serif}
    .ç .v-modal-örtük,.ç .v-yan-panel-örtük{position:relative!important;inset:auto!important}`;
  for (const v of $$(".vidjet-elementi")) {
    const yer = $(".miniatür", v);
    if (!yer) continue;
    const x = S.kataloq.vidjetlər.find((y) => y.ad === v.dataset.vidjet);
    const kök = yer.shadowRoot || yer.attachShadow({ mode: "open" });
    kök.innerHTML = `<style>${üslub}</style><div class="ç">${x.miniatür}</div>`;
  }
}

$("#palet").addEventListener("toggle", () => {
  yaddaş("paletAçıq", $$(".kateqoriya[open]").map((d) => d.dataset.kateqoriya));
}, true);

$("#palet-axtar").addEventListener("input", (h) => {
  const s = h.target.value.trim().toLocaleLowerCase("az");
  for (const v of $$(".vidjet-elementi")) {
    const x = S.kataloq.vidjetlər.find((y) => y.ad === v.dataset.vidjet);
    const kat = S.kataloq.kateqoriyaAdları?.[x.kateqoriya] || "";
    v.hidden = !!s && !(`${x.beynəlxalqAd} ${x.ad} ${x.izah} ${x.kateqoriya} ${kat}`
      .toLocaleLowerCase("az").includes(s));
  }
  for (const d of $$(".kateqoriya")) {
    const görünən = $$(".vidjet-elementi:not([hidden])", d).length;
    d.hidden = !görünən;
    if (s && görünən) d.open = true;
  }
});

let klikTaymeri = 0;
$("#palet").addEventListener("click", (h) => {
  const v = h.target.closest("[data-vidjet]");
  if (!v) return;
  clearTimeout(klikTaymeri);
  if (h.detail > 1) return;
  // Tək klik — iki klikdən ayırmaq üçün qısa gözləmə
  klikTaymeri = setTimeout(() => nümunəniQoy(v.dataset.vidjet), 260);
});
$("#palet").addEventListener("dblclick", (h) => {
  const v = h.target.closest("[data-vidjet]");
  if (!v) return;
  clearTimeout(klikTaymeri);
  vidjetiƏlavəEt(v.dataset.vidjet);
});
$("#palet").addEventListener("dragstart", (h) => {
  const v = h.target.closest("[data-vidjet]");
  if (!v) return;
  const x = S.kataloq.vidjetlər.find((y) => y.ad === v.dataset.vidjet);
  h.dataTransfer.setData("application/x-alqor-vidjet", v.dataset.vidjet);
  h.dataTransfer.setData("text/plain", x.nümunə);
  h.dataTransfer.effectAllowed = "copy";
});

/** Açıq fayl yoxdursa — yeni fayl yaradılır ki, element boşa getməsin. */
async function faylLazımdır() {
  if (cari()) return true;
  const mövcud = new Set(bütünFayllar());
  let ad = "tətbiq.alq", n = 2;
  while (mövcud.has(ad)) ad = `tətbiq${n++}.alq`;
  try {
    await API.göndər("/api/fayl/yarat", { yol: ad, növ: "fayl", mətn: "" });
    await ağacıYenilə();
    await faylıAç(ad);
    return true;
  } catch (x) { xəta(x); return false; }
}

async function nümunəniQoy(ad) {
  if (!(await faylLazımdır())) return;
  try {
    const n = await API.göndər("/api/vidjet/numune", { mətn: R.mətn, vidjet: ad, kursor: R.kursor });
    R.daxilEt(n.kod);
    bildir(`\`${ad}\` qoyuldu — üzərinə iki klik lazım olan kodu yazar`, "", 2600);
  } catch (x) { xəta(x); }
}

async function vidjetiƏlavəEt(ad, kursor = null) {
  if (!(await faylLazımdır())) return;
  try {
    const n = await API.göndər("/api/vidjet/elave", {
      mətn: R.mətn, vidjet: ad, kursor: kursor ?? R.kursor });
    R.mətniƏvəzlə(n.mətn, n.kursor, n.yeniSətirlər);
    R.fokus();
    bildir(n.mesaj, "uğur", 4200);
    planlaYoxla(100);
  } catch (x) { xəta(x); }
}

async function vidjetiTamamla(kursor) {
  try {
    const n = await API.göndər("/api/vidjet/tamamla", { mətn: R.mətn, kursor });
    if (n.dəyişdi) {
      R.mətniƏvəzlə(n.mətn, n.kursor, n.yeniSətirlər);
      bildir(n.mesaj, "uğur", 4200);
      planlaYoxla(100);
    } else bildir(n.mesaj, "", 2400);
  } catch (x) { xəta(x); }
}

function elementləriÇək(siyahı) {
  siyahı = siyahı || [];
  const yarımçıq = siyahı.filter((e) => e.çatışmır.length).length;
  $("#element-sayi").textContent = siyahı.length
    ? `(${siyahı.length}${yarımçıq ? `, ${yarımçıq} yarımçıq` : ""})` : "";
  $("#elementler").innerHTML = siyahı.length ? siyahı.map((e, i) => {
    const tam = !e.çatışmır.length;
    return `<div class="fayl-elementi ${tam ? "tam" : "yarımçıq"}" data-i="${i}" ` +
      `title="${tam ? "Hazırdır" : "İki klik: " + qaç(e.çatışmır.join(", ")) + " yazılsın"}">` +
      `<span class="vəziyyət-işarəsi">${tam ? "✓" : "⚡"}</span>` +
      `<span>${qaç(e.beynəlxalqAd || e.ad)}</span><span class="sönük">${qaç(e.ad)} :${e.sətir}</span>` +
      (tam ? "" : `<span class="çatışmır">${qaç(e.çatışmır.join(", "))}</span>`) + "</div>";
  }).join("") : '<p class="ipucu-mətni">Bu faylda `vidjet.…` çağırışı yoxdur.</p>';
}

$("#elementler").addEventListener("click", (h) => {
  const d = h.target.closest("[data-i]");
  const e = cari()?.elementlər?.[+d?.dataset.i];
  if (!e) return;
  R.sətirəKeç(e.sətir, e.sütun);
  // Tək klik — xüsusiyyətlər; iki klikdən ayırmaq üçün qısa gözləmə
  clearTimeout(elementKlikTaymeri);
  if (h.detail > 1) return;
  elementKlikTaymeri = setTimeout(() => {
    panelAç("xususiyyet");
    xüsusiyyətləriYüklə(e.mövqe);
  }, 260);
});
let elementKlikTaymeri = 0;
$("#elementler").addEventListener("dblclick", (h) => {
  clearTimeout(elementKlikTaymeri);
  const d = h.target.closest("[data-i]");
  const e = cari()?.elementlər?.[+d?.dataset.i];
  if (e) vidjetiTamamla(e.mövqe);
});

function panelAç(ad) { Dok.aç(ad); }

// ══ Xüsusiyyətlər paneli ═════════════════════════════════════════════
//
// Kursorun içində olduğu `vidjet.…(…)` çağırışının parametrləri. Hər
// dəyişiklik koda yazılır (server mətni dəyişir — dırnaq, girinti,
// vergül düzgün qalır), fayl səssiz saxlanır, önbaxış canlı yenilənir.

const X = { mövqe: null, məlumat: null, taymer: 0, yazılır: false, növbə: Promise.resolve() };

function xüsusiyyətPaneliAçıqdır() { return !$("#panel-xususiyyet").hidden; }

async function xüsusiyyətləriYüklə(kursor = R.kursor) {
  const t = cari();
  const boş = $("#xus-bos"), forma = $("#xus-forma");
  if (!t || !/\.(alqor|alq)$/.test(t.yol)) { boş.hidden = false; forma.hidden = true; X.mövqe = null; return; }
  let n;
  try { n = await API.göndər("/api/vidjet/xususiyyetler", { mətn: R.mətn, kursor }); }
  catch (x) { return; }
  if (n.xəta) {
    // Kursor çağırışdan çıxıb — son seçilmiş element panelda qalır
    if (X.mövqe === null) { boş.hidden = false; forma.hidden = true; }
    return;
  }
  // Eyni element və istifadəçi paneldə yazır — formanı yenidən qurmuruq
  if (X.mövqe === n.mövqe && forma.contains(document.activeElement)) { X.məlumat = n; return; }
  X.mövqe = n.mövqe;
  X.məlumat = n;
  boş.hidden = true;
  forma.hidden = false;
  forma.innerHTML = xüsusiyyətFormu(n);
}

function xüsusiyyətFormu(n) {
  const sadələr = n.parametrlər.filter((p) => p.sadə);
  const ifadələr = n.parametrlər.filter((p) => !p.sadə);
  let h = `<div class="xüs-başlıq"><b>${qaç(n.beynəlxalqAd || n.ad)}</b>` +
    `<span class="sönük"><code>vidjet.${qaç(n.ad)}</code> · sətir ${n.sətir}</span>` +
    `<button data-xus-get title="Redaktorda göstər">↗ kod</button></div>`;
  h += `<div class="xüs-qrup"><h4>Xüsusiyyətlər</h4>${sadələr.map(sahəHTML).join("")}</div>`;
  h += `<div class="xüs-qrup"><h4>Görünüş</h4>`;
  if (n.üslub === null) {
    h += `<div class="xüs-sətir"><label>üslub</label><span class="ifadə" data-xus-get title="ifadədir — redaktorda dəyişin">${qaç(n.üslubİfadə)}</span></div>`;
  } else {
    h += n.üslubSahələri.map((u) => sahəHTML({
      ad: `üslub.${u.ad}`, görünən: u.ad, növ: u.növ, izah: u.izah, seçimlər: u.seçimlər,
      verilib: u.ad in n.üslub, dəyər: n.üslub[u.ad] ?? null, standart: null,
    })).join("");
  }
  h += "</div>";
  if (ifadələr.length) {
    h += `<div class="xüs-qrup"><h4>Hadisələr və ifadələr</h4>` + ifadələr.map((p) =>
      `<div class="xüs-sətir${p.verilib ? " verilib" : ""}"><label title="${qaç(p.izah)}">${qaç(p.ad)}</label>` +
      `<span class="ifadə" data-xus-get title="${p.verilib ? "redaktorda dəyişin" : qaç(p.izah)}">` +
      `${p.verilib ? qaç(p.ifadə) : "—"}</span><span></span></div>`).join("") + "</div>";
  }
  return h + `<div class="xüs-xəta" id="xus-xeta" hidden></div>`;
}

function sahəHTML(p) {
  const ad = qaç(p.ad), görünən = qaç(p.görünən || p.ad);
  const d = p.verilib ? p.dəyər : null;
  const std = p.standart;
  let giriş;
  if (p.növ === "məntiq") {
    const işarəli = d ?? std ?? false;
    giriş = `<input type="checkbox" data-xus="${ad}" data-nov="məntiq"${işarəli ? " checked" : ""}>`;
  } else if (p.növ === "seçim") {
    const cari = d ?? "";
    giriş = `<select data-xus="${ad}" data-nov="seçim"><option value="">${std != null ? `standart (${qaç(std)})` : "—"}</option>` +
      p.seçimlər.map((s) => `<option value="${qaç(s)}" data-tip="${typeof s}"${String(s) === String(cari) ? " selected" : ""}>${qaç(s)}</option>`).join("") +
      "</select>";
  } else if (p.növ === "rəng") {
    const hex = typeof d === "string" && /^#[0-9a-f]{6}$/i.test(d) ? d : "#000000";
    giriş = `<span class="birləşik"><input type="color" data-xus-reng="${ad}" value="${hex}">` +
      `<input type="text" data-xus="${ad}" data-nov="mətn" value="${qaç(d ?? "")}" placeholder="#0b6bcb, red …"></span>`;
  } else if (p.növ === "ədəd" || p.növ === "aralıq") {
    const ad_ = p.növ === "aralıq" ? ' step="0.05" min="0" max="1"' : "";
    giriş = `<input type="number" data-xus="${ad}" data-nov="ədəd"${ad_} value="${d ?? ""}" placeholder="${std != null ? qaç(std) : ""}">`;
  } else {
    giriş = `<input type="text" data-xus="${ad}" data-nov="mətn" value="${qaç(d ?? "")}" placeholder="${std != null && std !== "" ? qaç(std) : ""}">`;
  }
  return `<div class="xüs-sətir${p.verilib ? " verilib" : ""}" data-sətir="${ad}">` +
    `<label title="${qaç(p.izah || "")}">${görünən}</label>${giriş}` +
    `<button class="sıfırla" data-xus-sil="${ad}" title="Standarta qaytar (arqumenti sil)">✕</button>` +
    (p.izah ? `<div class="izah">${qaç(p.izah)}</div>` : "") + "</div>";
}

function xüsusiyyətDəyəri(el) {
  const növ = el.dataset.nov;
  if (növ === "məntiq") return el.checked;
  if (el.value === "") return null;
  if (növ === "ədəd") { const n = Number(el.value); return Number.isFinite(n) ? n : null; }
  if (növ === "seçim") {
    const o = el.selectedOptions[0];
    return o?.dataset.tip === "number" ? Number(el.value) : el.value;
  }
  return el.value;
}

function xüsusiyyətQoy(ad, dəyər) {
  // Ardıcıl icra — sürətli yazılan dəyişikliklər bir-birini ötməsin
  X.növbə = X.növbə.then(async () => {
    if (X.mövqe === null) return;
    const xət = $("#xus-xeta");
    try {
      const n = await API.göndər("/api/vidjet/xususiyyet", { mətn: R.mətn, kursor: X.mövqe, ad, dəyər });
      if (xət) xət.hidden = true;
      if (!n.dəyişdi) return;
      X.yazılır = true;
      R.mətniƏvəzlə(n.mətn, n.kursor);
      X.yazılır = false;
      $(`[data-sətir="${CSS.escape(ad)}"]`)?.classList.toggle("verilib", dəyər !== null);
      planlaYoxla(150);
      const t = cari();
      if (t && /\.(alqor|alq)$/.test(t.yol)) {
        if (await saxla(t, true) && !S.önbaxışAçıq) {
          // Önbaxış bağlıdır — ilk dəyişiklikdə açırıq ki, nəticə görünsün
          if (/\bkomponent\s+[\p{L}_]/u.test(R.mətn)) önbaxışıAçBağla(true);
        }
      }
    } catch (x) {
      X.yazılır = false;
      if (xət) { xət.hidden = false; xət.textContent = x.message; }
    }
  });
}

$("#xus-forma").addEventListener("input", (h) => {
  const el = h.target;
  if (el.dataset.xusReng) {                 // rəng seçici → mətn sahəsi
    const m = $(`[data-xus="${CSS.escape(el.dataset.xusReng)}"]`);
    if (m) m.value = el.value;
    clearTimeout(X.taymer);
    X.taymer = setTimeout(() => xüsusiyyətQoy(el.dataset.xusReng, el.value), 120);
    return;
  }
  if (!el.dataset.xus) return;
  // Rəng mətn kimi yazılır — yanındakı rəng kvadratı da yenilənsin
  const kvadrat = el.parentElement?.querySelector("input[type=color]");
  if (kvadrat && /^#[0-9a-f]{6}$/i.test(el.value)) kvadrat.value = el.value;
  if (el.dataset.nov === "mətn" || el.dataset.nov === "ədəd") {
    clearTimeout(X.taymer);
    X.taymer = setTimeout(() => xüsusiyyətQoy(el.dataset.xus, xüsusiyyətDəyəri(el)), 300);
  }
});
$("#xus-forma").addEventListener("change", (h) => {
  const el = h.target;
  if (!el.dataset.xus) return;
  clearTimeout(X.taymer);
  xüsusiyyətQoy(el.dataset.xus, xüsusiyyətDəyəri(el));
});
$("#xus-forma").addEventListener("click", (h) => {
  const sil = h.target.closest("[data-xus-sil]");
  if (sil) {
    const ad = sil.dataset.xusSil;
    const el = $(`[data-xus="${CSS.escape(ad)}"]`);
    if (el) { if (el.type === "checkbox") el.checked = false; else el.value = ""; }
    xüsusiyyətQoy(ad, null);
    return;
  }
  if (h.target.closest("[data-xus-get]") && X.məlumat) {
    R.sətirəKeç(X.məlumat.sətir, 1);
  }
});

// Kursor başqa vidjet çağırışına keçəndə panel yenilənir
let xüsKursorTaymeri = 0;
R.on("kursor", () => {
  if (!xüsusiyyətPaneliAçıqdır() || X.yazılır) return;
  clearTimeout(xüsKursorTaymeri);
  xüsKursorTaymeri = setTimeout(() => xüsusiyyətləriYüklə(), 220);
});

// ══ İcra ═════════════════════════════════════════════════════════════
const ANSİ = { 30: "#555", 31: "var(--xəta)", 32: "var(--uğur)", 33: "var(--xəbərdarlıq)",
  34: "var(--vurğu)", 35: "var(--t-açar)", 36: "var(--t-tip)", 37: "inherit", 90: "var(--sönük)" };

function çıxışaYaz(mətn, sinif = "") {
  const p = $("#cixis");
  const aşağıdadır = p.scrollHeight - p.scrollTop - p.clientHeight < 30;
  let html = "";
  let rəng = null;
  for (const [i, parça] of mətn.split(/\x1b\[([0-9;]*)m/).entries()) {
    if (i % 2) {
      const k = +parça.split(";").pop() || 0;
      rəng = k === 0 ? null : (ANSİ[k] || ANSİ[k - 60] || rəng);
      continue;
    }
    if (!parça) continue;
    let h = qaç(parça).replace(/([\p{L}\p{N}_\-./]+\.alq(?:or)?):(\d+):(\d+)/gu,
      '<span class="keçid-yer" data-fayl="$1" data-setir="$2" data-sutun="$3">$&</span>');
    if (rəng) h = `<span style="color:${rəng}">${h}</span>`;
    html += h;
  }
  const s = document.createElement("span");
  if (sinif) s.className = sinif;
  s.innerHTML = html;
  p.append(s);
  if (p.childNodes.length > 6000) p.firstChild.remove();
  if (aşağıdadır) p.scrollTop = p.scrollHeight;
}

$("#cixis").addEventListener("click", (h) => {
  const k = h.target.closest(".keçid-yer");
  if (!k) return;
  const ad = k.dataset.fayl.split("/").pop();
  const t = S.tablar.find((x) => x.yol.split("/").pop() === ad)
    || { yol: bütünFayllar().find((y) => y.split("/").pop() === ad) };
  if (!t.yol) return;
  faylıAç(t.yol).then(() => R.sətirəKeç(+k.dataset.setir, +k.dataset.sutun)).catch(xəta);
});

async function işlət() {
  const t = cari();
  if (!t) { bildir("Əvvəlcə fayl açın"); return; }
  if (!/\.(alqor|alq)$/.test(t.yol)) { bildir("Yalnız .alq faylları işlədilə bilər", "xəta"); return; }
  if (çirklidir(t) && !(await saxla(t))) return;
  if (S.iş) await dayandır();
  $("#cixis").textContent = "";
  altPaneliAç("cixis");
  çıxışaYaz(`▶ ${t.yol}\n`, "x-sistem");
  try {
    const iş = await API.göndər("/api/islet", { yol: t.yol });
    axınıOxu(iş.id);
  } catch (x) { çıxışaYaz(`✖ ${x.message}\n`, "x-xəta"); }
}

async function qur(hədəf) {
  const t = cari();
  if (!t) { bildir("Əvvəlcə proqram faylını açın"); return; }
  if (!/\.(alqor|alq)$/.test(t.yol)) { bildir("Yalnız .alq faylları qurula bilər", "xəta"); return; }
  if (çirklidir(t) && !(await saxla(t))) return;
  if (S.iş) await dayandır();
  $("#cixis").textContent = "";
  altPaneliAç("cixis");
  const adlar = { exe: "tək .exe (Windows)", veb: "veb səhifə", js: "JavaScript",
                  pyz: "Alqor paketi (.pyz)", "quraşdırıcı": "Windows quraşdırıcısı" };
  çıxışaYaz(`⚙ Qurulur: ${adlar[hədəf]} — ${t.yol}\n`, "x-sistem");
  try {
    const iş = await API.göndər("/api/qur", { yol: t.yol, hədəf });
    axınıOxu(iş.id);
  } catch (x) { çıxışaYaz(`✖ ${x.message}\n`, "x-xəta"); }
}

function axınıOxu(id) {
  const axın = new EventSource(`/api/islet/axin?id=${encodeURIComponent(id)}&t=${encodeURIComponent(API.nişan)}`);
  S.iş = { id, axın };
  $("#dym-dayandir").disabled = false;
  $("#dym-islet").disabled = true;
  $("#giris").disabled = false;
  $("#giris").focus();
  axın.onmessage = (h) => {
    const d = JSON.parse(h.data);
    if (d.növ === "çıxış") çıxışaYaz(d.mətn);
    else if (d.növ === "xəta") çıxışaYaz(d.mətn, "x-xəta");
    else if (d.növ === "dayandı") debaqDayandı(d);
    else if (d.növ === "davam") debaqDavam();
    else if (d.növ === "bitdi") {
      çıxışaYaz(`\n⊣ proses bitdi — kod ${d.kod}, ${d.müddət.toFixed(2)} san.\n`,
        d.kod === 0 ? "x-uğur" : "x-xəta");
      işBitdi();
    }
  };
  axın.onerror = () => {
    if (axın.readyState === EventSource.CLOSED) işBitdi();
  };
}

function işBitdi() {
  if (S.iş) S.iş.axın.close();
  const debaqİdi = S.iş?.debaq;
  S.iş = null;
  if (debaqİdi) debaqBitdi();
  $("#dym-dayandir").disabled = true;
  $("#dym-islet").disabled = false;
  $("#giris").disabled = true;
}

async function dayandır() {
  if (!S.iş) return;
  try { await API.göndər("/api/islet/dayandir", { id: S.iş.id }); } catch (x) { xəta(x); }
}

$("#giris-formu").addEventListener("submit", async (h) => {
  h.preventDefault();
  if (!S.iş) return;
  const g = $("#giris");
  çıxışaYaz(g.value + "\n", "x-giriş");
  try { await API.göndər("/api/islet/giris", { id: S.iş.id, mətn: g.value }); } catch (x) { xəta(x); }
  g.value = "";
});
$("#cixis-temizle").addEventListener("click", () => { $("#cixis").textContent = ""; });

// ══ Debaq ════════════════════════════════════════════════════════════
//
// Dayanma nöqtəsi: sətir nömrəsinə klik və ya F9. 🐞 Debaq (Ctrl+F5)
// proqramı `alqor dap` ilə işlədir; dayananda yığın və dəyişənlər
// "Debaq" panelində görünür. F5 davam, F10 növbəti, F11 daxil ol,
// Shift+F11 çıx.

S.nöqtələr = yaddaş("nöqtələr") || {};

R.on("nöqtələr", (sətirlər) => {
  const t = cari();
  if (!t) return;
  if (sətirlər.length) S.nöqtələr[t.yol] = sətirlər; else delete S.nöqtələr[t.yol];
  yaddaş("nöqtələr", S.nöqtələr);
  if (S.iş?.debaq) {
    API.göndər("/api/debaq/noqteler", { id: S.iş.id, nöqtələr: { [t.yol]: sətirlər } }).catch(() => {});
  }
});

function dbqSətri(yol) {
  const k = S.dbq?.yığın?.[S.dbq.kadr];
  return k && k.yol === yol ? k.sətir : 0;
}

function dbqDüymələri() {
  const aktiv = !!S.iş?.debaq, dayanıb = aktiv && !!S.dbq;
  for (const id of ["dbq-davam", "dbq-novbeti", "dbq-daxil", "dbq-cix"]) $("#" + id).disabled = !dayanıb;
  $("#dbq-fasile").disabled = !aktiv || dayanıb;
  $("#dbq-dayandir").disabled = !aktiv;
  $("#dym-debaq").disabled = aktiv;
}

async function debaqBaşlat() {
  const t = cari();
  if (!t) { bildir("Əvvəlcə fayl açın"); return; }
  if (!/\.(alqor|alq)$/.test(t.yol)) { bildir("Yalnız .alq faylları debaq edilə bilər", "xəta"); return; }
  if (çirklidir(t) && !(await saxla(t))) return;
  if (S.iş) await dayandır();
  $("#cixis").textContent = "";
  altPaneliAç("debaq");
  S.dbq = null;
  çıxışaYaz(`🐞 ${t.yol}\n`, "x-sistem");
  const nöqtələr = {};
  const fayllar = new Set(bütünFayllar());
  for (const [y, s] of Object.entries(S.nöqtələr)) if (fayllar.has(y)) nöqtələr[y] = s;
  $("#dbq-veziyyet").textContent = Object.keys(nöqtələr).length
    ? "İşləyir…" : "İşləyir — dayanma nöqtəsi yoxdur (⏸ ilə dayandırmaq olar)";
  try {
    const iş = await API.göndər("/api/debaq", { yol: t.yol, nöqtələr });
    axınıOxu(iş.id);
    S.iş.debaq = true;
    dbqDüymələri();
  } catch (x) { çıxışaYaz(`✖ ${x.message}\n`, "x-xəta"); }
}

async function debaqDayandı(d) {
  S.dbq = { yığın: d.yığın || [], kadr: 0, sahələr: d.sahələr || [] };
  const səbəb = { breakpoint: "dayanma nöqtəsi", step: "addım", pause: "fasilə", entry: "başlanğıc" }[d.səbəb] || d.səbəb;
  const k = S.dbq.yığın[0];
  $("#dbq-veziyyet").textContent = `Dayandı — ${səbəb}${k ? `: ${k.yol || "?"}:${k.sətir}` : ""}`;
  altPaneliAç("debaq");
  dbqDüymələri();
  dbqÇək();
  await kadraKeç(0, false);
}

async function kadraKeç(i, sahələriYüklə = true) {
  if (!S.dbq) return;
  S.dbq.kadr = i;
  const k = S.dbq.yığın[i];
  if (k?.yol) {
    try {
      if (cari()?.yol !== k.yol) await faylıAç(k.yol);
    } catch (_) { /* layihədən kənar fayl */ }
  }
  R.icraSətriniQoy(dbqSətri(cari()?.yol));
  if (sahələriYüklə && S.iş && k) {
    try {
      const n = await API.göndər("/api/debaq/kadr", { id: S.iş.id, kadr: k.id });
      S.dbq.sahələr = n.sahələr;
    } catch (x) { xəta(x); }
  }
  dbqÇək();
}

function dbqÇək() {
  const d = S.dbq;
  $("#dbq-yigin").innerHTML = d ? d.yığın.map((k, i) =>
    `<div class="kadr${i === d.kadr ? " seçili" : ""}" data-i="${i}"><span>${qaç(k.ad)}</span>` +
    `<span class="sönük">${qaç(k.yol || "")}:${k.sətir}</span></div>`).join("") : "";
  $("#dbq-deyisenler").innerHTML = d ? d.sahələr.map((s) =>
    `<div class="sönük" style="padding:2px 10px">${qaç(s.ad)}</div>` + dəyişənlərHTML(s.dəyişənlər)).join("") : "";
}

function dəyişənlərHTML(siyahı) {
  if (!siyahı?.length) return '<ul class="dəyişənlər"><li class="sönük">—</li></ul>';
  return '<ul class="dəyişənlər">' + siyahı.map((v) =>
    `<li class="dəyişən" data-ref="${v.ref}"><span class="ox">${v.ref ? "▸" : ""}</span>` +
    `<span class="d-ad">${qaç(v.ad)}</span> = <span class="d-dəyər">${qaç(v.dəyər)}</span>` +
    `<span class="d-tip">${qaç(v.tip || "")}</span></li>`).join("") + "</ul>";
}

$("#dbq-deyisenler").addEventListener("click", async (h) => {
  const ox = h.target.closest(".ox");
  const li = ox?.closest("[data-ref]");
  if (!li || !+li.dataset.ref || !S.iş) return;
  const açıq = li.querySelector(":scope > ul");
  if (açıq) { açıq.remove(); ox.textContent = "▸"; return; }
  try {
    const n = await API.göndər("/api/debaq/deyisenler", { id: S.iş.id, ref: +li.dataset.ref });
    li.insertAdjacentHTML("beforeend", dəyişənlərHTML(n.dəyişənlər));
    ox.textContent = "▾";
  } catch (x) { xəta(x); }
});

$("#dbq-yigin").addEventListener("click", (h) => {
  const d = h.target.closest("[data-i]");
  if (d) kadraKeç(+d.dataset.i);
});

function debaqDavam() {
  S.dbq = null;
  R.icraSətriniQoy(0);
  $("#dbq-veziyyet").textContent = "İşləyir…";
  dbqÇək();
  dbqDüymələri();
}

function debaqBitdi() {
  S.dbq = null;
  R.icraSətriniQoy(0);
  $("#dbq-veziyyet").textContent = "Debaq bitdi.";
  dbqÇək();
  dbqDüymələri();
}

async function debaqƏmri(əmr) {
  if (!S.iş?.debaq) return;
  if (əmr !== "fasilə" && !S.dbq) return;
  try { await API.göndər("/api/debaq/emr", { id: S.iş.id, əmr }); } catch (x) { xəta(x); }
}

$("#dbq-davam").addEventListener("click", () => debaqƏmri("davam"));
$("#dbq-novbeti").addEventListener("click", () => debaqƏmri("növbəti"));
$("#dbq-daxil").addEventListener("click", () => debaqƏmri("daxil"));
$("#dbq-cix").addEventListener("click", () => debaqƏmri("çıx"));
$("#dbq-fasile").addEventListener("click", () => debaqƏmri("fasilə"));
$("#dbq-dayandir").addEventListener("click", () => dayandır());
$("#dym-debaq").addEventListener("click", debaqBaşlat);

$("#dbq-ifade-formu").addEventListener("submit", async (h) => {
  h.preventDefault();
  const ifadə = $("#dbq-ifade").value.trim();
  if (!ifadə || !S.iş?.debaq) return;
  const k = S.dbq?.yığın?.[S.dbq.kadr];
  try {
    const n = await API.göndər("/api/debaq/hesabla", { id: S.iş.id, ifadə, kadr: k?.id });
    $("#dbq-netice").textContent = `${ifadə} = ${n.dəyər}` + (n.tip ? `   (${n.tip})` : "");
  } catch (x) { $("#dbq-netice").textContent = `✖ ${x.message}`; }
});

// ══ Vizual dizayner ══════════════════════════════════════════════════
//
// Komponentin vidjet ağacı qutular şəklində. Paletdən element buraxmaq,
// mövcud elementi daşımaq, silmək — hamısı KODU dəyişir (server
// `dizayner.py`), redaktor və önbaxış dərhal yenilənir.

let dzTaymer = 0;

async function dizaynıAçBağla(aç = !S.dizayn) {
  S.dizayn = aç;
  $("#dizayn").hidden = !aç;
  $("#dym-dizayn").classList.toggle("vurğulu", aç);
  if (aç && !S.önbaxışAçıq) await önbaxışıAçBağla(true);
  if (aç) dizaynıYenilə();
}

function dizaynıPlanla(ms = 250) {
  if (!S.dizayn) return;
  clearTimeout(dzTaymer);
  dzTaymer = setTimeout(dizaynıYenilə, ms);
}

async function dizaynıYenilə() {
  if (!S.dizayn) return;
  const yer = $("#dizayn-agac");
  const t = cari();
  if (!t || !/\.(alqor|alq)$/.test(t.yol)) { yer.innerHTML = '<div class="dz-xəta">.alq faylı açın.</div>'; return; }
  try {
    const n = await API.göndər("/api/dizayn/agac", {
      mətn: R.mətn, kursor: R.kursor, komponent: $("#onbaxis-komponent").value || undefined });
    if (n.xəta) { yer.innerHTML = `<div class="dz-xəta">${qaç(n.xəta)}</div>`; return; }
    if (!n.kök) {
      yer.innerHTML = '<div class="dz-xəta">`göstər()` vidjet qaytarmır. Paletdən element əlavə edin — ' +
        "kök `vidjet.sütun` avtomatik yaranacaq.</div>";
      return;
    }
    yer.innerHTML = dzDüyün(n.kök);
  } catch (x) { yer.innerHTML = `<div class="dz-xəta">${qaç(x.message)}</div>`; }
}

function dzDüyün(d) {
  const yol = qaç(JSON.stringify(d.yol));
  const seçili = S.dzSeçili === JSON.stringify(d.yol) ? " seçili" : "";
  const ad = d.ad ? qaç(d.beynəlxalqAd || d.ad) : "ifadə";
  const xülasə = d.xülasə ? `<span class="dz-xülasə">${qaç(d.xülasə)}</span>` : "";
  const sil = d.yol.length ? '<button class="dz-sil" title="Sil (Delete)">✕</button>' : "";
  if (!d.konteyner) {
    return `<div class="dz-element${d.ad ? "" : " kod"}${seçili}" draggable="true" data-yol="${yol}" ` +
      `data-movqe="${d.mövqe}" data-setir="${d.sətir}" title="${qaç(d.ad || "")} — sətir ${d.sətir}">` +
      `<b>${ad}</b>${xülasə}${sil}</div>`;
  }
  const yerlər = [];
  const uşaqlar = d.uşaqlar || [];
  for (let i = 0; i <= uşaqlar.length; i++) {
    yerlər.push(`<div class="dz-yer" data-hedef="${yol}" data-indeks="${i}"></div>`);
    if (i < uşaqlar.length) yerlər.push(dzDüyün(uşaqlar[i]));
  }
  return `<div class="dz-konteyner ${d.istiqamət}${seçili}" data-yol="${yol}" data-movqe="${d.mövqe}" ` +
    `data-setir="${d.sətir}"${d.yol.length ? ' draggable="true"' : ""}>` +
    `<div class="dz-başlıq"><b>${ad}</b><span class="sönük">${qaç(d.ad || "")}</span>${xülasə}${sil}</div>` +
    `<div class="dz-uşaqlar">${yerlər.join("")}</div></div>`;
}

async function dizaynƏməliyyatı(gövdə) {
  const t = cari();
  if (!t) return;
  try {
    const n = await API.göndər("/api/dizayn/emeliyyat", {
      mətn: R.mətn, komponent: $("#onbaxis-komponent").value || undefined, ...gövdə });
    if (n.mətn !== R.mətn) R.mətniƏvəzlə(n.mətn, n.kursor);
    S.dzSeçili = n.yol ? JSON.stringify(n.yol) : null;
    planlaYoxla(150);
    await saxla(t, true);
    await dizaynıYenilə();
    if (n.mesaj) bildir(n.mesaj, "uğur", 2200);
  } catch (x) { xəta(x); }
}

function dzSeç(el) {
  for (const x of $$("#dizayn .seçili")) x.classList.remove("seçili");
  el.classList.add("seçili");
  S.dzSeçili = el.dataset.yol;
  // Kursor elementin ÖZÜNƏ qoyulur — xüsusiyyətlər paneli kursoru izləyir
  const { sətir, sütun } = R.sətirSütun(+el.dataset.movqe);
  R.sətirəKeç(sətir, sütun);
  if (el.dataset.movqe) {
    panelAç("xususiyyet");
    xüsusiyyətləriYüklə(+el.dataset.movqe);
  }
}

$("#dizayn").addEventListener("click", (h) => {
  const sil = h.target.closest(".dz-sil");
  const el = h.target.closest("[data-yol]");
  if (!el) return;
  if (sil) { dizaynƏməliyyatı({ əməliyyat: "sil", yol: JSON.parse(el.dataset.yol) }); return; }
  dzSeç(el);
});

$("#dizayn").addEventListener("keydown", (h) => {
  if ((h.key === "Delete" || h.key === "Backspace") && S.dzSeçili && S.dzSeçili !== "[]") {
    h.preventDefault();
    dizaynƏməliyyatı({ əməliyyat: "sil", yol: JSON.parse(S.dzSeçili) });
  }
});

$("#dizayn").addEventListener("dragstart", (h) => {
  const el = h.target.closest("[data-yol][draggable]");
  if (!el) return;
  h.dataTransfer.setData("application/x-alqor-dizayn", el.dataset.yol);
  h.dataTransfer.effectAllowed = "move";
  el.classList.add("sürüklənir");
});

// Sürükləmə zamanı buraxma yerləri görünür (paletdən də, dizaynerdən də)
document.addEventListener("dragstart", (h) => {
  const növlər = [...(h.dataTransfer?.types || [])];
  if (növlər.includes("application/x-alqor-vidjet") || növlər.includes("application/x-alqor-dizayn")) {
    document.body.classList.add("dz-sürüklə");
  }
});
document.addEventListener("dragend", () => {
  document.body.classList.remove("dz-sürüklə");
  for (const x of $$("#dizayn .sürüklənir, #dizayn .üstündə")) x.classList.remove("sürüklənir", "üstündə");
});

$("#dizayn").addEventListener("dragover", (h) => {
  const y = h.target.closest(".dz-yer");
  const növlər = [...h.dataTransfer.types];
  if (!y || !(növlər.includes("application/x-alqor-vidjet") || növlər.includes("application/x-alqor-dizayn"))) return;
  h.preventDefault();
  h.dataTransfer.dropEffect = növlər.includes("application/x-alqor-dizayn") ? "move" : "copy";
  for (const x of $$("#dizayn .dz-yer.üstündə")) if (x !== y) x.classList.remove("üstündə");
  y.classList.add("üstündə");
});

$("#dizayn").addEventListener("drop", (h) => {
  const y = h.target.closest(".dz-yer");
  if (!y) return;
  h.preventDefault();
  document.body.classList.remove("dz-sürüklə");
  const hədəf = JSON.parse(y.dataset.hedef), indeks = +y.dataset.indeks;
  const yol = h.dataTransfer.getData("application/x-alqor-dizayn");
  const vidjet = h.dataTransfer.getData("application/x-alqor-vidjet");
  if (yol) dizaynƏməliyyatı({ əməliyyat: "köçür", yol: JSON.parse(yol), hədəf, indeks });
  else if (vidjet) dizaynƏməliyyatı({ əməliyyat: "əlavə", vidjet, hədəf, indeks });
});

$("#dym-dizayn").addEventListener("click", () => dizaynıAçBağla());

// ══ Önbaxış ══════════════════════════════════════════════════════════
async function önbaxışıAçBağla(aç = !S.önbaxışAçıq) {
  if (S.önbaxışAçıq === aç) { if (aç) Dok.aç("onbaxis"); return; }
  S.önbaxışAçıq = aç;
  if (!aç && S.dizayn) { S.dizayn = false; $("#dizayn").hidden = true; $("#dym-dizayn").classList.remove("vurğulu"); }
  $("#dym-onbaxis").classList.toggle("vurğulu", aç);
  if (aç) {
    Dok.aç("onbaxis");
    await önbaxışıYenilə();
  } else {
    Dok.gizlət("onbaxis");
    $("#onbaxis-cercive").src = "about:blank";
    API.göndər("/api/onbaxis/dayandir").catch(() => {});
  }
}

/** Önbaxış Studio-nun temasını izləyir (sistem temasını yox). */
var sonÖnbaxışÜnvanı = "";   // `var`: temaQur yüklənmədə daha əvvəl çağırılır
function önbaxışÜnvanı(ünvan, təzələ = false) {
  sonÖnbaxışÜnvanı = ünvan;
  const tema = encodeURIComponent(document.documentElement.dataset.tema || "");
  return `${ünvan}&tema=${tema}` + (təzələ ? `&y=${Date.now()}` : "");
}

async function önbaxışıYenilə(canlı = false) {
  const t = cari();
  const xət = $("#onbaxis-xeta");
  const çərçivə = $("#onbaxis-cercive");
  if (!t) { komponentSeçiminiSıfırla(); xət.hidden = false; xət.textContent = "Fayl açıq deyil."; return; }
  if (!/\bkomponent\s+[\p{L}_]/u.test(R.mətn)) {
    komponentSeçiminiSıfırla();
    xət.hidden = false;
    xət.textContent = "Bu faylda `komponent` yoxdur.\n\nPaletdən elementə iki dəfə klikləyin — " +
      "komponent iskeleti avtomatik yaradılacaq.";
    return;
  }
  if (çirklidir(t) && !(await saxla(t, canlı))) return;
  if (!canlı) { xət.hidden = false; xət.textContent = "Yüklənir…"; }
  try {
    const seçim = $("#onbaxis-komponent").value || undefined;
    const n = await API.göndər("/api/onbaxis", { yol: t.yol, komponent: seçim, canlı });
    if (n.xəta && seçim && /tapılmadı/.test(n.xəta)) {
      // Seçilmiş komponent bu faylda yoxdur — birincisi ilə yenidən
      komponentSeçiminiSıfırla();
      return önbaxışıYenilə(canlı);
    }
    if (n.xəta) {
      if (!seçim) komponentSeçiminiSıfırla();
      xət.hidden = false; xət.textContent = n.xəta;
      if (!canlı) çərçivə.src = "about:blank";
      return;
    }
    const s = $("#onbaxis-komponent");
    s.innerHTML = (n.komponentlər || []).map((k) =>
      `<option${k === n.komponent ? " selected" : ""}>${qaç(k)}</option>`).join("");
    s.hidden = (n.komponentlər || []).length < 2;
    // Canlı yeniləmədə proses və ünvan eynidir — yalnız səhifə yenilənir
    çərçivə.src = önbaxışÜnvanı(n.ünvan, n.yeniləndi);
    xət.hidden = true;
  } catch (x) {
    // Seçilmiş komponent artıq yoxdursa — birincisi ilə yenidən
    if ($("#onbaxis-komponent").value) { komponentSeçiminiSıfırla(); return önbaxışıYenilə(); }
    komponentSeçiminiSıfırla();
    xət.textContent = x.message;
  }
}

/** Komponent seçimini boşaldır və gizlədir (boş açılan siyahı görünməsin). */
function komponentSeçiminiSıfırla() {
  const s = $("#onbaxis-komponent");
  s.innerHTML = "";
  s.hidden = true;
}

$("#onbaxis-komponent").addEventListener("change", () => { önbaxışıYenilə(); dizaynıPlanla(0); });
$("#onbaxis-yenile").addEventListener("click", önbaxışıYenilə);
$("#onbaxis-bagla").addEventListener("click", () => önbaxışıAçBağla(false));

// ══ Axtarış ══════════════════════════════════════════════════════════
function axtarışıAç(əvəzlə = false) {
  $("#axtaris").hidden = false;
  $(".əvəzlə-hissə").hidden = !əvəzlə;
  const seçim = R.mətn.slice(R.ta.selectionStart, R.ta.selectionEnd);
  if (seçim && !seçim.includes("\n")) $("#axtar-sorgu").value = seçim;
  $("#axtar-sorgu").focus();
  $("#axtar-sorgu").select();
  axtarışıYenilə();
}

function axtarışıYenilə() {
  const n = R.axtar($("#axtar-sorgu").value,
    { hərfə: $("#axtar-herf").checked, regex: $("#axtar-regex").checked });
  $("#axtar-say").textContent = n < 0 ? "yanlış ifadə" : $("#axtar-sorgu").value ? `${n} nəticə` : "";
}

function axtarışıBağla() {
  $("#axtaris").hidden = true;
  R.axtar("");
  R.fokus();
}

$("#axtar-sorgu").addEventListener("input", axtarışıYenilə);
$("#axtar-herf").addEventListener("change", axtarışıYenilə);
$("#axtar-regex").addEventListener("change", axtarışıYenilə);
$("#axtar-sorgu").addEventListener("keydown", (h) => {
  if (h.key === "Enter") { h.preventDefault(); R.növbətiNəticə(h.shiftKey); }
  if (h.key === "Escape") axtarışıBağla();
});
$("#evezle-metn").addEventListener("keydown", (h) => {
  if (h.key === "Enter") { h.preventDefault(); R.əvəzlə($("#evezle-metn").value); axtarışıYenilə(); }
  if (h.key === "Escape") axtarışıBağla();
});
$("#axtar-sonra").addEventListener("click", () => R.növbətiNəticə());
$("#axtar-evvel").addEventListener("click", () => R.növbətiNəticə(true));
$("#evezle-bir").addEventListener("click", () => { R.əvəzlə($("#evezle-metn").value); axtarışıYenilə(); });
$("#evezle-hamisi").addEventListener("click", () => {
  const say = R.hamısınıƏvəzlə($("#evezle-metn").value);
  bildir(`${say} yer əvəzləndi`, "uğur");
  axtarışıYenilə();
});
$("#axtar-bagla").addEventListener("click", axtarışıBağla);

// ══ Alətlər ══════════════════════════════════════════════════════════
async function asciiDüzəlt() {
  if (!cari()) return;
  try {
    const n = await API.göndər("/api/ascii-duzelt", { mətn: R.mətn });
    if (n.say) {
      R.mətniƏvəzlə(n.mətn, Math.min(R.kursor, n.mətn.length));
      bildir(`${n.say} açar söz düzəldildi`, "uğur");
    } else bildir("ASCII yazılmış açar söz yoxdur");
  } catch (x) { xəta(x); }
}

async function formatla() {
  if (!cari()) return;
  try {
    const n = await API.göndər("/api/formatla", { mətn: R.mətn });
    R.mətniƏvəzlə(n.mətn, Math.min(R.kursor, n.mətn.length));
    bildir("Formatlandı", "uğur");
  } catch (x) { bildir(x.message, x.kod === 501 ? "" : "xəta", 5000); }
}

$("#dym-yeni").addEventListener("click", () => yeniFayl());
$("#dym-yeni-fayl").addEventListener("click", () => yeniFayl());
$("#dym-yeni-qovluq").addEventListener("click", yeniQovluq);
$("#dym-agac-yenile").addEventListener("click", ağacıYenilə);
$("#dym-saxla").addEventListener("click", () => saxla());
$("#dym-islet").addEventListener("click", işlət);
$("#dym-dayandir").addEventListener("click", dayandır);
$("#dym-onbaxis").addEventListener("click", () => önbaxışıAçBağla());
$("#dym-ascii").addEventListener("click", asciiDüzəlt);
$("#dym-formatla").addEventListener("click", formatla);
$("#dym-tema").addEventListener("click", () =>
  temaQur(document.documentElement.dataset.tema === "qaranlıq" ? "işıqlı" : "qaranlıq"));
$("#ayar-ascii").addEventListener("change", ayarlarıSaxla);
$("#ayar-terkib").addEventListener("change", ayarlarıSaxla);

// Qısayollar, menyular, panellər və başlanğıc — `qur.js`
