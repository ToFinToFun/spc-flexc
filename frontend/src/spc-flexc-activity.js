// SPC FlexC activity card: one timeline of what Home Assistant sent to the
// panel, what the panel answered, the events it pushed and new lines of its
// system and access logs. One coloured row per entry. Names are shown on
// purpose; the integration never sends PINs or card numbers here.

const SPC_ACTIVITY_SOURCES = {
  ha_command: { color: "#1e88e5", sv: "HA → central", en: "HA → panel" },
  panel_reply: { color: "#43a047", sv: "Centralens svar", en: "Panel answer" },
  panel_event: { color: "#fb8c00", sv: "Händelse", en: "Event" },
  panel_log: { color: "#9e9e9e", sv: "Centralens logg", en: "Panel log" },
};
const SPC_ACTIVITY_ERROR = "#e53935";
const SPC_ACTIVITY_MAX = 500;

const SPC_ACTIVITY_TEXT = {
  sv: { title: "SPC aktivitet", empty: "Ingen aktivitet ännu.", all: "Alla" },
  en: { title: "SPC activity", empty: "No activity yet.", all: "All" },
};

class SpcFlexCActivityCard extends HTMLElement {
  static getStubConfig() {
    return { limit: 100 };
  }

  setConfig(config) {
    this._config = { limit: 100, ...config };
    this._limit = Math.min(Math.max(Number(this._config.limit) || 100, 1), 2000);
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._lang = spcLanguage(hass);
      this._load();
      this._subscribe();
    }
  }

  getCardSize() {
    return 6;
  }

  connectedCallback() {
    this._onLanguage ||= () => {
      if (this._hass) {
        this._lang = spcLanguage(this._hass);
        this._render();
      }
    };
    window.addEventListener("spc-flexc-language-changed", this._onLanguage);
    if (this._hass && !this._unsubscribers) {
      this._subscribe();
    }
  }

  disconnectedCallback() {
    window.removeEventListener("spc-flexc-language-changed", this._onLanguage);
    for (const unsubscribe of this._unsubscribers || []) {
      Promise.resolve(unsubscribe)
        .then((fn) => typeof fn === "function" && fn())
        .catch(() => {});
    }
    this._unsubscribers = null;
  }

  _text(key) {
    return (SPC_ACTIVITY_TEXT[this._lang] || SPC_ACTIVITY_TEXT.en)[key];
  }

  async _load() {
    try {
      const data = {};
      if (this._config?.config_entry_id) {
        data.config_entry_id = this._config.config_entry_id;
      }
      data.limit = this._limit;
      const result = await this._hass.callWS({
        type: "call_service",
        domain: "spc_flexc",
        service: "get_activity",
        service_data: data,
        return_response: true,
      });
      const entries = result?.response?.entries || [];
      this._entries = entries.slice(0, this._limit);
    } catch (err) {
      this._error = String(err?.message || err);
      this._entries = this._entries || [];
    }
    this._render();
  }

  _subscribe() {
    const connection = this._hass?.connection;
    if (!connection?.subscribeEvents) {
      return;
    }
    this._unsubscribers = [
      connection.subscribeEvents(
        (event) => this._add(event.data || {}),
        "spc_flexc_activity"
      ),
      // Panel events are fired once, as spc_flexc_event.
      connection.subscribeEvents(
        (event) => this._add(spcActivityFromPanelEvent(event.data || {}, event.time_fired)),
        "spc_flexc_event"
      ),
    ];
  }

  _add(entry) {
    if (this._config?.config_entry_id && entry.entry_id &&
        entry.entry_id !== this._config.config_entry_id) {
      return;
    }
    this._entries = [entry, ...(this._entries || [])].slice(0, this._limit);
    this._render();
  }

  _render() {
    if (!this._config) {
      return;
    }
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    const root = this.shadowRoot;
    root.textContent = "";
    const style = document.createElement("style");
    style.textContent = `
      ha-card { padding: 12px 0; }
      .header { padding: 0 16px 8px; font-size: 1.2em; font-weight: 500; }
      .filters { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 16px 8px; }
      .chip { border: 1px solid var(--divider-color); border-radius: 12px;
        padding: 2px 10px; cursor: pointer; font-size: 0.85em; background: none;
        color: var(--primary-text-color); }
      .chip.on { background: var(--secondary-background-color); }
      .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 4px; }
      .list { max-height: ${Number(this._config.height) || 480}px; overflow-y: auto; }
      .row { display: grid; grid-template-columns: 70px 1fr; gap: 8px;
        padding: 4px 16px 4px 12px; border-left: 4px solid transparent;
        border-bottom: 1px solid var(--divider-color); font-size: 0.9em; }
      .time { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
      .title { font-weight: 500; }
      .source { color: var(--secondary-text-color); font-size: 0.8em; }
      .empty, .error { padding: 8px 16px; color: var(--secondary-text-color); }
      .error { color: ${SPC_ACTIVITY_ERROR}; }
    `;
    const card = document.createElement("ha-card");
    const header = document.createElement("div");
    header.className = "header";
    header.textContent = this._config.title || this._text("title");
    card.append(header);

    this._hidden ||= new Set();
    const filters = document.createElement("div");
    filters.className = "filters";
    for (const [source, info] of Object.entries(SPC_ACTIVITY_SOURCES)) {
      const chip = document.createElement("button");
      chip.className = `chip${this._hidden.has(source) ? "" : " on"}`;
      const dot = document.createElement("span");
      dot.className = "dot";
      dot.style.background = info.color;
      chip.append(dot, document.createTextNode(info[this._lang] || info.en));
      chip.addEventListener("click", () => {
        if (this._hidden.has(source)) {
          this._hidden.delete(source);
        } else {
          this._hidden.add(source);
        }
        this._render();
      });
      filters.append(chip);
    }
    card.append(filters);

    if (this._error) {
      const error = document.createElement("div");
      error.className = "error";
      error.textContent = this._error;
      card.append(error);
    }
    const list = document.createElement("div");
    list.className = "list";
    const shown = (this._entries || []).filter((entry) => !this._hidden.has(entry.source));
    if (!shown.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = this._text("empty");
      list.append(empty);
    }
    for (const entry of shown.slice(0, SPC_ACTIVITY_MAX)) {
      list.append(this._row(entry));
    }
    card.append(list);
    root.append(style, card);
  }

  _row(entry) {
    const info = SPC_ACTIVITY_SOURCES[entry.source] || SPC_ACTIVITY_SOURCES.panel_log;
    const row = document.createElement("div");
    row.className = "row";
    row.style.borderLeftColor = entry.ok === false ? SPC_ACTIVITY_ERROR :
      (entry.source === "panel_log" && entry.ok === true ? SPC_ACTIVITY_SOURCES.panel_reply.color : info.color);
    const time = document.createElement("div");
    time.className = "time";
    time.textContent = spcActivityTime(entry.time);
    time.title = entry.panel_time ? `panel: ${spcActivityTime(entry.panel_time)}` : "";
    const body = document.createElement("div");
    const title = document.createElement("span");
    title.className = "title";
    title.textContent = entry.title ? `${entry.title}: ` : "";
    const message = document.createTextNode(
      entry.user_name && !String(entry.message || "").includes(entry.user_name)
        ? `${entry.message || ""} (${entry.user_name})`
        : String(entry.message || "")
    );
    const source = document.createElement("div");
    source.className = "source";
    source.textContent = info[this._lang] || info.en;
    body.append(title, message, source);
    row.append(time, body);
    return row;
  }
}

function spcActivityTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (number) => String(number).padStart(2, "0");
  const today = new Date();
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  return date.toDateString() === today.toDateString()
    ? time
    : `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${time}`;
}

function spcActivityFromPanelEvent(data, timeFired) {
  const name = data.door_name || data.zone_name || data.area_name || "SPC";
  return {
    entry_id: data.entry_id,
    time: timeFired || new Date().toISOString(),
    panel_time: data.panel_time,
    source: "panel_event",
    title: name,
    message: data.panel_text || data.description || `event ${data.event_id}`,
    user_name: data.user_name,
    event_id: data.event_id,
  };
}

if (!customElements.get("spc-flexc-activity-card")) {
  customElements.define("spc-flexc-activity-card", SpcFlexCActivityCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "spc-flexc-activity-card")) {
  window.customCards.push({
    type: "spc-flexc-activity-card",
    name: "SPC FlexC Activity",
    description: "What HA sent, what the panel answered, events and panel log lines in one coloured timeline.",
  });
}
