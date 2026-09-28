import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

let calls = [];
await page.route("**/api/v1/**", async (route) => {
  const req = route.request();
  const url = new URL(req.url());
  const path = url.pathname.replace("/api/v1", "");
  const auth = req.headers()["authorization"] || "";
  calls.push({ path, method: req.method(), auth, query: Object.fromEntries(url.searchParams.entries()) });

  if (path === "/comptes/connexion" && req.method() === "POST") {
    const body = JSON.parse(req.postData() || "{}");
    assert.equal(body.email, "mike.test@example.fr");
    assert.equal(body.mot_de_passe, "motdepasse-test");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        token: "account-token",
        compte: { id: 1, email: body.email, prenom: "Mike", role: "parent", statut_abonnement: "actif", email_verifie: true },
      }),
    });
  }

  if (path === "/auth/eleve/jeton" && req.method() === "POST") {
    assert.equal(auth, "Bearer account-token");
    const body = JSON.parse(req.postData() || "{}");
    assert.equal(body.student_pseudo_id, "Test26Mika");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "student-token", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 }),
    });
  }

  if (path === "/parcours/prochaine-etape" && req.method() === "GET") {
    assert.equal(auth, "Bearer student-token");
    assert.equal(url.searchParams.get("student_id"), "Test26Mika");
    assert.equal(url.searchParams.get("level"), "5e");
    if (url.searchParams.get("subject") === "physique") {
      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "contenu_indisponible" }),
      });
    }
    assert.equal(url.searchParams.get("subject"), "maths");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        exercice_id: "exo-maths-algebre-1",
        niveau: "5e",
        competence: "equations_1er_degre",
        consigne: "Résous : x + 4 = 7",
      }),
    });
  }

  if (path === "/mika/session/start" && req.method() === "POST") {
    assert.equal(auth, "Bearer student-token");
    const body = JSON.parse(req.postData() || "{}");
    assert.equal(body.student_pseudo_id, "Test26Mika");
    assert.equal(body.exercice_id, "exo-maths-algebre-1");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tutorat_id: "tut-1",
        version: 1,
        etat: { messages: ["On commence ensemble."], attend_comprehension: false, termine: false },
        reponse: { message: "On commence ensemble." },
      }),
    });
  }

  return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "test_route_inconnue" }) });
});

await page.goto("http://127.0.0.1:4173/", { waitUntil: "networkidle" });
await page.locator("#accountEmail").fill("mike.test@example.fr");
await page.locator("#accountPassword").fill("motdepasse-test");
await page.locator("#studentCode").fill("Test26Mika");
await page.locator("#studentLevel").selectOption("5e");
await page.getByRole("button", { name: "Se connecter et commencer" }).click();

await page.waitForFunction(() => !document.querySelector("#dashboardView")?.hidden);
await page.waitForFunction(() => document.querySelector("#exerciseStatement")?.textContent.includes("x + 4 = 7"));
assert.equal(await page.locator("#loginView").isVisible(), false);
assert.equal(await page.locator("#dashboardView").isVisible(), true);
assert.match(await page.locator("#exerciseStatement").innerText(), /x \+ 4 = 7/);
assert.equal(await page.locator("#micButton").isEnabled(), true);

const storage = await page.evaluate(() => ({
  account: sessionStorage.getItem("mikamike_account_token"),
  student: sessionStorage.getItem("mikamike_student_token"),
  id: sessionStorage.getItem("mikamike_student_id"),
  level: sessionStorage.getItem("mikamike_student_level"),
}));
assert.equal(storage.account, "account-token");
assert.equal(storage.student, null, "le jeton élève ne doit jamais être persisté");
assert.equal(storage.id, "Test26Mika");
assert.equal(storage.level, "5e");

await page.locator('button[data-panel="subjects"]').click();
await page.locator('#panel-subjects .subject-card[data-subject="Mathématiques"]').click();
await page.waitForFunction(() => document.querySelector("#panel-mika")?.classList.contains("active-panel"));
assert.ok(calls.filter(x => x.path === "/parcours/prochaine-etape" && x.query.subject === "maths").length >= 2);

await page.locator('button[data-panel="subjects"]').click();
await page.locator('#panel-subjects .subject-card[data-subject="Physique"]').click();
await page.waitForFunction(() => document.querySelector("#catalogNotice")?.textContent.includes("aucun exercice validé"));
assert.match(await page.locator("#catalogNotice").innerText(), /aucun exercice validé/i);

const accountCall = calls.find(x => x.path === "/comptes/connexion");
const studentCall = calls.find(x => x.path === "/auth/eleve/jeton");
assert.ok(accountCall);
assert.equal(accountCall.auth, "");
assert.ok(studentCall);
assert.equal(studentCall.auth, "Bearer account-token");

const shortcut = await browser.newPage({ viewport: { width: 375, height: 812 } });
await shortcut.goto("http://127.0.0.1:4173/?demo=1&open=mika", { waitUntil: "networkidle" });
assert.equal(await shortcut.locator("#panel-mika").isVisible(), true, "?open=mika doit ouvrir Mika");
await shortcut.close();

console.log("PASS functional-auth: compte -> élève -> parcours filtré -> Mika + open=mika");
await browser.close();
