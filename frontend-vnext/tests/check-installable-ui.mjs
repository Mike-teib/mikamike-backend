import {readFileSync} from "node:fs";import {strict as assert} from "node:assert";
const html=readFileSync(new URL("../index.html",import.meta.url),"utf8");
const app=readFileSync(new URL("../app.js",import.meta.url),"utf8");
const manifest=JSON.parse(readFileSync(new URL("../manifest.webmanifest",import.meta.url),"utf8"));
const sw=readFileSync(new URL("../service-worker.js",import.meta.url),"utf8");
assert.match(html,/id="micButton"/);assert.match(html,/id="micCheckButton"/);assert.match(html,/id="installButton"/);assert.match(html,/id="installDialog"/);assert.match(html,/id="exerciseContext"/);assert.match(html,/native-bridge\.js/);
assert.match(app,/SpeechRecognition/);assert.match(app,/getUserMedia/);assert.match(app,/prepareMicrophone/);assert.match(app,/MikaNativeSpeech/);assert.match(app,/\/api\/login/);assert.match(app,/\/api\/chat/);assert.doesNotMatch(app,/\/api\/v1/);assert.doesNotMatch(app,/\/mika\/session\//);
assert.equal(manifest.display,"standalone");assert.ok(manifest.icons.some(x=>x.sizes==="192x192"));assert.ok(manifest.icons.some(x=>x.sizes==="512x512"));
assert.match(sw,/mikamike-ui-v4-prod-backend-adapter/);console.log("PASS installable-ui: backend OVH prod + micro + PWA");
