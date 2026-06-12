import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";

const model = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
  loading: false,
  error: "",
  success: "",

  reset() {
    this.currentPassword = "";
    this.newPassword = "";
    this.confirmPassword = "";
    this.loading = false;
    this.error = "";
    this.success = "";
  },

  get policyOk() {
    return (
      this.newPassword.length >= 12 &&
      /[A-Za-z]/.test(this.newPassword) &&
      /\d/.test(this.newPassword)
    );
  },

  get confirmOk() {
    return this.confirmPassword.length > 0 && this.confirmPassword === this.newPassword;
  },

  async submit() {
    this.error = "";
    this.success = "";

    if (!this.currentPassword) {
      this.error = "Saisissez votre mot de passe actuel.";
      return;
    }
    if (!this.policyOk) {
      this.error =
        "Le nouveau mot de passe doit contenir au moins 12 caractères, une lettre et un chiffre.";
      return;
    }
    if (!this.confirmOk) {
      this.error = "La confirmation ne correspond pas au nouveau mot de passe.";
      return;
    }

    this.loading = true;
    try {
      const response = await fetchApi("/change_password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          current_password: this.currentPassword,
          new_password: this.newPassword,
        }),
      });

      let payload = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (response.ok && payload?.success) {
        this.success = payload.message || "Mot de passe mis à jour avec succès.";
        this.currentPassword = "";
        this.newPassword = "";
        this.confirmPassword = "";
        setTimeout(() => {
          if (globalThis.closeModal) globalThis.closeModal();
          this.reset();
        }, 1800);
      } else {
        this.error =
          payload?.error || "Échec du changement de mot de passe. Réessayez.";
      }
    } catch (e) {
      console.error("change_password failed:", e);
      this.error = "Erreur réseau. Vérifiez votre connexion puis réessayez.";
    } finally {
      this.loading = false;
    }
  },
};

export const store = createStore("passwordModal", model);
