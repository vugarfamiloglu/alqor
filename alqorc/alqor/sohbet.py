"""
Alqor — İnteraktiv rejim (REPL / söhbət).

    $ python alqorc.py söhbət
    Alqor 2.3.1 — interaktiv rejim. Kömək üçün :kömək
    alqor> 2 + 2
    4

Xüsusiyyətlər:
  • Çoxsətirli giriş — blok bitənə qədər `  ...` davam sətri
  • İfadənin nəticəsi avtomatik çap olunur
  • Vəziyyət sətirlər arasında saxlanılır
  • `:` ilə başlayan meta-əmrlər
  • Tarixçə (`~/.alqor/tarixce`) və tamamlama (readline olduqda)
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Any

from . import VERSIYA
from . import aac as A
from . import acar_sozler as AS
from .deyerler import (AlqorXəta, Çağırılan, DayanmaSiqnalı, Daxili,
                       Modul, Mühit, Nümunə, QaytarSiqnalı, Sadalama,
                       Sinif, _daxili_mətn, mətnə, tip_adı)
from .icraci import İcraçı
from .lekser import Lekser
from .menbe import Mənbə
from .parser import Parser
from .xeta import Diaqnostika, Səviyyə, XətaToplayıcı, rənglər_açıqdır

ƏSAS_SƏTİR = "alqor> "
DAVAM_SƏTRİ = "  ... "
TARİXÇƏ_YOLU = Path.home() / ".alqor" / "tarixce"
TARİXÇƏ_HƏDDİ = 2000

# Girişin yarımçıq olduğunu bildirən leksik xətalar
YARIMÇIQ_KODLAR = {"ALQ-L003", "ALQ-L004", "ALQ-L011", "ALQ-L017"}


# ═══════════════════════════════════════════════════════════════════════
#  Rəng
# ═══════════════════════════════════════════════════════════════════════

class Boya:
    def __init__(self, aktiv: bool):
        self.aktiv = aktiv

    def _r(self, m: str, kod: str) -> str:
        return f"\033[{kod}m{m}\033[0m" if self.aktiv else m

    def solğun(self, m): return self._r(m, "90")
    def yaşıl(self, m): return self._r(m, "32")
    def sarı(self, m): return self._r(m, "33")
    def qırmızı(self, m): return self._r(m, "31")
    def mavi(self, m): return self._r(m, "36")
    def qalın(self, m): return self._r(m, "1")


# ═══════════════════════════════════════════════════════════════════════
#  Yarımçıq giriş aşkarlanması
# ═══════════════════════════════════════════════════════════════════════

def yarımçıqdır(mətn: str) -> bool:
    """
    Giriş hələ bitməyibmi? (açıq blok, bağlanmamış mötərizə/mətn)

    Lekserin kontekst yığınından istifadə edir — `funksiya f()` yazılıbsa
    yığında BLOK qalır, deməli `son` gözlənilir.
    """
    if not mətn.strip():
        return False
    x = XətaToplayıcı()
    s = Mənbə.mətndən(mətn, "<söhbət>", x)
    lekser = Lekser(s, x, ascii_xəbərdarlığı=False)
    try:
        lekser.leksə()
    except Exception:
        return False
    for d in x.xətalar:
        if d.kod in YARIMÇIQ_KODLAR:
            return True
    return bool(lekser.yığın)


# ═══════════════════════════════════════════════════════════════════════
#  Söhbət
# ═══════════════════════════════════════════════════════════════════════

class Söhbət:
    def __init__(self, rəngli: bool | None = None):
        self.b = Boya(rənglər_açıqdır() if rəngli is None else rəngli)
        self.icraçı = İcraçı()
        self.mühit = self.icraçı.qlobal
        # Ad → ilkin dəyər. Dəyər dəyişibsə, istifadəçi onu kölgələyib
        # (`dəyişən siyahı = [...]`) və `:siyahı`-da görünməlidir.
        self.daxili_dəyərlər = dict(self.mühit.adlar)
        self.tarixçə: list[str] = []
        self.sayğac = 0
        self.ascii_xəbərdarlığı = True
        self.son_dəyər: Any = None
        self._readline_qur()

    # ── readline (varsa) ──────────────────────────────────────────────

    def _readline_qur(self) -> None:
        self.readline = None
        try:
            import readline
        except ImportError:
            try:
                import pyreadline3 as _p          # type: ignore
                import readline                   # noqa: F811
            except ImportError:
                return
        self.readline = readline
        try:
            readline.set_completer(self._tamamla)
            readline.parse_and_bind("tab: complete")
            readline.set_completer_delims(" \t\n()[]{},;:+-*/%<>=!|&")
        except Exception:
            pass
        if TARİXÇƏ_YOLU.exists():
            try:
                readline.read_history_file(str(TARİXÇƏ_YOLU))
            except Exception:
                pass

    def _tarixçəni_saxla(self) -> None:
        if self.readline is None:
            return
        try:
            TARİXÇƏ_YOLU.parent.mkdir(parents=True, exist_ok=True)
            self.readline.set_history_length(TARİXÇƏ_HƏDDİ)
            self.readline.write_history_file(str(TARİXÇƏ_YOLU))
        except Exception:
            pass

    def _tamamla(self, parça: str, indeks: int):
        """Tab ilə tamamlama: açar sözlər, tip adları, elan olunmuş adlar."""
        namizədlər = sorted(
            set(AS.ACAR_SOZLER) | set(AS.TIP_ADLARI)
            | set(self.mühit.adlar) | {f":{a}" for a in META_ƏMRLƏR})
        uyğunlar = [n for n in namizədlər if n.startswith(parça)]
        return uyğunlar[indeks] if indeks < len(uyğunlar) else None

    # ── Əsas dövr ─────────────────────────────────────────────────────

    def işlət(self) -> int:
        self._başlıq()
        bufer: list[str] = []
        boş_sətir_sayı = 0

        while True:
            sətir_başlığı = DAVAM_SƏTRİ if bufer else ƏSAS_SƏTİR
            try:
                sətir = input(self.b.solğun(sətir_başlığı)
                              if bufer else self.b.yaşıl(sətir_başlığı))
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print(self.b.solğun("  (ləğv edildi)"))
                bufer.clear()
                boş_sətir_sayı = 0
                continue

            # ── Meta-əmrlər (yalnız bufer boş olanda) ───────────
            if not bufer and sətir.strip().startswith(":"):
                if self._meta(sətir.strip()) == "çıx":
                    break
                continue

            if not sətir.strip() and not bufer:
                continue

            # ── Boş sətir: ikincisi blokdan çıxarır ─────────────
            if not sətir.strip() and bufer:
                boş_sətir_sayı += 1
                if boş_sətir_sayı >= 2:
                    print(self.b.solğun(
                        "  (yarımçıq giriş ləğv edildi — "
                        "`:ləğv` də işləyir)"))
                    bufer.clear()
                    boş_sətir_sayı = 0
                    continue
            else:
                boş_sətir_sayı = 0

            bufer.append(sətir)
            mətn = "\n".join(bufer)

            if yarımçıqdır(mətn):
                continue

            bufer.clear()
            boş_sətir_sayı = 0
            if mətn.strip():
                self.tarixçə.append(mətn)
                self._icra(mətn)

        self._tarixçəni_saxla()
        print(self.b.solğun("Sağ olun!"))
        return 0

    def _başlıq(self) -> None:
        b = self.b
        print(b.qalın(f"Alqor {VERSIYA}") + " — interaktiv rejim")
        print(b.solğun("Azərbaycan dilində proqramlaşdırma dili"))
        print()
        print(b.solğun("  :kömək   bütün əmrlər"))
        print(b.solğun("  :çıx     çıxış (Ctrl+D də işləyir)"))
        if self.readline is None:
            print(b.solğun("  ⚠ readline yoxdur — tarixçə və tamamlama "
                           "söndürülüb"))
            print(b.solğun("    aktivləşdirmək: pip install pyreadline3"))
        print()

    # ── Kodun icrası ──────────────────────────────────────────────────

    def _icra(self, mətn: str) -> None:
        self.sayğac += 1
        x = XətaToplayıcı()
        s = Mənbə.mətndən(mətn, "<söhbət>", x)
        tokenlər = Lekser(s, x,
                          ascii_xəbərdarlığı=self.ascii_xəbərdarlığı
                          ).leksə()
        ağac = Parser(tokenlər, s, x).ayır()

        if not x.uğurludur():
            self._diaqnostika_çap(x, s)
            return
        self._xəbərdarlıqları_çap(x)

        try:
            self._ağacı_icra(ağac)
        except AlqorXəta as xəta:
            self._icra_xətası(xəta, s)
        except DayanmaSiqnalı:
            print(self.b.solğun("  (dayan çağırıldı — söhbətdə "
                                "nəzərə alınmır)"))
        except QaytarSiqnalı:
            print(self.b.sarı("  ⚠ `qaytar` funksiyadan kənarda"))
        except RecursionError:
            print(self.b.qırmızı(
                "  ✖ StekDaşmaXətası: çağırış dərinliyi həddi aşıldı"))
        except KeyboardInterrupt:
            print(self.b.solğun("\n  (icra dayandırıldı)"))

    def _ağacı_icra(self, ağac: A.Proqram) -> None:
        """
        Elanları qaldırır, cümlələri icra edir, SON ifadənin dəyərini
        çap edir (REPL davranışı).
        """
        gövdə = ağac.gövdə
        if not gövdə:
            return

        self.icraçı._elanları_qaldır(gövdə, self.mühit)

        son = gövdə[-1]
        çap_edilən = (son if isinstance(son, A.İfadəCümləsi)
                      and not isinstance(son.ifadə, A.Mənimsətmə)
                      else None)

        for c in gövdə:
            if self.icraçı._elandır(c):
                self._elan_xəbəri(c)
                continue
            if c is çap_edilən:
                dəyər = self.icraçı._ifadə(c.ifadə, self.mühit)
                self._dəyər_çap(dəyər)
            else:
                self.icraçı._cümlə(c, self.mühit)

    def _elan_xəbəri(self, c: A.Cümlə) -> None:
        """Elanlar `_elanları_qaldır`-da işlənib — istifadəçiyə bildir."""
        ad = getattr(c, "ad", None)
        if ad is None:
            return
        növ = {
            A.FunksiyaElanı: "funksiya",
            A.SinifElanı: "sinif",
            A.InterfeysElanı: "interfeys",
            A.SadalamaElanı: "sadalama",
            A.QarışıqElanı: "qarışıq",
            A.TipAliası: "tip",
        }.get(type(c), "elan")
        if isinstance(c, A.SinifElanı):
            növ = c.quruluş
        print(self.b.solğun(f"  {növ} `{ad}` təyin edildi"))

    def _dəyər_çap(self, dəyər: Any) -> None:
        if dəyər is None:
            return
        self.son_dəyər = dəyər
        # `_` atma tokenidir (OP), dəyişən ola bilməz — `nəticə` işlədirik
        self.mühit.adlar["nəticə"] = dəyər
        mətn = (_daxili_mətn(dəyər, self.icraçı)
                if isinstance(dəyər, str)
                else mətnə(dəyər, self.icraçı))
        tip = tip_adı(dəyər)
        print(f"{mətn}  {self.b.solğun('// ' + tip)}")

    # ── Diaqnostika ───────────────────────────────────────────────────

    def _diaqnostika_çap(self, x: XətaToplayıcı, mənbə: Mənbə) -> None:
        for d in x.xətalar[:3]:
            print(d.formatla(rəngli=self.b.aktiv), file=sys.stderr)
        if len(x.xətalar) > 3:
            print(self.b.solğun(f"  … və {len(x.xətalar) - 3} xəta daha"),
                  file=sys.stderr)

    def _xəbərdarlıqları_çap(self, x: XətaToplayıcı) -> None:
        """Söhbətdə xəbərdarlıqlar qısa — bir sətirlik."""
        for d in x.xəbərdarlıqlar:
            qeyd = f" — {d.qeyd}" if d.qeyd else ""
            print(self.b.sarı(f"  ⚠ {d.kod} {d.mesaj}{qeyd}"))

    def _icra_xətası(self, xəta: AlqorXəta, mənbə: Mənbə) -> None:
        d = Diaqnostika(xəta.kod or "ALQ-R000",
                        f"{xəta.tip}: {xəta.mesaj}",
                        xəta.yer, Səviyyə.XETA,
                        "burada baş verdi" if xəta.yer else "")
        print(d.formatla(rəngli=self.b.aktiv), file=sys.stderr)

    # ═══════════════════════════════════════════════════════════════════
    #  Meta-əmrlər
    # ═══════════════════════════════════════════════════════════════════

    def _meta(self, sətir: str) -> str | None:
        hissələr = sətir[1:].split(None, 1)
        if not hissələr:
            return None
        əmr = hissələr[0]
        arq = hissələr[1].strip() if len(hissələr) > 1 else ""

        işləyici = META_ƏMRLƏR.get(əmr)
        if işləyici is None:
            # Yaxın əmr təklif et
            yaxın = [a for a in META_ƏMRLƏR if a.startswith(əmr[:2])]
            print(self.b.qırmızı(f"  ✖ naməlum əmr: :{əmr}"))
            if yaxın:
                print(self.b.solğun(
                    f"    bəlkə: {', '.join(':' + a for a in sorted(set(yaxın))[:4])}"))
            else:
                print(self.b.solğun("    `:kömək` yazın"))
            return None
        return işləyici(self, arq)

    # ── Əmrlər ────────────────────────────────────────────────────────

    def m_kömək(self, arq: str) -> None:
        b = self.b
        print(b.qalın("Meta-əmrlər"))
        for ad, təsvir in KÖMƏK_MƏTNİ:
            print(f"  {b.mavi(':' + ad):<28} {b.solğun(təsvir)}")
        print()
        print(b.qalın("İpucları"))
        for ipucu in İPUCLARI:
            print(f"  {b.solğun('•')} {ipucu}")

    def m_çıx(self, arq: str) -> str:
        return "çıx"

    def m_ləğv(self, arq: str) -> None:
        print(self.b.solğun("  (bufer boşdur)"))

    def m_tip(self, arq: str) -> None:
        if not arq:
            print(self.b.sarı("  istifadə: :tip <ifadə>"))
            return
        dəyər, uğurlu = self._qiymətləndir(arq)
        if uğurlu:
            print(f"  {self.b.mavi(tip_adı(dəyər))}")

    def m_siyahı(self, arq: str) -> None:
        adlar = {
            a: d for a, d in self.mühit.adlar.items()
            if not a.startswith("__")
            and (a not in self.daxili_dəyərlər
                 or self.daxili_dəyərlər[a] is not d)
        }
        if not adlar:
            print(self.b.solğun("  (hələ heç nə təyin edilməyib)"))
            return
        qruplar: dict[str, list[str]] = {}
        for ad, dəyər in sorted(adlar.items()):
            qrup = self._qrup(dəyər)
            qruplar.setdefault(qrup, []).append(ad)
        for qrup in ("funksiya", "sinif", "sadalama", "modul", "dəyişən"):
            if qrup not in qruplar:
                continue
            print(f"  {self.b.qalın(qrup)}:")
            for ad in qruplar[qrup]:
                dəyər = adlar[ad]
                if qrup == "dəyişən":
                    qısa = mətnə(dəyər, self.icraçı)
                    if len(qısa) > 40:
                        qısa = qısa[:37] + "..."
                    print(f"    {ad:<20} {self.b.solğun(tip_adı(dəyər))}"
                          f"  = {qısa}")
                else:
                    print(f"    {ad}")

    @staticmethod
    def _qrup(dəyər: Any) -> str:
        if isinstance(dəyər, Sinif):
            return "sinif"
        if isinstance(dəyər, Sadalama):
            return "sadalama"
        if isinstance(dəyər, Modul):
            return "modul"
        if isinstance(dəyər, Çağırılan):
            return "funksiya"
        return "dəyişən"

    def m_təmizlə(self, arq: str) -> None:
        self.icraçı = İcraçı()
        self.mühit = self.icraçı.qlobal
        self.daxili_dəyərlər = dict(self.mühit.adlar)
        self.sayğac = 0
        self.son_dəyər = None
        print(self.b.yaşıl("  ✓ mühit təmizləndi"))

    def m_yüklə(self, arq: str) -> None:
        if not arq:
            print(self.b.sarı("  istifadə: :yüklə <fayl.alq>"))
            return
        yol = Path(arq)
        if not yol.exists():
            for uzantı in (".alq", ".alqor"):
                if Path(arq + uzantı).exists():
                    yol = Path(arq + uzantı)
                    break
        if not yol.exists():
            print(self.b.qırmızı(f'  ✖ "{arq}" tapılmadı'))
            return
        try:
            mətn = yol.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(self.b.qırmızı(f'  ✖ "{yol.name}" UTF-8 deyil'))
            return
        print(self.b.solğun(f"  → {yol.name} yüklənir "
                            f"({len(mətn.splitlines())} sətir)"))
        self._icra(mətn)

    def m_vaxt(self, arq: str) -> None:
        if not arq:
            print(self.b.sarı("  istifadə: :vaxt <ifadə>"))
            return
        başlanğıc = time.perf_counter()
        dəyər, uğurlu = self._qiymətləndir(arq)
        müddət = (time.perf_counter() - başlanğıc) * 1000
        if uğurlu:
            if dəyər is not None:
                self._dəyər_çap(dəyər)
            print(self.b.solğun(f"  ⏱ {müddət:.3f} ms"))

    def m_tokenlər(self, arq: str) -> None:
        if not arq:
            print(self.b.sarı("  istifadə: :tokenlər <kod>"))
            return
        from .token import Növ
        x = XətaToplayıcı()
        s = Mənbə.mətndən(arq, "<söhbət>", x)
        for t in Lekser(s, x).leksə():
            if t.növ is Növ.FAYL_SONU:
                continue
            if t.növ is Növ.SETIR_SONU:
                print(self.b.solğun("    ⏎"))
                continue
            əlavə = (self.b.sarı(f"  ← ASCII: {t.xam!r}")
                     if t.ascii_idi else "")
            print(f"    {self.b.mavi(t.növ.name):<20} {t.dəyər!r}{əlavə}")

    def m_aac(self, arq: str) -> None:
        if not arq:
            print(self.b.sarı("  istifadə: :aac <kod>"))
            return
        x = XətaToplayıcı()
        s = Mənbə.mətndən(arq, "<söhbət>", x)
        ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
        if not x.uğurludur():
            self._diaqnostika_çap(x, s)
            return
        print(A.göstər(ağac.gövdə if len(ağac.gövdə) != 1
                       else ağac.gövdə[0]))

    def m_tarixçə(self, arq: str) -> None:
        if not self.tarixçə:
            print(self.b.solğun("  (tarixçə boşdur)"))
            return
        n = int(arq) if arq.isdigit() else 20
        for i, giriş in enumerate(self.tarixçə[-n:], 1):
            ilk, *qalan = giriş.split("\n")
            print(f"  {self.b.solğun(f'{i:3}')} {ilk}")
            for sətir in qalan:
                print(f"      {sətir}")

    def m_saxla(self, arq: str) -> None:
        if not arq:
            print(self.b.sarı("  istifadə: :saxla <fayl.alq>"))
            return
        yol = Path(arq if arq.endswith((".alq", ".alqor"))
                   else arq + ".alq")
        məzmun = ("// Alqor söhbət seansı\n\n"
                  + "\n\n".join(self.tarixçə) + "\n")
        try:
            yol.write_text(məzmun, encoding="utf-8", newline="\n")
        except OSError as e:
            print(self.b.qırmızı(f"  ✖ yazılmadı: {e}"))
            return
        print(self.b.yaşıl(f"  ✓ {yol} saxlanıldı "
                           f"({len(self.tarixçə)} giriş)"))

    def m_ascii(self, arq: str) -> None:
        a = arq.strip().lower()
        if a in ("aç", "ac", "on"):
            self.ascii_xəbərdarlığı = True
        elif a in ("qapat", "söndür", "sondur", "off"):
            self.ascii_xəbərdarlığı = False
        else:
            print(self.b.sarı("  istifadə: :ascii aç | :ascii qapat"))
            return
        vəziyyət = "açıq" if self.ascii_xəbərdarlığı else "qapalı"
        print(self.b.yaşıl(f"  ✓ ASCII xəbərdarlığı {vəziyyət}"))

    def m_hərflər(self, arq: str) -> None:
        b = self.b
        print(b.qalın("  Azərbaycan hərfləri — kopyalayın"))
        print(f"    {b.mavi('ə ı ğ ş ç ö ü İ')}")
        print(f"    {b.mavi('Ə I Ğ Ş Ç Ö Ü')}")
        print()
        print(b.qalın("  ASCII yazsanız, kompilyator özü başa düşür"))
        nümunələr = [("eger", "əgər"), ("deyisen", "dəyişən"),
                     ("ne qeder ki", "nə qədər ki"), ("ucun", "üçün"),
                     ("icinde", "içində"), ("her", "hər"),
                     ("cehd et", "cəhd et"), ("qaytar", "qaytar")]
        for ascii_, kanonik in nümunələr:
            print(f"    {ascii_:<14} → {b.mavi(kanonik)}")
        print()
        print(b.solğun("  DİQQƏT: bu yalnız AÇAR SÖZLƏRƏ aiddir."))
        print(b.solğun("  Dəyişən adlarında `yaş` ≠ `yas`."))

    def m_əlifba(self, arq: str) -> None:
        from .elifba import BOYUK, KICIK
        print(f"  {self.b.qalın('Azərbaycan əlifbası')} (32 hərf)")
        print(f"    {' '.join(KICIK)}")
        print(f"    {' '.join(BOYUK)}")
        print()
        print(self.b.solğun("  Sıralama bu ardıcıllıqla aparılır — "
                            "Unicode-un öz sırası yanlışdır."))

    # ── Köməkçi ───────────────────────────────────────────────────────

    def _qiymətləndir(self, kod: str) -> tuple[Any, bool]:
        """Bir ifadəni qiymətləndirir: (dəyər, uğurlu)."""
        x = XətaToplayıcı()
        s = Mənbə.mətndən(kod, "<söhbət>", x)
        ağac = Parser(Lekser(s, x, ascii_xəbərdarlığı=False).leksə(),
                      s, x).ayır()
        if not x.uğurludur():
            self._diaqnostika_çap(x, s)
            return None, False
        if (len(ağac.gövdə) != 1
                or not isinstance(ağac.gövdə[0], A.İfadəCümləsi)):
            print(self.b.sarı("  ⚠ bir ifadə gözlənilirdi"))
            return None, False
        try:
            return self.icraçı._ifadə(ağac.gövdə[0].ifadə, self.mühit), True
        except AlqorXəta as xəta:
            self._icra_xətası(xəta, s)
            return None, False


# ═══════════════════════════════════════════════════════════════════════
#  Əmr cədvəli
# ═══════════════════════════════════════════════════════════════════════

META_ƏMRLƏR = {
    "kömək": Söhbət.m_kömək, "komek": Söhbət.m_kömək, "k": Söhbət.m_kömək,
    "?": Söhbət.m_kömək,
    "çıx": Söhbət.m_çıx, "cix": Söhbət.m_çıx, "q": Söhbət.m_çıx,
    "ləğv": Söhbət.m_ləğv, "legv": Söhbət.m_ləğv,
    "tip": Söhbət.m_tip, "t": Söhbət.m_tip,
    "siyahı": Söhbət.m_siyahı, "siyahi": Söhbət.m_siyahı,
    "s": Söhbət.m_siyahı,
    "təmizlə": Söhbət.m_təmizlə, "temizle": Söhbət.m_təmizlə,
    "yüklə": Söhbət.m_yüklə, "yukle": Söhbət.m_yüklə,
    "vaxt": Söhbət.m_vaxt, "v": Söhbət.m_vaxt,
    "tokenlər": Söhbət.m_tokenlər, "tokenler": Söhbət.m_tokenlər,
    "aac": Söhbət.m_aac, "ağac": Söhbət.m_aac, "agac": Söhbət.m_aac,
    "tarixçə": Söhbət.m_tarixçə, "tarixce": Söhbət.m_tarixçə,
    "saxla": Söhbət.m_saxla,
    "ascii": Söhbət.m_ascii,
    "hərflər": Söhbət.m_hərflər, "herfler": Söhbət.m_hərflər,
    "əlifba": Söhbət.m_əlifba, "elifba": Söhbət.m_əlifba,
}

KÖMƏK_MƏTNİ = [
    ("kömək", "bu mətn  (:k, :?)"),
    ("çıx", "söhbəti bitir  (:q, Ctrl+D)"),
    ("tip <ifadə>", "ifadənin tipini göstər  (:t)"),
    ("siyahı", "təyin edilmiş adlar  (:s)"),
    ("vaxt <ifadə>", "icra müddətini ölç  (:v)"),
    ("yüklə <fayl>", "faylı seansa yüklə"),
    ("saxla <fayl>", "seansı `.alq` faylı kimi saxla"),
    ("tarixçə [n]", "son n giriş"),
    ("təmizlə", "bütün dəyişənləri sil"),
    ("tokenlər <kod>", "lekserin çıxışını göstər"),
    ("aac <kod>", "sintaksis ağacını göstər"),
    ("hərflər", "Azərbaycan hərfləri və ASCII qarşılıqları"),
    ("əlifba", "32 hərfli əlifba və sıralama"),
    ("ascii aç|qapat", "ASCII açar söz xəbərdarlığı"),
    ("ləğv", "yarımçıq girişi ləğv et"),
]

İPUCLARI = [
    "Bloklar avtomatik davam edir — `əgər x > 5 onda` yazıb Enter basın.",
    "Yarımçıq girişi ləğv etmək: iki dəfə boş Enter və ya Ctrl+C.",
    "Son nəticə `nəticə` dəyişənində saxlanılır.",
    "ASCII yaza bilərsiniz: `eger`, `deyisen`, `ne qeder ki`.",
    "Klaviaturada Azərbaycan hərfləri yoxdursa: `:hərflər`.",
]


def söhbət_başlat(rəngli: bool | None = None) -> int:
    return Söhbət(rəngli).işlət()
