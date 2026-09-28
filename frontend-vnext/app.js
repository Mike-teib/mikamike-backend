(() => {
  "use strict";

  const API = window.MIKAMIKE_API_BASE || "/api/v1";
  const state = {
    token: sessionStorage.getItem("mikamike_student_token") || "",
    studentId: sessionStorage.getItem("mikamike_student_id") || "",
    demo: new URLSearchParams(location.search).get("demo") === "1",
    tutorat: null,
    nextStep: null,
    listening: false,
    installPrompt: null,
    recognition: null,
    voiceBaseText: "",
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  const loginView = $("#loginView");
  const dashboardView = $("#dashboardView");
  const loginForm = $("#studentLoginForm");
  const studentCode = $("#studentCode");
  const loginError = $("#loginError");
  const logoutButton = $("#logoutButton");
  const networkStatus = $("#networkStatus");
  const catalogNotice = $("#catalogNotice");
  const chatInput = $("#chatInput");
  const chatSubmit = $("#chatSubmit");
  const micButton = $("#micButton");
  const voiceStatus = $("#voiceStatus");
  const installButton = $("#installButton");

  function setNetworkStatus() {
    const online = navigator.onLine;
    if (!networkStatus) return;
    networkStatus.textContent = online ? "En ligne" : "Hors ligne";
    networkStatus.style.background = online ? "var(--mint)" : "var(--cream)";
    networkStatus.style.color = online ? "var(--green)" : "#9B4C00";
  }

  function showError(message) {
    if (!loginError) return;
    loginError.textContent = message;
    loginError.hidden = !message;
  }

  function friendlyError(status, detail) {
    const code = typeof detail === "string" ? detail : detail?.code;
    const map = {
      jeton_requis: "Ton code élève est nécessaire.",
      jeton_invalide: "Ce code élève n’est pas reconnu.",
      jeton_expire: "Ta session a expiré. Reconnecte-toi.",
      jeton_revoque: "Cette session n’est plus active. Reconnecte-toi.",
      trop_de_tentatives: "Trop de tentatives. Attends un peu avant de réessayer.",
      auth_mal_configuree: "La connexion est momentanément indisponible.",
      auth_non_configuree: "La connexion est momentanément indisponible.",
      exercice_inconnu: "Cet exercice n’est plus disponible.",
      contenu_retire: "Ce contenu a été retiré du parcours.",
      version_perimee: "Mika a reçu une réponse plus récente. Recharge la séance.",
    };
    if (code && map[code]) return map[code];
    if (status >= 500) return "MikaMike rencontre un problème temporaire. Réessaie dans un instant.";
    if (status === 404) return "Ce contenu n’est pas disponible.";
    if (status === 403) return "Tu n’as pas accès à ce contenu.";
    return "Impossible de continuer pour le moment. Réessaie dans un instant.";
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");
    if (state.token) headers.set("Authorization", \`Bearer \${state.token}\`);

    if (window.MikaNativeHttp?.request) {
      const result = await window.MikaNativeHttp.request({
        path,
        method: options.method || "GET",
        headers: Object.fromEntries(headers.entries()),
        body: options.body || null,
      });
      if (result.status < 200 || result.status >= 300) {
        const error = new Error(friendlyError(result.status, result.data?.detail));
        error.status = result.status;
        error.payload = result.data;
        throw error;
      }
      return result.data;
    }

    const response = await fetch(\`\${API}\${path}\`, { ...options, headers });
    let payload = null;
    if (response.status !== 204) {
      const text = await response.text();
      payload = text ? JSON.parse(text) : null;
    }
    if (!response.ok) {
      const error = new Error(friendlyError(response.status, payload?.detail));
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function requestId(prefix) {
    const suffix = globalThis.crypto?.randomUUID?.() || \`\${Date.now()}-\${Math.random().toString(16).slice(2)}\`;
    return \`\${prefix}-\${suffix}\`.slice(0, 120);
  }

  async function loginStudent(code) {
    if (state.demo) return { token: "demo-token", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 };
    return api("/auth/eleve/jeton", {
      method: "POST",
      body: JSON.stringify({ student_pseudo_id: code }),
    });
  }

  function appendMessage(kind, text) {
    const wrap = document.createElement("div");
    wrap.className = \`message \${kind === "user" ? "user-message" : "mika-message"}\`;
    if (kind !== "user") {
      const icon = document.createElement("span");
      icon.textContent = "🐱";
      wrap.appendChild(icon);
    }
    const p = document.createElement("p");
    p.textContent = text;
    wrap.appendChild(p);
    $("#chatMessages")?.appendChild(wrap);
    wrap.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function setComposerEnabled(enabled, statusText = "") {
    if (chatInput) chatInput.disabled = !enabled;
    if (chatSubmit) chatSubmit.disabled = !enabled;
    if (micButton) micButton.disabled = !enabled;
    if (voiceStatus && statusText) voiceStatus.textContent = statusText;
  }

  function renderTutor(payload) {
    state.tutorat = payload;
    const messages = payload?.etat?.messages || [];
    const message = payload?.reponse?.message || messages[messages.length - 1];
    if (message) appendMessage("mika", message);
  }

  async function prepareTutor() {
    setComposerEnabled(false, "Mika prépare ton exercice…");
    try {
      const step = await api(\`/parcours/prochaine-etape?student_id=\${encodeURIComponent(state.studentId)}\`);
      state.nextStep = step;
      const ctx = $("#exerciseContext");
      if (ctx) ctx.hidden = false;
      $("#exerciseTitle").textContent = step.exercice_id || "Exercice";
      $("#exerciseStatement").textContent = step.consigne || "";
      $("#chatMessages").innerHTML = "";
      const session = await api("/mika/session/start", {
        method: "POST",
        body: JSON.stringify({
          student_pseudo_id: state.studentId,
          exercice_id: step.exercice_id,
          requete_id: requestId("start"),
        }),
      });
      renderTutor(session);
      setComposerEnabled(true, voiceCapabilityText());
    } catch (error) {
      appendMessage("mika", \`Je n’arrive pas à ouvrir le prochain exercice : \${error.message}\`);
      setComposerEnabled(false, "Le micro sera disponible quand l’exercice pourra démarrer.");
    }
  }

  function openDashboard() {
    loginView.hidden = true;
    dashboardView.hidden = false;
    $("#studentName").textContent = state.demo ? "Alex 👋" : "👋";
    $("#heroMessage").textContent = state.demo
      ? "Aujourd’hui : consolider les fractions, puis un mini-quiz."
      : "On reprend là où tu t’es arrêté.";
    if (state.demo) hydrateDemo();
    else prepareTutor();
  }

  function closeDashboard() {
    stopVoice();
    state.token = "";
    state.studentId = "";
    state.tutorat = null;
    state.nextStep = null;
    sessionStorage.removeItem("mikamike_student_token");
    sessionStorage.removeItem("mikamike_student_id");
    dashboardView.hidden = true;
    loginView.hidden = false;
    studentCode.value = "";
    showError("");
    setComposerEnabled(false, "Le micro sera disponible avec un exercice actif.");
    studentCode.focus();
  }

  function switchPanel(name) {
    $$(".panel").forEach((panel) => panel.classList.toggle("active-panel", panel.id === \`panel-\${name}\`));
    $$(".nav-card").forEach((button) => button.classList.toggle("active", button.dataset.panel === name));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function hydrateDemo() {
    $("#progressGrid").innerHTML = \`
      <article class="metric-card"><span class="metric-icon">🌱</span><strong>3 à découvrir</strong><p>Proportionnalité, vitesse, mélanges.</p></article>
      <article class="metric-card"><span class="metric-icon">🧠</span><strong>4 en cours</strong><p>Fractions, calcul littéral, unités, angles.</p></article>
      <article class="metric-card"><span class="metric-icon">🏆</span><strong>7 maîtrisées</strong><p>Des acquis confirmés sur plusieurs jours.</p></article>\`;
    catalogNotice.hidden = false;
    catalogNotice.textContent = "Mode démonstration : ces contenus sont fictifs et ne représentent pas le catalogue pédagogique publié.";
    $("#exerciseContext").hidden = false;
    $("#exerciseTitle").textContent = "Démo — Fractions";
    $("#exerciseStatement").textContent = "Explique avec tes mots ce que signifie 3/4.";
    $("#chatMessages").innerHTML = '<div class="message mika-message"><span>🐱</span><p>On travaille les fractions. Explique-moi avec tes mots ce que signifie 3/4.</p></div>';
    setComposerEnabled(true, voiceCapabilityText());
  }

  function voiceCapabilityText() {
    if (window.MikaNativeSpeech?.available) return "Micro natif disponible.";
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    return SpeechRecognition
      ? "Micro disponible. Appuie sur « Dicter » puis parle normalement."
      : "La dictée vocale n’est pas prise en charge par ce navigateur. L’app Android/iOS utilisera le micro natif.";
  }

  function setListening(listening, message) {
    state.listening = listening;
    if (micButton) {
      micButton.classList.toggle("listening", listening);
      micButton.setAttribute("aria-label", listening ? "Arrêter la dictée vocale" : "Activer la dictée vocale");
      micButton.querySelector("span:last-child").textContent = listening ? "Arrêter" : "Dicter";
    }
    if (voiceStatus && message) voiceStatus.textContent = message;
  }

  function applyTranscript(transcript) {
    if (!chatInput || !transcript) return;
    const spacer = state.voiceBaseText && !state.voiceBaseText.endsWith(" ") ? " " : "";
    chatInput.value = \`\${state.voiceBaseText}\${spacer}\${transcript}\`;
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
  }

  async function startNativeVoice() {
    state.voiceBaseText = chatInput.value.trimEnd();
    setListening(true, "Écoute en cours… parle normalement.");
    try {
      await window.MikaNativeSpeech.start({
        language: "fr-FR",
        onPartial: applyTranscript,
        onState: (listening) => {
          if (!listening) setListening(false, "Dictée terminée. Tu peux corriger le texte puis l’envoyer.");
        },
        onError: (message) => setListening(false, message || "La dictée vocale a rencontré un problème."),
      });
    } catch (error) {
      setListening(false, error?.message || "Impossible de démarrer le micro.");
    }
  }

  function startWebVoice() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setListening(false, "La dictée vocale n’est pas prise en charge par ce navigateur.");
      return;
    }
    state.voiceBaseText = chatInput.value.trimEnd();
    const recognition = new Recognition();
    recognition.lang = "fr-FR";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true, "Écoute en cours… parle normalement.");
    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i += 1) transcript += event.results[i][0]?.transcript || "";
      applyTranscript(transcript.trim());
    };
    recognition.onerror = (event) => {
      const map = {
        "not-allowed": "Accès au micro refusé. Autorise le micro dans les réglages puis réessaie.",
        "service-not-allowed": "Le service vocal est bloqué par le navigateur.",
        "audio-capture": "Aucun micro utilisable n’a été détecté.",
        "no-speech": "Je n’ai rien entendu. Réessaie en parlant un peu plus près du micro.",
        "network": "La reconnaissance vocale est momentanément indisponible.",
      };
      setListening(false, map[event.error] || "La dictée vocale a rencontré un problème.");
    };
    recognition.onend = () => {
      state.recognition = null;
      if (state.listening) setListening(false, "Dictée terminée. Tu peux corriger le texte puis l’envoyer.");
    };
    state.recognition = recognition;
    try { recognition.start(); }
    catch { setListening(false, "Impossible de démarrer la dictée vocale pour le moment."); }
  }

  async function stopVoice() {
    try {
      if (window.MikaNativeSpeech?.stop && state.listening) await window.MikaNativeSpeech.stop();
      state.recognition?.stop?.();
    } catch {}
    state.recognition = null;
    if (state.listening) setListening(false, "Dictée arrêtée.");
  }

  async function toggleVoice() {
    if (state.listening) return stopVoice();
    if (window.MikaNativeSpeech?.available) return startNativeVoice();
    return startWebVoice();
  }

  function setupInstall() {
    if (!installButton) return;
    const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true || window.MIKAMIKE_NATIVE;
    if (standalone) return;

    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      state.installPrompt = event;
      installButton.hidden = false;
    });

    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
    if (isIos) installButton.hidden = false;

    installButton.addEventListener("click", async () => {
      if (state.installPrompt) {
        state.installPrompt.prompt();
        const choice = await state.installPrompt.userChoice;
        state.installPrompt = null;
        if (choice?.outcome === "accepted") installButton.hidden = true;
        return;
      }
      if (isIos) alert("Sur iPhone/iPad : ouvre le menu Partager puis choisis « Sur l’écran d’accueil ».");
      else alert("Utilise le menu du navigateur puis « Installer MikaMike » ou « Ajouter à l’écran d’accueil ».");
    });

    window.addEventListener("appinstalled", () => {
      installButton.hidden = true;
      state.installPrompt = null;
    });
  }

  loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    const code = studentCode.value.trim();
    if (!code) return showError("Entre ton code élève.");
    const button = loginForm.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = "Connexion…";
    try {
      const result = await loginStudent(code);
      state.token = result.token;
      state.studentId = code;
      sessionStorage.setItem("mikamike_student_token", state.token);
      sessionStorage.setItem("mikamike_student_id", state.studentId);
      openDashboard();
    } catch (error) {
      showError(error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Commencer avec Mika";
    }
  });

  logoutButton?.addEventListener("click", closeDashboard);
  micButton?.addEventListener("click", toggleVoice);
  $$(".nav-card").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.panel)));
  $$("[data-go]").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.go)));

  $$(".subject-card").forEach((button) => {
    button.addEventListener("click", () => {
      const subject = button.dataset.subject;
      catalogNotice.hidden = false;
      catalogNotice.textContent = state.demo
        ? \`\${subject} sélectionné. En démonstration, ouvre Mika pour voir le parcours fictif.\`
        : \`\${subject} sélectionné. Mika choisit la prochaine étape validée par le serveur.\`;
    });
  });

  $("#chatForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = chatInput.value.trim();
    if (!value) return;
    await stopVoice();
    appendMessage("user", value);
    chatInput.value = "";

    if (state.demo) {
      setTimeout(() => appendMessage("mika", "Bien vu. Maintenant, donne-moi un exemple concret où on partage quelque chose en quatre parts égales."), 250);
      return;
    }

    if (!state.tutorat) {
      appendMessage("mika", "La séance n’est pas encore prête. Recharge le prochain exercice.");
      return;
    }

    setComposerEnabled(false, "Mika analyse ta réponse…");
    try {
      const endpoint = state.tutorat.etat?.attend_comprehension ? "comprehension" : "answer";
      const result = await api(\`/mika/session/\${endpoint}\`, {
        method: "POST",
        body: JSON.stringify({
          student_pseudo_id: state.studentId,
          tutorat_id: state.tutorat.tutorat_id,
          version: state.tutorat.version,
          requete_id: requestId(endpoint),
          reponse: value,
        }),
      });
      renderTutor(result);
      setComposerEnabled(!result?.etat?.termine, result?.etat?.termine ? "Exercice terminé." : voiceCapabilityText());
    } catch (error) {
      appendMessage("mika", error.message);
      setComposerEnabled(true, voiceCapabilityText());
    }
  });

  window.addEventListener("online", setNetworkStatus);
  window.addEventListener("offline", setNetworkStatus);
  setNetworkStatus();
  setupInstall();

  if (!window.MIKAMIKE_NATIVE && "serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {});
  }

  if (state.demo) {
    state.token = "demo-token";
    state.studentId = "demo-eleve";
    openDashboard();
  } else if (state.token && state.studentId) {
    openDashboard();
  }
})();