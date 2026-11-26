// Shared base for the SPC FlexC management cards (users, calendars, profiles,
// logs, system) and the tabbed SPC app: one look, one way to call the
// integration's actions and show their result.

// Language of the SPC cards: the choice in the SPC app's language menu (kept
// in this browser), otherwise Home Assistant's language. Swedish and English
// for now; more languages can be added to each card's texts.
const SPC_LANGUAGE_KEY = "spc-flexc-language";
const SPC_LANGUAGES = { sv: "Svenska", en: "English" };

function spcLanguageChoice() {
  try {
    return localStorage.getItem(SPC_LANGUAGE_KEY) || "auto";
  } catch (err) {
    return "auto";
  }
}

function spcLanguage(hass) {
  const choice = spcLanguageChoice();
  if (choice in SPC_LANGUAGES) return choice;
  return String(hass?.language || hass?.locale?.language || "en").startsWith("sv") ? "sv" : "en";
}

function spcSetLanguage(choice) {
  try {
    if (choice === "auto") localStorage.removeItem(SPC_LANGUAGE_KEY);
    else localStorage.setItem(SPC_LANGUAGE_KEY, choice);
  } catch (err) {
    // Remembering the language is only a convenience.
  }
  window.dispatchEvent(new CustomEvent("spc-flexc-language-changed"));
}

function spcEl(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else if (value !== undefined) {
      node[key] = value;
    }
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

const SPC_UI_STYLE = `
  :host { display: block; }
  ha-card { padding: 12px 16px; container-type: inline-size; }
  .header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px;
    font-size: 1.2em; font-weight: 500; margin-bottom: 8px; }
  .header button { font-size: 0.75em; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
  th { text-align: left; color: var(--secondary-text-color); font-weight: 500;
    border-bottom: 1px solid var(--divider-color); padding: 4px; }
  td { border-bottom: 1px solid var(--divider-color); padding: 6px 4px; vertical-align: top; }
  tr.row { cursor: pointer; }
  tr.row:hover, tr.row.selected { background: var(--secondary-background-color); }
  button { font: inherit; padding: 6px 12px; border-radius: 6px; cursor: pointer;
    border: 1px solid var(--divider-color); background: var(--card-background-color);
    color: var(--primary-text-color); }
  button:disabled { opacity: 0.5; cursor: default; }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff);
    border-color: var(--primary-color); }
  button.danger { color: var(--error-color, #db4437); }
  button.small { padding: 2px 6px; font-size: 0.85em; }
  .form { border: 1px solid var(--divider-color); border-radius: 8px; padding: 12px;
    margin-top: 12px; display: grid; gap: 10px; }
  .form h3 { margin: 0; font-size: 1.05em; }
  .field { display: grid; gap: 4px; }
  .field > span { color: var(--secondary-text-color); font-size: 0.85em; }
  input, select, textarea { font: inherit; padding: 6px; border-radius: 6px;
    border: 1px solid var(--divider-color); background: var(--card-background-color);
    color: var(--primary-text-color); }
  .checks { display: flex; flex-wrap: wrap; gap: 6px 14px; }
  .checks label { display: flex; align-items: center; gap: 4px; }
  .rowline { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .note { color: var(--secondary-text-color); font-size: 0.85em; }
  .error { color: var(--error-color, #db4437); margin: 4px 0; }
  .ok { color: var(--success-color, #43a047); margin: 4px 0; }
  .scroll { max-height: 520px; overflow-y: auto; }
  /* Narrow screens (phones): each table row becomes a block whose cells
     wrap side by side, each with its column name above the value. */
  @container (max-width: 600px) {
    ha-card { padding: 10px 12px; }
    table.stack, table.stack tbody { display: block; }
    table.stack tr:has(> th) { display: none; }
    table.stack tr { display: flex; flex-wrap: wrap; gap: 4px 16px; padding: 8px 2px;
      border-bottom: 1px solid var(--divider-color); }
    table.stack td { display: block; border: none; padding: 0; min-width: 0; overflow-wrap: anywhere; }
    table.stack td[data-label]::before { content: attr(data-label); display: block;
      color: var(--secondary-text-color); font-size: 0.75em; }
    table.stack td:first-child { flex-basis: 100%; font-weight: 500; }
    table.stack td:first-child::before { display: none; }
    .form { padding: 10px; }
    input, select, textarea { max-width: 100%; box-sizing: border-box; }
  }
`;

// Label each cell with its column name so narrow screens can stack rows.
function spcStackTables(root) {
  for (const table of root.querySelectorAll("table")) {
    const head = table.querySelector("tr");
    const names = head ? [...head.children].map((cell) => (cell.tagName === "TH" ? cell.textContent : "")) : [];
    if (!names.some(Boolean)) continue;
    table.classList.add("stack");
    for (const row of table.querySelectorAll("tr")) {
      [...row.children].forEach((cell, index) => {
        if (cell.tagName === "TD" && names[index]) cell.dataset.label = names[index];
      });
    }
  }
}

class SpcFlexCBaseCard extends HTMLElement {
  // Subclasses set: static texts = { sv: {...}, en: {...} }, defaults, entities().
  static get texts() {
    return { sv: {}, en: {} };
  }

  static get defaults() {
    return {};
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = { ...this.constructor.defaults, ...(config || {}) };
    this._render();
  }

  // Entities whose change redraws the card (unless a form is open).
  watched() {
    return [];
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    const language = spcLanguage(hass);
    const languageChanged = language !== this._lang;
    this._lang = language;
    const changed = languageChanged || !previous || this.watched().some((id) => previous.states[id] !== hass.states[id]);
    if (changed && !this._editing) {
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    this._onLanguage ||= () => {
      if (this._hass) this.hass = this._hass;
    };
    window.addEventListener("spc-flexc-language-changed", this._onLanguage);
  }

  disconnectedCallback() {
    window.removeEventListener("spc-flexc-language-changed", this._onLanguage);
  }

  getCardSize() {
    return 6;
  }

  _t(key, values = {}) {
    const texts = this.constructor.texts;
    let text = (texts[this._lang] || texts.en)[key] ?? SPC_UI_COMMON[this._lang]?.[key] ?? SPC_UI_COMMON.en[key] ?? key;
    if (typeof text === "string") {
      for (const [name, value] of Object.entries(values)) {
        text = text.replaceAll(`{${name}}`, value);
      }
    }
    return text;
  }

  _state(entity) {
    return this._hass?.states[entity];
  }

  _attr(entity, name, fallback) {
    return this._hass?.states[entity]?.attributes?.[name] ?? fallback;
  }

  async _call(service, data, { response = false } = {}) {
    this._error = "";
    this._message = "";
    this._busy = true;
    this._render();
    try {
      if (response) {
        const result = await this._hass.callWS({
          type: "call_service", domain: "spc_flexc", service,
          service_data: data, return_response: true,
        });
        return result?.response ?? {};
      }
      await this._hass.callService("spc_flexc", service, data);
      this._message = this._t("done");
      return true;
    } catch (err) {
      this._error = String(err?.message || err);
      return false;
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _open(editing) {
    this._editing = editing;
    this._error = "";
    this._message = "";
    this._render();
  }

  _close() {
    this._editing = null;
    this._render();
  }

  // Draw the frame; subclasses fill it in body(card).
  _render() {
    if (!this._config || !this._hass) {
      return;
    }
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    const root = this.shadowRoot;
    root.textContent = "";
    const style = spcEl("style", { textContent: SPC_UI_STYLE + (this.style_extra?.() || "") });
    const card = spcEl("ha-card");
    root.append(style, card);
    const header = spcEl("div", { className: "header" }, [this._config.title || this._t("title")]);
    const actions = this.headerActions?.();
    if (actions) header.append(spcEl("div", { className: "rowline" }, actions));
    if (!this._config.hide_header) card.append(header);
    if (this._error) {
      card.append(spcEl("div", { className: "error" }, [this._error]));
    } else if (this._message) {
      card.append(spcEl("div", { className: "ok" }, [this._message]));
    }
    this.body(card);
    spcStackTables(card);
  }

  body() {}

  _field(label, ...children) {
    return spcEl("div", { className: "field" }, [spcEl("span", {}, [label]), ...children]);
  }

  _closeButton() {
    return spcEl("button", { onclick: () => this._close() }, [this._t("close")]);
  }

  _confirmButton(label, question, action) {
    return spcEl("button", { className: "danger", disabled: this._busy, onclick: async () => {
      if (confirm(question) && (await action())) this._close();
    } }, [label]);
  }
}

const SPC_UI_COMMON = {
  sv: { done: "Klart", close: "Stäng", save: "Spara", add: "Lägg till", delete: "Ta bort",
    none: "–", missing: "Sensorn {entity} saknas.", name: "Namn", from: "Från", until: "Till" },
  en: { done: "Done", close: "Close", save: "Save", add: "Add", delete: "Delete",
    none: "–", missing: "The sensor {entity} is missing.", name: "Name", from: "From", until: "Until" },
};

// SPC FlexC entities of a domain that carry an attribute (e.g. area_id).
function spcEntities(hass, domain, attribute) {
  const states = hass?.states || {};
  const registry = hass?.entities;
  return Object.keys(states)
    .filter((id) => id.startsWith(`${domain}.`) && states[id].attributes?.[attribute] !== undefined)
    .filter((id) => (registry?.[id] ? registry[id].platform === "spc_flexc" : id.includes(".spc_")))
    .map((id) => ({ entity: id, ...states[id].attributes }))
    .sort((a, b) => a[attribute] - b[attribute]);
}

function spcDefineCard(type, cls, name, description) {
  if (!customElements.get(type)) {
    customElements.define(type, cls);
  }
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === type)) {
    window.customCards.push({ type, name, description });
  }
}
