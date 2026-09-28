import { chromium } from "playwright";
import { strict as assert } from "node:assert";
import fs from "node:fs/promises";

const BASE="https://app.mikamike.fr";
await fs.mkdir("audit-artifacts",{recursive:true});
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:375,height:812}});
await context.addInitScript(()=>{
  Object.defineProperty(navigator,"mediaDevices",{configurable:true,value:{getUserMedia:async()=>({getTracks:()=>[{stop(){}}]})}});
  class FakeSpeechRecognition{start(){this.onstart?.();}stop(){this.onend?.();}}
  window.SpeechRecognition=FakeSpeechRecognition;
});
const page=await context.newPage();
const errors=[];
page.on("pageerror",e=>errors.push(String(e)));
page.on("console",m=>{if(m.type()==="error")errors.push(m.text());});

const health=await context.request.get(BASE+"/api/health");
assert.equal(health.status(),200);

await page.goto(BASE+"/",{waitUntil:"networkidle",timeout:60000});
assert.equal(await page.locator("#loginView").isVisible(),true);
assert.equal(await page.locator("#installButton").isVisible(),true);
assert.equal(await page.locator("#micCheckButton").isVisible(),true);

await page.locator("#studentCode").fill("Test26Mika");
await page.getByRole("button",{name:"Commencer avec Mika"}).click();
await page.locator("#dashboardView").waitFor({state:"visible",timeout:20000});
assert.equal(await page.locator("#loginView").isVisible(),false);

await page.locator('button[data-panel="subjects"]').click();
const panel=page.locator("#panel-subjects");
await panel.waitFor({state:"visible"});
for(const subject of ["Mathématiques","Physique","Chimie"]){
  const b=panel.locator('.subject-card[data-subject="'+subject+'"]');
  assert.equal(await b.isEnabled(),true,subject+" doit être actif");
}
assert.equal(await panel.locator('.subject-card[data-subject="SVT"]').isDisabled(),true);

await panel.locator('.subject-card[data-subject="Mathématiques"]').click();
await page.locator("#panel-mika").waitFor({state:"visible"});
assert.equal(await page.locator("#chatInput").isEnabled(),true);
await page.locator("#chatInput").fill("Bonjour Mika, contrôle technique après mise à jour.");
await page.locator("#chatSubmit").click();
await page.waitForFunction(()=>{
  const msgs=[...document.querySelectorAll("#chatMessages .mika-message p")];
  return msgs.length>=2 && !msgs.at(-1).textContent.includes("souci technique");
},{timeout:60000});

const storage=await page.evaluate(()=>({
  code:localStorage.getItem("mika_code"),
  token:sessionStorage.getItem("mika_token")
}));
assert.equal(storage.code,"Test26Mika");
assert.ok(storage.token);

const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1);
assert.equal(overflow,false);
await page.screenshot({path:"audit-artifacts/mobile-375.png",fullPage:true});

await page.goto(BASE+"/?open=mika",{waitUntil:"networkidle",timeout:60000});
await page.locator("#panel-mika").waitFor({state:"visible",timeout:20000});
assert.equal(await page.locator("#panel-mika").isVisible(),true);

await page.locator("#logoutButton").click();
await page.locator("#loginView").waitFor({state:"visible"});
assert.equal(await page.evaluate(()=>localStorage.getItem("mika_code")),null);

assert.deepEqual(errors,[]);
console.log("PASS PROD E2E: health -> Test26Mika -> matières -> chat -> open=mika -> logout");
await browser.close();
