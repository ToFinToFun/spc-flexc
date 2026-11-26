// SPC FlexC system card: the panel's system state like its home page and
// status pages: active system alerts, what is inhibited or isolated, the
// panel clock, and what the integration can do on this panel (Capabilities).

const SPC_SYSTEM_TEXT = {
  sv: {
    title: "SPC system", alerts: "Aktiva systemlarm", noAlerts: "Inga",
    clearAlerts: "Rensa systemlarm", inhibited: "Spärrade och isolerade", noneInhibited: "Inga",
    clock: "Klocka", clockOffset: "Centralens klocka går {offset} s fel.", clockOk: "Centralens klocka går rätt.",
    setClock: "Ställ centralens klocka", silence: "Tysta sirener",
    functions: "Funktioner", login: "Integrationen loggar in som användare {id} (FlexC-kommandoprofilen){engineer}.",
    engineer: ", programtekniker", noEngineer: ", inte programtekniker",
    states: { isolated: "Isolerad", inhibited: "Spärrad" },
    functionNames: {
      panel_status: "Centralens status", panel_settings: "Centralens inställningar", set_clock: "Ställa klockan",
      save_config: "Spara konfiguration", engineer_mode: "Installatörsläge", engineer_access: "Installatörsåtkomst",
      xbus: "X-BUS", logs: "System- och sektionslogg", areas: "Områden", zones: "Sektioner",
      alerts: "Systemlarm", alert_control: "Spärra/isolera systemlarm", silence_bells: "Tysta sirener",
      holdup: "Överfallslarm", zone_config: "Ändra sektion", virtual_keypad: "Virtuell knappsats",
      wireless: "Trådlöst", mapping_gates: "Mapping gates", doors: "Dörrar", access_log: "Passerlogg",
      unknown_cards: "Okända kort", users: "Användare", add_delete_users: "Lägg till/ta bort användare",
      pins: "PIN-koder", user_status: "Användarstatus", user_profiles: "Användarprofiler",
      user_devices: "Fjärrkontroller, SMS, taggar", calendars: "Kalendrar", calendar_exceptions: "Kalenderundantag",
      flexc_status: "FlexC-status", flexc_logs: "FlexC-loggar", flexc_test_call: "Testanrop",
      modem: "Modem", camera: "Kamera", flexc_admin: "FlexC-administration", files_firmware: "Filer och firmware",
    },
    groupNames: {
      system: "System", alarm: "Larm", outputs: "Utgångar", access: "Passerkontroll",
      users: "Användare", calendars: "Kalendrar", communication: "Kommunikation",
    },

    kinds: { zone: "Sektion", xbus: "X-BUS", system_alert: "Systemlarm" },
    alertNames: {"mains_fault": "Fel 230V AC", "battery_fault": "Centralapparat, batterifel", "psu_fault": "Centralapparat, fel på PSU-enhet", "aux_fuse_fault": "AUX-utgång, säkring", "external_bell_fuse_fault": "Extern siren säkring", "internal_bell_fuse_fault": "Intern siren säkring", "bell_tamper": "Sirensabotage", "cabinet_tamper": "Kapslingssabotage", "aux_tamper_1": "Aux. Sabotage 1", "aux_tamper_2": "Aux. Sabotage 2", "antenna_tamper": "Antennsabotage", "rf_jamming": "RF Störning", "fail_to_communicate": "Kommunikationsfel", "xbus_cable_fault": "X-BUS KABEL Fel", "code_tamper": "ANV KOD SAB", "ethernet_link": "Ethernet länk", "network_fault": "Nätverksfel"},
    xbusFaults: {"tamper": "Sabotage", "mains_fault": "Nätspänningsfel"},
    status: {
      works: "Fungerar", untested: "Otestad", not_built: "Inte byggd", no_hardware: "Hårdvara saknas",
      refused: "Nekad av centralen", needs_engineer: "Kräver programtekniker",
    },
  },
  en: {
    title: "SPC system", alerts: "Active system alerts", noAlerts: "None",
    clearAlerts: "Clear system alerts", inhibited: "Inhibited and isolated", noneInhibited: "None",
    clock: "Clock", clockOffset: "The panel clock is {offset} s off.", clockOk: "The panel clock is right.",
    setClock: "Set the panel clock", silence: "Silence bells",
    functions: "Functions", login: "The integration logs in as user {id} (FlexC command profile){engineer}.",
    engineer: ", engineer", noEngineer: ", not engineer",
    states: { isolated: "Isolated", inhibited: "Inhibited" },
    functionNames: {
      panel_status: "Panel status", panel_settings: "Panel settings", set_clock: "Set the clock",
      save_config: "Save configuration", engineer_mode: "Engineer mode", engineer_access: "Engineer access",
      xbus: "X-BUS", logs: "System and zone log", areas: "Areas", zones: "Zones",
      alerts: "System alerts", alert_control: "Inhibit/isolate system alerts", silence_bells: "Silence bells",
      holdup: "Hold-up", zone_config: "Edit zone", virtual_keypad: "Virtual keypad",
      wireless: "Wireless", mapping_gates: "Mapping gates", doors: "Doors", access_log: "Access log",
      unknown_cards: "Unknown cards", users: "Users", add_delete_users: "Add/delete users",
      pins: "PINs", user_status: "User status", user_profiles: "User profiles",
      user_devices: "Fobs, SMS, tags", calendars: "Calendars", calendar_exceptions: "Calendar exceptions",
      flexc_status: "FlexC status", flexc_logs: "FlexC logs", flexc_test_call: "Test call",
      modem: "Modem", camera: "Camera", flexc_admin: "FlexC administration", files_firmware: "Files and firmware",
    },
    groupNames: {
      system: "System", alarm: "Alarm", outputs: "Outputs", access: "Access control",
      users: "Users", calendars: "Calendars", communication: "Communication",
    },

    kinds: { zone: "Zone", xbus: "X-BUS", system_alert: "System alert" },
    alertNames: {"mains_fault": "Mains fault", "battery_fault": "Battery fault", "psu_fault": "PSU fault", "aux_fuse_fault": "Aux fuse fault", "external_bell_fuse_fault": "External bell fuse fault", "internal_bell_fuse_fault": "Internal bell fuse fault", "bell_tamper": "Bell tamper", "cabinet_tamper": "Cabinet tamper", "aux_tamper_1": "Aux tamper 1", "aux_tamper_2": "Aux tamper 2", "antenna_tamper": "Antenna tamper", "rf_jamming": "RF jamming", "fail_to_communicate": "Fail to communicate", "xbus_cable_fault": "X-BUS cable fault", "code_tamper": "Code tamper", "ethernet_link": "Ethernet link fault", "network_fault": "Network fault"},
    xbusFaults: {"tamper": "Tamper", "mains_fault": "Mains fault"},
    status: {
      works: "Works", untested: "Untested", not_built: "Not built", no_hardware: "No hardware",
      refused: "Refused by the panel", needs_engineer: "Needs engineer",
    },
  },
};

class SpcFlexCSystemCard extends SpcFlexCBaseCard {
  static get texts() {
    return SPC_SYSTEM_TEXT;
  }

  static get defaults() {
    return {
      alerts_entity: "sensor.spc_active_alerts",
      inhibited_entity: "sensor.spc_inhibited_isolated",
      clock_entity: "sensor.spc_clock_offset",
      capabilities_entity: "sensor.spc_capabilities",
      silence_entity: "button.spc_silence_bells",
      settings_entity: "sensor.spc_panel_settings",
    };
  }

  watched() {
    const c = this._config;
    return [c.alerts_entity, c.inhibited_entity, c.clock_entity, c.capabilities_entity, c.settings_entity];
  }

  style_extra() {
    return `h3 { margin: 12px 0 4px; font-size: 1em; }
      .status-works { color: var(--success-color, #43a047); }
      .status-refused { color: var(--error-color, #db4437); }
      details { margin: 4px 0; } summary { cursor: pointer; padding: 4px 0; font-weight: 500; }
      .setting-off { color: var(--secondary-text-color); }`;
  }

  body(card) {
    const c = this._config;
    // System alerts
    const alerts = this._attr(c.alerts_entity, "alerts", []);
    card.append(spcEl("h3", {}, [this._t("alerts")]));
    card.append(spcEl("div", {}, [alerts.length
      ? alerts.map((a) => a.name || a.description || `${a.event_id}`).join(", ")
      : this._t("noAlerts")]));
    const actions = [spcEl("button", { disabled: this._busy, onclick: () => this._call("clear_alerts", {}) }, [this._t("clearAlerts")])];
    const silence = this._state(c.silence_entity);
    if (silence && silence.state !== "unavailable") {
      actions.push(spcEl("button", { disabled: this._busy, onclick: async () => {
        try {
          await this._hass.callService("button", "press", { entity_id: c.silence_entity });
          this._message = this._t("done");
        } catch (err) {
          this._error = String(err?.message || err);
        }
        this._render();
      } }, [this._t("silence")]));
    }
    card.append(spcEl("div", { className: "rowline" }, actions));

    // Inhibited and isolated
    const items = this._attr(c.inhibited_entity, "items", []);
    card.append(spcEl("h3", {}, [`${this._t("inhibited")} (${items.length})`]));
    if (!items.length) {
      card.append(spcEl("div", {}, [this._t("noneInhibited")]));
    } else {
      const table = spcEl("table");
      for (const item of items) {
        const what = item.kind === "zone"
          ? `${this._t("kinds").zone} ${item.name || item.id}`
          : item.kind === "xbus" ? `${item.name || item.id}: ${this._t("xbusFaults")[item.fault] || item.fault || ""}`
          : `${this._t("kinds").system_alert}: ${this._t("alertNames")[item.id] || item.id}`;
        table.append(spcEl("tr", {}, [spcEl("td", {}, [what]), spcEl("td", {}, [this._t("states")[item.state] || item.state])]));
      }
      card.append(table);
    }

    // Clock
    const offset = Number(this._state(c.clock_entity)?.state);
    card.append(spcEl("h3", {}, [this._t("clock")]));
    card.append(spcEl("div", { className: "rowline" }, [
      Number.isFinite(offset) && Math.abs(offset) >= 5 ? this._t("clockOffset", { offset: Math.round(offset) }) : this._t("clockOk"),
      spcEl("button", { disabled: this._busy, onclick: () => this._call("set_clock", {}) }, [this._t("setClock")]),
    ]));

    this._settings(card);

    // Capabilities
    const login = this._attr(c.capabilities_entity, "command_login", null);
    const functions = this._attr(c.capabilities_entity, "functions", []);
    card.append(spcEl("h3", {}, [this._t("functions")]));
    if (login) {
      card.append(spcEl("div", { className: "note" }, [this._t("login", {
        id: login.user_id, engineer: login.engineer ? this._t("engineer") : this._t("noEngineer"),
      })]));
    }
    const table = spcEl("table");
    for (const f of functions) {
      const status = spcEl("td", { className: `status-${f.status}` }, [this._t("status")[f.status] || f.status]);
      table.append(spcEl("tr", {}, [
        spcEl("td", {}, [this._t("functionNames")[f.function] || f.function]),
        spcEl("td", {}, [this._t("groupNames")[f.group] || f.group]), status,
      ]));
    }
    card.append(spcEl("div", { className: "scroll" }, [table]));
  }
}

// The panel's settings (READ_INTRUDER_CFG) by the web page's names and units.
SpcFlexCSystemCard.prototype._settings = function (card) {
  const settings = this._attr(this._config.settings_entity, "settings", null);
  if (!settings) return;
  const text = SPC_SETTINGS_TEXT[this._lang] || SPC_SETTINGS_TEXT.en;
  const choice = (name, value) => text.choiceValues[name]?.[value] ?? value;
  const rows = (pairs) => {
    const table = spcEl("table");
    for (const [label, value, off] of pairs) {
      table.append(spcEl("tr", {}, [spcEl("td", {}, [label]), spcEl("td", { className: off ? "setting-off" : "" }, [String(value)])]));
    }
    return table;
  };
  const section = (title, table) => spcEl("details", {}, [spcEl("summary", {}, [title]), table]);
  card.append(spcEl("h3", {}, [text.settings]));
  const standard = ["continent", "region", "type", "grade"].filter((k) => settings.choices?.[k] !== undefined)
    .map((k) => [text.standardNames[k], choice(k, settings.choices[k])]);
  if (standard.length) card.append(section(text.standard, rows(standard)));
  const options = Object.keys(text.optionNames).filter((k) => settings.options?.[k] !== undefined)
    .map((k) => [text.optionNames[k], settings.options[k] ? text.yes : text.no, !settings.options[k]]);
  if (options.length) card.append(section(text.options, rows(options)));
  const choices = Object.keys(text.choiceNames).filter((k) => settings.choices?.[k] !== undefined)
    .map((k) => [text.choiceNames[k], choice(k, settings.choices[k])]);
  if (choices.length) card.append(section(text.choices, rows(choices)));
  const timers = Object.keys(text.timerNames).filter((k) => settings.timers?.[k] !== undefined)
    .map((k) => [text.timerNames[k], `${settings.timers[k].value} ${text.units[settings.timers[k].unit] ?? settings.timers[k].unit}`.trim()]);
  if (timers.length) card.append(section(text.timers, rows(timers)));
};

spcDefineCard(
  "spc-flexc-system-card",
  SpcFlexCSystemCard,
  "SPC FlexC System",
  "System alerts, inhibited and isolated, the panel clock and what the integration can do."
);
