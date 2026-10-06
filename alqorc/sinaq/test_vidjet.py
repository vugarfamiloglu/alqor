"""`vidjet` modulu — hazır interfeys elementləri sınaqları."""

import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import alqor.pencere as P                                   # noqa: E402
import alqor.vidjet as V                                    # noqa: E402
from alqor.acar_sozler import ACAR_SOZLER                   # noqa: E402
from test_icraci import işlət, çıxış                        # noqa: E402

BAŞLIQ = "gətir vidjet\n"
PƏNCƏRƏ = "gətir vidjet\ngətir pəncərə\n"

# Sınaqlarda pəncərə açılmasın
P._başsız_rejimdir = lambda: True


def HTML(ifadə: str, əlavə: str = "") -> str:
    """Vidjetin HTML-ini qaytarır."""
    sətirlər = çıxış(
        PƏNCƏRƏ + əlavə
        + "funksiya əsas()\n"
          '    dəyişən p = yeni pəncərə.Pəncərə("S")\n'
          f"    p.məzmun({ifadə})\n"
          "    yaz(p.HTML())\n"
          "son\n")
    return sətirlər[0] if sətirlər else ""


# ═══════════════════════════════════════════════════════════════════════
#  Kataloqun bütövlüyü
# ═══════════════════════════════════════════════════════════════════════

class KataloqSınağı(unittest.TestCase):
    def test_hər_vidjetin_funksiyası_var(self):
        for ad in V.VİDJETLƏR:
            self.assertTrue(callable(getattr(V, ad, None)),
                            f"`{ad}` funksiyası yoxdur")

    def test_təkrar_yoxdur(self):
        self.assertEqual(len(V.VİDJETLƏR), len(set(V.VİDJETLƏR)))

    def test_hər_vidjetin_izahı_və_nümunəsi_var(self):
        for m in V.KATALOQ:
            self.assertTrue(m.izah, f"`{m.ad}` izahsızdır")
            self.assertTrue(m.nümunə, f"`{m.ad}` nümunəsizdir")
            self.assertIn(m.kateqoriya, V.KATEQORİYALAR, m.ad)

    def test_parametr_adları_açar_söz_deyil(self):
        """
        Adlı arqumentin etiketi identifikator olmalıdır — `açıq:`
        və ya `sinif:` kimi ad Alqor tərəfində ayrılmır.
        """
        for ad in V.VİDJETLƏR:
            imza = inspect.signature(getattr(V, ad))
            for p in list(imza.parameters.values())[1:]:
                self.assertNotIn(p.name, ACAR_SOZLER,
                                 f"{ad}({p.name}: …) açar sözdür")

    def test_parametr_adlarında_alt_xətt_yoxdur(self):
        for ad in V.VİDJETLƏR:
            imza = inspect.signature(getattr(V, ad))
            for p in list(imza.parameters.values())[1:]:
                self.assertFalse(p.name.endswith("_"),
                                 f"{ad}({p.name}) — API-də alt xətt")

    def test_nümunələr_həqiqətən_ayrılır(self):
        """Kataloqdaki hər nümunə işlək Alqor kodu olmalıdır."""
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı

        for m in V.KATALOQ:
            kod = (BAŞLIQ + "funksiya əsas()\n    dəyişən e = "
                   + m.nümunə.replace("{ad}", "sınaqAdı")
                   + "\n    yaz(e)\nson\n")
            x = XətaToplayıcı()
            mənbə = Mənbə.mətndən(kod, "nümunə.alqor", x)
            Parser(Lekser(mənbə, x).leksə(), mənbə, x).ayır()
            self.assertTrue(x.uğurludur(),
                            f"`{m.ad}` nümunəsi ayrılmır:\n"
                            + x.hesabat(False))

    def test_skeletlər_həqiqətən_ayrılır(self):
        """Hər kod skeleti komponent gövdəsinə yapışdırıla bilməlidir."""
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı

        for m in V.KATALOQ:
            if not m.skelet and not m.vəziyyət:
                continue
            gövdə = V.skelet(None, m.ad, "sınaqAdı")
            kod = (BAŞLIQ + "komponent K\n"
                   + "".join(f"    {s}\n" if s.strip() else "\n"
                             for s in gövdə.split("\n"))
                   + "\n    göstər()\n        qaytar <p>a</p>\n    son\n"
                     "son\n")
            x = XətaToplayıcı()
            mənbə = Mənbə.mətndən(kod, "skelet.alqor", x)
            Parser(Lekser(mənbə, x).leksə(), mənbə, x).ayır()
            self.assertTrue(x.uğurludur(),
                            f"`{m.ad}` skeleti ayrılmır:\n{gövdə}\n"
                            + x.hesabat(False))

    def test_skeletlərdəki_tiplər_mövcuddur(self):
        """
        Skelet yalnız ayrılmamalı, tip yoxlamasından da keçməlidir:
        IDE onu redaktora yazır, `tamEn` kimi naməlum tip istifadəçiyə
        dərhal xəta göstərərdi (ALQ-T002).
        """
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.tipyoxlayici import TipYoxlayıcı
        from alqor.xeta import XətaToplayıcı

        for m in V.KATALOQ:
            if not m.skelet and not m.vəziyyət:
                continue
            gövdə = V.skelet(None, m.ad, "sınaqAdı")
            kod = ("komponent K\n"
                   + "".join(f"    {s}\n" if s.strip() else "\n"
                             for s in gövdə.split("\n"))
                   + "\n    göstər()\n        qaytar <p>a</p>\n    son\n"
                     "son\n")
            x = XətaToplayıcı()
            mənbə = Mənbə.mətndən(kod, "skelet.alqor", x)
            ağac = Parser(Lekser(mənbə, x).leksə(), mənbə, x).ayır()
            t = XətaToplayıcı()
            TipYoxlayıcı(t).yoxla(ağac)
            naməlum = [d for d in t.siyahı if d.kod == "ALQ-T002"]
            self.assertEqual(naməlum, [],
                             f"`{m.ad}` skeletində naməlum tip:\n{gövdə}")

    def test_kataloq_dildən_oxunur(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    dəyişən k = vidjet.kataloq()
    yaz(uzunluq(k))
    yaz(k[0]["ad"])
    yaz("kateqoriya" içindədir k[0])
    yaz("skelet" içindədir k[0])
son
''')
        self.assertEqual(sətirlər[0], str(len(V.VİDJETLƏR)))
        self.assertEqual(sətirlər[1], "düymə")
        self.assertEqual(sətirlər[2:], ["doğru", "doğru"])

    def test_kateqoriyaya_görə_süzülür(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    yaz(uzunluq(vidjet.kataloq("form")) < uzunluq(vidjet.kataloq()))
    yaz(uzunluq(vidjet.kateqoriyalar()))
son
''')
        self.assertEqual(sətirlər, ["doğru", str(len(V.KATEQORİYALAR))])

    def test_olmayan_kateqoriya(self):
        _, xəta = işlət(BAŞLIQ + '''
funksiya əsas()
    vidjet.kataloq("yoxdur")
son
''')
        self.assertIsNotNone(xəta)
        self.assertIn("yoxdur", xəta.mesaj)

    def test_skelet_dəyişən_adını_yerləşdirir(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    yaz(vidjet.skelet("sahə", "istifadəçiAdı"))
son
''')
        hamısı = "\n".join(sətirlər)
        self.assertIn("vəziyyət istifadəçiAdı: mətn", hamısı)
        self.assertIn("metod istifadəçiAdıDəyişdi", hamısı)
        self.assertIn("özü.istifadəçiAdı = dəyər", hamısı)
        self.assertNotIn("{ad}", hamısı)

    def test_skelet_standart_ad(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    yaz(x"{ad}" içindədir vidjet.skelet("sahə"))
son
''')
        self.assertEqual(sətirlər, ["yanlış"])

    def test_olmayan_vidjetin_skeleti(self):
        _, xəta = işlət(BAŞLIQ + '''
funksiya əsas()
    vidjet.skelet("yoxdurBeləVidjet")
son
''')
        self.assertIsNotNone(xəta)
        self.assertIn("yoxdurBeləVidjet", xəta.mesaj)

    def test_nümunə_oxunur(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    yaz("vidjet.düymə" içindədir vidjet.nümunə("düymə", "yadda"))
son
''')
        self.assertEqual(sətirlər, ["doğru"])


# ═══════════════════════════════════════════════════════════════════════
#  Düymələr
# ═══════════════════════════════════════════════════════════════════════

class DüyməSınağı(unittest.TestCase):
    def test_sadə(self):
        h = HTML('vidjet.düymə(mətn: "Bas")')
        self.assertIn('class="v-düymə v-düymə--əsas v-düymə--orta"', h)
        self.assertIn(">Bas</button>", h)
        self.assertIn('type="button"', h)

    def test_növlər(self):
        for n in ("əsas", "ikinci", "sakit", "təhlükə", "uğur",
                  "xəbərdarlıq", "əlaqə"):
            h = HTML(f'vidjet.düymə(mətn: "A", növ: "{n}")')
            self.assertIn(f"v-düymə--{n}", h)

    def test_yanlış_növ(self):
        _, xəta = işlət(PƏNCƏRƏ + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("S")
    p.məzmun(vidjet.düymə(mətn: "A", növ: "qırmızı"))
    yaz(p.HTML())
son
''')
        self.assertIsNotNone(xəta)
        self.assertIn("qırmızı", xəta.mesaj)

    def test_ölçülər(self):
        for ö in ("kiçik", "orta", "böyük"):
            self.assertIn(f"v-düymə--{ö}",
                          HTML(f'vidjet.düymə(mətn: "A", ölçü: "{ö}")'))

    def test_söndürülmüş(self):
        h = HTML('vidjet.düymə(mətn: "A", söndürülmüş: doğru,'
                 ' klik: () => 1)')
        self.assertIn("disabled", h)
        self.assertNotIn("data-a-klik", h)

    def test_gözləyir(self):
        h = HTML('vidjet.düymə(mətn: "A", gözləyir: doğru)')
        self.assertIn("v-fırlanan", h)
        self.assertIn("disabled", h)

    def test_tam_en(self):
        self.assertIn("v-düymə--tam",
                      HTML('vidjet.düymə(mətn: "A", tamEn: doğru)'))

    def test_ikon(self):
        h = HTML('vidjet.düymə(mətn: "Saxla", ikon: "💾")')
        self.assertIn('class="v-ikon"', h)

    def test_klik_bağlanır(self):
        h = HTML('vidjet.düymə(mətn: "A", klik: () => 1)')
        self.assertIn("data-a-klik=", h)
        self.assertNotIn(" klik=", h)

    def test_ikon_düyməsi(self):
        h = HTML('vidjet.ikonDüymə(ikon: "✕", başlıq: "Sil")')
        self.assertIn("v-düymə--ikon", h)
        self.assertIn('title="Sil"', h)

    def test_qrup(self):
        h = HTML('vidjet.düyməQrupu(məzmun: ['
                 'vidjet.düymə(mətn: "A"), vidjet.düymə(mətn: "B")])')
        self.assertIn("v-düymə-qrupu", h)
        self.assertEqual(h.count("<button"), 2)

    def test_əlaqə(self):
        h = HTML('vidjet.əlaqə(mətn: "Ətraflı", ünvan: "/a",'
                 ' yeniNişan: doğru)')
        self.assertIn('href="/a"', h)
        self.assertIn('target="_blank"', h)
        self.assertIn('rel="noopener noreferrer"', h)


# ═══════════════════════════════════════════════════════════════════════
#  Form sahələri
# ═══════════════════════════════════════════════════════════════════════

class FormSınağı(unittest.TestCase):
    def test_mətn_sahəsi(self):
        h = HTML('vidjet.sahə(etiket: "Ad", ad: "ad", dəyər: "Əli")')
        self.assertIn('<label class="v-etiket" for="ad">Ad</label>', h)
        self.assertIn('type="text"', h)
        self.assertIn('name="ad"', h)
        self.assertIn('value="Əli"', h)

    def test_etiket_nişan_kimi_yazılır(self):
        """Sınaq sürücüsü sahəni görünən etiketinə görə tapa bilsin."""
        h = HTML('vidjet.sahə(etiket: "Ad", ad: "ad")')
        self.assertIn('data-a-ad="Ad"', h)

    def test_tələb_ulduz_qoyur(self):
        h = HTML('vidjet.sahə(etiket: "Ad", ad: "ad", tələb: doğru)')
        self.assertIn('class="v-tələb"', h)
        self.assertIn("required", h)

    def test_kömək_mətni(self):
        h = HTML('vidjet.sahə(etiket: "Ad", ad: "a", kömək: "Tam adınız")')
        self.assertIn('class="v-kömək">Tam adınız</p>', h)

    def test_xəta_köməyi_üstələyir(self):
        h = HTML('vidjet.sahə(etiket: "Ad", ad: "a", kömək: "Kömək",'
                 ' xəta: "Boş ola bilməz")')
        self.assertIn("Boş ola bilməz", h)
        self.assertNotIn("Kömək", h)
        self.assertIn("v-sahə--xətalı", h)
        self.assertIn("v-giriş--xətalı", h)

    def test_parol(self):
        h = HTML('vidjet.parol(etiket: "Şifrə")')
        self.assertIn('type="password"', h)
        self.assertIn('autocomplete="current-password"', h)

    def test_ədəd_hədləri(self):
        h = HTML('vidjet.ədəd(etiket: "Yaş", ad: "y", minimum: 0,'
                 ' maksimum: 120, pillə: 5)')
        self.assertIn('type="number"', h)
        self.assertIn('min="0"', h)
        self.assertIn('max="120"', h)
        self.assertIn('step="5"', h)

    def test_çoxsətirli(self):
        h = HTML('vidjet.çoxsətirli(etiket: "Qeyd", ad: "q",'
                 ' sətirlər: 6, dəyər: "mətn")')
        self.assertIn("<textarea", h)
        self.assertIn('rows="6"', h)
        self.assertIn(">mətn</textarea>", h)

    def test_seçim_siyahısı(self):
        h = HTML('vidjet.seçim(etiket: "Şəhər", ad: "ş",'
                 ' seçimlər: ["Bakı", "Gəncə"], dəyər: "Gəncə")')
        self.assertIn("<select", h)
        self.assertIn('<option value="Bakı">Bakı</option>', h)
        self.assertIn('<option value="Gəncə" selected>', h)

    def test_seçim_lüğətlə(self):
        h = HTML('vidjet.seçim(ad: "d", seçimlər:'
                 ' {"az": "Azərbaycan", "en": "İngilis"})')
        self.assertIn('<option value="az">Azərbaycan</option>', h)

    def test_seçim_cütlərlə(self):
        h = HTML('vidjet.seçim(ad: "d", seçimlər:'
                 ' [["az", "Azərbaycan"]])')
        self.assertIn('<option value="az">Azərbaycan</option>', h)

    def test_boş_etiket(self):
        h = HTML('vidjet.seçim(ad: "d", seçimlər: ["a"],'
                 ' boşEtiket: "Seçin…")')
        self.assertIn('<option value="">Seçin…</option>', h)

    def test_qeyd(self):
        h = HTML('vidjet.qeyd(etiket: "Qəbul", ad: "q",'
                 ' işarələnmiş: doğru)')
        self.assertIn('type="checkbox"', h)
        self.assertIn("checked", h)
        self.assertIn('data-a-ad="Qəbul"', h)

    def test_açar(self):
        h = HTML('vidjet.açar(etiket: "Bildiriş", ad: "b", yanıq: doğru)')
        self.assertIn("v-açar", h)
        self.assertIn("v-açar-topu", h)
        self.assertIn("checked", h)

    def test_radio_qrupu(self):
        h = HTML('vidjet.radioQrupu(etiket: "Ödəniş", ad: "ö",'
                 ' seçimlər: ["Nağd", "Kart"], dəyər: "Kart")')
        self.assertEqual(h.count('type="radio"'), 2)
        self.assertIn('value="Kart" checked', h)
        self.assertIn('data-a-ad="Nağd"', h)

    def test_radio_üfüqi(self):
        h = HTML('vidjet.radioQrupu(ad: "ö", seçimlər: ["a"],'
                 ' üfüqi: doğru)')
        self.assertIn("v-radio-qrupu--üfüqi", h)

    def test_sürüşdürücü(self):
        h = HTML('vidjet.sürüşdürücü(etiket: "Səs", ad: "s",'
                 ' dəyər: 70, minimum: 10, maksimum: 90)')
        self.assertIn('type="range"', h)
        self.assertIn('value="70"', h)
        self.assertIn('min="10"', h)
        self.assertIn("<output", h)

    def test_sürüşdürücü_dəyərsiz(self):
        h = HTML('vidjet.sürüşdürücü(ad: "s", dəyəriGöstər: yanlış)')
        self.assertNotIn("<output", h)

    def test_tarix_vaxt_rəng(self):
        self.assertIn('type="date"', HTML('vidjet.tarix(ad: "t")'))
        self.assertIn('type="time"', HTML('vidjet.vaxt(ad: "v")'))
        self.assertIn('type="color"', HTML('vidjet.rəng(ad: "r")'))

    def test_fayl_sahəsi(self):
        h = HTML('vidjet.faylSahəsi(ad: "f", növlər: ["image/*", ".pdf"],'
                 ' çoxlu: doğru)')
        self.assertIn('type="file"', h)
        self.assertIn('accept="image/*,.pdf"', h)
        self.assertIn("multiple", h)

    def test_axtarış(self):
        h = HTML('vidjet.axtarış(ad: "q")')
        self.assertIn("v-axtarış", h)
        self.assertIn('type="search"', h)

    def test_form(self):
        h = HTML('vidjet.form(başlıq: "Giriş", göndərildi: () => 1,'
                 ' məzmun: [vidjet.sahə(ad: "a")])')
        self.assertIn("<form", h)
        self.assertIn("v-form-başlığı", h)
        self.assertIn("data-a-gonderildi", h)

    def test_sahə_dəsti(self):
        h = HTML('vidjet.sahəDəsti(başlıq: "Ünvan", məzmun: ['
                 'vidjet.sahə(ad: "ş")])')
        self.assertIn("<fieldset", h)
        self.assertIn("<legend", h)

    def test_etiket_vidjeti(self):
        h = HTML('vidjet.etiket(mətn: "Ad", sahəsi: "ad")')
        self.assertIn('<label class="v-etiket" for="ad">Ad</label>', h)


# ═══════════════════════════════════════════════════════════════════════
#  Göstərmə
# ═══════════════════════════════════════════════════════════════════════

class GöstərməSınağı(unittest.TestCase):
    def test_başlıq_səviyyələri(self):
        for n in (1, 3, 6):
            self.assertIn(f"<h{n} ",
                          HTML(f'vidjet.başlıq(mətn: "A", səviyyə: {n})'))

    def test_başlıq_həddi_aşmır(self):
        self.assertIn("<h6 ", HTML('vidjet.başlıq(mətn: "A", səviyyə: 9)'))
        self.assertIn("<h1 ", HTML('vidjet.başlıq(mətn: "A", səviyyə: 0)'))

    def test_başlıq_alt_mətni(self):
        h = HTML('vidjet.başlıq(mətn: "A", altMətn: "izah")')
        self.assertIn("v-başlıq-qrupu", h)
        self.assertIn("izah", h)

    def test_mətn(self):
        h = HTML('vidjet.mətn(məzmun: "Salam", sönük: doğru,'
                 ' qalın: doğru)')
        self.assertIn("v-mətn--sönük", h)
        self.assertIn("v-mətn--qalın", h)

    def test_nişan(self):
        self.assertIn("v-nişan--uğur",
                      HTML('vidjet.nişan(mətn: "Yeni", növ: "uğur")'))

    def test_xəbərdarlıq(self):
        h = HTML('vidjet.xəbərdarlıq(mətn: "Oldu", növ: "uğur",'
                 ' başlıq: "Hazır")')
        self.assertIn("v-xəbərdarlıq--uğur", h)
        self.assertIn('role="alert"', h)
        self.assertIn("Hazır", h)
        self.assertIn("✓", h)

    def test_xəbərdarlıq_bağlana(self):
        h = HTML('vidjet.xəbərdarlıq(mətn: "A", bağlana: doğru,'
                 ' bağlandı: () => 1)')
        self.assertIn("v-xəbərdarlıq-bağla", h)
        self.assertIn("data-a-klik", h)

    def test_xəbərdarlıq_yanlış_növ(self):
        _, xəta = işlət(PƏNCƏRƏ + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("S")
    p.məzmun(vidjet.xəbərdarlıq(mətn: "A", növ: "əsas"))
    yaz(p.HTML())
son
''')
        self.assertIsNotNone(xəta)

    def test_kart(self):
        h = HTML('vidjet.kart(başlıq: "Hesabat", altMətn: "2026",'
                 ' məzmun: [vidjet.mətn(məzmun: "a")],'
                 ' altlıq: [vidjet.düymə(mətn: "Aç")])')
        self.assertIn("v-kart-başı", h)
        self.assertIn("v-kart-gövdəsi", h)
        self.assertIn("v-kart-altlığı", h)
        self.assertIn("2026", h)

    def test_kart_basılan(self):
        h = HTML('vidjet.kart(başlıq: "A", klik: () => 1)')
        self.assertIn("v-kart--basılan", h)
        self.assertIn("data-a-klik", h)

    def test_cədvəl_siyahı_sətirləri(self):
        h = HTML('vidjet.cədvəl(sütunlar: ["Ad", "Yaş"],'
                 ' sətirlər: [["Əli", 30], ["Aysel", 28]])')
        self.assertIn("<th>Ad</th>", h)
        self.assertIn("<td>Əli</td>", h)
        self.assertIn("<td>28</td>", h)
        self.assertIn("v-cədvəl--zolaqlı", h)

    def test_cədvəl_lüğət_sətirləri(self):
        h = HTML('vidjet.cədvəl(sütunlar: [["ad", "Ad"],'
                 ' ["yaş", "Yaş"]], sətirlər:'
                 ' [{"ad": "Əli", "yaş": 30}])')
        self.assertIn("<th>Ad</th>", h)
        self.assertIn("<td>Əli</td>", h)

    def test_cədvəl_nümunə_sətirləri(self):
        h = HTML('vidjet.cədvəl(sütunlar: [["ad", "Ad"]],'
                 ' sətirlər: [yeni İ("Əli")])',
                 əlavə="sinif İ\n    qurucu(açıq xassə ad: mətn)\nson\n")
        self.assertIn("<td>Əli</td>", h)

    def test_cədvəl_boş(self):
        h = HTML('vidjet.cədvəl(sütunlar: ["A", "B"], sətirlər: [],'
                 ' boşMətn: "Heç nə")')
        self.assertIn("v-cədvəl-boş", h)
        self.assertIn('colspan="2"', h)
        self.assertIn("Heç nə", h)

    def test_cədvəl_sətir_kliki(self):
        h = HTML('vidjet.cədvəl(sütunlar: ["A"], sətirlər: [["x"]],'
                 ' sətirKlik: () => 1)')
        self.assertIn("v-sətir--basılan", h)

    def test_siyahı(self):
        h = HTML('vidjet.siyahı(elementlər: ["bir", "iki"])')
        self.assertIn("<ul", h)
        self.assertIn("<li>bir</li>", h)

    def test_nömrəli_siyahı(self):
        self.assertIn("<ol",
                      HTML('vidjet.siyahı(elementlər: ["a"],'
                           ' nömrəli: doğru)'))

    def test_təsvir_siyahısı(self):
        h = HTML('vidjet.təsvirSiyahısı(cütlər: {"Ad": "Əli"})')
        self.assertIn("<dt>Ad</dt>", h)
        self.assertIn("<dd>Əli</dd>", h)

    def test_kod(self):
        h = HTML('vidjet.kod(məzmun: "yaz(1)", dil: "alqor")')
        self.assertIn("<pre", h)
        self.assertIn('data-dil="alqor"', h)
        self.assertIn("<code>yaz(1)</code>", h)

    def test_sitat(self):
        h = HTML('vidjet.sitat(mətn: "Söz", mənbə: "Kimsə")')
        self.assertIn("<blockquote", h)
        self.assertIn("v-sitat-mənbəyi", h)

    def test_şəkil(self):
        h = HTML('vidjet.şəkil(mənbə: "/a.png", alternativ: "A",'
                 ' en: 120, yuvarlaq: doğru)')
        self.assertIn('src="/a.png"', h)
        self.assertIn('width="120px"', h)
        self.assertIn("v-şəkil--yuvarlaq", h)
        self.assertIn('loading="lazy"', h)

    def test_avatar_hərflərlə(self):
        h = HTML('vidjet.avatar(ad: "aysel məmmədova")')
        self.assertIn(">AM<", h)

    def test_avatar_şəkillə(self):
        h = HTML('vidjet.avatar(ad: "A", mənbə: "/a.png")')
        self.assertIn("<img", h)

    def test_ayırıcı(self):
        self.assertIn("<hr", HTML("vidjet.ayırıcı()"))
        h = HTML('vidjet.ayırıcı(mətn: "və ya")')
        self.assertIn("v-ayırıcı-mətnli", h)
        self.assertIn("və ya", h)

    def test_boş_baxış(self):
        h = HTML('vidjet.boşBaxış(başlıq: "Yoxdur", mətn: "Əlavə edin",'
                 ' hərəkət: vidjet.düymə(mətn: "Əlavə et"))')
        self.assertIn("v-boş-baxış", h)
        self.assertIn("Əlavə edin", h)
        self.assertIn("<button", h)

    def test_HTML_qaçışı(self):
        h = HTML('vidjet.mətn(məzmun: "<script>alert(1)</script>")')
        self.assertIn("&lt;script&gt;", h)
        self.assertNotIn("<script>", h)

    def test_atribut_qaçışı(self):
        h = HTML('vidjet.şəkil(mənbə: "a\\"b", alternativ: "c<d")')
        self.assertNotIn('src="a"b"', h)
        self.assertIn("&quot;", h)
        self.assertIn("&lt;", h)


# ═══════════════════════════════════════════════════════════════════════
#  Vəziyyət göstəriciləri
# ═══════════════════════════════════════════════════════════════════════

class VəziyyətSınağı(unittest.TestCase):
    def test_tərəqqi(self):
        h = HTML('vidjet.tərəqqi(dəyər: 30, etiket: "Yüklənir")')
        self.assertIn("width:30.00%", h)
        self.assertIn("Yüklənir", h)
        self.assertIn("30%", h)
        self.assertIn('role="progressbar"', h)

    def test_tərəqqi_faizi_gizlədilir(self):
        h = HTML('vidjet.tərəqqi(dəyər: 30, faizGöstər: yanlış)')
        self.assertNotIn("30%", h)

    def test_tərəqqi_öz_maksimumu(self):
        h = HTML('vidjet.tərəqqi(dəyər: 5, maksimum: 20)')
        self.assertIn("width:25.00%", h)

    def test_tərəqqi_həddi_keçmir(self):
        self.assertIn("width:100.00%",
                      HTML('vidjet.tərəqqi(dəyər: 500)'))
        self.assertIn("width:0.00%",
                      HTML('vidjet.tərəqqi(dəyər: -10)'))

    def test_tərəqqi_qeyri_müəyyən(self):
        h = HTML('vidjet.tərəqqi(qeyriMüəyyən: doğru)')
        self.assertIn("v-tərəqqi-yolu--qeyri-müəyyən", h)
        self.assertNotIn("width:", h)

    def test_halqa(self):
        h = HTML('vidjet.halqaTərəqqi(dəyər: 75, ölçü: 80)')
        self.assertIn("--v-halqa-ölçü:80px", h)
        self.assertIn("--v-halqa-faiz:75.00", h)
        self.assertIn(">75%<", h)

    def test_fırlanan(self):
        self.assertIn("v-fırlanan--orta", HTML("vidjet.fırlanan()"))
        h = HTML('vidjet.fırlanan(mətn: "Gözləyin")')
        self.assertIn("v-fırlanan-qrupu", h)
        self.assertIn("Gözləyin", h)

    def test_skelet_yüklənmə(self):
        h = HTML('vidjet.skeletYüklənmə(sətirlər: 4)')
        self.assertEqual(h.count("v-skelet-sətri"), 4)

    def test_statistika(self):
        h = HTML('vidjet.statistika(etiket: "Satış", dəyər: "100 ₼",'
                 ' dəyişmə: 12, ikon: "↗")')
        self.assertIn("v-statistika-dəyişməsi--artıb", h)
        self.assertIn("▲ 12%", h)
        self.assertIn("100 ₼", h)

    def test_statistika_azalma(self):
        h = HTML('vidjet.statistika(etiket: "A", dəyər: "1",'
                 ' dəyişmə: -5)')
        self.assertIn("v-statistika-dəyişməsi--azalıb", h)
        self.assertIn("▼ 5%", h)

    def test_statistika_sabit(self):
        h = HTML('vidjet.statistika(etiket: "A", dəyər: "1",'
                 ' dəyişmə: 0)')
        self.assertIn("v-statistika-dəyişməsi--sabit", h)


# ═══════════════════════════════════════════════════════════════════════
#  Düzülüş və naviqasiya
# ═══════════════════════════════════════════════════════════════════════

class DüzülüşSınağı(unittest.TestCase):
    def test_qutu(self):
        h = HTML('vidjet.qutu(boşluq: 20, kənar: doğru,'
                 ' fon: "#eee", kimlik: "q")')
        self.assertIn("padding:20px", h)
        self.assertIn("background:#eee", h)
        self.assertIn("v-qutu--kənarlı", h)
        self.assertIn('id="q"', h)

    def test_sətir_düzləndirmə(self):
        h = HTML('vidjet.sətir(boşluq: 12, düzləndir: "ara")')
        self.assertIn("gap:12px", h)
        self.assertIn("justify-content:space-between", h)

    def test_sütun(self):
        h = HTML('vidjet.sütun(boşluq: 8, düzləndir: "mərkəz")')
        self.assertIn("align-items:center", h)

    def test_tor_sütunlarla(self):
        h = HTML('vidjet.tor(sütunlar: 3, boşluq: 10)')
        self.assertIn("grid-template-columns:repeat(3,1fr)", h)

    def test_tor_minimum_enlə(self):
        h = HTML('vidjet.tor(minimum: 240)')
        self.assertIn("minmax(240px,1fr)", h)

    def test_boşluq(self):
        self.assertIn("height:24px",
                      HTML('vidjet.boşluq(hündürlük: 24)'))

    def test_ölçü_mətnlə(self):
        self.assertIn("height:2rem",
                      HTML('vidjet.boşluq(hündürlük: "2rem")'))

    def test_panel(self):
        h = HTML('vidjet.panel(başlıq: "Ayarlar",'
                 ' alətlər: [vidjet.ikonDüymə(ikon: "⚙")],'
                 ' məzmun: [vidjet.mətn(məzmun: "a")])')
        self.assertIn("v-panel-başı", h)
        self.assertIn("v-panel-alətləri", h)

    def test_bölmə(self):
        h = HTML('vidjet.bölmə(başlıq: "Haqqında", altMətn: "izah")')
        self.assertIn("<section", h)
        self.assertIn("v-bölmə-başlığı", h)


class NaviqasiyaSınağı(unittest.TestCase):
    def test_naviqasiya(self):
        h = HTML('vidjet.naviqasiya(başlıq: "Tətbiq",'
                 ' elementlər: [vidjet.əlaqə(mətn: "Ana", ünvan: "/")],'
                 ' sağ: [vidjet.avatar(ad: "A")])')
        self.assertIn("<nav", h)
        self.assertIn("v-nav-elementləri", h)
        self.assertIn("v-nav-sağ", h)

    def test_nişanlar(self):
        h = HTML('vidjet.nişanlar(elementlər: ["Bir", "İki"],'
                 ' cari: "İki", klik: () => 1)')
        self.assertIn('role="tablist"', h)
        self.assertIn("v-nişan-düyməsi--seçili", h)
        self.assertIn('value="İki"', h)

    def test_nişanlar_cari_verilməyibsə_birincidir(self):
        h = HTML('vidjet.nişanlar(elementlər: ["Bir", "İki"])')
        i = h.index("Bir")
        self.assertIn("seçili", h[:i])

    def test_yığcam(self):
        h = HTML('vidjet.yığcam(başlıq: "Ətraflı", açılmış: doğru,'
                 ' məzmun: [vidjet.mətn(məzmun: "a")])')
        self.assertIn("<details", h)
        self.assertIn("open", h)
        self.assertIn("<summary", h)

    def test_səhifələmə(self):
        h = HTML('vidjet.səhifələmə(səhifə: 1, cəmi: 5, klik: () => 1)')
        self.assertIn("v-səhifə-düyməsi--seçili", h)
        self.assertIn("‹", h)
        self.assertIn("›", h)

    def test_səhifələmə_ilk_səhifədə_geri_sönükdür(self):
        h = HTML('vidjet.səhifələmə(səhifə: 1, cəmi: 5)')
        i = h.index("‹")
        self.assertIn("disabled", h[:i])

    def test_səhifələmə_fasilə(self):
        h = HTML('vidjet.səhifələmə(səhifə: 1, cəmi: 20)')
        self.assertIn("v-səhifə-fasiləsi", h)
        self.assertIn("…", h)

    def test_səhifələmə_az_səhifə(self):
        h = HTML('vidjet.səhifələmə(səhifə: 1, cəmi: 3)')
        self.assertNotIn("v-səhifə-fasiləsi", h)

    def test_addımlar(self):
        h = HTML('vidjet.addımlar(adlar: ["Bir", "İki", "Üç"], cari: 2)')
        self.assertIn("v-addım--bitmiş", h)
        self.assertIn("v-addım--cari", h)
        self.assertIn("v-addım--gözləyən", h)
        self.assertIn("✓", h)

    def test_çörək_qırıntıları(self):
        h = HTML('vidjet.çörəkQırıntıları(yollar: [["/", "Ana"],'
                 ' ["/a", "Alt"]], klik: () => 1)')
        self.assertIn("v-qırıntı--son", h)
        self.assertIn("v-qırıntı-ayırıcısı", h)


class ÜstQatSınağı(unittest.TestCase):
    def test_modal(self):
        h = HTML('vidjet.modal(başlıq: "Təsdiq", görünür: doğru,'
                 ' bağlandı: () => 1,'
                 ' məzmun: [vidjet.mətn(məzmun: "a")],'
                 ' altlıq: [vidjet.düymə(mətn: "Bəli")])')
        self.assertIn("v-modal-örtüyü", h)
        self.assertIn('role="dialog"', h)
        self.assertIn("v-modal-bağla", h)
        self.assertIn("v-modal-altlığı", h)

    def test_modal_gizli(self):
        self.assertEqual(
            HTML('vidjet.modal(başlıq: "A", görünür: yanlış)'), "")

    def test_modal_ölçüləri(self):
        self.assertIn("v-modal--böyük",
                      HTML('vidjet.modal(başlıq: "A", ölçü: "böyük")'))

    def test_yan_panel(self):
        h = HTML('vidjet.yanPanel(başlıq: "Menyu", görünür: doğru,'
                 ' tərəf: "sol")')
        self.assertIn("v-yan-panel--sol", h)

    def test_yan_panel_gizli(self):
        self.assertEqual(
            HTML('vidjet.yanPanel(başlıq: "A", görünür: yanlış)'), "")

    def test_yan_panel_yanlış_tərəf(self):
        _, xəta = işlət(PƏNCƏRƏ + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("S")
    p.məzmun(vidjet.yanPanel(başlıq: "A", tərəf: "yuxarı"))
    yaz(p.HTML())
son
''')
        self.assertIsNotNone(xəta)

    def test_ipucu(self):
        h = HTML('vidjet.ipucu(mətn: "Silinəcək", tərəf: "alt",'
                 ' məzmun: vidjet.ikonDüymə(ikon: "✕"))')
        self.assertIn('data-ipucu="Silinəcək"', h)
        self.assertIn("v-ipucu--alt", h)

    def test_bildiriş_qutusu(self):
        h = HTML('vidjet.bildirişQutusu(mətn: "Oldu", növ: "uğur",'
                 ' bağlandı: () => 1)')
        self.assertIn("v-bildiriş-qutusu", h)
        self.assertIn("v-xəbərdarlıq--uğur", h)


# ═══════════════════════════════════════════════════════════════════════
#  Üslub və iki hədəf
# ═══════════════════════════════════════════════════════════════════════

class ÜslubSınağı(unittest.TestCase):
    def test_üslub_mətn_kimi(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    yaz(x".v-düymə{" içindədir vidjet.üslub())
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_üslublar_elementi(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    yaz("<style>" içindədir vidjet.üslublar().HTML())
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_səhifə_tam_sənəddir(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    dəyişən s = vidjet.səhifə(başlıq: "Mənim səhifəm", məzmun: [
        vidjet.başlıq(mətn: "Salam")
    ]).HTML()
    yaz("<html lang=\\"az\\">" içindədir s)
    yaz("<title>Mənim səhifəm</title>" içindədir s)
    yaz("charset=\\"UTF-8\\"" içindədir s)
    yaz(x".v-düymə{" içindədir s)
    yaz("<h1 class=\\"v-başlıq\\">Salam</h1>" içindədir s)
son
''')
        self.assertEqual(sətirlər, ["doğru"] * 5)

    def test_səhifə_əlavə_üslub(self):
        sətirlər = çıxış(BAŞLIQ + '''
funksiya əsas()
    dəyişən s = vidjet.səhifə(başlıq: "A",
                              əlavəÜslub: x".mən{color:red}").HTML()
    yaz(x".mən{color:red}" içindədir s)
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_üslubda_işlənən_siniflər_təyin_olunub(self):
        """
        Vidjetlərin yazdığı hər `v-…` sinfi üslubda olmalıdır —
        əks halda element üslubsuz görünər.
        """
        import re
        from alqor.icraci import İcraçı

        icraçı = İcraçı()
        reyestr = P.Reyestr()
        işlənən: set[str] = set()
        for m in V.KATALOQ:
            funksiya = getattr(V, m.ad)
            try:
                element = funksiya(icraçı)
            except Exception:                       # noqa: BLE001
                continue
            html = P.HTML_ə(element, reyestr, icraçı)
            for sinif_sətri in re.findall(r'class="([^"]+)"', html):
                işlənən.update(s for s in sinif_sətri.split()
                               if s.startswith("v-"))

        təyin = set(re.findall(
            r"\.(v-[0-9A-Za-zƏəĞğIıİiÖöŞşÇçÜü_-]+)", V.ÜSLUB))
        # `--orta`, `--əsas`, `--ikinci` standart variantlardır: əsas
        # sinfin qaydası onları artıq əhatə edir (`.v-düymə` özü
        # `--orta` ölçüsündədir), ayrıca qayda lazım deyil.
        STANDART = ("orta", "əsas", "ikinci")
        çatışmayan = []
        for c in sorted(işlənən - təyin):
            if "--" in c:
                ə, variant = c.rsplit("--", 1)
                if variant in STANDART and ə in təyin:
                    continue
            çatışmayan.append(c)
        self.assertEqual(çatışmayan, [],
                         f"üslubda yoxdur: {çatışmayan}")


class İkiHədəfSınağı(unittest.TestCase):
    """Eyni vidjet ağacı həm desktopda, həm vebdə göstərilir."""

    KOMPONENT = '''
komponent Form
    vəziyyət ad: mətn = ""

    metod adDəyişdi(dəyər: mətn)
        özü.ad = dəyər
    son

    göstər()
        qaytar vidjet.kart(başlıq: "Giriş", məzmun: [
            vidjet.sahə(etiket: "Ad", ad: "ad", dəyər: özü.ad,
                        dəyişdi: özü.adDəyişdi),
            vidjet.mətn(məzmun: "Salam, {özü.ad}!")
        ])
    son
son
'''

    def test_desktopda(self):
        sətirlər = çıxış("gətir vidjet\ngətir pəncərə\n" + self.KOMPONENT
                         + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("S")
    p.məzmun(<Form />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.yaz("Ad", "Aysel")
    yaz(s.ehtiva("Salam, Aysel!"))
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_vebdə(self):
        sətirlər = çıxış("gətir vidjet\ngətir veb\n" + self.KOMPONENT
                         + '''
funksiya əsas()
    dəyişən s = yeni veb.Server()
    dəyişən f = yeni Form()
    s.al("/", (sorğu) => veb.html(
        vidjet.səhifə(başlıq: "Giriş", məzmun: [f.göstər()])))
    dəyişən c = veb.sınaq.server(s).al("/")
    yaz(c.vəziyyət())
    yaz("<!DOCTYPE html>" içindədir c.mətnƏt())
    yaz("v-kart" içindədir c.mətnƏt())
    yaz(x".v-giriş{" içindədir c.mətnƏt())
son
''')
        self.assertEqual(sətirlər, ["200", "doğru", "doğru", "doğru"])


# ═══════════════════════════════════════════════════════════════════════
#  Nümunə
# ═══════════════════════════════════════════════════════════════════════

class NümunəSınağı(unittest.TestCase):
    def test_08_vidjetler_işləyir(self):
        yol = (Path(__file__).parent.parent.parent / "numuneler"
               / "08-vidjetler.alqor")
        if not yol.exists():
            self.skipTest("nümunə yoxdur")

        from alqor.icraci import İcraçı
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı

        x = XətaToplayıcı()
        mənbə = Mənbə.fayldan(yol, x)
        ağac = Parser(Lekser(mənbə, x).leksə(), mənbə, x).ayır()
        self.assertTrue(x.uğurludur(), x.hesabat(False))

        sətirlər: list[str] = []
        icraçı = İcraçı(çıxış=sətirlər.append, giriş=lambda: "")
        icraçı.əsas_qovluq = yol.parent
        self.assertEqual(icraçı.işlət(ağac, ["sınaq"]), 0)

        hamısı = "\n".join(sətirlər)
        self.assertNotIn("yanlış", hamısı, "bir yoxlama uğursuzdur")
        for gözlənilən in ("Heyət nişanı", "Boş baxış", "Səhifə 6",
                           "Modal açıq", "İşçi silindi", "Açar söndü",
                           "DOCTYPE", "IDE kataloqu"):
            self.assertIn(gözlənilən, hamısı)


if __name__ == "__main__":
    unittest.main(verbosity=2)
