import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const cases = [
  {name:"phone", width:375, height:812},
  {name:"tablet", width:768, height:1024},
  {name:"desktop", width:1366, height:768},
];

const browser = await chromium.launch({headless:true});
for (const c of cases) {
  const page = await browser.newPage({viewport:{width:c.width,height:c.height}});
  await page.addInitScript(() => {
    class FakeSpeechRecognition {
      start(){
        setTimeout(()=>this.onstart?.(),5);
        setTimeout(()=>this.onresult?.({results:[[{transcript:"trois quarts"}]]}),15);
        setTimeout(()=>this.onend?.(),30);
      }
      stop(){ this.onend?.(); }
    }
    window.SpeechRecognition = FakeSpeechRecognition;
  });
  await page.goto("http://127.0.0.1:4173/?demo=1",{waitUntil:"networkidle"});
  await page.locator('button[data-panel="mika"]').click();
  const mic=page.locator("#micButton");
  await mic.waitFor({state:"visible"});
  assert.equal(await mic.isEnabled(),true,`${c.name}: micro disabled`);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert.ok(overflow<=1,`${c.name}: horizontal overflow ${overflow}px`);
  assert.equal(await page.locator("#exerciseContext").isVisible(),true,`${c.name}: exercise context hidden`);
  await mic.click();
  await page.waitForFunction(()=>document.querySelector("#chatInput")?.value.includes("trois quarts"));
  assert.match(await page.locator("#chatInput").inputValue(),/trois quarts/);
  console.log(`PASS ${c.name} ${c.width}x${c.height}: micro + dictée + no-overflow`);
  await page.close();
}
await browser.close();
