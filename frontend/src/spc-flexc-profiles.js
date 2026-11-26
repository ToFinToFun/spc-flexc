// SPC FlexC user profiles card: the panel's user profiles like its web page
// (Användare > Användarprofiler): name, areas and calendar; add and delete.
// Door settings and user rights are shown as the panel reports them; their
// values are not mapped yet, so they are not edited here.

const SPC_PROFILES_TEXT = {
  sv: {
    title: "SPC användarprofiler", addProfile: "Lägg till profil", id: "ID",
    areas: "Områden", calendar: "Kalender", noCalendar: "Ingen kalender", doors: "Dörrar",
    doorsNote: "Dörrinställningarna visas som centralen rapporterar dem (betydelsen är inte kartlagd än).",
    users: "Användare", deleteProfile: "Ta bort profil", confirmDelete: "Ta bort profil {id} {name}?",
    inUse: "Används av {n} användare.", noProfiles: "Inga profiler.",
  },
  en: {
    title: "SPC user profiles", addProfile: "Add profile", id: "ID",
    areas: "Areas", calendar: "Calendar", noCalendar: "No calendar", doors: "Doors",
    doorsNote: "Door settings are shown as the panel reports them (their meaning is not mapped yet).",
    users: "Users", deleteProfile: "Delete profile", confirmDelete: "Delete profile {id} {name}?",
    inUse: "Used by {n} users.", noProfiles: "No profiles.",
  },
};


class SpcFlexCProfilesCard extends SpcFlexCBaseCard {
  static get texts() {
    return SPC_PROFILES_TEXT;
  }

  static get defaults() {
    return { profiles_entity: "sensor.spc_user_profiles", users_entity: "sensor.spc_users" };
  }

  watched() {
    return [this._config.profiles_entity, this._config.users_entity];
  }

  headerActions() {
    return [spcEl("button", { className: "primary", onclick: () => this._open({ mode: "add" }) }, [this._t("addProfile")])];
  }

  _profiles() {
    return [...this._attr(this._config.profiles_entity, "profiles", [])].sort((a, b) => a.profile_id - b.profile_id);
  }

  _areas() {
    return spcEntities(this._hass, "alarm_control_panel", "area_id");
  }

  _calendars() {
    return spcEntities(this._hass, "calendar", "calendar_id");
  }

  _doors() {
    return spcEntities(this._hass, "sensor", "door_id").filter((d) => d.entity.endsWith("_mode"));
  }

  _areaName(id) {
    return this._areas().find((a) => a.area_id === id)?.area_name || String(id);
  }

  _users(profileId) {
    return this._attr(this._config.users_entity, "users", []).filter((u) => (u.profiles || []).includes(profileId));
  }

  body(card) {
    if (!this._state(this._config.profiles_entity)) {
      card.append(spcEl("div", { className: "error" }, [this._t("missing", { entity: this._config.profiles_entity })]));
      return;
    }
    const profiles = this._profiles();
    if (!profiles.length) {
      card.append(spcEl("div", { className: "note" }, [this._t("noProfiles")]));
    }
    const table = spcEl("table", {}, [spcEl("tr", {}, [
      spcEl("th", {}, [this._t("id")]), spcEl("th", {}, [this._t("name")]), spcEl("th", {}, [this._t("areas")]),
      spcEl("th", {}, [this._t("calendar")]), spcEl("th", {}, [this._t("users")]),
    ])]);
    const calendars = this._calendars();
    for (const profile of profiles) {
      const calendar = calendars.find((c) => c.calendar_id === profile.calendar);
      table.append(spcEl("tr", { className: "row", onclick: () => this._open({ mode: "edit", profile }) }, [
        spcEl("td", {}, [String(profile.profile_id)]), spcEl("td", {}, [profile.name || ""]),
        spcEl("td", {}, [(profile.areas || []).map((a) => this._areaName(a)).join(", ")]),
        spcEl("td", {}, [profile.calendar ? `${profile.calendar} ${calendar?.calendar_name || ""}` : this._t("none")]),
        spcEl("td", {}, [String(this._users(profile.profile_id).length)]),
      ]));
    }
    card.append(table);
    if (this._editing) {
      card.append(this._form(this._editing.mode === "edit" ? this._editing.profile : null, profiles));
    }
  }

  _form(profile, profiles) {
    const form = spcEl("div", { className: "form" }, [
      spcEl("h3", {}, [profile ? `${profile.profile_id} ${profile.name}` : this._t("addProfile")]),
    ]);
    let id = null;
    if (!profile) {
      const used = new Set(profiles.map((p) => p.profile_id));
      let free = 1;
      while (used.has(free)) free += 1;
      id = spcEl("input", { type: "number", min: 1, max: 255, value: free });
      form.append(this._field(this._t("id"), id));
    }
    const name = spcEl("input", { type: "text", maxLength: 16, value: profile?.name || "" });
    const areas = spcEl("div", { className: "checks" });
    for (const area of this._areas()) {
      const input = spcEl("input", { type: "checkbox", value: String(area.area_id) });
      input.checked = (profile?.areas || []).includes(area.area_id);
      areas.append(spcEl("label", {}, [input, `${area.area_id}: ${area.area_name || ""}`]));
    }
    const calendar = spcEl("select");
    calendar.append(spcEl("option", { value: "0" }, [this._t("noCalendar")]));
    for (const c of this._calendars()) {
      const option = spcEl("option", { value: String(c.calendar_id) }, [`${c.calendar_id}: ${c.calendar_name || ""}`]);
      option.selected = c.calendar_id === profile?.calendar;
      calendar.append(option);
    }
    form.append(
      this._field(this._t("name"), name),
      this._field(this._t("areas"), areas),
      this._field(this._t("calendar"), calendar),
    );
    if (profile) {
      const doors = this._doors();
      const list = spcEl("div", { className: "note" }, [this._t("doorsNote")]);
      const rows = Object.entries(profile.doors || {}).map(([doorId, value]) => {
        const door = doors.find((d) => String(d.door_id) === doorId);
        return spcEl("div", {}, [`${doorId} ${door?.zone_name || ""}: ${value}`]);
      });
      form.append(this._field(this._t("doors"), list, ...rows));
      const users = this._users(profile.profile_id);
      if (users.length) form.append(spcEl("div", { className: "note" }, [this._t("inUse", { n: users.length })]));
    }
    const save = spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
      const chosen = [...areas.querySelectorAll("input:checked")].map((i) => Number(i.value));
      if (!profile) {
        const data = { profile_id: Number(id.value), name: name.value.trim(), areas: chosen, calendar: Number(calendar.value) };
        if (await this._call("add_user_profile", data)) this._close();
        return;
      }
      const data = { profile_id: profile.profile_id };
      if (name.value.trim() && name.value.trim() !== profile.name) data.name = name.value.trim();
      if (chosen.join() !== (profile.areas || []).join()) data.areas = chosen;
      if (Number(calendar.value) !== profile.calendar) data.calendar = Number(calendar.value);
      if (Object.keys(data).length > 1 && (await this._call("edit_user_profile", data))) this._close();
    } }, [this._t("save")]);
    form.append(spcEl("div", { className: "rowline" }, [save, this._closeButton()]));
    if (profile) {
      form.append(spcEl("div", { className: "rowline" }, [
        this._confirmButton(this._t("deleteProfile"), this._t("confirmDelete", { id: profile.profile_id, name: profile.name }),
          () => this._call("delete_user_profile", { profile_id: profile.profile_id })),
      ]));
    }
    return form;
  }
}

spcDefineCard(
  "spc-flexc-profiles-card",
  SpcFlexCProfilesCard,
  "SPC FlexC User profiles",
  "The panel's user profiles like its web page: name, areas and calendar; add and delete."
);
