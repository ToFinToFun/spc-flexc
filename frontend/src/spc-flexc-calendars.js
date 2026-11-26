// SPC FlexC calendars card: the panel's calendars and exception days like its
// web page (Konfiguration > Kalendrar / Undantag): add, rename and delete a
// calendar, set the week types of the year and each week type's day times,
// and add, edit and delete exception days.

const SPC_CAL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

const SPC_CALENDARS_TEXT = {
  sv: {
    title: "SPC kalendrar", calendars: "Kalendrar", exceptions: "Undantag",
    addCalendar: "Lägg till kalender", addException: "Lägg till undantag", id: "ID",
    weekTypes: "Veckotyper", weekTypesNote: "Veckotyp (1–3) för varje vecka 1–53. Klicka för att växla.",
    week: "Veckotyp {n}", times: "Tider", timesNote: "Perioder som 06:00-23:00, flera med mellanslag. Bara starttid: 09:00.",
    deleteCalendar: "Ta bort kalender", confirmDeleteCalendar: "Ta bort kalender {id} {name}?",
    confirmDeleteException: "Ta bort undantag {name}?", start: "Startdatum", end: "Slutdatum",
    calendarsIn: "Gäller kalendrar", noCalendars: "Inga kalendrar.", noExceptions: "Inga undantag.",
    saveWeek: "Spara veckotyp {n}", nowWeek: "Nu: veckotyp {n}",
    days: { mon: "Måndag", tue: "Tisdag", wed: "Onsdag", thu: "Torsdag", fri: "Fredag", sat: "Lördag", sun: "Söndag" },
  },
  en: {
    title: "SPC calendars", calendars: "Calendars", exceptions: "Exceptions",
    addCalendar: "Add calendar", addException: "Add exception", id: "ID",
    weekTypes: "Week types", weekTypesNote: "Week type (1–3) of every week 1–53. Click to change.",
    week: "Week type {n}", times: "Times", timesNote: "Periods like 06:00-23:00, several separated by spaces. Start only: 09:00.",
    deleteCalendar: "Delete calendar", confirmDeleteCalendar: "Delete calendar {id} {name}?",
    confirmDeleteException: "Delete exception {name}?", start: "Start date", end: "End date",
    calendarsIn: "Applies to calendars", noCalendars: "No calendars.", noExceptions: "No exceptions.",
    saveWeek: "Save week type {n}", nowWeek: "Now: week type {n}",
    days: { mon: "Monday", tue: "Tuesday", wed: "Wednesday", thu: "Thursday", fri: "Friday", sat: "Saturday", sun: "Sunday" },
  },
};

// "06:00;23:00 09:00;--:--" <-> "06:00-23:00 09:00"
function spcPeriodsToText(value) {
  return String(value || "").split(/\s+/).filter(Boolean)
    .map((item) => {
      const [start, end] = item.split(";");
      return end && end !== "--:--" ? `${start}-${end}` : start;
    }).join(" ");
}

function spcTextToPeriods(value) {
  return String(value || "").split(/\s+/).filter(Boolean)
    .map((item) => {
      const [start, end] = item.split("-");
      return `${start};${end || "--:--"}`;
    }).join(" ");
}

class SpcFlexCCalendarsCard extends SpcFlexCBaseCard {
  static get texts() {
    return SPC_CALENDARS_TEXT;
  }

  watched() {
    return this._calendarIds();
  }

  _calendarIds() {
    const states = this._hass?.states || {};
    const registry = this._hass?.entities;
    return Object.keys(states)
      .filter((id) => id.startsWith("calendar.") && states[id].attributes?.calendar_id !== undefined)
      .filter((id) => (registry?.[id] ? registry[id].platform === "spc_flexc" : id.startsWith("calendar.spc_")))
      .sort((a, b) => states[a].attributes.calendar_id - states[b].attributes.calendar_id);
  }

  _calendars() {
    return this._calendarIds().map((id) => ({ entity: id, ...this._hass.states[id].attributes }));
  }

  _exceptions() {
    const seen = new Map();
    for (const calendar of this._calendars()) {
      for (const exception of calendar.exceptions || []) {
        seen.set(exception.exception_id, exception);
      }
    }
    return [...seen.values()].sort((a, b) => String(a.start).localeCompare(String(b.start)));
  }

  headerActions() {
    return [
      spcEl("button", { onclick: () => this._open({ mode: "add_calendar" }) }, [this._t("addCalendar")]),
      spcEl("button", { onclick: () => this._open({ mode: "add_exception" }) }, [this._t("addException")]),
    ];
  }

  body(card) {
    const calendars = this._calendars();
    card.append(spcEl("h3", {}, [this._t("calendars")]));
    if (!calendars.length) {
      card.append(spcEl("div", { className: "note" }, [this._t("noCalendars")]));
    } else {
      const table = spcEl("table", {}, [spcEl("tr", {}, [
        spcEl("th", {}, [this._t("id")]), spcEl("th", {}, [this._t("name")]), spcEl("th", {}, [this._t("weekTypes")]),
      ])]);
      for (const calendar of calendars) {
        const selected = this._editing?.mode === "calendar" && this._editing.id === calendar.calendar_id;
        table.append(spcEl("tr", {
          className: `row${selected ? " selected" : ""}`,
          onclick: () => this._open({ mode: "calendar", id: calendar.calendar_id, week: 1 }),
        }, [
          spcEl("td", {}, [String(calendar.calendar_id)]),
          spcEl("td", {}, [calendar.calendar_name || ""]),
          spcEl("td", {}, [calendar.week_type_now ? this._t("nowWeek", { n: calendar.week_type_now }) : ""]),
        ]));
      }
      card.append(table);
    }
    if (this._editing?.mode === "calendar") {
      const calendar = calendars.find((c) => c.calendar_id === this._editing.id);
      if (calendar) card.append(this._calendarForm(calendar));
    } else if (this._editing?.mode === "add_calendar") {
      card.append(this._addCalendarForm(calendars));
    }

    card.append(spcEl("h3", {}, [this._t("exceptions")]));
    const exceptions = this._exceptions();
    if (!exceptions.length) {
      card.append(spcEl("div", { className: "note" }, [this._t("noExceptions")]));
    } else {
      const table = spcEl("table", {}, [spcEl("tr", {}, [
        spcEl("th", {}, [this._t("name")]), spcEl("th", {}, [this._t("start")]), spcEl("th", {}, [this._t("end")]),
        spcEl("th", {}, [this._t("times")]), spcEl("th", {}, [this._t("calendars")]),
      ])]);
      for (const exception of exceptions) {
        table.append(spcEl("tr", { className: "row", onclick: () => this._open({ mode: "exception", exception }) }, [
          spcEl("td", {}, [exception.name || ""]), spcEl("td", {}, [exception.start || ""]),
          spcEl("td", {}, [exception.end || ""]), spcEl("td", {}, [spcPeriodsToText(exception.times)]),
          spcEl("td", {}, [(exception.calendars || []).join(", ")]),
        ]));
      }
      card.append(table);
    }
    if (this._editing?.mode === "exception" || this._editing?.mode === "add_exception") {
      card.append(this._exceptionForm(this._editing.exception));
    }
  }

  _weekTypeGrid(value) {
    const types = String(value || "").padEnd(53, "1").slice(0, 53).split("");
    const grid = spcEl("div", { className: "weeks" });
    types.forEach((type, index) => {
      const button = spcEl("button", { className: `week w${type}`, title: `v${index + 1}` }, [`${index + 1}:${type}`]);
      button.addEventListener("click", () => {
        types[index] = String((Number(types[index]) % 3) + 1);
        button.textContent = `${index + 1}:${types[index]}`;
        button.className = `week w${types[index]}`;
      });
      grid.append(button);
    });
    return { node: grid, value: () => types.join("") };
  }

  style_extra() {
    return `
      .weeks { display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: 3px; }
      .week { padding: 2px; font-size: 0.75em; }
      .week.w1 { background: var(--card-background-color); }
      .week.w2 { background: rgba(30, 136, 229, 0.25); }
      .week.w3 { background: rgba(251, 140, 0, 0.3); }
      .tabs { display: flex; gap: 4px; }
      .tabs button.on { background: var(--secondary-background-color); font-weight: 500; }
      .days { display: grid; grid-template-columns: max-content 1fr; gap: 6px 10px; align-items: center; }
    `;
  }

  _calendarForm(calendar) {
    const id = calendar.calendar_id;
    const form = spcEl("div", { className: "form" }, [spcEl("h3", {}, [`${id} ${calendar.calendar_name || ""}`])]);
    const name = spcEl("input", { type: "text", maxLength: 16, value: calendar.calendar_name || "" });
    const grid = this._weekTypeGrid(calendar.week_types);
    form.append(
      this._field(this._t("name"), name),
      this._field(this._t("weekTypes"), spcEl("div", { className: "note" }, [this._t("weekTypesNote")]), grid.node),
      spcEl("div", { className: "rowline" }, [
        spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
          const data = { calendar_id: id };
          if (name.value.trim() && name.value.trim() !== calendar.calendar_name) data.name = name.value.trim();
          if (grid.value() !== calendar.week_types) data.week_types = grid.value();
          if (Object.keys(data).length > 1) await this._call("set_calendar", data);
        } }, [this._t("save")]),
      ]),
    );
    // Day times per week type
    const week = this._editing.week || 1;
    const tabs = spcEl("div", { className: "tabs" });
    for (const n of [1, 2, 3]) {
      tabs.append(spcEl("button", { className: n === week ? "on" : "", onclick: () => {
        this._editing.week = n;
        this._render();
      } }, [this._t("week", { n })]));
    }
    const times = (calendar.weeks || {})[String(week)] || {};
    const days = spcEl("div", { className: "days" });
    const inputs = {};
    for (const day of SPC_CAL_DAYS) {
      inputs[day] = spcEl("input", { type: "text", value: spcPeriodsToText(times[day]), placeholder: "06:00-23:00" });
      days.append(spcEl("span", {}, [this._t("days")[day]]), inputs[day]);
    }
    form.append(
      this._field(this._t("times"), tabs, spcEl("div", { className: "note" }, [this._t("timesNote")]), days),
      spcEl("div", { className: "rowline" }, [
        spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
          const data = { calendar_id: id, week_type: week };
          for (const day of SPC_CAL_DAYS) data[day] = spcTextToPeriods(inputs[day].value);
          await this._call("set_calendar_week", data);
        } }, [this._t("saveWeek", { n: week })]),
        this._closeButton(),
      ]),
      spcEl("div", { className: "rowline" }, [
        this._confirmButton(this._t("deleteCalendar"),
          this._t("confirmDeleteCalendar", { id, name: calendar.calendar_name || "" }),
          () => this._call("delete_calendar", { calendar_id: id })),
      ]),
    );
    return form;
  }

  _addCalendarForm(calendars) {
    const used = new Set(calendars.map((c) => c.calendar_id));
    let free = 1;
    while (used.has(free)) free += 1;
    const form = spcEl("div", { className: "form" }, [spcEl("h3", {}, [this._t("addCalendar")])]);
    const id = spcEl("input", { type: "number", min: 1, max: 64, value: free });
    const name = spcEl("input", { type: "text", maxLength: 16 });
    const days = spcEl("div", { className: "days" });
    const inputs = {};
    for (const day of SPC_CAL_DAYS) {
      inputs[day] = spcEl("input", { type: "text", placeholder: "06:00-23:00" });
      days.append(spcEl("span", {}, [this._t("days")[day]]), inputs[day]);
    }
    form.append(
      this._field(this._t("id"), id),
      this._field(this._t("name"), name),
      this._field(this._t("week", { n: 1 }), spcEl("div", { className: "note" }, [this._t("timesNote")]), days),
      spcEl("div", { className: "rowline" }, [
        spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
          const data = { calendar_id: Number(id.value), name: name.value.trim() };
          for (const day of SPC_CAL_DAYS) {
            if (inputs[day].value.trim()) data[day] = spcTextToPeriods(inputs[day].value);
          }
          if (await this._call("add_calendar", data)) this._close();
        } }, [this._t("save")]),
        this._closeButton(),
      ]),
    );
    return form;
  }

  _exceptionForm(exception) {
    const form = spcEl("div", { className: "form" }, [spcEl("h3", {}, [exception ? exception.name : this._t("addException")])]);
    const name = spcEl("input", { type: "text", maxLength: 16, value: exception?.name || "" });
    const start = spcEl("input", { type: "date", value: exception?.start || "" });
    const end = spcEl("input", { type: "date", value: exception?.end || "" });
    const times = spcEl("input", { type: "text", value: spcPeriodsToText(exception?.times), placeholder: "06:00-23:00" });
    const checks = spcEl("div", { className: "checks" });
    for (const calendar of this._calendars()) {
      const input = spcEl("input", { type: "checkbox", value: String(calendar.calendar_id) });
      input.checked = (exception?.calendars || []).includes(calendar.calendar_id);
      checks.append(spcEl("label", {}, [input, `${calendar.calendar_id}: ${calendar.calendar_name || ""}`]));
    }
    form.append(
      this._field(this._t("name"), name),
      spcEl("div", { className: "rowline" }, [this._t("start"), start, this._t("end"), end]),
      this._field(this._t("times"), spcEl("div", { className: "note" }, [this._t("timesNote")]), times),
      this._field(this._t("calendarsIn"), checks),
    );
    const save = spcEl("button", { className: "primary", disabled: this._busy, onclick: async () => {
      const data = {
        name: name.value.trim(), start_date: start.value, end_date: end.value || start.value,
        times: spcTextToPeriods(times.value),
        calendars: [...checks.querySelectorAll("input:checked")].map((i) => Number(i.value)),
      };
      if (exception) data.exception_id = exception.exception_id;
      if (await this._call(exception ? "edit_calendar_exception" : "add_calendar_exception", data)) this._close();
    } }, [this._t("save")]);
    form.append(spcEl("div", { className: "rowline" }, [save, this._closeButton()]));
    if (exception) {
      form.append(spcEl("div", { className: "rowline" }, [
        this._confirmButton(this._t("delete"), this._t("confirmDeleteException", { name: exception.name }),
          () => this._call("delete_calendar_exception", { exception_id: exception.exception_id })),
      ]));
    }
    return form;
  }
}

spcDefineCard(
  "spc-flexc-calendars-card",
  SpcFlexCCalendarsCard,
  "SPC FlexC Calendars",
  "The panel's calendars and exception days like its web page: add, edit and delete."
);
