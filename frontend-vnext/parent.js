(() => {
  "use strict";

  const API = "/api/v1";
  const TOKEN_KEY = "mikamike_parent_token";
  const CHILDREN_KEY = "mikamike_parent_children";
  const demo = new URLSearchParams(location.search).get("demo") === "1";
  const $ = (s) => document.querySelector(s);

  function readChildren() {
    try {
      const value = JSON.parse(sessionStorage.getItem(CHILDREN_KEY) || "[]");
      return Array.isArray(value) ? value.filter((v) => typeof v === "string" && v.length > 0).slice(0, 8) : [];
    } catch {
      return [];
    }
  }

  const state = {
    token: sessionStorage.getItem(TOKEN_KEY) || "",
    account: null,
    children: readChildren(),
    selected: "",
  };

  function setMessage(element, text) {
    if (!element) return;
    element.textContent = text || "";
    element.hidden = !text;
  }

  function globalMessage(text, tone = "info") {
    const el = $("#parentGlobalMessage");
    if (!el) return;
    el.dataset.tone = tone;
    setMessage(el, text);
  }

  function friendlyError(status, detail) {
    const code = typeof detail === "string" ? detail : detail && detail.code;
    const messages = {
      identifiants_invalides: "Adresse e-mail ou mot de passe incorrect.",
      email_deja_utilise: "Cette adresse e-mail est déjà utilisée.",
      mot_de_passe_trop_court: "Le mot de passe doit contenir au moins 8 caractères.",
      email_non_verifie: "Vérifiez d’abord votre adresse e-mail.",
      invitation_invalide: "Ce code d’invitation est invalide ou expiré.",
      deja_lie: "Cet enfant est déjà lié à votre compte.",
      acces_refuse: "Ce compte n’est pas autorisé à consulter cet élève.",
      token_absent: "Votre session parent a expiré.",
      token_invalide: "Votre session parent n’est plus valide.",
      jeton_revoque: "Votre session parent a été révoquée. Reconnectez-vous.",
      compte_inconnu: "Ce compte n’est plus disponible.",
      trop_de_tentatives: "Trop de tentatives. Réessayez un peu plus tard.",
      courriel_indisponible: "Le message de vérification ne peut pas être envoyé pour le moment.",
    };
    if (code && messages[code]) return messages[code];
    if (status >= 500) return "MikaMike rencontre un problème temporaire. Réessayez dans un instant.";
    if (status === 403) return "Accès refusé.";
    if (status === 404) return "Aucune donnée disponible pour cet élève.";
    return "Impossible de continuer pour le moment.";
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.body !== undefined) headers.set("Content-Type", "application/json");
    if (state.token) headers.set("Authorization", "Bearer " + state.token);
    const response = await fetch(API + path, { ...options, headers });
    const text = response.status === 204 ? "" : await response.text();
    let payload = null;
    if (text) {
      try { payload = JSON.parse(text); } catch { payload = null; }
    }
    if (!response.ok) {
      const err = new Error(friendlyError(response.status, payload && payload.detail));
      err.status = response.status;
      err.code = typeof (payload && payload.detail) === "string"
        ? payload.detail
        : payload && payload.detail && payload.detail.code || null;
      throw err;
    }
    return payload;
  }

  function saveToken(token) {
    state.token = token || "";
    if (state.token) sessionStorage.setItem(TOKEN_KEY, state.token);
    else sessionStorage.removeItem(TOKEN_KEY);
  }

  function writeChildren() {
    sessionStorage.setItem(CHILDREN_KEY, JSON.stringify(state.children));
  }

  function clearSession() {
    saveToken("");
    state.account = null;
    state.selected = "";
    state.children = [];
    sessionStorage.removeItem(CHILDREN_KEY);
  }

  function showAuth(mode = "login") {
    $("#parentAuthView").hidden = mode !== "login";
    $("#parentSignupView").hidden = mode !== "signup";
    $("#parentDashboardView").hidden = true;
    $("#parentLogout").hidden = true;
  }

  function showDashboard() {
    $("#parentAuthView").hidden = true;
    $("#parentSignupView").hidden = true;
    $("#parentDashboardView").hidden = false;
    $("#parentLogout").hidden = false;
    const name = state.account && state.account.prenom && state.account.prenom.trim();
    $("#parentWelcome").textContent = name ? "Bonjour " + name + " 👋" : "Bonjour 👋";
    $("#emailVerificationBanner").hidden = !(state.account && state.account.email_verifie === false);
    renderChildren();
  }

  function setNetworkStatus() {
    const el = $("#parentNetworkStatus");
    const online = navigator.onLine;
    el.textContent = online ? "En ligne" : "Hors ligne";
    el.style.background = online ? "var(--mint)" : "var(--cream)";
    el.style.color = online ? "var(--green)" : "#9B4C00";
  }

  function addChild(pseudo) {
    const clean = String(pseudo || "").trim();
    if (!clean || state.children.includes(clean)) return;
    state.children = [...state.children, clean].slice(-8);
    writeChildren();
  }

  function maskedChild(pseudo) {
    const p = String(pseudo);
    if (p.length <= 4) return "Élève •" + p.slice(-2);
    return "Élève ••••" + p.slice(-4);
  }

  function renderChildren() {
    const wrap = $("#parentChildren");
    const section = $("#parentChildrenSection");
    section.hidden = state.children.length === 0;
    wrap.innerHTML = "";
    state.children.forEach((pseudo) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "parent-child-tab" + (pseudo === state.selected ? " active" : "");
      button.textContent = maskedChild(pseudo);
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", pseudo === state.selected ? "true" : "false");
      button.addEventListener("click", () => loadDashboard(pseudo));
      wrap.appendChild(button);
    });
  }

  function demoDashboard() {
    return {
      pseudo_id: "demo-eleve",
      statistiques_pedagogiques: {
        exercices_tentes: 32,
        exercices_reussis: 24,
        taux_reussite: 0.75,
        niveau_actuel: "3/6 compétences consolidées",
        competences: {
          "Fractions": { tentatives: 8, reussites: 7, etat: "MAITRISE" },
          "Proportionnalité": { tentatives: 7, reussites: 5, etat: "EN_COURS" },
          "Conversions d’unités": { tentatives: 6, reussites: 3, etat: "FRAGILE" },
          "Angles": { tentatives: 5, reussites: 5, etat: "ACQUIS_AUTONOME" },
          "Calcul littéral": { tentatives: 6, reussites: 4, etat: "A_REVOIR" },
        },
      },
    };
  }

  function stateLabel(etat) {
    const map = {
      INCONNU: "À découvrir",
      FRAGILE: "Fragile",
      EN_COURS: "En cours",
      ACQUIS_ASSISTE: "Acquis avec aide",
      ACQUIS_AUTONOME: "Acquis autonome",
      A_REVOIR: "À revoir",
      MAITRISE: "Maîtrisée",
    };
    return map[etat] || "En cours";
  }

  function renderDashboard(data) {
    const stats = data.statistiques_pedagogiques;
    const entries = Object.entries(stats.competences || {});
    const consolidated = entries.filter(([, value]) => ["MAITRISE", "ACQUIS_AUTONOME"].includes(value.etat)).length;
    const percent = Math.round((stats.taux_reussite || 0) * 100);
    $("#parentProgressSection").hidden = false;
    $("#parentStudentLabel").textContent = maskedChild(data.pseudo_id);
    $("#parentLevelLabel").textContent = stats.niveau_actuel || "Progression en cours";
    $("#parentMetrics").innerHTML =
      '<article class="metric-card accent-green"><span class="metric-icon">📝</span><strong>' + stats.exercices_tentes + '</strong><p>exercices tentés</p></article>' +
      '<article class="metric-card accent-blue"><span class="metric-icon">✅</span><strong>' + stats.exercices_reussis + '</strong><p>exercices réussis</p></article>' +
      '<article class="metric-card accent-teal"><span class="metric-icon">📈</span><strong>' + percent + '%</strong><p>taux de réussite global</p></article>' +
      '<article class="metric-card accent-orange"><span class="metric-icon">🏆</span><strong>' + consolidated + '</strong><p>compétences consolidées</p></article>';

    const list = $("#parentCompetences");
    list.innerHTML = "";
    if (!entries.length) {
      list.innerHTML = '<div class="parent-empty-state">Les premiers indicateurs apparaîtront après quelques activités.</div>';
      return;
    }
    entries.sort((a, b) => a[0].localeCompare(b[0], "fr"));
    entries.forEach(([name, value]) => {
      const row = document.createElement("article");
      row.className = "parent-competence-row";
      const rate = value.tentatives ? Math.round((value.reussites / value.tentatives) * 100) : 0;
      const left = document.createElement("div");
      const strong = document.createElement("strong");
      const detail = document.createElement("span");
      const chip = document.createElement("span");
      strong.textContent = name;
      detail.textContent = value.reussites + "/" + value.tentatives + " réussites · " + rate + "%";
      chip.className = "parent-state-chip";
      chip.dataset.state = value.etat;
      chip.textContent = stateLabel(value.etat);
      left.append(strong, detail);
      row.append(left, chip);
      list.appendChild(row);
    });
  }

  async function loadDashboard(pseudo) {
    state.selected = pseudo;
    renderChildren();
    globalMessage("Chargement du suivi…");
    try {
      const data = demo ? demoDashboard() : await api("/parents/dashboard/" + encodeURIComponent(pseudo));
      renderDashboard(data);
      globalMessage("");
    } catch (error) {
      $("#parentProgressSection").hidden = true;
      if (error.status === 403) {
        state.children = state.children.filter((value) => value !== pseudo);
        writeChildren();
        renderChildren();
      }
      globalMessage(error.message, "error");
    }
  }

  async function restoreSession() {
    if (demo) {
      state.account = { prenom: "Camille", email_verifie: true, role: "parent" };
      state.children = ["demo-eleve"];
      showDashboard();
      await loadDashboard("demo-eleve");
      globalMessage("Mode démonstration : toutes les données affichées sont fictives.", "demo");
      return;
    }
    if (!state.token) {
      showAuth("login");
      return;
    }
    try {
      state.account = await api("/comptes/moi");
      showDashboard();
      if (state.children.length) await loadDashboard(state.children[0]);
    } catch {
      clearSession();
      showAuth("login");
    }
  }

  $("#parentLoginForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const errorEl = $("#parentLoginError");
    setMessage(errorEl, "");
    const email = $("#parentEmail").value.trim();
    const password = $("#parentPassword").value;
    const button = form.querySelector('button[type="submit"]');
    if (!email || !password) {
      setMessage(errorEl, "Renseignez votre adresse e-mail et votre mot de passe.");
      return;
    }
    button.disabled = true;
    button.textContent = "Connexion…";
    try {
      const result = await api("/comptes/connexion", {
        method: "POST",
        body: JSON.stringify({ email, mot_de_passe: password }),
      });
      saveToken(result.token);
      state.account = result.compte;
      showDashboard();
      if (state.children.length) await loadDashboard(state.children[0]);
    } catch (error) {
      setMessage(errorEl, error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Se connecter";
    }
  });

  $("#parentSignupForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const errorEl = $("#parentSignupError");
    setMessage(errorEl, "");
    const email = $("#parentSignupEmail").value.trim();
    const password = $("#parentSignupPassword").value;
    const firstName = $("#parentFirstName").value.trim();
    const button = form.querySelector('button[type="submit"]');
    if (!email || password.length < 8) {
      setMessage(errorEl, "Saisissez une adresse valide et un mot de passe d’au moins 8 caractères.");
      return;
    }
    button.disabled = true;
    button.textContent = "Création…";
    try {
      const body = { email, mot_de_passe: password, role: "parent" };
      if (firstName) body.prenom = firstName;
      const result = await api("/comptes/inscription", {
        method: "POST",
        body: JSON.stringify(body),
      });
      saveToken(result.token);
      state.account = result.compte;
      showDashboard();
      globalMessage("Compte créé. Vérifiez maintenant votre adresse e-mail.");
    } catch (error) {
      setMessage(errorEl, error.message);
    } finally {
      button.disabled = false;
      button.textContent = "Créer mon compte";
    }
  });

  $("#parentConfirmation")?.addEventListener("change", (event) => {
    $("#parentLinkButton").disabled = !event.target.checked;
  });

  $("#parentLinkForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorEl = $("#parentLinkError");
    setMessage(errorEl, "");
    const codeInput = $("#parentInviteCode");
    const code = codeInput.value.trim();
    if (!code || !$("#parentConfirmation").checked) {
      setMessage(errorEl, "Saisissez le code et confirmez votre relation avec l’enfant.");
      return;
    }
    const button = $("#parentLinkButton");
    button.disabled = true;
    button.textContent = "Rattachement…";
    try {
      const result = await api("/liens/accepter", {
        method: "POST",
        body: JSON.stringify({ code, confirmation: true }),
      });
      codeInput.value = "";
      $("#parentConfirmation").checked = false;
      addChild(result.student_pseudo_id);
      renderChildren();
      globalMessage("Enfant rattaché. Le tableau de bord est maintenant accessible.", "success");
      await loadDashboard(result.student_pseudo_id);
    } catch (error) {
      setMessage(errorEl, error.message);
    } finally {
      button.textContent = "Rattacher l’enfant";
      button.disabled = !$("#parentConfirmation").checked;
    }
  });

  $("#parentExistingChildForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorEl = $("#parentExistingError");
    setMessage(errorEl, "");
    const pseudo = $("#existingStudentCode").value.trim();
    if (!pseudo) {
      setMessage(errorEl, "Saisissez le code élève.");
      return;
    }
    try {
      const data = demo ? demoDashboard() : await api("/parents/dashboard/" + encodeURIComponent(pseudo));
      addChild(pseudo);
      state.selected = pseudo;
      renderChildren();
      renderDashboard(data);
      $("#existingStudentCode").value = "";
      globalMessage("Enfant retrouvé et ajouté à cet onglet.", "success");
    } catch (error) {
      setMessage(errorEl, error.message);
    }
  });

  $("#resendVerification")?.addEventListener("click", async () => {
    const button = $("#resendVerification");
    button.disabled = true;
    try {
      await api("/comptes/verification-email", { method: "POST" });
      globalMessage("Message de vérification envoyé. Consultez votre boîte e-mail.", "success");
    } catch (error) {
      globalMessage(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  $("#parentRefresh")?.addEventListener("click", async () => {
    if (state.selected) await loadDashboard(state.selected);
    else if (state.children.length) await loadDashboard(state.children[0]);
    else globalMessage("Rattachez d’abord un enfant pour afficher sa progression.");
  });

  $("#parentLogout")?.addEventListener("click", async () => {
    try {
      if (!demo && state.token) await api("/comptes/deconnexion", { method: "POST" });
    } catch {
      // Purge locale dans tous les cas.
    }
    clearSession();
    showAuth("login");
    globalMessage("");
  });

  $("#showParentSignup")?.addEventListener("click", () => showAuth("signup"));
  $("#showParentLogin")?.addEventListener("click", () => showAuth("login"));
  window.addEventListener("online", setNetworkStatus);
  window.addEventListener("offline", setNetworkStatus);
  setNetworkStatus();
  restoreSession();
})();