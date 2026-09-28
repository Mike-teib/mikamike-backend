
import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const BASE = "https://app.mikamike.fr";
const OUT = "audit-artifacts";
await fs.mkdir(OUT, { recursive: true });

const report = { target: BASE, started_at: new Date().toISOString(), checks: [], console_errors: [], page_errors: [], request_failures: [], notes: [] };
const add = (name,status,detail="",evidence={}) => report.checks.push({name,status,detail,evidence});
const pass = (n,d="",e={}) => add(n,"PASS",d,e);
const fail = (n,d="",e={}) => add(n,"FAIL",d,e);
const warn = (n,d="",e={}) => add(n,"WARN",d,e);

const browser = await chromium.launch({ headless: true });

function wire(page,label) {
  page.on("console", m => { if (m.type()==="error") report.console_errors.push({page:label,text:m.text()}); });
  page.on("pageerror", e => report.page_errors.push({page:label,text:String(e)}));
  page.on("requestfailed", r => report.request_failures.push({page:label,url:r.url(),method:r.method(),failure:r.failure()?.errorText||"unknown"}));
}
async function txt(locator) { try { return (await locator.innerText()).trim(); } catch { return ""; } }

async function assets() {
  const context = await browser.newContext();
  const urls = ["/","/app.js","/native-bridge.js","/styles.css","/manifest.webmanifest","/service-worker.js","/parent.html","/api/health"];
  for (const suffix of urls) {
    const r = await context.request.get(BASE + suffix, { timeout: 30000 });
    if (r.status()===200) pass("HTTP " + suffix,"200"); else fail("HTTP " + suffix,"Statut " + r.status());
  }
  await context.close();
}

async function root() {
  const context = await browser.newContext({ viewport: { width:1440,height:900 } });
  const page = await context.newPage(); wire(page,"root");
  const r = await page.goto(BASE + "/", { waitUntil:"networkidle", timeout:60000 });
  if (r?.status()===200) pass("Accueil HTTP","200"); else fail("Accueil HTTP","Statut " + r?.status());
  if (await page.locator("#loginView").isVisible()) pass("Écran connexion visible"); else fail("Écran connexion visible");
  const code = page.locator("#studentCode");
  const submit = page.locator('#studentLoginForm button[type="submit"]');
  if (await code.isVisible() && await submit.isVisible()) pass("Champs connexion visibles"); else fail("Champs connexion visibles");

  await submit.click();
  const blank = await txt(page.locator("#loginError"));
  if (/Entre ton code élève/i.test(blank)) pass("Validation code vide",blank); else fail("Validation code vide",blank||"Aucun message");

  await code.fill("TEST-AUDIT-INVALID");
  try {
    const wait = page.waitForResponse(x => x.url().includes("/api/v1/auth/eleve/jeton") && x.request().method()==="POST", {timeout:15000});
    await submit.click();
    const ar = await wait;
    const msg = await txt(page.locator("#loginError"));
    if (ar.status()===404) fail("Connexion par simple code élève","Le frontend appelle /api/v1/auth/eleve/jeton mais la production répond 404 : endpoint absent.",{status:ar.status(),message:msg});
    else if ([401,403].includes(ar.status())) fail("Connexion par simple code élève","L'API refuse le code seul (" + ar.status() + "). Message visible: " + (msg||"(vide)"),{status:ar.status(),message:msg});
    else warn("Connexion par simple code élève","Réponse " + ar.status(),{message:msg});
  } catch (e) {
    fail("Appel authentification","Aucune réponse du endpoint d'authentification",{error:String(e)});
  }

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (!overflow) pass("Desktop sans débordement horizontal"); else fail("Desktop sans débordement horizontal");
  await page.screenshot({path:path.join(OUT,"root-desktop.png"),fullPage:true});
  await context.close();
}

async function demo(width,height,label) {
  const context = await browser.newContext({ viewport:{width,height} });
  await context.addInitScript(() => {
    window.__auditMicRequested = false;
    Object.defineProperty(navigator,"mediaDevices",{configurable:true,value:{getUserMedia:async()=>{window.__auditMicRequested=true;return{getTracks:()=>[{stop(){}}]};}}});
    class FakeSpeechRecognition { start(){this.onstart?.();} stop(){this.onend?.();} }
    window.SpeechRecognition = FakeSpeechRecognition;
    window.webkitSpeechRecognition = FakeSpeechRecognition;
  });
  const page = await context.newPage(); wire(page,label);
  const r = await page.goto(BASE + "/?demo=1", {waitUntil:"networkidle",timeout:60000});
  await page.screenshot({path:path.join(OUT,label + "-initial.png"),fullPage:true});
  const imageState = await page.evaluate(() => [...document.images].map(img => ({
    src: img.src,
    complete: img.complete,
    naturalWidth: img.naturalWidth,
    naturalHeight: img.naturalHeight
  })));
  const brokenImages = imageState.filter(x => !x.complete || x.naturalWidth === 0);
  if (brokenImages.length === 0) pass(label + " illustrations chargées", imageState.length + " image(s)");
  else fail(label + " illustrations chargées", brokenImages.length + " image(s) cassée(s)", {brokenImages});
  if (r?.status()===200) pass(label + " démo HTTP","200"); else fail(label + " démo HTTP","Statut " + r?.status());
  if (await page.locator("#dashboardView").isVisible() && !(await page.locator("#loginView").isVisible())) pass(label + " ouverture démo"); else fail(label + " ouverture démo");

  const nav = page.locator(".nav-card");
  const n = await nav.count();
  if (n>=3) pass(label + " navigation présente",n + " onglets"); else fail(label + " navigation présente",n + " onglets");
  for (let i=0;i<n;i++) {
    const b = nav.nth(i); const panel = await b.getAttribute("data-panel"); const name = (await b.innerText()).trim().replace(/\s+/g," ");
    await b.click();
    if (await page.locator("#panel-" + panel).isVisible()) pass(label + " onglet " + name,panel||""); else fail(label + " onglet " + name,"Panneau non visible");
  }

  const mc = page.locator("#micCheckButton");
  if (await mc.isVisible()) {
    await mc.click(); await page.waitForTimeout(100);
    const requested = await page.evaluate(() => window.__auditMicRequested===true);
    const t = await txt(mc);
    if (requested && /Micro prêt/i.test(t)) pass(label + " vérification micro",t); else fail(label + " vérification micro","requested=" + requested + "; bouton=" + t);
  } else fail(label + " vérification micro","Bouton absent");

  const mikaNav = page.locator('.nav-card[data-panel="mika"]');
  if (await mikaNav.count()) await mikaNav.click();
  const mic = page.locator("#micButton");
  if (await mic.isVisible()) {
    const before = await mic.getAttribute("aria-label");
    await mic.click(); await page.waitForTimeout(100);
    const after = await mic.getAttribute("aria-label");
    if (/Arrêter la dictée/i.test(after||"")) pass(label + " bouton Dicter",(before||"") + " -> " + (after||"")); else fail(label + " bouton Dicter",(before||"") + " -> " + (after||""));
    await mic.click().catch(()=>{});
  } else fail(label + " bouton Dicter","Absent");

  const install = page.locator("#installButton");
  if (await install.isVisible()) {
    await install.click();
    const dialog = page.locator("#installDialog");
    if (await dialog.isVisible()) pass(label + " installation",await txt(page.locator("#installDialogText"))); else pass(label + " installation","Prompt natif ou guide non modal");
    await page.locator("#installDialogClose").click().catch(()=>{});
    await page.waitForTimeout(100);
    const dialogOpen = await dialog.evaluate(el => !!el.open).catch(()=>false);
    if (!dialogOpen) pass(label + " dialogue installation fermé"); else fail(label + " dialogue installation fermé","Le dialogue reste ouvert après fermeture");
  } else fail(label + " installation","Bouton absent");

  const subjectsNav = page.locator('.nav-card[data-panel="subjects"]');
  if (await subjectsNav.count()) await subjectsNav.click();
  const subject = page.locator(".subject-card").first();
  if (await subject.count() && await subject.isVisible()) {
    let count=0; const h=req=>{if(req.url().includes("/api/"))count++;}; page.on("request",h);
    await subject.click(); await page.waitForTimeout(700); page.off("request",h);
    const notice = await txt(page.locator("#catalogNotice"));
    if (count===0) fail(label + " sélection matière","Aucune requête/changement de parcours; seul le message change",{notice}); else pass(label + " sélection matière",count + " requête(s) API");
  }

  const visualState = await page.evaluate(() => {
    const card = document.querySelector(".subject-card");
    const panel = document.querySelector("#panel-subjects");
    const dlg = document.querySelector("#installDialog");
    const cs = card ? getComputedStyle(card) : null;
    return {
      subjectVisible: !!card && !!(card.offsetWidth || card.offsetHeight || card.getClientRects().length),
      subjectOpacity: cs?.opacity || null,
      subjectFilter: cs?.filter || null,
      subjectColor: cs?.color || null,
      panelDisplay: panel ? getComputedStyle(panel).display : null,
      panelOpacity: panel ? getComputedStyle(panel).opacity : null,
      panelAnimationPlayStates: panel ? panel.getAnimations().map(a => a.playState) : [],
      dialogOpen: !!dlg?.open
    };
  });
  if (visualState.subjectOpacity === "1" && visualState.subjectFilter === "none" && visualState.panelOpacity === "1" && !visualState.dialogOpen) {
    pass(label + " cartes matières visuellement actives","opacity=1, panelOpacity=1, filter=none");
  } else {
    fail(label + " cartes matières visuellement actives","État visuel inattendu",{visualState});
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (!overflow) pass(label + " aucun débordement horizontal"); else fail(label + " aucun débordement horizontal");
  await page.screenshot({path:path.join(OUT,label + "-final.png"),fullPage:true});
  await context.close();
}

async function parent() {
  const context = await browser.newContext({viewport:{width:1280,height:900}});
  const page = await context.newPage(); wire(page,"parent");
  const r = await page.goto(BASE + "/parent.html",{waitUntil:"networkidle",timeout:60000});
  if (r?.status()===200) pass("Espace parent HTTP","200"); else fail("Espace parent HTTP","Statut " + r?.status());
  if ((await page.title()).toLowerCase().includes("parent")) pass("Espace parent rendu",await page.title()); else warn("Espace parent rendu",await page.title());
  await page.screenshot({path:path.join(OUT,"parent.png"),fullPage:true});
  await context.close();
}

async function shortcut() {
  const context = await browser.newContext({viewport:{width:375,height:812}});
  const page = await context.newPage(); wire(page,"shortcut");
  await page.goto(BASE + "/?demo=1&open=mika",{waitUntil:"networkidle",timeout:60000});
  if (await page.locator("#panel-mika").isVisible()) pass("Raccourci PWA Ouvrir Mika"); else fail("Raccourci PWA Ouvrir Mika","Le paramètre ?open=mika est ignoré");
  await context.close();
}

try {
  await assets();
  await root();
  await demo(375,812,"mobile-375");
  await demo(768,1024,"tablette-768");
  await demo(1440,900,"desktop-1440");
  await parent();
  await shortcut();
} catch (e) {
  report.notes.push("Exception générale: " + String(e));
  fail("Audit interrompu",String(e));
} finally {
  await browser.close();
}

report.summary = {
  pass: report.checks.filter(x=>x.status==="PASS").length,
  fail: report.checks.filter(x=>x.status==="FAIL").length,
  warn: report.checks.filter(x=>x.status==="WARN").length,
  console_errors: report.console_errors.length,
  page_errors: report.page_errors.length,
  request_failures: report.request_failures.length
};
report.finished_at = new Date().toISOString();
await fs.writeFile(path.join(OUT,"report.json"),JSON.stringify(report,null,2)+"\n");
const lines = ["# MikaMike production audit","",
  "PASS: " + report.summary.pass,
  "FAIL: " + report.summary.fail,
  "WARN: " + report.summary.warn,"",
  ...report.checks.map(x=>"- " + x.status + " — " + x.name + (x.detail?": " + x.detail:"")),
  "","Console errors: " + report.summary.console_errors,
  ...report.console_errors.map(x=>"- console[" + x.page + "]: " + x.text),
  "Page errors: " + report.summary.page_errors,
  ...report.page_errors.map(x=>"- page[" + x.page + "]: " + x.text),
  "Request failures: " + report.summary.request_failures,
  ...report.request_failures.map(x=>"- request[" + x.page + "]: " + x.method + " " + x.url + " — " + x.failure)
];
await fs.writeFile(path.join(OUT,"report.md"),lines.join("\n")+"\n");
console.log(lines.join("\n"));
process.exitCode = report.summary.fail>0 ? 1 : 0;
