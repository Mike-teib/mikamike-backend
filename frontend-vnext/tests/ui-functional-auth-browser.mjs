import { chromium } from "playwright";
import { strict as assert } from "node:assert";

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();

const calls = [];
await page.route("**/api/v1/**", async (route) => {
  const req = route.request();
  const url = new URL(req.url());
  const path = url.pathname;
  const auth = req.headers()["authorization"] || "";
  let body = null;
  try { body = req.postDataJSON(); } catch {}

  calls.push({ path, method: req.method(), auth, body, search: url.search });

  if (path.endsWith("/comptes/connexion")) {
    assert.equal(req.method(), "POST");
    assert.equal(body.email, "parent@example.fr");
    assert.equal(body.mot_de_passe, "motdepasse-test");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        token: "account-token",
        compte: { id: 7, email: "parent@example.fr", prenom: "Parent", role: "parent", statut_abonnement: "actif", email_verifie: true }
      })
    });
  }

  if (path.endsWith("/auth/eleve/jeton")) {
    assert.equal(auth, "Bearer account-token");
    assert.equal(body.student_pseudo_id, "Test26Mika");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "student-token", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 })
    });
  }

  if (path.endsWith("/parcours/prochaine-etape")) {
    assert.equal(auth, "Bearer student-token");
    assert.equal(url.searchParams.get("student_id"), "Test26Mika");
    assert.equal(url.searchParams.get("level"), "6e");
    assert.equal(url.searchParams.get("subject"), "maths");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        exercice_id: "exo-maths-priorites-1",
        niveau: "6e",
        competence: "priorites_operatoires",
        consigne: "Calcule : 2 + 3 × 4"
      })
    });
  }

  if (path.endsWith("/mika/session/start")) {
    assert.equal(auth, "Bearer student-token");
    assert.equal(body.student_pseudo_id, "Test26Mika");
    assert.equal(body.exercice_id, "exo-maths-priorites-1");
    return route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        tutorat_id: "0123456789abcdef0123456789abcdef",
        version: 1,
        etat: { messages: ["Commence par la multiplication."], attend_comprehension: false, termine: false },
        reponse: { message: "Commence par la multiplication." }
      })
    });
  }

  if (path.endsWith("/mika/session/answer")) {
    assert.equal(auth, "Bearer student-token");
    assert.equal(body.reponse, "14");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tutorat_id: "0123456789abcdef0123456789abcdef",
        version: 2,
        etat: { messages: ["Bravo !"], attend_comprehension: false, termine: true },
        reponse: { message: "Bravo !" }
      })
    });
  }

  if (path.includes("/parents/dashboard/")) {
    assert.equal(auth, "Bearer account-token");
    assert.ok(path.endsWith("/parents/dashboard/Test26Mika"));
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        pseudo_id: "Test26Mika",
        statistiques_pedagogiques: {
          exercices_tentes: 4,
          exercices_reussis: 3,
          taux_reussite: 0.75,
          niveau_actuel: "6e",
          competences: {
            priorites_operatoires: { tentatives: 2, reussites: 2, etat: "MAITRISE" }
          }
        }
      })
    });
  }

  return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "audit_route_inconnue" }) });
});

await page.addInitScript(() => {
  window.__microPermissionRequested = false;
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: async () => {
        window.__microPermissionRequested = true;
        return { getTracks: () => [{ stop() {} }] };
      }
    }
  });
  class FakeSpeechRecognition {
    start(){ setTimeout(() => this.onstart?.(), 5); setTimeout(() => this.onend?.(), 15); }
    stop(){ this.onend?.(); }
  }
  window.SpeechRecognition = FakeSpeechRecognition;
});

await page.goto("http://127.0.0.1:4173/", { waitUntil: "networkidle" });
await page.locator("#accountEmail").fill("parent@example.fr");
await page.locator("#accountPassword").fill("motdepasse-test");
await page.locator("#studentCode").fill("Test26Mika");
await page.getByRole("button", { name: "Se connecter et commencer" }).click();

await page.locator("#dashboardView").waitFor({ state: "visible" });
await page.waitForFunction(() => document.querySelector("#exerciseStatement")?.textContent?.includes("2 + 3 × 4"));
assert.equal(await page.locator("#studentLevel").inputValue(), "6e");
await page.locator('button[data-panel="mika"]').click();
await page.locator("#exerciseContext").waitFor({ state: "visible" });
assert.match(await page.locator("#exerciseStatement").innerText(), /2 \+ 3 × 4/);

const storage = await page.evaluate(() => ({
  accountToken: sessionStorage.getItem("mikamike_account_token"),
  studentId: sessionStorage.getItem("mikamike_student_id"),
  forbiddenStudentToken: sessionStorage.getItem("mikamike_student_token")
}));
assert.equal(storage.accountToken, "account-token");
assert.equal(storage.studentId, "Test26Mika");
assert.equal(storage.forbiddenStudentToken, null);

await page.locator('button[data-panel="subjects"]').click();
const maths = page.locator('#panel-subjects .subject-card[data-api-subject="maths"]');
await maths.click();
await page.locator("#panel-mika").waitFor({ state: "visible" });
assert.match(await page.locator("#catalogNotice").textContent(), /parcours chargé depuis le serveur/);

await page.locator("#chatInput").fill("14");
await page.locator("#chatSubmit").click();
await page.waitForFunction(() => [...document.querySelectorAll("#chatMessages p")].some(p => p.textContent.includes("Bravo")));
assert.match(await page.locator("#chatMessages").innerText(), /Bravo/);

await page.goto("http://127.0.0.1:4173/?open=mika", { waitUntil: "networkidle" });
await page.locator("#panel-mika").waitFor({ state: "visible" });
assert.equal(await page.locator("#panel-mika").isVisible(), true);

await page.goto("http://127.0.0.1:4173/parent.html", { waitUntil: "networkidle" });
await page.locator("#parentEmail").fill("parent@example.fr");
await page.locator("#parentPassword").fill("motdepasse-test");
await page.locator("#parentStudentCode").fill("Test26Mika");
await page.getByRole("button", { name: "Afficher les progrès" }).click();
await page.locator("#parentDashboard").waitFor({ state: "visible" });
assert.equal(await page.locator("#parentSuccess").innerText(), "3 / 4");
assert.equal(await page.locator("#parentRate").innerText(), "75 %");
assert.equal(await page.locator("#parentLevel").innerText(), "6e");
assert.match(await page.locator("#parentCompetences").innerText(), /priorites_operatoires/);

assert.ok(calls.some(c => c.path.endsWith("/comptes/connexion")));
assert.ok(calls.some(c => c.path.endsWith("/auth/eleve/jeton") && c.auth === "Bearer account-token"));
assert.ok(calls.some(c => c.path.endsWith("/parcours/prochaine-etape") && c.search.includes("level=6e") && c.search.includes("subject=maths")));
assert.ok(calls.some(c => c.path.endsWith("/mika/session/start") && c.auth === "Bearer student-token"));
assert.ok(calls.some(c => c.path.includes("/parents/dashboard/") && c.auth === "Bearer account-token"));

console.log("PASS functional-e2e: compte -> élève -> Maths 6e -> Mika -> parent");
await browser.close();
