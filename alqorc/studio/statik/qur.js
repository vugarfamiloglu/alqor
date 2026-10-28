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
  .qeyd("sazlama", { başlıq: "Sazlama", ikon: "sazlama", el: $("#alt-sazlama"), yer: "alt", zolaq: 12 })
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
const sazlamaDayanıb = () => !!S.dbq;
const ƏQ = (id, ad, ikon, qısayol, işlə, aktiv, əlavə = {}) => Əmrlər.qeyd(id, { ad, ikon, qısayol, işlə, aktiv, ...əlavə });

// Fayl
ƏQ("fayl.yeni", "Yeni fayl", "fayl-yeni", "Alt+N", () => yeniFayl());
ƏQ("fayl.yeniQovluq", "Yeni qovluq", "qovluq-yeni", null, () => yeniQovluq());
ƏQ("fayl.yeniForma", "Yeni forma…", "dizayn", null, () => yeniForma());

// Forma dizayneri (`.forma`)
const formaAçıqdır = () => fdFormadır();
const bazaVar = () => fdFormadır() && Object.keys(FD.cavab?.verilənlər?.bazalar || {}).length > 0;
ƏQ("forma.kodDizayn", "Forma: Kod / Dizayn", "dizayn", "Alt+F12", () => fdKodDizayn(!cari()?.fdKod), formaAçıqdır,
  { seçilib: () => fdFormadır() && !cari().fdKod });
ƏQ("forma.cədvəllər", "Verilənlər: cədvəllər…", "layihə", null, () => fdCədvəlRedaktoru(fdSeçilmişBaza()), bazaVar);
ƏQ("forma.crud", "Verilənlər: cədvəldən forma yarat…", "elementlər", null, () => fdCrudDialoq(fdSeçilmişBaza()), bazaVar);
ƏQ("forma.model", "Verilənlər: model kodu yarat", "fayl-yeni", null, () => fdModelKodu(fdSeçilmişBaza()), bazaVar);
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
// Forma dizaynerində geri al / irəli al dizayner əməliyyatlarına aiddir
ƏQ("redaktə.geriAl", "Geri al", "geri-al", "Ctrl+Z", () => (fdDizayndadır() ? fdGeriAl() : R.geriAl()), varCari);
ƏQ("redaktə.irəliAl", "İrəli al", "irəli-al", ["Ctrl+Y", "Ctrl+Shift+Z"], () => (fdDizayndadır() ? fdGeriAl(true) : R.irəliAl()), varCari);
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
ƏQ("işlət.işlət", "İşlət", "işlət", "F5", () => (S.dbq ? sazlamaƏmri("davam") : işlət()), () => varCari() && (!S.iş || !!S.dbq));
ƏQ("işlət.dayandır", "Dayandır", "dayandır", "Shift+F5", dayandır, işləyir);
ƏQ("işlət.önbaxış", "Komponent önbaxışı", "önbaxış", null, () => önbaxışıAçBağla(true), varCari, { gizli: true });
ƏQ("qur.exe", "Qur: tək .exe (Windows)", "paket", "Ctrl+Shift+B", () => qur("exe"), varCari);
ƏQ("qur.veb", "Qur: veb səhifə (brauzer)", "paket", null, () => qur("veb"), varCari);
ƏQ("qur.js", "Qur: JavaScript (Node.js)", "paket", null, () => qur("js"), varCari);
ƏQ("qur.pyz", "Qur: Alqor paketi (.pyz)", "paket", null, () => qur("pyz"), varCari);
ƏQ("qur.quraşdırıcı", "Qur: Windows quraşdırıcısı", "paket", null, () => qur("quraşdırıcı"), varCari);
ƏQ("qur.yerləşdir", "Qur: vebə yerləşdir (sayt / server)", "paket", null, () => qur("yerləşdir"), varCari);
ƏQ("işlət.çıxışıTəmizlə", "Çıxışı təmizlə", "sil", null, () => { $("#cixis").textContent = ""; });

// Sazlama
ƏQ("sazlama.başla", "Sazlamaya başla", "sazlama", "Ctrl+F5", sazlamaBaşlat, () => varCari() && !S.iş);
ƏQ("sazlama.davam", "Davam et", "işlət", null, () => sazlamaƏmri("davam"), sazlamaDayanıb);
ƏQ("sazlama.növbəti", "Növbəti addım", "addım-üstündən", "F10", () => sazlamaƏmri("növbəti"), sazlamaDayanıb);
ƏQ("sazlama.daxil", "Funksiyaya gir", "addım-daxil", "F11", () => sazlamaƏmri("daxil"), sazlamaDayanıb);
ƏQ("sazlama.çıx", "Funksiyadan çıx", "addım-çıx", "Shift+F11", () => sazlamaƏmri("çıx"), sazlamaDayanıb);
ƏQ("sazlama.fasilə", "Fasilə", "fasilə", null, () => sazlamaƏmri("fasilə"), () => !!S.iş?.sazlama && !S.dbq);
ƏQ("sazlama.dayandır", "Sazlamanı dayandır", "dayandır", null, dayandır, () => !!S.iş?.sazlama);
ƏQ("sazlama.nöqtə", "Dayanma nöqtəsi qoy / götür", "nöqtə", "F9", () => R.nöqtəDəyiş(), varCari);
ƏQ("sazlama.nöqtələriSil", "Bütün dayanma nöqtələrini sil", "sil", null, () => {
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
function haqqındaDüyünü() {
  const k = document.createElement("div");
  k.className = "haqqında";
  const sətir = (etiket, dəyər) => {
    const s = document.createElement("div");
    const e = document.createElement("span"); e.className = "etiket"; e.textContent = etiket;
    s.append(e, dəyər);
    return s;
  };
  const p = document.createElement("p");
  p.textContent = "Alqor — açar sözləri, xəta mesajları və sənədləri Azərbaycan dilində olan " +
    "proqramlaşdırma dilidir. Bir dildə konsol proqramı, veb sayt, desktop tətbiq və " +
    "brauzer kodu yazılır; proqram tək .exe faylına çevrilir və bir əmrlə vebə yerləşdirilir.";
  const sayt = document.createElement("a");
  sayt.href = "https://vuqar.pro/alqor"; sayt.textContent = "vuqar.pro/alqor";
  sayt.target = "_blank"; sayt.rel = "noopener";
  k.append(p,
    sətir("Versiya", `Alqor Studio ${S.məlumat?.versiya || ""}`),
    sətir("Developer", "Vüqar Familoğlu"),
    sətir("Sayt", sayt));
  return k;
}
ƏQ("kömək.haqqında", "Alqor Studio haqqında", "məlumat", null, () =>
  dialoq("Alqor Studio", { düyün: haqqındaDüyünü(), giriş: false, ləğv: false }));

const QISAYOL_QRUPLARI = [
  ["fayl", "Fayl"], ["redaktə", "Redaktə"], ["seçim", "Seçim"], ["görünüş", "Görünüş"],
  ["keç", "Keç"], ["işlət", "İşlət və qur"], ["qur", "İşlət və qur"], ["sazlama", "Sazlama"],
  ["alətlər", "Alətlər"], ["kömək", "Kömək"],
];

function qısayollarıGöstər() {
  const qruplar = new Map();
  for (const ə of Əmrlər.siyahı.values()) {
    if (!ə.qısayol || ə.gizli) continue;
    const ön = ə.id.split(".")[0];
    const ad = (QISAYOL_QRUPLARI.find(([k]) => k === ön) || [, "Digər"])[1];
    if (!qruplar.has(ad)) qruplar.set(ad, []);
    qruplar.get(ad).push(ə);
  }
  const sıra = [...new Set(QISAYOL_QRUPLARI.map(([, a]) => a)), "Digər"];
  const k = document.createElement("div");
  k.className = "qısayol-cədvəli";
  for (const ad of sıra) {
    const əmrlər = qruplar.get(ad);
    if (!əmrlər) continue;
    const b = document.createElement("section");
    const h = document.createElement("h4"); h.textContent = ad;
    b.append(h);
    for (const ə of əmrlər) {
      const s = document.createElement("div"); s.className = "qısayol";
      const a = document.createElement("span"); a.textContent = ə.ad.replace(/…$/, "");
      const d = document.createElement("span"); d.className = "düymələr";
      const q = Əmrlər.göstər(Array.isArray(ə.qısayol) ? ə.qısayol[0] : ə.qısayol);
      q.split(" ").forEach((akkord, i) => {
        if (i) d.append(" ");
        akkord.split("+").forEach((düymə, j) => {
          if (j) d.append("+");
          const kbd = document.createElement("kbd"); kbd.textContent = düymə;
          d.append(kbd);
        });
      });
      s.append(a, d);
      b.append(s);
    }
    k.append(b);
  }
  dialoq("Klaviatura qısayolları", { düyün: k, giriş: false, ləğv: false });
}

// ══ Menyu sətri ══════════════════════════════════════════════════════
const paneller = () => Dok.panellər().filter((p) => p.id !== "onbaxis").map((p) => `görünüş.${p.id}`);
MenyuSətri.qur($("#menyu-setri"), [
  { ad: "Fayl", hərf: "F", elementlər: ["fayl.yeni", "fayl.yeniForma", "fayl.yeniQovluq", "fayl.yeniLayihə", "-", "fayl.aç", "-",
    "fayl.saxla", "fayl.hamısınıSaxla", "-", "fayl.bağla", "fayl.hamısınıBağla", "-", "fayl.yoluKopyala", "fayl.yenilə", "-", "fayl.çıxış"] },
  { ad: "Redaktə", hərf: "R", elementlər: ["redaktə.geriAl", "redaktə.irəliAl", "-", "redaktə.kəs", "redaktə.kopyala",
    "redaktə.yapışdır", "-", "redaktə.axtar", "redaktə.əvəzlə", "redaktə.layihədəAxtar", "-", "redaktə.şərh",
    "redaktə.formatla", "redaktə.ascii"] },
  { ad: "Seçim", hərf: "S", elementlər: ["seçim.hamısı", "seçim.sətir", "-", "seçim.yuxarıDaşı", "seçim.aşağıDaşı",
    "seçim.yuxarıTəkrarla", "seçim.aşağıTəkrarla", "-", "seçim.sətriSil"] },
  { ad: "Görünüş", hərf: "G", elementlər: ["görünüş.palitra", "-",
    { ad: "Panellər", ikon: "layihə", alt: paneller }, "görünüş.önbaxış", "görünüş.dizayn", "forma.kodDizayn", "-",
    "görünüş.yanPanel", "görünüş.altPanel", "görünüş.sağPanel", "görünüş.düzülüşüSıfırla", "-",
    "görünüş.tema", "görünüş.hərfPaneli", "-", "görünüş.böyüt", "görünüş.kiçilt", "görünüş.şriftSıfırla", "-",
    "görünüş.xoşGəldin"] },
  { ad: "Keç", hərf: "K", elementlər: ["fayl.aç", "keç.sətir", "keç.simvol", "-", "keç.təyinat", "keç.istinadlar",
    "keç.adDəyiş", "-", "keç.növbətiProblem", "-", "keç.növbətiNişan", "keç.əvvəlkiNişan"] },
  { ad: "İşlət", hərf: "I", elementlər: ["işlət.işlət", "işlət.dayandır", "-", "görünüş.önbaxış", "görünüş.dizayn", "-",
    "qur.exe", "qur.veb", "qur.js", "qur.pyz", "qur.quraşdırıcı", "qur.yerləşdir", "-",
    "işlət.çıxışıTəmizlə"] },
  { ad: "Sazlama", hərf: "Z", elementlər: ["sazlama.başla", "sazlama.davam", "sazlama.fasilə", "sazlama.dayandır", "-",
    "sazlama.növbəti", "sazlama.daxil", "sazlama.çıx", "-", "sazlama.nöqtə", "sazlama.nöqtələriSil"] },
  { ad: "Alətlər", hərf: "A", elementlər: ["redaktə.formatla", "redaktə.ascii", "-",
    "forma.cədvəllər", "forma.crud", "forma.model", "-", "alətlər.asciiAvto", "alətlər.tərkib", "-",
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
    "sazlama.nöqtə", "-", "işlət.işlət", "görünüş.önbaxış", "-", "görünüş.palitra",
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
    { ad: "Yeni forma…", ikon: "dizayn", işlə: () => { S.seçiliQovluq = qovluq; yeniForma(qovluq); } },
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

// Brauzerin öz menyusu Studio-da heç yerdə açılmır: xüsusi menyusu olmayan
// yerlərdə (xoş gəldin ekranı, panellər, dialoqlar, giriş sahələri) Studio-nun
// menyusu. `window`-da — sahələrin və `document`-in öz işləyicilərindən sonra.
function sahəMenyusu(el) {
  const yazılır = !el.readOnly && !el.disabled;
  const seçilib = () => el.selectionStart !== el.selectionEnd;
  const seçilmiş = () => el.value.slice(el.selectionStart, el.selectionEnd);
  const qoy = (m) => { el.focus(); el.setRangeText(m, el.selectionStart, el.selectionEnd, "end");
    el.dispatchEvent(new Event("input", { bubbles: true })); };
  return [
    { ad: "Kəs", ikon: "kəs", qısayol: "Ctrl+X", aktiv: () => yazılır && seçilib(),
      işlə: () => { mətniKopyala(seçilmiş(), "Kəsildi"); qoy(""); } },
    { ad: "Kopyala", ikon: "kopyala", qısayol: "Ctrl+C", aktiv: seçilib, işlə: () => mətniKopyala(seçilmiş()) },
    { ad: "Yapışdır", ikon: "yapışdır", qısayol: "Ctrl+V", aktiv: () => yazılır,
      işlə: async () => { try { qoy(await navigator.clipboard.readText()); } catch (_) { bildir("Bufer əlçatan deyil — Ctrl+V", "xəta"); } } },
    "-",
    { ad: "Hamısını seç", qısayol: "Ctrl+A", işlə: () => { el.focus(); el.select(); } },
  ];
}

function xoşGəldinMenyusu(h) {
  const ş = h.target.closest("[data-sablon]");
  const f = h.target.closest("[data-ac]");
  return [
    ...(ş ? [{ ad: `«${ş.querySelector("b")?.textContent || ş.dataset.sablon}» layihəsi yarat…`, ikon: "fayl-yeni",
      işlə: () => ş.click() }, "-"] : []),
    ...(f ? [{ ad: "Aç", ikon: "fayl", işlə: () => faylıAç(f.dataset.ac).catch(xəta) },
      { ad: "Aç və işlət", ikon: "işlət", işlə: async () => { await faylıAç(f.dataset.ac); işlət(); } },
      { ad: "Yolu kopyala", ikon: "kopyala", işlə: () => mətniKopyala(f.dataset.ac, "Yol kopyalandı") }, "-"] : []),
    "fayl.yeni", "fayl.yeniForma", "fayl.yeniLayihə", "fayl.yeniQovluq", "-",
    "keç.fayl", "görünüş.palitra", "-",
    { ad: "Kömək", ikon: "kitab", alt: ["kömək.ilk", "kömək.dərslik", "kömək.nümunələr", "kömək.sənədlər", "kömək.qısayollar"] },
    "görünüş.tema", "-", "kömək.haqqında",
  ];
}

window.addEventListener("contextmenu", (h) => {
  if (h.defaultPrevented) return;
  h.preventDefault();
  const el = h.target instanceof Element ? h.target : h.target.parentElement;
  if (!el) return;
  const sahə = el.closest("input:not([type=checkbox]):not([type=radio]):not([type=range]), textarea");
  let elementlər;
  if (sahə && sahə !== R.ta) elementlər = sahəMenyusu(sahə);
  else if (el.closest("#xos-geldin")) elementlər = xoşGəldinMenyusu(h);
  else {
    const seç = getSelection().toString();
    elementlər = [
      ...(seç ? [{ ad: "Kopyala", ikon: "kopyala", qısayol: "Ctrl+C", işlə: () => mətniKopyala(seç) }, "-"] : []),
      "görünüş.palitra", "keç.fayl", "-", "fayl.yeni", "fayl.yeniForma", "-",
      "görünüş.tema", "görünüş.xoşGəldin", "kömək.qısayollar", "-", "kömək.haqqında",
    ];
  }
  KontekstMenyu.göstər(h.clientX, h.clientY, elementlər);
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
