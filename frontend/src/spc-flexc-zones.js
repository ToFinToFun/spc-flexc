// SPC FlexC zones card: the panel's zones like its web page (Status >
// Sektioner): status, area, and inhibit, isolate and restore per zone. The
// buttons use the integration's own zone entities (switches for inhibit and
// isolate, the restore button) and are offered only when the panel allows
// the action, as it reports in ZONE_STATUS.

const SPC_ZONES_TEXT = {
  sv: {
    title: "SPC sektioner", zone: "Sektion", area: "Område", status: "Status", actions: "Åtgärd",
    allAreas: "Alla områden", onlyDeviating: "Bara avvikande", noZones: "Inga sektioner.",
    activeTitle: "Aktiva sektioner", allNormal: "Alla sektioner är normala.",
    inhibit: "Spärra", deinhibit: "Avspärra", isolate: "Isolera", deisolate: "Avisolera", restore: "Återställ",
    confirmIsolate: "Isolera sektion {id} {name}? Den larmar inte förrän den avisoleras.",
    edit: "Ändra", editTitle: "Ändra sektion {id}", type: "Sektionstyp", techDelay: "Teknisk fördröjning (s)",
    keyarm: "Nyckeltillkoppling", attributes: "Attribut", saved: "Sektion {id} sparad.",
    editHint: "Ändras i centralen via FlexC (programtekniker i installatörsläge) och sparas direkt.",
    keyarmNames: { 1: "Deltillkoppling A", 2: "Deltillkoppling B", 3: "Tillkoppling" },
    typeNames: ["Larm", "In/utpassering", "Utpasseringstid", "Brand", "Nödutgång", "Linje", "Bråklarm", "Överfall",
      "Sabotage", "Tekniskt larm", "Medicinskt", "Nyckeltillkoppling", "Används ej", "Förbikopplare", "X-förbikopplare",
      "Detektorfel", "Låskontroll", "Seismisk", "Allt OK", "Överfall fel", "Varning fel", "Tillkopplingstillstånd",
      "Lås element", "Glaskross", "Vatten", "Värme", "Kyl/frys", "Gas", "Sprinkler", "CO", "In/utpassering 2"],
    attrNames: {
      access: "Följande", exclude_a: "Uteslut A", exclude_b: "Uteslut B", "24_hour": "24 timmar", local: "Lokal",
      double_knock: "Dubbel aktivering", chime: "Ding-Dong", inhibit: "Spärra", normally_open: "Normalt öppen",
      silent: "Tyst", log: "Logg", open_only: "Endast öppen", report_only: "Endast rapport", final_exit: "Sista utgång",
      keyarm_set: "Tillkoppling aktiverad", keyarm_unset: "Frånkoppling aktiverat", shunt: "Förbikopplare",
      report: "Rapport", display: "Visa", audible: "Hörbar", report_when_set: "Rapportera vid tillkopplad",
      frequent: "Frekvent", fire_prealarm: "Förlarm", fire_recognition: "Upptäckt", exit_open: "Nödutgång öppen",
      unset_local: "Frånkoppling lokalt", keyarm_delayed: "Fördröjd", forced_set: "Tvångstillkoppla",
      auto_restore: "Automatisk återställning", no_bells: "Ingen siren",
    },
    statusNames: {
      normal: "Normal", active: "Aktiv", alarm: "Larm", tamper: "Sabotage", trouble: "Fel",
      inhibited: "Spärrad", isolated: "Isolerad", short: "Kortslutning", disconnected: "Avbrott",
      masked: "Maskerad", dc_substitution: "DC-substitution", missing: "Detektor saknas", offline: "Offline",
    },
  },
  en: {
    title: "SPC zones", zone: "Zone", area: "Area", status: "Status", actions: "Action",
    allAreas: "All areas", onlyDeviating: "Only deviating", noZones: "No zones.",
    activeTitle: "Active zones", allNormal: "All zones are normal.",
    inhibit: "Inhibit", deinhibit: "De-inhibit", isolate: "Isolate", deisolate: "De-isolate", restore: "Restore",
    confirmIsolate: "Isolate zone {id} {name}? It will not alarm until it is de-isolated.",
    edit: "Edit", editTitle: "Edit zone {id}", type: "Zone type", techDelay: "Technical delay (s)",
    keyarm: "Key arm", attributes: "Attributes", saved: "Zone {id} saved.",
    editHint: "Changed on the panel over FlexC (engineer in installer mode) and saved at once.",
    keyarmNames: { 1: "Part set A", 2: "Part set B", 3: "Full set" },
    typeNames: ["Alarm", "Entry/exit", "Exit terminator", "Fire", "Fire exit", "Line", "Panic", "Hold-up",
      "Tamper", "Technical", "Medical", "Key arm", "Unused", "Shunt", "X-shunt", "Fault", "Lock supervision",
      "Seismic", "All okay", "Hold-up fault", "Warning fault", "Setting authorisation", "Lock element",
      "Glass break", "Water", "Heat", "Freezer", "Gas", "Sprinkler", "CO", "Entry/exit 2"],
    attrNames: {
      access: "Access", exclude_a: "Exclude A", exclude_b: "Exclude B", "24_hour": "24 hour", local: "Local",
      double_knock: "Double knock", chime: "Chime", inhibit: "Inhibit", normally_open: "Normally open",
      silent: "Silent", log: "Log", open_only: "Open only", report_only: "Report only", final_exit: "Final exit",
      keyarm_set: "Key arm sets", keyarm_unset: "Key arm unsets", shunt: "Shunt", report: "Report",
      display: "Display", audible: "Audible", report_when_set: "Report when set", frequent: "Frequent",
      fire_prealarm: "Fire pre-alarm", fire_recognition: "Fire recognition", exit_open: "Exit open",
      unset_local: "Unset local", keyarm_delayed: "Delayed", forced_set: "Forced set",
      auto_restore: "Auto restore", no_bells: "No bells",
    },
    statusNames: {
      normal: "Normal", active: "Active", alarm: "Alarm", tamper: "Tamper", trouble: "Trouble",
      inhibited: "Inhibited", isolated: "Isolated", short: "Short circuit", disconnected: "Disconnected",
      masked: "Masked", dc_substitution: "DC substitution", missing: "Detector missing", offline: "Offline",
    },
  },
};
const SPC_ZONE_ENTITY_KEYS = { zone_status: "status", inhibition: "inhibition", isolation: "isolation", restore: "restore" };
const SPC_ZONE_ENTITY_ID = /^(?:sensor|switch|button)\.spc_zone_(\d+)_(status|inhibition|isolation|restore)$/;
// Attributes the web page offers per zone type (read 2026-11-13); other
// types show every attribute.
const SPC_ZONE_TYPE_ATTRS = {
  0: ["access", "exclude_a", "exclude_b", "24_hour", "local", "unset_local", "double_knock", "chime", "inhibit",
    "normally_open", "silent", "log", "shunt", "frequent", "auto_restore", "no_bells"],
  1: ["exclude_a", "exclude_b", "local", "chime", "inhibit", "log", "final_exit", "shunt", "frequent", "exit_open",
    "auto_restore", "no_bells"],
  3: ["local", "unset_local", "inhibit", "normally_open", "log", "report_only", "fire_prealarm", "fire_recognition",
    "auto_restore"],
  9: ["chime", "inhibit", "normally_open", "log", "report", "report_when_set", "display", "audible", "frequent",
    "auto_restore"],
  11: ["inhibit", "normally_open", "log", "open_only", "keyarm_set", "keyarm_unset", "frequent", "keyarm_delayed",
    "forced_set"],
  16: ["inhibit", "normally_open", "log", "auto_restore"],
};
const SPC_ZONE_STATUS_CLASS = {
  normal: "st-ok", active: "st-active", alarm: "st-bad", tamper: "st-bad", trouble: "st-bad",
  short: "st-bad", disconnected: "st-bad", masked: "st-bad", dc_substitution: "st-bad",
  missing: "st-bad", offline: "st-bad", inhibited: "st-off", isolated: "st-off",
};

class SpcFlexCZonesCard extends SpcFlexCBaseCard {
  static get texts() {
    return SPC_ZONES_TEXT;
  }

  // compact: true is the live list for the home page: only zones that are
  // not normal (open, alarm, faults, then inhibited and isolated), no
  // filters and no buttons.
  static get defaults() {
    return { only_deviating: false, compact: false };
  }

  // Every zone with its entities. Several zones share a device (an I/O
  // card, a door), so entities are matched by their zone_id attribute and
  // translation key, else by the default entity IDs.
  _zones() {
    const states = this._hass?.states || {};
    const registry = this._hass?.entities || {};
    const zones = new Map();
    for (const z of spcEntities(this._hass, "binary_sensor", "zone_id").filter((e) => e.logic_input !== undefined)) {
      zones.set(z.zone_id, { id: z.zone_id, name: z.zone_name || "", areaId: z.area_id, areaName: z.area_name || "", main: z.entity });
    }
    for (const [entityId, state] of Object.entries(states)) {
      const entry = registry[entityId];
      if (entry ? entry.platform !== "spc_flexc" : !entityId.includes(".spc_")) continue;
      const match = entityId.match(SPC_ZONE_ENTITY_ID);
      const key = SPC_ZONE_ENTITY_KEYS[entry?.translation_key] || match?.[2];
      const zoneId = state.attributes?.zone_id ?? (match ? Number(match[1]) : undefined);
      const zone = zones.get(zoneId);
      if (zone && key && ["status", "inhibition", "isolation", "restore"].includes(key)) zone[key] = entityId;
    }
    return [...zones.values()].sort((a, b) => a.id - b.id);
  }

  watched() {
    return [...this._zones().flatMap((z) => [z.main, z.status, z.inhibition, z.isolation, z.restore]), this._config?.capabilities_entity || "sensor.spc_capabilities"].filter(Boolean);
  }

  _t(key, values) {
    return super._t(key === "title" && this._config?.compact ? "activeTitle" : key, values);
  }

  _choice() {
    this._picked ||= { area: "", deviating: Boolean(this._config.only_deviating) };
    return this._picked;
  }

  _compact(card, zones) {
    const order = (status) => (status === "isolated" || status === "inhibited" ? 2 : status === "active" ? 1 : 0);
    const shown = zones
      .map((zone) => ({ zone, status: this._state(zone.status)?.state }))
      .filter(({ status }) => status && status !== "normal" && status !== "unavailable" && status !== "unknown")
      .sort((a, b) => order(a.status) - order(b.status) || a.zone.id - b.zone.id);
    if (!shown.length) {
      card.append(spcEl("div", { className: "note" }, [this._t("allNormal")]));
      return;
    }
    const list = spcEl("div", { className: "live" });
    for (const { zone, status } of shown) {
      list.append(spcEl("div", { className: "live-row" }, [
        spcEl("span", {}, [`${zone.id} ${zone.name}`]),
        spcEl("span", { className: "note" }, [zone.areaName]),
        spcEl("span", { className: `live-state ${SPC_ZONE_STATUS_CLASS[status] || ""}` }, [this._t("statusNames")[status] || status]),
      ]));
    }
    card.append(list);
  }

  body(card) {
    const zones = this._zones();
    if (this._config.compact) {
      this._compact(card, zones);
      return;
    }
    const areas = [...new Map(zones.map((z) => [z.areaId, z.areaName])).entries()].sort((a, b) => a[0] - b[0]);
    if (this._editing) {
      this._editForm(card, this._editing, areas);
      return;
    }
    const choice = this._choice();
    const area = spcEl("select", { onchange: () => { choice.area = area.value; this._render(); } });
    area.append(spcEl("option", { value: "" }, [this._t("allAreas")]));
    for (const [id, name] of areas) {
      const option = spcEl("option", { value: String(id) }, [`${id} ${name}`]);
      option.selected = String(id) === choice.area;
      area.append(option);
    }
    const deviating = spcEl("input", { type: "checkbox", checked: choice.deviating,
      onchange: () => { choice.deviating = deviating.checked; this._render(); } });
    card.append(spcEl("div", { className: "rowline" }, [
      this._field(this._t("area"), area),
      spcEl("label", { className: "rowline" }, [deviating, this._t("onlyDeviating")]),
    ]));

    const shown = zones.filter((z) => (!choice.area || String(z.areaId) === choice.area)
      && (!choice.deviating || !["normal", undefined].includes(this._state(z.status)?.state)));
    if (!shown.length) {
      card.append(spcEl("div", { className: "note" }, [this._t("noZones")]));
      return;
    }
    const table = spcEl("table", {}, [spcEl("tr", {}, [
      spcEl("th", {}, [this._t("zone")]), spcEl("th", {}, [this._t("area")]),
      spcEl("th", {}, [this._t("status")]), spcEl("th", {}, [this._t("actions")]),
    ])]);
    for (const zone of shown) {
      const status = this._state(zone.status)?.state;
      table.append(spcEl("tr", {}, [
        spcEl("td", {}, [`${zone.id} ${zone.name}`]),
        spcEl("td", {}, [`${zone.areaId ?? ""} ${zone.areaName}`]),
        spcEl("td", { className: SPC_ZONE_STATUS_CLASS[status] || "" }, [this._t("statusNames")[status] || status || this._t("none")]),
        spcEl("td", {}, [spcEl("div", { className: "rowline" }, this._actions(zone))]),
      ]));
    }
    card.append(table);
  }

  // The buttons the panel allows now: inhibit/de-inhibit, isolate/de-isolate
  // and restore, like the web page's zone actions.
  _actions(zone) {
    const buttons = [];
    const toggle = (entity, onKey, offKey, allowOn, allowOff, confirmText) => {
      const state = this._state(entity);
      if (!state || state.state === "unavailable") return;
      const on = state.state === "on";
      if (on ? state.attributes[allowOff] === false : state.attributes[allowOn] === false) return;
      buttons.push(spcEl("button", { className: "small", disabled: this._busy, onclick: () => {
        if (!on && confirmText && !confirm(confirmText)) return;
        this._press("switch", on ? "turn_off" : "turn_on", entity);
      } }, [this._t(on ? offKey : onKey)]));
    };
    toggle(zone.inhibition, "inhibit", "deinhibit", "inhibit_allowed", "deinhibit_allowed");
    toggle(zone.isolation, "isolate", "deisolate", "isolate_allowed", "deisolate_allowed",
      this._t("confirmIsolate", { id: zone.id, name: zone.name }));
    if (this._engineerReady()) {
      buttons.push(spcEl("button", { className: "small", disabled: this._busy, onclick: () => this._edit(zone) },
        [this._t("edit")]));
    }
    const restore = this._state(zone.restore);
    if (restore && restore.state !== "unavailable") {
      buttons.push(spcEl("button", { className: "small primary", disabled: this._busy,
        onclick: () => this._press("button", "press", zone.restore) }, [this._t("restore")]));
    }
    return buttons;
  }

  // Zones can be changed only with the engineer logged in and the panel in
  // installer mode (EDIT_ZONE answers 65 otherwise).
  _engineerReady() {
    const attrs = this._hass?.states[this._config.capabilities_entity || "sensor.spc_capabilities"]?.attributes || {};
    return attrs.engineer_login?.logged_in === true && attrs.engineer_mode === true;
  }

  async _edit(zone) {
    const record = await this._call("get_zone_config", { zone_id: zone.id }, { response: true });
    if (!record || record.zone_id === undefined) return;
    this._open({ ...record, attributes: [...record.attributes], original: record });
  }

  _editForm(card, form, areas) {
    const typeNames = this._t("typeNames");
    const name = spcEl("input", { type: "text", maxLength: 16, value: form.name,
      oninput: () => { form.name = name.value; } });
    const type = spcEl("select", { onchange: () => { form.type = Number(type.value); this._render(); } });
    typeNames.forEach((label, value) => {
      const option = spcEl("option", { value: String(value) }, [`${value} ${label}`]);
      option.selected = value === form.type;
      type.append(option);
    });
    const area = spcEl("select", { onchange: () => { form.area = Number(area.value); } });
    const areaList = areas.some(([id]) => id === form.area) ? areas : [...areas, [form.area, ""]];
    for (const [id, label] of areaList) {
      const option = spcEl("option", { value: String(id) }, [`${id} ${label}`]);
      option.selected = id === form.area;
      area.append(option);
    }
    const delay = spcEl("input", { type: "number", min: 0, max: 9999, value: form.technical_delay,
      oninput: () => { form.technical_delay = Number(delay.value); } });
    const fields = [
      this._field(this._t("name"), name), this._field(this._t("type"), type),
      this._field(this._t("area"), area), this._field(this._t("techDelay"), delay),
    ];
    if (form.type === 11) {
      const keyarm = spcEl("select", { onchange: () => { form.keyarm_function = Number(keyarm.value); } });
      for (const [value, label] of Object.entries(this._t("keyarmNames"))) {
        const option = spcEl("option", { value }, [label]);
        option.selected = Number(value) === form.keyarm_function;
        keyarm.append(option);
      }
      fields.push(this._field(this._t("keyarm"), keyarm));
    }
    const attrNames = this._t("attrNames");
    const shown = SPC_ZONE_TYPE_ATTRS[form.type] || Object.keys(attrNames);
    const boxes = [...new Set([...shown, ...form.attributes])].map((attr) => {
      const box = spcEl("input", { type: "checkbox", checked: form.attributes.includes(attr), onchange: () => {
        form.attributes = box.checked ? [...form.attributes, attr] : form.attributes.filter((a) => a !== attr);
      } });
      return spcEl("label", { className: "attr" }, [box, attrNames[attr] || attr]);
    });
    card.append(
      spcEl("div", { className: "edit-title" }, [this._t("editTitle", { id: form.zone_id })]),
      spcEl("div", { className: "note" }, [this._t("editHint")]),
      spcEl("div", { className: "edit-grid" }, fields),
      spcEl("div", { className: "label" }, [this._t("attributes")]),
      spcEl("div", { className: "attrs" }, boxes),
      spcEl("div", { className: "rowline" }, [
        spcEl("button", { className: "primary", disabled: this._busy, onclick: () => this._saveZone(form) },
          [this._t("save")]),
        this._closeButton(),
      ]),
    );
  }

  async _saveZone(form) {
    const original = form.original;
    const data = { zone_id: form.zone_id };
    if (form.name !== original.name) data.name = form.name;
    if (form.type !== original.type) data.type = form.type;
    if (form.area !== original.area) data.area = form.area;
    if (form.technical_delay !== original.technical_delay) data.technical_delay = form.technical_delay;
    if (form.keyarm_function !== original.keyarm_function) data.keyarm_function = form.keyarm_function;
    const on = form.attributes.filter((a) => !original.attributes.includes(a));
    const off = original.attributes.filter((a) => !form.attributes.includes(a));
    if (on.length) data.attributes_on = on;
    if (off.length) data.attributes_off = off;
    if (Object.keys(data).length === 1) {
      this._close();
      return;
    }
    const result = await this._call("edit_zone", data, { response: true });
    if (result && result.zone_id !== undefined) {
      this._editing = null;
      this._message = this._t("saved", { id: form.zone_id });
      this._render();
    }
  }

  async _press(domain, service, entity) {
    this._error = "";
    this._message = "";
    this._busy = true;
    this._render();
    try {
      await this._hass.callService(domain, service, { entity_id: entity });
      this._message = this._t("done");
    } catch (err) {
      this._error = String(err?.message || err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  style_extra() {
    return `.st-ok { color: var(--success-color, #43a047); }
      .st-active { color: var(--warning-color, #ffa600); font-weight: 500; }
      .st-bad { color: var(--error-color, #db4437); font-weight: 500; }
      .st-off { color: var(--secondary-text-color); font-style: italic; }
      .live { display: grid; gap: 2px; }
      .live-row { display: grid; grid-template-columns: 1fr auto auto; gap: 12px; align-items: baseline;
        padding: 6px 2px; border-bottom: 1px solid var(--divider-color); }
      .live-state { text-align: right; min-width: 6em; }
      .edit-title { font-weight: 500; font-size: 1.05em; margin-bottom: 4px; }
      .edit-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px 16px; margin: 8px 0; }
      .attrs { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 4px 12px; margin: 6px 0 12px; }
      .attr { display: flex; align-items: center; gap: 6px; }`;
  }
}

spcDefineCard(
  "spc-flexc-zones-card",
  SpcFlexCZonesCard,
  "SPC FlexC Zones",
  "The panel's zones like its web page: status per zone, inhibit, isolate and restore."
);
