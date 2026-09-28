(() => {
  "use strict";
  const API = window.MIKAMIKE_API_BASE || "/api/v1";
  const $ = (s) => document.querySelector(s);
  let accountToken = sessionStorage.getItem("mikamike_account_token") || "";

  function detailMessage(status, detail) {
    const code = typeof detail === "string" ? detail : detail?.code;
    const map = {
      identifiants_invalides: "Adresse e-mail ou mot de passe incorrect.",
      token_absent: "Reconnecte ton compte parent.",
      token_invalide: "La session parent n’est plus valide.",
      jeton_revoque: "La session a été révoquée. Reconnecte-toi.",
      acces_refuse: "Ce compte parent n’est pas lié à ce code élève.",
      compte_inconnu: "Ce compte n’est plus disponible.",
      trop_de_tentatives: "Trop de tentatives. Réessaie plus tard."
    };
    if (code && map[code]) return map[code];
    if (status >= 500) return "MikaMike rencontre un problème temporaire.";
    if (status === 403) return "Ce compte n’a pas accès à cet élève.";
    return "Impossible de charger le tableau de bord.";
  }

  async function api(path, options = {}, token = "") {
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const r = await fetch(`${API}${path}`, {...options, headers});
    const raw = r.status === 204 ? "" : await r.text();
    const payload = raw ? JSON.parse(raw) : null;
    if (!r.ok) {
      const e = new Error(detailMessage(r.status, payload?.detail));
      e.status = r.status;
      e.payload = payload;
      throw e;
    }
    return payload;
  }

  async function connect(email, password) {
    return api("/comptes/connexion", {
      method: "POST",
      body: JSON.stringify({email, mot_de_passe: password})
    });
  }

  function renderDashboard(code, data) {
    const s = data.statistiques_pedagogiques || {};
    $("#parentStudentTitle").textContent = `Progression — ${code}`;
    $("#parentSuccess").textContent = `${s.exercices_reussis ?? 0} / ${s.exercices_tentes ?? 0}`;
    $("#parentRate").textContent = `${Math.round((s.taux_reussite ?? 0) * 100)} %`;
    $("#parentLevel").textContent = s.niveau_actuel || "—";
    const wrap = $("#parentCompetences");
    wrap.innerHTML = "";
    const entries = Object.entries(s.competences || {});
    if (!entries.length) {
      wrap.innerHTML = '<p class="form-help">Aucune compétence suivie pour le moment.</p>';
    } else {
      for (const [name, value] of entries) {
        const card = document.createElement("article");
        card.className = "parent-competence";
        const strong = document.createElement("strong");
        strong.textContent = name;
        const state = document.createElement("span");
        state.textContent = value.etat || "INCONNU";
        const small = document.createElement("small");
        small.textContent = `${value.reussites ?? 0} réussite(s) sur ${value.tentatives ?? 0} tentative(s)`;
        card.append(strong, state, small);
        wrap.appendChild(card);
      }
    }
    $("#parentDashboard").hidden = false;
  }

  $("#parentLoginForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = $("#parentEmail").value.trim();
    const password = $("#parentPassword").value;
    const code = $("#parentStudentCode").value.trim();
    const error = $("#parentError");
    error.hidden = true;
    error.textContent = "";
    if (!email || !password || !code) {
      error.textContent = "Renseigne l’e-mail, le mot de passe et le code élève.";
      error.hidden = false;
      return;
    }
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = "Connexion…";
    try {
      const auth = await connect(email, password);
      accountToken = auth.token;
      sessionStorage.setItem("mikamike_account_token", accountToken);
      $("#parentPassword").value = "";
      $("#parentStatus").textContent = `Compte connecté : ${auth.compte?.prenom || auth.compte?.email || "parent"}.`;
      const dashboard = await api(`/parents/dashboard/${encodeURIComponent(code)}`, {}, accountToken);
      renderDashboard(code, dashboard);
    } catch (e) {
      error.textContent = e.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = "Afficher les progrès";
    }
  });

  $("#parentLogout")?.addEventListener("click", () => {
    accountToken = "";
    sessionStorage.removeItem("mikamike_account_token");
    $("#parentDashboard").hidden = true;
    $("#parentStatus").textContent = "Le compte parent doit déjà être lié à cet élève.";
  });
})();