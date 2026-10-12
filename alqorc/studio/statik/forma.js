/*
 * Alqor Studio — `.forma` dizayneri (Delphi üslubu).
 *
 * `.forma` faylı açılanda mətn redaktoru əvəzinə dizayn səthi göstərilir:
 * üstdə komponent paleti (nişanlarla), ortada formanın HƏQİQİ görünüşü
 * (vidjet HTML-i serverdə qurulur, Shadow DOM-da vidjet üslubu ilə),
 * sağda «Struktur» ağacı və «Obyekt inspektoru». Hər dəyişiklik server
 * əməliyyatıdır (`/api/forma/emeliyyat`): model dəyişir, fayl
 * `forma.yaz()` ilə yazılır, cavab yeni mətn + görünüşdür. Alt+F12 —
 * Kod / Dizayn keçidi (mətn redaktoru eyni faylı göstərir).
 *
 *   FD.cavab  — son etibarlı server cavabı {forma, html, metodlar, verilənlər, alq}
 *   FD.seçim  — seçilmiş obyekt adları ([] — formanın özü)
 */
"use strict";

const FD = {
  kataloq: null, yol: null, cavab: null, seçim: [], bufer: null,
  kateqoriya: "form", inspektor: "x", növbə: Promise.resolve(), sakit: false,
  tor: true, aparıcı: null,
};

const fdFormadır = (t = cari()) => !!t && /\.forma$/.test(t.yol);
const fdDizayndadır = () => fdFormadır() && !cari().fdKod;
const ÜFÜQİ_NÖVLƏR = new Set(["sətir", "düyməQrupu", "alətlərPaneli", "avatarQrupu"]);

// Hizalama ikonları (24×24, currentColor)
const FD_İKON = {
  sol: '<path d="M4 3v18"/><rect x="7" y="6" width="10" height="4" rx="1"/><rect x="7" y="14" width="6" height="4" rx="1"/>',
  sağ: '<path d="M20 3v18"/><rect x="7" y="6" width="10" height="4" rx="1"/><rect x="11" y="14" width="6" height="4" rx="1"/>',
  yuxarı: '<path d="M3 4h18"/><rect x="6" y="7" width="4" height="10" rx="1"/><rect x="14" y="7" width="4" height="6" rx="1"/>',
  aşağı: '<path d="M3 20h18"/><rect x="6" y="7" width="4" height="10" rx="1"/><rect x="14" y="11" width="4" height="6" rx="1"/>',
  üfüqiMərkəz: '<path d="M12 3v18"/><rect x="6" y="6" width="12" height="4" rx="1"/><rect x="8" y="14" width="8" height="4" rx="1"/>',
  şaquliMərkəz: '<path d="M3 12h18"/><rect x="6" y="6" width="4" height="12" rx="1"/><rect x="14" y="8" width="4" height="8" rx="1"/>',
  eyniEn: '<rect x="5" y="5" width="14" height="5" rx="1"/><rect x="5" y="14" width="14" height="5" rx="1"/>',
  eyniHündürlük: '<rect x="5" y="5" width="5" height="14" rx="1"/><rect x="14" y="5" width="5" height="14" rx="1"/>',
  eyniÖlçü: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  üfüqiPaylaş: '<rect x="3" y="8" width="4" height="8" rx="1"/><rect x="10" y="8" width="4" height="8" rx="1"/><rect x="17" y="8" width="4" height="8" rx="1"/>',
  şaquliPaylaş: '<rect x="8" y="3" width="8" height="4" rx="1"/><rect x="8" y="10" width="8" height="4" rx="1"/><rect x="8" y="17" width="8" height="4" rx="1"/>',
  kod: '<path d="M8 6l-6 6 6 6M16 6l6 6-6 6"/>',
  dizayn: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 8h18M8 12h8M8 16h5"/>',
  tor: '<path d="M4 4h16v16H4zM4 10h16M4 16h16M10 4v16M16 4v16"/>',
  baza: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  sorğu: '<path d="M3 5h18v14H3zM3 10h18M3 14h18M9 5v14"/>',
  naviqator: '<path d="M4 6v12M20 6v12M14 7l-5 5 5 5"/>',
  sehrbaz: '<path d="M4 20L16 8M14 4l1 2 2 1-2 1-1 2-1-2-2-1 2-1zM19 11l.7 1.3L21 13l-1.3.7L19 15l-.7-1.3L17 13l1.3-.7z"/>',
};
const fdİkon = (ad, ö = 16) => `<svg width="${ö}" height="${ö}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${FD_İKON[ad] || ""}</svg>`;

// ══ DOM ══════════════════════════════════════════════════════════════
(function fdQur() {
  const q = $("#redaktor-qabi");
  q.insertAdjacentHTML("beforeend", `
  <button class="fd-keçid" id="fd-kecid" hidden title="Kod / Dizayn (Alt+F12)"></button>
  <div class="fd" id="fd" hidden tabindex="-1" aria-label="Forma dizayneri">
    <div class="fd-alətlər" role="toolbar">
      <span class="fd-seqment"><button data-fd="kod">${fdİkon("kod", 14)}Kod</button><button data-fd="dizayn" class="aktiv">${fdİkon("dizayn", 14)}Dizayn</button></span>
      <span class="ayırıcı-xətt"></span>
      <button data-fd="geri" title="Geri al (Ctrl+Z)">${İkon("geri-al", 15)}</button>
      <button data-fd="irəli" title="İrəli al (Ctrl+Y)">${İkon("irəli-al", 15)}</button>
      <span class="ayırıcı-xətt"></span>
      <span class="fd-hizala">
        ${["sol", "üfüqiMərkəz", "sağ", "yuxarı", "şaquliMərkəz", "aşağı", "eyniEn", "eyniHündürlük", "eyniÖlçü", "üfüqiPaylaş", "şaquliPaylaş"]
          .map((n) => `<button data-hizala="${n}" title="${{ sol: "Sola düzlə", sağ: "Sağa düzlə", yuxarı: "Yuxarıya düzlə",
            aşağı: "Aşağıya düzlə", üfüqiMərkəz: "Üfüqi mərkəzə", şaquliMərkəz: "Şaquli mərkəzə", eyniEn: "Eyni en",
            eyniHündürlük: "Eyni hündürlük", eyniÖlçü: "Eyni ölçü", üfüqiPaylaş: "Üfüqi bərabər payla",
            şaquliPaylaş: "Şaquli bərabər payla" }[n]} (sərbəst düzülüş, 2+ obyekt)">${fdİkon(n)}</button>`).join("")}
      </span>
      <button data-fd="tor" class="aktiv" title="Tora yapışdır (8 px)">${fdİkon("tor", 15)}</button>
      <span class="ayırıcı-xətt"></span>
      <button data-fd="cədvəllər" title="Verilənlər bazasının cədvəlləri (.sxem)">${fdİkon("baza", 15)}Cədvəllər…</button>
      <button data-fd="crud" title="Cədvəldən forma yarat: Sorğu + siyahı + sahələr + naviqator">${fdİkon("sehrbaz", 15)}Cədvəldən forma…</button>
      <span class="boşluq"></span>
      <span class="fd-ölçü sönük" id="fd-olcu"></span>
    </div>
    <div class="fd-palet">
      <div class="fd-palet-nişanlar" id="fd-palet-nisanlar" role="tablist"></div>
      <div class="fd-palet-elementlər" id="fd-palet"></div>
    </div>
    <div class="fd-iş">
      <div class="fd-səth" id="fd-seth">
        <div class="fd-diaq" id="fd-diaq" hidden></div>
        <div class="fd-pəncərə" id="fd-pencere">
          <div class="fd-pb"><span class="fd-pb-ad" id="fd-baslik"></span><span class="fd-pb-düymələr"><i></i><i></i><i></i></span></div>
          <div class="fd-məzmun" id="fd-mezmun">
            <div class="fd-host" id="fd-host"></div>
            <div class="fd-örtük" id="fd-ortuk"></div>
          </div>
          <div class="fd-pəncərə-tutacaq" id="fd-pencere-tutacaq" title="Formanın ölçüsü (en × hündürlük)"></div>
        </div>
        <div class="fd-görünməz" id="fd-gorunmez" aria-label="Görünməyən komponentlər">
          <span class="fd-gz-başlıq">Görünməyən komponentlər</span><div class="fd-gz-siyahı" id="fd-gz"></div>
        </div>
      </div>
      <div class="bölücü şaquli" id="fd-bolucu"></div>
      <div class="fd-yan" id="fd-yan">
        <section class="fd-struktur"><h4>Struktur</h4><div class="fd-ağac" id="fd-agac" role="tree"></div></section>
        <section class="fd-inspektor">
          <div class="fd-ins-başlıq" id="fd-ins-baslik"></div>
          <div class="fd-ins-nişanlar" role="tablist">
            <button data-ins="x" class="aktiv">Xüsusiyyətlər</button><button data-ins="h">Hadisələr</button>
          </div>
          <div class="fd-ins-gövdə" id="fd-ins"></div>
        </section>
      </div>
    </div>
  </div>`);
  $("#fd-kecid").innerHTML = `${fdİkon("dizayn", 14)}<span>Dizayn</span>`;
  const host = $("#fd-host");
  host.attachShadow({ mode: "open" });
})();

const fdKök = () => $("#fd-host").shadowRoot;

// ══ Server ═══════════════════════════════════════════════════════════
async function fdKataloq() {
  if (!FD.kataloq) FD.kataloq = await API.al("/api/forma/kataloq");
  return FD.kataloq;
}

/** Aktiv tab `.forma`-dırsa dizayneri göstərir, deyilsə gizlədir. */
async function fdTabDəyişdi() {
  const t = cari();
  const forma = fdFormadır(t);
  $("#fd-kecid").hidden = !forma;
  if (!forma) { $("#fd").hidden = true; FD.yol = null; return; }
  const kod = !!t.fdKod;
  $("#fd").hidden = kod;
  fdKeçidiYenilə();
  if (FD.yol !== t.yol) { FD.seçim = []; FD.cavab = null; }
  FD.yol = t.yol;
  t.fdTarix ||= { geri: [], irəli: [] };
  try { await fdKataloq(); } catch (x) { xəta(x); return; }
  if (!FD.palet) fdPaletiQur();
  await fdOxu();
  if (!kod) $("#fd").focus({ preventScroll: true });
}

function fdKeçidiYenilə() {
  const t = cari();
  const kod = !!t?.fdKod;
  $("#fd-kecid").innerHTML = kod ? `${fdİkon("dizayn", 14)}<span>Dizayn</span>` : `${fdİkon("kod", 14)}<span>Kod</span>`;
  $("#fd-kecid").title = kod ? "Dizayna qayıt (Alt+F12)" : "Formanın mətni (Alt+F12)";
  $("#fd-kecid").classList.toggle("kodda", kod);
  for (const b of $$(".fd-seqment button")) b.classList.toggle("aktiv", (b.dataset.fd === "kod") === kod);
}

/** Mətn redaktordakıdır (saxlanmamış ola bilər) — server oxuyur və çəkir. */
async function fdOxu() {
  const t = cari();
  if (!fdFormadır(t)) return;
  try {
    const n = await API.göndər("/api/forma/oxu", { yol: t.yol, mətn: R.mətn });
    if (cari() !== t) return;
    fdCavab(n, false);
  } catch (x) { xəta(x); }
}

function fdDiaqnostika(n) {
  const d = n.diaqnostikalar || [];
  const xəta = d.filter((x) => x.səviyyə === "xəta").length;
  diaqnostikaNəticəsi({ diaqnostikalar: d, xəta, xəbərdarlıq: d.length - xəta, ascii: 0 });
  const b = $("#fd-diaq");
  b.hidden = !!n.forma;
  if (!n.forma) {
    const ilk = d.find((x) => x.səviyyə === "xəta");
    b.innerHTML = `<b>Forma mətnində xəta var</b> — dizayner son düzgün vəziyyəti göstərir. ` +
      (ilk ? `<span>Sətir ${ilk.sətir}: ${qaç(ilk.mesaj)}</span> ` : "") +
      `<button data-fd="kod">Mətnə keç</button>`;
  }
}

function fdCavab(n, mətnYenilə = true) {
  const t = cari();
  fdDiaqnostika(n);
  if (mətnYenilə && n.mətn !== undefined && t) {
    t.saxlanmış = n.mətn;
    if (R.mətn !== n.mətn) { FD.sakit = true; R.mətniƏvəzlə(n.mətn, Math.min(R.kursor, n.mətn.length)); FD.sakit = false; }
    tablarıÇək();
  }
  if (!n.forma) return;
  FD.cavab = n;
  if (n.seçim) FD.seçim = n.seçim;
  const adlar = new Set();
  const gəz = (s) => s.forEach((o) => { adlar.add(o.ad); gəz(o.uşaqlar); });
  gəz(n.forma.obyektlər);
  FD.seçim = FD.seçim.filter((a) => adlar.has(a));
  fdÇək();
}

/** Bir dizayner əməliyyatı — ardıcıl (növbə ilə), geri al tarixçəsi ilə. */
function fdƏməliyyat(əməliyyat, { tarix = true } = {}) {
  FD.növbə = FD.növbə.then(async () => {
    const t = cari();
    if (!fdFormadır(t)) return null;
    const əvvəl = R.mətn;
    try {
      const n = await API.göndər("/api/forma/emeliyyat", { yol: t.yol, mətn: əvvəl, əməliyyat });
      if (tarix && n.mətn !== əvvəl) {
        t.fdTarix.geri.push(əvvəl);
        if (t.fdTarix.geri.length > 200) t.fdTarix.geri.shift();
        t.fdTarix.irəli = [];
      }
      if (cari() === t) fdCavab(n); else t.saxlanmış = n.mətn;
      return n;
    } catch (x) { xəta(x); fdÇək(); return null; }
  });
  return FD.növbə;
}

function fdGeriAl(irəli = false) {
  const t = cari();
  if (!fdFormadır(t)) return;
  const [mənbə, hədəf] = irəli ? [t.fdTarix.irəli, t.fdTarix.geri] : [t.fdTarix.geri, t.fdTarix.irəli];
  const m = mənbə.pop();
  if (m === undefined) { bildir(irəli ? "İrəli alınacaq dəyişiklik yoxdur" : "Geri alınacaq dəyişiklik yoxdur", "", 1400); return; }
  hədəf.push(R.mətn);
  fdƏməliyyat({ növ: "mətn", mətn: m }, { tarix: false });
}

// ══ Model köməkçiləri ════════════════════════════════════════════════
function fdObyektlər() {
  const n = new Map();
  const gəz = (s, ana) => s.forEach((o, i) => { n.set(o.ad, { o, ana, i }); gəz(o.uşaqlar, o.ad); });
  if (FD.cavab?.forma) gəz(FD.cavab.forma.obyektlər, null);
  return n;
}
const fdTap = (ad) => fdObyektlər().get(ad)?.o || null;
const fdNöv = (növ) => FD.kataloq?.növlər?.[növ] || null;
const fdSərbəstdir = (ana) => (ana === null ? FD.cavab?.forma?.xassələr?.düzülüş === "sərbəst" : fdTap(ana)?.növ === "kətan");
const fdİzah = (növ) => fdNöv(növ)?.beynəlxalqAd || növ;

function fdDəyər(v) {
  if (v && typeof v === "object") return v.$ad ?? v.$ifadə ?? "";
  return v;
}

// ══ Çəkmə ════════════════════════════════════════════════════════════
function fdÜslub() {
  let css = (S.kataloq?.üslub || "").replaceAll(":root", ":host");
  const qaranlıq = document.documentElement.dataset.tema === "qaranlıq";
  css = css.replace(/@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(:host\{[^}]*\})\}/, (_, iç) => (qaranlıq ? iç : ""));
  return `${css}
  :host{display:block;min-height:100%;background:var(--v-fon);color:var(--v-mətn);font:14px/1.5 system-ui,"Segoe UI",sans-serif}
  .fd-qab{min-height:100%;height:100%}
  .dz-o{position:relative;min-width:8px;min-height:8px}
  .dz-o *{pointer-events:none}
  .dz-o .dz-o{pointer-events:auto}
  .dz-o.dz-gizli{opacity:.38}
  .dz-o.dz-sürüklənir{opacity:.35}
  .dz-boş{min-height:44px;display:flex;align-items:center;justify-content:center;border:1px dashed color-mix(in srgb,currentColor 35%,transparent);border-radius:6px;font-size:12px;opacity:.6;padding:8px}
  .dz-kətan{outline:1px dashed color-mix(in srgb,currentColor 30%,transparent);min-height:60px;min-width:60px;
    background-image:radial-gradient(color-mix(in srgb,currentColor 18%,transparent) 1px,transparent 1px);background-size:8px 8px}
  .dz-kök[data-serbest]{min-height:100%;background-image:radial-gradient(color-mix(in srgb,currentColor 14%,transparent) 1px,transparent 1px);background-size:8px 8px}
  .dz-xəta{color:#d03238;font:12px monospace;border:1px dashed #d03238;padding:4px 6px;border-radius:4px}
  .v-modal-örtük,.v-yan-panel-örtük{position:relative!important;inset:auto!important}`;
}

function fdÇək() {
  const n = FD.cavab;
  if (!n?.forma) return;
  const f = n.forma;
  const en = +fdDəyər(f.xassələr.en) || 800, hün = +fdDəyər(f.xassələr.hündürlük) || 600;
  const m = $("#fd-mezmun");
  m.style.width = `${en}px`;
  m.style.height = `${hün}px`;
  $("#fd-baslik").textContent = fdDəyər(f.xassələr.başlıq) || f.ad;
  $("#fd-olcu").textContent = `${f.ad} · ${en} × ${hün}${fdSərbəstdir(null) ? " · sərbəst" : ""}`;
  const kök = fdKök();
  kök.innerHTML = `<style>${fdÜslub()}</style><div class="fd-qab">${n.html}</div>`;
  fdGörünməzləriÇək();
  fdAğacıÇək();
  fdİnspektoruÇək();
  fdAlətləriYenilə();
  requestAnimationFrame(fdÖrtüyüÇək);
}

function fdGörünməzləriÇək() {
  const s = (FD.cavab.forma.obyektlər || []).filter((o) => o.görünməz);
  $("#fd-gz").innerHTML = s.length ? s.map((o) =>
    `<div class="fd-gz-element${FD.seçim.includes(o.ad) ? " seçili" : ""}" data-dz="${qaç(o.ad)}" title="${qaç(o.növ)} — iki klik: ${o.növ === "VerilənlərBazası" ? "cədvəllər" : "xüsusiyyətlər"}">` +
    `<span class="fd-gz-ikon">${fdİkon(o.növ === "VerilənlərBazası" ? "baza" : "sorğu", 22)}</span>` +
    `<b>${qaç(o.ad)}</b><small>${qaç(o.növ)}</small></div>`).join("")
    : '<span class="sönük">Yoxdur — «Verilənlər» nişanından VerilənlərBazası və Sorğu atın</span>';
}

/** Seçim çərçivələri və tutacaqlar (işıq DOM-da, kətanın üstündə). */
function fdÖrtüyüÇək() {
  const ö = $("#fd-ortuk");
  if (!FD.cavab || $("#fd").hidden) { ö.innerHTML = ""; return; }
  const m = $("#fd-mezmun");
  const M = m.getBoundingClientRect();
  const kök = fdKök();
  const obyektlər = fdObyektlər();
  let h = "";
  FD.seçim.forEach((ad, i) => {
    const el = kök.querySelector(`[data-dz="${CSS.escape(ad)}"]`);
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = r.left - M.left + m.scrollLeft, y = r.top - M.top + m.scrollTop;
    const sərbəst = fdSərbəstdir(obyektlər.get(ad)?.ana ?? null);
    const tutacaqlar = (sərbəst ? ["nw", "n", "ne", "e", "se", "s", "sw", "w"] : ["e", "se", "s"])
      .map((t) => `<i class="fd-tutacaq" data-t="${t}" data-ad="${qaç(ad)}"></i>`).join("");
    h += `<div class="fd-seçim${i === FD.seçim.length - 1 ? " əsas" : ""}" style="left:${x}px;top:${y}px;width:${r.width}px;height:${r.height}px">` +
      `<span class="fd-seçim-ad">${qaç(ad)}</span>${FD.seçim.length === 1 || i === FD.seçim.length - 1 ? tutacaqlar : ""}</div>`;
  });
  ö.innerHTML = h;
}

function fdAlətləriYenilə() {
  const t = cari();
  const ok = fdHizalanır();
  for (const b of $$("[data-hizala]")) b.disabled = !ok || (/Paylaş$/.test(b.dataset.hizala) && FD.seçim.length < 3);
  $('[data-fd="geri"]').disabled = !t?.fdTarix?.geri.length;
  $('[data-fd="irəli"]').disabled = !t?.fdTarix?.irəli.length;
  $('[data-fd="tor"]').classList.toggle("aktiv", FD.tor);
  const bazalar = Object.keys(FD.cavab?.verilənlər?.bazalar || {});
  $('[data-fd="cədvəllər"]').disabled = !bazalar.length;
  $('[data-fd="crud"]').disabled = !bazalar.length;
}

function fdHizalanır() {
  if (FD.seçim.length < 2) return false;
  const ob = fdObyektlər();
  const ana = ob.get(FD.seçim[0])?.ana ?? null;
  return FD.seçim.every((a) => (ob.get(a)?.ana ?? null) === ana && !ob.get(a)?.o.görünməz) && fdSərbəstdir(ana);
}

// ══ Palet ════════════════════════════════════════════════════════════
function fdPaletiQur() {
  FD.palet = true;
  const k = FD.kataloq;
  $("#fd-palet-nisanlar").innerHTML = k.kateqoriyalar.map((x) =>
    `<button data-kat="${qaç(x.ad)}" role="tab" title="${qaç(x.beynəlxalq)}">${qaç(x.başlıq)}</button>`).join("");
  fdPaletiÇək();
}

function fdPaletiÇək() {
  for (const b of $$("#fd-palet-nisanlar button")) b.classList.toggle("aktiv", b.dataset.kat === FD.kateqoriya);
  const növlər = Object.values(FD.kataloq.növlər).filter((n) => n.kateqoriya === FD.kateqoriya);
  if (FD.kateqoriya === "düzülüş" && !növlər.some((n) => n.ad === "kətan")) növlər.unshift(FD.kataloq.növlər.kətan);
  $("#fd-palet").innerHTML = növlər.map((n) =>
    `<div class="fd-palet-element${n.görünməz ? " görünməz" : ""}" draggable="true" data-fd-vidjet="${qaç(n.ad)}" ` +
    `title="${qaç(n.beynəlxalqAd)} — ${qaç(n.izah)}\nSürüklə və ya iki klik">` +
    `<span class="fd-pe-ikon">${n.görünməz ? fdİkon(n.ad === "Sorğu" ? "sorğu" : "baza", 15) : n.ad === "naviqator" ? fdİkon("naviqator", 15) : (n.konteyner ? "▭" : "◆")}</span>` +
    `<span>${qaç(n.ad)}</span></div>`).join("");
}

$("#fd-palet-nisanlar").addEventListener("click", (h) => {
  const b = h.target.closest("[data-kat]");
  if (!b) return;
  FD.kateqoriya = b.dataset.kat;
  fdPaletiÇək();
});
$("#fd-palet").addEventListener("dragstart", (h) => {
  const v = h.target.closest("[data-fd-vidjet]");
  if (!v) return;
  h.dataTransfer.setData("application/x-alqor-forma", v.dataset.fdVidjet);
  h.dataTransfer.effectAllowed = "copy";
  FD.sürüklənən = v.dataset.fdVidjet;
});
$("#fd-palet").addEventListener("dragend", () => { FD.sürüklənən = null; fdGöstəriciniGizlət(); });
$("#fd-palet").addEventListener("dblclick", (h) => {
  const v = h.target.closest("[data-fd-vidjet]");
  if (!v) return;
  // Seçilmiş konteynerin içinə, yoxdursa formanın sonuna
  const s = FD.seçim.length === 1 ? fdTap(FD.seçim[0]) : null;
  const ana = s?.konteyner ? s.ad : null;
  const x = {};
  if (fdSərbəstdir(ana)) { x.sol = 16; x.yuxarı = 16; }
  fdƏməliyyat({ növ: "əlavə", vidjet: v.dataset.fdVidjet, ana, xassələr: x });
});

// ══ Hədəf (buraxma yeri) ═════════════════════════════════════════════
/**
 * Göstəricinin altındakı konteyner və yer: {ana, indeks, sərbəst, sol, yuxarı, xətt}.
 * `istisna` — sürüklənən obyektlər (öz içinə buraxılmasın).
 */
function fdHədəf(x, y, istisna = new Set()) {
  const kök = fdKök();
  const m = $("#fd-mezmun").getBoundingClientRect();
  if (x < m.left || x > m.right || y < m.top || y > m.bottom) return null;
  const qadağan = (el) => {
    for (let e = el; e; e = e.parentElement?.closest(".dz-o")) if (istisna.has(e.dataset.dz)) return true;
    return false;
  };
  let o = null;
  for (const e of kök.elementsFromPoint(x, y)) {
    const w = e.closest?.(".dz-o");
    if (w && !qadağan(w)) { o = w; break; }
  }
  const kökEl = kök.querySelector(".dz-kök");
  let qab = null, ana = null;
  if (o && o.dataset.konteyner) {
    const r = o.getBoundingClientRect();
    const kənar = 6;
    const kənardadır = y - r.top < kənar || r.bottom - y < kənar;
    if (!kənardadır || o.dataset.serbest) { qab = o; ana = o.dataset.dz; }
  }
  if (!qab) {
    const üst = o ? o.parentElement.closest(".dz-o") : null;
    qab = üst || null;
    ana = üst ? üst.dataset.dz : null;
  }
  const qabEl = qab ? (qab.dataset.serbest ? qab.querySelector(":scope > .dz-kətan") : qab) : kökEl;
  if (!qabEl) return null;
  const R0 = qabEl.getBoundingClientRect();
  if (fdSərbəstdir(ana)) {
    return { ana, sərbəst: true, sol: x - R0.left, yuxarı: y - R0.top, qabRect: R0 };
  }
  // Axın: uşaq qablar (birbaşa)
  const uşaqlar = [...qabEl.querySelectorAll(".dz-o")].filter((e) =>
    (e.parentElement.closest(".dz-o") || null) === (qab || null) && e !== qab);
  const r = uşaqlar.map((e) => e.getBoundingClientRect());
  const üfüqi = r.length >= 2 ? Math.abs(r[1].top - r[0].top) < Math.min(r[0].height, r[1].height) / 2
    : ÜFÜQİ_NÖVLƏR.has(qab?.dataset.nov);
  let indeks = 0;
  r.forEach((q, i) => {
    const əvvəl = üfüqi ? (q.bottom < y || (q.top <= y && q.left + q.width / 2 < x)) : q.top + q.height / 2 < y;
    if (əvvəl) indeks = i + 1;
  });
  // Göstərici xətti
  let xətt;
  if (!r.length) xətt = { x: R0.left + 8, y: R0.top + 8, en: R0.width - 16, hün: 0 };
  else if (üfüqi) {
    const q = r[Math.min(indeks, r.length - 1)];
    const xx = indeks >= r.length ? q.right + 2 : q.left - 3;
    xətt = { x: xx, y: q.top, en: 0, hün: q.height };
  } else {
    const yy = indeks >= r.length ? r[r.length - 1].bottom + 3 : indeks === 0 ? r[0].top - 3
      : (r[indeks - 1].bottom + r[indeks].top) / 2;
    const q = r[Math.min(indeks, r.length - 1)];
    xətt = { x: q.left, y: yy, en: q.width, hün: 0 };
  }
  return { ana, indeks, sərbəst: false, xətt };
}

function fdGöstərici(h) {
  const ö = $("#fd-ortuk");
  ö.querySelector(".fd-yer")?.remove();
  ö.querySelector(".fd-qab-vurğu")?.remove();
  if (!h) return;
  const m = $("#fd-mezmun");
  const M = m.getBoundingClientRect();
  const kök = fdKök();
  const qab = h.ana ? kök.querySelector(`[data-dz="${CSS.escape(h.ana)}"]`) : kök.querySelector(".dz-kök");
  if (qab) {
    const r = qab.getBoundingClientRect();
    ö.insertAdjacentHTML("beforeend", `<div class="fd-qab-vurğu" style="left:${r.left - M.left + m.scrollLeft}px;top:${r.top - M.top + m.scrollTop}px;width:${r.width}px;height:${r.height}px"></div>`);
  }
  if (h.xətt) {
    const x = h.xətt;
    ö.insertAdjacentHTML("beforeend", `<div class="fd-yer${x.hün ? " şaquli" : ""}" style="left:${x.x - M.left + m.scrollLeft}px;top:${x.y - M.top + m.scrollTop}px;width:${Math.max(2, x.en)}px;height:${Math.max(2, x.hün)}px"></div>`);
  }
}
function fdGöstəriciniGizlət() { fdGöstərici(null); $$("#fd-ortuk .fd-bələdçi").forEach((e) => e.remove()); }

const fdTora = (v) => (FD.tor ? Math.round(v / 8) * 8 : Math.round(v));

// Paletdən buraxma (HTML5 DnD)
$("#fd-mezmun").addEventListener("dragover", (h) => {
  if (![...h.dataTransfer.types].includes("application/x-alqor-forma")) return;
  h.preventDefault();
  h.dataTransfer.dropEffect = "copy";
  const n = FD.sürüklənən ? fdNöv(FD.sürüklənən) : null;
  fdGöstərici(n?.görünməz ? null : fdHədəf(h.clientX, h.clientY));
});
$("#fd-mezmun").addEventListener("dragleave", (h) => {
  if (!$("#fd-mezmun").contains(h.relatedTarget)) fdGöstəriciniGizlət();
});
$("#fd-mezmun").addEventListener("drop", (h) => {
  const vidjet = h.dataTransfer.getData("application/x-alqor-forma");
  if (!vidjet) return;
  h.preventDefault();
  fdGöstəriciniGizlət();
  const hd = fdHədəf(h.clientX, h.clientY) || { ana: null };
  const x = {};
  if (hd.sərbəst) { x.sol = Math.max(0, fdTora(hd.sol)); x.yuxarı = Math.max(0, fdTora(hd.yuxarı)); }
  fdƏməliyyat({ növ: "əlavə", vidjet, ana: hd.ana, indeks: hd.indeks ?? null, xassələr: x });
});
// Görünməyənlər zolağına da atmaq olar
$("#fd-gorunmez").addEventListener("dragover", (h) => {
  if ([...h.dataTransfer.types].includes("application/x-alqor-forma")) { h.preventDefault(); h.dataTransfer.dropEffect = "copy"; }
});
$("#fd-gorunmez").addEventListener("drop", (h) => {
  const vidjet = h.dataTransfer.getData("application/x-alqor-forma");
  if (!vidjet) return;
  h.preventDefault();
  fdƏməliyyat({ növ: "əlavə", vidjet, ana: null });
});

// ══ Seçim, daşıma, ölçü ══════════════════════════════════════════════
function fdSeç(adlar, əlavə = false) {
  if (əlavə) {
    const s = new Set(FD.seçim);
    for (const a of adlar) { if (s.has(a)) s.delete(a); else s.add(a); }
    FD.seçim = [...s];
  } else FD.seçim = [...adlar];
  fdÖrtüyüÇək();
  fdGörünməzləriÇək();
  fdAğacıÇək();
  fdİnspektoruÇək();
  fdAlətləriYenilə();
}

function fdObyektNöqtədə(h) {
  for (const e of h.composedPath()) {
    if (e === $("#fd-host")) break;
    if (e.dataset?.dz && e.classList?.contains("dz-o")) return e.dataset.dz;
  }
  return null;
}

$("#fd-mezmun").addEventListener("pointerdown", (h) => {
  if (h.button !== 0) return;
  $("#fd").focus({ preventScroll: true });
  const tut = h.target.closest(".fd-tutacaq");
  if (tut) { h.preventDefault(); fdÖlçüDəyiş(h, tut.dataset.ad, tut.dataset.t); return; }
  const ad = fdObyektNöqtədə(h);
  if (!ad) { fdSeç([]); return; }
  h.preventDefault();
  const çox = h.shiftKey || h.ctrlKey || h.metaKey;
  if (çox) { fdSeç([ad], true); return; }
  if (!FD.seçim.includes(ad)) fdSeç([ad]);
  else if (FD.seçim.at(-1) !== ad) { FD.seçim = [...FD.seçim.filter((x) => x !== ad), ad]; fdSeç(FD.seçim); }
  fdDaşı(h, ad);
});

$("#fd-mezmun").addEventListener("dblclick", (h) => {
  const ad = fdObyektNöqtədə(h);
  if (ad) fdObyektİkiKlik(ad);
});

function fdObyektİkiKlik(ad) {
  const o = fdTap(ad);
  if (!o) return;
  if (o.növ === "VerilənlərBazası") { fdCədvəlRedaktoru(ad); return; }
  const h = fdNöv(o.növ)?.hadisələr?.[0];
  if (h) fdHadisə(ad, h, true);
  else bildir(`${o.növ} obyektinin hadisəsi yoxdur`, "", 1800);
}

/** Obyekti daşımaq: sərbəst düzülüşdə mövqe (tor + bələdçilər), axında yer. */
function fdDaşı(h0, ad) {
  const ob = fdObyektlər();
  const ana = ob.get(ad)?.ana ?? null;
  const adlar = FD.seçim.filter((a) => (ob.get(a)?.ana ?? null) === ana);
  const kök = fdKök();
  const el = (a) => kök.querySelector(`[data-dz="${CSS.escape(a)}"]`);
  const sərbəst = fdSərbəstdir(ana);
  const başlanğıc = new Map(adlar.map((a) => {
    const o = ob.get(a).o;
    const e = el(a);
    return [a, { sol: +fdDəyər(o.xassələr.sol) || e?.offsetLeft || 0, yuxarı: +fdDəyər(o.xassələr.yuxarı) || e?.offsetTop || 0 }];
  }));
  let başladı = false, son = null;
  const istisna = new Set(adlar);
  const hərəkət = (h) => {
    const dx = h.clientX - h0.clientX, dy = h.clientY - h0.clientY;
    if (!başladı && Math.hypot(dx, dy) < 4) return;
    if (!başladı) {
      başladı = true;
      document.body.classList.add("sürüklənir");
      for (const a of adlar) el(a)?.classList.add(sərbəst ? "dz-daşınır" : "dz-sürüklənir");
      if (!sərbəst) for (const a of adlar) { const e = el(a); if (e) e.style.pointerEvents = "none"; }
    }
    if (sərbəst) {
      const qab = fdQabRect(ana);
      const çöldə = qab && (h.clientX < qab.left || h.clientX > qab.right || h.clientY < qab.top || h.clientY > qab.bottom);
      if (çöldə) {
        for (const a of adlar) { const e = el(a); if (e) { e.style.translate = ""; e.style.pointerEvents = "none"; } }
        son = { köçür: fdHədəf(h.clientX, h.clientY, istisna) };
        fdGöstərici(son.köçür);
        return;
      }
      fdGöstəriciniGizlət();
      for (const a of adlar) { const e = el(a); if (e) e.style.pointerEvents = ""; }
      const b = başlanğıc.get(ad);
      let yx = fdTora(b.sol + dx), yy = fdTora(b.yuxarı + dy);
      const bələdçi = fdBələdçilər(ad, ana, yx, yy, istisna);
      yx = bələdçi.sol; yy = bələdçi.yuxarı;
      const fx = yx - b.sol, fy = yy - b.yuxarı;
      for (const a of adlar) { const e = el(a); if (e) e.style.translate = `${fx}px ${fy}px`; }
      son = { fx, fy };
      fdÖrtüyüÇək();
      fdBələdçiləriÇək(bələdçi.xətlər);
    } else {
      son = { köçür: fdHədəf(h.clientX, h.clientY, istisna) };
      fdGöstərici(son.köçür);
    }
  };
  const bit = () => {
    document.removeEventListener("pointermove", hərəkət);
    document.body.classList.remove("sürüklənir");
    fdGöstəriciniGizlət();
    for (const a of adlar) { const e = el(a); if (e) { e.style.pointerEvents = ""; e.classList.remove("dz-sürüklənir", "dz-daşınır"); } }
    if (!başladı || !son) return;
    if (son.köçür) {
      const hd = son.köçür;
      const x = {};
      if (hd.sərbəst) {
        adlar.forEach((a, i) => { x[a] = { sol: Math.max(0, fdTora(hd.sol + i * 16)), yuxarı: Math.max(0, fdTora(hd.yuxarı + i * 16)) }; });
      } else if (sərbəst) {
        for (const a of adlar) x[a] = { sol: null, yuxarı: null };      // axına keçir — mövqe lazım deyil
      }
      fdƏməliyyat({ növ: "köçür", adlar, ana: hd.ana, indeks: hd.indeks ?? null, xassələr: x });
      return;
    }
    const d = {};
    for (const a of adlar) {
      const b = başlanğıc.get(a);
      d[a] = { sol: Math.max(0, Math.round(b.sol + son.fx)), yuxarı: Math.max(0, Math.round(b.yuxarı + son.fy)) };
    }
    if (son.fx || son.fy) fdƏməliyyat({ növ: "xassələr", dəyişikliklər: d });
    else fdÖrtüyüÇək();
  };
  document.addEventListener("pointermove", hərəkət);
  document.addEventListener("pointerup", bit, { once: true });
}

function fdQabRect(ana) {
  const kök = fdKök();
  const e = ana ? kök.querySelector(`[data-dz="${CSS.escape(ana)}"] > .dz-kətan`) : kök.querySelector(".dz-kök");
  return e?.getBoundingClientRect() || null;
}

/** Hizalama bələdçiləri: qonşuların kənarları və mərkəzləri (4 px yaxınlıq). */
function fdBələdçilər(ad, ana, sol, yuxarı, istisna) {
  const kök = fdKök();
  const e = kök.querySelector(`[data-dz="${CSS.escape(ad)}"]`);
  const qab = fdQabRect(ana);
  if (!e || !qab) return { sol, yuxarı, xətlər: [] };
  const en = e.offsetWidth, hün = e.offsetHeight;
  const qonşular = [];
  for (const [a, x] of fdObyektlər()) {
    if (x.ana !== ana || istisna.has(a) || x.o.görünməz) continue;
    const q = kök.querySelector(`[data-dz="${CSS.escape(a)}"]`);
    if (!q) continue;
    const r = q.getBoundingClientRect();
    qonşular.push({ sol: r.left - qab.left, yuxarı: r.top - qab.top, en: r.width, hün: r.height });
  }
  qonşular.push({ sol: 0, yuxarı: 0, en: qab.width, hün: qab.height, qab: true });
  const xətlər = [];
  const yapış = (dəyər, ölçü, ox) => {
    let ən = null;
    for (const q of qonşular) {
      const nöqtələr = q.qab ? [q[ox === "x" ? "en" : "hün"] / 2] : [q[ox === "x" ? "sol" : "yuxarı"],
        q[ox === "x" ? "sol" : "yuxarı"] + q[ox === "x" ? "en" : "hün"] / 2, q[ox === "x" ? "sol" : "yuxarı"] + q[ox === "x" ? "en" : "hün"]];
      for (const n of nöqtələr) {
        for (const [f, k] of [[0, 0], [ölçü / 2, 1], [ölçü, 2]]) {
          const fərq = n - (dəyər + f);
          if (Math.abs(fərq) <= 4 && (!ən || Math.abs(fərq) < Math.abs(ən.fərq))) ən = { fərq, n, k };
        }
      }
    }
    return ən;
  };
  const bx = yapış(sol, en, "x"), by = yapış(yuxarı, hün, "y");
  if (bx) { sol += bx.fərq; xətlər.push({ ox: "x", d: bx.n + qab.left }); }
  if (by) { yuxarı += by.fərq; xətlər.push({ ox: "y", d: by.n + qab.top }); }
  return { sol, yuxarı, xətlər };
}

function fdBələdçiləriÇək(xətlər) {
  const ö = $("#fd-ortuk");
  $$(".fd-bələdçi", ö).forEach((e) => e.remove());
  const m = $("#fd-mezmun");
  const M = m.getBoundingClientRect();
  for (const x of xətlər) {
    ö.insertAdjacentHTML("beforeend", x.ox === "x"
      ? `<div class="fd-bələdçi" style="left:${x.d - M.left + m.scrollLeft}px;top:${m.scrollTop}px;width:1px;height:${m.clientHeight}px"></div>`
      : `<div class="fd-bələdçi" style="left:${m.scrollLeft}px;top:${x.d - M.top + m.scrollTop}px;width:${m.clientWidth}px;height:1px"></div>`);
  }
}

/** Tutacaqla ölçü dəyişmə (en/hündürlük; sərbəstdə sol/yuxarı da). */
function fdÖlçüDəyiş(h0, ad, t) {
  const ob = fdObyektlər();
  const x = ob.get(ad);
  const e = fdKök().querySelector(`[data-dz="${CSS.escape(ad)}"]`);
  if (!x || !e) return;
  const sərbəst = fdSərbəstdir(x.ana);
  const b = { sol: +fdDəyər(x.o.xassələr.sol) || e.offsetLeft, yuxarı: +fdDəyər(x.o.xassələr.yuxarı) || e.offsetTop,
    en: e.offsetWidth, hün: e.offsetHeight };
  let n = { ...b };
  document.body.classList.add("sürüklənir");
  const hərəkət = (h) => {
    const dx = h.clientX - h0.clientX, dy = h.clientY - h0.clientY;
    n = { ...b };
    if (t.includes("e")) n.en = Math.max(16, fdTora(b.en + dx));
    if (t.includes("s")) n.hün = Math.max(12, fdTora(b.hün + dy));
    if (t.includes("w")) { n.sol = fdTora(b.sol + dx); n.en = Math.max(16, b.en + b.sol - n.sol); }
    if (t.includes("n")) { n.yuxarı = fdTora(b.yuxarı + dy); n.hün = Math.max(12, b.hün + b.yuxarı - n.yuxarı); }
    e.style.width = `${n.en}px`;
    e.style.height = `${n.hün}px`;
    if (sərbəst) { e.style.left = `${n.sol}px`; e.style.top = `${n.yuxarı}px`; }
    $("#fd-olcu").textContent = `${ad}: ${n.en} × ${n.hün}`;
    fdÖrtüyüÇək();
  };
  document.addEventListener("pointermove", hərəkət);
  document.addEventListener("pointerup", () => {
    document.removeEventListener("pointermove", hərəkət);
    document.body.classList.remove("sürüklənir");
    const d = {};
    if (n.en !== b.en) d.en = n.en;
    if (n.hün !== b.hün) d.hündürlük = n.hün;
    if (sərbəst && n.sol !== b.sol) d.sol = n.sol;
    if (sərbəst && n.yuxarı !== b.yuxarı) d.yuxarı = n.yuxarı;
    if (Object.keys(d).length) fdƏməliyyat({ növ: "xassələr", dəyişikliklər: { [ad]: d } });
    else fdÇək();
  }, { once: true });
}

// Formanın özünün ölçüsü (pəncərənin sağ-aşağı küncü)
$("#fd-pencere-tutacaq").addEventListener("pointerdown", (h0) => {
  h0.preventDefault();
  const m = $("#fd-mezmun");
  const b = { en: m.offsetWidth, hün: m.offsetHeight };
  let n = { ...b };
  document.body.classList.add("sürüklənir");
  const hərəkət = (h) => {
    n = { en: Math.max(160, fdTora(b.en + h.clientX - h0.clientX)), hün: Math.max(120, fdTora(b.hün + h.clientY - h0.clientY)) };
    m.style.width = `${n.en}px`; m.style.height = `${n.hün}px`;
    $("#fd-olcu").textContent = `${n.en} × ${n.hün}`;
    fdÖrtüyüÇək();
  };
  document.addEventListener("pointermove", hərəkət);
  document.addEventListener("pointerup", () => {
    document.removeEventListener("pointermove", hərəkət);
    document.body.classList.remove("sürüklənir");
    if (n.en !== b.en || n.hün !== b.hün) fdƏməliyyat({ növ: "xassələr", dəyişikliklər: { "": { en: n.en, hündürlük: n.hün } } });
  }, { once: true });
});

$("#fd-mezmun").addEventListener("scroll", () => fdÖrtüyüÇək());
new ResizeObserver(() => fdÖrtüyüÇək()).observe($("#fd-seth"));

// Görünməyən komponentlər zolağı
$("#fd-gz").addEventListener("click", (h) => {
  const e = h.target.closest("[data-dz]");
  if (e) fdSeç([e.dataset.dz], h.shiftKey || h.ctrlKey || h.metaKey);
});
$("#fd-gz").addEventListener("dblclick", (h) => {
  const e = h.target.closest("[data-dz]");
  if (e) fdObyektİkiKlik(e.dataset.dz);
});

// ══ Klaviatura ═══════════════════════════════════════════════════════
$("#fd").addEventListener("keydown", (h) => {
  if (h.target.closest("input, select, textarea, .fd-inspektor")) return;
  const ctrl = h.ctrlKey || h.metaKey;
  let ok = true;
  if (h.key === "Delete" || h.key === "Backspace") fdSil();
  else if (ctrl && h.code === "KeyZ" && !h.shiftKey) fdGeriAl();
  else if (ctrl && (h.code === "KeyY" || (h.code === "KeyZ" && h.shiftKey))) fdGeriAl(true);
  else if (ctrl && h.code === "KeyC") fdKopyala();
  else if (ctrl && h.code === "KeyX") { fdKopyala(); fdSil(); }
  else if (ctrl && h.code === "KeyV") fdYapışdır();
  else if (ctrl && h.code === "KeyD") fdTəkrarla();
  else if (ctrl && h.code === "KeyA") fdSeç([...fdObyektlər()].filter(([, x]) => x.ana === null).map(([a]) => a));
  else if (h.key === "Escape") {
    const ana = FD.seçim.length ? fdObyektlər().get(FD.seçim.at(-1))?.ana : null;
    fdSeç(ana ? [ana] : []);
  } else if (h.key.startsWith("Arrow") && FD.seçim.length) fdOxla(h);
  else if (h.key === "F2" && FD.seçim.length === 1) fdAdDəyişDialoq(FD.seçim[0]);
  else if (h.key === "Enter" && FD.seçim.length === 1) fdObyektİkiKlik(FD.seçim[0]);
  else ok = false;
  if (ok) { h.preventDefault(); h.stopPropagation(); }
});

function fdOxla(h) {
  const ob = fdObyektlər();
  const addım = h.shiftKey ? 8 : 1;
  const [dx, dy] = { ArrowLeft: [-addım, 0], ArrowRight: [addım, 0], ArrowUp: [0, -addım], ArrowDown: [0, addım] }[h.key];
  const d = {};
  for (const a of FD.seçim) {
    const x = ob.get(a);
    if (!x || !fdSərbəstdir(x.ana) || x.o.görünməz) continue;
    const e = fdKök().querySelector(`[data-dz="${CSS.escape(a)}"]`);
    d[a] = { sol: Math.max(0, (+fdDəyər(x.o.xassələr.sol) || e?.offsetLeft || 0) + dx),
             yuxarı: Math.max(0, (+fdDəyər(x.o.xassələr.yuxarı) || e?.offsetTop || 0) + dy) };
  }
  if (Object.keys(d).length) fdƏməliyyat({ növ: "xassələr", dəyişikliklər: d });
  else if (FD.seçim.length === 1 && (dy || dx)) {
    // Axında: oxlar qonşu obyektə keçir
    const x = ob.get(FD.seçim[0]);
    const qardaşlar = [...ob].filter(([, y]) => y.ana === x.ana && !y.o.görünməz).map(([a]) => a);
    const i = qardaşlar.indexOf(FD.seçim[0]) + (dy || dx);
    if (qardaşlar[i]) fdSeç([qardaşlar[i]]);
  }
}

function fdSil() {
  if (!FD.seçim.length) return;
  fdƏməliyyat({ növ: "sil", adlar: [...FD.seçim] });
}
function fdKopyala() {
  if (!FD.seçim.length) return;
  FD.bufer = FD.seçim.map((a) => fdTap(a)).filter(Boolean).map((o) => JSON.parse(JSON.stringify(o)));
  bildir(`${FD.bufer.length} obyekt kopyalandı`, "", 1200);
}
function fdYapışdır() {
  if (!FD.bufer?.length) return;
  const s = FD.seçim.length === 1 ? fdTap(FD.seçim[0]) : null;
  const ob = fdObyektlər();
  let ana = null, indeks = null;
  if (s?.konteyner) ana = s.ad;
  else if (s) { const x = ob.get(s.ad); ana = x.ana; indeks = x.i + 1; }
  fdƏməliyyat({ növ: "yapışdır", obyektlər: FD.bufer, ana, indeks });
}
function fdTəkrarla() {
  if (FD.seçim.length) fdƏməliyyat({ növ: "təkrarla", adlar: [...FD.seçim] });
}

async function fdAdDəyişDialoq(ad) {
  const yeni = await dialoq("Adını dəyiş", { mətn: `${ad} obyektinin yeni adı (kodda özü.${ad})`, standart: ad });
  if (yeni && yeni !== ad) fdƏməliyyat({ növ: "adDəyiş", ad, yeni });
}

// ══ Alətlər sətri ════════════════════════════════════════════════════
$("#fd").addEventListener("click", (h) => {
  const b = h.target.closest("[data-fd], [data-hizala]");
  if (!b || b.disabled) return;
  if (b.dataset.hizala) { fdHizala(b.dataset.hizala); return; }
  const ə = b.dataset.fd;
  if (ə === "kod") fdKodDizayn(true);
  else if (ə === "dizayn") fdKodDizayn(false);
  else if (ə === "geri") fdGeriAl();
  else if (ə === "irəli") fdGeriAl(true);
  else if (ə === "tor") { FD.tor = !FD.tor; fdAlətləriYenilə(); }
  else if (ə === "cədvəllər") fdCədvəlRedaktoru(fdSeçilmişBaza());
  else if (ə === "crud") fdCrudDialoq(fdSeçilmişBaza());
});
$("#fd-kecid").addEventListener("click", () => fdKodDizayn(!cari()?.fdKod));

function fdSeçilmişBaza() {
  const b = Object.keys(FD.cavab?.verilənlər?.bazalar || {});
  const s = FD.seçim.find((a) => b.includes(a));
  if (s) return s;
  const sorğu = FD.seçim.map(fdTap).find((o) => o?.növ === "Sorğu");
  const sb = sorğu && fdDəyər(sorğu.xassələr.baza);
  return b.includes(sb) ? sb : b[0];
}

function fdHizala(necə) {
  if (!fdHizalanır()) return;
  const kök = fdKök();
  const ob = fdObyektlər();
  const qab = fdQabRect(ob.get(FD.seçim[0]).ana);
  // İstinad — ilk seçilən (Delphi kimi); ölçülər DOM-dan
  const ölçülər = {};
  for (const a of FD.seçim) {
    const e = kök.querySelector(`[data-dz="${CSS.escape(a)}"]`);
    const r = e.getBoundingClientRect();
    ölçülər[a] = { sol: r.left - qab.left, yuxarı: r.top - qab.top, en: r.width, hündürlük: r.height };
  }
  fdƏməliyyat({ növ: "düzləndir", necə, ölçülər });
}

function fdKodDizayn(kod) {
  const t = cari();
  if (!fdFormadır(t)) return;
  t.fdKod = kod;
  fdKeçidiYenilə();
  $("#fd").hidden = kod;
  if (kod) { R.fokus(); R.yenidənÖlç?.(); }
  else { fdOxu(); $("#fd").focus({ preventScroll: true }); }
}

// Kod rejimində mətn dəyişəndə — diaqnostika və model (gecikmə ilə)
let fdMətnTaymer = 0;
function fdMətnDəyişdi() {
  if (FD.sakit || !fdFormadır()) return;
  clearTimeout(fdMətnTaymer);
  fdMətnTaymer = setTimeout(fdOxu, 400);
}

// ══ Struktur ağacı ═══════════════════════════════════════════════════
function fdAğacıÇək() {
  const f = FD.cavab?.forma;
  if (!f) return;
  const seç = new Set(FD.seçim);
  const düyün = (o, d) =>
    `<div class="fd-ağ-düyün${seç.has(o.ad) ? " seçili" : ""}" draggable="true" data-dz="${qaç(o.ad)}" style="padding-left:${8 + d * 14}px" role="treeitem">` +
    `<span class="fd-ağ-ikon">${o.görünməz ? fdİkon(o.növ === "Sorğu" ? "sorğu" : "baza", 13) : o.konteyner ? "▭" : "◆"}</span>` +
    `<span class="fd-ağ-ad">${qaç(o.ad)}</span><span class="sönük">${qaç(o.növ)}</span></div>` +
    o.uşaqlar.map((u) => düyün(u, d + 1)).join("");
  $("#fd-agac").innerHTML =
    `<div class="fd-ağ-düyün kök${seç.size ? "" : " seçili"}" data-dz="" role="treeitem"><span class="fd-ağ-ikon">${fdİkon("dizayn", 13)}</span>` +
    `<span class="fd-ağ-ad">${qaç(f.ad)}</span><span class="sönük">forma</span></div>` +
    f.obyektlər.map((o) => düyün(o, 1)).join("");
}

$("#fd-agac").addEventListener("click", (h) => {
  const d = h.target.closest("[data-dz]");
  if (!d) return;
  if (!d.dataset.dz) fdSeç([]);
  else fdSeç([d.dataset.dz], h.shiftKey || h.ctrlKey || h.metaKey);
});
$("#fd-agac").addEventListener("dblclick", (h) => {
  const d = h.target.closest("[data-dz]");
  if (d?.dataset.dz) fdAdDəyişDialoq(d.dataset.dz);
});
$("#fd-agac").addEventListener("dragstart", (h) => {
  const d = h.target.closest("[data-dz]");
  if (!d?.dataset.dz) return;
  h.dataTransfer.setData("application/x-alqor-forma-agac", d.dataset.dz);
  h.dataTransfer.effectAllowed = "move";
});
function fdAğacHədəfi(h) {
  const d = h.target.closest("[data-dz]");
  if (!d) return null;
  const r = d.getBoundingClientRect();
  const nisbət = (h.clientY - r.top) / r.height;
  if (!d.dataset.dz) return { yer: "içinə", ad: null };
  const o = fdTap(d.dataset.dz);
  const yer = o?.konteyner && nisbət > 0.28 && nisbət < 0.72 ? "içinə" : nisbət < 0.5 ? "əvvəl" : "sonra";
  return { yer, ad: d.dataset.dz, el: d };
}
$("#fd-agac").addEventListener("dragover", (h) => {
  if (![...h.dataTransfer.types].includes("application/x-alqor-forma-agac")) return;
  const x = fdAğacHədəfi(h);
  if (!x) return;
  h.preventDefault();
  for (const e of $$("#fd-agac .üstündə, #fd-agac .əvvəl, #fd-agac .sonra")) e.classList.remove("üstündə", "əvvəl", "sonra");
  (x.el || $("#fd-agac .kök")).classList.add(x.yer === "içinə" ? "üstündə" : x.yer);
});
$("#fd-agac").addEventListener("dragend", () => {
  for (const e of $$("#fd-agac .üstündə, #fd-agac .əvvəl, #fd-agac .sonra")) e.classList.remove("üstündə", "əvvəl", "sonra");
});
$("#fd-agac").addEventListener("drop", (h) => {
  const ad = h.dataTransfer.getData("application/x-alqor-forma-agac");
  const x = fdAğacHədəfi(h);
  if (!ad || !x) return;
  h.preventDefault();
  if (x.ad === ad) return;
  if (x.yer === "içinə") { fdƏməliyyat({ növ: "köçür", adlar: [ad], ana: x.ad, indeks: null }); return; }
  const y = fdObyektlər().get(x.ad);
  fdƏməliyyat({ növ: "köçür", adlar: [ad], ana: y.ana, indeks: y.i + (x.yer === "sonra" ? 1 : 0) });
});

// ══ Obyekt inspektoru ════════════════════════════════════════════════
function fdİnspektoruÇək() {
  const f = FD.cavab?.forma;
  if (!f) return;
  if (FD.ins?.contains(document.activeElement) && FD.insAd === (FD.seçim.at(-1) ?? "") && FD.insYazılır) return;
  const ad = FD.seçim.at(-1) ?? null;
  const o = ad ? fdTap(ad) : null;
  FD.insAd = ad ?? "";
  for (const b of $$(".fd-ins-nişanlar button")) b.classList.toggle("aktiv", b.dataset.ins === FD.inspektor);
  $(".fd-ins-nişanlar [data-ins='h']").disabled = !o || !(fdNöv(o.növ)?.hadisələr?.length);
  if (FD.inspektor === "h" && (!o || !(fdNöv(o.növ)?.hadisələr?.length))) FD.inspektor = "x";
  const n = o ? fdNöv(o.növ) : null;
  $("#fd-ins-baslik").innerHTML = o
    ? `<b>${qaç(o.ad)}</b><span class="sönük">${qaç(o.növ)} · ${qaç(n?.beynəlxalqAd || "")}</span>` +
      (FD.seçim.length > 1 ? `<span class="fd-say">${FD.seçim.length} seçilib</span>` : "")
    : `<b>${qaç(f.ad)}</b><span class="sönük">forma · pəncərə</span>`;
  const qab = $("#fd-ins");
  FD.ins = qab;
  qab.innerHTML = FD.inspektor === "h" && o ? fdHadisələrHTML(o) : fdXüsusiyyətlərHTML(o);
}

$(".fd-ins-nişanlar").addEventListener("click", (h) => {
  const b = h.target.closest("[data-ins]");
  if (!b || b.disabled) return;
  FD.inspektor = b.dataset.ins;
  fdİnspektoruÇək();
});

function fdSətir(p, dəyər, verilib) {
  const ad = qaç(p.ad);
  const v = fdDəyər(dəyər);
  const std = p.standart;
  let g;
  const seçimHTML = (siyahı, boşMətn = "—") => `<select data-fx="${ad}" data-nov="seçim"><option value="">${qaç(boşMətn)}</option>` +
    siyahı.map((s) => `<option value="${qaç(s)}" data-tip="${typeof s}"${String(s) === String(v ?? "") ? " selected" : ""}>${qaç(s)}</option>`).join("") +
    (v !== undefined && v !== null && v !== "" && !siyahı.map(String).includes(String(v)) ? `<option selected value="${qaç(v)}">${qaç(v)}</option>` : "") + "</select>";
  switch (p.növ) {
    case "məntiq": {
      const işarəli = verilib ? !!v : !!std;
      g = `<input type="checkbox" data-fx="${ad}" data-nov="məntiq"${işarəli ? " checked" : ""}>`;
      break;
    }
    case "seçim": g = seçimHTML(p.seçimlər || [], std != null ? `standart (${std})` : "—"); break;
    case "ədəd":
      g = `<input type="number" data-fx="${ad}" data-nov="ədəd" value="${verilib ? qaç(v) : ""}" placeholder="${std != null ? qaç(std) : ""}">`;
      break;
    case "rəng": {
      const hex = typeof v === "string" && /^#[0-9a-f]{6}$/i.test(v) ? v : "#000000";
      g = `<span class="birləşik"><input type="color" data-fx-reng="${ad}" value="${hex}"><input type="text" data-fx="${ad}" data-nov="mətn" value="${qaç(v ?? "")}" placeholder="#0b6bcb"></span>`;
      break;
    }
    case "ifadə":
      g = `<input type="text" class="kod" data-fx="${ad}" data-nov="ifadə" value="${qaç(verilib ? (typeof dəyər === "object" && dəyər?.$ifadə !== undefined ? dəyər.$ifadə : JSON.stringify(v)) : "")}" placeholder='["a", "b"]' spellcheck="false">`;
      break;
    case "sorğu": {
      const s = Object.keys(FD.cavab.verilənlər?.sorğular || {});
      g = seçimHTML(s).replace('data-nov="seçim"', 'data-nov="istinad"');
      break;
    }
    case "istinad": {
      const s = Object.keys(FD.cavab.verilənlər?.bazalar || {});
      g = seçimHTML(s).replace('data-nov="seçim"', 'data-nov="istinad"');
      break;
    }
    case "sütun": case "cədvəl": case "sıra":
      g = p.siyahı ? seçimHTML(p.siyahı) : `<input type="text" data-fx="${ad}" data-nov="mətn" value="${qaç(v ?? "")}">`;
      break;
    default:
      g = `<input type="text" data-fx="${ad}" data-nov="mətn" value="${qaç(verilib ? v ?? "" : "")}" placeholder="${std != null && std !== "" ? qaç(std) : ""}" spellcheck="false">`;
  }
  return `<div class="xüs-sətir${verilib ? " verilib" : ""}" data-fsetir="${ad}">` +
    `<label title="${qaç(p.izah || "")}">${qaç(p.ad)}</label>${g}` +
    `<button class="sıfırla" data-fx-sil="${ad}" title="Standarta qaytar (xassəni sil)">✕</button></div>`;
}

function fdXüsusiyyətlərHTML(o) {
  const k = FD.kataloq;
  const f = FD.cavab.forma;
  if (!o) {
    return `<div class="xüs-qrup"><h4>Forma</h4>` +
      `<div class="xüs-sətir verilib"><label>ad</label><input type="text" value="${qaç(f.ad)}" disabled title="Forma adı = komponentin adı (fayl adı ilə dəyişir)"><span></span></div>` +
      k.kök.map((p) => fdSətir(p, f.xassələr[p.ad], p.ad in f.xassələr)).join("") + "</div>";
  }
  const n = fdNöv(o.növ) || { parametrlər: [] };
  const x = o.xassələr;
  let h = `<div class="xüs-sətir verilib"><label title="Kodda: özü.${qaç(o.ad)}">ad</label>` +
    `<input type="text" data-fx-ad value="${qaç(o.ad)}" spellcheck="false"><span></span></div>`;
  const vd = FD.cavab.verilənlər || { bazalar: {}, sorğular: {} };
  let parametrlər = n.parametrlər.map((p) => ({ ...p }));
  if (o.növ === "Sorğu") {
    const baza = vd.bazalar[fdDəyər(x.baza)];
    const cədvəllər = baza ? Object.keys(baza.cədvəllər) : null;
    const sütunlar = vd.sorğular[o.ad]?.sütunlar || [];
    parametrlər = parametrlər.map((p) => (p.ad === "cədvəl" ? { ...p, növ: "cədvəl", siyahı: cədvəllər }
      : p.ad === "sırala" ? { ...p, növ: "sıra", siyahı: sütunlar.length ? sütunlar : null } : p));
  }
  h += `<div class="xüs-qrup"><h4>${n.görünməz ? "Komponent" : "Xüsusiyyətlər"}</h4>` +
    parametrlər.map((p) => fdSətir(p, x[p.ad], p.ad in x)).join("") + "</div>";
  if (o.növ === "VerilənlərBazası") {
    const b = vd.bazalar[o.ad] || {};
    h += `<div class="fd-ins-düymələr"><button data-fd-ins="cədvəllər">${fdİkon("baza", 14)} Cədvəllər…</button>` +
      `<button data-fd-ins="crud"${Object.keys(b.cədvəllər || {}).length ? "" : " disabled"}>${fdİkon("sehrbaz", 14)} Cədvəldən forma…</button>` +
      `<button data-fd-ins="model"${Object.keys(b.cədvəllər || {}).length ? "" : " disabled"}>Model kodu yarat</button></div>` +
      `<p class="ipucu-mətni">${b.var ? `Sxem: <code>${qaç(b.sxem)}</code> — ${Object.keys(b.cədvəllər || {}).length} cədvəl`
        : "Sxem hələ yoxdur — «Cədvəllər…» ilə yaradın"}${b.xətalar?.length ? `<br><span class="xəta-mətni">${qaç(b.xətalar.join("; "))}</span>` : ""}</p>`;
  }
  if (n.metodlar) {
    h += `<div class="xüs-qrup"><h4>Kodda</h4><dl class="fd-metodlar">` + Object.entries(n.metodlar).map(([m, i]) =>
      `<dt><code>özü.${qaç(o.ad)}.${qaç(m)}</code></dt><dd>${qaç(i)}</dd>`).join("") + "</dl></div>";
  }
  if (!n.görünməz) {
    if (o.növ !== "kətan") {
      const sorğu = vd.sorğular[fdDəyər(x.mənbə)];
      h += `<div class="xüs-qrup"><h4>Verilənlər</h4>` + k.bağlama.map((p) =>
        fdSətir(p.ad === "sütun" ? { ...p, siyahı: sorğu?.sütunlar?.length ? sorğu.sütunlar : null } : p,
          x[p.ad], p.ad in x)).join("") + "</div>";
    }
    h += `<div class="xüs-qrup"><h4>Yerləşmə</h4>` + k.ortaq.map((p) => fdSətir(p, x[p.ad], p.ad in x)).join("") + "</div>";
  }
  return h + `<div class="xüs-xəta" id="fd-ins-xeta" hidden></div>`;
}

function fdHadisələrHTML(o) {
  const n = fdNöv(o.növ);
  const metodlar = FD.cavab.metodlar || [];
  const id = "fd-metodlar";
  return `<datalist id="${id}">${metodlar.map((m) => `<option value="${qaç(m)}">`).join("")}</datalist>` +
    `<div class="xüs-qrup"><h4>Hadisələr</h4>` + (n.hadisələr || []).map((h) => {
      const v = fdDəyər(o.xassələr[h]) || "";
      return `<div class="xüs-sətir${v ? " verilib" : ""}" data-fsetir="${qaç(h)}"><label title="İki klik — idarəedici yaradılır və kodda açılır">${qaç(h)}</label>` +
        `<input type="text" data-fh="${qaç(h)}" list="${id}" value="${qaç(v)}" placeholder="iki klik → ${qaç(o.ad)}_${qaç(h)}" spellcheck="false">` +
        `<button class="sıfırla" data-fh-sil="${qaç(h)}" title="Hadisəni ayır">✕</button></div>`;
    }).join("") + `</div><p class="ipucu-mətni">Metod komponentdə <code>əməl Ad()</code> kimi yazılır — ` +
    `${qaç(FD.cavab.alq || "")}. Mövcud metodu siyahıdan seçin və ya yeni ad yazın.</p>`;
}

function fdInsDəyəri(el) {
  const növ = el.dataset.nov;
  if (növ === "məntiq") return el.checked;
  if (el.value === "") return null;
  if (növ === "ədəd") { const n = Number(el.value); return Number.isFinite(n) ? n : null; }
  if (növ === "seçim") { const o = el.selectedOptions[0]; return o?.dataset.tip === "number" ? Number(el.value) : el.value; }
  if (növ === "istinad") return { $ad: el.value };
  if (növ === "ifadə") return { $ifadə: el.value };
  return el.value;
}

function fdXassəQoy(xassə, dəyər) {
  const ad = FD.seçim.at(-1) ?? null;
  fdƏməliyyat({ növ: "xassə", ad, xassə, dəyər });
}

$("#fd-ins").addEventListener("change", (h) => {
  const el = h.target;
  if (el.dataset.fxAd !== undefined) {
    const köhnə = FD.seçim.at(-1);
    const yeni = el.value.trim();
    if (köhnə && yeni && yeni !== köhnə) fdƏməliyyat({ növ: "adDəyiş", ad: köhnə, yeni });
    return;
  }
  if (el.dataset.fh) { fdHadisəQoy(el.dataset.fh, el.value.trim()); return; }
  if (el.dataset.fxReng) {
    const m = el.parentElement.querySelector("[data-fx]");
    if (m) m.value = el.value;
    fdXassəQoy(el.dataset.fxReng, el.value);
    return;
  }
  if (el.dataset.fx) fdXassəQoy(el.dataset.fx, fdInsDəyəri(el));
});
$("#fd-ins").addEventListener("keydown", (h) => {
  if (h.key === "Enter" && h.target.matches("input[type=text], input[type=number], input:not([type])")) {
    h.preventDefault();
    h.target.dispatchEvent(new Event("change", { bubbles: true }));
  }
  if (h.key === "Escape") { $("#fd").focus(); fdİnspektoruÇək(); }
});
$("#fd-ins").addEventListener("click", (h) => {
  const s = h.target.closest("[data-fx-sil]");
  if (s) { fdXassəQoy(s.dataset.fxSil, null); return; }
  const hs = h.target.closest("[data-fh-sil]");
  if (hs) { fdXassəQoy(hs.dataset.fhSil, null); return; }
  const b = h.target.closest("[data-fd-ins]");
  if (!b) return;
  const ad = FD.seçim.at(-1);
  if (b.dataset.fdIns === "cədvəllər") fdCədvəlRedaktoru(ad);
  else if (b.dataset.fdIns === "crud") fdCrudDialoq(ad);
  else if (b.dataset.fdIns === "model") fdModelKodu(ad);
});
$("#fd-ins").addEventListener("dblclick", (h) => {
  const i = h.target.closest("[data-fh]") || h.target.closest("[data-fsetir]")?.querySelector("[data-fh]");
  const ad = FD.seçim.at(-1);
  if (i && ad) fdHadisə(ad, i.dataset.fh, true, i.value.trim() || null);
});

function fdHadisəQoy(hadisə, metod) {
  const ad = FD.seçim.at(-1);
  if (!ad) return;
  if (!metod) { fdXassəQoy(hadisə, null); return; }
  fdHadisə(ad, hadisə, false, metod);
}

/**
 * Hadisə idarəedicisi: `.forma`-da `hadisə = Obyekt_hadisə`, `.alq`-da
 * `əməl` skeleti (yoxdursa). `keç` — kodu açıb metoda keçir.
 */
async function fdHadisə(obyekt, hadisə, keç = true, metod = null) {
  const t = cari();
  if (!fdFormadır(t)) return;
  await FD.növbə;
  const alqYol = FD.cavab?.alq;
  const alqTab = S.tablar.find((x) => x.yol === alqYol);
  const əvvəl = R.mətn;
  try {
    const n = await API.göndər("/api/forma/hadise", {
      yol: t.yol, mətn: əvvəl, obyekt, hadisə, metod: metod || undefined,
      alqMətn: alqTab ? alqTab.v.mətn : undefined });
    if (n.mətn !== əvvəl) { t.fdTarix.geri.push(əvvəl); t.fdTarix.irəli = []; }
    fdCavab(n);
    if (alqTab) { alqTab.v = { ...alqTab.v, mətn: n.alqMətn }; alqTab.saxlanmış = n.alqMətn; }
    if (n.yeniMetod) bildir(`əməl ${n.metod}() yaradıldı — ${n.alq}`, "uğur", 2600);
    if (keç) {
      await ağacıYenilə();
      await faylıAç(n.alq);
      R.sətirəKeç(n.sətir, 9);
    }
  } catch (x) { xəta(x); }
}

// ══ Kontekst menyusu ═════════════════════════════════════════════════
function fdKontekst(h, ad) {
  h.preventDefault();
  if (ad && !FD.seçim.includes(ad)) fdSeç([ad]);
  if (!ad) fdSeç([]);
  const o = ad ? fdTap(ad) : null;
  const var_ = () => FD.seçim.length > 0;
  const baza = o?.növ === "VerilənlərBazası";
  KontekstMenyu.göstər(h.clientX, h.clientY, [
    ...(o && fdNöv(o.növ)?.hadisələr?.length ? [{ ad: `Hadisə: ${fdNöv(o.növ).hadisələr[0]}`, ikon: "keç-sətir", işlə: () => fdHadisə(ad, fdNöv(o.növ).hadisələr[0]) }, "-"] : []),
    ...(baza ? [{ ad: "Cədvəllər…", ikon: "layihə", işlə: () => fdCədvəlRedaktoru(ad) },
      { ad: "Cədvəldən forma yarat…", ikon: "elementlər", işlə: () => fdCrudDialoq(ad) },
      { ad: "Model kodu yarat", ikon: "fayl-yeni", işlə: () => fdModelKodu(ad) }, "-"] : []),
    { ad: "Kəs", ikon: "kəs", qısayol: "Ctrl+X", aktiv: var_, işlə: () => { fdKopyala(); fdSil(); } },
    { ad: "Kopyala", ikon: "kopyala", qısayol: "Ctrl+C", aktiv: var_, işlə: fdKopyala },
    { ad: "Yapışdır", ikon: "yapışdır", qısayol: "Ctrl+V", aktiv: () => !!FD.bufer?.length, işlə: fdYapışdır },
    { ad: "Təkrarla", ikon: "təkrarla", qısayol: "Ctrl+D", aktiv: var_, işlə: fdTəkrarla },
    "-",
    { ad: "Adını dəyiş…", ikon: "ad-dəyiş", qısayol: "F2", aktiv: () => FD.seçim.length === 1, işlə: () => fdAdDəyişDialoq(FD.seçim[0]) },
    { ad: "Öndə (əvvələ)", ikon: "sətir-yuxarı", aktiv: () => !!o, işlə: () => fdƏməliyyat({ növ: "köçür", adlar: [ad], ana: fdObyektlər().get(ad).ana, indeks: 0 }) },
    { ad: "Arxada (sona)", ikon: "sətir-aşağı", aktiv: () => !!o, işlə: () => fdƏməliyyat({ növ: "köçür", adlar: [ad], ana: fdObyektlər().get(ad).ana, indeks: null }) },
    "-",
    { ad: "Sil", ikon: "sil", qısayol: "Delete", aktiv: var_, işlə: fdSil },
    "-",
    { ad: "Formanın mətni (Kod)", ikon: "keç-fayl", qısayol: "Alt+F12", işlə: () => fdKodDizayn(true) },
  ]);
}
$("#fd-mezmun").addEventListener("contextmenu", (h) => fdKontekst(h, fdObyektNöqtədə(h)));
$("#fd-gz").addEventListener("contextmenu", (h) => fdKontekst(h, h.target.closest("[data-dz]")?.dataset.dz || null));
$("#fd-agac").addEventListener("contextmenu", (h) => fdKontekst(h, h.target.closest("[data-dz]")?.dataset.dz || null));

// Yan panelin eni
$("#fd-bolucu").addEventListener("pointerdown", (h0) => {
  h0.preventDefault();
  const y = $("#fd-yan");
  const b = y.offsetWidth;
  document.body.classList.add("sürüklənir");
  const hərəkət = (h) => { y.style.width = `${Math.max(220, Math.min(560, b - (h.clientX - h0.clientX)))}px`; };
  document.addEventListener("pointermove", hərəkət);
  document.addEventListener("pointerup", () => {
    document.removeEventListener("pointermove", hərəkət);
    document.body.classList.remove("sürüklənir");
    yaddaş("fdYanEn", y.style.width);
    fdÖrtüyüÇək();
  }, { once: true });
});
if (yaddaş("fdYanEn")) $("#fd-yan").style.width = yaddaş("fdYanEn");

// ══ Cədvəl redaktoru (.sxem) ═════════════════════════════════════════
document.body.insertAdjacentHTML("beforeend", `
<dialog class="dialoq fd-sxem-dialoq" id="fd-sxem">
  <form method="dialog" id="fd-sxem-forma">
    <h3 id="fd-sxem-baslik">Cədvəllər</h3>
    <p class="sönük" id="fd-sxem-alt"></p>
    <div class="fd-sxem-gövdə">
      <div class="fd-sxem-cədvəllər">
        <div class="fd-sxem-siyahı" id="fd-sxem-cedveller"></div>
        <div class="fd-sxem-alt-düymələr">
          <button type="button" data-sx="cədvəlƏlavə" title="Yeni cədvəl">＋ Cədvəl</button>
          <button type="button" data-sx="cədvəlSil" title="Seçilmiş cədvəli sil">− Sil</button>
        </div>
      </div>
      <div class="fd-sxem-sahələr">
        <div class="fd-sxem-cədvəl-ad"><label>Cədvəlin adı</label><input id="fd-sxem-cad" spellcheck="false"></div>
        <table class="fd-sxem-cədvəl"><thead><tr><th>Sahə</th><th>Tip</th><th title="Birincil açar (tam açar — avtomatik artır)">açar</th>
          <th title="Boş ola bilməz">məcburi</th><th title="Təkrarlanmaz">tək</th><th>standart</th><th>əlaqə</th><th></th></tr></thead>
          <tbody id="fd-sxem-sahe"></tbody></table>
        <button type="button" data-sx="sahəƏlavə">＋ Sahə</button>
      </div>
    </div>
    <div class="xüs-xəta" id="fd-sxem-xeta" hidden></div>
    <div class="dialoq-düymələri">
      <button type="button" data-sx="idxal" title="Mövcud SQLite (və ya bağlantı) bazasının cədvəllərini oxu">Mövcud bazadan idxal</button>
      <span class="boşluq"></span>
      <button value="ləğv" formnovalidate>Ləğv et</button>
      <button type="button" data-sx="saxla" class="vurğulu">Saxla</button>
    </div>
  </form>
</dialog>`);

const SX = { baza: null, sxem: null, cari: 0, tiplər: [] };

async function fdCədvəlRedaktoru(baza) {
  const t = cari();
  if (!baza || !fdFormadır(t)) { bildir("Əvvəlcə VerilənlərBazası komponenti əlavə edin", "xəta"); return; }
  await FD.növbə;
  try {
    const n = await API.göndər("/api/forma/sxem", { yol: t.yol, mətn: R.mətn, baza });
    SX.baza = baza; SX.sxem = n.sxem; SX.tiplər = n.tiplər; SX.cari = 0; SX.fayl = n.fayl;
    $("#fd-sxem-baslik").textContent = `${baza} — cədvəllər`;
    $("#fd-sxem-alt").textContent = `${n.fayl}${n.var ? "" : " (yeni fayl yaradılacaq)"} · proqram bazaya qoşulanda çatışmayan cədvəl və sütunlar avtomatik yaradılır`;
    $("#fd-sxem-xeta").hidden = !n.xətalar?.length;
    $("#fd-sxem-xeta").textContent = (n.xətalar || []).join("\n");
    sxÇək();
    $("#fd-sxem").showModal();
  } catch (x) { xəta(x); }
}

function sxCədvəl() { return SX.sxem.cədvəllər[SX.cari] || null; }

function sxÇək() {
  const c = SX.sxem.cədvəllər;
  $("#fd-sxem-cedveller").innerHTML = c.length ? c.map((x, i) =>
    `<div class="fd-sxem-c${i === SX.cari ? " seçili" : ""}" data-i="${i}">${fdİkon("sorğu", 14)}<span>${qaç(x.ad)}</span><small class="sönük">${x.sahələr.length}</small></div>`).join("")
    : '<p class="ipucu-mətni">Cədvəl yoxdur — «＋ Cədvəl»</p>';
  const cd = sxCədvəl();
  $(".fd-sxem-sahələr").classList.toggle("boş", !cd);
  $("#fd-sxem-cad").value = cd?.ad || "";
  const əlaqələr = [];
  for (const x of c) if (x !== cd) for (const f of x.sahələr) əlaqələr.push(`${x.ad}.${f.ad}`);
  $("#fd-sxem-sahe").innerHTML = (cd?.sahələr || []).map((f, i) => {
    const std = f.standart === null || f.standart === undefined ? "" : f.standart === true ? "doğru" : f.standart === false ? "yanlış" : String(f.standart);
    return `<tr data-i="${i}"><td><input data-f="ad" value="${qaç(f.ad)}" spellcheck="false"></td>` +
      `<td><select data-f="tip">${SX.tiplər.map((t) => `<option${t === f.tip ? " selected" : ""}>${t}</option>`).join("")}</select></td>` +
      ["açar", "məcburi", "tək"].map((b) => `<td class="m"><input type="checkbox" data-f="${b}"${f[b] ? " checked" : ""}></td>`).join("") +
      `<td><input data-f="standart" value="${qaç(std)}" placeholder="—" spellcheck="false"></td>` +
      `<td><select data-f="əlaqə"><option value="">—</option>${əlaqələr.map((e) => `<option${e === f.əlaqə ? " selected" : ""}>${qaç(e)}</option>`).join("")}</select></td>` +
      `<td><button type="button" data-sx="sahəSil" title="Sahəni sil">✕</button></td></tr>`;
  }).join("");
}

function sxStandart(m) {
  const s = m.trim();
  if (s === "") return { standart: null, standartVar: false };
  if (s === "doğru" || s === "yanlış") return { standart: s === "doğru", standartVar: true };
  if (/^-?\d+(\.\d+)?$/.test(s)) return { standart: Number(s), standartVar: true };
  return { standart: s.replace(/^"(.*)"$/, "$1"), standartVar: true };
}

$("#fd-sxem-cedveller").addEventListener("click", (h) => {
  const d = h.target.closest("[data-i]");
  if (d) { SX.cari = +d.dataset.i; sxÇək(); }
});
$("#fd-sxem-cad").addEventListener("input", (h) => {
  const cd = sxCədvəl();
  if (!cd) return;
  cd.ad = h.target.value.trim();
  const e = $(`#fd-sxem-cedveller [data-i="${SX.cari}"] span`);
  if (e) e.textContent = cd.ad;
});
$("#fd-sxem-sahe").addEventListener("input", (h) => sxSahəDəyiş(h.target));
$("#fd-sxem-sahe").addEventListener("change", (h) => { sxSahəDəyiş(h.target); if (h.target.dataset.f === "açar") sxÇək(); });
function sxSahəDəyiş(el) {
  const tr = el.closest("tr[data-i]");
  const f = sxCədvəl()?.sahələr[+tr?.dataset.i];
  if (!f) return;
  const k = el.dataset.f;
  if (el.type === "checkbox") {
    f[k] = el.checked;
    if (k === "açar" && el.checked) for (const x of sxCədvəl().sahələr) if (x !== f) x.açar = false;
  } else if (k === "standart") Object.assign(f, sxStandart(el.value));
  else if (k === "əlaqə") f.əlaqə = el.value || null;
  else f[k] = k === "ad" ? el.value.trim() : el.value;
}

$("#fd-sxem").addEventListener("click", async (h) => {
  const b = h.target.closest("[data-sx]");
  if (!b) return;
  const ə = b.dataset.sx;
  const c = SX.sxem.cədvəllər;
  if (ə === "cədvəlƏlavə") {
    let ad = "cədvəl", i = 1;
    while (c.some((x) => x.ad === ad)) ad = `cədvəl${++i}`;
    c.push({ ad, sahələr: [{ ad: "id", tip: "tam", açar: true, məcburi: false, tək: false, standart: null, standartVar: false, əlaqə: null }] });
    SX.cari = c.length - 1;
    sxÇək();
    $("#fd-sxem-cad").focus(); $("#fd-sxem-cad").select();
  } else if (ə === "cədvəlSil") {
    if (!sxCədvəl()) return;
    c.splice(SX.cari, 1);
    SX.cari = Math.max(0, SX.cari - 1);
    sxÇək();
  } else if (ə === "sahəƏlavə") {
    const cd = sxCədvəl();
    if (!cd) return;
    let ad = "sahə", i = 1;
    while (cd.sahələr.some((x) => x.ad === ad)) ad = `sahə${++i}`;
    cd.sahələr.push({ ad, tip: "mətn", açar: false, məcburi: false, tək: false, standart: null, standartVar: false, əlaqə: null });
    sxÇək();
    const s = $$("#fd-sxem-sahe input[data-f='ad']").at(-1);
    s?.focus(); s?.select();
  } else if (ə === "sahəSil") {
    const tr = b.closest("tr[data-i]");
    sxCədvəl()?.sahələr.splice(+tr.dataset.i, 1);
    sxÇək();
  } else if (ə === "idxal") {
    try {
      const n = await API.göndər("/api/forma/sxem/idxal", { yol: cari().yol, mətn: R.mətn, baza: SX.baza });
      const ok = !c.length || await sxTəsdiq(`Bazada ${n.sxem.cədvəllər.length} cədvəl tapıldı. Redaktordakı cədvəllər əvəzlənsin?`);
      if (!ok) return;
      SX.sxem.cədvəllər = n.sxem.cədvəllər;
      SX.cari = 0;
      sxÇək();
      bildir(`${n.sxem.cədvəllər.length} cədvəl idxal olundu`, "uğur");
    } catch (x) { $("#fd-sxem-xeta").hidden = false; $("#fd-sxem-xeta").textContent = x.message; }
  } else if (ə === "saxla") {
    await sxSaxla();
  }
});

function sxTəsdiq(m) { return Promise.resolve(confirm(m)); }

async function sxSaxla() {
  const t = cari();
  const xət = $("#fd-sxem-xeta");
  try {
    const n = await API.göndər("/api/forma/sxem/yaz", { yol: t.yol, mətn: R.mətn, baza: SX.baza, sxem: SX.sxem });
    if (n.xətalar?.length) { xət.hidden = false; xət.textContent = n.xətalar.join("\n"); return; }
    xət.hidden = true;
    $("#fd-sxem").close();
    if (n.mətn !== R.mətn) { t.fdTarix.geri.push(R.mətn); t.fdTarix.irəli = []; }
    fdCavab(n);
    ağacıYenilə();
    bildir(`${n.sxemYol} saxlanıldı`, "uğur", 2600);
  } catch (x) { xət.hidden = false; xət.textContent = x.message; }
}

// ══ «Cədvəldən forma yarat» və model kodu ════════════════════════════
async function fdCrudDialoq(baza) {
  const t = cari();
  if (!fdFormadır(t)) return;
  const bazalar = FD.cavab?.verilənlər?.bazalar || {};
  baza = baza && bazalar[baza] ? baza : Object.keys(bazalar)[0];
  if (!baza) { bildir("Əvvəlcə VerilənlərBazası komponenti əlavə edin", "xəta"); return; }
  const cədvəllər = Object.keys(bazalar[baza].cədvəllər || {});
  if (!cədvəllər.length) {
    bildir(`${baza}: cədvəl yoxdur — əvvəlcə «Cədvəllər…»`, "xəta");
    fdCədvəlRedaktoru(baza);
    return;
  }
  const k = document.createElement("div");
  k.className = "fd-crud";
  k.innerHTML = `<label>Baza <select id="fd-crud-baza">${Object.keys(bazalar).map((b) => `<option${b === baza ? " selected" : ""}>${qaç(b)}</option>`).join("")}</select></label>` +
    `<label>Cədvəl <select id="fd-crud-cedvel">${cədvəllər.map((c) => `<option>${qaç(c)}</option>`).join("")}</select></label>` +
    `<p class="ipucu-mətni">Formaya əlavə olunur: Sorğu, cədvəl (siyahı), hər sahə üçün giriş elementi və naviqator — hamısı bir-birinə bağlı.</p>`;
  k.querySelector("#fd-crud-baza").addEventListener("change", (h) => {
    const s = Object.keys(bazalar[h.target.value].cədvəllər || {});
    k.querySelector("#fd-crud-cedvel").innerHTML = s.map((c) => `<option>${qaç(c)}</option>`).join("");
  });
  const ok = await dialoq("Cədvəldən forma yarat", { düyün: k, giriş: false, tamam: "Yarat" });
  if (!ok) return;
  const b = k.querySelector("#fd-crud-baza").value, c = k.querySelector("#fd-crud-cedvel").value;
  if (!c) return;
  const n = await fdƏməliyyat({ növ: "crud", baza: b, cədvəl: c });
  if (n) bildir(`«${c}» cədvəli üçün ${n.seçim?.length || 0} obyekt əlavə olundu`, "uğur");
}

async function fdModelKodu(baza) {
  const t = cari();
  baza = baza || fdSeçilmişBaza();
  if (!fdFormadır(t) || !baza) return;
  try {
    const n = await API.göndər("/api/forma/model", { yol: t.yol, mətn: R.mətn, baza });
    await ağacıYenilə();
    const açıq = S.tablar.find((x) => x.yol === n.yol);
    if (açıq) tabıBağla(n.yol, true);
    await faylıAç(n.yol);
    bildir(`${n.yol} yaradıldı`, "uğur");
  } catch (x) { xəta(x); }
}

// ══ Yeni forma ═══════════════════════════════════════════════════════
async function yeniForma(qovluq = S.seçiliQovluq) {
  const ad = await dialoq("Yeni forma", {
    mətn: `${qovluq ? `Qovluq: ${qovluq}/ · ` : ""}Ad.forma (görünüş) + Ad.alq (kod: komponent Ad) yaradılır`,
    standart: "Əsas" });
  if (!ad) return null;
  try {
    const n = await API.göndər("/api/forma/yeni", { qovluq, ad });
    await ağacıYenilə();
    await faylıAç(n.forma);
    bildir(`${n.forma} + ${n.alq} yaradıldı`, "uğur");
    return n.forma;
  } catch (x) { xəta(x); return null; }
}

function fdTemaDəyişdi() { if (FD.cavab && fdFormadır()) fdÇək(); }
