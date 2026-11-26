// SPC FlexC logs card: the panel's own logs like its web page (Logg):
// system log, access log (Passerlogg) per door, zone log, wireless log and
// the FlexC logs, read on request with get_log.

const SPC_LOGS_TEXT = {
  sv: {
    title: "SPC loggar", log: "Logg", door: "Dörr", zone: "Sektion", ats: "ATS", atp: "ATP",
    count: "Antal", read: "Läs", time: "Tid", event: "Händelse", user: "Användare",
    empty: "Inga rader.", shown: "{count} av {total} rader",
    kinds: {
      system: "Systemlogg", access: "Passerlogg", zone: "Sektionslogg", wireless: "Trådlös logg",
      ats: "FlexC ATS-händelser", ats_network: "FlexC ATS-nätverk", atp: "FlexC ATP", atp_network: "FlexC ATP-nätverk",
    },
  },
  en: {
    title: "SPC logs", log: "Log", door: "Door", zone: "Zone", ats: "ATS", atp: "ATP",
    count: "Lines", read: "Read", time: "Time", event: "Event", user: "User",
    empty: "No lines.", shown: "{count} of {total} lines",
    kinds: {
      system: "System log", access: "Access log", zone: "Zone log", wireless: "Wireless log",
      ats: "FlexC ATS events", ats_network: "FlexC ATS network", atp: "FlexC ATP", atp_network: "FlexC ATP network",
    },
  },
};
const SPC_LOG_KINDS = ["system", "access", "zone", "wireless", "ats", "ats_network", "atp", "atp_network"];
// Access log colours like the web page's Passerlogg.
const SPC_ACCESS_COLOURS = {
  granted: "#43a047", denied: "#e53935", forced_open: "#e53935", invalid_format: "#e53935",
  unknown_card: "#e53935", code_lockout: "#e53935", door_left_open: "#ffa600",
  door_normal: "#1e3a8a", door_blocked: "#1e3a8a", door_unlocked: "#1e3a8a", door_release: "#43a047",
};

class SpcFlexCLogsCard extends SpcFlexCBaseCard {
  static get texts() {
    return SPC_LOGS_TEXT;
  }

  static get defaults() {
    return { log: "system", limit: 100 };
  }

  style_extra() {
    return `.log td.time { white-space: nowrap; color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums; }`;
  }

  _choice() {
    this._picked ||= { log: this._config.log, id: "", atp: "1", limit: String(this._config.limit) };
    return this._picked;
  }

  body(card) {
    const choice = this._choice();
    const kind = spcEl("select", { onchange: () => { choice.log = kind.value; choice.id = ""; this._render(); } });
    for (const key of SPC_LOG_KINDS) {
      const option = spcEl("option", { value: key }, [this._t("kinds")[key]]);
      option.selected = key === choice.log;
      kind.append(option);
    }
    const controls = [this._field(this._t("log"), kind)];
    let idSelect = null;
    if (choice.log === "access") {
      idSelect = this._select(spcEntities(this._hass, "sensor", "door_id").filter((d) => d.entity.endsWith("_mode"))
        .map((d) => [String(d.door_id), `${d.door_id} ${d.zone_name || ""}`]), choice.id);
      controls.push(this._field(this._t("door"), idSelect));
    } else if (choice.log === "zone") {
      const zones = spcEntities(this._hass, "binary_sensor", "zone_id").filter((z) => z.logic_input !== undefined);
      idSelect = this._select(zones.map((z) => [String(z.zone_id), `${z.zone_id} ${z.zone_name || ""}`]), choice.id);
      controls.push(this._field(this._t("zone"), idSelect));
    } else if (choice.log.startsWith("ats") || choice.log.startsWith("atp")) {
      idSelect = spcEl("input", { type: "number", min: 1, max: 32, value: choice.id || "1" });
      controls.push(this._field(this._t("ats"), idSelect));
    }
    let atp = null;
    if (choice.log.startsWith("atp")) {
      atp = spcEl("input", { type: "number", min: 1, max: 16, value: choice.atp });
      controls.push(this._field(this._t("atp"), atp));
    }
    const limit = spcEl("input", { type: "number", min: 1, max: 2000, value: choice.limit });
    controls.push(this._field(this._t("count"), limit));
    const read = spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
      choice.id = idSelect ? idSelect.value : "";
      choice.atp = atp ? atp.value : "1";
      choice.limit = limit.value;
      const data = { log: choice.log, limit: Number(choice.limit) || 100 };
      if (idSelect && idSelect.value) data.id = Number(idSelect.value);
      if (atp) data.atp = Number(atp.value) || 1;
      const result = await this._call("get_log", data, { response: true });
      if (result) {
        this._result = result;
        this._render();
      }
    } }, [this._t("read")]);
    controls.push(read);
    card.append(spcEl("div", { className: "rowline" }, controls));
    if (this._result) card.append(this._table(this._result));
  }

  _select(options, current) {
    const select = spcEl("select");
    for (const [value, label] of options) {
      const option = spcEl("option", { value }, [label]);
      option.selected = value === current;
      select.append(option);
    }
    return select;
  }

  _table(result) {
    const wrap = spcEl("div", {}, [spcEl("div", { className: "note" }, [this._t("shown", { count: result.count ?? 0, total: result.total ?? 0 })])]);
    const entries = result.entries || [];
    if (!entries.length) {
      wrap.append(spcEl("div", { className: "note" }, [this._t("empty")]));
      return wrap;
    }
    const access = result.log === "access";
    const table = spcEl("table", { className: "log" }, [spcEl("tr", {}, [
      spcEl("th", {}, [this._t("time")]), spcEl("th", {}, [this._t("event")]),
      access ? spcEl("th", {}, [this._t("door")]) : null, access ? spcEl("th", {}, [this._t("user")]) : null,
    ])]);
    for (const entry of entries) {
      const time = String(entry.time || "").replace("T", " ").slice(0, 19);
      let text = entry.text || entry.event || entry.message || "";
      if (!text) {
        text = Object.entries(entry).filter(([k]) => k !== "time").map(([k, v]) => `${k}: ${v}`).join(", ");
      }
      const event = spcEl("td", {}, [access ? String(text).split(",(")[0] : text]);
      if (access && SPC_ACCESS_COLOURS[entry.type_name]) event.style.color = SPC_ACCESS_COLOURS[entry.type_name];
      table.append(spcEl("tr", {}, [
        spcEl("td", { className: "time" }, [time]), event,
        access ? spcEl("td", {}, [entry.door_id ? `${entry.door_id}- ${entry.door_name || ""}` : ""]) : null,
        access ? spcEl("td", {}, [entry.user_id ? `${entry.user_id} ${entry.user_name || ""}` : ""]) : null,
      ]));
    }
    wrap.append(spcEl("div", { className: "scroll" }, [table]));
    return wrap;
  }
}

spcDefineCard(
  "spc-flexc-logs-card",
  SpcFlexCLogsCard,
  "SPC FlexC Logs",
  "The panel's logs like its web page: system, access (per door), zone, wireless and FlexC."
);
