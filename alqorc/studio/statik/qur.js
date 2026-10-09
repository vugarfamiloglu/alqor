/*
 * Alqor Studio — IDE qabığı: panellər (dok), əmrlər, menyu sətri,
 * kontekst menyuları, qısayollar, layihədə axtarış, struktur, naviqasiya.
 * `studio.js`-dən sonra yüklənir və Studio-nu başladır.
 */
"use strict";

// ══ Panellər ═════════════════════════════════════════════════════════
Dok.qeyd("layihe", { başlıq: "Layihə", ikon: "qovluq", el: $("#panel-layihe"), yer: "sol", zolaq: 1, qısayol: "Ctrl+Shift+E" })
  .qeyd("axtar", { başlıq: "Axtarış", ikon: "axtar", el: $("#panel-axtar"), yer: "sol", zolaq: 2, qısayol: "Ctrl+Shift+F" })
  .qeyd("palet", { başlıq: "Elementlər", ikon: "elementlər", el: $("#panel-palet"), yer: "sol", zolaq: 3 })
  .qeyd("xususiyyet", { başlıq: "Xüsusiyyətlər", ikon: "xüsusiyyət", el: $("#panel-xususiyyet"), yer: "sol", zolaq: 4 })
  .qeyd("struktur", { başlıq: "Struktur", ikon: "struktur", el: $("#panel-struktur"), yer: "sol", zolaq: 5 })
  .qeyd("cixis", { başlıq: "Çıxış", ikon: "terminal", el: $("#alt-cixis"), yer: "alt", zolaq: 10 })
  .qeyd("problemler", { başlıq: "Problemlər", ikon: "problem", el: $("#alt-problemler"), yer: "alt", zolaq: 11, qısayol: "Ctrl+Shift+M" })
  .qeyd("debaq", { başlıq: "Debaq", ikon: "debaq", el: $("#alt-debaq"), yer: "alt", zolaq: 12 })
  .qeyd("onbaxis", { başlıq: "Önbaxış", ikon: "önbaxış", el: $("#onbaxis-panel"), yer: "sağ", zolaq: 13,
    görünür: false, bağlanır: true, qısayol: "F6" });

Dok.on("aktiv", (id) => {
  if (id === "xususiyyet") xüsusiyyətləriYüklə();
  if (id === "struktur") strukturuYenilə();
  if (id === "palet") setTimeout(() => $("#palet-axtar").focus(), 0);
  if (id === "axtar") setTimeout(() => { $("#lay-axtar").focus(); $("#lay-axtar").select(); }, 0);
});
Dok.on("gizləndi", (id) => { if (id === "onbaxis" && S.önbaxışAçıq) önbaxışıAçBağla(false); });
Dok.on("köçdü", (id) => {
  // iframe DOM-da yer dəyişəndə özü yenidən yüklənir — ünvanı təzələyirik
  if (id === "onbaxis" && S.önbaxışAçıq) setTimeout(() => önbaxışıYenilə(), 50);
});

// ══ İkonlar (alət sətri, panel düymələri) ════════════════════════════
for (const b of $$("[data-ikon]")) b.insertAdjacentHTML("afterbegin", İkon(b.dataset.ikon));
$("#dym-palitra .pd-ikon").innerHTML = İkon("axtar", 14);

// ══ Köməkçi əməllər ══════════════════════════════════════════════════
const alqFaylıdır = (t = cari()) => !!t && /\.(alqor|alq)$/.test(t.yol);

async function hamısınıSaxla() {
  let n = 0;
  for (const t of S.tablar) if (çirklidir(t) && (await saxla(t, true))) n++;
  bildir(n ? `${n} fayl saxlanıldı` : "Saxlanılmamış fayl yoxdur", n ? "uğur" : "", 1800);
}

async function hamısınıBağla(istisna = null) {
  for (const t of [...S.tablar]) if (t.yol !== istisna) await tabıBağla(t.yol);
}

async function sağdakılarıBağla(yol) {
  const i = S.tablar.findIndex((t) => t.yol === yol);
  for (const t of S.tablar.slice(i + 1)) await tabıBağla(t.yol);
}

async function mətniKopyala(m, mesaj = "Kopyalandı") {
  try { await navigator.clipboard.writeText(m); bildir(mesaj, "", 1400); }
  catch (_) { bildir("Bufer əlçatan deyil", "xəta"); }
}

function redaktorƏmri(ad) {
  R.fokus();
  if (ad === "yapışdır") {
    navigator.clipboard?.readText?.().then((m) => R.daxilEt(m))
      .catch(() => bildir("Yapışdırmaq üçün Ctrl+V istifadə edin", "", 2400));
    return;
  }
  document.execCommand(ad === "kəs" ? "cut" : "copy");
}

function şriftÖlçüsü(f) {
  const kök = document.documentElement;
  const indi = parseFloat(getComputedStyle(kök).getPropertyValue("--şrift-ölçü")) || 13.5;
  const yeni = f === 0 ? 13.5 : Math.max(9, Math.min(28, indi + f));
  kök.style.setProperty("--şrift-ölçü", `${yeni}px`);
  const ö = yaddaş("ölçülər") || {};
  ö["--şrift-ölçü"] = `${yeni}px`;
  yaddaş("ölçülər", ö);
  R.yenidənÖlç();
}

async function sətrəKeçDialoq() {
  if (!cari()) return;
  const { sətir } = R.sətirSütun();
  const c = await dialoq("Sətrə keç", { mətn: `Sətir nömrəsi (cari: ${sətir})`, standart: String(sətir) });
  const n = parseInt(c, 10);
  if (n) R.sətirəKeç(n);
}

// ── Naviqasiya (alqorls) ─────────────────────────────────────────────
async function yeraKeç(yol, aralıq) {
  if (cari()?.yol !== yol) await faylıAç(yol);
  R.sətirəKeç(aralıq.start.line + 1, aralıq.start.character + 1,
    aralıq.end.line === aralıq.start.line ? aralıq.end.character - aralıq.start.character : 0);
}

async function təyinataKeç() {
  if (!alqFaylıdır()) return;
  const n = await dilSorğusu("teyinat", R.kursor).catch(xəta);
  if (!n?.length) { bildir(`"${R.kursordakıSöz()}" üçün təyinat tapılmadı`); return; }
  await yeraKeç(n[0].yol, n[0].aralıq);
}

async function istinadlarıGöstər() {
  if (!alqFaylıdır()) return;
  const söz = R.kursordakıSöz();
  const n = await dilSorğusu("istinadlar", R.kursor).catch(xəta);
  if (!n?.length) { bildir(`"${söz}" üçün istinad tapılmadı`); return; }
  const fayllar = {};
  for (const x of n) {
    (fayllar[x.yol] ||= []).push(x);
  }
  const mətnlər = {};
  for (const yol of Object.keys(fayllar)) {
    const t = S.tablar.find((x) => x.yol === yol);
    mətnlər[yol] = t ? (t.yol === S.aktiv ? R.mətn : t.v.mətn)
      : (await API.göndər("/api/fayl/oxu", { yol }).catch(() => ({ mətn: "" }))).mətn;
  }
  const nəticə = Object.entries(fayllar).map(([yol, x]) => ({
    yol, sətirlər: x.map((r) => {
      const s = mətnlər[yol].split("\n")[r.aralıq.start.line] || "";
      return { no: r.aralıq.start.line + 1, sütun: r.aralıq.start.character + 1,
        uzunluq: Math.max(1, r.aralıq.end.character - r.aralıq.start.character), mətn: s };
    }) }));
  axtarışNəticələriniÇək({ fayllar: nəticə, say: n.length }, `"${söz}" — ${n.length} istinad`);
  Dok.aç("axtar");
}

async function adıDəyiş() {
  if (!alqFaylıdır()) return;
  const köhnə = R.kursordakıSöz();
  if (!köhnə) return;
  const yeni = await dialoq("Adını dəyiş", { mətn: `"${köhnə}" bütün layihədə dəyişdiriləcək`, standart: köhnə });
  if (!yeni || yeni === köhnə) return;
  const t = cari();
  try {
    const { sətir, sütun } = lspMövqe(R.kursor);
    const n = await API.göndər("/api/dil", { metod: "adDəyiş", yol: t.yol, mətn: R.mətn, sətir, sütun, yeniAd: yeni });
    const dəyişən = Object.entries(n.nəticə || {});
    for (const [yol, mətn] of dəyişən) {
      const tab = S.tablar.find((x) => x.yol === yol);
      if (tab && tab.yol === S.aktiv) R.mətniƏvəzlə(mətn, R.kursor);
      else if (tab) tab.v = { ...tab.v, mətn };
      else await API.göndər("/api/fayl/yaz", { yol, mətn });
    }
    tablarıÇək();
    planlaYoxla(100);
    bildir(`"${köhnə}" → "${yeni}": ${dəyişən.length} faylda dəyişdi`, "uğur");
  } catch (x) { xəta(x); }
}

// ── Layihədə axtarış ─────────────────────────────────────────────────
function açıqMətnlər() {
  const n = {};
  for (const t of S.tablar) n[t.yol] = t.yol === S.aktiv ? R.mətn : t.v.mətn;
  return n;
}

function axtarışSorğusu() {
  return { sorğu: $("#lay-axtar").value, hərf: $("#lay-herf").checked, söz: $("#lay-soz").checked,
    regex: $("#lay-regex").checked, filtr: $("#lay-filtr").value.trim(), açıqlar: açıqMətnlər() };
}

let layAxtarTaymer = 0;
async function layihədəAxtar() {
  clearTimeout(layAxtarTaymer);
  if (!$("#lay-axtar").value) { $("#lay-axtar-netice").innerHTML = ""; $("#lay-axtar-say").textContent = ""; return; }
  try {
    const n = await API.göndər("/api/axtar", axtarışSorğusu());
    axtarışNəticələriniÇək(n, `${n.say}${n.kəsilib ? "+" : ""} nəticə, ${n.fayllar.length} fayl`);
  } catch (x) { $("#lay-axtar-say").textContent = x.message; $("#lay-axtar-netice").innerHTML = ""; }
}

function axtarışNəticələriniÇək(n, başlıq) {
  $("#lay-axtar-say").textContent = başlıq;
  $("#lay-axtar-netice").innerHTML = n.fayllar.map((f) =>
    `<div class="ax-qrup"><div class="ax-fayl" data-yol="${qaç(f.yol)}">${İkon("fayl", 14)}` +
    `<span>${qaç(f.yol)}</span><span class="say">${f.sətirlər.length}</span></div>` +
    f.sətirlər.map((s) => {
      const b = s.sütun - 1, e = b + s.uzunluq;
      const önü = s.mətn.slice(Math.max(0, b - 40), b).trimStart();
      return `<div class="ax-sətir" data-yol="${qaç(f.yol)}" data-no="${s.no}" data-sutun="${s.sütun}" ` +
        `data-uz="${s.uzunluq}"><span class="ax-no">${s.no}</span><span>${qaç(önü)}` +
        `<mark>${qaç(s.mətn.slice(b, e))}</mark>${qaç(s.mətn.slice(e, e + 120))}</span></div>`;
    }).join("") + "</div>").join("");
}

$("#lay-axtar-netice").addEventListener("click", async (h) => {
  const s = h.target.closest(".ax-sətir");
  if (s) {
    await faylıAç(s.dataset.yol).catch(xəta);
    R.sətirəKeç(+s.dataset.no, +s.dataset.sutun, +s.dataset.uz);
    return;
  }
  const f = h.target.closest(".ax-fayl");
  if (f) f.parentElement.classList.toggle("yığılıb");
});
$("#axtar-formu").addEventListener("submit", (h) => { h.preventDefault(); layihədəAxtar(); });
for (const id of ["#lay-axtar", "#lay-filtr"]) {
  $(id).addEventListener("input", () => { clearTimeout(layAxtarTaymer); layAxtarTaymer = setTimeout(layihədəAxtar, 300); });
}
for (const id of ["#lay-herf", "#lay-soz", "#lay-regex"]) $(id).addEventListener("change", layihədəAxtar);
$("#lay-evezle-dym").addEventListener("click", async () => {
  const q = axtarışSorğusu();
  if (!q.sorğu) return;
  const ok = await dialoq("Hamısını əvəzlə", { mətn: `"${q.sorğu}" → "${$("#lay-evezle").value}" bütün layihədə əvəzlənsin?`,
    giriş: false, tamam: "Əvəzlə" });
  if (!ok) return;
  try {
    const n = await API.göndər("/api/axtar/evezle", { ...q, əvəz: $("#lay-evezle").value });
    for (const [yol, mətn] of Object.entries(n.fayllar)) {
      const t = S.tablar.find((x) => x.yol === yol);
      if (!t) continue;
      t.saxlanmış = mətn;
      if (t.yol === S.aktiv) R.mətniƏvəzlə(mətn, Math.min(R.kursor, mətn.length));
      else t.v = { ...t.v, mətn };
    }
    tablarıÇək();
    bildir(`${n.say} əvəzləmə, ${Object.keys(n.fayllar).length} fayl`, "uğur");
    layihədəAxtar();
  } catch (x) { xəta(x); }
});

// ── Struktur (sənəd simvolları) ──────────────────────────────────────
const SİMVOL_İŞARƏ = { 2: "M", 5: "S", 6: "m", 7: "x", 8: "x", 9: "q", 10: "E", 11: "İ", 12: "ƒ", 13: "v", 14: "c", 22: "e" };
let strukturMəlumatı = [];
let strukturTaymer = 0;

async function simvollarıAl() {
  if (!alqFaylıdır()) return [];
  try { return (await dilSorğusu("simvollar", 0)) || []; } catch (_) { return []; }
}

async function strukturuYenilə() {
  if (!Dok.açıqdır("struktur")) return;
  strukturMəlumatı = await simvollarıAl();
  strukturuÇək();
}

function strukturuÇək() {
  const süz = $("#struktur-suzgec").value.toLocaleLowerCase("az");
  const gəz = (s, d) => s.map((x) => {
    const uşaq = gəz(x.children || [], d + 1);
    if (süz && !x.name.toLocaleLowerCase("az").includes(süz) && !uşaq) return "";
    return `<div class="st-düyün" style="padding-left:${4 + d * 14}px" data-setir="${x.selectionRange.start.line + 1}" ` +
      `data-sutun="${x.selectionRange.start.character + 1}"><span class="st-növ st-n${x.kind}">${SİMVOL_İŞARƏ[x.kind] || "•"}</span>` +
      `<span>${qaç(x.name)}</span><span class="sönük">${qaç(x.detail || "")}</span></div>` + uşaq;
  }).join("");
  $("#struktur").innerHTML = alqFaylıdır()
    ? (gəz(strukturMəlumatı, 0) || '<p class="ipucu-mətni">Simvol yoxdur.</p>')
    : '<p class="ipucu-mətni">.alq faylı açın.</p>';
}

$("#struktur").addEventListener("click", (h) => {
  const d = h.target.closest("[data-setir]");
  if (d) R.sətirəKeç(+d.dataset.setir, +d.dataset.sutun);
});
$("#struktur-suzgec").addEventListener("input", strukturuÇək);
R.on("dəyişdi", () => { clearTimeout(strukturTaymer); strukturTaymer = setTimeout(strukturuYenilə, 700); });

$("#dym-agac-yigis").addEventListener("click", () => { yaddaş("açıqQovluqlar", []); ağacıYenilə(); });
$("#onbaxis-dizayn").addEventListener("click", () => dizaynıAçBağla());
$("#dym-palitra").addEventListener("click", () => Palitra.aç(">"));

// ══ Əmrlər ═══════════════════════════════════════════════════════════
const varCari = () => !!cari();
const işləyir = () => !!S.iş;
const debaqDayanıb = () => !!S.dbq;
const ƏQ = (id, ad, ikon, qısayol, işlə, aktiv, əlavə = {}) => Əmrlər.qeyd(id, { ad, ikon, qısayol, işlə, aktiv, ...əlavə });

// Fayl
ƏQ("fayl.yeni", "Yeni fayl", "fayl-yeni", "Alt+N", () => yeniFayl());
ƏQ("fayl.yeniQovluq", "Yeni qovluq", "qovluq-yeni", null, () => yeniQovluq());
ƏQ("fayl.yeniLayihə", "Yeni layihə…", "layihə", null, () => { hamısınıBağla().then(() => xoşGəldin()); });
ƏQ("fayl.aç", "Fayla keç…", "keç-fayl", "Ctrl+P", () => Palitra.aç(""));
ƏQ("fayl.saxla", "Saxla", "saxla", "Ctrl+S", () => saxla(), varCari);
ƏQ("fayl.hamısınıSaxla", "Hamısını saxla", "saxla-hamısı", "Ctrl+Alt+S", hamısınıSaxla, () => S.tablar.some(çirklidir));
ƏQ("fayl.bağla", "Nişanı bağla", "bağla", "Alt+W", () => tabıBağla(S.aktiv), varCari);
ƏQ("fayl.hamısınıBağla", "Bütün nişanları bağla", null, null, () => hamısınıBağla(), () => S.tablar.length > 0);
ƏQ("fayl.yoluKopyala", "Yolu kopyala", "kopyala", null, () => mətniKopyala(S.aktiv, "Yol kopyalandı"), varCari);
ƏQ("fayl.yenilə", "Layihə ağacını yenilə", "yenilə", null, () => ağacıYenilə());
ƏQ("fayl.çıxış", "Studio-dan çıx", "çıxış", null, async () => {
  if (S.tablar.some(çirklidir) && !(await dialoq("Saxlanmamış fayllar var", { mətn: "Çıxılsın?", giriş: false, tamam: "Çıx" }))) return;
  await API.göndər("/api/bagla").catch(() => {});
  window.close();
});

// Redaktə
ƏQ("redaktə.geriAl", "Geri al", "geri-al", "Ctrl+Z", () => R.geriAl(), varCari);
ƏQ("redaktə.irəliAl", "İrəli al", "irəli-al", ["Ctrl+Y", "Ctrl+Shift+Z"], () => R.irəliAl(), varCari);
ƏQ("redaktə.kəs", "Kəs", "kəs", "Ctrl+X", () => redaktorƏmri("kəs"), varCari, { yalnızGöstər: true });
ƏQ("redaktə.kopyala", "Kopyala", "kopyala", "Ctrl+C", () => redaktorƏmri("kopyala"), varCari, { yalnızGöstər: true });
ƏQ("redaktə.yapışdır", "Yapışdır", "yapışdır", "Ctrl+V", () => redaktorƏmri("yapışdır"), varCari, { yalnızGöstər: true });
ƏQ("redaktə.axtar", "Axtar", "axtar", "Ctrl+F", () => axtarışıAç(false), varCari);
ƏQ("redaktə.əvəzlə", "Əvəzlə", "əvəzlə", "Ctrl+H", () => axtarışıAç(true), varCari);
ƏQ("redaktə.layihədəAxtar", "Layihədə axtar", "axtar", "Ctrl+Shift+F", () => Dok.aç("axtar", { fokus: true }));
ƏQ("redaktə.şərh", "Şərh et / aç", "şərh", "Ctrl+/", () => R.şərhlə(), varCari);
ƏQ("redaktə.formatla", "Sənədi formatla", "formatla", "Shift+Alt+F", () => formatla(), varCari);
ƏQ("redaktə.ascii", "ASCII açar sözləri düzəlt", "ascii", null, () => asciiDüzəlt(), varCari);

// Seçim
ƏQ("seçim.hamısı", "Hamısını seç", "seç", "Ctrl+A", () => R.hamısınıSeç(), varCari, { yalnızGöstər: true });
ƏQ("seçim.sətir", "Sətri seç", "seç", "Ctrl+L", () => R.sətriSeç(), varCari);
ƏQ("seçim.yuxarıDaşı", "Sətri yuxarı daşı", "sətir-yuxarı", "Alt+Up", () => R.sətriDaşı(-1), varCari);
ƏQ("seçim.aşağıDaşı", "Sətri aşağı daşı", "sətir-aşağı", "Alt+Down", () => R.sətriDaşı(1), varCari);
ƏQ("seçim.yuxarıTəkrarla", "Sətri yuxarı təkrarla", "təkrarla", "Shift+Alt+Up", () => R.sətriTəkrarla(-1), varCari);
ƏQ("seçim.aşağıTəkrarla", "Sətri aşağı təkrarla", "təkrarla", "Shift+Alt+Down", () => R.sətriTəkrarla(1), varCari);
ƏQ("seçim.sətriSil", "Sətri sil", "sil", "Ctrl+Shift+K", () => R.sətriSil(), varCari);

// Görünüş
ƏQ("görünüş.palitra", "Əmr palitrası…", "palitra", "Ctrl+Shift+P", () => Palitra.aç(">"));
for (const p of Dok.panellər()) {
  if (p.id === "onbaxis") continue;
  ƏQ(`görünüş.${p.id}`, p.başlıq, p.ikon, p.qısayol || null, () => Dok.aç(p.id, { fokus: true }), null,
    { seçilib: () => Dok.açıqdır(p.id), qrup: "panel" });
}
ƏQ("görünüş.önbaxış", "Önbaxış", "önbaxış", "F6", () => önbaxışıAçBağla(), null, { seçilib: () => S.önbaxışAçıq });
ƏQ("görünüş.dizayn", "Vizual dizayner", "dizayn", "F7", () => dizaynıAçBağla(), null, { seçilib: () => S.dizayn });
ƏQ("görünüş.yanPanel", "Yan panel", "yan-panel", "Ctrl+B", () => Dok.zonanıDəyiş("sol"), null, { seçilib: () => Dok.zonaAçıqdır("sol") });
ƏQ("görünüş.altPanel", "Alt panel", "alt-panel", "Ctrl+J", () => Dok.zonanıDəyiş("alt"), null, { seçilib: () => Dok.zonaAçıqdır("alt") });
ƏQ("görünüş.sağPanel", "Sağ panel", "sağ-panel", "Ctrl+Alt+B", () => Dok.zonanıDəyiş("sağ"), null, { seçilib: () => Dok.zonaAçıqdır("sağ") });
ƏQ("görünüş.düzülüşüSıfırla", "Düzülüşü sıfırla", "sıfırla", null, () => Dok.sıfırla());
ƏQ("görünüş.tema", "Qaranlıq tema", "tema", "Ctrl+K Ctrl+T", () =>
  temaQur(document.documentElement.dataset.tema === "qaranlıq" ? "işıqlı" : "qaranlıq"), null,
  { seçilib: () => document.documentElement.dataset.tema === "qaranlıq" });
ƏQ("görünüş.hərfPaneli", "Azərbaycan hərfləri paneli", "klaviatura", null, () => {
  const p = $("#herf-paneli"); p.hidden = !p.hidden; yaddaş("hərfPaneliGizli", p.hidden);
}, null, { seçilib: () => !$("#herf-paneli").hidden });
ƏQ("görünüş.böyüt", "Şrifti böyüt", "böyüt", "Ctrl+=", () => şriftÖlçüsü(1));
ƏQ("görünüş.kiçilt", "Şrifti kiçilt", "kiçilt", "Ctrl+-", () => şriftÖlçüsü(-1));
ƏQ("görünüş.şriftSıfırla", "Şrift ölçüsünü sıfırla", null, "Ctrl+0", () => şriftÖlçüsü(0));
ƏQ("görünüş.xoşGəldin", "Xoş gəldin ekranı", "ev", null, () => hamısınıBağla());

// Keç
ƏQ("keç.fayl", "Fayla keç…", "keç-fayl", null, () => Palitra.aç(""), null, { gizli: true });
ƏQ("keç.sətir", "Sətrə keç…", "keç-sətir", "Ctrl+G", sətrəKeçDialoq, varCari);
ƏQ("keç.simvol", "Simvola keç…", "struktur", "Ctrl+Shift+O", () => Palitra.aç("@"), alqFaylıdır);
ƏQ("keç.təyinat", "Təyinata keç", "təyinat", "F12", təyinataKeç, alqFaylıdır);
ƏQ("keç.istinadlar", "Bütün istinadlar", "istinad", "Shift+F12", istinadlarıGöstər, alqFaylıdır);
ƏQ("keç.adDəyiş", "Adını dəyiş (layihə üzrə)", "ad-dəyiş", "F2", adıDəyiş, alqFaylıdır);
ƏQ("keç.növbətiProblem", "Növbəti problem", "növbəti", "F8", növbətiProblem, varCari);
ƏQ("keç.əvvəlkiNişan", "Əvvəlki nişan", "əvvəlki", "Ctrl+Shift+Tab", () => nişanaKeç(-1), () => S.tablar.length > 1);
ƏQ("keç.növbətiNişan", "Növbəti nişan", "növbəti", "Ctrl+Tab", () => nişanaKeç(1), () => S.tablar.length > 1);

function nişanaKeç(d) {
  const i = S.tablar.findIndex((t) => t.yol === S.aktiv);
  const n = S.tablar[(i + d + S.tablar.length) % S.tablar.length];
  if (n) tabaKeç(n.yol);
}

// İşlət
ƏQ("işlət.işlət", "İşlət", "işlət", "F5", () => (S.dbq ? debaqƏmri("davam") : işlət()), () => varCari() && (!S.iş || !!S.dbq));
ƏQ("işlət.dayandır", "Dayandır", "dayandır", "Shift+F5", dayandır, işləyir);
ƏQ("işlət.önbaxış", "Komponent önbaxışı", "önbaxış", null, () => önbaxışıAçBağla(true), varCari, { gizli: true });
ƏQ("işlət.çıxışıTəmizlə", "Çıxışı təmizlə", "sil", null, () => { $("#cixis").textContent = ""; });

// Debaq
ƏQ("debaq.başla", "Debaqa başla", "debaq", "Ctrl+F5", debaqBaşlat, () => varCari() && !S.iş);
ƏQ("debaq.davam", "Davam et", "işlət", null, () => debaqƏmri("davam"), debaqDayanıb);
ƏQ("debaq.növbəti", "Növbəti addım", "addım-üstündən", "F10", () => debaqƏmri("növbəti"), debaqDayanıb);
ƏQ("debaq.daxil", "Funksiyaya gir", "addım-daxil", "F11", () => debaqƏmri("daxil"), debaqDayanıb);
ƏQ("debaq.çıx", "Funksiyadan çıx", "addım-çıx", "Shift+F11", () => debaqƏmri("çıx"), debaqDayanıb);
ƏQ("debaq.fasilə", "Fasilə", "fasilə", null, () => debaqƏmri("fasilə"), () => !!S.iş?.debaq && !S.dbq);
ƏQ("debaq.dayandır", "Debaqı dayandır", "dayandır", null, dayandır, () => !!S.iş?.debaq);
ƏQ("debaq.nöqtə", "Dayanma nöqtəsi qoy / götür", "nöqtə", "F9", () => R.nöqtəDəyiş(), varCari);
ƏQ("debaq.nöqtələriSil", "Bütün dayanma nöqtələrini sil", "sil", null, () => {
  S.nöqtələr = {}; yaddaş("nöqtələr", {}); R.nöqtələriQoy([]); bildir("Dayanma nöqtələri silindi");
}, () => Object.keys(S.nöqtələr).length > 0);

// Alətlər
ƏQ("alətlər.formatla", "Formatla", "formatla", null, () => formatla(), varCari, { gizli: true });
ƏQ("alətlər.asciiAvto", "Yazarkən ASCII → Azərbaycan", "ascii", null, () => {
  $("#ayar-ascii").checked = !$("#ayar-ascii").checked; ayarlarıSaxla();
}, null, { seçilib: () => $("#ayar-ascii").checked });
ƏQ("alətlər.tərkib", "; tərkibi (;e → ə)", "klaviatura", null, () => {
  $("#ayar-terkib").checked = !$("#ayar-terkib").checked; ayarlarıSaxla();
}, null, { seçilib: () => $("#ayar-terkib").checked });

// Kömək
ƏQ("kömək.qısayollar", "Klaviatura qısayolları", "klaviatura", "Ctrl+K Ctrl+S", qısayollarıGöstər);
// Sənədlər Studio-nun öz serverindən gəlir — internet lazım deyil
const sənədAç = (səhifə) => window.open(`/sened/${səhifə}`, "_blank");
ƏQ("kömək.sənədlər", "Alqor sənədləri", "kitab", "F1", () => sənədAç("index.html"));
ƏQ("kömək.ilk", "İlk addımlar", "kitab", null, () => sənədAç("ilk-addimlar.html"));
ƏQ("kömək.dərslik", "Dil dərsliyi", "kitab", null, () => sənədAç("beledci-01-dil-dersliyi.html"));
ƏQ("kömək.arayış", "Tez arayış", "kitab", null, () => sənədAç("beledci-06-tez-arayis.html"));
ƏQ("kömək.əmrlər", "Əmrlər arayışı", "kitab", null, () => sənədAç("emrler.html"));
ƏQ("kömək.xətalar", "Xəta lüğəti", "kitab", null, () => sənədAç("beledci-05-xeta-lugeti.html"));
ƏQ("kömək.nümunələr", "Nümunə proqramlar", "kitab", null, () => sənədAç("numuneler.html"));
ƏQ("kömək.spesifikasiya", "Dil spesifikasiyası", "kitab", null, () => sənədAç("spes-01-leksik-qurulus.html"));
ƏQ("kömək.haqqında", "Alqor Studio haqqında", "məlumat", null, () =>
  dialoq("Alqor Studio", { mətn: `Versiya ${S.məlumat?.versiya || ""} · Azərbaycan dilində proqramlaşdırma dili Alqor üçün IDE.`, giriş: false }));

function qısayollarıGöstər() {
  const n = [...Əmrlər.siyahı.values()].filter((ə) => ə.qısayol && !ə.gizli)
    .map((ə) => `${Əmrlər.göstər(Array.isArray(ə.qısayol) ? ə.qısayol[0] : ə.qısayol).padEnd(18)} ${ə.ad}`);
  dialoq("Klaviatura qısayolları", { mətn: n.join("\n"), giriş: false });
}

// ══ Menyu sətri ══════════════════════════════════════════════════════
const paneller = () => Dok.panellər().filter((p) => p.id !== "onbaxis").map((p) => `görünüş.${p.id}`);
MenyuSətri.qur($("#menyu-setri"), [
  { ad: "Fayl", hərf: "F", elementlər: ["fayl.yeni", "fayl.yeniQovluq", "fayl.yeniLayihə", "-", "fayl.aç", "-",
    "fayl.saxla", "fayl.hamısınıSaxla", "-", "fayl.bağla", "fayl.hamısınıBağla", "-", "fayl.yoluKopyala", "fayl.yenilə", "-", "fayl.çıxış"] },
  { ad: "Redaktə", hərf: "R", elementlər: ["redaktə.geriAl", "redaktə.irəliAl", "-", "redaktə.kəs", "redaktə.kopyala",
    "redaktə.yapışdır", "-", "redaktə.axtar", "redaktə.əvəzlə", "redaktə.layihədəAxtar", "-", "redaktə.şərh",
    "redaktə.formatla", "redaktə.ascii"] },
  { ad: "Seçim", hərf: "S", elementlər: ["seçim.hamısı", "seçim.sətir", "-", "seçim.yuxarıDaşı", "seçim.aşağıDaşı",
    "seçim.yuxarıTəkrarla", "seçim.aşağıTəkrarla", "-", "seçim.sətriSil"] },
  { ad: "Görünüş", hərf: "G", elementlər: ["görünüş.palitra", "-",
    { ad: "Panellər", ikon: "layihə", alt: paneller }, "görünüş.önbaxış", "görünüş.dizayn", "-",
    "görünüş.yanPanel", "görünüş.altPanel", "görünüş.sağPanel", "görünüş.düzülüşüSıfırla", "-",
    "görünüş.tema", "görünüş.hərfPaneli", "-", "görünüş.böyüt", "görünüş.kiçilt", "görünüş.şriftSıfırla", "-",
    "görünüş.xoşGəldin"] },
  { ad: "Keç", hərf: "K", elementlər: ["fayl.aç", "keç.sətir", "keç.simvol", "-", "keç.təyinat", "keç.istinadlar",
    "keç.adDəyiş", "-", "keç.növbətiProblem", "-", "keç.növbətiNişan", "keç.əvvəlkiNişan"] },
  { ad: "İşlət", hərf: "I", elementlər: ["işlət.işlət", "işlət.dayandır", "-", "görünüş.önbaxış", "görünüş.dizayn", "-",
    "işlət.çıxışıTəmizlə"] },
  { ad: "Debaq", hərf: "D", elementlər: ["debaq.başla", "debaq.davam", "debaq.fasilə", "debaq.dayandır", "-",
    "debaq.növbəti", "debaq.daxil", "debaq.çıx", "-", "debaq.nöqtə", "debaq.nöqtələriSil"] },
  { ad: "Alətlər", hərf: "A", elementlər: ["redaktə.formatla", "redaktə.ascii", "-", "alətlər.asciiAvto", "alətlər.tərkib", "-",
    "görünüş.palitra"] },
  { ad: "Kömək", hərf: "M", elementlər: ["kömək.sənədlər", "kömək.ilk", "-", "kömək.dərslik", "kömək.arayış", "kömək.əmrlər", "kömək.xətalar", "kömək.nümunələr", "kömək.spesifikasiya", "-", "kömək.qısayollar", "kömək.haqqında"] },
]);

// ══ Əmr palitrasının mənbələri ═══════════════════════════════════════
Palitra.mənbələr.fayllar = () => bütünFayllar();
Palitra.mənbələr.faylıAç = (y) => faylıAç(y).catch(xəta);
Palitra.mənbələr.sətrəKeç = (n) => R.sətirəKeç(n);
Palitra.mənbələr.simvollar = async () => {
  const düz = [];
  const gəz = (s, kont) => {
    for (const x of s) {
      düz.push({ ad: x.name, əlavə: kont || x.detail || "", ikon: "struktur",
        işlə: () => R.sətirəKeç(x.selectionRange.start.line + 1, x.selectionRange.start.character + 1) });
      gəz(x.children || [], x.name);
    }
  };
  gəz(await simvollarıAl(), "");
  return düz;
};

// ══ Kontekst menyuları ═══════════════════════════════════════════════
R.ta.addEventListener("contextmenu", (h) => {
  if (!cari()) return;
  h.preventDefault();
  // Sağ klik seçimin xaricindədirsə kursoru oraya qoy
  const k = R.mövqeNöqtədən(h.clientX, h.clientY);
  if (k < R.ta.selectionStart || k > R.ta.selectionEnd) R.ta.setSelectionRange(k, k);
  const alq = alqFaylıdır();
  KontekstMenyu.göstər(h.clientX, h.clientY, [
    ...(alq ? ["keç.təyinat", "keç.istinadlar", "keç.adDəyiş", "-"] : []),
    "redaktə.kəs", "redaktə.kopyala", "redaktə.yapışdır", "-",
    "seçim.hamısı", "redaktə.şərh", "redaktə.formatla", "-",
    { ad: "Sətir", ikon: "struktur", alt: ["seçim.yuxarıDaşı", "seçim.aşağıDaşı", "seçim.aşağıTəkrarla", "seçim.sətriSil"] },
    "debaq.nöqtə", "-", "işlət.işlət", "görünüş.önbaxış", "-", "görünüş.palitra",
  ]);
});

$("#agac").addEventListener("contextmenu", (h) => {
  h.preventDefault();
  const d = h.target.closest(".düyün");
  const yol = d?.dataset.yol || "";
  const qovluq = !d ? "" : d.dataset.nov === "qovluq" ? yol : (yol.includes("/") ? yol.slice(0, yol.lastIndexOf("/")) : "");
  const fayl = d && d.dataset.nov === "fayl";
  KontekstMenyu.göstər(h.clientX, h.clientY, [
    ...(fayl ? [{ ad: "Aç", ikon: "fayl", işlə: () => faylıAç(yol).catch(xəta) },
      ...(/\.(alqor|alq)$/.test(yol) ? [{ ad: "Aç və işlət", ikon: "işlət", işlə: async () => { await faylıAç(yol); işlət(); } }] : []),
      "-"] : []),
    { ad: "Yeni fayl", ikon: "fayl-yeni", işlə: () => { S.seçiliQovluq = qovluq; yeniFayl(qovluq); } },
    { ad: "Yeni qovluq", ikon: "qovluq-yeni", işlə: () => { S.seçiliQovluq = qovluq; yeniQovluq(); } },
    ...(d ? ["-",
      { ad: "Adını dəyiş", ikon: "ad-dəyiş", işlə: () => adınıDəyiş(yol) },
      { ad: "Sil", ikon: "sil", işlə: () => faylıSil(yol, d.dataset.nov) },
      "-",
      { ad: "Yolu kopyala", ikon: "kopyala", işlə: () => mətniKopyala(yol, "Yol kopyalandı") },
      { ad: "Adı kopyala", ikon: "kopyala", işlə: () => mətniKopyala(yol.split("/").pop(), "Ad kopyalandı") }] : []),
    "-", "fayl.yenilə",
  ]);
});

$("#tablar").addEventListener("contextmenu", (h) => {
  const t = h.target.closest(".tab");
  if (!t) return;
  h.preventDefault();
  const yol = t.dataset.yol;
  KontekstMenyu.göstər(h.clientX, h.clientY, [
    { ad: "Bağla", ikon: "bağla", qısayol: "Alt+W", işlə: () => tabıBağla(yol) },
    { ad: "Digərlərini bağla", işlə: () => hamısınıBağla(yol), aktiv: () => S.tablar.length > 1 },
    { ad: "Sağdakıları bağla", işlə: () => sağdakılarıBağla(yol), aktiv: () => S.tablar.at(-1)?.yol !== yol },
    { ad: "Hamısını bağla", işlə: () => hamısınıBağla() },
    "-",
    { ad: "Saxla", ikon: "saxla", işlə: () => saxla(S.tablar.find((x) => x.yol === yol)) },
    { ad: "Yolu kopyala", ikon: "kopyala", işlə: () => mətniKopyala(yol, "Yol kopyalandı") },
    { ad: "Ağacda göstər", ikon: "qovluq", işlə: () => ağacdaGöstər(yol) },
  ]);
});

function ağacdaGöstər(yol) {
  const açıq = new Set(yaddaş("açıqQovluqlar") || []);
  const h = yol.split("/");
  for (let i = 1; i < h.length; i++) açıq.add(h.slice(0, i).join("/"));
  yaddaş("açıqQovluqlar", [...açıq]);
  Dok.aç("layihe");
  ağacıYenilə().then(() => $(`.düyün[data-yol="${CSS.escape(yol)}"]`)?.scrollIntoView({ block: "center" }));
}

$("#dizayn").addEventListener("contextmenu", (h) => {
  const el = h.target.closest("[data-yol]");
  if (!el) return;
  h.preventDefault();
  dzSeç(el);
  const yol = JSON.parse(el.dataset.yol);
  const kök = yol.length === 0;
  const qardaş = (d) => {
    const ana = yol.slice(0, -1), i = yol.at(-1);
    return () => dizaynƏməliyyatı({ əməliyyat: "köçür", yol, hədəf: ana, indeks: d < 0 ? i - 1 : i + 2 });
  };
  KontekstMenyu.göstər(h.clientX, h.clientY, [
    { ad: "Koda keç", ikon: "keç-sətir", işlə: () => { R.fokus(); } },
    { ad: "Xüsusiyyətlər", ikon: "xüsusiyyət", işlə: () => Dok.aç("xususiyyet") },
    "-",
    { ad: "Yuxarı daşı", ikon: "sətir-yuxarı", aktiv: () => !kök && yol.at(-1) > 0, işlə: qardaş(-1) },
    { ad: "Aşağı daşı", ikon: "sətir-aşağı", aktiv: () => !kök, işlə: qardaş(1) },
    "-",
    { ad: "Sil", ikon: "sil", qısayol: "Delete", aktiv: () => !kök,
      işlə: () => dizaynƏməliyyatı({ əməliyyat: "sil", yol }) },
  ]);
});

$("#palet").addEventListener("contextmenu", (h) => {
  const v = h.target.closest("[data-vidjet]");
  if (!v) return;
  h.preventDefault();
  const ad = v.dataset.vidjet;
  KontekstMenyu.göstər(h.clientX, h.clientY, [
    { ad: "İşləyən kodla əlavə et", ikon: "elementlər", işlə: () => vidjetiƏlavəEt(ad) },
    { ad: "Kursora nümunə qoy", ikon: "fayl", işlə: () => nümunəniQoy(ad) },
    { ad: "Adı kopyala", ikon: "kopyala", işlə: () => mətniKopyala(`vidjet.${ad}`) },
  ]);
});

$("#cixis").addEventListener("contextmenu", (h) => {
  h.preventDefault();
  const seç = getSelection().toString();
  KontekstMenyu.göstər(h.clientX, h.clientY, [
    { ad: "Kopyala", ikon: "kopyala", aktiv: () => !!seç, işlə: () => mətniKopyala(seç) },
    { ad: "Hamısını kopyala", ikon: "kopyala", işlə: () => mətniKopyala($("#cixis").textContent) },
    "-", "işlət.çıxışıTəmizlə",
  ]);
});

// ══ Klaviatura ═══════════════════════════════════════════════════════
document.addEventListener("keydown", (h) => {
  if (h.key === "Alt") document.body.classList.add("alt-basılıb");
  if (Menyu.düymə(h)) return;
  if (Palitra.açıqdır()) return;
  if (MenyuSətri.hərflə(h)) return;
}, true);
document.addEventListener("keyup", (h) => { if (h.key === "Alt") document.body.classList.remove("alt-basılıb"); });
window.addEventListener("blur", () => document.body.classList.remove("alt-basılıb"));

let akkordİlk = null, akkordTaymer = 0;
document.addEventListener("keydown", (h) => {
  if (h.defaultPrevented) return;                  // redaktor özü işlədib
  if ($("#dialoq").open) return;
  // İki addımlı qısayollar: Ctrl+K Ctrl+T
  if (akkordİlk) {
    const q = `${akkordİlk} ${[(h.ctrlKey || h.metaKey) && "Ctrl", h.shiftKey && "Shift",
      /^Key[A-Z]$/.test(h.code) && h.code.slice(3)].filter(Boolean).join("+")}`;
    akkordİlk = null;
    for (const ə of Əmrlər.siyahı.values()) {
      if ([].concat(ə.qısayol || []).includes(q)) { h.preventDefault(); Əmrlər.işlət(ə.id); return; }
    }
  }
  if ((h.ctrlKey || h.metaKey) && h.code === "KeyK" && !h.shiftKey && !h.altKey) {
    akkordİlk = "Ctrl+K";
    clearTimeout(akkordTaymer);
    akkordTaymer = setTimeout(() => { akkordİlk = null; }, 1500);
    h.preventDefault();
    return;
  }
  const id = Əmrlər.qısayolla(h);
  if (id && !Əmrlər.al(id).yalnızGöstər) {
    h.preventDefault();
    Əmrlər.işlət(id);
    return;
  }
  if (h.key === "Escape" && !$("#axtaris").hidden) axtarışıBağla();
});

// ══ Başlanğıc ════════════════════════════════════════════════════════
if (yaddaş("hərfPaneliGizli")) $("#herf-paneli").hidden = true;
Dok.qur();
bölücüləriQur();
başla();
