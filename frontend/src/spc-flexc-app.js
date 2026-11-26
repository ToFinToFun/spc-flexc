// SPC FlexC app: every SPC card in one place with tabs, as a dashboard card
// (spc-flexc-app-card) and as the "SPC" page in Home Assistant's sidebar
// (spc-flexc-panel, registered by the integration). Each tab is the same card
// that can also be used on its own.

// Few tabs, the daily ones first. Översikt holds what most people do: set and
// unset areas, open and lock doors, door status and the zones that are
// active now. Each tab is one or more of the cards that can also be used on
// their own; the overview card is shown with one fixed view and no tab row
// of its own, so the app has only one row of tabs.
const SPC_APP_TABS = [
  { key: "overview", sv: "Översikt", en: "Overview", cards: [
    ["spc-flexc-card", { view: "system", hide_header: true }],
    ["spc-flexc-doors-card", {}],
    ["spc-flexc-zones-card", { compact: true }],
  ] },
  { key: "zones", sv: "Sektioner", en: "Zones", cards: [["spc-flexc-zones-card", { title: " " }]] },
  { key: "users", sv: "Användare", en: "Users", cards: [
    ["spc-flexc-users-card", {}],
    ["spc-flexc-profiles-card", {}],
  ] },
  { key: "calendars", sv: "Kalendrar", en: "Calendars", cards: [["spc-flexc-calendars-card", { title: " " }]] },
  { key: "logs", sv: "Loggar", en: "Logs", cards: [
    ["spc-flexc-activity-card", {}],
    ["spc-flexc-logs-card", {}],
  ] },
  { key: "system", sv: "System", en: "System", cards: [
    ["spc-flexc-system-card", {}],
    ["spc-flexc-card", { view: "outputs", hide_header: true }],
    ["spc-flexc-card", { view: "technical", hide_header: true }],
  ] },
];
// Tabs of earlier versions, kept in browsers, and where they are now.
const SPC_APP_OLD_TABS = { home: "overview", doors: "overview", profiles: "users", activity: "logs" };

// Programtekniker (engineer) login and engineer mode, like the web page:
// log in and out, choose whether the password is remembered, enter and
// leave engineer mode, and a warning on every tab while it is on.
const SPC_ENGINEER_TEXT = {
  sv: {
    engineer: "Programtekniker", login: "Logga in", logout: "Logga ut", cancel: "Avbryt",
    username: "Användarnamn", password: "Lösenord",
    remember: "Kom ihåg inloggningen (sparas okrypterat i Home Assistants konfiguration)",
    loggedIn: "Programtekniker {id} inloggad", remembered: "sparad", idle: "loggas ut efter {min} min utan användning",
    mode: "Installatörsläge", enter: "Gå in i installatörsläge", leave: "Lämna installatörsläge",
    banner: "Installatörsläge: centralen larmar inte och kan inte tillkopplas.",
    bannerNoLogin: "Logga in som programtekniker för att lämna det.",
    confirmEnter: "Gå in i installatörsläge? Centralen larmar inte och kan inte tillkopplas förrän du lämnar det.",
    leaveFirst: "Lämna installatörsläget innan du loggar ut.",
  },
  en: {
    engineer: "Engineer", login: "Log in", logout: "Log out", cancel: "Cancel",
    username: "Username", password: "Password",
    remember: "Remember the login (stored unencrypted in Home Assistant's configuration)",
    loggedIn: "Engineer {id} logged in", remembered: "remembered", idle: "logged out after {min} min unused",
    mode: "Engineer mode", enter: "Enter engineer mode", leave: "Leave engineer mode",
    banner: "Engineer mode: the panel does not alarm and cannot be set.",
    bannerNoLogin: "Log in as engineer to leave it.",
    confirmEnter: "Enter engineer mode? The panel does not alarm and cannot be set until you leave it.",
    leaveFirst: "Leave engineer mode before logging out.",
  },
};

class SpcFlexCApp extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = { ...(config || {}) };
    this._cards = {};
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    const previous = this._hass?.states?.[this._capabilitiesEntity()];
    this._hass = hass;
    this._lang = spcLanguage(hass);
    if (first || !this.shadowRoot) {
      this._render();
    } else {
      for (const card of this._current || []) card.hass = hass;
      if (previous !== hass.states[this._capabilitiesEntity()] && !this._loginOpen) this._renderEngineer();
    }
  }

  _capabilitiesEntity() {
    return this._config?.capabilities_entity || "sensor.spc_capabilities";
  }

  _e(key, values = {}) {
    let text = (SPC_ENGINEER_TEXT[this._lang] || SPC_ENGINEER_TEXT.en)[key] ?? key;
    for (const [name, value] of Object.entries(values)) text = text.replaceAll(`{${name}}`, value);
    return text;
  }

  async _engineerCall(service, data = {}) {
    this._engineerError = "";
    this._engineerBusy = true;
    this._renderEngineer();
    try {
      await this._hass.callService("spc_flexc", service, data);
      return true;
    } catch (err) {
      this._engineerError = String(err?.message || err);
      return false;
    } finally {
      this._engineerBusy = false;
      this._renderEngineer();
    }
  }

  // The engineer line under the tabs and, in engineer mode, a warning.
  _renderEngineer() {
    const box = this._engineerBox;
    if (!box || !this._hass) return;
    box.textContent = "";
    const attrs = this._hass.states[this._capabilitiesEntity()]?.attributes || {};
    const session = attrs.engineer_login || { logged_in: false };
    const mode = attrs.engineer_mode === true;
    const busy = this._engineerBusy;
    if (mode) {
      box.append(spcEl("div", { className: "eng-banner", role: "alert" }, [
        spcEl("ha-icon", { icon: "mdi:account-hard-hat" }),
        spcEl("span", {}, [this._e("banner"), session.logged_in ? "" : ` ${this._e("bannerNoLogin")}`]),
        session.logged_in ? spcEl("button", { disabled: busy,
          onclick: () => this._engineerCall("set_engineer_mode", { enter: false }) }, [this._e("leave")]) : null,
      ]));
    }
    const line = spcEl("div", { className: "eng-line" });
    if (session.logged_in) {
      const how = session.remembered ? this._e("remembered") : this._e("idle", { min: Math.round((session.idle_logout || 1800) / 60) });
      const toggle = spcEl("input", { type: "checkbox", checked: mode, disabled: busy, onchange: () => {
        if (toggle.checked && !confirm(this._e("confirmEnter"))) {
          toggle.checked = false;
          return;
        }
        this._engineerCall("set_engineer_mode", { enter: toggle.checked });
      } });
      line.append(
        spcEl("span", {}, [spcEl("ha-icon", { icon: "mdi:account-hard-hat" }), ` ${this._e("loggedIn", { id: session.user_id ?? "" })} (${how})`]),
        spcEl("label", { className: "eng-toggle" }, [toggle, this._e("mode")]),
        spcEl("button", { disabled: busy || mode, title: mode ? this._e("leaveFirst") : "",
          onclick: () => this._engineerCall("engineer_logout") }, [this._e("logout")]),
      );
    } else if (this._loginOpen) {
      const user = spcEl("input", { type: "text", autocomplete: "off", placeholder: this._e("username") });
      const password = spcEl("input", { type: "password", autocomplete: "new-password", placeholder: this._e("password") });
      const remember = spcEl("input", { type: "checkbox" });
      const submit = async () => {
        if (!user.value || !password.value) return;
        const ok = await this._engineerCall("engineer_login", {
          username: user.value, password: password.value, remember: remember.checked,
        });
        password.value = "";
        if (ok) {
          this._loginOpen = false;
          this._renderEngineer();
        }
      };
      password.addEventListener("keydown", (event) => { if (event.key === "Enter") submit(); });
      line.append(
        spcEl("strong", {}, [this._e("engineer")]), user, password,
        spcEl("label", { className: "eng-toggle" }, [remember, this._e("remember")]),
        spcEl("button", { className: "primary", disabled: busy, onclick: submit }, [this._e("login")]),
        spcEl("button", { onclick: () => { this._loginOpen = false; this._engineerError = ""; this._renderEngineer(); } }, [this._e("cancel")]),
      );
    } else {
      line.append(spcEl("button", { className: "link", onclick: () => { this._loginOpen = true; this._renderEngineer(); } }, [
        spcEl("ha-icon", { icon: "mdi:account-hard-hat" }), ` ${this._e("engineer")}: ${this._e("login")}`,
      ]));
    }
    box.append(line);
    if (this._engineerError) box.append(spcEl("div", { className: "eng-error" }, [this._engineerError]));
  }

  getCardSize() {
    return 10;
  }

  _tab() {
    if (!this._active) {
      try {
        this._active = localStorage.getItem("spc-flexc-app-tab") || "overview";
      } catch (err) {
        this._active = "overview";
      }
      this._active = SPC_APP_OLD_TABS[this._active] || this._active;
    }
    return SPC_APP_TABS.find((t) => t.key === this._active) || SPC_APP_TABS[0];
  }

  _alarmEntity() {
    if (this._config?.entity) return this._config.entity;
    const states = this._hass?.states || {};
    return states["alarm_control_panel.spc_alarm"] ? "alarm_control_panel.spc_alarm"
      : Object.keys(states).find((id) => id.startsWith("alarm_control_panel.spc_"));
  }

  // The tab's cards, made once and kept, so switching tabs is quick and a
  // card keeps what was typed in it.
  _cardsOf(tab) {
    if (!this._cards[tab.key]) {
      const box = spcEl("div", { className: "stack" });
      const cards = [];
      for (const [type, extra] of tab.cards) {
        const element = document.createElement(type);
        const config = type === "spc-flexc-card" ? { entity: this._alarmEntity(), ...extra } : extra;
        try {
          element.setConfig(config);
          cards.push(element);
          box.append(element);
        } catch (err) {
          box.append(spcEl("div", {}, [String(err?.message || err)]));
        }
      }
      this._cards[tab.key] = { box, cards };
    }
    return this._cards[tab.key];
  }

  _render() {
    if (!this._config || !this._hass) {
      return;
    }
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    const root = this.shadowRoot;
    root.textContent = "";
    const style = document.createElement("style");
    style.textContent = `
      :host { display: block; }
      .tabs { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 8px; }
      @media (max-width: 600px) {
        .tabs { flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; padding-bottom: 4px; }
        .tabs button { padding: 6px 10px; white-space: nowrap; flex: none; }
        .tabs select { flex: none; }
      }
      .tabs button { font: inherit; padding: 8px 14px; border-radius: 8px; cursor: pointer;
        border: 1px solid var(--divider-color); background: var(--card-background-color);
        color: var(--primary-text-color); }
      .tabs button.on { background: var(--primary-color); color: var(--text-primary-color, #fff);
        border-color: var(--primary-color); }
      .tabs select { margin-left: auto; font: inherit; padding: 6px; border-radius: 8px;
        border: 1px solid var(--divider-color); background: var(--card-background-color);
        color: var(--primary-text-color); }
      .stack { display: grid; gap: 12px; }
      .engineer { display: grid; gap: 6px; margin: 0 0 8px; }
      .eng-banner { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 10px 12px;
        border-radius: 8px; background: var(--error-color, #db4437); color: #fff; font-weight: 500; }
      .eng-banner button { margin-left: auto; }
      .eng-line { display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
        color: var(--secondary-text-color); font-size: 0.9em; }
      .eng-line input[type=text], .eng-line input[type=password] { font: inherit; padding: 6px; border-radius: 6px;
        border: 1px solid var(--divider-color); background: var(--card-background-color);
        color: var(--primary-text-color); min-width: 0; flex: 1 1 140px; }
      .eng-toggle { display: flex; align-items: center; gap: 4px; }
      .engineer button { font: inherit; padding: 6px 12px; border-radius: 6px; cursor: pointer;
        border: 1px solid var(--divider-color); background: var(--card-background-color);
        color: var(--primary-text-color); }
      .engineer button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff);
        border-color: var(--primary-color); }
      .engineer button.link { border: none; background: none; padding: 2px 0; color: var(--secondary-text-color); }
      .engineer button:disabled { opacity: 0.5; cursor: default; }
      .eng-error { color: var(--error-color, #db4437); font-size: 0.9em; }
      ha-icon { --mdc-icon-size: 18px; }
    `;
    const tabs = document.createElement("div");
    tabs.className = "tabs";
    const active = this._tab();
    for (const tab of SPC_APP_TABS) {
      const button = document.createElement("button");
      button.textContent = tab[this._lang] || tab.en;
      button.className = tab.key === active.key ? "on" : "";
      button.addEventListener("click", () => {
        this._active = tab.key;
        try {
          localStorage.setItem("spc-flexc-app-tab", tab.key);
        } catch (err) {
          // Remembering the tab is only a convenience.
        }
        this._render();
      });
      tabs.append(button);
    }
    const language = document.createElement("select");
    language.title = this._lang === "sv" ? "Språk" : "Language";
    const auto = this._lang === "sv" ? "Automatiskt (Home Assistant)" : "Automatic (Home Assistant)";
    for (const [value, label] of [["auto", auto], ...Object.entries(SPC_LANGUAGES)]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = value === spcLanguageChoice();
      language.append(option);
    }
    language.addEventListener("change", () => {
      spcSetLanguage(language.value);
      this._lang = spcLanguage(this._hass);
      this._render();
    });
    tabs.append(language);
    const { box, cards } = this._cardsOf(active);
    this._current = cards;
    for (const card of cards) card.hass = this._hass;
    this._engineerBox = spcEl("div", { className: "engineer" });
    this._renderEngineer();
    root.append(style, tabs, this._engineerBox, box);
  }
}

// The sidebar page: a toolbar like Home Assistant's own pages and the app.
class SpcFlexCPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._app) {
      this._build();
    }
    this._app.hass = hass;
    if (this._menu) this._menu.hass = hass;
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  set panel(panel) {
    this._panel = panel;
  }

  _build() {
    this.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = `
      :host { display: block; background: var(--primary-background-color); min-height: 100vh; }
      .toolbar { display: flex; align-items: center; gap: 8px; height: 56px; padding: 0 12px;
        background: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, var(--text-primary-color, #fff)); font-size: 20px; }
      .content { padding: 16px; max-width: 1200px; margin: 0 auto; }
      @media (max-width: 600px) { .content { padding: 8px; } }
    `;
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    this._menu = document.createElement("ha-menu-button");
    this._menu.narrow = this._narrow;
    const title = document.createElement("div");
    title.textContent = this._panel?.title || "SPC";
    toolbar.append(this._menu, title);
    const content = document.createElement("div");
    content.className = "content";
    this._app = document.createElement("spc-flexc-app-card");
    this._app.setConfig({});
    content.append(this._app);
    this.shadowRoot.append(style, toolbar, content);
  }
}

if (!customElements.get("spc-flexc-panel")) {
  customElements.define("spc-flexc-panel", SpcFlexCPanel);
}
spcDefineCard(
  "spc-flexc-app-card",
  SpcFlexCApp,
  "SPC FlexC App",
  "Every SPC card in one place with tabs: overview (areas, doors, active zones), zones, users, calendars, logs, system."
);
