"""
Alqor Studio — "yeni layihə" şablonları: konsol, veb, desktop.

Hər şablon `numuneler/` qovluğundakı nümunələrin üslubundadır və
`-- sınaq` arqumenti ilə PORT/PƏNCƏRƏ AÇMADAN yoxlana bilir.
"""

from __future__ import annotations

KONSOL = """\
// {ad} — konsol proqramı
//
//   alqor işlət əsas.alqor

funksiya salamla(ad: mətn) -> mətn
    qaytar "Salam, {{ad}}!"
son

funksiya əsas()
    yaz("Adınızı daxil edin:")
    dəyişən ad = oxu()
    əgər ad.kəs() == "" onda
        ad = "dünya"
    son
    yaz(salamla(ad))

    hər i üçün 1..3 içində
        yaz("{{i}}. sətir")
    son
son
"""

VEB = """\
// {ad} — veb server
//
//   alqor işlət əsas.alqor            serveri işə salır (port 8080)
//   alqor işlət əsas.alqor -- sınaq   port açmadan yoxlayır

gətir veb
gətir vidjet

funksiya serveriQur() -> istənilən
    dəyişən s = yeni veb.Server()
    s.ara(veb.jurnal())

    s.al("/", funksiya(sorğu)
        qaytar veb.html(vidjet.səhifə(başlıq: "{ad}", məzmun: [
            vidjet.başlıq(mətn: "{ad}", altMətn: "Alqor ilə yazılıb"),
            vidjet.mətn(məzmun: "Salam, dünya!")
        ]))
    son)

    s.al("/api/salam/:ad", (sorğu) =>
        veb.json({{"salam": sorğu.parametrlər["ad"]}}))

    qaytar s
son

funksiya əsas(arqumentlər: siyahı[mətn])
    dəyişən s = serveriQur()
    əgər "sınaq" içindədir arqumentlər onda
        dəyişən c = veb.sınaq.server(s).al("/")
        yaz("Vəziyyət: {{c.vəziyyət()}}")
        qaytar
    son
    yaz("Server: http://127.0.0.1:8080")
    s.dinlə(8080)
son
"""

DESKTOP = """\
// {ad} — desktop tətbiqi
//
//   alqor işlət əsas.alqor            pəncərəni açır
//   alqor işlət əsas.alqor -- sınaq   pəncərə açmadan yoxlayır
//
// Alqor Studio: soldakı paletdən elementə İKİ DƏFƏ klikləyin —
// lazım olan vəziyyət və idarəedici kodu avtomatik yazılır.

gətir pəncərə
gətir vidjet

komponent Tətbiq
    vəziyyət say: tam = 0

    metod artır()
        özü.say += 1
    son

    göstər()
        qaytar vidjet.sütun(boşluq: 12, məzmun: [
            vidjet.başlıq(mətn: "{ad}"),
            vidjet.statistika(etiket: "Sayğac", dəyər: "{{özü.say}}"),
            vidjet.düymə(mətn: "Artır", klik: özü.artır)
        ])
    son
son

funksiya əsas(arqumentlər: siyahı[mətn])
    dəyişən p = yeni pəncərə.Pəncərə("{ad}", 640, 480)
    p.məzmun(<Tətbiq />)

    əgər "sınaq" içindədir arqumentlər onda
        dəyişən s = pəncərə.sınaq.aç(p)
        s.klik("Artır")
        yaz("Sayğac: {{s.mətn()}}")
        qaytar
    son

    p.mərkəzə()
    p.göstər()
    pəncərə.işlət()
son
"""

LAYİHƏ = """\
[layihə]
ad = "{ad}"
versiya = "0.1.0"
növ = "{növ}"

[tip]
rejim = "normal"

[format]
girinti = 4
ascii_düzəlt = doğru
"""

ŞABLONLAR: dict[str, tuple[str, str]] = {
    "konsol": ("Konsol proqramı", KONSOL),
    "veb": ("Veb server", VEB),
    "desktop": ("Desktop tətbiqi", DESKTOP),
}


def siyahı() -> list[dict]:
    return [{"növ": n, "ad": a} for n, (a, _) in ŞABLONLAR.items()]


def fayllar(növ: str, ad: str) -> dict[str, str]:
    """Şablonun faylları: nisbi yol → məzmun."""
    if növ not in ŞABLONLAR:
        raise KeyError(f"`{növ}` şablonu yoxdur. Mövcud: "
                       f"{', '.join(ŞABLONLAR)}")
    _, mətn = ŞABLONLAR[növ]
    return {
        "əsas.alqor": mətn.format(ad=ad),
        "layihe.alqor": LAYİHƏ.format(ad=ad, növ=növ),
    }
