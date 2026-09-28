import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const browser = await chromium.launch({headless:true});
const context = await browser.newContext({viewport:{width:390,height:844}});
const page = await context.newPage();
await page.addInitScript(() => {
  window.MIKAMIKE_API_BASE = "http://127.0.0.1:8000/api/v1";
  Object.defineProperty(navigator,"mediaDevices",{configurable:true,value:{getUserMedia:async()=>({getTracks:()=>[{stop(){}}]})}});
  class FakeSpeechRecognition { start(){this.onstart?.();} stop(){this.onend?.();} }
  window.SpeechRecognition=FakeSpeechRecognition;
});

const apiCalls=[];
page.on("response", response => {
  if(response.url().includes("127.0.0.1:8000/api/v1/")) apiCalls.push({url:response.url(),status:response.status()});
});

await page.goto("http://127.0.0.1:4173/",{waitUntil:"networkidle"});
await page.locator("#accountEmail").fill("parent.e2e@example.com");
await page.locator("#accountPassword").fill("motdepasse-e2e-0001");
await page.locator("#studentCode").fill("Test26Mika");
await page.locator("#studentLevel").selectOption("5e");
await page.getByRole("button",{name:"Se connecter et commencer"}).click();

await page.waitForFunction(()=>!document.querySelector("#dashboardView")?.hidden,{timeout:15000});
await page.waitForFunction(()=>document.querySelector("#exerciseStatement")?.textContent.includes("x + 4 = 7"),{timeout:15000});
assert.match(await page.locator("#exerciseStatement").innerText(),/x \+ 4 = 7/);
await page.locator('button[data-panel="mika"]').click();
await page.waitForFunction(()=>document.querySelector("#chatMessages")?.textContent.includes("Résous") || document.querySelector("#chatMessages")?.textContent.includes("On commence") || document.querySelector("#chatMessages")?.textContent.length>20,{timeout:10000});
assert.equal(await page.locator("#chatInput").isEnabled(),true);

const storage=await page.evaluate(()=>({
  account:sessionStorage.getItem("mikamike_account_token"),
  student:sessionStorage.getItem("mikamike_student_token"),
  id:sessionStorage.getItem("mikamike_student_id"),
  level:sessionStorage.getItem("mikamike_student_level"),
}));
assert.ok(storage.account);
assert.equal(storage.student,null);
assert.equal(storage.id,"Test26Mika");
assert.equal(storage.level,"5e");

await page.locator("#chatInput").fill("3");
await page.locator("#chatSubmit").click();
await page.waitForTimeout(700);
assert.match(await page.locator("#chatMessages").innerText(),/3/);

assert.ok(apiCalls.some(x=>x.url.includes("/comptes/connexion") && x.status===200));
assert.ok(apiCalls.some(x=>x.url.includes("/auth/eleve/jeton") && x.status===200));
assert.ok(apiCalls.some(x=>x.url.includes("/parcours/prochaine-etape") && x.url.includes("level=5e") && x.url.includes("subject=maths") && x.status===200));
assert.ok(apiCalls.some(x=>x.url.includes("/mika/session/start") && [200,201].includes(x.status)));

await page.goto("http://127.0.0.1:4173/parent.html",{waitUntil:"networkidle"});
await page.waitForFunction(()=>document.querySelector("#parentAccountFields")?.hidden===true);
assert.equal(await page.locator("#parentStudentCode").inputValue(),"Test26Mika");
assert.equal(await page.locator("#parentStudentLevel").inputValue(),"5e");
await page.getByRole("button",{name:"Afficher le suivi"}).click();
await page.waitForFunction(()=>document.querySelector("#parentDashboardTitle")?.textContent.includes("Test26Mika"),{timeout:10000});
assert.match(await page.locator("#parentDashboardTitle").innerText(),/Test26Mika/);
assert.ok(apiCalls.some(x=>x.url.includes("/parents/dashboard/Test26Mika") && x.status===200));

console.log("PASS real-backend-e2e: compte réel test -> lien élève -> jeton élève -> parcours -> Mika -> dashboard parent");
await browser.close();
