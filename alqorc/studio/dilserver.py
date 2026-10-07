"""
Studio ↔ `alqorls` körpüsü.

Studio redaktoru tamamlama, imza köməyi, hover və təyinata keçid üçün
VS Code ilə EYNİ dil serverini işlədir — ayrıca proses yox, eyni
prosesdə `alqorls.Server` nümunəsi. Sənədlər yaddaşda saxlanılır;
hər sorğuda redaktorun cari mətni ilə sinxronlaşdırılır.

Mövqelər LSP formatındadır (sətir 0-dan, sütun UTF-16 vahidi) — brauzerin
JavaScript sətirləri də UTF-16 olduğu üçün çevirmə lazım deyil.
"""

from __future__ import annotations

import io
import threading
from pathlib import Path
from typing import Any

from alqor import alqorls as L


class _Udum(io.RawIOBase):
    """Bildirişləri (diaqnostika) udur — Studio onları `/api/yoxla`-dan alır."""

    def writable(self) -> bool:
        return True

    def write(self, b) -> int:
        return len(b)


class DilKörpüsü:
    def __init__(self, kök: Path, rejim: str = "normal"):
        self.kök = Path(kök).resolve()
        self._kilid = threading.Lock()
        self.s = L.Server(io.BytesIO(), _Udum())
        self.s.m_initialize({"rootUri": self.kök.as_uri(),
                             "initializationOptions": {"tipRejimi": rejim}})

    def _sinxronla(self, yol: Path, mətn: str) -> str:
        uri = yol.as_uri()
        d = self.s.sənədlər.get(uri)
        if d is None:
            self.s.m_didOpen({"textDocument": {
                "uri": uri, "text": mətn, "version": 1}})
        elif d.mətn != mətn:
            self.s.m_didChange({
                "textDocument": {"uri": uri, "version": d.versiya + 1},
                "contentChanges": [{"text": mətn}]})
        return uri

    def _nisbi(self, uri: str) -> str | None:
        p = L.uri_yolu(uri)
        try:
            return p.resolve().relative_to(self.kök).as_posix()
        except (ValueError, OSError, AttributeError):
            return None

    def sorğu(self, metod: str, yol: Path, mətn: str, sətir: int,
              sütun: int, yeni_ad: str | None = None) -> Any:
        işləyici = {
            "tamamla": L.Server.m_completion,
            "imza": L.Server.m_signatureHelp,
            "hover": L.Server.m_hover,
            "teyinat": L.Server.m_definition,
            "istinadlar": L.Server.m_references,
            "simvollar": L.Server.m_documentSymbol,
            "adDəyiş": L.Server.m_rename,
        }.get(metod)
        if işləyici is None:
            raise ValueError(f"naməlum metod: {metod}")
        with self._kilid:
            uri = self._sinxronla(yol, mətn)
            p = {"textDocument": {"uri": uri},
                 "position": {"line": sətir, "character": sütun},
                 "context": {"includeDeclaration": True}}
            if yeni_ad is not None:
                p["newName"] = yeni_ad
            try:
                nəticə = işləyici(self.s, p)
            except L.Xəta as x:
                raise ValueError(str(x)) from None
            if metod == "adDəyiş":
                return self._dəyişikliklər(nəticə)
        if metod == "istinadlar":
            return [{"yol": self._nisbi(x["uri"]), "aralıq": x["range"]}
                    for x in nəticə or [] if self._nisbi(x["uri"])]
        if metod == "teyinat" and nəticə:
            # Layihə daxilindəki fayla nisbi yol (Studio faylı özü açır)
            n = []
            for x in nəticə:
                p = L.uri_yolu(x["uri"])
                try:
                    nisbi = p.resolve().relative_to(self.kök).as_posix()
                except (ValueError, OSError, AttributeError):
                    continue
                n.append({"yol": nisbi, "aralıq": x["range"]})
            return n
        return nəticə

    def _dəyişikliklər(self, edit: dict) -> dict[str, str]:
        """WorkspaceEdit → {nisbi yol: yeni mətn} (açıq sənəd və ya disk)."""
        n: dict[str, str] = {}
        for uri, dəyişikliklər in (edit.get("changes") or {}).items():
            nisbi = self._nisbi(uri)
            if nisbi is None:
                continue
            d = self.s.sənədlər.get(uri)
            mətn = d.mətn if d is not None else L.uri_yolu(uri).read_text(
                encoding="utf-8")
            m = L.Mövqelər(mətn)
            for x in sorted(dəyişikliklər, key=lambda x: (
                    x["range"]["start"]["line"],
                    x["range"]["start"]["character"]), reverse=True):
                b = m.ofset(x["range"]["start"])
                e = m.ofset(x["range"]["end"])
                mətn = mətn[:b] + x["newText"] + mətn[e:]
            n[nisbi] = mətn
        return n

    def bağla(self, yol: Path) -> None:
        with self._kilid:
            self.s.sənədlər.pop(yol.as_uri(), None)
