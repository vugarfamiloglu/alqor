"""`pəncərə` modulu — desktop tətbiqləri sınaqları."""

import json
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import alqor.pencere as P                                   # noqa: E402
from alqor.pencere import (HADİSƏLƏR, Reyestr, _atribut_tap,  # noqa: E402
                           _qısayolu_normallaşdır, _teqsiz,
                           _uyğundur)
from test_icraci import çıxış                               # noqa: E402

BAŞLIQ = "gətir pəncərə\n"

# Sınaq zamanı pəncərə açılmasın
P._başsız_rejimdir = lambda: True


def başsız(kod: str) -> list[str]:
    """Başsız rejimdə işlədir — `pəncərə.sınaq` sürücüsü ilə."""
    return çıxış(BAŞLIQ + kod)


# Sınaqlarda təkrarlanan sadə komponent
SAYĞAC = """
komponent Sayğac
    vəziyyət say: tam = 0

    hesablanan ikiqat: tam
        qaytar özü.say * 2
    son

    metod artır()
        özü.say += 1
    son

    metod azalt()
        özü.say -= 1
    son

    göstər()
        qaytar <div>
            <h1>{özü.say}</h1>
            <span kimlik="ikiqat">{özü.ikiqat}</span>
            <button klik={özü.azalt}>-</button>
            <button klik={özü.artır}>+</button>
        </div>
    son
son
"""


# ═══════════════════════════════════════════════════════════════════════
#  Python səviyyəsindəki köməkçilər
# ═══════════════════════════════════════════════════════════════════════

class ReyestrSınağı(unittest.TestCase):
    def test_açar_verilir_və_oxunur(self):
        r = Reyestr()
        a = r.yaz(lambda: 1)
        self.assertIsNotNone(r.al(a))

    def test_sıfırlama_köhnə_açarları_etibarsızlaşdırır(self):
        r = Reyestr()
        köhnə = r.yaz(lambda: 1)
        r.sıfırla()
        self.assertIsNone(r.al(köhnə))

    def test_nəsil_dəyişir(self):
        r = Reyestr()
        a1 = r.yaz(lambda: 1)
        r.sıfırla()
        a2 = r.yaz(lambda: 1)
        self.assertNotEqual(a1, a2)

    def test_olmayan_açar(self):
        self.assertIsNone(Reyestr().al("yoxdur"))


class QısayolSınağı(unittest.TestCase):
    def test_sadə(self):
        self.assertEqual(_qısayolu_normallaşdır("Ctrl+S"), "ctrl+s")

    def test_sıra_normallaşır(self):
        self.assertEqual(_qısayolu_normallaşdır("Shift+Ctrl+P"),
                         "ctrl+shift+p")

    def test_cmd_meta_olur(self):
        self.assertEqual(_qısayolu_normallaşdır("Cmd+Q"), "meta+q")

    def test_control_ctrl_olur(self):
        self.assertEqual(_qısayolu_normallaşdır("Control+A"), "ctrl+a")

    def test_dəyişdiricisiz(self):
        self.assertEqual(_qısayolu_normallaşdır("F5"), "f5")

    def test_boş(self):
        self.assertEqual(_qısayolu_normallaşdır(""), "")


class TeqsizSınağı(unittest.TestCase):
    def test_teqlər_silinir(self):
        self.assertEqual(_teqsiz("<p>Salam <b>dünya</b></p>"),
                         "Salam dünya")

    def test_qaçış_açılır(self):
        self.assertEqual(_teqsiz("<p>a &amp; b &lt;c&gt;</p>"),
                         "a & b <c>")

    def test_boşluqlar_sıxılır(self):
        self.assertEqual(_teqsiz("<p>a</p>\n\n   <p>b</p>"), "a b")


class UyğunluqSınağı(unittest.TestCase):
    def test_eyni(self):
        self.assertTrue(_uyğundur("Sıfırla", "Sıfırla"))

    def test_ascii_yazılış_qəbul_olunur(self):
        self.assertTrue(_uyğundur("Sifirla", "Sıfırla"))
        self.assertTrue(_uyğundur("Cixis", "Çıxış"))

    def test_fərqli(self):
        self.assertFalse(_uyğundur("Sil", "Saxla"))

    def test_boş(self):
        self.assertFalse(_uyğundur("a", ""))


class AtributTapSınağı(unittest.TestCase):
    HTML = ('<div><button data-a-klik="h1">Artır</button>'
            '<button data-a-klik="h2" id="azalt">Azalt</button>'
            '<input data-a-deyisdi="h3" name="ad"></div>')

    def test_mətnə_görə(self):
        self.assertEqual(_atribut_tap(self.HTML, "data-a-klik", "Artır"),
                         "h1")

    def test_kimliyə_görə(self):
        self.assertEqual(_atribut_tap(self.HTML, "data-a-klik", "azalt"),
                         "h2")

    def test_sahə_adına_görə(self):
        self.assertEqual(_atribut_tap(self.HTML, "data-a-deyisdi", "ad"),
                         "h3")

    def test_nişansız_ilk_tapılanı_verir(self):
        self.assertEqual(_atribut_tap(self.HTML, "data-a-klik", None),
                         "h1")

    def test_tapılmayan(self):
        self.assertIsNone(
            _atribut_tap(self.HTML, "data-a-klik", "Yoxdur"))


class HadisəCədvəliSınağı(unittest.TestCase):
    def test_şəkilçilər_ASCII_dir(self):
        for alqor_adı, (dom, şəkilçi) in HADİSƏLƏR.items():
            self.assertTrue(şəkilçi.isascii(),
                            f"{alqor_adı} → {şəkilçi} ASCII deyil")
            self.assertTrue(dom.isascii(), dom)

    def test_şəkilçilər_təkrarlanmır(self):
        şəkilçilər = [ş for _, ş in HADİSƏLƏR.values()]
        self.assertEqual(len(şəkilçilər), len(set(şəkilçilər)))

    def test_JS_tərəfi_eyni_şəkilçiləri_bilir(self):
        """`SKRIPT` içindəki cədvəl Python cədvəli ilə uyğun olmalıdır."""
        for alqor_adı, (dom, şəkilçi) in HADİSƏLƏR.items():
            self.assertTrue(f'["{dom}","{şəkilçi}"]' in P.SKRIPT,
                            f"{alqor_adı} JS cədvəlində yoxdur")


# ═══════════════════════════════════════════════════════════════════════
#  Dil səviyyəsi — pəncərə və göstərmə
# ═══════════════════════════════════════════════════════════════════════

class PəncərəSınağı(unittest.TestCase):
    def test_başlıq(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Mənim tətbiqim", 300, 200)
    yaz(p.başlıq())
son
''')
        self.assertEqual(sətirlər, ["Mənim tətbiqim"])

    def test_başlıq_təyin_olunur(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Köhnə")
    p.başlıq("Yeni")
    yaz(p.başlıq())
son
''')
        self.assertEqual(sətirlər, ["Yeni"])

    def test_sabit_məzmun(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<h1>Salam</h1>)
    yaz(p.HTML())
son
''')
        self.assertEqual(sətirlər, ["<h1>Salam</h1>"])

    def test_funksiya_məzmunu_hər_dəfə_çağırılır(self):
        sətirlər = başsız('''
dəyişən say = 0

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(funksiya()
        say += 1
        qaytar <p>{say}</p>
    son)
    yaz(p.HTML())
    yaz(p.HTML())
son
''')
        self.assertEqual(sətirlər, ["<p>1</p>", "<p>2</p>"])

    def test_atributlar_çevrilir(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<input növ="text" dəyər="a" yer="Ad" söndürülmüş={doğru} />)
    yaz(p.HTML())
son
''')
        self.assertEqual(
            sətirlər,
            ['<input type="text" value="a" placeholder="Ad" disabled>'])

    def test_yanlış_atribut_yazılmır(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<input söndürülmüş={yanlış} />)
    yaz(p.HTML())
son
''')
        self.assertEqual(sətirlər, ["<input>"])

    def test_HTML_qaçışı(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<p>{"<script>"}</p>)
    yaz(p.HTML())
son
''')
        self.assertEqual(sətirlər, ["<p>&lt;script&gt;</p>"])

    def test_hadisə_atributu_HTML_ə_yazılmır(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<button klik={() => 1}>Bas</button>)
    dəyişən h = p.HTML()
    yaz(" klik=" içindədir h)
    yaz("data-a-klik=" içindədir h)
son
''')
        self.assertEqual(sətirlər, ["yanlış", "doğru"])

    def test_hadisə_atributu_funksiya_olmalıdır(self):
        from test_icraci import xəta_tipi
        self.assertEqual(xəta_tipi(BAŞLIQ + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<button klik="mətn">Bas</button>)
    yaz(p.HTML())
son
'''), "TipXətası")

    def test_tək_teqlər_bağlanmır(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<div><br /><hr /><img mənbə="a.png" /></div>)
    yaz(p.HTML())
son
''')
        self.assertEqual(
            sətirlər, ['<div><br><hr><img src="a.png"></div>'])

    def test_səhifə_tam_sənəddir(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Başlıq")
    p.məzmun(<p>a</p>)
    dəyişən s = p.səhifə()
    yaz("<!DOCTYPE html>" içindədir s)
    yaz("<title>Başlıq</title>" içindədir s)
    yaz("charset=\\"UTF-8\\"" içindədir s)
    yaz("alqor-kök" içindədir s)
son
''')
        self.assertEqual(sətirlər, ["doğru"] * 4)

    def test_öz_üslubu_səhifəyə_düşür(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.üslub(x"""
        .mənim{color:red}
    """)
    p.məzmun(<p>a</p>)
    yaz(x".mənim{color:red}" içindədir p.səhifə())
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_ölçü_və_mərkəz_zəncirlənir(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.ölç(640, 480).mərkəzə().ölçüsüSabit()
    yaz(p.başlıq())
son
''')
        self.assertEqual(sətirlər, ["A"])

    def test_bağlanma(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<p>a</p>)
    p.göstər()
    yaz(p.açıqdır())
    p.bağla()
    yaz(p.açıqdır())
son
''')
        self.assertEqual(sətirlər, ["doğru", "yanlış"])

    def test_bağlananda_idarəedicisi(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.bağlananda(() => yaz("sağ ol"))
    p.məzmun(<p>a</p>)
    p.göstər()
    p.bağla()
son
''')
        self.assertEqual(sətirlər, ["sağ ol"])

    def test_başsız_rejim(self):
        sətirlər = başsız('''
funksiya əsas()
    yaz(pəncərə.başsızdır())
son
''')
        self.assertEqual(sətirlər, ["doğru"])


class MenyuSınağı(unittest.TestCase):
    QUR = '''
funksiya qur() -> istənilən
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.menyu([
        pəncərə.menyu("Fayl", [
            pəncərə.element("Yeni", qısayol: "Ctrl+N",
                            klik: () => yaz("yeni")),
            pəncərə.ayırıcı(),
            pəncərə.element("Çıxış", qısayol: "Ctrl+Q",
                            klik: () => p.bağla())
        ]),
        pəncərə.menyu("Kömək", [
            pəncərə.element("Haqqında", klik: () => yaz("haqqında"))
        ])
    ])
    p.məzmun(<p>a</p>)
    qaytar p
son
'''

    def test_menyu_HTML_i(self):
        sətirlər = başsız(self.QUR + '''
funksiya əsas()
    dəyişən h = qur().menyu()
    yaz("Fayl" içindədir h)
    yaz("Kömək" içindədir h)
    yaz("ayırıcı" içindədir h)
    yaz('data-a-qisayol="ctrl+n"' içindədir h)
son
''')
        self.assertEqual(sətirlər, ["doğru"] * 4)

    def test_menyu_elementi_basılır(self):
        sətirlər = başsız(self.QUR + '''
funksiya əsas()
    dəyişən s = pəncərə.sınaq.aç(qur())
    s.klik("Yeni")
    s.klik("Haqqında")
son
''')
        self.assertEqual(sətirlər, ["yeni", "haqqında"])

    def test_menyudan_bağlanma(self):
        sətirlər = başsız(self.QUR + '''
funksiya əsas()
    dəyişən s = pəncərə.sınaq.aç(qur())
    yaz(s.açıqdır())
    s.klik("Çıxış")
    yaz(s.açıqdır())
son
''')
        self.assertEqual(sətirlər, ["doğru", "yanlış"])

    def test_klik_olmayan_element_sönükdür(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.menyu([pəncərə.menyu("Fayl", [
        pəncərə.element("İşləməyən")
    ])])
    p.məzmun(<p>a</p>)
    yaz("sönük" içindədir p.menyu())
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_işarələnmiş_element(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.menyu([pəncərə.menyu("Görünüş", [
        pəncərə.element("Tam ekran", klik: () => 1, işarələnmiş: doğru)
    ])])
    p.məzmun(<p>a</p>)
    yaz("✓" içindədir p.menyu())
son
''')
        self.assertEqual(sətirlər, ["doğru"])


# ═══════════════════════════════════════════════════════════════════════
#  Komponentlər və vəziyyət
# ═══════════════════════════════════════════════════════════════════════

class KomponentSınağı(unittest.TestCase):
    def test_vəziyyət_dəyişəndə_yenidən_göstərilir(self):
        sətirlər = başsız(SAYĞAC + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Sayğac />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.klik("+")
    s.klik("+")
    s.klik("+")
    yaz(s.ehtiva("<h1>3</h1>"))
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_hesablanan_xassə_yenilənir(self):
        """`_keş` təmizlənməsə `ikiqat` köhnə qalardı."""
        sətirlər = başsız(SAYĞAC + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Sayğac />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.klik("+")
    s.klik("+")
    yaz(s.ehtiva('<span id="ikiqat">4</span>'))
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_mənfi_dəyər(self):
        sətirlər = başsız(SAYĞAC + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Sayğac />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.klik("-")
    s.klik("-")
    yaz(s.ehtiva("<h1>-2</h1>"))
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_mətn_teqsiz_oxunur(self):
        sətirlər = başsız(SAYĞAC + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Sayğac />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.klik("+")
    yaz(s.mətn())
son
''')
        self.assertEqual(sətirlər, ["1 2 - +"])

    def test_siyahı_göstərilir(self):
        sətirlər = başsız('''
komponent Siyahı
    vəziyyət sözlər: siyahı[mətn] = ["a", "b"]

    metod əlavə()
        özü.sözlər.əlavə("c")
    son

    göstər()
        qaytar <ul>
            {özü.sözlər.çevir((s) => <li>{s}</li>)}
            <button klik={özü.əlavə}>Əlavə</button>
        </ul>
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Siyahı />)
    dəyişən s = pəncərə.sınaq.aç(p)
    yaz(s.ehtiva("<li>a</li><li>b</li>"))
    s.klik("Əlavə")
    yaz(s.ehtiva("<li>c</li>"))
son
''')
        self.assertEqual(sətirlər, ["doğru", "doğru"])

    def test_sahəyə_yazma(self):
        sətirlər = başsız('''
komponent Form
    vəziyyət ad: mətn = ""

    metod adDəyişdi(dəyər: mətn)
        özü.ad = dəyər
    son

    göstər()
        qaytar <div>
            <input ad="ad" dəyişdi={özü.adDəyişdi} />
            <p>Salam, {özü.ad}!</p>
        </div>
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Form />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.yaz("ad", "Aysel")
    yaz(s.ehtiva("Salam, Aysel!"))
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_istənilən_hadisə(self):
        sətirlər = başsız('''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<div kimlik="qutu"
                  ikiKlik={() => yaz("iki klik")}>Qutu</div>)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.hadisə("ikiKlik", "qutu")
son
''')
        self.assertEqual(sətirlər, ["iki klik"])

    def test_olmayan_hadisə_xəta_verir(self):
        from test_icraci import işlət
        _, xəta = işlət(BAŞLIQ + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<p>a</p>)
    pəncərə.sınaq.aç(p).hadisə("naməlumHadisə")
son
''')
        self.assertIsNotNone(xəta)
        self.assertIn("naməlumHadisə", xəta.mesaj)

    def test_tapılmayan_düymə(self):
        from test_icraci import işlət
        _, xəta = işlət(BAŞLIQ + SAYĞAC + '''
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Sayğac />)
    pəncərə.sınaq.aç(p).klik("Yoxdur")
son
''')
        self.assertIsNotNone(xəta)
        self.assertIn("Yoxdur", xəta.mesaj)

    def test_silinmiş_düyməyə_basmaq_çökmür(self):
        """Köhnə nəsil açarı — HTML yenilənir, xəta atılmır."""
        sətirlər = başsız('''
komponent Dəyişən
    vəziyyət göstər_: məntiq = doğru

    metod gizlət()
        özü.göstər_ = yanlış
    son

    göstər()
        əgər özü.göstər_ onda
            qaytar <button klik={özü.gizlət}>Gizlət</button>
        son
        qaytar <p>gizlədildi</p>
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Dəyişən />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.klik("Gizlət")
    yaz(s.mətn())
son
''')
        self.assertEqual(sətirlər, ["gizlədildi"])


# ═══════════════════════════════════════════════════════════════════════
#  Dialoqlar — başsız rejimdə əvvəlcədən verilən cavablarla
# ═══════════════════════════════════════════════════════════════════════

class DialoqSınağı(unittest.TestCase):
    BAŞ = "gətir pəncərə\ngətir pəncərə.dialoq\n"

    def işlət(self, kod: str) -> list[str]:
        return çıxış(self.BAŞ + kod)

    def test_təsdiq_bəli(self):
        sətirlər = self.işlət('''
funksiya əsas()
    pəncərə.sınaq.cavablar([doğru])
    yaz(dialoq.təsdiqlə("Silinsin?", "Geri qaytarmaq olmaz"))
son
''')
        self.assertEqual(sətirlər, ["doğru"])

    def test_təsdiq_xeyr(self):
        sətirlər = self.işlət('''
funksiya əsas()
    pəncərə.sınaq.cavablar([yanlış])
    yaz(dialoq.təsdiqlə("Silinsin?"))
son
''')
        self.assertEqual(sətirlər, ["yanlış"])

    def test_cavab_verilməyibsə_standart(self):
        sətirlər = self.işlət('''
funksiya əsas()
    yaz(dialoq.təsdiqlə("Silinsin?"))
son
''')
        self.assertEqual(sətirlər, ["yanlış"])

    def test_növbə_sırası_ilə_işlənir(self):
        sətirlər = self.işlət('''
funksiya əsas()
    pəncərə.sınaq.cavablar([doğru, yanlış, doğru])
    yaz(dialoq.təsdiqlə("1"))
    yaz(dialoq.təsdiqlə("2"))
    yaz(dialoq.təsdiqlə("3"))
son
''')
        self.assertEqual(sətirlər, ["doğru", "yanlış", "doğru"])

    def test_soruş(self):
        sətirlər = self.işlət('''
funksiya əsas()
    pəncərə.sınaq.cavablar(["Aysel"])
    yaz(dialoq.soruş("Ad", "Adınız nədir?") ?? "boş")
son
''')
        self.assertEqual(sətirlər, ["Aysel"])

    def test_fayl_saxla(self):
        sətirlər = self.işlət('''
funksiya əsas()
    pəncərə.sınaq.cavablar(["/tmp/a.txt"])
    varsa yol = dialoq.faylSaxla(standartAd: "a.txt") onda
        yaz(yol)
    yoxsa
        yaz("ləğv")
    son
son
''')
        self.assertEqual(sətirlər, ["/tmp/a.txt"])

    def test_fayl_saxla_ləğv(self):
        sətirlər = self.işlət('''
funksiya əsas()
    yoxdursa yol = dialoq.faylSaxla(standartAd: "a.txt") onda
        yaz("ləğv")
    son
son
''')
        self.assertEqual(sətirlər, ["ləğv"])

    def test_jurnal_yazılır(self):
        sətirlər = self.işlət('''
funksiya əsas()
    pəncərə.sınaq.təmizlə()
    pəncərə.sınaq.cavablar([doğru])
    dialoq.təsdiqlə("Başlıq", "Mesaj")
    dialoq.məlumat("Məlumat")
    dəyişən j = pəncərə.sınaq.jurnal()
    yaz(uzunluq(j))
    yaz(j[0][0])
    yaz(j[0][1])
    yaz(j[1][0])
son
''')
        self.assertEqual(
            sətirlər, ["2", "təsdiqlə", "Başlıq Mesaj", "məlumat"])

    def test_bildiriş_başsızda_səssizdir(self):
        sətirlər = self.işlət('''
funksiya əsas()
    pəncərə.bildiriş("Hazırdır", "Fayl saxlanıldı")
    yaz("davam")
son
''')
        self.assertEqual(sətirlər, ["davam"])

    def test_dialoq_komponent_metodundan(self):
        sətirlər = self.işlət('''
komponent Siyahı
    vəziyyət sözlər: siyahı[mətn] = ["a", "b"]

    metod təmizlə()
        əgər dialoq.təsdiqlə("Təmizlənsin?") onda
            özü.sözlər = []
        son
    son

    göstər()
        qaytar <div>
            <p>{uzunluq(özü.sözlər)} element</p>
            <button klik={özü.təmizlə}>Təmizlə</button>
        </div>
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("A")
    p.məzmun(<Siyahı />)
    dəyişən s = pəncərə.sınaq.aç(p)

    pəncərə.sınaq.cavablar([yanlış])
    s.klik("Təmizlə")
    yaz(s.ehtiva("2 element"))

    pəncərə.sınaq.cavablar([doğru])
    s.klik("Təmizlə")
    yaz(s.ehtiva("0 element"))
son
''')
        self.assertEqual(sətirlər, ["doğru", "doğru"])


# ═══════════════════════════════════════════════════════════════════════
#  HTTP tərəfi — həqiqi server, brauzer açmadan
# ═══════════════════════════════════════════════════════════════════════

class ServerSınağı(unittest.TestCase):
    """Pəncərənin brauzerə verdiyi səhifə və hadisə son nöqtəsi."""

    KOD = """
gətir pəncərə

komponent Sayğac
    vəziyyət say: tam = 0

    metod artır()
        özü.say += 1
    son

    göstər()
        qaytar <div><h1>{özü.say}</h1>
            <button kimlik="artır" klik={özü.artır}>+</button></div>
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Sınaq", 300, 200)
    p.menyu([pəncərə.menyu("Fayl", [
        pəncərə.element("Çıxış", qısayol: "Ctrl+Q", klik: () => p.bağla())
    ])])
    p.məzmun(<Sayğac />)
    p.göstər()
    pəncərə.işlət()
son
"""

    def setUp(self):
        from alqor.icraci import İcraçı
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı

        x = XətaToplayıcı()
        mənbə = Mənbə.mətndən(self.KOD, "sınaq.alqor", x)
        ağac = Parser(Lekser(mənbə, x).leksə(), mənbə, x).ayır()
        self.assertTrue(x.uğurludur(), x.hesabat(False))

        # Başsızlıq söndürülür, brauzer isə açılmır
        self._köhnə_başsız = P._başsız_rejimdir
        self._köhnə_aç = P._pəncərəni_aç
        P._başsız_rejimdir = lambda: False
        P._pəncərəni_aç = lambda t, p: "sınaq"

        self.sətirlər: list[str] = []
        self.icraçı = İcraçı(çıxış=self.sətirlər.append, giriş=lambda: "")
        self.sap = threading.Thread(
            target=lambda: self.icraçı.işlət(ağac, []), daemon=True)
        self.sap.start()

        for _ in range(200):
            t = getattr(self.icraçı, "_pəncərə_tətbiqi", None)
            if t is not None and t._port:
                break
            time.sleep(0.01)
        self.t = getattr(self.icraçı, "_pəncərə_tətbiqi", None)
        self.assertIsNotNone(self.t, "server qalxmadı")
        self.ünvan = f"http://127.0.0.1:{self.t._port}"

    def tearDown(self):
        if self.t is not None:
            self.t.dayandır()
        self.sap.join(timeout=5)
        P._başsız_rejimdir = self._köhnə_başsız
        P._pəncərəni_aç = self._köhnə_aç

    # ── Köməkçilər ────────────────────────────────────────────────────

    def al(self, yol: str) -> str:
        with urllib.request.urlopen(self.ünvan + yol, timeout=10) as c:
            return c.read().decode("utf-8")

    def göndər(self, yol: str, verilənlər: dict) -> dict:
        sorğu = urllib.request.Request(
            self.ünvan + yol,
            data=_json_bayt(verilənlər),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(sorğu, timeout=10) as c:
            return json.loads(c.read().decode("utf-8"))

    @staticmethod
    def açar(HTML: str, yaxınlıq: str = "") -> str:
        baş = HTML.index(yaxınlıq) if yaxınlıq else 0
        i = HTML.index('data-a-klik="', baş) + len('data-a-klik="')
        return HTML[i:HTML.index('"', i)]

    # ── Sınaqlar ──────────────────────────────────────────────────────

    def test_səhifə_verilir(self):
        s = self.al("/")
        for parça in ("<!DOCTYPE html>", '<meta charset="UTF-8">',
                      "<title>Sınaq</title>", 'id="alqor-kök"',
                      'id="alqor-menyu"', "data-a-klik=",
                      'data-a-qisayol="ctrl+q"', "<h1>0</h1>"):
            self.assertIn(parça, s)

    def test_hadisə_vəziyyəti_dəyişir(self):
        s = self.al("/")
        açar = self.açar(s, 'id="artır"')
        for n in (1, 2, 3):
            cavab = self.göndər("/_alqor/hadise",
                                {"id": açar, "dəyər": None})
            self.assertIn(f"<h1>{n}</h1>", cavab["html"])
            self.assertEqual(cavab["başlıq"], "Sınaq")
            açar = self.açar(cavab["html"], 'id="artır"')

    def test_köhnə_açar_HTML_i_yeniləyir(self):
        s = self.al("/")
        açar = self.açar(s, 'id="artır"')
        self.göndər("/_alqor/hadise", {"id": açar, "dəyər": None})
        # Həmin açar artıq keçmiş nəsildəndir
        cavab = self.göndər("/_alqor/hadise", {"id": açar, "dəyər": None})
        self.assertTrue(cavab.get("köhnə"))
        self.assertIn("<h1>1</h1>", cavab["html"])

    def test_vəziyyət_son_nöqtəsi(self):
        self.assertEqual(json.loads(self.al("/_alqor/veziyyet")),
                         {"pəncərələr": 1})

    def test_olmayan_yol_404(self):
        with self.assertRaises(urllib.error.HTTPError) as k:
            self.al("/yoxdur")
        self.assertEqual(k.exception.code, 404)

    def test_menyudan_bağlanma_dövrü_bitirir(self):
        s = self.al("/")
        i = s.index('data-a-qisayol="ctrl+q"')
        baş = s.rfind('data-a-klik="', 0, i) + len('data-a-klik="')
        açar = s[baş:s.index('"', baş)]
        cavab = self.göndər("/_alqor/hadise", {"id": açar, "dəyər": None})
        self.assertTrue(cavab.get("bağlı"))
        self.sap.join(timeout=5)
        self.assertFalse(self.sap.is_alive(), "`işlət()` dövrü bitməli idi")

    def test_bağlandı_siqnalı(self):
        self.göndər("/_alqor/baglandi", {})
        self.sap.join(timeout=5)
        self.assertFalse(self.sap.is_alive())

    def test_idarəedici_əsas_sapda_işləyir(self):
        """
        Server sapından göndərilən iş `işlət()` dövrünün sapında
        icra olunmalıdır — `dialoq.*` üçün bu şərtdir.
        """
        t = self.t
        assert t is not None
        nəticə: list[str] = []

        def server_sapı_kimi() -> None:
            nəticə.append(
                t.növbəyə(lambda: threading.current_thread().name))

        s = threading.Thread(target=server_sapı_kimi, name="saxta-server")
        s.start()
        s.join(timeout=10)
        self.assertEqual(nəticə, [self.sap.name])


def _json_bayt(d: dict) -> bytes:
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


# ═══════════════════════════════════════════════════════════════════════
#  Nümunə
# ═══════════════════════════════════════════════════════════════════════

class NümunəSınağı(unittest.TestCase):
    def test_06_desktop_işləyir(self):
        yol = (Path(__file__).parent.parent.parent / "numuneler"
               / "06-desktop.alqor")
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
        self.assertIn("Sayğac", hamısı)
        self.assertIn("<h1>3</h1>" if "<h1>" in hamısı else "3", hamısı)
        self.assertIn("2 dəfə soruşuldu", hamısı)
        self.assertIn("açıqdır = yanlış", hamısı)


if __name__ == "__main__":
    unittest.main(verbosity=2)
