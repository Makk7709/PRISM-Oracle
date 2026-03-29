// Product decision:
// Evidence always starts on the neutral landing screen unless explicit
// resume is enabled in config.
export function shouldResumeLastSession(resumeLastSession) {
  return resumeLastSession === true;
}

export function applyLandingState(storage, localStore) {
  if (storage && typeof storage.setItem === "function") {
    storage.setItem("hasVisited", "true");
  }
  if (localStore) {
    if (typeof localStore.removeItem === "function") {
      localStore.removeItem("lastSelectedChat");
      localStore.removeItem("lastSelectedTask");
    }
    if (typeof localStore.setItem === "function") {
      localStore.setItem("korev_show_welcome", "true");
    }
  }
}
