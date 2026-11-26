// SPC FlexC doors card: every door like the web page's door status, with its
// mode, door contact, exit button and last entry, and the door's buttons
// Momentan, Lås upp, Blockera and Normal. A button is offered when the
// integration's button entity is available, which follows the door's mode
// like the web page (Normal is offered only when the door is not normal).

const SPC_DOORS_TEXT = {
  sv: {
    title: "SPC dörrar", door: "Dörr", mode: "Läge", contact: "Dörrkontakt", exitButton: "Öppnaknapp",
    lastUnlock: "Senaste upplåsning", lastPassage: "Senaste passage", area: "Område", side: "Andra sidan", noDoors: "Inga dörrar.",
    unlockedBy: { granted: "Inpassage godkänd", exit_granted: "Utpassage godkänd", exit_button: "Öppnaknapp", unlocked: "Dörr olåst" },
    modes: { normal: "Normal", blocked: "Blockerad", unlocked: "Upplåst" },
    open: "Öppen", closed: "Stängd", normal: "Normal", active: "Aktiv", granted: "Upplåst nu",
    actions: { open_momentarily: "Momentan", open_permanently: "Lås upp", lock: "Blockera", set_normal: "Normal" },
    confirmLock: "Blockera dörr {id} {name}? Kort, koder och öppnaknapp nekas tills den sätts i Normal.",
    confirmUnlock: "Lås upp dörr {id} {name}? Den står olåst tills den sätts i Normal.",
  },
  en: {
    title: "SPC doors", door: "Door", mode: "Mode", contact: "Door contact", exitButton: "Exit button",
    lastUnlock: "Last unlock", lastPassage: "Last passage", area: "Area", side: "Other side", noDoors: "No doors.",
    unlockedBy: { granted: "Entry granted", exit_granted: "Exit granted", exit_button: "Exit button", unlocked: "Door unlocked" },
    modes: { normal: "Normal", blocked: "Blocked", unlocked: "Unlocked" },
    open: "Open", closed: "Closed", normal: "Normal", active: "Active", granted: "Unlocked now",
    actions: { open_momentarily: "Momentary", open_permanently: "Unlock", lock: "Block", set_normal: "Normal" },
    confirmLock: "Block door {id} {name}? Cards, codes and the exit button are refused until it is set to Normal.",
    confirmUnlock: "Unlock door {id} {name}? It stays unlocked until it is set to Normal.",
  },
};
const SPC_DOOR_ACTIONS = ["open_momentarily", "open_permanently", "lock", "set_normal"];
const SPC_DOOR_KEYS = {
  door_mode: "mode", door_open: "contact", door_exit_button: "exitButton", door_entry_granted: "granted",
  open_momentarily: "open_momentarily", open_permanently: "open_permanently", lock: "lock", set_normal: "set_normal",
};
const SPC_DOOR_ENTITY_ID = /^(?:sensor|binary_sensor|button)\.spc_door_(\d+)_(mode|open|exit_button|entry_granted|open_momentarily|open_permanently|lock|set_normal)$/;
const SPC_DOOR_ID_KEYS = { mode: "mode", open: "contact", exit_button: "exitButton", entry_granted: "granted" };

class SpcFlexCDoorsCard extends SpcFlexCBaseCard {
  static get texts() {
    return SPC_DOORS_TEXT;
  }

  // Every door with its entities, through the door's device in the entity
  // registry (renamed entity IDs still work), else by the default IDs.
  _doors() {
    const states = this._hass?.states || {};
    const registry = this._hass?.entities || {};
    const doors = new Map();
    const byDevice = new Map();
    for (const d of spcEntities(this._hass, "sensor", "door_id")) {
      const key = registry[d.entity]?.translation_key;
      if (key ? key !== "door_mode" : !d.entity.endsWith("_mode")) continue;
      const door = { ...d, id: d.door_id, name: d.door_name || d.zone_name || "", mode: d.entity };
      doors.set(d.door_id, door);
      const device = registry[d.entity]?.device_id;
      if (device) byDevice.set(device, door);
    }
    for (const [entityId, entry] of Object.entries(registry)) {
      if (entry.platform !== "spc_flexc" || !states[entityId]) continue;
      let door = entry.device_id ? byDevice.get(entry.device_id) : null;
      let key = door ? SPC_DOOR_KEYS[entry.translation_key] : null;
      if (!door || !key) {
        const match = entityId.match(SPC_DOOR_ENTITY_ID);
        if (!match) continue;
        door = doors.get(Number(match[1]));
        key = SPC_DOOR_ID_KEYS[match[2]] || match[2];
      }
      if (door && key && key !== "mode") door[key] = entityId;
    }
    return [...doors.values()].sort((a, b) => a.id - b.id);
  }

  watched() {
    return this._doors().flatMap((d) => [d.mode, d.contact, d.exitButton, d.granted, ...SPC_DOOR_ACTIONS.map((a) => d[a])]).filter(Boolean);
  }

  body(card) {
    const doors = this._doors();
    if (!doors.length) {
      card.append(spcEl("div", { className: "note" }, [this._t("noDoors")]));
      return;
    }
    const grid = spcEl("div", { className: "doors" });
    for (const door of doors) grid.append(this._door(door));
    card.append(grid);
  }

  _door(door) {
    const mode = this._state(door.mode)?.state;
    const contact = this._state(door.contact)?.state;
    const exit = this._state(door.exitButton)?.state; // on = pressed (Aktiv)
    const granted = this._state(door.granted);
    const attrs = granted?.attributes || {};
    // Colours (owner 2026-11-14): normal green, active yellow, alarm red. An
    // open door is yellow when it was unlocked first, red when it was not.
    const open = contact === "on";
    const tone = (cls, text) => spcEl("span", { className: cls }, [text]);
    const modeTone = mode === "normal" ? "st-ok" : mode === "blocked" ? "st-alarm" : mode ? "st-active" : "";
    const contactTone = !open ? "st-ok" : this._openedUnlocked(mode, granted, attrs) ? "st-active" : "st-alarm";
    const lines = [
      [this._t("mode"), tone(`mode ${modeTone}`, this._t("modes")[mode] || mode || this._t("none"))],
      door.contact ? [this._t("contact"), contact === undefined || contact === "unavailable" ? this._t("none")
        : tone(contactTone, open ? this._t("open") : this._t("closed"))] : null,
      door.exitButton ? [this._t("exitButton"), exit === "on" ? tone("st-active", this._t("active"))
        : exit === "off" ? tone("st-ok", this._t("normal")) : this._t("none")] : null,
      granted ? [this._t("lastUnlock"), granted.state === "on"
        ? spcEl("span", {}, [tone("st-active", this._t("granted")), this._who(attrs, " · ")])
        : this._unlock(attrs)] : null,
      granted ? [this._t("lastPassage"), this._time(attrs.last_opened)] : null,
      [this._t("area"), `${door.area_id ?? ""} ${door.area_name || ""}`],
      door.area_side_2 || door.area_side_1 ? [this._t("side"),
        `${door.area_side_2 ?? door.area_side_1} ${door.area_side_2_name || door.area_side_1_name || ""}`] : null,
    ].filter(Boolean);
    const buttons = SPC_DOOR_ACTIONS.filter((action) => door[action]).map((action) => {
      const state = this._state(door[action]);
      const available = state && state.state !== "unavailable";
      return spcEl("button", {
        className: action === "set_normal" ? "primary" : action === "lock" ? "danger" : "",
        disabled: this._busy || !available,
        onclick: () => this._press(door, action),
      }, [this._t("actions")[action]]);
    });
    return spcEl("div", { className: `door mode-box-${mode}` }, [
      spcEl("div", { className: "door-title" }, [
        spcEl("ha-icon", { icon: contact === "on" ? "mdi:door-open" : mode === "blocked" ? "mdi:door-closed-lock" : "mdi:door-closed" }),
        `${this._t("door")} ${door.id} ${door.name}`,
      ]),
      spcEl("div", { className: "door-lines" }, lines.flatMap(([label, value]) => [
        spcEl("span", { className: "label" }, [label]), spcEl("span", {}, [value]),
      ])),
      spcEl("div", { className: "rowline door-buttons" }, buttons),
    ]);
  }

  // "14/11 09:12 · Anna" or "· Öppnaknapp": when, and who or what unlocked.
  _unlock(attrs) {
    const when = attrs.last_unlocked || attrs.last_entry_granted;
    if (!when) return this._t("none");
    return `${this._time(when)}${this._who(attrs, " · ")}`;
  }

  // Who or what unlocked: the user, else how (code/card, exit button...).
  _who(attrs, prefix = "") {
    const who = attrs.last_unlocked_user_name || this._t("unlockedBy")[attrs.last_unlocked_by] || "";
    return who ? `${prefix}${who}` : "";
  }

  // Whether the open door was unlocked first: mode Unlocked, the lock
  // released now, or an unlock just before it opened (code, card, exit button).
  _openedUnlocked(mode, granted, attrs) {
    if (mode === "unlocked" || granted?.state === "on") return true;
    const opened = Date.parse(attrs.last_opened || "");
    const unlocked = Date.parse(attrs.last_unlocked || "");
    if (Number.isNaN(opened) || Number.isNaN(unlocked)) return true; // unknown: not an alarm
    const window = ((attrs.granted_time || 3) + 10) * 1000;
    return opened - unlocked >= -2000 && opened - unlocked <= window;
  }

  // Within 24 hours only the time, else date and time.
  _time(value) {
    if (!value) return this._t("none");
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    const locale = this._lang === "sv" ? "sv-SE" : undefined;
    if (Math.abs(Date.now() - date.getTime()) < 24 * 3600 * 1000) {
      return date.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleString(locale, { dateStyle: "short", timeStyle: "short" });
  }

  async _press(door, action) {
    const values = { id: door.id, name: door.name };
    if (action === "lock" && !confirm(this._t("confirmLock", values))) return;
    if (action === "open_permanently" && !confirm(this._t("confirmUnlock", values))) return;
    this._error = "";
    this._message = "";
    this._busy = true;
    this._render();
    try {
      await this._hass.callService("button", "press", { entity_id: door[action] });
      this._message = this._t("done");
    } catch (err) {
      this._error = String(err?.message || err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  style_extra() {
    return `.doors { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
      .door { border: 1px solid var(--divider-color); border-radius: 10px; padding: 12px; display: grid; gap: 10px; }
      .door.mode-box-blocked { border-color: var(--error-color, #db4437); }
      .door.mode-box-unlocked { border-color: var(--warning-color, #ffa600); }
      .door-title { display: flex; align-items: center; gap: 8px; font-weight: 500; font-size: 1.05em; }
      .door-lines { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 0.9em; }
      .door-lines .label { color: var(--secondary-text-color); }
      .mode { font-weight: 500; }
      .st-ok { color: var(--success-color, #43a047); font-weight: 500; }
      .st-active { color: var(--warning-color, #ffa600); font-weight: 500; }
      .st-alarm { color: var(--error-color, #db4437); font-weight: 500; }
      .door-buttons button { flex: 1 1 auto; }`;
  }
}

spcDefineCard(
  "spc-flexc-doors-card",
  SpcFlexCDoorsCard,
  "SPC FlexC Doors",
  "Every door like the web page: mode, door contact, exit button, last entry, and Momentary, Unlock, Block and Normal."
);
