import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:375,height:812}});
await page.addInitScript(() => {
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
await page.getByRole("button",{name:"Mika",exact:true}).click();
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
console.log("PASS browser 375px: micro + dictée + énoncé + PWA");
await browser.close();
