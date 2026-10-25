/* For reviewed authored lessons. No eval, remote resources or browser storage. */
(() => {
  "use strict";
  if (window.__readingThemes) return;
  const root = document.documentElement;
  const data = JSON.parse(document.getElementById("reading-themes-data").textContent);
  const palettes = Object.freeze(data.palettes.map(p => Object.freeze({ ...p })));
  const byId = new Map(palettes.map(p => [p.id, p]));
  let current = null;
  let dialog, launcher, status;
  const radios = new Map();
  const localLink = anchor => {
    const raw = anchor.getAttribute("href");
    if (!raw || raw.startsWith("#") || anchor.hasAttribute("download")) return null;
    try {
      const url = new URL(raw, document.baseURI);
      if (!["http:", "https:", "file:"].includes(url.protocol) ||
          url.protocol !== location.protocol || url.origin !== location.origin ||
          !/\.html?$/i.test(url.pathname)) return null;
      return url;
    } catch { return null; }
  };
  const updateLink = anchor => {
    const url = localLink(anchor);
    if (!url) return;
    if (current) url.searchParams.set("theme", current);
    else url.searchParams.delete("theme");
    // Absolute URLs also work when the authored page uses a <base> element.
    if (anchor.getAttribute("href") !== url.href) anchor.setAttribute("href", url.href);
  };
  const updateLinks = () => document.querySelectorAll("a[href]").forEach(updateLink);
  const apply = (id, { updateURL = true } = {}) => {
    if (id === "original" || id === null) id = null;
    else if (!byId.has(id)) throw new RangeError("Unknown reading theme");
    current = id;
    if (id) root.dataset.readingTheme = id;
    else delete root.dataset.readingTheme;
    if (updateURL) {
      const url = new URL(location.href);
      if (id) url.searchParams.set("theme", id);
      else url.searchParams.delete("theme");
      try { history.replaceState(history.state, "", url); }
      catch { /* A restrictive embed may deny URL changes; never loosen it. */ }
    }
    radios.forEach((input, key) => { input.checked = key === id; });
    if (status) status.textContent = id ? `${byId.get(id).name} selected.` : "Original appearance selected.";
    if (launcher) launcher.setAttribute("aria-label", `Reading theme: ${id ? byId.get(id).name : "Original"}`);
    updateLinks();
    return current;
  };
  Object.defineProperty(window, "__readingThemes", {
    value: Object.freeze({ palettes, get current() { return current; }, apply }),
    writable: false, configurable: false
  });
  // Runs in <head>, before lesson/board setup. CSS owns custom tokens separately
  // from data-board, so later engine initialization cannot reset the selection.
  const initial = new URL(location.href).searchParams.get("theme");
  if (byId.has(initial)) apply(initial, { updateURL: false });
  const make = (tag, attrs = {}, text) => {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const init = () => {
    launcher = make("button", { type: "button", class: "rt-launch", "aria-haspopup": "dialog", "aria-controls": "reading-themes-dialog" }, "Reading theme");
    dialog = make("dialog", { id: "reading-themes-dialog", class: "rt-dialog", "aria-labelledby": "reading-themes-title", "aria-describedby": "reading-themes-note" });
    dialog.append(make("h2", { id: "reading-themes-title" }, "Reading themes"));
    dialog.append(make("p", { id: "reading-themes-note" }, "Change page and inline figure colors. Rendered videos and images keep their original colors."));
    for (const group of ["Dark", "Night"]) {
      const field = make("fieldset");
      field.append(make("legend", {}, group));
      const cards = make("div", { class: "rt-cards" });
      for (const palette of palettes.filter(p => p.group === group)) {
        const label = make("label", { class: "rt-card" });
        label.style.setProperty("--rt-preview-bg", palette.bg);
        label.style.setProperty("--rt-preview-ink", palette.ink);
        label.style.setProperty("--rt-preview-border", palette.border);
        const input = make("input", { type: "radio", name: "reading-theme", value: palette.id });
        input.checked = current === palette.id;
        input.addEventListener("change", () => { if (input.checked) apply(palette.id); });
        radios.set(palette.id, input);
        label.append(input, make("span", { class: "rt-aa", "aria-hidden": "true" }, "Aa"), make("span", { class: "rt-name" }, palette.name));
        cards.append(label);
      }
      field.append(cards);
      dialog.append(field);
    }
    status = make("p", { role: "status", "aria-live": "polite" });
    status.textContent = current ? `${byId.get(current).name} selected.` : "Original appearance selected.";
    const actions = make("div", { class: "rt-actions" });
    const reset = make("button", { type: "button" }, "Original");
    reset.addEventListener("click", () => apply(null));
    const done = make("button", { type: "button" }, "Done");
    done.addEventListener("click", () => dialog.close());
    actions.append(reset, done);
    dialog.append(status, actions);
    document.body.append(launcher, dialog);
    launcher.setAttribute("aria-label", `Reading theme: ${current ? byId.get(current).name : "Original"}`);
    launcher.addEventListener("click", () => {
      dialog.showModal();
      (radios.get(current) || reset).focus();
    });
    dialog.addEventListener("close", () => launcher.focus());
    updateLinks();
    // Lesson engines can create course navigation after this initializer.
    new MutationObserver(records => {
      for (const record of records) {
        if (record.type === "attributes") updateLink(record.target);
        for (const node of record.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;
          if (node.matches("a[href]")) updateLink(node);
          node.querySelectorAll("a[href]").forEach(updateLink);
        }
      }
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["href"] });
    document.addEventListener("click", event => {
      const anchor = event.target.closest?.("a[href]");
      if (anchor) updateLink(anchor);
    }, true);
    window.addEventListener("popstate", () => {
      const id = new URL(location.href).searchParams.get("theme");
      apply(byId.has(id) ? id : null, { updateURL: false });
    });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
