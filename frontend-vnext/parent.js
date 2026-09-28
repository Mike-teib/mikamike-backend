(() => {
  "use strict";

  const API = window.MIKAMIKE_API_BASE || "/api/v1";
  const state = {
    accountToken: sessionStorage.getItem("mikamike_account_token") || "",
  };
  const $ = (s) => document.querySelector(s);
  const form = $("#parentLoginForm");
  const fields = $("#parentAccountFields");
  const email = $("#parentEmail");
  const password = $("#parentPassword");
  const studentCode = $("#parentStudentCode");
  const errorBox = $("#parentLoginError");

  function showError(message) {
    errorBox.textContent = message || "";
    errorBox.hidden = !message;
  }

  async function request(path, options = {}, token = "") {
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${API}${path}`, { ...options, headers });
    let payload = null;
    if (response.status !== 204) {
      const text = await response.text();
      try { payload = text ? JSON.parse(text) : null; }
      catch { payload = text ? { detail: text } : null; }
    }
    if (!response.ok) {
      const err = new Error(typeof payload?.detail === "string" ? payload.detail : "requete_refusee");
      err.status = response.status;
      err.path = path;
      throw err;
    }
    return payload;
  }

  async function loginAccount() {
    const e = email.value.trim();
    const p = password.value;
    if (!e || !p) throw new Error("Entre l’e-mail et le mot de passe du compte.");
    const result = await request("/comptes/connexion", {
      method: "POST",
      body: JSON.stringify({ email: e, mot_de_passe: p }),
    });
    state.accountToken = result.token;
    sessionStorage.setItem("mikamike_account_token", state.accountToken);
    password.value = "";
    return result;
  }

  function renderDashboard(payload) {
    const stats = payload?.statistiques_pedagogiques || {};
    $("#parentDashboardTitle").textContent = `Suivi de ${payload?.pseudo_id || "l’élève"}`;
    $("#parentSuccess").textContent = String(stats.exercices_reussis ?? 0);
    $("#parentAttempts").textContent = String(stats.exercices_tentes ?? 0);
    $("#parentRate").textContent = Number.isFinite(Number(stats.taux_reussite))
      ? `${Math.round(Number(stats.taux_reussite) * (Number(stats.taux_reussite) <= 1 ? 100 : 1))}%`
      : "—";
    $("#parentLevel").textContent = stats.niveau_actuel || "À déterminer";
  }

  if (state.accountToken && fields) {
    fields.hidden = true;
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    const code = studentCode.value.trim();
    if (!code) return showError("Entre le code élève lié à ton compte.");
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = "Chargement…";
    try {
      if (!state.accountToken) await loginAccount();
      const dashboard = await request(`/parents/dashboard/${encodeURIComponent(code)}`, {}, state.accountToken);
      renderDashboard(dashboard);
      if (fields) fields.hidden = true;
    } catch (error) {
      if (error.status === 401) {
        state.accountToken = "";
        sessionStorage.removeItem("mikamike_account_token");
        if (fields) fields.hidden = false;
        showError("La session du compte n’est plus valide. Reconnecte-toi.");
      } else if (error.status === 403) {
        showError("Ce compte n’est pas lié à ce code élève.");
      } else if (error.status === 404 && ["/comptes/connexion"].includes(error.path)) {
        showError("Le serveur MikaMike n’est pas raccordé à la bonne version.");
      } else {
        showError(error.message === "identifiants_invalides" ? "E-mail ou mot de passe incorrect." : "Impossible de charger le suivi pour le moment.");
      }
    } finally {
      button.disabled = false;
      button.textContent = "Afficher le suivi";
    }
  });
})();
