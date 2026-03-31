import { createStore } from "/js/AlpineStore.js";

const model = {
  versionNo: "",
  commitTime: "",
  userName: "",

  get versionLabel() {
    if (!this.versionNo) return "";
    if (this.commitTime) {
      return `${this.versionNo} · ${this.commitTime}`;
    }
    return this.versionNo;
  },

  logout() {
    window.location.href = "/logout";
  },

  init() {
    const gi = globalThis.gitinfo;
    if (gi && gi.version && gi.version !== "unknown") {
      this.versionNo = gi.version;
      this.commitTime = gi.commit_time && gi.commit_time !== "unknown" ? gi.commit_time : "";
    }
    if (window.__korevUserName) {
      this.userName = window.__korevUserName;
    }
  },
};

export const store = createStore("sidebarBottom", model);

