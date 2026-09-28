import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const browser = await chromium.launch({headless:true});
const page = await browser.newPage({viewport:{width:1024,height:900}});
await page.route("**/api/v1/**", async route => {
  const req=route.request();
  const url=new URL(req.url());
  const path=url.pathname.replace("/api/v1","");
  const auth=req.headers()["authorization"]||"";
  if(path==="/comptes/connexion" && req.method()==="POST"){
    return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({
      token:"parent-account-token",
      compte:{id:7,email:"parent.test@example.fr",prenom:"Parent",role:"parent",statut_abonnement:"actif",email_verifie:true}
    })});
  }
  if(path==="/parents/dashboard/Test26Mika" && req.method()==="GET"){
    assert.equal(auth,"Bearer parent-account-token");
    return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({
      pseudo_id:"Test26Mika",
      statistiques_pedagogiques:{
        exercices_tentes:10,exercices_reussis:7,taux_reussite:0.7,niveau_actuel:"5e",
        competences:{equations_1er_degre:{tentatives:4,reussites:3,etat:"EN_COURS"}}
      }
    })});
  }
  return route.fulfill({status:404,contentType:"application/json",body:JSON.stringify({detail:"test_route_inconnue"})});
});

await page.goto("http://127.0.0.1:4173/parent.html",{waitUntil:"networkidle"});
await page.locator("#parentEmail").fill("parent.test@example.fr");
await page.locator("#parentPassword").fill("motdepasse-test");
await page.locator("#parentStudentCode").fill("Test26Mika");
await page.getByRole("button",{name:"Afficher le suivi"}).click();
await page.waitForFunction(()=>document.querySelector("#parentDashboardTitle")?.textContent.includes("Test26Mika"));
assert.equal(await page.locator("#parentSuccess").innerText(),"7");
assert.equal(await page.locator("#parentAttempts").innerText(),"10");
assert.equal(await page.locator("#parentRate").innerText(),"70%");
assert.equal(await page.locator("#parentLevel").innerText(),"5e");
assert.equal(await page.evaluate(()=>sessionStorage.getItem("mikamike_account_token")),"parent-account-token");
console.log("PASS parent-auth: compte parent -> dashboard élève lié");
await browser.close();
