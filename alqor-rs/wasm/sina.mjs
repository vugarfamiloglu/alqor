// WebAssembly paketini yoxlayır: verilən `.alq` fayllarını (və ya `=====`
// ilə ayrılmış parçaları) icra edib JSON nəticələri çap edir.
//
//   node wasm/sina.mjs fayl.alq [giriş-sətri…]
//   node wasm/sina.mjs --parçalar parçalar.alq     (hər parça üçün bir JSON sətri)
import { readFileSync } from "node:fs";
import { yüklə } from "./alqor.js";

const alqor = await yüklə(new URL("./alqor.wasm", import.meta.url));
const a = process.argv.slice(2);
if (a[0] === "--parçalar") {
  const parçalar = readFileSync(a[1], "utf8").split("=====\n");
  for (const p of parçalar) {
    console.log(JSON.stringify(alqor.işlət(p, ["bir", "iki"])));
  }
} else {
  console.log(JSON.stringify(alqor.işlət(readFileSync(a[0], "utf8"), a.slice(1))));
}
