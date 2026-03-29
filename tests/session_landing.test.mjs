import test from "node:test";
import assert from "node:assert/strict";
import {
  applyLandingState,
  shouldResumeLastSession,
} from "../webui/js/session-landing.mjs";

function createStorage(initial = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return map.has(key) ? map.get(key) : null;
    },
    setItem(key, value) {
      map.set(key, String(value));
    },
    removeItem(key) {
      map.delete(key);
    },
    snapshot() {
      return Object.fromEntries(map.entries());
    },
  };
}

test("landing policy disables resume by default", () => {
  assert.equal(shouldResumeLastSession(false), false);
  assert.equal(shouldResumeLastSession(undefined), false);
  assert.equal(shouldResumeLastSession(true), true);
});

test("applyLandingState clears selected chat and forces welcome flag", () => {
  const session = createStorage();
  const local = createStorage({
    lastSelectedChat: "abc123",
    lastSelectedTask: "task456",
    korev_show_welcome: "false",
  });

  applyLandingState(session, local);
  const snap = local.snapshot();

  assert.equal(session.getItem("hasVisited"), "true");
  assert.equal(Object.hasOwn(snap, "lastSelectedChat"), false);
  assert.equal(Object.hasOwn(snap, "lastSelectedTask"), false);
  assert.equal(local.getItem("korev_show_welcome"), "true");
});
