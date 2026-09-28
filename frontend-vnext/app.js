(() => {
  "use strict";

  const API = window.MIKAMIKE_API_BASE || "";
  const params = new URLSearchParams(location.search);
  const state = {
    token: sessionStorage.getItem("mika_token") || "",
    studentId: localStorage.getItem("mika_code") || "",
    studentName: "",
    level: "",
    subjects: [],
    selectedSubject: sessionStorage.getItem("mika_subject") || "maths",
    history: [],
    demo: params.get("demo") === "1",
    openTarget: params.get("open") || "",
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
  const studentCode = $("#studentCode");
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
    if (state.token) headers.set("Authorization", `Bearer ${state.token}`);

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

    const response = await fetch(`${API}${path}`, { ...options, headers });
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
    const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return `${prefix}-${suffix}`.slice(0, 120);
  }

  async function loginStudent(code) {
    if (state.demo) {
      return { ok: true, eleve: "Alex", niveau: "college", matieres: ["maths", "physique"], upload: true, token: "demo-token" };
    }
    const result = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
    if (!result?.ok) throw new Error("Code incorrect. Réessaie.");
    return result;
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

  function subjectApiName(label) {
    const map = {
      "Mathématiques": "maths",
      "Physique": "physique",
      "SVT": "svt",
      "Chimie": "chimie",
    };
    return map[label] || label?.toLowerCase() || "maths";
  }

  function applySubjectAccess() {
    const allowed = state.subjects.length ? state.subjects : ["maths"];
    $$(".subject-card").forEach((button) => {
      const apiName = subjectApiName(button.dataset.subject);
      const enabled = allowed.includes(apiName);
      button.disabled = !enabled;
      button.classList.toggle("subject-disabled", !enabled);
      button.setAttribute("aria-disabled", String(!enabled));
      if (!enabled) button.title = "Cette matière n’est pas activée pour ce compte.";
      else button.removeAttribute("title");
    });
    if (!allowed.includes(state.selectedSubject)) state.selectedSubject = allowed[0] || "maths";
    sessionStorage.setItem("mika_subject", state.selectedSubject);
  }

  function prepareLegacySession() {
    state.history = [];
    state.selectedSubject = state.subjects.includes(state.selectedSubject)
      ? state.selectedSubject
      : (state.subjects[0] || "maths");
    applySubjectAccess();
    const ctx = $("#exerciseContext");
    if (ctx) ctx.hidden = true;
    $("#chatMessages").innerHTML = "";
    appendMessage("mika", `Salut ${state.studentName || "!"} 🐾 Explique-moi sur quoi tu bloques ou colle ton exercice. On avance ensemble, étape par étape.`);
    setComposerEnabled(true, voiceCapabilityText());
    if (catalogNotice) {
      catalogNotice.hidden = false;
      catalogNotice.textContent = `Matière active : ${state.selectedSubject}. Les autres matières disponibles dépendent de ton compte.`;
    }
  }

  function openDashboard() {
    loginView.hidden = true;
    dashboardView.hidden = false;
    $("#studentName").textContent = `${state.studentName || (state.demo ? "Alex" : "")} 👋`;
    $("#heroMessage").textContent = state.demo
      ? "Aujourd’hui : consolider les fractions, puis un mini-quiz."
      : (state.level ? `Niveau ${state.level} — on reprend là où tu t’es arrêté.` : "On reprend là où tu t’es arrêté.");
    if (state.demo) hydrateDemo();
    else prepareLegacySession();
    if (state.openTarget === "mika") switchPanel("mika");
  }

  function closeDashboard() {
    stopVoice();
    state.token = "";
    state.studentId = "";
    state.studentName = "";
    state.level = "";
    state.subjects = [];
    state.history = [];
    sessionStorage.removeItem("mika_token");
    sessionStorage.removeItem("mika_subject");
    localStorage.removeItem("mika_code");
    dashboardView.hidden = true;
    loginView.hidden = false;
    studentCode.value = "";
    showError("");
    setComposerEnabled(false, "Connecte-toi pour utiliser Mika et le micro.");
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

  async function completeLogin(code) {
    const result = await loginStudent(code);
    state.token = result.token || "";
    state.studentId = code;
    state.studentName = result.eleve || "";
    state.level = result.niveau || "";
    state.subjects = Array.isArray(result.matieres) && result.matieres.length ? result.matieres : ["maths"];
    if (state.token) sessionStorage.setItem("mika_token", state.token);
    else sessionStorage.removeItem("mika_token");
    localStorage.setItem("mika_code", code);
    openDashboard();
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
      await completeLogin(code);
    } catch (error) {
      showError(error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Commencer avec Mika";
    }
  });

  logoutButton?.addEventListener("click", closeDashboard);
  micCheckButton?.addEventListener("click", () => prepareMicrophone());
  micButton?.addEventListener("click", toggleVoice);
  $$(".nav-card").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.panel)));
  $$("[data-go]").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.go)));

  $$(".subject-card").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) return;
      const subject = button.dataset.subject;
      const apiName = subjectApiName(subject);
      if (!state.demo && !state.subjects.includes(apiName)) return;
      state.selectedSubject = apiName;
      sessionStorage.setItem("mika_subject", apiName);
      catalogNotice.hidden = false;
      catalogNotice.textContent = state.demo
        ? `${subject} sélectionné. Mode démonstration.`
        : `${subject} sélectionné. Mika utilisera cette matière pour la conversation.`;
      if (!state.demo) switchPanel("mika");
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

    state.history.push({ role: "user", content: value });
    setComposerEnabled(false, "Mika réfléchit…");
    try {
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          messages: state.history,
          code: state.studentId,
          matiere: state.selectedSubject || "maths",
          exercice_id: 0,
        }),
      });
      const reply = result?.reply || "Je n’ai pas reçu de réponse exploitable. Réessaie.";
      state.history.push({ role: "assistant", content: reply });
      appendMessage("mika", reply);
      if (result?.indice) appendMessage("mika", `💡 Indice : ${result.indice}`);
      setComposerEnabled(true, voiceCapabilityText());
    } catch (error) {
      appendMessage("mika", error.message || "Oups, petit souci technique. Réessaie dans un instant.");
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
    state.studentName = "Alex";
    state.level = "démo";
    state.subjects = ["maths", "physique"];
    openDashboard();
  } else if (state.studentId) {
    completeLogin(state.studentId).catch(() => {
      state.token = "";
      state.studentId = "";
      localStorage.removeItem("mika_code");
      sessionStorage.removeItem("mika_token");
      dashboardView.hidden = true;
      loginView.hidden = false;
    });
  }
})();