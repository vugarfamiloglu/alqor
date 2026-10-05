# Alqor — İnkişaf Mühiti

> Mərhələ 7–9 (native binar, desktop, IDE) üçün lazım olan alətlərin
> vəziyyəti. Son yenilənmə: 5 oktyabr 2026

---

## Hazır olan

| Alət | Versiya | Qeyd |
|---|---|---|
| **Python** | 3.12.7 | Etalon implementasiya işləyir |
| **Rust** | 1.99.0 | `%USERPROFILE%\.cargo\bin` (PATH-a əlavə edilməyib) |
| **Cargo** | 1.99.0 | |
| **Zig** | 0.16.0 | Python `ziglang` paketi ilə — cross-linker |
| **Node** | 22 | Gələcək JS backend üçün |
| **git / gh** | 2.55 / 2.97 | |

### Rust hədəfləri

| Hədəf | Qurulur? | Linker |
|---|:---:|---|
| `x86_64-pc-windows-gnu` | ✅ | daxili (rustup ilə gəlir) |
| `wasm32-unknown-unknown` | ✅ | linker lazım deyil |
| `x86_64-unknown-linux-gnu` | ✅ | **Zig** (`alqor-linux-cc.cmd`) |
| `x86_64-unknown-linux-musl` | ⬜ | `cargo-zigbuild` lazımdır |
| `aarch64-unknown-linux-gnu` | ⬜ | `cargo-zigbuild` lazımdır |

**Təsdiqlənmiş:** Windows-dan həqiqi Linux ELF binarı qurulur —
WSL olmadan.

```
target/x86_64-unknown-linux-gnu/debug/sinaq:
  ELF 64-bit LSB pie executable, x86-64, dynamically linked,
  interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux
```

---

## PATH quraşdırması (bir dəfəlik)

Rust `--no-modify-path` ilə quraşdırılıb — qlobal PATH-a toxunulmayıb.
Daimi etmək üçün **PowerShell**-də:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:USERPROFILE\.cargo\bin", "User")
```

Və ya hər seansda (Git Bash):

```bash
export PATH="$USERPROFILE/.cargo/bin:$PATH"
```

---

## Zig cross-linker

Zig Python paketi kimi quraşdırılıb (admin tələb etmir):

```bash
python -m pip install ziglang
python -m ziglang version      # 0.16.0
```

`~/.cargo/bin/` qovluğunda üç sarğı skript var:

| Fayl | Hədəf |
|---|---|
| `alqor-linux-cc.cmd` | `x86_64-linux-gnu.2.31` |
| `alqor-musl-cc.cmd` | `x86_64-linux-musl` |
| `alqor-arm64-cc.cmd` | `aarch64-linux-gnu.2.31` |

Layihənin `.cargo/config.toml` faylında:

```toml
[target.x86_64-unknown-linux-gnu]
linker = "alqor-linux-cc.cmd"
[target.x86_64-unknown-linux-musl]
linker = "alqor-musl-cc.cmd"
[target.aarch64-unknown-linux-gnu]
linker = "alqor-arm64-cc.cmd"
```

Qurma:

```bash
cargo build --release --target x86_64-unknown-linux-gnu
```

### musl və ARM64 üçün qalan iş

`rustc` zig-in qəbul etmədiyi bayraqlar ötürür
(`-Wl,--fix-cortex-a53-843419`, `crtbeginS.o`, `-static-pie`).
`cargo-zigbuild` məhz bu bayraqları tərcümə edir:

```bash
cargo install cargo-zigbuild
cargo zigbuild --release --target x86_64-unknown-linux-musl
```

> Bu sessiyada `cargo install cargo-zigbuild` uğursuz oldu (kompilyasiya
> xətası). glibc x86_64 hədəfi işlədiyi üçün bu, bloklayıcı deyil —
> `.deb` paketləri üçün əsas hədəf odur.

---

## ⚠ WSL — SİZİN QƏRARINIZ LAZIMDIR

WSL **quraşdırılmayıb**. Vəziyyət:

| | |
|---|---|
| Administrator hüququ | ✅ var |
| Aparat virtualizasiyası | ✅ var |
| `Microsoft-Windows-Subsystem-Linux` | ⬜ **söndürülüb** |
| `VirtualMachinePlatform` | ⬜ **söndürülüb** |

Windows xüsusiyyətlərini aktivləşdirmək **sistem parametrlərinin
dəyişdirilməsidir** və **kompüterin yenidən başladılmasını** tələb edir —
ona görə bunu özüm etmədim. Siz icra edin.

### Addım 1 — Xüsusiyyətləri aktivləşdir (PowerShell, administrator)

```powershell
wsl --install --no-distribution
```

Və ya əl ilə:

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

### Addım 2 — Kompüteri yenidən başladın

### Addım 3 — Ubuntu quraşdır

```powershell
wsl --install -d Ubuntu
```

### Addım 4 — Linux tərəfində alətləri qur

```bash
sudo apt update
sudo apt install -y build-essential pkg-config libwebkit2gtk-4.1-dev \
                    libgtk-3-dev libayatana-appindicator3-dev \
                    librsvg2-dev patchelf python3
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### WSL nəyi açır?

| Mərhələ | WSL olmadan | WSL ilə |
|---|---|---|
| 7. ELF binar | ✅ Zig ilə qurulur, **test edilmir** | ✅ qurulur və test edilir |
| 7. `.deb` / `.AppImage` | ⚠ qurula bilər, yoxlanmır | ✅ tam |
| 8. Desktop (WebKitGTK) | ✖ GTK başlıq faylları yoxdur | ✅ |
| 9. Alqor Studio (Tauri) | ✖ Linux qurulması mümkün deyil | ✅ |
| 6. Veb (JS/WASM) | ✅ tam işləyir | ✅ |

**Yəni:** veb hədəfi və WASM WSL olmadan tam işləyir. Desktop və IDE
Linux tərəfi üçün WSL məcburidir.

---

## Alternativ: Docker

WSL istəmirsinizsə, Docker Desktop da Linux mühiti verir (o da
`VirtualMachinePlatform` tələb edir):

```bash
docker run --rm -v "$PWD":/layihe -w /layihe rust:1.99 \
  cargo build --release
```

Bu, qurmaq və test etmək üçün kifayətdir, amma GUI (WebKitGTK pəncərəsi)
göstərmək üçün əlavə X11/Wayland ötürülməsi lazımdır.

---

## Yoxlama əmrləri

```bash
export PATH="$USERPROFILE/.cargo/bin:$PATH"

rustc --version
cargo --version
rustup target list --installed
python -m ziglang version

# Linux binarı qurma sınağı
cd /tmp && cargo new sinaq && cd sinaq
mkdir -p .cargo && printf '[target.x86_64-unknown-linux-gnu]\nlinker = "alqor-linux-cc.cmd"\n' > .cargo/config.toml
cargo build --target x86_64-unknown-linux-gnu
file target/x86_64-unknown-linux-gnu/debug/sinaq
```
