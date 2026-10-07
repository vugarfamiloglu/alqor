// Alqor — VS Code genişlənməsi.
//
// Rəngləmə TextMate qrammatikasından gəlir; qalan hər şey (xətalar,
// tamamlama, hover, təyinata keçid, istinadlar, ad dəyişmə, formatlama,
// sürətli düzəlişlər, kod linzaları, semantik rənglər, layihə üzrə
// simvollar) `alqor ls --stdio` dil serverindəndir.

const vscode = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let müştəri;

function serverƏmri() {
  const k = vscode.workspace.getConfiguration("alqor");
  const əmr = (k.get("serverƏmri") || "").trim();
  if (əmr) {
    // "python3 /yol/alqorc.py" kimi bir neçə hissəli əmr
    const hissələr = əmr.match(/"[^"]+"|\S+/g).map((h) => h.replace(/^"|"$/g, ""));
    return { command: hissələr[0], args: [...hissələr.slice(1), "ls", "--stdio"] };
  }
  const windows = process.platform === "win32";
  return { command: windows ? "alqor.cmd" : "alqor", args: ["ls", "--stdio"] };
}

async function başlat(context) {
  const { command, args } = serverƏmri();
  const serverSeçimləri = {
    command,
    args,
    transport: TransportKind.stdio,
    options: { shell: process.platform === "win32", env: { ...process.env, PYTHONIOENCODING: "utf-8" } },
  };
  const müştəriSeçimləri = {
    documentSelector: [{ scheme: "file", language: "alqor" }, { scheme: "untitled", language: "alqor" }],
    initializationOptions: {
      tipRejimi: vscode.workspace.getConfiguration("alqor").get("tipRejimi"),
    },
    outputChannelName: "Alqor",
  };
  müştəri = new LanguageClient("alqor", "Alqor dil serveri", serverSeçimləri, müştəriSeçimləri);
  try {
    await müştəri.start();
  } catch (x) {
    vscode.window.showErrorMessage(
      `Alqor dil serveri başlamadı (${command}). Alqor quraşdırılıb və PATH-dadır? ` +
        "Parametrlərdə `alqor.serverƏmri` ilə tam yolu göstərə bilərsiniz."
    );
  }
}

// Kod linzası: "N istinad" — LSP-nin JSON obyektlərini VS Code tiplərinə çeviririk
async function istinadlarıGöstər(uri, mövqe, yerlər) {
  if (!müştəri) return;
  const c = müştəri.protocol2CodeConverter;
  await vscode.commands.executeCommand(
    "editor.action.showReferences",
    c.asUri(uri),
    c.asPosition(mövqe),
    (yerlər || []).map((y) => c.asLocation(y))
  );
}

// Kod linzası: "▶ Sına" — `alqor sına fayl --filtr ad` terminalda
function sına(uri, ad) {
  const fayl = vscode.Uri.parse(uri).fsPath;
  const { command, args } = serverƏmri();
  const əsas = [command, ...args.slice(0, -2)].map((h) => (/\s/.test(h) ? `"${h}"` : h));
  let t = vscode.window.terminals.find((x) => x.name === "Alqor sınaq");
  if (!t) t = vscode.window.createTerminal({ name: "Alqor sınaq", env: { PYTHONIOENCODING: "utf-8" } });
  t.show(true);
  t.sendText(`${əsas.join(" ")} sına "${fayl}" --filtr "${ad.replace(/"/g, '\\"')}"`);
}

async function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("alqor.istinadlarıGöstər", istinadlarıGöstər),
    vscode.commands.registerCommand("alqor.sına", sına),
    vscode.commands.registerCommand("alqor.serveriYenidənBaşlat", async () => {
      if (müştəri) await müştəri.stop();
      await başlat(context);
    })
  );
  await başlat(context);
}

async function deactivate() {
  if (müştəri) await müştəri.stop();
}

module.exports = { activate, deactivate };
