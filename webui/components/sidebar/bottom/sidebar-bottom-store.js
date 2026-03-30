import { createStore } from "/js/AlpineStore.js";

// Sidebar Bottom store manages version info display
const model = {
  versionNo: "",
  commitTime: "",

  get versionLabel() {
    if (!this.versionNo) return "";
    if (this.commitTime) {
      return `${this.versionNo} · ${this.commitTime}`;
    }
    return this.versionNo;
  },

  init() {
    const gi = globalThis.gitinfo;
    if (gi && gi.version && gi.version !== "unknown") {
      this.versionNo = gi.version;
      this.commitTime = gi.commit_time && gi.commit_time !== "unknown" ? gi.commit_time : "";
    }
  },
};

export const store = createStore("sidebarBottom", model);

