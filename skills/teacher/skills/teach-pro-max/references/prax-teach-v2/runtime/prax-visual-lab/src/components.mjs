import { createSession, exportReceipt, importReceipt, nextHint, transition, deleteReceipt } from "./core.mjs";

function element(name, attributes = {}, ...children) {
  const node = document.createElement(name);
  for (const [attribute, value] of Object.entries(attributes)) {
    if (value === true) node.setAttribute(attribute, "");
    else if (value !== false && value != null) node.setAttribute(attribute, String(value));
  }
  node.append(...children.flat().filter((child) => child != null));
  return node;
}

function shell(host, content) {
  const stylesheet = element("link", {
    rel: "stylesheet",
    "data-prax-style": "",
    href: new URL("./components.css", import.meta.url),
  });
  host.shadowRoot.replaceChildren(stylesheet, content);
}

function button(label, action) {
  return element("button", { type: "button", "data-action": action }, label);
}

export class PraxStateStepper extends HTMLElement {
  set lesson(value) { this._lesson = value; this._session = this._session || createSession(value); this.render(); }
  set session(value) { this._session = value; this.render(); }
  get session() { return this._session; }
  connectedCallback() { if (!this.shadowRoot) this.attachShadow({ mode: "open" }); this.render(); }
  render() {
    if (!this.shadowRoot || !this._lesson) return;
    const state = this._lesson.states[this._session.state_index];
    const previous = button("Previous", "previous");
    const next = button("Next", "next");
    const reset = button("Reset", "reset");
    for (const control of [previous, next, reset]) control.addEventListener("click", () => this.act(control.dataset.action));
    const select = element("select");
    this._lesson.states.forEach((item, index) => {
      const option = element("option", { value: index }, item.label);
      option.selected = index === this._session.state_index;
      select.append(option);
    });
    select.addEventListener("change", (event) => {
      const state = this._lesson.states[Number(event.target.value)];
      this._session = transition(this._session, this._lesson, `jump:${state.id}`);
      this.render();
      this.dispatchEvent(new CustomEvent("statechange", { detail: this._session }));
    });
    shell(this, element("section", { "aria-labelledby": "stepper-title" },
      element("h2", { id: "stepper-title" }, state.label),
      element("p", {}, state.content),
      element("p", { role: "status", "aria-live": "polite" }, `State ${this._session.state_index + 1} of ${this._lesson.states.length}`),
      previous, next, reset, element("label", {}, "Jump to ", select),
    ));
  }
  act(action) { this._session = transition(this._session, this._lesson, action); this.render(); this.dispatchEvent(new CustomEvent("statechange", { detail: this._session })); }
}

export class PraxParameterLab extends HTMLElement {
  connectedCallback() { if (!this.shadowRoot) this.attachShadow({ mode: "open" }); this.min = Number(this.getAttribute("min") ?? 0); this.max = Number(this.getAttribute("max") ?? 1); this.value = Number(this.getAttribute("value") ?? this.min); this.render(); }
  render() {
    const input = element("input", { id: "parameter", type: "range", min: this.min, max: this.max, step: "any", value: this.value });
    const output = element("output", { id: "value", for: "parameter" }, String(this.value));
    const reset = button("Reset", "reset");
    input.addEventListener("input", () => { this.value = Number(input.value); output.value = String(this.value); this.dispatchEvent(new CustomEvent("parameterchange", { detail: this.value })); });
    reset.addEventListener("click", () => { input.value = String(this.min); this.value = this.min; output.value = String(this.min); this.dispatchEvent(new CustomEvent("parameterchange", { detail: this.value })); });
    shell(this, element("div", {},
      element("label", { for: "parameter" }, this.getAttribute("label") || "Parameter"),
      input, output, reset,
    ));
  }
}

export class PraxCompareViews extends HTMLElement {
  set views(value) { this._views = value; this.render(); }
  connectedCallback() { if (!this.shadowRoot) this.attachShadow({ mode: "open" }); this.render(); }
  render() {
    if (!this.shadowRoot) return;
    const views = this._views || { symbolic: "No state", numerical: "No state", spatial: "No state" };
    const body = element("tbody");
    for (const [key, value] of Object.entries(views)) body.append(element("tr", {}, element("th", { scope: "row" }, key), element("td", {}, String(value))));
    shell(this, element("section", { "aria-labelledby": "compare-title" },
      element("h2", { id: "compare-title" }, "Compare representations"),
      element("table", {},
        element("caption", {}, "All views describe the same state"),
        element("thead", {}, element("tr", {}, element("th", {}, "View"), element("th", {}, "Value"))),
        body,
      ),
    ));
  }
}

export class PraxHintEngine extends HTMLElement {
  set lesson(value) { this._lesson = value; this._session = this._session || { highest_hint_level: 0 }; this.render(); }
  set session(value) { this._session = value; this.render(); }
  connectedCallback() { if (!this.shadowRoot) this.attachShadow({ mode: "open" }); this.render(); }
  render() {
    if (!this.shadowRoot) return;
    const control = button("Show next hint", "hint");
    if (this._lesson) control.addEventListener("click", () => { this._session = nextHint(this._session, this._lesson); this.render(); this.dispatchEvent(new CustomEvent("hint", { detail: this._session })); });
    shell(this, element("section", { "aria-labelledby": "hint-title" },
      element("h2", { id: "hint-title" }, "Ordered hint"),
      element("p", {}, String(this._session?.hint || "No hint shown. Attempt first.")),
      control,
    ));
  }
}

export class PraxReceiptPanel extends HTMLElement {
  set lesson(value) { this._lesson = value; this._session = this._session || createSession(value); this.render(); }
  set session(value) { this._session = value; this.render(); }
  connectedCallback() { if (!this.shadowRoot) this.attachShadow({ mode: "open" }); this.render(); }
  render() {
    if (!this.shadowRoot || !this._lesson) return;
    const area = element("textarea", { "aria-label": "Receipt JSON", rows: 10, cols: 60 });
    area.value = exportReceipt(this._session, this._lesson);
    const status = element("p", { role: "status", "aria-live": "polite" });
    const copy = button("Copy", "copy");
    const download = button("Download", "download");
    const importButton = button("Import", "import");
    const deleteButton = button("Delete local receipt", "delete");
    copy.addEventListener("click", async () => { if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(area.value); status.textContent = "Copied only after your action."; });
    download.addEventListener("click", () => { const blob = new Blob([area.value], { type: "application/json" }); const anchor = document.createElement("a"); anchor.href = URL.createObjectURL(blob); anchor.download = `${this._lesson.lesson_id}-receipt.json`; anchor.click(); URL.revokeObjectURL(anchor.href); status.textContent = "Downloaded locally."; });
    importButton.addEventListener("click", () => { try { const receipt = importReceipt(area.value, this._lesson); this._session = receipt; status.textContent = "Imported and validated."; this.dispatchEvent(new CustomEvent("receiptimport", { detail: receipt })); } catch (error) { status.textContent = `Import rejected: ${error.message}`; } });
    deleteButton.addEventListener("click", () => { deleteReceipt(globalThis.localStorage, `prax:${this._lesson.lesson_id}`); area.value = ""; status.textContent = "Local receipt deleted."; });
    shell(this, element("section", { "aria-labelledby": "receipt-title" },
      element("h2", { id: "receipt-title" }, "Local learning receipt"),
      element("p", {}, "This stays on this device until you choose to copy or download it."),
      area, element("br"), copy, download, importButton, deleteButton, status,
    ));
  }
}

export function registerComponents() { if (!globalThis.customElements) return; for (const [name, component] of [["prax-state-stepper", PraxStateStepper], ["prax-parameter-lab", PraxParameterLab], ["prax-compare-views", PraxCompareViews], ["prax-hint-engine", PraxHintEngine], ["prax-receipt-panel", PraxReceiptPanel]]) if (!customElements.get(name)) customElements.define(name, component); }
