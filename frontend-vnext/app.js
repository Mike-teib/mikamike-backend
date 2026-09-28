(() => {
  "use strict";

  const API = window.MIKAMIKE_API_BASE || "/api/v1";
  const params = new URLSearchParams(location.search);
  const state = {
    accountToken: sessionStorage.getItem("mikamike_account_token") || "",
    token: "",
    studentId: sessionStorage.getItem("mikamike_student_id") || "",
    level: sessionStorage.getItem("mikamike_student_level") || "5e",
    selectedSubject: sessionStorage.getItem("mikamike_selected_subject") || "maths",
    demo: params.get("demo") === "1",
    openPanel: params.get("open") || "",
    tutorat: null,
    nextStep: null,
    listening: false,
    installPrompt: null,
    recognition: null,
    voiceBaseText: "",
    microphoneReady: false,
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  const loginView = $("#loginView");
  const dashboardView = $("#dashboardView");
  const loginForm = $("#studentLoginForm");
  const accountEmail = $("#accountEmail");
  const accountPassword = $("#accountPassword");
  const studentCode = $("#studentCode");
  const studentLevel = $("#studentLevel");
  const loginError = $("#loginError");
  const logoutButton = $("#logoutButton");
  const networkStatus = $("#networkStatus");
  const catalogNotice = $("#catalogNotice");
  const chatInput = $("#chatInput");
  const chatSubmit = $("#chatSubmit");
  const micButton = $("#micButton");
  const voiceStatus = $("#voiceStatus");
  const micCheckButton = $("#micCheckButton");
  const microCheckStatus = $("#microCheckStatus");
  const installButton = $("#installButton");
  const installDialog = $("#installDialog");
  const installDialogText = $("#installDialogText");
  const installDialogClose = $("#installDialogClose");

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
      token_absent: "Connecte d’abord ton compte MikaMike.",
      token_invalide: "La connexion du compte n’est plus valide.",
      identifiants_invalides: "E-mail ou mot de passe incorrect.",
      jeton_requis: "La session élève est nécessaire.",
      jeton_invalide: "La session élève n’est pas reconnue.",
      acces_refuse: "Ce compte n’est pas lié à ce code élève.",
      jeton_expire: "Ta session a expiré. Reconnecte-toi.",
      jeton_revoque: "Cette session n’est plus active. Reconnecte-toi.",
      trop_de_tentatives: "Trop de tentatives. Attends un peu avant de réessayer.",
      auth_mal_configuree: "La connexion est momentanément indisponible.",
      auth_non_configuree: "La connexion est momentanément indisponible.",
      exercice_inconnu: "Cet exercice n’est plus disponible.",
      contenu_indisponible: "Aucun exercice validé n’est encore disponible pour ce niveau et cette matière.",
      programme_indisponible: "Le programme de ce niveau et de cette matière n’est pas encore publié.",
      niveau_inconnu: "Ce niveau n’est pas reconnu.",
      matiere_inconnue: "Cette matière n’est pas encore disponible.",
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
    const { auth = "student", ...fetchOptions } = options;
    const headers = new Headers(fetchOptions.headers || {});
    headers.set("Content-Type", "application/json");
    const token = auth === "account" ? state.accountToken : auth === "student" ? state.token : "";
    if (token) headers.set("Authorization", `Bearer ${token}`);

    if (window.MikaNativeHttp?.request) {
      const result = await window.MikaNativeHttp.request({
        path,
        method: fetchOptions.method || "GET",
        headers: Object.fromEntries(headers.entries()),
        body: fetchOptions.body || null,
      });
      if (result.status < 200 || result.status >= 300) {
        const error = new Error(friendlyError(result.status, result.data?.detail));
        error.status = result.status;
        error.payload = result.data;
        error.path = path;
        throw error;
      }
      return result.data;
    }

    const response = await fetch(`${API}${path}`, { ...fetchOptions, headers });
    let payload = null;
    if (response.status !== 204) {
      const text = await response.text();
      try { payload = text ? JSON.parse(text) : null; }
      catch { payload = text ? { detail: text } : null; }
    }
    if (!response.ok) {
      const error = new Error(friendlyError(response.status, payload?.detail));
      error.status = response.status;
      error.payload = payload;
      error.path = path;
      throw error;
    }
    return payload;
  }

  function requestId(prefix) {
    const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return `${prefix}-${suffix}`.slice(0, 120);
  }

  async function loginAccount(email, password) {
    return api("/comptes/connexion", {
      auth: "none",
      method: "POST",
      body: JSON.stringify({ email, mot_de_passe: password }),
    });
  }

  async function loginStudent(code) {
    if (state.demo) return { token: "demo-token", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 };
    if (!state.accountToken) throw new Error("Connecte d’abord ton compte MikaMike.");
    return api("/auth/eleve/jeton", {
      auth: "account",
      method: "POST",
      body: JSON.stringify({ student_pseudo_id: code }),
    });
  }

  function subjectApiValue(label) {
    const map = {
      "Mathématiques": "maths",
      "Physique": "physique",
      "Chimie": "chimie",
      "SVT": "svt",
    };
    return map[label] || String(label || "").toLowerCase();
  }

  function appendMessage(kind, text) {
    const wrap = document.createElement("div");
    wrap.className = `message ${kind === "user" ? "user-message" : "mika-message"}`;
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
      const step = await api(`/parcours/prochaine-etape?student_id=${encodeURIComponent(state.studentId)}&level=${encodeURIComponent(state.level)}&subject=${encodeURIComponent(state.selectedSubject)}`);
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
      return true;
    } catch (error) {
      appendMessage("mika", `Je n’arrive pas à ouvrir le prochain exercice : ${error.message}`);
      setComposerEnabled(false, "Le micro sera disponible quand l’exercice pourra démarrer.");
      return false;
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
    if (state.openPanel === "mika") switchPanel("mika");
  }

  function closeDashboard() {
    stopVoice();
    state.accountToken = "";
    state.token = "";
    state.studentId = "";
    state.level = "5e";
    state.selectedSubject = "maths";
    state.tutorat = null;
    state.nextStep = null;
    sessionStorage.removeItem("mikamike_account_token");
    sessionStorage.removeItem("mikamike_student_id");
    sessionStorage.removeItem("mikamike_student_level");
    sessionStorage.removeItem("mikamike_selected_subject");
    dashboardView.hidden = true;
    loginView.hidden = false;
    if (accountPassword) accountPassword.value = "";
    studentCode.value = "";
    showError("");
    setComposerEnabled(false, "Le micro sera disponible avec un exercice actif.");
    studentCode.focus();
  }

  function switchPanel(name) {
    $$(".panel").forEach((panel) => panel.classList.toggle("active-panel", panel.id === `panel-${name}`));
    $$(".nav-card").forEach((button) => button.classList.toggle("active", button.dataset.panel === name));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function hydrateDemo() {
    $("#progressGrid").innerHTML = `
      <article class="metric-card"><span class="metric-icon">🌱</span><strong>3 à découvrir</strong><p>Proportionnalité, vitesse, mélanges.</p></article>
      <article class="metric-card"><span class="metric-icon">🧠</span><strong>4 en cours</strong><p>Fractions, calcul littéral, unités, angles.</p></article>
      <article class="metric-card"><span class="metric-icon">🏆</span><strong>7 maîtrisées</strong><p>Des acquis confirmés sur plusieurs jours.</p></article>`;
    catalogNotice.hidden = false;
    catalogNotice.textContent = "Mode démonstration : ces contenus sont fictifs et ne représentent pas le catalogue pédagogique publié.";
    $("#exerciseContext").hidden = false;
    $("#exerciseTitle").textContent = "Démo — Fractions";
    $("#exerciseStatement").textContent = "Explique avec tes mots ce que signifie 3/4.";
    $("#chatMessages").innerHTML = '<div class="message mika-message"><span>🐱</span><p>On travaille les fractions. Explique-moi avec tes mots ce que signifie 3/4.</p></div>';
    setComposerEnabled(true, voiceCapabilityText());
  }

  function setMicroCheckState(kind, message) {
    state.microphoneReady = kind === "ready";
    if (micCheckButton) {
      micCheckButton.classList.toggle("micro-ready", kind === "ready");
      micCheckButton.classList.toggle("micro-error", kind === "error");
      micCheckButton.textContent = kind === "checking"
        ? "🎙️ Vérification…"
        : kind === "ready"
          ? "🎙️ Micro prêt"
          : kind === "error"
            ? "🎙️ Micro à autoriser"
            : "🎙️ Vérifier le micro";
      micCheckButton.disabled = kind === "checking";
    }
    if (microCheckStatus) microCheckStatus.textContent = message;
    if (voiceStatus && message) voiceStatus.textContent = message;
  }

  function voiceCapabilityText() {
    if (window.MikaNativeSpeech?.available) return state.microphoneReady
      ? "Micro natif prêt. Appuie sur « Dicter » puis parle normalement."
      : "Micro natif disponible. Tu peux le vérifier puis utiliser « Dicter ».";
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return "La dictée vocale n’est pas prise en charge par ce navigateur. L’app Android/iOS utilisera le micro natif.";
    return state.microphoneReady
      ? "Micro prêt. Appuie sur « Dicter » puis parle normalement."
      : "Micro disponible. Appuie sur « Dicter » : MikaMike demandera l’autorisation si nécessaire.";
  }

  async function prepareMicrophone({ quiet = false } = {}) {
    if (window.MikaNativeSpeech?.available) {
      if (!quiet) setMicroCheckState("checking", "Vérification du micro natif…");
      try {
        if (window.MikaNativeSpeech.prepare) await window.MikaNativeSpeech.prepare();
        setMicroCheckState("ready", "Micro natif autorisé et prêt.");
        return true;
      } catch (error) {
        setMicroCheckState("error", error?.message || "Autorisation micro refusée.");
        return false;
      }
    }

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setMicroCheckState("error", "La dictée vocale n’est pas prise en charge par ce navigateur.");
      return false;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setMicroCheckState("ready", "Dictée vocale disponible. Le navigateur demandera le micro au démarrage.");
      return true;
    }

    if (!quiet) setMicroCheckState("checking", "Autorise le micro dans la fenêtre du navigateur.");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setMicroCheckState("ready", "Micro autorisé et prêt. Aucun son n’est conservé.");
      return true;
    } catch (error) {
      const denied = error?.name === "NotAllowedError" || error?.name === "PermissionDeniedError";
      setMicroCheckState("error", denied
        ? "Accès au micro refusé. Autorise le micro dans les réglages du navigateur puis réessaie."
        : "Aucun micro utilisable n’a été détecté.");
      return false;
    }
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
    chatInput.value = `${state.voiceBaseText}${spacer}${transcript}`;
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
    const ready = state.microphoneReady || await prepareMicrophone({ quiet: true });
    if (!ready) return;
    if (window.MikaNativeSpeech?.available) return startNativeVoice();
    return startWebVoice();
  }

  function showInstallGuide(message) {
    if (installDialogText) installDialogText.textContent = message;
    if (installDialog?.showModal) installDialog.showModal();
  }

  function setupInstall() {
    if (!installButton) return;
    const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true || window.MIKAMIKE_NATIVE;
    if (standalone) return;

    installButton.hidden = false;

    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      state.installPrompt = event;
    });

    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);

    installButton.addEventListener("click", async () => {
      if (state.installPrompt) {
        state.installPrompt.prompt();
        const choice = await state.installPrompt.userChoice;
        state.installPrompt = null;
        if (choice?.outcome === "accepted") installButton.hidden = true;
        return;
      }
      showInstallGuide(isIos
        ? "Sur iPhone ou iPad : touche Partager, puis « Sur l’écran d’accueil », puis confirme « Ajouter »."
        : "Dans le menu de ton navigateur, choisis « Installer MikaMike » ou « Ajouter à l’écran d’accueil ». Sur PC, Chrome et Edge proposent aussi l’installation dans la barre d’adresse.");
    });

    installDialogClose?.addEventListener("click", () => installDialog?.close?.());
    installDialog?.addEventListener("click", (event) => {
      if (event.target === installDialog) installDialog.close();
    });

    window.addEventListener("appinstalled", () => {
      installButton.hidden = true;
      state.installPrompt = null;
      installDialog?.close?.();
    });
  }

  loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    const email = accountEmail?.value.trim() || "";
    const password = accountPassword?.value || "";
    const code = studentCode.value.trim();
    const level = studentLevel?.value || "5e";
    if (!email) return showError("Entre l’e-mail du compte MikaMike.");
    if (!password) return showError("Entre le mot de passe.");
    if (!code) return showError("Entre le code élève.");

    const button = loginForm.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = "Connexion sécurisée…";
    try {
      const account = await loginAccount(email, password);
      state.accountToken = account.token;
      sessionStorage.setItem("mikamike_account_token", state.accountToken);

      const result = await loginStudent(code);
      state.token = result.token;
      state.studentId = code;
      state.level = level;
      state.selectedSubject = "maths";
      sessionStorage.setItem("mikamike_student_id", state.studentId);
      sessionStorage.setItem("mikamike_student_level", state.level);
      sessionStorage.setItem("mikamike_selected_subject", state.selectedSubject);

      if (accountPassword) accountPassword.value = "";
      openDashboard();
    } catch (error) {
      state.token = "";
      if (error.status === 404 && ["/comptes/connexion", "/auth/eleve/jeton"].includes(error.path)) {
        showError("Le serveur MikaMike n’est pas raccordé à la bonne version. La connexion a été arrêtée sans ouvrir de fausse session.");
      } else {
        showError(error.message);
      }
    } finally {
      button.disabled = false;
      button.textContent = "Se connecter et commencer";
    }
  });

  logoutButton?.addEventListener("click", closeDashboard);
  micCheckButton?.addEventListener("click", () => prepareMicrophone());
  micButton?.addEventListener("click", toggleVoice);
  $$(".nav-card").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.panel)));
  $$("[data-go]").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.go)));

  $$(".subject-card").forEach((button) => {
    button.addEventListener("click", async () => {
      const subject = button.dataset.subject;
      catalogNotice.hidden = false;
      if (state.demo) {
        catalogNotice.textContent = `${subject} sélectionné. En démonstration, ouvre Mika pour voir le parcours fictif.`;
        return;
      }

      state.selectedSubject = subjectApiValue(subject);
      sessionStorage.setItem("mikamike_selected_subject", state.selectedSubject);
      catalogNotice.textContent = `${subject} : recherche du prochain exercice validé…`;
      const ready = await prepareTutor();
      if (ready) {
        catalogNotice.textContent = `${subject} sélectionné. Le prochain exercice validé est prêt dans Mika.`;
        switchPanel("mika");
      } else {
        catalogNotice.textContent = `${subject} : aucun exercice validé n’est disponible pour ${state.level} pour le moment.`;
      }
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
      const result = await api(`/mika/session/${endpoint}`, {
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
    state.level = "5e";
    state.selectedSubject = "maths";
    openDashboard();
  } else if (state.accountToken && state.studentId) {
    if (studentLevel) studentLevel.value = state.level;
    loginStudent(state.studentId)
      .then((result) => {
        state.token = result.token;
        openDashboard();
      })
      .catch(() => {
        state.accountToken = "";
        state.token = "";
        sessionStorage.removeItem("mikamike_account_token");
        showError("Ta session de compte a expiré. Reconnecte-toi.");
      });
  }
})();