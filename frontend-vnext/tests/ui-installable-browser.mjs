import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:375,height:812}});
const runtimeErrors=[];
page.on("pageerror",e=>runtimeErrors.push(String(e)));
page.on("console",m=>{if(m.type()==="error")runtimeErrors.push(m.text());});
await page.addInitScript(() => {
  window.__microPermissionRequested = false;
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: async () => {
        window.__microPermissionRequested = true;
        return { getTracks: () => [{ stop() {} }] };
      },
    },
  });
  class FakeSpeechRecognition {
    constructor(){this.lang="";this.interimResults=false;this.continuous=false;this.maxAlternatives=1;}
    start(){
      setTimeout(()=>this.onstart?.(),10);
      setTimeout(()=>this.onresult?.({results:[[{transcript:"trois quarts"}]]}),25);
      setTimeout(()=>this.onend?.(),45);
    }
    stop(){this.onend?.();}
  }
  window.SpeechRecognition=FakeSpeechRecognition;
});
await page.goto("http://127.0.0.1:4173/?demo=1",{waitUntil:"networkidle"});
const micCheck=page.getByRole("button",{name:/Vérifier le micro|Micro prêt/});
await micCheck.click();
await page.waitForFunction(()=>window.__microPermissionRequested===true);
await page.waitForFunction(()=>document.querySelector("#micCheckButton")?.textContent.includes("Micro prêt"));
if(!(await page.locator("#installButton").isVisible())){
  console.error("DIAG install hidden",await page.evaluate(()=>({
    hidden:document.querySelector("#installButton")?.hidden,
    native:window.MIKAMIKE_NATIVE,
    standalone:matchMedia("(display-mode: standalone)").matches,
    dashboardHidden:document.querySelector("#dashboardView")?.hidden
  })),runtimeErrors);
}
assert.equal(await page.locator("#installButton").isVisible(),true);
await page.locator("#installButton").click();
assert.equal(await page.locator("#installDialog").getAttribute("open")!==null,true);
await page.locator("#installDialogClose").click();
await page.locator('button[data-panel="mika"]').click();
const mic=page.getByRole("button",{name:"Activer la dictée vocale"});
await mic.waitFor({state:"visible"});
assert.equal(await mic.isEnabled(),true);
await mic.click();
await page.waitForFunction(()=>document.querySelector("#chatInput")?.value.includes("trois quarts"));
assert.match(await page.locator("#chatInput").inputValue(),/trois quarts/);
assert.equal(await page.locator("#exerciseContext").isVisible(),true);
assert.match(await page.locator("#exerciseStatement").innerText(),/3\/4/);
const manifestHref=await page.locator('link[rel="manifest"]').getAttribute("href");
assert.equal(manifestHref,"./manifest.webmanifest");
const manifestResponse=await page.request.get("http://127.0.0.1:4173/manifest.webmanifest");
assert.equal(manifestResponse.ok(),true);
const manifest=await manifestResponse.json();
assert.equal(manifest.display,"standalone");
assert.ok(manifest.icons.length>=2);
console.log("PASS browser 375px: permission micro + dictée + installation + énoncé + PWA");
await browser.close();
