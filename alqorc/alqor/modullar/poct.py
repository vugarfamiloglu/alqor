"""
`poçt` — e-poçt göndərmə (SMTP) və məktub oxuma (§ 10.17).

    gətir poçt

    dəyişən m = poçt.məktub(
        kimdən: "Alqor <bot@alqor.az>",
        kimə: ["aysel@nümunə.az"],
        mövzu: "Hesabat hazırdır",
        mətn: "Salam! Hesabat əlavədədir.",
        html: "<p>Salam! <b>Hesabat</b> əlavədədir.</p>",
        əlavələr: ["hesabat.pdf"],
    )

    dəyişən s = poçt.smtp("smtp.nümunə.az", port: 587,
                          istifadəçi: "bot@alqor.az", parol: mühit("SMTP_PAROL"))
    s.göndər(m)
    s.bağla()

    // Bir sətirdə:
    poçt.göndər(m, {"host": "smtp.nümunə.az", "port": 465, "şifrələmə": "ssl",
                    "istifadəçi": "…", "parol": "…"})

    // Sınaqlar üçün — heç nə göndərmir, yaddaşda saxlayır:
    dəyişən t = poçt.sınaq()
    t.göndər(m)
    yaz(t.göndərilənlər()[0]["mövzu"])

`şifrələmə`: "starttls" (port 587, standart), "ssl" (port 465), "yox"
(yalnız yerli sınaq serverləri üçün). Başlıqlarda sətir sonu (CR/LF)
qadağandır — başlıq inyeksiyası mümkün deyil.
"""

from __future__ import annotations

import mimetypes
import smtplib
import ssl
from email import policy
from email.headerregistry import Address
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formatdate, getaddresses, make_msgid
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı
from .validasiya import ePoçtdur


def _xəta(mesaj: str, tip: str = "PoçtXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _başlıq(x: Any, ad: str) -> str:
    s = str(x)
    if "\r" in s or "\n" in s:
        raise _xəta(f"`{ad}` sətir sonu ehtiva edə bilməz")
    return s


def _ünvanlar(x: Any, ad: str) -> list[str]:
    if x is None:
        return []
    siyahı = x if isinstance(x, list) else [x]
    n = []
    for e in siyahı:
        if not isinstance(e, str):
            raise _xəta(f"`{ad}` mətn və ya mətn siyahısı olmalıdır, "
                        f"`{tip_adı(e)}` gəlib", "TipXətası")
        _başlıq(e, ad)
        for adı, ünvan in getaddresses([e]):
            if not ePoçtdur(ünvan):
                raise _xəta(f"`{ad}`: `{e}` düzgün e-poçt ünvanı deyil")
            n.append(str(Address(adı, addr_spec=ünvan)) if adı else ünvan)
    return n


class Məktub:
    ALQOR_TİP_ADI = "məktub"

    def __init__(self, kimdən: Any = None, kimə: Any = None,
                 mövzu: Any = "", mətn: Any = None, html: Any = None,
                 kopya: Any = None, gizliKopya: Any = None,
                 cavabla: Any = None, əlavələr: Any = None,
                 başlıqlar: Any = None):
        self.kimdən = _ünvanlar(kimdən, "kimdən")[:1]
        self.kimə = _ünvanlar(kimə, "kimə")
        self.kopya = _ünvanlar(kopya, "kopya")
        self.gizli = _ünvanlar(gizliKopya, "gizliKopya")
        self.cavabla = _ünvanlar(cavabla, "cavabla")
        self.mövzu = _başlıq(mövzu, "mövzu")
        self.mətn = None if mətn is None else str(mətn)
        self.html = None if html is None else str(html)
        self.başlıqlar: dict[str, str] = {}
        for a, v in (başlıqlar or {}).items():
            self.başlıqlar[_başlıq(a, "başlıq")] = _başlıq(v, a)
        self.əlavələr: list[tuple[str, bytes, str]] = []
        for e in (əlavələr if isinstance(əlavələr, list)
                  else [əlavələr] if əlavələr else []):
            self.əlavə_et(e)

    def __repr__(self) -> str:
        return f"<məktub {self.mövzu!r} → {', '.join(self.kimə)}>"

    def əlavə_et(self, e: Any, ad: Any = None, növ: Any = None) -> None:
        if isinstance(e, dict):
            ad, növ = e.get("ad", ad), e.get("növ", növ)
            məzmun = e.get("məzmun")
            if məzmun is None:
                raise _xəta("əlavə lüğətində `məzmun` lazımdır")
            b = məzmun.encode("utf-8") if isinstance(məzmun, str) \
                else bytes(məzmun)
            if not ad:
                raise _xəta("əlavə lüğətində `ad` lazımdır")
        else:
            p = Path(str(e))
            try:
                b = p.read_bytes()
            except FileNotFoundError:
                raise AlqorXəta("FaylTapılmadıXətası",
                                f'"{e}" faylı tapılmadı', None, "ALQ-R009")
            ad = ad or p.name
        ad = _başlıq(ad, "əlavə adı")
        növ = növ or mimetypes.guess_type(ad)[0] or \
            "application/octet-stream"
        if "/" not in str(növ):
            raise _xəta(f"əlavə növü `{növ}` yanlışdır (məs. `text/plain`)")
        self.əlavələr.append((ad, b, str(növ)))

    def mesaj(self) -> EmailMessage:
        if not self.kimdən:
            raise _xəta("`kimdən` göstərilməyib")
        if not (self.kimə or self.kopya or self.gizli):
            raise _xəta("alıcı yoxdur (`kimə`, `kopya` və ya `gizliKopya`)")
        m = EmailMessage(policy=policy.SMTP)
        m["From"] = self.kimdən[0]
        if self.kimə:
            m["To"] = ", ".join(self.kimə)
        if self.kopya:
            m["Cc"] = ", ".join(self.kopya)
        if self.cavabla:
            m["Reply-To"] = ", ".join(self.cavabla)
        m["Subject"] = self.mövzu
        m["Date"] = formatdate(localtime=True)
        domen = self.kimdən[0].rsplit("@", 1)[-1].rstrip(">")
        m["Message-ID"] = make_msgid(domain=domen.encode("idna").decode()
                                     if domen else None)
        m["X-Mailer"] = "Alqor poçt"
        for a, v in self.başlıqlar.items():
            m[a] = v
        if self.mətn is not None or self.html is None:
            m.set_content(self.mətn or "", charset="utf-8")
            if self.html is not None:
                m.add_alternative(self.html, subtype="html", charset="utf-8")
        else:
            m.set_content(self.html, subtype="html", charset="utf-8")
        for ad, b, növ in self.əlavələr:
            əsas, alt = növ.split("/", 1)
            m.add_attachment(b, maintype=əsas, subtype=alt, filename=ad)
        return m

    def alıcılar(self) -> list[str]:
        return [a for _, a in getaddresses(self.kimə + self.kopya +
                                           self.gizli)]


Məktub.ALQOR_METODLARI = {
    "əlavəEt": lambda i, m, e, ad=None, növ=None: m.əlavə_et(e, ad, növ),
    "mətn": lambda i, m: m.mesaj().as_string(),
    "alıcılar": lambda i, m: m.alıcılar(),
    "mövzu": lambda i, m: m.mövzu,
}


# ── Göndəricilər ──────────────────────────────────────────────────────

class SMTP:
    ALQOR_TİP_ADI = "smtp"

    def __init__(self, host: Any, port: Any = None, istifadəçi: Any = None,
                 parol: Any = None, şifrələmə: Any = "starttls",
                 vaxtLimiti: Any = 30, yoxla: Any = True):
        if şifrələmə not in ("starttls", "ssl", "yox"):
            raise _xəta('`şifrələmə` "starttls", "ssl" və ya "yox" '
                        "olmalıdır")
        self.host = str(host)
        self.port = int(port) if port else (465 if şifrələmə == "ssl"
                                            else 587)
        self.istifadəçi = istifadəçi
        self.parol = parol
        self.şifrələmə = şifrələmə
        self.vaxt = float(vaxtLimiti)
        self.kontekst = ssl.create_default_context()
        if not yoxla:
            self.kontekst.check_hostname = False
            self.kontekst.verify_mode = ssl.CERT_NONE
        self._s: smtplib.SMTP | None = None

    def __repr__(self) -> str:
        return f"<smtp {self.host}:{self.port}>"

    def _qoşul(self) -> smtplib.SMTP:
        if self._s is not None:
            try:
                self._s.noop()
                return self._s
            except smtplib.SMTPException:
                self._s = None
            except OSError:
                self._s = None
        s = None
        try:
            if self.şifrələmə == "ssl":
                s = smtplib.SMTP_SSL(self.host, self.port, timeout=self.vaxt,
                                     context=self.kontekst)
            else:
                s = smtplib.SMTP(self.host, self.port, timeout=self.vaxt)
                s.ehlo()
                if self.şifrələmə == "starttls":
                    s.starttls(context=self.kontekst)
                    s.ehlo()
            if self.istifadəçi:
                s.login(str(self.istifadəçi), str(self.parol or ""))
        except smtplib.SMTPAuthenticationError:
            s.close()
            raise _xəta("SMTP: istifadəçi adı və ya parol yanlışdır")
        except (OSError, smtplib.SMTPException) as x:
            if s is not None:
                s.close()
            raise _xəta(f"SMTP serverinə qoşulmaq olmadı "
                        f"({self.host}:{self.port}): {x}", "ŞəbəkəXətası")
        self._s = s
        return s

    def göndər(self, m: Any) -> dict:
        if not isinstance(m, Məktub):
            raise _xəta(f"`göndər` məktub gözləyir, `{tip_adı(m)}` gəlib",
                        "TipXətası")
        msg = m.mesaj()
        s = self._qoşul()
        try:
            rədd = s.send_message(msg, to_addrs=m.alıcılar())
        except smtplib.SMTPRecipientsRefused as x:
            raise _xəta("bütün alıcılar rədd edildi: " +
                        ", ".join(x.recipients))
        except smtplib.SMTPException as x:
            raise _xəta(f"SMTP: {x}")
        return {"id": msg["Message-ID"],
                "rəddEdilənlər": {a: v[1].decode("utf-8", "replace")
                                  if isinstance(v[1], bytes) else str(v[1])
                                  for a, v in rədd.items()}}

    def bağla(self) -> None:
        if self._s is not None:
            try:
                self._s.quit()
            except (OSError, smtplib.SMTPException):
                pass
            self._s = None


class Sınaq:
    """Heç nə göndərmir — məktubları yaddaşda saxlayır."""
    ALQOR_TİP_ADI = "smtp"

    def __init__(self):
        self.qutu: list[dict] = []

    def __repr__(self) -> str:
        return f"<smtp sınaq ({len(self.qutu)} məktub)>"

    def göndər(self, m: Any) -> dict:
        if not isinstance(m, Məktub):
            raise _xəta("`göndər` məktub gözləyir", "TipXətası")
        msg = m.mesaj()
        d = oxu(msg.as_bytes())
        d["alıcılar"] = m.alıcılar()
        self.qutu.append(d)
        return {"id": msg["Message-ID"], "rəddEdilənlər": {}}

    def bağla(self) -> None:
        pass


_GÖNDƏRİCİ = {
    "göndər": lambda i, s, m: s.göndər(m),
    "bağla": lambda i, s: s.bağla(),
}
SMTP.ALQOR_METODLARI = dict(_GÖNDƏRİCİ)
Sınaq.ALQOR_METODLARI = {
    **_GÖNDƏRİCİ,
    "göndərilənlər": lambda i, s: list(s.qutu),
    "təmizlə": lambda i, s: s.qutu.clear(),
}


def oxu(x: Any) -> dict:
    """Xam məktub (RFC 5322) → lüğət."""
    b = x.encode("utf-8") if isinstance(x, str) else bytes(x)
    m = BytesParser(policy=policy.default).parsebytes(b)
    mətn = m.get_body(preferencelist=("plain",))
    html = m.get_body(preferencelist=("html",))
    əlavələr = []
    for p in m.iter_attachments():
        məzmun = p.get_payload(decode=True) or b""
        əlavələr.append({"ad": p.get_filename() or "", "növ":
                         p.get_content_type(), "ölçü": len(məzmun),
                         "məzmun": məzmun})
    return {
        "kimdən": str(m.get("From", "")),
        "kimə": [a for _, a in getaddresses(m.get_all("To", []))],
        "kopya": [a for _, a in getaddresses(m.get_all("Cc", []))],
        "mövzu": str(m.get("Subject", "")),
        "tarix": str(m.get("Date", "")),
        "id": str(m.get("Message-ID", "")),
        "mətn": mətn.get_content() if mətn is not None else None,
        "html": html.get_content() if html is not None else None,
        "əlavələr": əlavələr,
        "başlıqlar": {a: str(v) for a, v in m.items()},
    }


def göndər(m: Any, server: Any) -> dict:
    if not isinstance(server, dict):
        raise _xəta("`server` lüğət olmalıdır: "
                    '{"host": …, "port": …, "istifadəçi": …, "parol": …}',
                    "TipXətası")
    if "host" not in server:
        raise _xəta("`server` lüğətində `host` lazımdır")
    s = SMTP(server["host"], server.get("port"), server.get("istifadəçi"),
             server.get("parol"), server.get("şifrələmə", "starttls"),
             server.get("vaxtLimiti", 30), server.get("yoxla", True))
    try:
        return s.göndər(m)
    finally:
        s.bağla()


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "məktub": D("məktub", Məktub, 0, 10),
        "smtp": D("smtp", SMTP, 1, 7),
        "sınaq": D("sınaq", Sınaq),
        "göndər": D("göndər", göndər, 2, 2),
        "oxu": D("oxu", oxu, 1, 1),
        "ünvanDüzgündür": D("ünvanDüzgündür", ePoçtdur, 1, 1),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    m, e = T.MƏTN, T.İSTƏNİLƏN
    S = T.Sadə("smtp")
    return {
        "məktub": Fsərbəst(T.Sadə("məktub")),
        "smtp": Fsərbəst(S),
        "sınaq": F(qaytarır=S),
        "göndər": F(T.Sadə("məktub"), T.Lüğət(m, e),
                    qaytarır=T.Lüğət(m, e)),
        "oxu": F(e, qaytarır=T.Lüğət(m, e)),
        "ünvanDüzgündür": F(e, qaytarır=T.MƏNTİQ),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, h = T.MƏTN, T.İSTƏNİLƏN, T.HEÇ
    M = T.Sadə("məktub")
    return {
        "məktub": {
            "əlavəEt": F(e, m, m, qaytarır=h, standart=2),
            "mətn": F(qaytarır=m), "alıcılar": F(qaytarır=T.Siyahı(m)),
            "mövzu": F(qaytarır=m),
        },
        "smtp": {
            "göndər": F(M, qaytarır=T.Lüğət(m, e)),
            "bağla": F(qaytarır=h),
            "göndərilənlər": F(qaytarır=T.Siyahı(T.Lüğət(m, e))),
            "təmizlə": F(qaytarır=h),
        },
    }
