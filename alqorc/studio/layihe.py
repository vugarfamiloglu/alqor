"""
Alqor Studio — layihə qovluğu: fayl ağacı və fayl əməliyyatları.

TƏHLÜKƏSİZLİK
─────────────
Bütün yollar layihənin KÖK qovluğuna nisbətəndir və ondan kənara çıxa
bilməz. Yoxlama iki addımdır:

  1. Mətn səviyyəsində: mütləq yol, `..` hissəsi, NUL simvolu, sürücü
     hərfi (`C:`) rədd edilir
  2. Fayl sistemi səviyyəsində: `Path.resolve()` (simvolik keçidlər
     açılır) + `is_relative_to(kök)` — sətir `startswith` İŞLƏNMİR,
     çünki `/layihə-gizli` də `/layihə` ilə başlayır
"""

from __future__ import annotations
import os
import secrets
import shutil
from pathlib import Path, PurePosixPath

# Ağacda göstərilməyən qovluqlar
GİZLİ_QOVLUQLAR = frozenset({
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv",
    "venv", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
})
MAKS_FAYL = 2 * 1024 * 1024        # redaktorda açılan faylın həddi
MAKS_ELEMENT = 5000                 # ağacda ən çox element


class YolXətası(Exception):
    """İstifadəçiyə göstərilən fayl xətası. `kod` — HTTP vəziyyəti."""

    def __init__(self, mesaj: str, kod: int = 400):
        super().__init__(mesaj)
        self.kod = kod


class Layihə:
    def __init__(self, kök: str | Path):
        self.kök = Path(kök).resolve()
        if not self.kök.is_dir():
            raise YolXətası(f'"{kök}" qovluq deyil', 404)

    @property
    def ad(self) -> str:
        return self.kök.name or str(self.kök)

    # ── Yolun yoxlanması ──────────────────────────────────────────────

    def yol(self, nisbi: str, kök_ola_bilər: bool = False) -> Path:
        """Nisbi yolu yoxlayıb mütləq yola çevirir."""
        if not isinstance(nisbi, str):
            raise YolXətası("yol mətn olmalıdır")
        if "\x00" in nisbi:
            raise YolXətası("yolda NUL simvolu var", 403)
        təmiz = nisbi.replace("\\", "/").strip()
        p = PurePosixPath(təmiz)
        if (p.is_absolute() or təmiz.startswith("/")
                or (len(təmiz) > 1 and təmiz[1] == ":")):
            raise YolXətası("mütləq yol qəbul edilmir", 403)
        if ".." in p.parts:
            raise YolXətası("`..` ilə layihədən kənara çıxmaq olmaz", 403)
        hissələr = [h for h in p.parts if h not in ("", ".")]
        if not hissələr and not kök_ola_bilər:
            raise YolXətası("fayl adı lazımdır")
        tam = self.kök.joinpath(*hissələr).resolve()
        if not tam.is_relative_to(self.kök):
            raise YolXətası("yol layihə qovluğundan kənardadır", 403)
        return tam

    def nisbi(self, p: Path) -> str:
        return p.resolve().relative_to(self.kök).as_posix()

    # ── Ağac ──────────────────────────────────────────────────────────

    def ağac(self) -> dict:
        say = [0]

        def gəz(q: Path) -> list[dict]:
            try:
                elementlər = sorted(
                    q.iterdir(),
                    key=lambda e: (not e.is_dir(), e.name.lower()))
            except OSError:
                return []
            nəticə: list[dict] = []
            for e in elementlər:
                if say[0] >= MAKS_ELEMENT:
                    break
                if e.name in GİZLİ_QOVLUQLAR or e.name.startswith("."):
                    continue
                try:
                    if not e.resolve().is_relative_to(self.kök):
                        continue          # kənara aparan simvolik keçid
                except OSError:
                    continue
                say[0] += 1
                if e.is_dir():
                    nəticə.append({"ad": e.name, "yol": self.nisbi(e),
                                   "növ": "qovluq", "uşaqlar": gəz(e)})
                else:
                    nəticə.append({"ad": e.name, "yol": self.nisbi(e),
                                   "növ": "fayl"})
            return nəticə

        return {"ad": self.ad, "yol": "", "növ": "qovluq",
                "uşaqlar": gəz(self.kök), "kəsilib": say[0] >= MAKS_ELEMENT}

    # ── Fayl əməliyyatları ────────────────────────────────────────────

    def oxu(self, nisbi: str) -> str:
        p = self.yol(nisbi)
        if not p.is_file():
            raise YolXətası(f'"{nisbi}" faylı tapılmadı', 404)
        if p.stat().st_size > MAKS_FAYL:
            raise YolXətası("fayl redaktor üçün çox böyükdür (2 MB+)", 413)
        xam = p.read_bytes()
        try:
            mətn = xam.decode("utf-8")
        except UnicodeDecodeError:
            raise YolXətası(
                "fayl UTF-8 deyil (ALQ-L001) — ikili fayl ola bilər", 415)
        if mətn.startswith("﻿"):
            mətn = mətn[1:]
        return mətn.replace("\r\n", "\n").replace("\r", "\n")

    def yaz(self, nisbi: str, mətn: str) -> None:
        if not isinstance(mətn, str):
            raise YolXətası("mətn lazımdır")
        p = self.yol(nisbi)
        if p.is_dir():
            raise YolXətası(f'"{nisbi}" qovluqdur', 409)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Atomar yazı: yarımçıq fayl qalmasın. Ad hər yazıda unikaldır —
        # eyni anda iki saxlama bir-birinin müvəqqəti faylını aparmasın
        müvəqqəti = p.with_name(f".{p.name}.{secrets.token_hex(4)}.yazı")
        try:
            müvəqqəti.write_bytes(mətn.encode("utf-8"))
            os.replace(müvəqqəti, p)
        finally:
            if müvəqqəti.exists():
                müvəqqəti.unlink()

    def yarat(self, nisbi: str, növ: str = "fayl", mətn: str = "") -> str:
        p = self.yol(nisbi)
        if p.exists():
            raise YolXətası(f'"{nisbi}" artıq mövcuddur', 409)
        if növ == "qovluq":
            p.mkdir(parents=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(mətn.encode("utf-8"))
        return self.nisbi(p)

    def adını_dəyiş(self, nisbi: str, yeni: str) -> str:
        p = self.yol(nisbi)
        h = self.yol(yeni)
        if not p.exists():
            raise YolXətası(f'"{nisbi}" tapılmadı', 404)
        if h.exists():
            raise YolXətası(f'"{yeni}" artıq mövcuddur', 409)
        h.parent.mkdir(parents=True, exist_ok=True)
        p.rename(h)
        return self.nisbi(h)

    def sil(self, nisbi: str) -> None:
        p = self.yol(nisbi)
        if p == self.kök:
            raise YolXətası("layihənin kökü silinə bilməz", 403)
        # Simvolik keçid silinəndə hədəfinə yox, özünə toxunulur
        xam = self.kök.joinpath(*[
            h for h in PurePosixPath(nisbi.replace("\\", "/")).parts
            if h not in ("", ".")])
        if xam.is_symlink():
            xam.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
        else:
            raise YolXətası(f'"{nisbi}" tapılmadı', 404)
