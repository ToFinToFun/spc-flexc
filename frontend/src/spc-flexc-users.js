// SPC FlexC users card: the panel's users like the web page's user page.
// Lists users and lets the owner add, edit and delete them, change PINs and
// cards, all through the integration's own actions (no developer tools).
// PINs are typed in and sent once; they are never shown or stored here.

const SPC_USERS_TEXT = {
  sv: {
    title: "SPC användare", add: "Lägg till användare", edit: "Ändra", close: "Stäng",
    save: "Spara", delete: "Ta bort användare", confirmDelete: "Ta bort användare {id} {name}?",
    number: "Nr", name: "Namn", profiles: "Profiler", valid: "Giltig", card: "Kort", pin: "PIN",
    dateLimit: "Datumbegränsad", from: "Från", until: "Till", cardNumber: "Kortnummer",
    unknownCard: "Okänt kort…", removeCard: "Ta bort kort", cardOptions: "Passerkontroll",
    language: "Språk", systemLanguage: "Systemspråk", newPin: "Ny PIN", changePin: "Byt PIN",
    currentPin: "Nuvarande PIN",
    pinTitle: "PIN-kod",
    pinStates: { off: "Inte sparad i HA", unconfirmed: "Sparad – inte kontrollerad", pending: "Ny kod satt – väntar på prov", confirmed: "Kontrollerad" },
    pinWhat: "Centralen visar aldrig koder. För att byta en kod behöver HA användarens nuvarande kod. Med Kom ihåg sparar HA en nyckel (inte koden), så nästa gång räcker den nya koden, till exempel vid gästbyte. HA visar aldrig koden.",
    pinRemember: "Kom ihåg i HA – nästa gång räcker den nya koden",
    pinUnconfirmed: "HA kan inte se om den nuvarande koden du angav var rätt. Byt koden (samma kod går bra) och slå den vid en dörr som användaren har tillgång till.",
    pinPending: "Den nya koden är skriven till centralen. Slå den vid en dörr som användaren har tillgång till (eller på knappsatsen om användaren har områden). Öppnar dörren är allt rätt.",
    pinPendingDenied: "Nekar dörren koden var den nuvarande kod du angav fel: sätt användarens kod på centralen och byt den sedan här med den koden som nuvarande.",
    pinConfirmed: "Skriv en ny kod och tryck Byt PIN. Den gamla koden slutar gälla direkt.",
    pinForget: "Glöm i HA", pinForgetNote: "HA glömmer nyckeln. Koden i centralen ändras inte.",
    pinNeedCurrent: "Skriv användarens nuvarande kod.", pinNeedNew: "Skriv den nya koden.",
    pinSaveNote: "Spara ovan gäller namn, datum, kort och språk – inte koden.",
    pinDone: { set_pin: "Ny kod skriven till centralen.", enable_pin_management: "Sparad i HA.", disable_pin_management: "HA har glömt nyckeln." },
    noFreeNumbers: "Inga lediga användarnummer med PIN-nyckel. Skapa användaren en gång på centralen och slå på PIN-hantering för numret, så kan det sedan återanvändas här.",
    userNumber: "Användarnummer", done: "Klart", none: "–", missing: "Sensorn {entity} saknas.",
    options: {
      card_blocked: "Spärra kort", extended_time: "Förlängd tid", pin_bypass: "PIN förbikoppling",
      priority: "Prioritet", escort: "Vittne", custodian: "Ledsagare",
    },
    languages: { 7: "Svenska" },
  },
  en: {
    title: "SPC users", add: "Add user", edit: "Edit", close: "Close",
    save: "Save", delete: "Delete user", confirmDelete: "Delete user {id} {name}?",
    number: "No.", name: "Name", profiles: "Profiles", valid: "Valid", card: "Card", pin: "PIN",
    dateLimit: "Date limited", from: "From", until: "Until", cardNumber: "Card number",
    unknownCard: "Unknown card…", removeCard: "Remove card", cardOptions: "Access control",
    language: "Language", systemLanguage: "System language", newPin: "New PIN", changePin: "Change PIN",
    currentPin: "Current PIN",
    pinTitle: "PIN code",
    pinStates: { off: "Not stored in HA", unconfirmed: "Stored – not checked", pending: "New code set – waiting for a try", confirmed: "Checked" },
    pinWhat: "The panel never shows codes. To change a code Home Assistant needs the user's current code. With Remember, Home Assistant stores a key (not the code), so next time the new code is enough, for example when guests change. Home Assistant never shows the code.",
    pinRemember: "Remember in HA – next time the new code is enough",
    pinUnconfirmed: "Home Assistant cannot see whether the current code you gave was right. Change the code (the same code is fine) and use it at a door the user has access to.",
    pinPending: "The new code is written to the panel. Use it at a door the user has access to (or on a keypad if the user has areas). If the door opens, all is right.",
    pinPendingDenied: "If the door refuses the code, the current code you gave was wrong: set the user's code on the panel, then change it here with that code as current.",
    pinConfirmed: "Enter a new code and press Change PIN. The old code stops working at once.",
    pinForget: "Forget in HA", pinForgetNote: "Home Assistant forgets the key. The code on the panel does not change.",
    pinNeedCurrent: "Enter the user's current code.", pinNeedNew: "Enter the new code.",
    pinSaveNote: "Save above is for name, dates, card and language – not the code.",
    pinDone: { set_pin: "New code written to the panel.", enable_pin_management: "Stored in HA.", disable_pin_management: "Home Assistant forgot the key." },
    noFreeNumbers: "No free user numbers with a PIN key. Create the user once on the panel and enable PIN management for the number; it can then be reused here.",
    userNumber: "User number", done: "Done", none: "–", missing: "The sensor {entity} is missing.",
    options: {
      card_blocked: "Block card", extended_time: "Extended time", pin_bypass: "PIN bypass",
      priority: "Priority", escort: "Escort", custodian: "Custodian",
    },
    languages: { 7: "Swedish" },
  },
};
const SPC_USERS_CARD_OPTIONS = [
  "card_blocked", "extended_time", "pin_bypass", "priority", "escort", "custodian",
];

class SpcFlexCUsersCard extends SpcFlexCBaseCard {
  style_extra() {
    return `.pin-box { border: 1px solid var(--divider-color); border-radius: 10px; padding: 12px; margin: 12px 0; display: grid; gap: 8px; }
      .pin-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; }
      .pin-title { font-weight: 500; font-size: 1.05em; }
      .pin-state { font-weight: 500; }
      .pin-ok { color: var(--success-color, #43a047); }
      .pin-warn { color: var(--warning-color, #ffa600); }
      .pin-off { margin-top: 4px; }`;
  }

  static get texts() {
    return SPC_USERS_TEXT;
  }

  static get defaults() {
    return {
      users_entity: "sensor.spc_users",
      profiles_entity: "sensor.spc_user_profiles",
      unknown_cards_entity: "sensor.spc_unknown_cards",
      settings_entity: "sensor.spc_panel_settings",
    };
  }

  watched() {
    return [this._config.users_entity, this._config.profiles_entity, this._config.unknown_cards_entity];
  }

  headerActions() {
    return [spcEl("button", { className: "primary", onclick: () => this._open({ mode: "add" }) }, [this._t("add")])];
  }

  _users() {
    return this._attr(this._config.users_entity, "users", []);
  }

  _profiles() {
    return this._attr(this._config.profiles_entity, "profiles", []);
  }

  _profileName(id) {
    const profile = this._profiles().find((p) => p.profile_id === id);
    return profile ? profile.name : String(id);
  }

  body(card) {
    if (!this._hass.states[this._config.users_entity]) {
      card.append(spcEl("div", { className: "error" }, [this._t("missing", { entity: this._config.users_entity })]));
      return;
    }
    const table = spcEl("table");
    table.append(spcEl("tr", {}, [
      spcEl("th", {}, [this._t("number")]), spcEl("th", {}, [this._t("name")]),
      spcEl("th", {}, [this._t("profiles")]), spcEl("th", {}, [this._t("valid")]),
      spcEl("th", {}, [this._t("card")]), spcEl("th", {}, [this._t("pin")]),
    ]));
    for (const user of [...this._users()].sort((a, b) => a.user_id - b.user_id)) {
      const valid = user.valid_from ? `${user.valid_from} – ${user.valid_until || ""}` : this._t("none");
      const row = spcEl("tr", { className: "row", onclick: () => this._open({ mode: "edit", user }) }, [
        spcEl("td", {}, [String(user.user_id)]),
        spcEl("td", {}, [user.name || ""]),
        spcEl("td", {}, [(user.profiles || []).map((p) => this._profileName(p)).join(", ")]),
        spcEl("td", {}, [valid]),
        spcEl("td", {}, [user.card_number || this._t("none")]),
        spcEl("td", {}, [user.pin_managed === "confirmed" ? "✓" : user.pin_managed ? "…" : ""]),
      ]);
      table.append(row);
    }
    card.append(table);

    if (this._editing) {
      card.append(this._editing.mode === "add" ? this._addForm() : this._editForm(this._editing.user));
    }
  }

  _profileChecks(selected) {
    const box = spcEl("div", { className: "checks" });
    for (const profile of this._profiles()) {
      const input = spcEl("input", { type: "checkbox", value: String(profile.profile_id) });
      input.checked = selected.includes(profile.profile_id);
      box.append(spcEl("label", {}, [input, `${profile.profile_id}: ${profile.name}`]));
    }
    return box;
  }

  _checked(box) {
    return [...box.querySelectorAll("input:checked")].map((input) => Number(input.value));
  }

  _languageSelect(current) {
    const select = spcEl("select");
    const installed = this._attr(this._config.settings_entity, "installed_languages", []);
    const names = this._t("languages");
    const options = [["255", this._t("systemLanguage")], ...installed.map((id) => [String(id), names[id] || `${this._t("language")} ${id}`])];
    if (current && !options.some(([value]) => value === String(current))) {
      options.push([String(current), `${this._t("language")} ${current}`]);
    }
    for (const [value, label] of options) {
      const option = spcEl("option", { value }, [label]);
      option.selected = value === String(current ?? "255");
      select.append(option);
    }
    return select;
  }

  _dateFields(from, until) {
    const limited = spcEl("input", { type: "checkbox" });
    limited.checked = Boolean(from);
    const start = spcEl("input", { type: "date", value: from || "" });
    const end = spcEl("input", { type: "date", value: until || "" });
    const sync = () => {
      start.disabled = !limited.checked;
      end.disabled = !limited.checked;
    };
    limited.addEventListener("change", sync);
    sync();
    return { limited, start, end, node: spcEl("div", { className: "rowline" }, [
      spcEl("label", {}, [limited, this._t("dateLimit")]),
      this._t("from"), start, this._t("until"), end,
    ]) };
  }

  _cardFields(number) {
    const input = spcEl("input", { type: "text", inputMode: "numeric", value: number || "" });
    const unknown = spcEl("select");
    unknown.append(spcEl("option", { value: "" }, [this._t("unknownCard")]));
    for (const card of this._attr(this._config.unknown_cards_entity, "cards", [])) {
      unknown.append(spcEl("option", { value: card.card_number || "" }, [
        `${card.last_presented || ""} · ${card.door || ""} · ${card.card_number || ""}`,
      ]));
    }
    unknown.addEventListener("change", () => {
      if (unknown.value) {
        input.value = unknown.value;
      }
    });
    const remove = spcEl("button", { onclick: () => { input.value = "0"; } }, [this._t("removeCard")]);
    return { input, node: spcEl("div", { className: "rowline" }, [input, unknown, remove]) };
  }



  _editForm(user) {
    const form = spcEl("div", { className: "form" });
    form.append(spcEl("h3", {}, [`${user.user_id} ${user.name || ""}`]));
    const name = spcEl("input", { type: "text", maxLength: 16, value: user.name || "" });
    const profiles = this._profileChecks(user.profiles || []);
    const dates = this._dateFields(user.valid_from, user.valid_until);
    const card = this._cardFields(user.card_number);
    const options = spcEl("div", { className: "checks" });
    const optionInputs = {};
    for (const key of SPC_USERS_CARD_OPTIONS) {
      const input = spcEl("input", { type: "checkbox" });
      input.checked = (user.card_options || []).includes(key);
      optionInputs[key] = input;
      options.append(spcEl("label", {}, [input, this._t("options")[key]]));
    }
    const language = this._languageSelect(user.language);
    form.append(
      this._field(this._t("name"), name),
      this._field(this._t("profiles"), profiles),
      dates.node,
      this._field(this._t("cardNumber"), card.node),
      this._field(this._t("cardOptions"), options),
      this._field(this._t("language"), language),
    );
    const save = spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
      const data = { user_id: user.user_id };
      if (name.value.trim() && name.value.trim() !== user.name) data.name = name.value.trim();
      const chosen = this._checked(profiles);
      if (chosen.join() !== (user.profiles || []).join()) data.profiles = chosen;
      if (!dates.limited.checked && user.valid_from) data.no_date_limit = true;
      if (dates.limited.checked && (dates.start.value !== (user.valid_from || "") || dates.end.value !== (user.valid_until || ""))) {
        data.valid_from = dates.start.value;
        data.valid_until = dates.end.value;
      }
      const number = card.input.value.trim() || "0";
      if (number !== (user.card_number || "0")) data.card_number = number;
      for (const key of SPC_USERS_CARD_OPTIONS) {
        if (optionInputs[key].checked !== (user.card_options || []).includes(key)) data[key] = optionInputs[key].checked;
      }
      if (language.value !== String(user.language ?? "255")) data.language = Number(language.value);
      if (Object.keys(data).length > 1 && (await this._call("edit_user", data))) this._close();
    } }, [this._t("save")]);
    form.append(spcEl("div", { className: "rowline" }, [save, spcEl("button", { onclick: () => this._close() }, [this._t("close")])]));
    form.append(spcEl("div", { className: "note" }, [this._t("pinSaveNote")]));
    form.append(this._pinSection(user));
    const remove = spcEl("button", { className: "danger", onclick: async () => {
      if (confirm(this._t("confirmDelete", { id: user.user_id, name: user.name || "" })) &&
          (await this._call("delete_user", { user_id: user.user_id }))) this._close();
    } }, [this._t("delete")]);
    form.append(spcEl("div", { className: "rowline" }, [remove]));
    return form;
  }

  // The PIN code in its own box: what PIN management is, its state, and
  // what to do next (owner 2026-11-14: "fattar inte").
  _pinSection(user) {
    const state = user.pin_managed || "off";
    const tone = { off: "", unconfirmed: "pin-warn", pending: "pin-warn", confirmed: "pin-ok" }[state];
    const box = spcEl("div", { className: "pin-box" }, [
      spcEl("div", { className: "pin-head" }, [
        spcEl("span", { className: "pin-title" }, [this._t("pinTitle")]),
        spcEl("span", { className: `pin-state ${tone}` }, [this._t("pinStates")[state]]),
      ]),
    ]);
    const note = (key) => box.append(spcEl("div", { className: "note" }, [this._t(key)]));
    const field = () => spcEl("input", { type: "password", inputMode: "numeric", autocomplete: "new-password", maxLength: 8 });
    const remembered = state !== "off";
    const current = remembered ? null : field();
    const fresh = field();
    const remember = remembered ? null : spcEl("input", { type: "checkbox", checked: true });
    if (!remembered) note("pinWhat");
    else note({ unconfirmed: "pinUnconfirmed", pending: "pinPending", confirmed: "pinConfirmed" }[state]);
    if (state === "pending") note("pinPendingDenied");
    if (current) box.append(spcEl("div", { className: "rowline" }, [this._t("currentPin"), current]));
    box.append(spcEl("div", { className: "rowline" }, [this._t("newPin"), fresh]));
    if (remember) box.append(spcEl("label", { className: "rowline" }, [remember, this._t("pinRemember")]));
    const change = spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
      const now = current?.value || "";
      const next = fresh.value;
      if (current && !now) { this._error = this._t("pinNeedCurrent"); this._render(); return; }
      if (!next && !(remember?.checked)) { this._error = this._t("pinNeedNew"); this._render(); return; }
      if (current) current.value = "";
      fresh.value = "";
      const id = user.user_id;
      let ok = true;
      let last = "set_pin";
      if (remember?.checked) {
        // Store the key from the current code, then change with the key.
        ok = await this._call("enable_pin_management", { user_id: id, pin: now });
        last = "enable_pin_management";
        if (ok && next) { ok = await this._call("set_pin", { user_id: id, pin: next }); last = "set_pin"; }
      } else if (current) {
        ok = await this._call("set_pin", { user_id: id, pin: next, current_pin: now });
      } else {
        ok = await this._call("set_pin", { user_id: id, pin: next });
      }
      if (ok) await this._pinRefresh(user, last);
    } }, [this._t("changePin")]);
    box.append(spcEl("div", { className: "rowline" }, [change]));
    if (remembered) {
      box.append(spcEl("div", { className: "rowline pin-off" }, [
        spcEl("button", { disabled: this._busy, onclick: async () => {
          if (await this._call("disable_pin_management", { user_id: user.user_id })) await this._pinRefresh(user, "disable_pin_management");
        } }, [this._t("pinForget")]),
        spcEl("span", { className: "note" }, [this._t("pinForgetNote")]),
      ]));
    }
    return box;
  }

  // The edit form is not redrawn by state updates (it would lose what is
  // typed), so after a PIN action wait for the user's new PIN state and
  // redraw it, with a message (owner 2026-11-14: "inget händer").
  async _pinRefresh(user, service) {
    const before = user.pin_managed;
    const entity = this._config.users_entity;
    const stateBefore = this._hass?.states[entity];
    let fresh = null;
    for (let i = 0; i < 40; i++) {
      fresh = this._users().find((u) => u.user_id === user.user_id);
      if (fresh && (fresh.pin_managed !== before || this._hass?.states[entity] !== stateBefore)) break;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    if (fresh && this._editing?.user?.user_id === user.user_id) this._editing.user = fresh;
    this._message = this._t("pinDone")[service] || this._t("done");
    this._render();
  }

  _addForm() {
    const form = spcEl("div", { className: "form" });
    form.append(spcEl("h3", {}, [this._t("add")]));
    const used = new Set(this._users().map((u) => String(u.user_id)));
    const free = Object.keys(this._attr(this._config.users_entity, "pin_managed_numbers", {}))
      .filter((n) => !used.has(n)).sort((a, b) => a - b);
    if (!free.length) {
      form.append(spcEl("div", { className: "note" }, [this._t("noFreeNumbers")]));
      form.append(spcEl("div", { className: "rowline" }, [spcEl("button", { onclick: () => this._close() }, [this._t("close")])]));
      return form;
    }
    const number = spcEl("select");
    for (const n of free) number.append(spcEl("option", { value: n }, [n]));
    const name = spcEl("input", { type: "text", maxLength: 16 });
    const profiles = this._profileChecks([]);
    const pin = spcEl("input", { type: "password", inputMode: "numeric", autocomplete: "new-password", maxLength: 8 });
    const dates = this._dateFields(null, null);
    const card = this._cardFields("");
    const language = this._languageSelect("255");
    form.append(
      this._field(this._t("userNumber"), number),
      this._field(this._t("name"), name),
      this._field(this._t("profiles"), profiles),
      this._field(this._t("pin"), pin),
      dates.node,
      this._field(this._t("cardNumber"), card.node),
      this._field(this._t("language"), language),
    );
    const save = spcEl("button", { className: "primary", onclick: async () => {
      const data = {
        user_id: Number(number.value), name: name.value.trim(),
        profiles: this._checked(profiles), pin: pin.value,
      };
      pin.value = "";
      if (dates.limited.checked) {
        data.valid_from = dates.start.value;
        data.valid_until = dates.end.value;
      }
      if (card.input.value.trim() && card.input.value.trim() !== "0") data.card_number = card.input.value.trim();
      if (language.value !== "255") data.language = Number(language.value);
      if (await this._call("add_user", data)) this._close();
    } }, [this._t("save")]);
    form.append(spcEl("div", { className: "rowline" }, [save, spcEl("button", { onclick: () => this._close() }, [this._t("close")])]));
    return form;
  }
}


spcDefineCard(
  "spc-flexc-users-card",
  SpcFlexCUsersCard,
  "SPC FlexC Users",
  "The panel's users like its web page: add, edit, delete, PIN, card, dates and profiles."
);
