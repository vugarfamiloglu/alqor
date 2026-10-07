/*
 * Alqor Studio — yüngül kod redaktoru.
 *
 * Quruluş: şəffaf <textarea> (yazı, kursor, seçim, klaviatura) +
 * onun altında rənglənmiş <pre> örtüyü. Hər ikisi eyni şrift və
 * ölçüdədir; sürüşdürmə `transform` ilə sinxronlaşır.
 *
 *   • sintaksis rəngləmə (dil.js), sətir nömrələri, cari sətir
 *   • avtomatik girinti (`onda`, `et`, blok açanlar) və `son`/`yoxsa`
 *     yazılanda geri çəkilmə; Tab = 4 boşluq
 *   • öz geri al / irəli al yığını (Ctrl+Z / Ctrl+Y)
 *   • axtar / əvəzlə
 *   • Azərbaycan klaviaturası: ASCII açar söz çevrilməsi və `;` tərkibi
 *   • diaqnostika: dalğalı xətt + sətir nişanı
 *   • tamamlama siyahısı və imza ipucu (`tamamlayıcı`, `imzaVerən` —
 *     Studio onları `alqorls` dil serverinə bağlayır)
 */
"use strict";

class Redaktor {
  constructor(qab, ayarlar = {}) {
    this.qab = qab;
    this.ayarlar = Object.assign({ ascii: true, tərkib: true, girinti: 4 },
                                 ayarlar);
    this.kompozisiya = {};
    this.blokAçanlar = new Set();
    qab.classList.add("redaktor");
    qab.innerHTML =
      '<div class="r-xətlər" aria-hidden="true"><div class="r-nömrələr"></div></div>' +
      '<div class="r-sahə">' +
      '<div class="r-fon" aria-hidden="true"><div class="r-cari"></div><div class="r-icra" hidden></div><div class="r-vurğular"></div></div>' +
      '<pre class="r-örtük" aria-hidden="true"></pre>' +
      '<textarea class="r-giriş" spellcheck="false" autocapitalize="off" ' +
      'autocomplete="off" autocorrect="off" wrap="off" aria-label="Kod redaktoru"></textarea>' +
      '</div>';
    this.ta = qab.querySelector(".r-giriş");
    this.örtük = qab.querySelector(".r-örtük");
    this.fon = qab.querySelector(".r-fon");
    this.cari = qab.querySelector(".r-cari");
    this.icra = qab.querySelector(".r-icra");
    this.vurğuQabı = qab.querySelector(".r-vurğular");
    this.nömrələr = qab.querySelector(".r-nömrələr");
    this.sahə = qab.querySelector(".r-sahə");

    this.dinləyicilər = {};
    this.diaqnostikalar = [];
    this.axtarış = { nəticələr: [], cari: -1 };
    this.vurğular = [];
    this.tarixçə = [];
    this.irəli = [];
    this._sonNöv = null;
    this._sonVaxt = 0;
    this._tərkibSon = false;
    this._çəkmə = 0;
    this.versiya = 0;

    this.nöqtələr = new Set();    // dayanma nöqtələri (sətir nömrələri)
    this.icraSətri = 0;           // debaqda dayanılan sətir
    this.tamamlayıcı = null;      // async (kursor) → {maddələr} (LSP CompletionItem)
    this.imzaVerən = null;        // async (kursor) → LSP SignatureHelp | null
    this._tamamlaQur();

    this._bağla();
    this._ölç();
    this.çək();
  }

  // ══ Hadisələr ══════════════════════════════════════════════════════
  on(ad, f) { (this.dinləyicilər[ad] ||= []).push(f); return this; }
  _yay(ad, ...a) { for (const f of this.dinləyicilər[ad] || []) f(...a); }

  _bağla() {
    const ta = this.ta;
    ta.addEventListener("beforeinput", (h) => this._öncəDaxiletmə(h));
    ta.addEventListener("input", (h) => this._daxiletmə(h));
    ta.addEventListener("keydown", (h) => this._düymə(h));
    ta.addEventListener("scroll", () => this._sürüşdür());
    // Sətir nömrəsinə klik — dayanma nöqtəsi
    this.qab.querySelector(".r-xətlər").addEventListener("mousedown", (h) => {
      const d = h.target.closest("[data-s]");
      if (!d) return;
      h.preventDefault();
      this.nöqtəDəyiş(+d.dataset.s);
    });
    ta.addEventListener("dblclick", () => {
      this._yay("ikiKlik", ta.selectionStart, ta.selectionEnd);
    });
    document.addEventListener("selectionchange", () => {
      if (document.activeElement === ta) this._kursorDəyişdi();
    });
    ta.addEventListener("keyup", () => this._kursorDəyişdi());
    ta.addEventListener("mouseup", () => this._kursorDəyişdi());
    ta.addEventListener("dragover", (h) => {
      if ([...h.dataTransfer.types].includes("application/x-alqor-vidjet")) {
        h.preventDefault();
        h.dataTransfer.dropEffect = "copy";
        const m = this.mövqeNöqtədən(h.clientX, h.clientY);
        ta.focus();
        ta.setSelectionRange(m, m);
      }
    });
    ta.addEventListener("drop", (h) => {
      const ad = h.dataTransfer.getData("application/x-alqor-vidjet");
      if (!ad) return;
      h.preventDefault();
      this._yay("buraxıldı", this.mövqeNöqtədən(h.clientX, h.clientY), ad);
    });
    new ResizeObserver(() => { this._ölç(); this._sürüşdür(); }).observe(this.sahə);
  }

  _ölç() {
    const st = getComputedStyle(this.ta);
    this.sh = parseFloat(st.lineHeight) || 21;
    const k = document.createElement("canvas").getContext("2d");
    k.font = `${st.fontSize} ${st.fontFamily}`;
    this.sw = k.measureText("MMMMMMMMMM").width / 10 || 8.4;
    this.padL = parseFloat(st.paddingLeft) || 0;
    this.padT = parseFloat(st.paddingTop) || 0;
  }

  // ══ Mətn ═══════════════════════════════════════════════════════════
  get mətn() { return this.ta.value; }
  get kursor() { return this.ta.selectionStart; }

  /** Yeni mətn yükləyir (fayl açılanda). Tarixçə də verilə bilər. */
  yüklə(mətn, v = null) {
    this.ta.value = mətn;
    this.tarixçə = v?.tarixçə || [];
    this.irəli = v?.irəli || [];
    this._sonNöv = null;
    this.diaqnostikalar = v?.diaqnostikalar || [];
    this.vurğular = [];
    const b = v?.baş ?? 0, s = v?.son ?? b;
    this.ta.setSelectionRange(b, s);
    this.ta.scrollTop = v?.scrollTop || 0;
    this.ta.scrollLeft = v?.scrollLeft || 0;
    this.versiya++;
    this.çək();
    this._sürüşdür();
    this._kursorDəyişdi();
  }

  /** Nişan dəyişəndə saxlanılan vəziyyət. */
  vəziyyət() {
    return {
      mətn: this.ta.value, tarixçə: this.tarixçə, irəli: this.irəli,
      baş: this.ta.selectionStart, son: this.ta.selectionEnd,
      scrollTop: this.ta.scrollTop, scrollLeft: this.ta.scrollLeft,
      diaqnostikalar: this.diaqnostikalar,
    };
  }

  fokus() { this.ta.focus({ preventScroll: true }); }

  sətirSütun(mövqe = this.ta.selectionStart) {
    const m = this.ta.value;
    let sətir = 1, baş = 0;
    for (let i = m.indexOf("\n"); i >= 0 && i < mövqe; i = m.indexOf("\n", i + 1)) {
      sətir++; baş = i + 1;
    }
    return { sətir, sütun: mövqe - baş + 1 };
  }

  mövqe(sətir, sütun = 1) {
    const m = this.ta.value;
    let b = 0;
    for (let i = 1; i < sətir; i++) {
      const j = m.indexOf("\n", b);
      if (j < 0) return m.length;
      b = j + 1;
    }
    let son = m.indexOf("\n", b);
    if (son < 0) son = m.length;
    return Math.min(b + Math.max(0, sütun - 1), son);
  }

  mövqeNöqtədən(x, y) {
    const r = this.ta.getBoundingClientRect();
    const sətir = Math.max(0, Math.floor((y - r.top - this.padT + this.ta.scrollTop) / this.sh));
    const sütun = Math.max(0, Math.round((x - r.left - this.padL + this.ta.scrollLeft) / this.sw));
    return this.mövqe(sətir + 1, sütun + 1);
  }

  // ══ Geri al / irəli al ═════════════════════════════════════════════
  _anlıq() {
    return { mətn: this.ta.value, baş: this.ta.selectionStart, son: this.ta.selectionEnd };
  }

  /** Dəyişiklikdən ƏVVƏL çağırılır. Eyni növ ardıcıl yazılar birləşir. */
  _qeyd(növ = null) {
    const indi = Date.now();
    if (növ && növ === this._sonNöv && indi - this._sonVaxt < 1200) {
      this._sonVaxt = indi;
      return;
    }
    this.tarixçə.push(this._anlıq());
    if (this.tarixçə.length > 800) this.tarixçə.shift();
    this.irəli = [];
    this._sonNöv = növ;
    this._sonVaxt = indi;
  }

  _bərpa(a) {
    const əvvəl = this.ta.value;
    this._aralığıƏvəzlə(əvvəl, a.mətn);
    this.ta.setSelectionRange(a.baş, a.son);
    this._sonNöv = null;
    this._dəyişdi();
    this._görünsün();
  }

  geriAl() {
    if (!this.tarixçə.length) return false;
    this.irəli.push(this._anlıq());
    this._bərpa(this.tarixçə.pop());
    return true;
  }

  irəliAl() {
    if (!this.irəli.length) return false;
    this.tarixçə.push(this._anlıq());
    this._bərpa(this.irəli.pop());
    return true;
  }

  // ══ Proqramla dəyişiklik ═══════════════════════════════════════════
  /** Yalnız fərqlənən hissəni əvəzləyir — sürüşdürmə yerində qalır. */
  _aralığıƏvəzlə(köhnə, yeni) {
    let a = 0;
    const max = Math.min(köhnə.length, yeni.length);
    while (a < max && köhnə[a] === yeni[a]) a++;
    let b = 0;
    while (b < max - a && köhnə[köhnə.length - 1 - b] === yeni[yeni.length - 1 - b]) b++;
    this.ta.setRangeText(yeni.slice(a, yeni.length - b), a, köhnə.length - b, "preserve");
  }

  /** [baş, son) aralığını `yeni` ilə əvəzləyir (bir geri al addımı). */
  dəyiş(baş, son, yeni, kursor = baş + yeni.length, növ = null) {
    this._qeyd(növ);
    this.ta.setRangeText(yeni, baş, son, "preserve");
    this.ta.setSelectionRange(kursor, kursor);
    this._dəyişdi();
  }

  /** Bütün mətni əvəzləyir — skelet nəticəsi üçün. */
  mətniƏvəzlə(yeni, kursor = null, yeniSətirlər = []) {
    if (yeni === this.ta.value) return;
    this._qeyd(null);
    this._aralığıƏvəzlə(this.ta.value, yeni);
    if (kursor !== null) this.ta.setSelectionRange(kursor, kursor);
    this._sonNöv = null;
    this.vurğula(yeniSətirlər);
    this._dəyişdi();
    this._görünsün();
  }

  /** Kursora mətn qoyur; çoxsətirli mətn cari girintiyə uyğunlaşır. */
  daxilEt(mətn) {
    const m = this.ta.value;
    const baş = this.ta.selectionStart, son = this.ta.selectionEnd;
    const sb = m.lastIndexOf("\n", baş - 1) + 1;
    const g = (m.slice(sb, baş).match(/^[ \t]*/) || [""])[0];
    const hazır = mətn.split("\n").map((s, i) => (i && s ? g + s : s)).join("\n");
    this.dəyiş(baş, son, hazır, baş + hazır.length);
    this._görünsün();
    this.fokus();
  }

  vurğula(aralıqlar) {
    this.vurğular = (aralıqlar || []).map(([a, b]) => [a, b, Date.now()]);
    this._vurğularıÇək();
    clearTimeout(this._vurğuTaymeri);
    this._vurğuTaymeri = setTimeout(() => {
      this.vurğular = [];
      this._vurğularıÇək();
    }, 2600);
  }

  // ══ Klaviatura ═════════════════════════════════════════════════════
  _öncəDaxiletmə(h) {
    const t = h.inputType || "";
    if (t === "historyUndo" || t === "historyRedo") {
      h.preventDefault();
      if (t === "historyUndo") this.geriAl(); else this.irəliAl();
      return;
    }
    let növ = "yaz";
    if (t.startsWith("delete")) növ = "sil";
    else if (t === "insertFromPaste" || t === "insertFromDrop") növ = null;
    else if (h.data === " ") növ = "boşluq";
    this._qeyd(növ);
  }

  _daxiletmə(h) {
    const ta = this.ta;
    if (h.inputType === "insertText" && h.data && h.data.length === 1
        && ta.selectionStart === ta.selectionEnd) {
      const c = h.data;
      const k = ta.selectionStart;
      // 1. `;` tərkibi: `;e` → `ə`
      if (this.ayarlar.tərkib && !this._tərkibSon && k >= 2
          && ta.value[k - 2] === ";" && this.kompozisiya[c] !== undefined) {
        const hərf = this.kompozisiya[c];
        ta.setRangeText(hərf, k - 2, k, "end");
        this._tərkibSon = c === ";";
        this._dəyişdi();
        return;
      }
      this._tərkibSon = false;
      // 2. ASCII açar söz: `eger` + sərhəd → `əgər`
      if (this.ayarlar.ascii && Redaktor.SƏRHƏDLƏR.has(c)) this._sözüÇevir(k - 1);
      // 3. `yoxsa ` / `tut ` — sətri geri çək
      if (c === " " || c === "(") this._geriÇək(false);
      this._dəyişdi();
      this._yazıldı(c);
      return;
    } else {
      this._tərkibSon = false;
    }
    this._dəyişdi();
    if (this.tmV) this._süz();
  }

  // ══ Tamamlama ══════════════════════════════════════════════════════

  _tamamlaQur() {
    this.tm = document.createElement("div");
    this.tm.className = "r-tamamla";
    this.tm.hidden = true;
    this.tm.setAttribute("role", "listbox");
    this.im = document.createElement("div");
    this.im.className = "r-imza";
    this.im.hidden = true;
    this.qab.append(this.tm, this.im);
    this.tmV = null;              // {hamısı, görünən, seçili}
    this._tmTaymer = 0;
    this._tmSorğu = 0;
    this.tm.addEventListener("mousedown", (h) => {
      const d = h.target.closest("[data-i]");
      h.preventDefault();
      if (d) this._qəbulEt(+d.dataset.i);
    });
    this.ta.addEventListener("blur", () => setTimeout(() => {
      if (document.activeElement !== this.ta) { this.tamamlaBağla(); this.imzaBağla(); }
    }, 120));
    this.ta.addEventListener("mousedown", () => { this.tamamlaBağla(); });
  }

  /** Yazılmış simvola görə tamamlama / imza. */
  _yazıldı(c) {
    if (c === ".") { this.tamamla(false); }
    else if (Redaktor.AD.test(c)) {
      if (this.tmV) this._süz();
      else {
        clearTimeout(this._tmTaymer);
        this._tmTaymer = setTimeout(() => {
          if (this._söz().length >= 2) this.tamamla(false);
        }, 140);
      }
    } else this.tamamlaBağla();
    if (c === "(" || c === ",") this.imzaGöstər();
    else if (c === ")") this.imzaBağla();
  }

  /** Kursordan əvvəlki ad parçası. */
  _söz() {
    const m = this.ta.value, k = this.ta.selectionStart;
    let b = k;
    while (b > 0 && Redaktor.AD.test(m[b - 1])) b--;
    return m.slice(b, k);
  }

  async tamamla(əl = false) {
    if (!this.tamamlayıcı) return;
    const n = ++this._tmSorğu;
    let r;
    try { r = await this.tamamlayıcı(this.ta.selectionStart); } catch { return; }
    if (n !== this._tmSorğu || document.activeElement !== this.ta) return;
    const maddələr = (r && (r.items || r)) || [];
    if (!maddələr.length) { this.tamamlaBağla(); return; }
    this.tmV = { hamısı: maddələr, görünən: [], seçili: 0, əl };
    this._süz();
  }

  _süz() {
    const v = this.tmV;
    if (!v) return;
    const söz = this._söz().toLocaleLowerCase("az");
    const m = this.ta.value, k = this.ta.selectionStart;
    const əvvəl = m[k - söz.length - 1];
    // Ad yazılmırsa (boşluq, mötərizə...) və `.`-dan sonra deyilsə — bağla
    if (!söz && əvvəl !== "." && !v.əl) { this.tamamlaBağla(); return; }
    const n = [];
    for (const x of v.hamısı) {
      const a = (x.filterText || x.label).toLocaleLowerCase("az");
      let xal;
      if (a.startsWith(söz)) xal = 0;
      else if (a.includes(söz)) xal = 1;
      else {
        let i = 0;
        for (const c of a) if (c === söz[i]) i++;
        if (i < söz.length) continue;
        xal = 2;
      }
      n.push([xal, x.sortText || x.label, x]);
    }
    n.sort((p, q) => p[0] - q[0] || p[1].localeCompare(q[1], "az"));
    v.görünən = n.slice(0, 60).map((x) => x[2]);
    if (!v.görünən.length || (v.görünən.length === 1 &&
        (v.görünən[0].filterText || v.görünən[0].label) === this._söz())) {
      this.tamamlaBağla();
      return;
    }
    v.seçili = 0;
    this._tamamlaÇək();
  }

  _kursorXY() {
    const { sətir, sütun } = this.sətirSütun();
    const ta = this.ta.getBoundingClientRect(), q = this.qab.getBoundingClientRect();
    const sətirMətni = this.ta.value.slice(this.ta.selectionStart - sütun + 1, this.ta.selectionStart);
    const en = sətirMətni.replace(/\t/g, "    ").length;
    return {
      x: ta.left - q.left + this.padL + en * this.sw - this.ta.scrollLeft,
      y: ta.top - q.top + this.padT + (sətir - 1) * this.sh - this.ta.scrollTop,
    };
  }

  _tamamlaÇək() {
    const v = this.tmV;
    const sənəd = v.görünən[v.seçili]?.documentation;
    const izah = typeof sənəd === "string" ? sənəd : sənəd?.value || "";
    this.tm.innerHTML = '<div class="r-t-siyahı">' + v.görünən.map((x, i) =>
      `<div class="r-t-maddə${i === v.seçili ? " seçili" : ""}" data-i="${i}" role="option">` +
      `<span class="r-t-növ n${x.kind || 0}">${Redaktor.NÖV_İŞARƏSİ[x.kind] || "·"}</span>` +
      `<span class="r-t-ad">${Redaktor.qaç(x.label)}</span>` +
      `<span class="r-t-detal">${Redaktor.qaç(x.detail || "")}</span></div>`).join("") + "</div>" +
      (izah ? `<div class="r-t-izah">${Redaktor.qaç(izah.replace(/\*\*|`/g, ""))}</div>` : "");
    this.tm.hidden = false;
    const { x, y } = this._kursorXY();
    const q = this.qab.getBoundingClientRect();
    const h = this.tm.offsetHeight, w = this.tm.offsetWidth;
    const aşağı = y + this.sh + h < q.height || y < h;
    this.tm.style.top = `${aşağı ? y + this.sh : y - h}px`;
    this.tm.style.left = `${Math.max(0, Math.min(x - 22, q.width - w - 4))}px`;
    this.tm.querySelector(".seçili")?.scrollIntoView({ block: "nearest" });
  }

  tamamlaBağla() {
    clearTimeout(this._tmTaymer);
    this._tmSorğu++;
    this.tmV = null;
    this.tm.hidden = true;
  }

  _tamamlaDüyməsi(h) {
    if (h.key === "Escape" && !this.im.hidden && !this.tmV) { this.imzaBağla(); h.preventDefault(); return true; }
    const v = this.tmV;
    if (!v || h.isComposing) return false;
    const a = h.key;
    if (a === "ArrowDown" || a === "ArrowUp") {
      h.preventDefault();
      const n = v.görünən.length;
      v.seçili = (v.seçili + (a === "ArrowDown" ? 1 : n - 1)) % n;
      this._tamamlaÇək();
      return true;
    }
    if (a === "PageDown" || a === "PageUp") {
      h.preventDefault();
      v.seçili = Math.max(0, Math.min(v.görünən.length - 1, v.seçili + (a === "PageDown" ? 8 : -8)));
      this._tamamlaÇək();
      return true;
    }
    if ((a === "Enter" || a === "Tab") && !h.shiftKey && !h.ctrlKey && !h.altKey) {
      // Söz artıq tam yazılıbsa Enter adi yeni sətirdir
      const x = v.görünən[v.seçili];
      if (a === "Enter" && x && (x.insertText || x.label) === this._söz()) {
        this.tamamlaBağla();
        return false;
      }
      h.preventDefault();
      this._qəbulEt(v.seçili);
      return true;
    }
    if (a === "Escape") { h.preventDefault(); this.tamamlaBağla(); return true; }
    if (a === "ArrowLeft" || a === "ArrowRight" || a === "Home" || a === "End") this.tamamlaBağla();
    return false;
  }

  /** Seçilmiş maddəni yazır; şablonun (`${1:x}`) ilk yerinə kursor qoyur. */
  _qəbulEt(i) {
    const x = this.tmV?.görünən[i];
    if (!x) return;
    const k = this.ta.selectionStart;
    const baş = k - this._söz().length;
    let mətn = x.insertText || x.label;
    let kursor = null;
    if (x.insertTextFormat === 2) {
      let n = "";
      const rx = /\$\{(\d+)(?::([^}]*))?\}|\$(\d+)/g;
      let son = 0, t;
      while ((t = rx.exec(mətn))) {
        n += mətn.slice(son, t.index);
        if (kursor === null && (t[1] || t[3]) !== "0") kursor = n.length;
        n += t[2] || "";
        son = rx.lastIndex;
      }
      mətn = n + mətn.slice(son);
    }
    const sətirBaşı = this.ta.value.lastIndexOf("\n", baş - 1) + 1;
    const girinti = (this.ta.value.slice(sətirBaşı).match(/^[ \t]*/) || [""])[0];
    if (mətn.includes("\n")) {
      const əvvəlki = mətn;
      mətn = mətn.replace(/\n/g, "\n" + girinti);
      if (kursor !== null) kursor += mətn.length - əvvəlki.length
        - (əvvəlki.slice(kursor).split("\n").length - 1) * girinti.length;
    }
    this.tamamlaBağla();
    this.dəyiş(baş, k, mətn, baş + (kursor ?? mətn.length));
    this.fokus();
    if (mətn.endsWith("(") || mətn[kursor - 1] === "(") this.imzaGöstər();
  }

  // ══ İmza ipucu ═════════════════════════════════════════════════════

  async imzaGöstər() {
    if (!this.imzaVerən) return;
    let r;
    try { r = await this.imzaVerən(this.ta.selectionStart); } catch { return; }
    const i = r?.signatures?.[0];
    if (!i || document.activeElement !== this.ta) { this.imzaBağla(); return; }
    const aktiv = i.parameters?.[r.activeParameter ?? 0]?.label;
    let html = Redaktor.qaç(i.label);
    if (aktiv) {
      const j = i.label.indexOf(aktiv, i.label.indexOf("("));
      if (j >= 0) html = Redaktor.qaç(i.label.slice(0, j)) + "<b>" + Redaktor.qaç(aktiv) + "</b>" +
        Redaktor.qaç(i.label.slice(j + aktiv.length));
    }
    this.im.innerHTML = html;
    this.im.hidden = false;
    const { x, y } = this._kursorXY();
    this.im.style.left = `${Math.max(0, x - 30)}px`;
    this.im.style.top = `${Math.max(0, y - this.im.offsetHeight - 4)}px`;
  }

  imzaBağla() { this.im.hidden = true; }

  // ══ Debaq ══════════════════════════════════════════════════════════

  nöqtəDəyiş(sətir = this.sətirSütun().sətir) {
    if (this.nöqtələr.has(sətir)) this.nöqtələr.delete(sətir);
    else this.nöqtələr.add(sətir);
    this.çək();
    this._yay("nöqtələr", [...this.nöqtələr].sort((a, b) => a - b));
  }

  nöqtələriQoy(sətirlər) {
    this.nöqtələr = new Set(sətirlər || []);
    this.çək();
  }

  /** Debaqda dayanılan sətir (0 — yoxdur). */
  icraSətriniQoy(sətir) {
    this.icraSətri = sətir || 0;
    this.icra.hidden = !this.icraSətri;
    if (this.icraSətri) {
      this.icra.style.top = `${(this.icraSətri - 1) * this.sh + this.padT}px`;
      this.sətirəKeç(this.icraSətri);
    }
    this.çək();
  }

  /** `sonu` mövqeyində bitən söz ASCII açar sözdürsə çevirir. */
  _sözüÇevir(sonu) {
    const m = this.ta.value;
    let b = sonu;
    while (b > 0 && Redaktor.AD.test(m[b - 1])) b--;
    const söz = m.slice(b, sonu);
    const k = AlqorDil.ascii[söz];
    if (!k || k === söz) return false;
    if (b > 0 && m[b - 1] === ".") return false;
    const toks = AlqorDil.tokenlər(m.slice(0, sonu));
    if (!AlqorDil.koddur(toks, b)) return false;
    const s = this.ta.selectionStart, e = this.ta.selectionEnd;
    const fərq = k.length - söz.length;
    this.ta.setRangeText(k, b, sonu, "preserve");
    this.ta.setSelectionRange(s + (s >= sonu ? fərq : 0), e + (e >= sonu ? fərq : 0));
    return true;
  }

  _düymə(h) {
    const ctrl = h.ctrlKey || h.metaKey;
    const a = h.key;
    if (this._tamamlaDüyməsi(h)) return;
    if (ctrl && (a === " " || h.code === "Space")) { h.preventDefault(); this.tamamla(true); return; }
    if (ctrl && !h.altKey && (a === "z" || a === "Z")) {
      h.preventDefault();
      if (h.shiftKey) this.irəliAl(); else this.geriAl();
      return;
    }
    if (ctrl && (a === "y" || a === "Y")) { h.preventDefault(); this.irəliAl(); return; }
    if (ctrl && (a === "s" || a === "S") && !h.shiftKey) {
      h.preventDefault();
      this._yay("saxla");
      return;
    }
    if (ctrl && a === "/") { h.preventDefault(); this.şərhlə(); return; }
    if (h.isComposing) return;
    if (a === "Enter" && !ctrl && !h.altKey) { h.preventDefault(); this._yeniSətir(); return; }
    if (a === "Tab" && !ctrl && !h.altKey) {
      h.preventDefault();
      if (h.shiftKey) this._girintiAzalt(); else this._tab();
      return;
    }
    if (a === "Backspace" && !ctrl && !h.altKey && this._ağıllıSilmə()) {
      h.preventDefault();
      return;
    }
  }

  // ══ Girinti ════════════════════════════════════════════════════════
  static girinti(s) { return (s.match(/^[ \t]*/) || [""])[0].replace(/\t/g, "    ").length; }

  /** Sətrin kod hissəsi: mətn məzmunu və `//` şərhi atılır. */
  static kodHissəsi(s) {
    let n = "", mətndə = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (mətndə) {
        if (c === "\\") { i++; continue; }
        if (c === '"') { mətndə = false; n += c; }
        continue;
      }
      if (c === '"') { mətndə = true; n += c; continue; }
      if (c === "/" && s[i + 1] === "/") break;
      n += c;
    }
    return n.trim();
  }

  /** Bu sətirdən sonra girinti artırmaq lazımdırmı? */
  açandır(sətir) {
    const kod = Redaktor.kodHissəsi(sətir);
    if (!kod) return false;
    if (/[([{]$/.test(kod)) return true;
    // JSX açılan teq: `<div sinif="x">` (bağlanmamış, özü bağlanmayan)
    const teqlər = kod.match(/<\/?[\p{L}][^<>]*?\/?>|<\/?>/gu);
    if (teqlər && kod.endsWith(">")) {
      const son = teqlər[teqlər.length - 1];
      if (!son.startsWith("</") && !son.endsWith("/>")) {
        const ad = (son.match(/^<([\p{L}\p{N}_.-]*)/u) || [])[1] || "";
        if (!kod.includes(`</${ad}>`)) return true;
      }
    }
    const sözlər = kod.split(/\s+/);
    const sonSöz = sözlər[sözlər.length - 1];
    if (sözlər.length > 1 && sonSöz === "son") return false;     // bir sətirlik
    if (["onda", "et", "yoxsa", "nəhayət", "halda", "içində", "dəfə"].includes(sonSöz))
      return true;
    if (/\bfunksiya\s*\([^)]*\)(\s*->\s*\S+)?$/u.test(kod)) return true;
    let i = 0;
    while (i < sözlər.length - 1 && (Redaktor.DƏYİŞDİRİCİ.has(sözlər[i])
           || (sözlər[i] === "son" && /^(sinif|metod)$/.test(sözlər[i + 1])))) i++;
    if (sözlər.slice(0, i).includes("mücərrəd")) return false;
    const ilk = sözlər[i].replace(/[(<:].*$/u, "");
    if (ilk === "hal" || ilk === "digər") return !/→|->/.test(kod);
    if (ilk === "qurucu") return !/\bxassə\b/.test(kod);
    if (ilk === "oxu" || ilk === "yaz") return sözlər.length === 1 && /^(oxu|yaz)$/.test(kod);
    if (ilk === "əgər" || ilk === "varsa" || ilk === "yoxdursa") return true;
    return Redaktor.BLOK_SÖZLƏRİ.has(ilk) || this.blokAçanlar.has(ilk);
  }

  _sətir(mövqe) {
    const m = this.ta.value;
    const b = m.lastIndexOf("\n", mövqe - 1) + 1;
    let s = m.indexOf("\n", mövqe);
    if (s < 0) s = m.length;
    return { b, s, mətn: m.slice(b, s) };
  }

  /** `son`, `yoxsa`, `tut` … — sətri açan blokun səviyyəsinə çəkir. */
  _geriÇək(enter) {
    const k = this.ta.selectionStart;
    const { b } = this._sətir(k);
    const m = this.ta.value;
    const əvvəl = m.slice(b, k).trim();
    const söz = enter ? əvvəl : əvvəl.replace(/[ (]$/, "").trim();
    if (!(Redaktor.GERİ_SÖZLƏR.has(söz) || (enter && /^(son|tut|yoxsa əgər)\b/u.test(söz))
          || (enter && /^[)\]}]/.test(söz)) || (enter && /^<\//.test(söz)))) return;
    // Əvvəlki dolu sətir
    let j = b - 1, əvvəlki = null;
    while (j > 0) {
      const ps = m.lastIndexOf("\n", j - 1) + 1;
      const t = m.slice(ps, j);
      if (t.trim()) { əvvəlki = t; break; }
      j = ps - 1;
    }
    if (əvvəlki === null) return;
    const pg = Redaktor.girinti(əvvəlki);
    const hədəf = this.açandır(əvvəlki) ? pg : Math.max(0, pg - this.ayarlar.girinti);
    const indi = Redaktor.girinti(m.slice(b, k));
    if (indi <= hədəf) return;
    const boşluq = (m.slice(b).match(/^[ \t]*/) || [""])[0].length;
    this.ta.setRangeText(" ".repeat(hədəf), b, b + boşluq, "preserve");
    const yeniK = k - (boşluq - hədəf);
    this.ta.setSelectionRange(yeniK, yeniK);
  }

  _yeniSətir() {
    this._qeyd("sətir");
    this._sonNöv = null;
    const ta = this.ta;
    if (this.ayarlar.ascii && ta.selectionStart === ta.selectionEnd) {
      this._sözüÇevir(ta.selectionStart);
    }
    this._geriÇək(true);
    const baş = ta.selectionStart, son = ta.selectionEnd;
    const m = ta.value;
    const { b } = this._sətir(baş);
    const əvvəl = m.slice(b, baş);
    let g = Redaktor.girinti(əvvəl);
    if (!əvvəl.trim()) g = əvvəl.length;
    const açıq = this.açandır(əvvəl);
    const n = this.ayarlar.girinti;
    const solda = m[baş - 1], sağda = m[son];
    const cüt = { "(": ")", "[": "]", "{": "}" };
    let yeni, kursor;
    if ((cüt[solda] && cüt[solda] === sağda)
        || (/>$/.test(əvvəl) && açıq && m.slice(son, son + 2) === "</")) {
      // `(|)` → üç sətir, kursor ortada
      yeni = "\n" + " ".repeat(g + n) + "\n" + " ".repeat(g);
      kursor = baş + 1 + g + n;
    } else {
      // Kursordan sonrakı boşluqları atırıq
      let s = son;
      while (m[s] === " " || m[s] === "\t") s++;
      yeni = "\n" + " ".repeat(açıq ? g + n : g);
      kursor = baş + yeni.length;
      ta.setRangeText(yeni, baş, s, "preserve");
      ta.setSelectionRange(kursor, kursor);
      this._dəyişdi();
      this._görünsün();
      return;
    }
    ta.setRangeText(yeni, baş, son, "preserve");
    ta.setSelectionRange(kursor, kursor);
    this._dəyişdi();
    this._görünsün();
  }

  _tab() {
    const ta = this.ta, m = ta.value;
    const baş = ta.selectionStart, son = ta.selectionEnd;
    if (m.slice(baş, son).includes("\n")) { this._sətirləriGirintilə(1); return; }
    const { b } = this._sətir(baş);
    const n = this.ayarlar.girinti;
    const say = n - ((baş - b) % n);
    this.dəyiş(baş, son, " ".repeat(say), baş + say, "yaz");
  }

  _girintiAzalt() { this._sətirləriGirintilə(-1); }

  _seçilmişSətirlər() {
    const m = this.ta.value;
    const baş = this.ta.selectionStart;
    let son = this.ta.selectionEnd;
    if (son > baş && m[son - 1] === "\n") son--;
    const b = m.lastIndexOf("\n", baş - 1) + 1;
    let s = m.indexOf("\n", son);
    if (s < 0) s = m.length;
    return [b, s];
  }

  _sətirləriGirintilə(istiqamət) {
    const [b, s] = this._seçilmişSətirlər();
    const m = this.ta.value;
    const n = this.ayarlar.girinti;
    const sətirlər = m.slice(b, s).split("\n").map((t) => {
      if (istiqamət > 0) return t ? " ".repeat(n) + t : t;
      const g = (t.match(/^ */) || [""])[0].length;
      return t.slice(Math.min(g, n));
    });
    const yeni = sətirlər.join("\n");
    this._qeyd(null);
    this.ta.setRangeText(yeni, b, s, "preserve");
    this.ta.setSelectionRange(b, b + yeni.length);
    this._dəyişdi();
  }

  şərhlə() {
    const [b, s] = this._seçilmişSətirlər();
    const m = this.ta.value;
    const sətirlər = m.slice(b, s).split("\n");
    const hamısı = sətirlər.filter((t) => t.trim()).every((t) => /^\s*\/\//.test(t));
    const g = Math.min(...sətirlər.filter((t) => t.trim()).map(Redaktor.girinti), 999);
    const yeni = sətirlər.map((t) => {
      if (!t.trim()) return t;
      if (hamısı) return t.replace(/^(\s*)\/\/ ?/, "$1");
      return t.slice(0, g) + "// " + t.slice(g);
    }).join("\n");
    this._qeyd(null);
    this.ta.setRangeText(yeni, b, s, "preserve");
    this.ta.setSelectionRange(b, b + yeni.length);
    this._dəyişdi();
  }

  /** Sətir başındakı boşluqda Backspace — bir girinti addımı silir. */
  _ağıllıSilmə() {
    const ta = this.ta;
    const k = ta.selectionStart;
    if (k !== ta.selectionEnd || k === 0) return false;
    const { b } = this._sətir(k);
    const əvvəl = ta.value.slice(b, k);
    if (!əvvəl || /[^ ]/.test(əvvəl)) return false;
    const n = this.ayarlar.girinti;
    const say = əvvəl.length % n || n;
    this.dəyiş(k - say, k, "", k - say, "sil");
    return true;
  }

  // ══ Axtarış ════════════════════════════════════════════════════════
  axtar(sorğu, { hərfə = false, regex = false } = {}) {
    this.axtarış = { nəticələr: [], cari: -1, sorğu, hərfə, regex };
    if (!sorğu) { this.çək(); return 0; }
    let ifadə;
    try {
      const naxış = regex ? sorğu : sorğu.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      ifadə = new RegExp(naxış, "gu" + (hərfə ? "" : "i"));
    } catch (_) { this.çək(); return -1; }
    const m = this.ta.value;
    for (const a of m.matchAll(ifadə)) {
      if (!a[0].length) break;
      this.axtarış.nəticələr.push([a.index, a.index + a[0].length]);
      if (this.axtarış.nəticələr.length >= 5000) break;
    }
    this.çək();
    return this.axtarış.nəticələr.length;
  }

  növbətiNəticə(geri = false) {
    const n = this.axtarış.nəticələr;
    if (!n.length) return -1;
    const k = geri ? this.ta.selectionStart : this.ta.selectionEnd;
    let i;
    if (geri) {
      i = n.length - 1;
      for (let j = n.length - 1; j >= 0; j--) if (n[j][0] < k) { i = j; break; }
    } else {
      i = 0;
      for (let j = 0; j < n.length; j++) if (n[j][0] >= k) { i = j; break; }
    }
    this.axtarış.cari = i;
    this.ta.setSelectionRange(n[i][0], n[i][1]);
    this._görünsün();
    this.çək();
    this._kursorDəyişdi();
    return i;
  }

  əvəzlə(yeni) {
    const { nəticələr, cari } = this.axtarış;
    const n = nəticələr[cari];
    if (n && this.ta.selectionStart === n[0] && this.ta.selectionEnd === n[1]) {
      this.dəyiş(n[0], n[1], yeni, n[0] + yeni.length);
      const { sorğu, hərfə, regex } = this.axtarış;
      this.axtar(sorğu, { hərfə, regex });
    }
    return this.növbətiNəticə();
  }

  hamısınıƏvəzlə(yeni) {
    const n = this.axtarış.nəticələr;
    if (!n.length) return 0;
    const m = this.ta.value;
    let nəticə = "", son = 0;
    for (const [a, b] of n) { nəticə += m.slice(son, a) + yeni; son = b; }
    nəticə += m.slice(son);
    this.mətniƏvəzlə(nəticə, this.ta.selectionStart);
    const say = n.length;
    this.axtarış.nəticələr = [];
    this.çək();
    return say;
  }

  // ══ Diaqnostika və naviqasiya ══════════════════════════════════════
  diaqnostikaQoy(siyahı) {
    this.diaqnostikalar = siyahı || [];
    this.çək();
  }

  sətirəKeç(sətir, sütun = 1, uzunluq = 0) {
    const m = this.mövqe(sətir, sütun);
    this.fokus();
    this.ta.setSelectionRange(m, m + uzunluq);
    this._görünsün(true);
    this._kursorDəyişdi();
  }

  /** Kursor görünən sahədə olsun. */
  _görünsün(mərkəz = false) {
    const ta = this.ta;
    const { sətir, sütun } = this.sətirSütun(ta.selectionEnd);
    const y = (sətir - 1) * this.sh;
    const h = ta.clientHeight - 2 * this.padT;
    if (mərkəz && (y < ta.scrollTop || y > ta.scrollTop + h - this.sh)) {
      ta.scrollTop = Math.max(0, y - h / 3);
    } else if (y < ta.scrollTop) ta.scrollTop = y;
    else if (y + this.sh > ta.scrollTop + h) ta.scrollTop = y + this.sh - h + this.sh;
    const x = (sütun - 1) * this.sw;
    const w = ta.clientWidth - 2 * this.padL;
    if (x < ta.scrollLeft) ta.scrollLeft = Math.max(0, x - 40);
    else if (x > ta.scrollLeft + w - this.sw) ta.scrollLeft = x - w + 80;
    this._sürüşdür();
  }

  // ══ Çəkmə ══════════════════════════════════════════════════════════
  _dəyişdi() {
    this.versiya++;
    this._çəkməyiPlanla();
    this._yay("dəyişdi", this.versiya);
    this._kursorDəyişdi();
  }

  _çəkməyiPlanla() {
    if (this._çəkmə) return;
    this._çəkmə = requestAnimationFrame(() => { this._çəkmə = 0; this.çək(); });
  }

  _kursorDəyişdi() {
    const { sətir, sütun } = this.sətirSütun();
    this.cari.style.top = `${(sətir - 1) * this.sh + this.padT}px`;
    if (sətir !== this._sonSətir || sütun !== this._sonSütun) {
      this._sonSətir = sətir; this._sonSütun = sütun;
      this._yay("kursor", sətir, sütun);
    }
  }

  _sürüşdür() {
    const x = this.ta.scrollLeft, y = this.ta.scrollTop;
    this.örtük.style.transform = `translate(${-x}px, ${-y}px)`;
    this.fon.style.transform = `translate(${-x}px, ${-y}px)`;
    this.nömrələr.style.transform = `translateY(${-y}px)`;
  }

  _vurğularıÇək() {
    this.vurğuQabı.innerHTML = this.vurğular.map(([a, b]) =>
      `<div class="r-vurğu" style="top:${(a - 1) * this.sh + this.padT}px;` +
      `height:${(b - a + 1) * this.sh}px"></div>`).join("");
  }

  static qaç(s) {
    return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  }

  çək() {
    const m = this.ta.value;
    const n = m.length;
    const toks = AlqorDil.tokenlər(m);
    this.tokenlər = toks;

    // Bəzəklər: 1 xəta, 2 xəbərdarlıq, 4 axtarış, 8 cari nəticə
    const bəzək = new Uint8Array(n + 1);
    const sətirBaşları = [0];
    for (let i = m.indexOf("\n"); i >= 0; i = m.indexOf("\n", i + 1)) sətirBaşları.push(i + 1);
    const ofset = (s, st) => {
      const b = sətirBaşları[Math.min(Math.max(s, 1), sətirBaşları.length) - 1] ?? n;
      return Math.min(n, b + Math.max(0, st - 1));
    };
    const sətirİşarəsi = {};
    for (const d of this.diaqnostikalar) {
      const bit = d.səviyyə === "xəta" ? 1 : d.səviyyə === "xəbərdarlıq" ? 2 : 0;
      if (!bit) continue;
      let a = ofset(d.sətir, d.sütun);
      let b = ofset(d.sonSətir || d.sətir, d.sonSütun || d.sütun + 1);
      if (b <= a) b = a + 1;
      // Sətir sonundakı xəta görünsün — bir simvol geri
      if (a >= n || m[a] === "\n") { a = Math.max(0, a - 1); b = a + 1; }
      for (let i = a; i < Math.min(b, n); i++) bəzək[i] |= bit;
      sətirİşarəsi[d.sətir] = Math.min(sətirİşarəsi[d.sətir] || 9, bit);
    }
    this.axtarış.nəticələr.forEach(([a, b], i) => {
      const bit = i === this.axtarış.cari ? 12 : 4;
      for (let j = a; j < b; j++) bəzək[j] |= bit;
    });

    // Simvol → token sinfi
    const sinif = new Array(n);
    for (const [a, b, s] of toks) for (let i = a; i < b; i++) sinif[i] = s;

    const hissələr = [];
    let i = 0;
    while (i < n) {
      const s = sinif[i] || "", d = bəzək[i];
      let j = i + 1;
      while (j < n && (sinif[j] || "") === s && bəzək[j] === d) j++;
      const parça = Redaktor.qaç(m.slice(i, j));
      let siniflər = s ? s.split(" ").map((x) => "t-" + x).join(" ") : "";
      if (d & 1) siniflər += " d-xəta";
      else if (d & 2) siniflər += " d-xəbərdarlıq";
      if (d & 8) siniflər += " d-cari-tapıntı";
      else if (d & 4) siniflər += " d-tapıntı";
      siniflər = siniflər.trim();
      hissələr.push(siniflər ? `<span class="${siniflər}">${parça}</span>` : parça);
      i = j;
    }
    this.örtük.innerHTML = hissələr.join("") + "\n ";

    // Sətir nömrələri
    const say = sətirBaşları.length;
    const açar = JSON.stringify([sətirİşarəsi, [...this.nöqtələr], this.icraSətri]);
    if (say !== this._sətirSayı || this._işarələr !== açar) {
      this._sətirSayı = say;
      this._işarələr = açar;
      const nm = [];
      for (let s = 1; s <= say; s++) {
        const iş = sətirİşarəsi[s];
        let sinif = iş ? (iş === 1 ? "n-xəta" : "n-xəbərdarlıq") : "";
        if (this.nöqtələr.has(s)) sinif += " n-nöqtə";
        if (this.icraSətri === s) sinif += " n-icra";
        nm.push(`<div data-s="${s}"${sinif ? ` class="${sinif.trim()}"` : ""}>${s}</div>`);
      }
      this.nömrələr.innerHTML = nm.join("");
      this.qab.style.setProperty("--xətt-eni", `${Math.max(3, String(say).length) + 2}ch`);
    }
    this._vurğularıÇək();
    this._sürüşdür();
  }
}

Redaktor.AD = /[\p{L}\p{N}_]/u;
// LSP CompletionItemKind → qısa işarə
Redaktor.NÖV_İŞARƏSİ = { 2: "m", 3: "ƒ", 4: "ƒ", 5: "x", 6: "v", 7: "S", 8: "İ", 9: "M",
  10: "x", 13: "E", 14: "★", 15: "⋯", 20: "e", 21: "c", 22: "S", 25: "T" };
Redaktor.SƏRHƏDLƏR = new Set([..." \t()[]{},:.=<>!+-*/%&|^?"]);
Redaktor.GERİ_SÖZLƏR = new Set(["son", "yoxsa", "nəhayət", "əks halda", "tut"]);
Redaktor.DƏYİŞDİRİCİ = new Set(["açıq", "gizli", "qorunan", "statik", "mücərrəd",
  "tənbəl", "asinxron", "generator", "ixrac", "əvəz", "et", "sabit", "@yaddaşla"]);
Redaktor.BLOK_SÖZLƏRİ = new Set([
  "funksiya", "metod", "sinif", "struktur", "interfeys", "sadalama", "modul",
  "obyekt", "qarışıq", "komponent", "mağaza", "genişlət", "silinsin", "seç",
  "hər", "həmişə", "təkrarla", "istifadə", "təmin", "cəhd", "nə",
  "hesablanan", "əməl", "göstər", "başlanğıc", "bitiş", "blok", "tut",
  "nəhayət", "yoxsa", "əks",
]);
