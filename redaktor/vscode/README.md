# Alqor — VS Code genişlənməsi

Alqor dili üçün tam redaktor dəstəyi:

- **Sintaksis rəngləmə** — açar sözlər (ASCII formaları da: `eger`, `her`),
  mətn interpolyasiyası `"{ad}"`, xam mətnlər `x"…"`, annotasiyalar
- **Xətalar yazdıqca** — leksik, sintaksis və tip xətaları, Azərbaycan dilində
- **Tamamlama** — `vidjet.`, `s.` kimi üzvlər; açar sözlər, şablonlar
- **Hover** — tip, imza və `///` sənəd şərhi
- **Təyinata keçid** (F12), **istinadlar** (Shift+F12), **ad dəyişmə** (F2) —
  bütün layihə üzrə (`gətir "./x.alq"`)
- **İş sahəsi simvolları** (Ctrl+T)
- **Kod linzaları** — "N istinad", `@sınaq` funksiyaları üstündə "▶ Sına"
- **Semantik rənglər** — sinif, funksiya, metod, xassə, parametr, sabit
- **Sazlama** (F5) — dayanma nöqtələri (şərtli də), addım-addım icra,
  çağırış yığını, dəyişənlər, izləmə ifadələri (`alqor dap`)
- **Sənəd sxemi** (Ctrl+Shift+O)
- **Formatlama** (Shift+Alt+F) — `alqorfmt`
- **Sürətli düzəlişlər** (Ctrl+.) — `eger` → `əgər`, "bəlkə: uzunluq"

## Quraşdırma

1. Alqor-u quraşdırın və `alqor versiya` əmrinin işlədiyini yoxlayın
   (bax: `beledci/00-BASLANGIC.md`).
2. Genişlənməni qurun:
   ```bash
   cd redaktor/vscode
   npm install
   npx @vscode/vsce package          # alqor-2.4.0.vsix
   code --install-extension alqor-2.4.0.vsix
   ```
3. `.alq` faylını açın.

`alqor` PATH-da deyilsə: **Parametrlər → Alqor → Server Əmri** —
məsələn `C:\alqor\alqor.cmd` və ya `python3 /yol/alqorc/alqorc.py`.

## Digər redaktorlar

Dil serveri standart LSP-dir: `alqor ls --stdio`.

**Neovim** (0.10+):
```lua
vim.filetype.add({ extension = { alqor = "alqor" } })
vim.api.nvim_create_autocmd("FileType", {
  pattern = "alqor",
  callback = function()
    vim.lsp.start({ name = "alqorls", cmd = { "alqor", "ls", "--stdio" } })
  end,
})
```

**Helix** (`languages.toml`):
```toml
[language-server.alqorls]
command = "alqor"
args = ["ls", "--stdio"]

[[language]]
name = "alqor"
scope = "source.alq"
file-types = ["alqor"]
comment-token = "//"
indent = { tab-width = 4, unit = "    " }
language-servers = ["alqorls"]
```

Qrammatika və `language-configuration.json` açar söz siyahısından
yaradılır: `cd alqorc && python -m alqor.qrammatika --yaz`.
