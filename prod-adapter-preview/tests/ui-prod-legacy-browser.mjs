import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const browser = await chromium.launch({headless:true});
const context = await browser.newContext({viewport:{width:390,height:844}});
const page = await context.newPage();
const calls=[];

await page.route("**/api/**", async route => {
  const req=route.request();
  const url=new URL(req.url());
  let body=null; try{body=req.postDataJSON();}catch{}
  calls.push({path:url.pathname,method:req.method(),body,auth:req.headers()["authorization"]||""});

  if(url.pathname==="/api/login"){
    assert.equal(req.method(),"POST");
    assert.equal(body.code,"Test26Mika");
    return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({
      ok:true,eleve:"Test",niveau:"college",matieres:["maths","physique"],upload:true,token:"legacy-token"
    })});
  }
  if(url.pathname==="/api/chat"){
    assert.equal(req.method(),"POST");
    assert.equal(req.headers()["authorization"],"Bearer legacy-token");
    assert.equal(body.code,"Test26Mika");
    assert.equal(body.matiere,"physique");
    assert.ok(Array.isArray(body.messages));
    assert.equal(body.messages.at(-1).content,"Explique la vitesse");
    return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({
      reply:"La vitesse relie une distance et une durée. On commence par identifier les unités."
    })});
  }
  return route.fulfill({status:404,contentType:"application/json",body:JSON.stringify({detail:"unexpected"})});
});

await page.addInitScript(()=>{
  Object.defineProperty(navigator,"mediaDevices",{configurable:true,value:{getUserMedia:async()=>({getTracks:()=>[{stop(){}}]})}});
  class FakeSpeechRecognition{start(){this.onstart?.();}stop(){this.onend?.();}}
  window.SpeechRecognition=FakeSpeechRecognition;
});

await page.goto("http://127.0.0.1:4173/",{waitUntil:"networkidle"});
await page.locator("#studentCode").fill("Test26Mika");
await page.getByRole("button",{name:"Commencer avec Mika"}).click();
await page.locator("#dashboardView").waitFor({state:"visible"});
assert.match(await page.locator("#studentName").innerText(),/Test/);

const subjectsPanel=page.locator("#panel-subjects");
const maths=subjectsPanel.locator('.subject-card[data-subject="Mathématiques"]');
const physics=subjectsPanel.locator('.subject-card[data-subject="Physique"]');
const svt=subjectsPanel.locator('.subject-card[data-subject="SVT"]');
const chemistry=subjectsPanel.locator('.subject-card[data-subject="Chimie"]');
assert.equal(await maths.isEnabled(),true);
assert.equal(await physics.isEnabled(),true);
assert.equal(await svt.isDisabled(),true);
assert.equal(await chemistry.isDisabled(),true);

await page.locator('button[data-panel="subjects"]').click();
await physics.click();
await page.locator("#panel-mika").waitFor({state:"visible"});
await page.locator("#chatInput").fill("Explique la vitesse");
await page.locator("#chatSubmit").click();
await page.waitForFunction(()=>document.querySelector("#chatMessages")?.textContent?.includes("distance et une durée"));
assert.match(await page.locator("#chatMessages").innerText(),/distance et une durée/);

const storage=await page.evaluate(()=>({
  code:localStorage.getItem("mika_code"),
  token:sessionStorage.getItem("mika_token"),
  forbidden:sessionStorage.getItem("mikamike_student_token")
}));
assert.equal(storage.code,"Test26Mika");
assert.equal(storage.token,"legacy-token");
assert.equal(storage.forbidden,null);

assert.ok(calls.some(x=>x.path==="/api/login"));
assert.ok(calls.some(x=>x.path==="/api/chat" && x.body?.matiere==="physique"));
assert.equal(calls.some(x=>x.path.startsWith("/api/v1")),false);

await page.goto("http://127.0.0.1:4173/?open=mika",{waitUntil:"networkidle"});
await page.locator("#panel-mika").waitFor({state:"visible"});
assert.equal(await page.locator("#panel-mika").isVisible(),true);

console.log("PASS prod-adapter: Test26Mika -> /api/login -> matière -> /api/chat -> auto-login/open=mika");
await browser.close();
