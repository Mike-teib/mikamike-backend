(() => {
  "use strict";

  const API = "/api/v1";
  const state = {
    token: sessionStorage.getItem("mikamike_student_token") || "",
    studentId: sessionStorage.getItem("mikamike_student_id") || "",
    demo: new URLSearchParams(location.search).get("demo") === "1",
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

  function setNetworkStatus() {
    const online = navigator.onLine;
    if (networkStatus) {
      networkStatus.textContent = online ? "En ligne" : "Hors ligne";
      networkStatus.style.background = online ? "var(--mint)" : "var(--cream)";
      networkStatus.style.color = online ? "var(--green)" : "#9B4C00";
    }
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
    };
    if (code && map[code]) return map[code];
    if (status >= 500) return "MikaMike rencontre un problème temporaire. Réessaie dans un instant.";
    if (status === 404) return "Ce contenu n’est pas disponible.";
    if (status === 403) return "Tu n’as pas accès à ce contenu.";
    return "Impossible de continuer pour le moment. Vérifie ton code et réessaie.";
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");
    if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
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

  async function loginStudent(code) {
    if (state.demo) {
      return { token: "demo-token", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 };
    }
    return api("/auth/eleve/jeton", {
      method: "POST",
      body: JSON.stringify({ student_pseudo_id: code }),
    });
  }

  function openDashboard() {
    loginView.hidden = true;
    dashboardView.hidden = false;
    $("#studentName").textContent = state.demo ? "Alex 👋" : "👋";
    $("#heroMessage").textContent = state.demo
      ? "Aujourd’hui : consolider les fractions, puis un mini-quiz."
      : "On reprend là où tu t’es arrêté.";
    if (state.demo) hydrateDemo();
  }

  function closeDashboard() {
    state.token = "";
    state.studentId = "";
    sessionStorage.removeItem("mikamike_student_token");
    sessionStorage.removeItem("mikamike_student_id");
    dashboardView.hidden = true;
    loginView.hidden = false;
    studentCode.value = "";
    showError("");
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
    const chatInput = $("#chatInput");
    const chatButton = $("#chatForm button");
    chatInput.disabled = false;
    chatButton.disabled = false;
    $("#chatMessages").innerHTML = `
      <div class="message mika-message"><span>🐱</span><p>On travaille les fractions. Explique-moi avec tes mots ce que signifie 3/4.</p></div>`;
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
  $$(".nav-card").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.panel)));
  $$("[data-go]").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.go)));

  $$(".subject-card").forEach((button) => {
    button.addEventListener("click", () => {
      const subject = button.dataset.subject;
      catalogNotice.hidden = false;
      catalogNotice.textContent = state.demo
        ? `${subject} sélectionné. En démonstration, ouvre Mika pour voir le parcours fictif.`
        : `${subject} : l’interface est prête. Le branchement au catalogue validé nécessite l’endpoint de navigation pédagogique correspondant.`;
    });
  });

  $("#chatForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!state.demo) return;
    const input = $("#chatInput");
    const value = input.value.trim();
    if (!value) return;
    $("#chatMessages").insertAdjacentHTML("beforeend",
      `<div class="message user-message"><p></p></div>`);
    $("#chatMessages .user-message:last-child p").textContent = value;
    input.value = "";
    setTimeout(() => {
      $("#chatMessages").insertAdjacentHTML("beforeend",
        `<div class="message mika-message"><span>🐱</span><p>Bien vu. Maintenant, peux-tu donner un exemple concret où on partage quelque chose en quatre parts égales ?</p></div>`);
    }, 250);
  });

  window.addEventListener("online", setNetworkStatus);
  window.addEventListener("offline", setNetworkStatus);
  setNetworkStatus();

  if ("serviceWorker" in navigator && location.protocol === "https:") {
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