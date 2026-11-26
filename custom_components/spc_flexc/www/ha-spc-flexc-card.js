const CARD_VERSION = "1.2.12";

class SpcFlexCCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("spc-flexc-card-editor");
  }

  static getStubConfig(hass) {
    const alarmEntities = Object.entries(hass.states)
      .filter(([id]) => id.startsWith("alarm_control_panel."));

    const systemEntity = alarmEntities.find(([, stateObj]) =>
      stateObj?.attributes?.areas && typeof stateObj.attributes.areas === "object"
    );

    const entity = systemEntity?.[0] || alarmEntities[0]?.[0];
    return entity ? { entity } : {};
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("SPC FlexC Card requires an alarm_control_panel entity.");
    }

    const entityChanged = this._config?.entity !== config.entity;

    this._config = {
      name: "SPC FlexC",
      show_controls: true,
      confirm_actions: true,
      ...config,
    };

    const validTabs = [
      "system",
      "areas",
      "zones",
      "doors",
      "outputs",
      "technical",
    ];

    if (validTabs.includes(config.view)) {
      this._activeTab = config.view;
    } else if (entityChanged || !validTabs.includes(this._activeTab)) {
      this._activeTab = this._loadActiveTab(config.entity) || "system";
    }

    if (entityChanged) {
      // Invalidate any registry request started for the previous panel.
      this._scopeGeneration = (this._scopeGeneration || 0) + 1;
      this._diagnosticScope = null;
      this._diagnosticScopeForEntity = null;
      this._diagnosticScopeLoading = false;
      this._diagnosticScopeRetryAt = 0;
    }

    this._render();
    this._ensureDiagnosticScope();
  }

  set hass(hass) {
    this._hass = hass;
    this._reconcileLiveZoneStates();
    this._render();
    this._ensureDiagnosticScope();
    this._ensureStateSubscription();
  }

  connectedCallback() {
    this._ensureStateSubscription();
  }

  disconnectedCallback() {
    if (this._spcStateUnsubscribe) {
      this._spcStateUnsubscribe();
      this._spcStateUnsubscribe = null;
    }
  }

  _t(key, variables = {}, fallback = key) {
    if (typeof spcFlexCTranslate === "function") {
      return spcFlexCTranslate(this._hass, key, variables, fallback);
    }
    return fallback;
  }

  _tCount(key, count, variables = {}) {
    const suffix = Number(count) === 1 ? "one" : "other";
    return this._t(`${key}.${suffix}`, { count, ...variables }, String(count));
  }

  _reconcileLiveZoneStates() {
    if (!this._spcLiveStates?.size || !this._hass?.states) {
      return;
    }

    for (const [entityId, liveState] of this._spcLiveStates) {
      const currentState = this._hass.states[entityId];

      if (!currentState) {
        continue;
      }

      const currentUpdated = Date.parse(currentState.last_updated || "");
      const liveUpdated = Date.parse(liveState.last_updated || "");

      if (
        currentState === liveState ||
        (
          Number.isFinite(currentUpdated) &&
          Number.isFinite(liveUpdated) &&
          currentUpdated >= liveUpdated
        )
      ) {
        this._spcLiveStates.delete(entityId);
      }
    }
  }

  async _ensureStateSubscription() {
    if (
      this._spcStateUnsubscribe ||
      this._spcStateSubscriptionPending ||
      !this.isConnected ||
      !this._hass?.connection?.subscribeEvents
    ) {
      return;
    }

    this._spcStateSubscriptionPending = true;

    try {
      const unsubscribe = await this._hass.connection.subscribeEvents(
        (event) => {
          const entityId = event?.data?.entity_id;
          const newState = event?.data?.new_state || null;
          const oldState = event?.data?.old_state || null;
          const attrs = newState?.attributes || oldState?.attributes || {};
          const isSpcZone =
            entityId?.startsWith("binary_sensor.") &&
            attrs.zone_id != null &&
            attrs.area_id != null &&
            attrs.spc_zone_type != null;

          if (!isSpcZone) {
            return;
          }

          this._spcLiveStates ||= new Map();

          if (newState) {
            this._spcLiveStates.set(entityId, newState);
          } else {
            this._spcLiveStates.delete(entityId);
          }

          if (this.isConnected) {
            this._render();
          }
        },
        "state_changed"
      );

      if (!this.isConnected) {
        unsubscribe();
        return;
      }

      this._spcStateUnsubscribe = unsubscribe;
    } catch (error) {
      console.warn(
        "SPC FlexC Card: unable to subscribe to live zone state changes",
        error
      );
    } finally {
      this._spcStateSubscriptionPending = false;
    }
  }

  _activeTabStorageKey(entityId = this._config?.entity) {
    if (!entityId) {
      return null;
    }

    return `spc-flexc-card:${entityId}:active-tab`;
  }

  _loadActiveTab(entityId) {
    const key = this._activeTabStorageKey(entityId);

    if (!key) {
      return null;
    }

    try {
      const value = window.localStorage.getItem(key);
      return [
        "system",
        "areas",
        "zones",
        "doors",
        "outputs",
        "technical",
      ].includes(value)
        ? value
        : null;
    } catch {
      return null;
    }
  }

  _saveActiveTab(tabId) {
    const key = this._activeTabStorageKey();

    if (!key) {
      return;
    }

    try {
      window.localStorage.setItem(key, tabId);
    } catch {
      // Home Assistant can still keep the tab during normal rerenders even
      // when persistent browser storage is unavailable.
    }
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return {
      columns: 12,
      min_columns: 6,
    };
  }

  _escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _locale() {
    return this._hass?.locale?.language || navigator.language || undefined;
  }

  _formatDateTime(value) {
    if (!value) return null;

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;

    try {
      return new Intl.DateTimeFormat(this._locale(), {
        dateStyle: "short",
        timeStyle: "short",
      }).format(date);
    } catch {
      return date.toLocaleString(this._locale());
    }
  }

  _formatEventDateTime(value) {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return new Intl.DateTimeFormat(this._locale(), {
      dateStyle: "short",
      timeStyle: "medium",
    }).format(date);
  }

  _stateLabel(state) {
    const key = {
      disarmed: "state.disarmed",
      armed_away: "state.armed",
      armed_home: "state.part_a",
      armed_night: "state.part_b",
      armed_vacation: "state.armed",
      armed_custom_bypass: "state.armed",
      arming: "state.arming",
      disarming: "state.disarming",
      triggered: "state.alarm",
      pending: "state.pending",
      unavailable: "state.unavailable",
      unknown: "state.unknown",
      mixed: "state.mixed",
    }[state];

    return key ? this._t(key) : state || this._t("state.unknown_short");
  }

  _stateClass(state) {
    switch (state) {
      case "disarmed":
        return "ok";

      case "armed_away":
      case "armed_home":
      case "armed_night":
      case "armed_vacation":
      case "armed_custom_bypass":
      case "arming":
      case "pending":
        return "warning";

      case "mixed":
        return "partial";

      case "triggered":
        return "danger";

      default:
        return "muted";
    }
  }

  _stateIcon(state) {
    switch (state) {
      case "disarmed":
        return "mdi:lock-open-variant";

      case "armed_away":
      case "armed_home":
      case "armed_night":
      case "armed_vacation":
      case "armed_custom_bypass":
        return "mdi:lock";

      case "arming":
      case "pending":
        return "mdi:lock-clock";

      case "mixed":
        return "mdi:lock-alert";

      case "triggered":
        return "mdi:alarm-light";

      case "unavailable":
        return "mdi:alert-circle";

      default:
        return "mdi:shield-outline";
    }
  }

  _modeLabel(mode) {
    const normalized = String(mode ?? "").toLowerCase();
    const key = {
      unset: "state.disarmed_masc",
      disarmed: "state.disarmed_masc",
      full_set: "state.armed_masc",
      fullset: "state.armed_masc",
      set: "state.armed_masc",
      armed: "state.armed_masc",
      part_set_a: "state.part_a",
      partset_a: "state.part_a",
      part_set_b: "state.part_b",
      partset_b: "state.part_b",
      part_set: "state.partial",
      partset: "state.partial",
      unknown: "state.unknown_short",
    }[normalized];

    return key ? this._t(key) : String(mode ?? this._t("state.unknown_short"));
  }

  _modeClass(mode) {
    const normalized = String(mode ?? "").toLowerCase();

    if (normalized === "unset" || normalized === "disarmed") {
      return "ok";
    }

    if (normalized.includes("set") || normalized.includes("armed")) {
      return "warning";
    }

    return "muted";
  }

  _getAlarmEntity() {
    if (!this._hass || !this._config) {
      return undefined;
    }

    return this._hass.states[this._config.entity];
  }

  _getAreas() {
    const alarm = this._getAlarmEntity();
    const rawAreas = alarm?.attributes?.areas;

    if (!rawAreas || typeof rawAreas !== "object") {
      return [];
    }

    return Object.entries(rawAreas)
      .map(([id, area]) => ({
        id: String(id),
        numericId: Number(id),
        name: area?.name || this._t("area.name", { id }),
        mode: area?.mode,
        modeName: area?.mode_name,
        raw: area,
      }))
      .sort((a, b) => {
        if (
          Number.isFinite(a.numericId) &&
          Number.isFinite(b.numericId)
        ) {
          return a.numericId - b.numericId;
        }

        return a.name.localeCompare(b.name);
      });
  }

  _getAreaAlarmEntity(areaId) {
    const ids = this._panelEntityIds();
    if (!ids || !this._hass) {
      return null;
    }

    const id = String(areaId);
    return Array.from(ids)
      .filter((entityId) => entityId.startsWith("alarm_control_panel."))
      .map((entityId) => ({ entityId, stateObj: this._hass.states[entityId] }))
      .find(({ stateObj }) =>
        stateObj && String(stateObj.attributes?.area_id ?? "") === id
      ) || null;
  }

  // Never fall back to a global entity lookup: identical area/zone IDs
  // are normal when multiple SPC panels are configured.
  _panelEntityIds() {
    if (
      this._diagnosticScopeForEntity !== this._config?.entity ||
      !this._diagnosticScope?.integrationEntityIds ||
      !this._diagnosticScope?.selected?.config_entry_id
    ) {
      return null;
    }
    return this._diagnosticScope.integrationEntityIds;
  }

  _getZones() {
    const panelIds = this._panelEntityIds();
    if (!this._hass || !panelIds) {
      return [];
    }

    const states = { ...this._hass.states };

    if (this._spcLiveStates?.size) {
      for (const [entityId, stateObj] of this._spcLiveStates) {
        states[entityId] = stateObj;
      }
    }

    return Object.entries(states)
      .filter(([entityId, stateObj]) => {
        if (!panelIds.has(entityId) || !entityId.startsWith("binary_sensor.")) {
          return false;
        }

        const attrs = stateObj?.attributes || {};

        return (
          attrs.zone_id !== undefined &&
          attrs.zone_id !== null &&
          attrs.area_id !== undefined &&
          attrs.area_id !== null &&
          attrs.spc_zone_type !== undefined &&
          attrs.spc_zone_type !== null &&
          String(attrs.spc_zone_type).trim() !== ""
        );
      })
      .map(([entityId, stateObj]) => {
        const attrs = stateObj.attributes || {};

        return {
          entityId,
          state: stateObj.state,
          zoneId: attrs.zone_id,
          areaId: attrs.area_id,
          zoneType: String(
            attrs.spc_zone_type || ""
          ).toLowerCase(),
          deviceClass: String(
            attrs.device_class || ""
          ).toLowerCase(),
          name:
            attrs.friendly_name ||
            entityId.split(".").pop() ||
            this._t("zone.name", { id: attrs.zone_id }),
          logicInput: attrs.logic_input,
          status: attrs.status,
          procState: attrs.proc_state,
          alarmState: attrs.alarm_state,
          eventTamper: attrs.event_tamper,
          eventTrouble: attrs.event_trouble,
          lastEvent: attrs.last_event,
          actuationsSinceLastRead:
            attrs.actuations_since_last_read,
          raw: stateObj,
        };
      })
      .sort((a, b) => {
        const areaA = Number(a.areaId);
        const areaB = Number(b.areaId);

        if (
          Number.isFinite(areaA) &&
          Number.isFinite(areaB) &&
          areaA !== areaB
        ) {
          return areaA - areaB;
        }

        const zoneA = Number(a.zoneId);
        const zoneB = Number(b.zoneId);

        if (
          Number.isFinite(zoneA) &&
          Number.isFinite(zoneB)
        ) {
          return zoneA - zoneB;
        }

        return a.name.localeCompare(b.name);
      });
  }

  _getNormalZones() {
    return this._getZones().filter(
      (zone) =>
        zone.zoneType !== "tamper" &&
        zone.deviceClass !== "tamper"
    );
  }

  _getTamperZones() {
    return this._getZones().filter(
      (zone) =>
        zone.zoneType === "tamper" ||
        zone.deviceClass === "tamper"
    );
  }

  _areaName(areaId) {
    const id = String(areaId);

    const area = this._getAreas().find(
      (candidate) => String(candidate.id) === id
    );

    return area?.name || this._t("area.name", { id });
  }

  _zoneIcon(zone) {
    if (
      zone.zoneType === "tamper" ||
      zone.deviceClass === "tamper"
    ) {
      return "mdi:shield-alert-outline";
    }

    if (zone.eventTamper === true) {
      return "mdi:shield-alert";
    }

    switch (zone.deviceClass) {
      case "motion":
      case "occupancy":
        return "mdi:motion-sensor";

      case "door":
        return "mdi:door";

      case "window":
        return "mdi:window-closed-variant";

      case "opening":
        return "mdi:door-open";

      case "smoke":
        return "mdi:smoke-detector";

      case "heat":
        return "mdi:fire";

      case "moisture":
        return "mdi:water-alert";

      case "gas":
        return "mdi:gas-cylinder";

      default:
        break;
    }

    switch (zone.zoneType) {
      case "entry_exit":
      case "entry-exit":
        return "mdi:door-open";

      case "fire":
        return "mdi:fire";

      case "panic":
        return "mdi:alarm-light";

      default:
        return "mdi:shield-home-outline";
    }
  }

  _zoneStateInfo(zone) {
    const active = zone.state === "on";
    const isTamper =
      zone.zoneType === "tamper" ||
      zone.deviceClass === "tamper";
    const tamperActive =
      zone.eventTamper === true ||
      (isTamper && active);

    if (isTamper) {
      return {
        label: tamperActive
          ? this._t("zone.tamper")
          : this._t("state.normal"),
        className: tamperActive ? "danger" : "ok",
      };
    }

    if (zone.eventTamper === true) {
      return {
        label: this._t("zone.alert_tamper"),
        className: "danger",
      };
    }

    if (zone.state === "unavailable") {
      return {
        label: this._t("state.unavailable"),
        className: "muted",
      };
    }

    if (zone.state === "unknown") {
      return {
        label: this._t("state.unknown_short"),
        className: "muted",
      };
    }

    switch (zone.deviceClass) {
      case "motion":
      case "occupancy":
        return {
          label: active
            ? this._t("zone.motion")
            : this._t("zone.rest"),
          className: active ? "warning" : "ok",
        };

      case "door":
      case "window":
      case "opening":
        return {
          label: active
            ? this._t("zone.open")
            : this._t("zone.closed"),
          className: active ? "warning" : "ok",
        };

      case "smoke":
        return {
          label: active
            ? this._t("zone.smoke")
            : this._t("state.normal"),
          className: active ? "danger" : "ok",
        };

      case "heat":
        return {
          label: active
            ? this._t("zone.heat")
            : this._t("state.normal"),
          className: active ? "danger" : "ok",
        };

      default:
        return {
          label: active
            ? this._t("zone.active")
            : this._t("zone.rest"),
          className: active ? "warning" : "ok",
        };
    }
  }

  _lastAreaChange(stateObj) {
    if (!stateObj) {
      return "";
    }

    const attrs = stateObj.attributes || {};
    const rows = [
      ["last_arm", "last_set", "area.last_set"],
      ["last_disarm", "last_unset", "area.last_unset"],
    ].map(([prefix, legacyPrefix, labelKey]) => {
      const selectedPrefix = attrs[`${prefix}_time`] ? prefix : legacyPrefix;
      const formattedTime = this._formatDateTime(
        attrs[`${selectedPrefix}_time`]
      );
      if (!formattedTime) {
        return "";
      }

      const user = [
        attrs[`${selectedPrefix}_user_display_name`],
        attrs[`${selectedPrefix}_user_name`],
        attrs[`${selectedPrefix}_user_id`],
      ]
        .map((value) => String(value ?? "").trim())
        .find(Boolean);

      return `
        <div class="last-change">
          <div class="last-change-label">
            ${this._escapeHtml(this._t(labelKey))}
          </div>
          <div class="last-change-value">
            ${this._escapeHtml(formattedTime)}
            ${
              user
                ? `<span class="last-change-user"> · ${this._escapeHtml(user)}</span>`
                : ""
            }
          </div>
        </div>
      `;
    });

    return rows.filter(Boolean).join("");
  }

  async _ensureDiagnosticScope() {
    if (
      !this._hass?.callWS ||
      !this._config?.entity
    ) {
      return;
    }

    if (this._diagnosticScopeLoading) {
      return;
    }

    if (
      this._diagnosticScopeForEntity === this._config.entity &&
      this._diagnosticScope?.selected?.config_entry_id
    ) {
      return;
    }

    // Retry a failed or incomplete registry lookup on subsequent HA updates,
    // without flooding the websocket while the panel is temporarily unavailable.
    if (Date.now() < (this._diagnosticScopeRetryAt || 0)) {
      return;
    }
    this._diagnosticScopeRetryAt = Date.now() + 15000;
    this._diagnosticScopeLoading = true;
    const generation = this._scopeGeneration || 0;
    const requestedEntity = this._config.entity;

    try {
      const [entries, devices] = await Promise.all([
        this._hass.callWS({
          type: "config/entity_registry/list",
        }),
        this._hass.callWS({
          type: "config/device_registry/list",
        }).catch(() => []),
      ]);

      // Ignore stale results if the editor switched panels while loading.
      if (generation !== (this._scopeGeneration || 0) ||
          requestedEntity !== this._config?.entity) {
        return;
      }

      const selected = entries.find(
        (entry) => entry.entity_id === requestedEntity
      );

      if (!selected) {
        this._diagnosticScope = {
          method: "none",
          entityIds: null,
          integrationEntityIds: null,
          selected: null,
          device: null,
          integrationEntries: [],
          entryMap: new Map(),
        };
      } else {
        const integrationEntityIds = new Set(
          entries
            .filter((entry) => {
              if (selected.config_entry_id) {
                if (
                  entry.config_entry_id !==
                  selected.config_entry_id
                ) {
                  return false;
                }
              } else if (selected.device_id) {
                if (entry.device_id !== selected.device_id) {
                  return false;
                }
              } else if (
                entry.entity_id !== selected.entity_id
              ) {
                return false;
              }

              if (
                selected.platform &&
                entry.platform &&
                entry.platform !== selected.platform
              ) {
                return false;
              }

              return true;
            })
            .map((entry) => entry.entity_id)
        );

        let entityIds = integrationEntityIds;
        let method = "config_entry";

        if (selected.device_id) {
          entityIds = new Set(
            entries
              .filter(
                (entry) =>
                  entry.device_id &&
                  entry.device_id === selected.device_id
              )
              .map((entry) => entry.entity_id)
          );
          method = "device";
        }

        const device = Array.isArray(devices)
          ? devices.find(
              (candidate) =>
                candidate.id === selected.device_id
            ) || null
          : null;

        const integrationEntries = entries.filter((entry) =>
          integrationEntityIds.has(entry.entity_id)
        );

        this._diagnosticScope = {
          method,
          entityIds,
          integrationEntityIds,
          selected,
          device,
          integrationEntries,
          entryMap: new Map(
            integrationEntries.map((entry) => [entry.entity_id, entry])
          ),
        };
      }
    } catch (error) {
      if (generation !== (this._scopeGeneration || 0) ||
          requestedEntity !== this._config?.entity) {
        return;
      }
      console.warn(
        "SPC FlexC Card: unable to read Home Assistant registries for diagnostics",
        error
      );

      this._diagnosticScope = {
        method: "unavailable",
        entityIds: null,
        integrationEntityIds: null,
        selected: null,
        device: null,
        integrationEntries: [],
        entryMap: new Map(),
      };
    } finally {
      if (generation === (this._scopeGeneration || 0) &&
          requestedEntity === this._config?.entity) {
        this._diagnosticScopeForEntity = requestedEntity;
        this._diagnosticScopeLoading = false;
        this._render();
      }
    }
  }

  _scopeEntityIds(includeIntegration = false) {
    const scope = this._diagnosticScope;

    if (!scope) {
      return null;
    }

    if (
      includeIntegration &&
      scope.integrationEntityIds
    ) {
      return scope.integrationEntityIds;
    }

    return scope.entityIds || null;
  }

  _scopedStates(includeIntegration = false) {
    const ids = this._scopeEntityIds(
      includeIntegration
    );

    if (!ids || !this._hass) {
      return [];
    }

    const entryMap = this._diagnosticScope?.entryMap || new Map();

    return Array.from(ids)
      .map((entityId) => ({
        entityId,
        stateObj: this._hass.states[entityId],
        registryEntry: entryMap.get(entityId) || null,
      }))
      .filter((item) => Boolean(item.stateObj));
  }

  _getSystemDiagnostics() {
    const scope = this._diagnosticScope;

    if (!scope?.entityIds) {
      return {
        scopeAvailable: false,
        connection: null,
        engineerMode: null,
        faults: [],
      };
    }

    const diagnostics = [];

    for (const { entityId, stateObj } of this._scopedStates()) {
      if (!entityId.startsWith("binary_sensor.")) {
        continue;
      }

      const attrs = stateObj.attributes || {};

      if (
        attrs.zone_id !== undefined ||
        attrs.area_id !== undefined ||
        attrs.spc_zone_type !== undefined
      ) {
        continue;
      }

      diagnostics.push({
        entityId,
        stateObj,
        deviceClass: String(
          attrs.device_class || ""
        ).toLowerCase(),
        friendlyName: String(
          attrs.friendly_name || entityId
        ),
      });
    }

    const connection =
      diagnostics.find((item) => {
        if (item.deviceClass !== "connectivity") {
          return false;
        }

        return /flex\s*c|flexc/i.test(
          `${item.entityId} ${item.friendlyName}`
        );
      }) || null;

    const engineerMode =
      diagnostics.find((item) =>
        /engineer[_\s-]*mode|installer|installateur/i.test(
          `${item.entityId} ${item.friendlyName}`
        )
      ) || null;

    const problems = diagnostics
      .filter(
        (item) =>
          item.deviceClass === "problem" &&
          item.stateObj.state === "on"
      )
      .sort((a, b) =>
        a.friendlyName.localeCompare(
          b.friendlyName,
          this._locale()
        )
      );
    // An isolated or inhibited fault is known and switched off on the panel,
    // like the web page's "Spärrade och isolerade"; it is not an active fault.
    const switchedOff = (item) =>
      item.stateObj.attributes?.isolated === true ||
      item.stateObj.attributes?.inhibited === true;
    const faults = problems.filter((item) => !switchedOff(item));
    const switchedOffFaults = problems.filter(switchedOff);

    return {
      scopeAvailable: true,
      connection,
      engineerMode,
      faults,
      switchedOffFaults,
    };
  }

  _renderSystemDiagnostics() {
    const diagnostics = this._getSystemDiagnostics();

    let connectionHtml;

    if (!diagnostics.scopeAvailable) {
      connectionHtml = `
        <div class="diagnostic-row">
          <ha-icon class="muted" icon="mdi:lan-disconnect"></ha-icon>
          <div class="diagnostic-main">
            <div class="diagnostic-name">${this._t("system.connection")}</div>
            <div class="diagnostic-detail muted">${this._t("system.state_unknown")}</div>
          </div>
        </div>
      `;
    } else if (!diagnostics.connection) {
      connectionHtml = `
        <div class="diagnostic-row">
          <ha-icon class="muted" icon="mdi:lan"></ha-icon>
          <div class="diagnostic-main">
            <div class="diagnostic-name">${this._t("system.connection")}</div>
            <div class="diagnostic-detail muted">${this._t("system.entity_missing")}</div>
          </div>
        </div>
      `;
    } else {
      const connected =
        diagnostics.connection.stateObj.state === "on";

      connectionHtml = `
        <div class="diagnostic-row">
          <ha-icon
            class="${connected ? "ok" : "danger"}"
            icon="${connected ? "mdi:lan-connect" : "mdi:lan-disconnect"}"
          ></ha-icon>
          <div class="diagnostic-main">
            <div class="diagnostic-name">${this._t("system.connection")}</div>
            <div class="diagnostic-detail ${connected ? "ok" : "danger"}">
              ${this._t(connected ? "state.connected" : "state.disconnected")}
            </div>
          </div>
        </div>
      `;
    }

    const engineerHtml =
      diagnostics.engineerMode?.stateObj?.state === "on"
        ? `
          <div class="diagnostic-row engineer-warning">
            <ha-icon class="warning" icon="mdi:account-hard-hat"></ha-icon>
            <div class="diagnostic-main">
              <div class="diagnostic-name warning">${this._t("system.engineer_active")}</div>
              <div class="diagnostic-detail muted">
                ${this._t("system.engineer_detail")}
              </div>
            </div>
          </div>
        `
        : "";

    const faultsHtml =
      !diagnostics.scopeAvailable
        ? `
          <div class="fault-ok muted">
            <ha-icon icon="mdi:information-outline"></ha-icon>
            <span>${this._t("system.faults_unknown")}</span>
          </div>
        `
        : diagnostics.faults.length || diagnostics.switchedOffFaults?.length
          ? `
            ${diagnostics.faults.length ? `
            <div class="fault-header danger">
              <ha-icon icon="mdi:alert-circle"></ha-icon>
              <span>${this._t("system.active_faults")}</span>
              <span class="fault-count">${diagnostics.faults.length}</span>
            </div>
            <div class="fault-list">
              ${diagnostics.faults
                .map(
                  (fault) => `
                    <div class="fault-row danger">
                      <ha-icon icon="mdi:alert"></ha-icon>
                      <span>${this._escapeHtml(fault.friendlyName)}</span>
                    </div>
                  `
                )
                .join("")}
            </div>` : `
            <div class="fault-ok ok">
              <ha-icon icon="mdi:check-circle"></ha-icon>
              <span>${this._t("system.no_fault")}</span>
            </div>`}
            ${diagnostics.switchedOffFaults?.length ? `
            <div class="fault-list">
              ${diagnostics.switchedOffFaults
                .map(
                  (fault) => `
                    <div class="fault-row muted">
                      <ha-icon icon="mdi:alert-outline"></ha-icon>
                      <span>${this._escapeHtml(fault.friendlyName)} – ${this._t(
                        fault.stateObj.attributes?.isolated === true ? "state.isolated" : "state.inhibited"
                      )}</span>
                    </div>
                  `
                )
                .join("")}
            </div>` : ""}
            ${this._config.show_controls ? `
            <div class="fault-actions">
              <button type="button" class="control-button" data-spc-service="clear_alerts"
                data-confirm="${this._escapeHtml(this._t("confirm.clear_alerts"))}">
                <ha-icon icon="mdi:check-all"></ha-icon>
                <span>${this._t("action.clear_alerts")}</span>
              </button>
            </div>` : ""}
          `
          : `
            <div class="fault-ok ok">
              <ha-icon icon="mdi:check-circle"></ha-icon>
              <span>${this._t("system.no_fault")}</span>
            </div>
          `;

    return `
      <div class="diagnostics-block">
        <div class="group-title">${this._t("system.health")}</div>
        ${connectionHtml}
        ${engineerHtml}
        ${faultsHtml}
      </div>
    `;
  }

  _valueWithUnit(stateObj) {
    if (!stateObj) return null;

    const state = String(stateObj.state ?? "").trim();
    if (!state || ["unknown", "unavailable"].includes(state)) {
      return null;
    }

    const unit = String(
      stateObj.attributes?.unit_of_measurement || ""
    ).trim();

    return unit ? `${state} ${unit}` : state;
  }

  _findIntegrationState(patterns) {
    return (
      this._scopedStates(true).find(({ entityId, stateObj }) => {
        const friendlyName =
          stateObj?.attributes?.friendly_name || "";
        const haystack = `${entityId} ${friendlyName}`;
        return patterns.some((pattern) => pattern.test(haystack));
      }) || null
    );
  }

  _technicalLine(label, value, className = "") {
    if (
      value === undefined ||
      value === null ||
      String(value).trim() === ""
    ) {
      return "";
    }

    return `
      <div class="technical-row">
        <div class="technical-label">${this._escapeHtml(label)}</div>
        <div class="technical-value ${className}">${this._escapeHtml(value)}</div>
      </div>
    `;
  }

  _entityTechnicalLine(label, match, className = "") {
    return this._technicalLine(
      label,
      this._valueWithUnit(match?.stateObj),
      className
    );
  }

  _getFlexcCommunication() {
    const states = this._scopedStates(true);
    const atsMap = new Map();

    const ensureAts = (atsId) => {
      if (!atsMap.has(atsId)) {
        atsMap.set(atsId, {
          id: atsId,
          name: null,
          entities: [],
          atps: new Map(),
          activePath: null,
        });
      }
      return atsMap.get(atsId);
    };

    const ensureAtp = (ats, atpId) => {
      if (!ats.atps.has(atpId)) {
        ats.atps.set(atpId, {
          id: atpId,
          name: null,
          entities: [],
          lastTxOkTimestamp: null,
          active: null,
          fault: null,
        });
      }
      return ats.atps.get(atpId);
    };

    const friendlyName = (item) =>
      String(
        item.stateObj?.attributes?.friendly_name ||
          item.registryEntry?.original_name ||
          item.entityId ||
          ""
      ).trim();

    const atpNameFromFriendly = (friendly, atpId) => {
      const suffix = new RegExp(
        `\\s+ATP\\s+${atpId}\\s+(?:last\\s+TX\\s+successful|fault)$`,
        "i"
      );
      const match = String(friendly || "").match(suffix);
      if (!match) return null;
      const name = String(friendly).slice(0, match.index).trim();
      return name || null;
    };

    /*
     * SPC FlexC exposes stable registry unique IDs for communication entities:
     *   <entry_id>_ats_<ats_id>_active_path
     *   <entry_id>_ats_<ats_id>_atp_<atp_id>_last_tx_ok
     *   <entry_id>_ats_<ats_id>_atp_<atp_id>_fault
     *
     * Parse only those IDs. Do not infer ATS/ATP numbers from entity names or
     * unrelated states: doing so can incorrectly turn the alarm entity into
     * an ATS 0 / ATP 0.
     */
    for (const item of states) {
      const uniqueId = String(item.registryEntry?.unique_id || "");
      const stateObj = item.stateObj;
      if (!uniqueId || !stateObj) continue;

      let match = uniqueId.match(/_ats_(\d+)_active_path$/);
      if (match) {
        const atsId = Number(match[1]);
        if (atsId < 1) continue;

        const ats = ensureAts(atsId);
        ats.entities.push(item);

        const friendly = friendlyName(item);
        const nameMatch = friendly.match(/^(.*?)\s+active\s+path$/i);
        ats.name = nameMatch?.[1]?.trim() || ats.name;

        const activePath = String(stateObj.state || "").trim();
        if (activePath && !["unknown", "unavailable"].includes(activePath)) {
          ats.activePath = activePath;
        }
        continue;
      }

      match = uniqueId.match(/_ats_(\d+)_atp_(\d+)_(last_tx_ok|fault)$/);
      if (!match) continue;

      const atsId = Number(match[1]);
      const atpId = Number(match[2]);
      const kind = match[3];
      if (atsId < 1 || atpId < 1) continue;

      const ats = ensureAts(atsId);
      const atp = ensureAtp(ats, atpId);
      atp.entities.push(item);

      const parsedName = atpNameFromFriendly(friendlyName(item), atpId);
      if (parsedName && !atp.name) atp.name = parsedName;

      if (kind === "last_tx_ok") {
        const value = String(stateObj.state || "").trim();
        if (value && !["unknown", "unavailable"].includes(value)) {
          atp.lastTxOkTimestamp = value;
        }
      } else if (kind === "fault") {
        if (stateObj.state === "on") atp.fault = true;
        else if (stateObj.state === "off") atp.fault = false;
      }
    }

    const atsList = Array.from(atsMap.values())
      .map((ats) => {
        const rawAtps = Array.from(ats.atps.values()).sort(
          (a, b) => Number(a.id) - Number(b.id)
        );

        const normalizePath = (value) =>
          String(value || "")
            .toLocaleLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/\batp\s*\d+\b/g, " ")
            .replace(/[^a-z0-9]+/g, " ")
            .trim();

        const activePath = normalizePath(ats.activePath);

        rawAtps.forEach((atp, index) => {
          atp.displayId = index + 1;

          if (!activePath) return;

          const atpName = normalizePath(atp.name);
          const significantWords = atpName
            .split(/\s+/)
            .filter((word) => word.length >= 3);

          if (
            atpName &&
            (atpName.endsWith(activePath) ||
              activePath.endsWith(atpName) ||
              significantWords.some(
                (word) =>
                  activePath === word ||
                  activePath.startsWith(`${word} `) ||
                  activePath.endsWith(` ${word}`)
              ))
          ) {
            atp.active = true;
          } else {
            atp.active = false;
          }
        });

        if (activePath && rawAtps.length === 1) {
          rawAtps[0].active = true;
          if (!rawAtps[0].name && ats.activePath) {
            rawAtps[0].name = ats.activePath;
          }
        }

        ats.atps = rawAtps;
        return ats;
      })
      .sort((a, b) => Number(a.id) - Number(b.id));

    return atsList;
  }

  _atpStateLabel(atp) {
    if (atp.fault === true || String(atp.fault).toLowerCase() === "true") {
      return { label: this._t("state.fault"), className: "danger" };
    }

    if (atp.active === true || String(atp.active).toLowerCase() === "true") {
      return { label: this._t("state.ok"), className: "ok" };
    }

    if (atp.active === false || String(atp.active).toLowerCase() === "false") {
      return { label: this._t("state.inactive"), className: "muted" };
    }

    if (atp.fault === false || String(atp.fault).toLowerCase() === "false") {
      return { label: this._t("state.ok"), className: "ok" };
    }

    return null;
  }

  _renderFlexcCommunication() {
    const atsList = this._getFlexcCommunication();
    if (!atsList.length) return "";

    return `
      <div class="technical-section">
        <div class="technical-section-title">${this._t("system.communication")}</div>
        <div class="ats-list">
          ${atsList
            .map((ats) => {
              const atsLabel = ats.ungrouped
                ? ats.name
                : `ATS ${ats.id ?? "?"}${
                    ats.name ? ` — ${ats.name}` : ""
                  }`;

              return `
                <div class="ats-card">
                  <div class="ats-title">${this._escapeHtml(atsLabel)}</div>
                  ${ats.atps.length
                    ? `<div class="atp-list">
                        ${ats.atps
                          .map((atp) => {
                            const atpLabel = `ATP ${atp.displayId ?? "?"}${
                              atp.name ? ` — ${atp.name}` : ""
                            }`;
                            const stateInfo = this._atpStateLabel(atp);
                            const formattedTx = this._formatDateTime(
                              atp.lastTxOkTimestamp
                            );

                            return `
                              <div class="atp-card">
                                <div class="atp-title">${this._escapeHtml(atpLabel)}</div>
                                ${stateInfo
                                  ? this._technicalLine(
                                      this._t("system.state"),
                                      stateInfo.label,
                                      stateInfo.className
                                    )
                                  : ""}
                                ${ats.ungrouped
                                  ? ""
                                  : this._technicalLine(
                                      this._t("system.ats_used"),
                                      atsLabel
                                    )}
                                ${this._technicalLine(
                                  this._t("system.last_tx"),
                                  formattedTx
                                )}
                              </div>
                            `;
                          })
                          .join("")}
                      </div>`
                    : ""}
                </div>
              `;
            })
            .join("")}
        </div>
      </div>
    `;
  }

  _getXBusDevices() {
    const devices = new Map();

    for (const { entityId, stateObj } of this._scopedStates(true)) {
      const attrs = stateObj.attributes || {};
      const id = attrs.xbus_device_id;

      if (id === undefined || id === null) {
        continue;
      }

      const key = String(id);
      if (!devices.has(key)) {
        devices.set(key, {
          id,
          name: attrs.xbus_device_name || null,
          siaAddress: attrs.sia_address ?? null,
          tamperFault: attrs.tamper_fault ?? null,
          tamperIsolated: attrs.tamper_isolated ?? null,
          entities: [],
        });
      }

      const device = devices.get(key);
      device.entities.push({ entityId, stateObj });
      if (attrs.xbus_device_name) device.name = attrs.xbus_device_name;
      if (attrs.sia_address !== undefined) device.siaAddress = attrs.sia_address;
      if (attrs.tamper_fault !== undefined) device.tamperFault = attrs.tamper_fault;
      if (attrs.tamper_isolated !== undefined) device.tamperIsolated = attrs.tamper_isolated;
    }

    return Array.from(devices.values()).sort(
      (a, b) => Number(a.id) - Number(b.id)
    );
  }

  _renderXBusDevices() {
    const devices = this._getXBusDevices();
    if (!devices.length) return "";

    return `
      <div class="technical-section">
        <div class="technical-section-title">${this._t("system.xbus")}</div>
        <div class="xbus-list">
          ${devices
            .map((device) => {
              const title = device.name || `X-BUS ${device.id}`;
              const fault = device.tamperFault === true;
              const isolated = device.tamperIsolated === true;

              return `
                <div class="xbus-card">
                  <div class="xbus-title">
                    <span>${this._escapeHtml(title)}</span>
                    <span class="${fault ? "danger" : "ok"}">
                      ${this._t(fault ? "state.fault" : "state.ok")}
                    </span>
                  </div>
                  ${this._technicalLine(this._t("system.xbus_id"), device.id)}
                  ${this._technicalLine(this._t("system.sia_address"), device.siaAddress)}
                  ${device.tamperFault !== null
                    ? this._technicalLine(
                        this._t("system.tamper"),
                        this._t(fault ? "state.fault" : "state.ok"),
                        fault ? "danger" : "ok"
                      )
                    : ""}
                  ${device.tamperIsolated !== null
                    ? this._technicalLine(
                        this._t("system.tamper_isolation"),
                        this._t(isolated ? "state.isolated" : "state.not_isolated"),
                        isolated ? "warning" : "ok"
                      )
                    : ""}
                </div>
              `;
            })
            .join("")}
        </div>
      </div>
    `;
  }

  _renderTechnicalSystem() {
    const scope = this._diagnosticScope;
    const device = scope?.device || {};

    const identityLines = [
      this._technicalLine(this._t("system.manufacturer"), device.manufacturer),
      this._technicalLine(this._t("system.model"), device.model || device.model_id),
      this._technicalLine(this._t("system.firmware"), device.sw_version),
      this._technicalLine(this._t("system.hardware"), device.hw_version),
      this._technicalLine(this._t("system.serial"), device.serial_number),
    ].join("");

    const acFrequency = this._findIntegrationState([
      /ac[_\s-]*frequency/i,
      /fr[ée]quence.*secteur/i,
    ]);
    const batteryVoltage = this._findIntegrationState([
      /battery[_\s-]*voltage/i,
      /tension.*batterie/i,
    ]);
    const auxVoltage = this._findIntegrationState([
      /aux[_\s-]*voltage/i,
      /tension.*aux/i,
    ]);
    const auxCurrent = this._findIntegrationState([
      /aux[_\s-]*current/i,
      /courant.*aux/i,
    ]);

    const powerLines = [
      this._entityTechnicalLine(this._t("system.ac_frequency"), acFrequency),
      this._entityTechnicalLine(this._t("system.battery_voltage"), batteryVoltage),
      this._entityTechnicalLine(this._t("system.aux_voltage"), auxVoltage),
      this._entityTechnicalLine(this._t("system.aux_current"), auxCurrent),
    ].join("");

    const rfEntities = this._scopedStates(true).filter(({ entityId, stateObj }) =>
      /\brf\b|radio|jamming|brouillage/i.test(
        `${entityId} ${stateObj.attributes?.friendly_name || ""}`
      )
    );
    const modemEntities = this._scopedStates(true).filter(({ entityId, stateObj }) =>
      /modem/i.test(
        `${entityId} ${stateObj.attributes?.friendly_name || ""}`
      )
    );

    const renderEntityList = (title, entities) => {
      const rows = entities
        .filter(({ stateObj }) => this._valueWithUnit(stateObj) !== null)
        .map(({ stateObj }) =>
          this._technicalLine(
            stateObj.attributes?.friendly_name || this._t("system.state"),
            this._valueWithUnit(stateObj)
          )
        )
        .join("");

      return rows
        ? `<div class="technical-section">
            <div class="technical-section-title">${this._escapeHtml(title)}</div>
            ${rows}
          </div>`
        : "";
    };

    const identitySection = identityLines
      ? `<div class="technical-section" data-technical-section="panel">
          <div class="technical-section-title">${this._t("system.panel")}</div>
          ${identityLines}
        </div>`
      : "";

    const powerSection = powerLines
      ? `<div class="technical-section">
          <div class="technical-section-title">${this._t("system.power")}</div>
          ${powerLines}
        </div>`
      : "";

    const eventSensor = this._scopedStates(true).find(({ entityId, stateObj }) =>
      entityId.startsWith("sensor.") &&
      /last[_\\s-]*flexc[_\\s-]*event[_\\s-]*id/i.test(
        `${entityId} ${stateObj.attributes?.friendly_name || ""}`
      )
    );
    const recentEvents = eventSensor?.stateObj?.attributes?.recent_events;
    const eventMetadata = (event) => [
      event.received_at ? this._formatEventDateTime(event.received_at) : null,
      event.origin,
      event.alarm_type,
      event.alarm_transition,
      event.area_id != null
        ? `${this._t("system.area")} ${event.area_id}${event.area_name ? ` — ${event.area_name}` : ""}`
        : null,
      event.zone_id != null
        ? `${this._t("system.zone")} ${event.zone_id}${event.zone_name ? ` — ${event.zone_name}` : ""}`
        : null,
    ].filter(Boolean).join(" · ");
    const eventRows = Array.isArray(recentEvents)
      ? recentEvents.slice(-20).reverse().map((event) => {
          const description = event.description || this._t("system.event_unknown");
          const title = `#${event.event_id} — ${description}`;
          const metadata = eventMetadata(event);
          return `<div class="technical-line event-history-row">
            <span>${this._escapeHtml(String(title))}</span>
            <span class="muted">${this._escapeHtml(String(metadata))}</span>
          </div>`;
        }).join("")
      : "";
    const wirelessEvents = Array.isArray(recentEvents)
      ? recentEvents.filter((event) =>
          event.origin === "wireless_keypad" || event.origin === "wireless_device"
        ).slice(-20).reverse()
      : [];
    const wirelessRows = wirelessEvents.map((event) => {
      const description = event.description || this._t("system.event_unknown");
      const metadata = eventMetadata(event);
      return `<div class="technical-line">
        <span>${this._escapeHtml(`#${event.event_id} — ${description}`)}</span>
        <span class="muted">${this._escapeHtml(metadata)}</span>
      </div>`;
    }).join("");
    const wirelessDiagnostics = rfEntities.map(({ entityId, stateObj }) => {
      const label = stateObj.attributes?.friendly_name || entityId;
      const state = String(stateObj.state ?? "unknown").toLowerCase();
      const isJamming = /jamming|brouillage/i.test(`${entityId} ${label}`);
      const display = isJamming
        ? this._t(state === "on" ? "state.fault" : state === "off" ? "state.ok" : "state.unknown")
        : this._valueWithUnit(stateObj) || this._t("state.unknown");
      const tone = isJamming && state === "on" ? "danger" : isJamming && state === "off" ? "ok" : "muted";
      return `<div class="technical-row"><span class="technical-label">${this._escapeHtml(label)}</span><span class="technical-value ${tone}">${this._escapeHtml(display)}</span></div>`;
    }).join("");
    const wirelessCount = rfEntities.length + wirelessEvents.length;
    const wirelessSection = wirelessCount
      ? `<div class="technical-section" data-technical-section="wireless-events">
          <div class="technical-section-title">${this._t("system.rf")}</div>
          <details class="system-detail-card" data-system-detail-key="wireless-rf">
            <summary>${wirelessCount} ${this._t("system.rf")}</summary>
            <div class="system-detail-body">
              ${wirelessDiagnostics}
              ${wirelessRows ? `<div class="muted">${this._t("system.wireless_events")}</div>${wirelessRows}` : ""}
            </div>
          </details>
        </div>`
      : "";

    const eventSection = eventSensor && eventSensor.stateObj.state !== "unavailable"
      ? `<div class="technical-section" data-technical-section="flexc-events">
          <div class="technical-section-title">${this._t("system.event_history")}</div>
          <details class="system-detail-card" data-system-detail-key="flexc-events">
            <summary>${Array.isArray(recentEvents) ? Math.min(recentEvents.length, 20) : 0} ${this._t(Array.isArray(recentEvents) && recentEvents.length === 1 ? "system.event_count_one" : "system.event_count_many")}</summary>
            <div class="system-detail-body">
              <div class="muted">${this._t("system.event_observation")}</div>
              ${eventRows || `<div class="muted">${this._t("system.no_recent_events")}</div>`}
            </div>
          </details>
        </div>`
      : `<div class="technical-section" data-technical-section="flexc-events">
          <div class="technical-section-title">${this._t("system.event_history")}</div>
          <div class="muted">${this._t("system.event_enable_hint")}</div>
        </div>`;

    const pirSensor = this._scopedStates(true).find(({ entityId, stateObj }) =>
      entityId.startsWith("sensor.") &&
      /pir[_\\s-]*slow[_\\s-]*reads/i.test(
        `${entityId} ${stateObj.attributes?.friendly_name || ""}`
      )
    );
    const pirState = pirSensor?.stateObj?.state;
    const pirAvailable = pirState != null && pirState !== "unavailable" && pirState !== "unknown";
    const pirReadings = pirAvailable && Array.isArray(pirSensor.stateObj.attributes?.slow_reads)
      ? pirSensor.stateObj.attributes.slow_reads : [];
    const pirCount = pirAvailable ? Number(pirState) : 0;
    const pirRows = pirReadings.map((reading) => {
      const duration = Number(reading.read_ms);
      const timestamp = reading.timestamp ? this._formatEventDateTime(reading.timestamp) : "";
      const timing = [
        Number.isFinite(duration) ? `${duration.toFixed(1)} ms` : "",
        Number.isFinite(Number(reading.lock_wait_ms)) ? `lock ${reading.lock_wait_ms} ms` : "",
        Number.isFinite(Number(reading.resync_wait_ms)) ? `resync ${reading.resync_wait_ms} ms` : "",
      ].filter(Boolean).join(" · ");
      return `<div class="technical-line event-history-row">
        <span>${this._escapeHtml(timestamp)}</span>
        <span class="muted">${this._escapeHtml(timing)}</span>
        ${reading.log_level ? `<span class="muted">${this._escapeHtml(reading.log_level)}</span>` : ""}
      </div>`;
    }).join("");
    const pirSection = `<div class="technical-section" data-technical-section="pir-diagnostics">
      <div class="technical-section-title">${this._t("system.pir_diagnostics")}</div>
      <details class="system-detail-card" data-system-detail-key="pir-diagnostics">
        <summary>${pirAvailable && Number.isFinite(pirCount)
          ? `${pirCount} ${this._t("system.pir_slow_reads")}`
          : this._t(pirSensor ? "system.pir_unavailable" : "system.pir_disabled")}</summary>
        <div class="system-detail-body">
          ${pirAvailable
            ? `<div class="muted">${this._t("system.pir_maximum")}: ${this._escapeHtml(String(pirSensor.stateObj.attributes?.max_read_ms ?? "—"))} ms</div>
               ${pirRows || `<div class="muted">${this._t("system.pir_empty")}</div>`}`
            : `<div class="muted">${this._t(pirSensor ? "system.pir_unavailable_hint" : "system.pir_enable_hint")}</div>`}
        </div>
      </details>
    </div>`;

    const content = [
      eventSection,
      pirSection,
      wirelessSection,
      identitySection,
      powerSection,
      this._renderFlexcCommunication(),
      this._renderXBusDevices(),
      renderEntityList(this._t("system.modem"), modemEntities),
    ].join("");

    if (!content) {
      return "";
    }

    return `
      <div class="technical-system-view">
        ${content}
      </div>
    `;
  }

  async _callAlarmService(
    service,
    entityId = this._config?.entity,
    displayName = null,
    actionLabel = null
  ) {
    if (!this._hass || !entityId) {
      return;
    }

    // Fail closed if the selected panel cannot be established or the target
    // belongs to another config entry. The panel-level entity is allowed.
    const panelIds = this._panelEntityIds();
    if (!panelIds?.has(entityId)) {
      console.warn("SPC FlexC Card: blocked alarm command outside selected panel", entityId);
      return;
    }

    const stateObj = this._hass.states[entityId];
    const name =
      displayName ||
      stateObj?.attributes?.friendly_name ||
      this._config?.name ||
      entityId;

    let prompt = this._t("confirm.generic", { name });

    switch (service) {
      case "alarm_disarm":
        prompt = this._t("confirm.disarm", { name });
        break;

      case "alarm_arm_away":
        prompt = this._t("confirm.full_arm", { name });
        break;

      case "alarm_arm_home":
        prompt = this._t("confirm.part_set", {
          action: actionLabel || this._t("state.part_a"),
          name,
        });
        break;

      case "alarm_arm_night":
        prompt = this._t("confirm.part_set", {
          action: actionLabel || this._t("state.part_b"),
          name,
        });
        break;

      default:
        break;
    }

    if (
      this._config.confirm_actions &&
      !window.confirm(prompt)
    ) {
      return;
    }

    if (!this._panelEntityIds()?.has(entityId)) return;

    await this._hass.callService(
      "alarm_control_panel",
      service,
      {
        entity_id: entityId,
      }
    );
  }

  _getDoors() {
    const doors = new Map();

    const ensureDoor = (doorId) => {
      const key = String(doorId);

      if (!doors.has(key)) {
        doors.set(key, {
          id: doorId,
          name: null,
          areaId: null,
          areaName: null,
          areaSide1: null,
          areaSide1Name: null,
          zoneId: null,
          zoneName: null,
          status: null,
          mode: null,
          buttons: {},
        });
      }

      return doors.get(key);
    };

    for (const item of this._scopedStates(true)) {
      const {
        entityId,
        stateObj,
        registryEntry,
      } = item;

      const attrs = stateObj?.attributes || {};
      const uniqueId = String(registryEntry?.unique_id || "");
      let doorId = attrs.door_id;
      let match = uniqueId.match(/_door_(\d+)_(status|mode)$/);

      if (match) {
        doorId = match[1];
      }

      if (doorId !== undefined && doorId !== null) {
        const door = ensureDoor(doorId);

        door.zoneId = attrs.zone_id ?? door.zoneId;
        door.zoneName = attrs.zone_name || door.zoneName;
        door.areaId = attrs.area_id ?? door.areaId;
        door.areaName = attrs.area_name || door.areaName;
        door.areaSide1 = attrs.area_side_1 ?? door.areaSide1;
        door.areaSide1Name = attrs.area_side_1_name || door.areaSide1Name;
        door.name = attrs.zone_name || door.name;

        const rawStatus = attrs.raw_status;
        const rawMode = attrs.raw_mode;

        if (match?.[2] === "status" || rawStatus !== undefined) {
          door.status = rawStatus ?? stateObj.state;
        }

        if (match?.[2] === "mode" || rawMode !== undefined) {
          door.mode = rawMode ?? stateObj.state;
        }

        if (!door.name) {
          const friendly = String(attrs.friendly_name || "").trim();
          door.name =
            friendly
              .replace(/\s+(Status|Mode|Statut)$/i, "")
              .trim() || null;
        }
      }

      match = uniqueId.match(
        /_door_(\d+)_(open_momentarily|open_permanently|set_normal|lock)$/
      );

      if (match && entityId.startsWith("button.")) {
        const door = ensureDoor(match[1]);
        door.buttons[match[2]] = entityId;
      }
    }

    return Array.from(doors.values())
      .filter(
        (door) =>
          door.status !== null ||
          door.mode !== null ||
          Object.keys(door.buttons).length
      )
      .map((door) => ({
        ...door,
        name:
          door.name ||
          door.zoneName ||
          this._t("door.name", { id: door.id }),
      }))
      .sort((a, b) => Number(a.id) - Number(b.id));
  }

  _doorAreasLabel(door) {
    const first =
      door.areaName ||
      (
        door.areaId !== null &&
        door.areaId !== undefined
          ? this._areaName(door.areaId)
          : null
      );

    const second =
      door.areaSide1Name ||
      (
        door.areaSide1 !== null &&
        door.areaSide1 !== undefined
          ? this._areaName(door.areaSide1)
          : null
      );

    if (first && second && first !== second) {
      return `${first} ↔ ${second}`;
    }

    return first || second || this._t("door.unknown_area");
  }

  _renderDoorButton(
    door,
    action,
    label,
    icon,
    primary = false
  ) {
    const entityId = door.buttons[action];

    if (!entityId || this._config.show_controls === false) {
      return "";
    }

    return `
      <button
        type="button"
        class="control-button door-control${primary ? " primary" : ""}"
        data-door-entity="${this._escapeHtml(entityId)}"
        data-door-name="${this._escapeHtml(door.name)}"
        data-door-action="${this._escapeHtml(label)}"
      >
        <ha-icon icon="${this._escapeHtml(icon)}"></ha-icon>
        <span>${this._escapeHtml(label)}</span>
      </button>
    `;
  }

  _renderDoors() {
    const doors = this._getDoors();

    if (!doors.length) {
      return `
        <div class="empty-state">
          <ha-icon icon="mdi:door-closed-lock"></ha-icon>
          <div>${this._t("door.none")}</div>
        </div>
      `;
    }

    return `
      <div class="door-list">
        ${doors
          .map(
            (door) => `
              <div class="door-card">
                <div class="door-header">
                  <div>
                    <div class="door-title">${this._escapeHtml(door.name)}</div>
                    <div class="door-areas">${this._escapeHtml(this._doorAreasLabel(door))}</div>
                  </div>
                  <ha-icon class="door-icon" icon="mdi:door"></ha-icon>
                </div>

                <div class="door-state-grid">
                  <div class="door-state-card">
                    <div class="door-state-label">${this._t("door.status")}</div>
                    <div class="door-state-value">${this._escapeHtml(door.status ?? "—")}</div>
                  </div>
                  <div class="door-state-card">
                    <div class="door-state-label">${this._t("door.mode")}</div>
                    <div class="door-state-value">${this._escapeHtml(door.mode ?? "—")}</div>
                  </div>
                </div>

                ${
                  door.zoneName
                    ? `
                      <div class="door-zone">
                        <ha-icon icon="mdi:shield-home-outline"></ha-icon>
                        <span>
                          ${this._t("zone.name", { id: door.zoneId ?? "" })}${
                            door.zoneId != null ? " · " : ""
                          }${this._escapeHtml(door.zoneName)}
                        </span>
                      </div>
                    `
                    : ""
                }

                <div class="door-controls">
                  ${this._renderDoorButton(
                    door,
                    "open_momentarily",
                    this._t("action.door_momentary"),
                    "mdi:door-open",
                    true
                  )}
                  ${this._renderDoorButton(
                    door,
                    "open_permanently",
                    this._t("action.door_permanent"),
                    "mdi:lock-open-variant"
                  )}
                  ${this._renderDoorButton(
                    door,
                    "set_normal",
                    this._t("action.door_normal"),
                    "mdi:door-closed"
                  )}
                  ${this._renderDoorButton(
                    door,
                    "lock",
                    this._t("action.door_lock"),
                    "mdi:lock"
                  )}
                </div>

                <div class="door-raw-note">
                  ${this._t("door.raw_note")}
                </div>
              </div>
            `
          )
          .join("")}
      </div>
    `;
  }

  async _callDoorButton(entityId, doorName, actionLabel) {
    if (!this._hass || !entityId) {
      return;
    }

    if (!this._panelEntityIds()?.has(entityId)) {
      console.warn("SPC FlexC Card: blocked cross-panel door command", entityId);
      return;
    }

    if (
      this._config.confirm_actions &&
      !window.confirm(
        this._t("confirm.door", {
          action: actionLabel,
          name: doorName,
        })
      )
    ) {
      return;
    }

    if (!this._panelEntityIds()?.has(entityId)) return;

    await this._hass.callService(
      "button",
      "press",
      {
        entity_id: entityId,
      }
    );
  }

  _renderTabs() {
    const hasDoors = this._getDoors().length > 0;

    if (!hasDoors && this._activeTab === "doors") {
      this._activeTab = "system";
    }

    const tabs = [
      ["system", this._t("tab.general")],
      ["areas", this._t("tab.areas")],
      ["zones", this._t("tab.detectors")],
      ...(hasDoors ? [["doors", this._t("tab.doors")]] : []),
      ["technical", this._t("tab.system")],
    ];

    return `<div class="tabs">${tabs.map(([id, label]) => `
      <button type="button" class="tab ${this._activeTab === id ? "active" : ""}" data-tab="${id}">
        ${this._escapeHtml(label)}
      </button>
    `).join("")}</div>`;
  }

  _renderSystem() {
    const alarm = this._getAlarmEntity();
    const rawState = alarm?.state || "unknown";
    const state = rawState === "unknown" && alarm?.attributes?.arming_summary === "mixed"
      ? "mixed"
      : rawState;
    const areas = this._getAreas();
    const zones = this._getNormalZones();
    const tampers = this._getTamperZones();

    const activeZones = zones.filter(
      (zone) => zone.state === "on"
    ).length;

    const activeTampers = tampers.filter(
      (zone) =>
        zone.state === "on" ||
        zone.eventTamper === true
    ).length;

    const zoneTamperAlerts = this._getZones().filter((zone) => zone.eventTamper === true).length;
    const zoneTroubleAlerts = this._getZones().filter((zone) => zone.eventTrouble === true).length;

    const controls =
      this._config.show_controls
        ? `
          <div class="area-controls">
            <button
              type="button"
              class="control-button"
              data-service="alarm_disarm"
              data-entity="${this._escapeHtml(this._config.entity)}"
            >
              <ha-icon icon="mdi:lock-open-variant"></ha-icon>
              <span>${this._t("action.disarm")}</span>
            </button>

            <button
              type="button"
              class="control-button primary"
              data-service="alarm_arm_away"
              data-entity="${this._escapeHtml(this._config.entity)}"
            >
              <ha-icon icon="mdi:lock"></ha-icon>
              <span>${this._t("action.full_arm")}</span>
            </button>
          </div>
        `
        : "";

    const areaSummary = areas.length
      ? this._tCount("group.area_count", areas.length)
      : this._t("group.no_area");
    const detectorSummary = zones.length
      ? this._tCount("group.detector_count", zones.length)
      : this._t("group.no_detector");

    return `
      <div class="system-view">
        <div class="area-overview">
          <div class="area-overview-row all">
            <ha-icon class="${this._stateClass(state)}" icon="${this._escapeHtml(this._stateIcon(state))}"></ha-icon>
            <div class="area-overview-name">${this._t("area.all")}</div>
            <div class="area-overview-state ${this._stateClass(state)}">${this._escapeHtml(this._stateLabel(state))}</div>
            ${controls}
          </div>
          ${areas.map((area) => {
            const areaEntity = this._getAreaAlarmEntity(area.id);
            const areaState = areaEntity?.stateObj?.state || "unknown";
            const label = areaState === "armed_home"
              ? this._partSetLabel(areaEntity, "a")
              : areaState === "armed_night"
                ? this._partSetLabel(areaEntity, "b")
                : this._stateLabel(areaState);
            return `
              <div class="area-overview-row">
                <ha-icon class="${this._stateClass(areaState)}" icon="${this._escapeHtml(this._stateIcon(areaState))}"></ha-icon>
                <div class="area-overview-name">${this._escapeHtml(this._t("area.name_full", { id: area.id, name: area.name }))}</div>
                <div class="area-overview-state ${this._stateClass(areaState)}">${this._escapeHtml(label)}</div>
                ${this._renderAreaControls(area, areaEntity)}
              </div>`;
          }).join("")}
          <div class="system-summary">
            ${areaSummary} · ${detectorSummary}
            ${zoneTamperAlerts ? `<span class="zone-tamper-alert"> · ${zoneTamperAlerts} ${this._t("zone.alert_tamper")}</span>` : ""}
            ${zoneTroubleAlerts ? `<span class="zone-trouble-alert"> · ${zoneTroubleAlerts} ${this._t("zone.alert_trouble")}</span>` : ""}
          </div>
        </div>

        <div class="summary-grid">
          <div class="summary-card">
            <ha-icon icon="mdi:shield-home-outline"></ha-icon>
            <div>
              <div class="summary-value">${areas.length}</div>
              <div class="summary-label">${this._t("tab.areas")}</div>
            </div>
          </div>

          <div class="summary-card">
            <ha-icon icon="mdi:motion-sensor"></ha-icon>
            <div>
              <div class="summary-value">${zones.length}</div>
              <div class="summary-label">
                ${this._t("tab.detectors")}
                ${
                  activeZones
                    ? `<span class="warning"> · ${this._tCount("group.active_count", activeZones)}</span>`
                    : ""
                }
              </div>
            </div>
          </div>

          <div class="summary-card">
            <ha-icon icon="mdi:shield-alert-outline"></ha-icon>
            <div>
              <div class="summary-value">${tampers.length}</div>
              <div class="summary-label">
                ${this._t("group.tampers")}
                ${
                  activeTampers
                    ? `<span class="danger"> · ${this._t("group.in_fault", { count: activeTampers })}</span>`
                    : ""
                }
              </div>
            </div>
          </div>
        </div>

        ${zoneTamperAlerts || zoneTroubleAlerts ? `<div class="technical-section">
          ${zoneTamperAlerts ? `<span class="zone-tamper-alert"><ha-icon icon="mdi:shield-alert-outline"></ha-icon> ${zoneTamperAlerts} ${this._t("zone.alert_tamper")}</span>` : ""}
          ${zoneTroubleAlerts ? `<span class="zone-trouble-alert"><ha-icon icon="mdi:alert-outline"></ha-icon> ${zoneTroubleAlerts} ${this._t("zone.alert_trouble")}</span>` : ""}
        </div>` : ""}
        ${this._renderSystemDiagnostics()}
      </div>
    `;
  }

  _partSetLabel(areaEntity, part) {
    const attrs = areaEntity?.stateObj?.attributes || {};
    const attributeName = part === "a" ? "partset_a_name" : "partset_b_name";
    const value = attrs[attributeName];

    return value != null && String(value).trim()
      ? String(value).trim()
      : this._t(part === "a" ? "state.part_a" : "state.part_b");
  }

  _renderAreaControls(area, areaEntity) {
    if (!this._config.show_controls || !areaEntity) {
      return "";
    }

    const { entityId, stateObj } = areaEntity;
    const attrs = stateObj?.attributes || {};
    const state = stateObj?.state || "unknown";

    const stableArmedStates = new Set([
      "armed_away",
      "armed_home",
      "armed_night",
      "armed_vacation",
      "armed_custom_bypass",
    ]);

    const buttons = [];

    if (state === "disarmed") {
      buttons.push(`
        <button
          type="button"
          class="control-button primary"
          data-service="alarm_arm_away"
          data-entity="${this._escapeHtml(entityId)}"
          data-name="${this._escapeHtml(area.name)}"
        >
          <ha-icon icon="mdi:lock"></ha-icon>
          <span>${this._t("action.arm")}</span>
        </button>
      `);

      if (attrs.partset_a_enabled === true) {
        const label = this._partSetLabel(areaEntity, "a");
        buttons.push(`
          <button
            type="button"
            class="control-button"
            data-service="alarm_arm_home"
            data-entity="${this._escapeHtml(entityId)}"
            data-name="${this._escapeHtml(area.name)}"
            data-action-label="${this._escapeHtml(label)}"
          >
            <ha-icon icon="mdi:shield-home"></ha-icon>
            <span>${this._escapeHtml(label)}</span>
          </button>
        `);
      }

      if (attrs.partset_b_enabled === true) {
        const label = this._partSetLabel(areaEntity, "b");
        buttons.push(`
          <button
            type="button"
            class="control-button"
            data-service="alarm_arm_night"
            data-entity="${this._escapeHtml(entityId)}"
            data-name="${this._escapeHtml(area.name)}"
            data-action-label="${this._escapeHtml(label)}"
          >
            <ha-icon icon="mdi:weather-night"></ha-icon>
            <span>${this._escapeHtml(label)}</span>
          </button>
        `);
      }
    } else if (stableArmedStates.has(state) || state === "triggered") {
      buttons.push(`
        <button
          type="button"
          class="control-button"
          data-service="alarm_disarm"
          data-entity="${this._escapeHtml(entityId)}"
          data-name="${this._escapeHtml(area.name)}"
        >
          <ha-icon icon="mdi:lock-open-variant"></ha-icon>
          <span>${this._t("action.disarm")}</span>
        </button>
      `);
    }

    if (!buttons.length) {
      return "";
    }

    return `
      <div class="area-controls">
        ${buttons.join("")}
      </div>
    `;
  }

  _renderAreas() {
    const areas = this._getAreas();
    const zones = this._getZones();

    if (!areas.length) {
      return `
        <div class="empty-state">
          <ha-icon icon="mdi:shield-home-outline"></ha-icon>
          <div>${this._t("area.none")}</div>
        </div>
      `;
    }

    return `
      <div class="list area-list">
        ${areas
          .map((area) => {
            const areaZones = zones.filter(
              (zone) => String(zone.areaId) === String(area.id)
            );

            const normalZones = areaZones.filter(
              (zone) =>
                zone.zoneType !== "tamper" &&
                zone.deviceClass !== "tamper"
            );

            const tampers = areaZones.filter(
              (zone) =>
                zone.zoneType === "tamper" ||
                zone.deviceClass === "tamper"
            );

            const activeZones = normalZones.filter(
              (zone) => zone.state === "on"
            ).length;

            const activeTampers = areaZones.filter(
              (zone) =>
                zone.eventTamper === true ||
                ((zone.zoneType === "tamper" || zone.deviceClass === "tamper") &&
                  zone.state === "on")
            ).length;

            const areaEntity = this._getAreaAlarmEntity(area.id);

            const mode =
              areaEntity?.stateObj?.attributes?.mode_name ??
              area.modeName ??
              areaEntity?.stateObj?.attributes?.mode ??
              area.mode ??
              "unknown";

            const renderedState = areaEntity?.stateObj?.state || null;
            const stateClass = renderedState
              ? this._stateClass(renderedState)
              : this._modeClass(mode);

            const icon = renderedState
              ? this._stateIcon(renderedState)
              : stateClass === "ok"
                ? "mdi:lock-open-variant"
                : "mdi:lock";

            const label =
              renderedState === "armed_home"
                ? this._partSetLabel(areaEntity, "a")
                : renderedState === "armed_night"
                  ? this._partSetLabel(areaEntity, "b")
                  : renderedState === "disarmed"
                    ? this._t("state.disarmed_masc")
                    : renderedState
                      ? this._stateLabel(renderedState)
                      : this._modeLabel(mode);

            return `
              <div class="area-card">
                <div class="area-card-header">
                  <div class="area-card-title">${this._escapeHtml(area.name)}</div>
                  <div class="badge ${stateClass}">${this._escapeHtml(label)}</div>
                </div>

                <div class="area-lock">
                  <ha-icon class="${stateClass}" icon="${this._escapeHtml(icon)}"></ha-icon>
                </div>

                <div class="area-meta">
                  <span>${this._tCount("group.detector_count", normalZones.length)}</span>
                  ${
                    activeZones
                      ? `<span class="warning">${this._tCount("group.active_count", activeZones)}</span>`
                      : `<span class="ok">${this._t("group.rest")}</span>`
                  }
                  ${
                    activeTampers
                      ? `<span class="danger">${this._t("area.tamper")}</span>`
                      : ""
                  }
                </div>

                ${this._lastAreaChange(areaEntity?.stateObj)}
                ${this._renderAreaControls(area, areaEntity)}
              </div>
            `;
          })
          .join("")}
      </div>
    `;
  }

  _renderZoneRow(zone) {
    const stateInfo = this._zoneStateInfo(zone);

    return `
      <div class="zone-row">
        <div class="zone-icon ${stateInfo.className}">
          <ha-icon icon="${this._escapeHtml(this._zoneIcon(zone))}"></ha-icon>
        </div>

        <div class="zone-main">
          <div class="zone-name">${this._escapeHtml(zone.name)}</div>
          <div class="zone-area">${this._escapeHtml(this._areaName(zone.areaId))}</div>
          ${zone.eventTamper === true ? `<span class="zone-tamper-alert"><ha-icon icon="mdi:shield-alert-outline"></ha-icon> ${this._t("zone.alert_tamper")}</span>` : ""}
          ${zone.eventTrouble === true ? `<span class="zone-trouble-alert"><ha-icon icon="mdi:alert-outline"></ha-icon> ${this._t("zone.alert_trouble")}</span>` : ""}
        </div>

        <div class="zone-state ${stateInfo.className}">
          ${this._escapeHtml(stateInfo.label)}
        </div>
      </div>
    `;
  }

  _renderZones() {
    const zones = this._getNormalZones();
    const tampers = this._getTamperZones();

    if (!zones.length && !tampers.length && !this._panelEntityIds()) {
      return `<div class="empty-state">
        <ha-icon icon="mdi:progress-clock"></ha-icon>
        <div>${this._t("zone.loading", {}, "Chargement des entités SPC…")}</div>
      </div>`;
    }

    if (!zones.length && !tampers.length) {
      return `
        <div class="empty-state">
          <ha-icon icon="mdi:motion-sensor-off"></ha-icon>
          <div>${this._t("zone.none")}</div>
        </div>
      `;
    }

    return `
      <div class="zones-view">
        ${
          zones.length
            ? `
              <div class="group-title">
                ${this._t("group.detectors")}
                <span>${zones.length}</span>
              </div>
              <div class="zone-list">
                ${zones.map((zone) => this._renderZoneRow(zone)).join("")}
              </div>
            `
            : ""
        }

        ${
          tampers.length
            ? `
              <div class="group-title tamper-title">
                ${this._t("group.tampers")}
                <span>${tampers.length}</span>
              </div>
              <div class="zone-list tamper-list">
                ${tampers.map((zone) => this._renderZoneRow(zone)).join("")}
              </div>
            `
            : ""
        }
      </div>
    `;
  }

  _renderIntrusionBanner() {
    const alarm = this._getAlarmEntity();
    const areas = this._getAreas();
    const active = areas.filter((area) => area.raw?.alarm_event_active === true);
    if (!active.length && alarm?.state !== "triggered") return "";

    const details = active.map((area) => {
      const zones = Array.isArray(area.raw?.alarm_zones)
        ? area.raw.alarm_zones.map((zone) => zone?.name || `Zone ${zone?.zone_id ?? "?"}`)
        : [];
      return this._escapeHtml(
        zones.length ? `${area.name} : ${zones.join(", ")}` : area.name
      );
    });

    return `
      <div class="spc-intrusion-banner" role="alert" aria-live="assertive">
        <ha-icon icon="mdi:alarm-light"></ha-icon>
        <div>
          <strong>${this._escapeHtml(this._t("state.alarm"))}</strong>
          ${details.length ? `<div>${details.join("<br>")}</div>` : ""}
        </div>
      </div>
    `;
  }

  _renderActiveView() {
    switch (this._activeTab) {
      case "areas":
        return this._renderAreas();

      case "zones":
        return this._renderZones();

      case "doors":
        return this._getDoors().length
          ? this._renderDoors()
          : this._renderSystem();

      case "technical":
        return this._renderTechnicalSystem();

      case "system":
      default:
        return this._renderSystem();
    }
  }

  _styles() {
    return `
      <style>
        :host {
          display: block;
          width: 100%;
        }

        ha-card {
          overflow: hidden;
          padding: 0;
          width: 100%;
        }

        .card {
          padding: 22px;
        }

        .spc-intrusion-banner {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px;
          margin-bottom: 16px;
          border-radius: 10px;
          background: var(--error-color, #b3261e);
          color: #fff;
          animation: spc-intrusion-pulse 1.3s ease-in-out infinite;
        }

        .spc-intrusion-banner ha-icon {
          flex-shrink: 0;
        }

        @keyframes spc-intrusion-pulse {
          50% { opacity: 0.65; }
        }

        @media (prefers-reduced-motion: reduce) {
          .spc-intrusion-banner { animation: none; }
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 10px;
        }

        .title {
          font-size: 24px;
          line-height: 1.2;
          font-weight: 600;
        }

        .entity {
          margin-top: 4px;
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .tabs {
          display: flex;
          gap: 28px;
          overflow-x: auto;
          border-bottom: 1px solid var(--divider-color);
          margin: 0 -22px 20px;
          padding: 0 22px;
        }

        .tab {
          appearance: none;
          border: 0;
          border-bottom: 3px solid transparent;
          background: transparent;
          color: var(--secondary-text-color);
          cursor: pointer;
          font: inherit;
          font-weight: 600;
          padding: 12px 0 10px;
          white-space: nowrap;
        }

        .tab:hover {
          color: var(--primary-text-color);
        }

        .tab.active {
          color: var(--primary-color);
          border-bottom-color: var(--primary-color);
        }

        .system-panel {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 260px;
          padding: 28px;
          border-radius: 14px;
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.08)
          );
        }

        .system-state {
          font-size: 22px;
          font-weight: 700;
          text-align: center;
        }

        .system-icon {
          --mdc-icon-size: 140px;
          margin: 22px 0;
        }

        .system-summary {
          color: var(--secondary-text-color);
          text-align: center;
        }

        .summary-grid {
          display: grid;
          grid-template-columns: repeat(
            3,
            minmax(0, 1fr)
          );
          gap: 12px;
          margin-top: 16px;
        }

        .summary-card {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
          padding: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
        }

        .summary-card ha-icon {
          --mdc-icon-size: 28px;
          flex: 0 0 auto;
        }

        .summary-card > div {
          min-width: 0;
        }

        .summary-value {
          font-size: 20px;
          font-weight: 700;
          line-height: 1.1;
        }

        .summary-label {
          max-width: 100%;
          color: var(--secondary-text-color);
          font-size: 11px;
          line-height: 1.25;
          white-space: normal;
          overflow-wrap: anywhere;
          word-break: normal;
          hyphens: auto;
        }

        .alarm-controls {
          display: grid;
          gap: 10px;
          margin-top: 18px;
        }

        .system-controls {
          grid-template-columns: repeat(
            2,
            minmax(0, 1fr)
          );
        }

        .area-controls {
          display: grid;
          grid-template-columns: repeat(
            auto-fit,
            minmax(120px, 1fr)
          );
          gap: 10px;
          margin-top: 16px;
        }

        .control-button {
          appearance: none;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 7px;
          min-height: 70px;
          padding: 10px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          cursor: pointer;
          font: inherit;
        }

        .control-button:hover {
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.08)
          );
        }

        .control-button.primary {
          border-color: var(--primary-color);
          color: var(--primary-color);
        }

        .control-button ha-icon {
          --mdc-icon-size: 27px;
        }

        .diagnostics-block {
          margin-top: 18px;
          padding: 16px;
          border: 1px solid var(--divider-color);
          border-radius: 14px;
        }

        .diagnostic-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 4px 0 12px;
        }

        .diagnostic-row > ha-icon {
          --mdc-icon-size: 28px;
        }

        .diagnostic-main {
          min-width: 0;
        }

        .diagnostic-name {
          font-weight: 600;
        }

        .diagnostic-detail {
          margin-top: 2px;
          font-size: 12px;
        }

        .fault-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color);
          font-weight: 700;
        }

        .fault-count {
          margin-left: auto;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 22px;
          height: 22px;
          padding: 0 6px;
          border-radius: 11px;
          background: color-mix(
            in srgb,
            currentColor 14%,
            transparent
          );
        }

        .fault-list {
          display: grid;
          gap: 7px;
          margin-top: 10px;
        }

        .fault-row {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 9px;
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.08)
          );
        }

        .fault-row ha-icon {
          --mdc-icon-size: 20px;
        }

        .fault-ok {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color);
          font-weight: 600;
        }

        .engineer-warning {
          margin-top: 8px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color);
        }

        .technical-system-view {
          display: grid;
          gap: 18px;
        }

        .technical-section {
          padding-top: 15px;
        }

        .event-history-row {
          padding: 3px 0;
          line-height: 1.3;
        }

        .technical-section-title {
          margin-bottom: 8px;
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }

        .technical-row {
          display: grid;
          grid-template-columns: minmax(130px, 0.7fr) minmax(0, 1.3fr);
          gap: 14px;
          padding: 6px 0;
          border-bottom: 1px solid color-mix(
            in srgb,
            var(--divider-color) 55%,
            transparent
          );
        }

        .technical-row:last-child {
          border-bottom: 0;
        }

        .technical-label {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .technical-value {
          min-width: 0;
          overflow-wrap: anywhere;
          text-align: right;
          font-size: 13px;
          font-weight: 600;
        }

        .ats-list,
        .atp-list,
        .xbus-list {
          display: grid;
          gap: 10px;
        }

        .ats-card,
        .atp-card,
        .xbus-card {
          padding: 12px;
          border-radius: 11px;
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.08)
          );
        }

        .atp-list {
          margin-top: 10px;
          padding-left: 10px;
          border-left: 2px solid var(--divider-color);
        }

        .atp-card {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
        }

        .ats-title,
        .atp-title,
        .xbus-title {
          font-weight: 700;
        }

        .xbus-title {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 4px;
        }

        .list {
          display: grid;
          gap: 14px;
        }

        .area-list {
          grid-template-columns: repeat(
            auto-fit,
            minmax(280px, 1fr)
          );
        }

        .area-card {
          padding: 18px;
          border-radius: 14px;
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.08)
          );
        }

        .area-card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }

        .area-card-title {
          font-size: 18px;
          font-weight: 700;
        }

        .badge {
          font-weight: 700;
        }

        .area-lock {
          display: flex;
          justify-content: center;
          padding: 18px 0 10px;
        }

        .area-lock ha-icon {
          --mdc-icon-size: 78px;
        }

        .area-meta {
          display: flex;
          justify-content: center;
          flex-wrap: wrap;
          gap: 8px 18px;
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .last-change {
          margin-top: 15px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color);
          text-align: center;
        }

        .last-change-label {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .last-change-value {
          margin-top: 4px;
          font-size: 13px;
          color: var(--primary-text-color);
        }

        .last-change-user {
          color: var(--secondary-text-color);
        }

        .zones-view {
          display: grid;
          gap: 12px;
        }

        .group-title {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 2px;
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }

        .group-title span {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 18px;
          height: 18px;
          padding: 0 5px;
          border-radius: 9px;
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.12)
          );
          font-size: 10px;
        }

        .tamper-title {
          margin-top: 16px;
        }

        .zone-list {
          display: grid;
          gap: 7px;
        }

        .zone-row {
          display: grid;
          grid-template-columns:
            46px minmax(0, 1fr) auto;
          align-items: center;
          gap: 12px;
          min-height: 52px;
          padding: 8px 12px;
          border-radius: 10px;
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.08)
          );
        }

        .zone-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border: 2px solid currentColor;
          border-radius: 50%;
        }

        .zone-icon ha-icon {
          --mdc-icon-size: 22px;
        }

        .zone-main {
          min-width: 0;
        }

        .zone-name {
          overflow: hidden;
          font-weight: 600;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .zone-area {
          overflow: hidden;
          margin-top: 2px;
          color: var(--secondary-text-color);
          font-size: 12px;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .zone-state {
          font-weight: 700;
          text-align: right;
          white-space: nowrap;
        }

        .door-list {
          display: grid;
          grid-template-columns: repeat(
            auto-fit,
            minmax(300px, 1fr)
          );
          gap: 14px;
        }

        .door-card {
          padding: 18px;
          border-radius: 14px;
          background: var(
            --secondary-background-color,
            rgba(127, 127, 127, 0.08)
          );
        }

        .door-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 14px;
        }

        .door-title {
          font-size: 18px;
          font-weight: 700;
        }

        .door-areas,
        .door-zone,
        .door-raw-note {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .door-areas {
          margin-top: 3px;
        }

        .door-icon {
          --mdc-icon-size: 38px;
        }

        .door-state-grid {
          display: grid;
          grid-template-columns:
            1fr 1fr;
          gap: 10px;
          margin-top: 16px;
        }

        .door-state-card {
          padding: 11px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
        }

        .door-state-label {
          color: var(--secondary-text-color);
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .door-state-value {
          margin-top: 3px;
          font-size: 18px;
          font-weight: 700;
        }

        .door-zone {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 12px;
        }

        .door-zone ha-icon {
          --mdc-icon-size: 18px;
        }

        .door-controls {
          display: grid;
          grid-template-columns:
            repeat(2, minmax(0, 1fr));
          gap: 10px;
          margin-top: 16px;
        }

        .door-raw-note {
          margin-top: 14px;
          line-height: 1.4;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          min-height: 180px;
          color: var(--secondary-text-color);
          text-align: center;
        }

        .empty-state ha-icon {
          --mdc-icon-size: 54px;
        }

        .ok {
          color: var(
            --success-color,
            #4caf50
          );
        }

        .warning {
          color: var(
            --warning-color,
            #ff9800
          );
        }

        .danger {
          color: var(
            --error-color,
            #f44336
          );
        }

        .partial {
          color: var(--info-color, #039be5);
        }

        .area-overview {
          display: grid;
          gap: 8px;
          padding: 12px;
          border-radius: 12px;
          background: var(--secondary-background-color);
        }

        .area-overview-row {
          display: grid;
          grid-template-columns: 28px minmax(120px, 1fr) minmax(90px, auto) auto;
          align-items: center;
          gap: 10px;
          padding: 6px 4px;
          border-bottom: 1px solid var(--divider-color);
        }

        .area-overview-row.all {
          font-weight: 600;
        }

        .area-overview-row .area-controls {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 6px;
          margin-top: 0;
        }

        .area-overview-row .control-button {
          flex-direction: row;
          min-height: 36px;
          padding: 6px 10px;
          gap: 6px;
        }

        .area-overview-state {
          font-weight: 500;
        }

        .fault-row.muted {
          color: var(--secondary-text-color);
          background: none;
        }

        .fault-actions {
          display: flex;
          justify-content: flex-end;
          margin-top: 8px;
        }

        .fault-actions .control-button {
          flex-direction: row;
          min-height: 36px;
          padding: 6px 12px;
        }

        @media (max-width: 600px) {
          .area-overview-row {
            grid-template-columns: 28px 1fr auto;
          }
          .area-overview-row .area-controls {
            grid-column: 1 / -1;
            justify-content: flex-start;
          }
        }

        .muted {
          color: var(--secondary-text-color);
        }

        @media (max-width: 520px) {
          .door-list,
          .door-controls,
          .door-state-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 700px) {
          .card {
            padding: 16px;
          }

          .tabs {
            margin-left: -16px;
            margin-right: -16px;
            padding-left: 16px;
            padding-right: 16px;
          }

          .summary-grid {
            grid-template-columns: 1fr;
          }

          .technical-row {
            grid-template-columns: 1fr;
            gap: 2px;
          }

          .technical-value {
            text-align: left;
          }

          .system-controls {
            grid-template-columns: repeat(
              2,
              minmax(0, 1fr)
            );
          }

          .area-list {
            grid-template-columns: 1fr;
          }

          .system-panel {
            min-height: 220px;
          }

          .system-icon {
            --mdc-icon-size: 110px;
          }
        }

        @media (max-width: 420px) {
          .zone-row {
            grid-template-columns:
              40px minmax(0, 1fr);
          }

          .zone-state {
            grid-column: 2;
            text-align: left;
            font-size: 12px;
          }

          .system-controls {
            grid-template-columns:
              1fr 1fr;
          }
        }
      </style>
    `;
  }

  _render() {
    if (!this._config || !this._hass) {
      return;
    }

    const stateObj = this._getAlarmEntity();

    if (!stateObj) {
      this.innerHTML = `
        <ha-card>
          <div style="padding:16px">
            ${this._escapeHtml(
              this._t("card.entity_not_found", {
                entity: this._config.entity,
              })
            )}
          </div>
        </ha-card>
      `;
      return;
    }

    const title =
      this._config.name ||
      stateObj.attributes.friendly_name ||
      "SPC FlexC";

    const previousCard = this.querySelector(":scope > ha-card");
    const previousTabIds = previousCard
      ? Array.from(previousCard.querySelectorAll("[data-tab]"), (tab) => tab.dataset.tab).join("|")
      : null;
    const previousActiveTab = previousCard?.querySelector("[data-tab].active")?.dataset.tab;

    const markup = `
      <ha-card>
        ${this._styles()}

        <div class="card">
          ${this._config.hide_header ? "" : `<div class="header">
            <div>
              <div class="title">
                ${this._escapeHtml(title)}
              </div>
            </div>
          </div>`}

          ${this._renderTabs()}

          ${this._renderIntrusionBanner()}

          <div class="content">
            ${this._renderActiveView()}
          </div>
        </div>
      </ha-card>
    `;
    const template = document.createElement("template");
    template.innerHTML = markup;
    const nextCard = template.content.querySelector("ha-card");
    const nextTabIds = Array.from(nextCard.querySelectorAll("[data-tab]"), (tab) => tab.dataset.tab).join("|");
    const nextActiveTab = nextCard.querySelector("[data-tab].active")?.dataset.tab;
    const preserveTabs = previousCard &&
      previousTabIds === nextTabIds &&
      previousActiveTab === nextActiveTab;

    if (preserveTabs) {
      // Keep the existing tab strip connected during routine state updates.
      // Firefox otherwise reactivates its overlay scrollbar on each DOM detach.
      const oldContent = previousCard.querySelector(".content");
      const nextContent = nextCard.querySelector(".content");
      if (oldContent && nextContent) oldContent.replaceWith(nextContent);

      const oldBanner = previousCard.querySelector(".spc-intrusion-banner");
      const nextBanner = nextCard.querySelector(".spc-intrusion-banner");
      if (oldBanner && nextBanner) oldBanner.replaceWith(nextBanner);
      else if (oldBanner) oldBanner.remove();
      else if (nextBanner) previousCard.querySelector(".content")?.before(nextBanner);

      const oldTitle = previousCard.querySelector(".title");
      const nextTitle = nextCard.querySelector(".title");
      if (oldTitle && nextTitle) oldTitle.textContent = nextTitle.textContent;
    } else {
      this.replaceChildren(nextCard);
    }

    if (!preserveTabs) this.querySelectorAll("[data-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        this._activeTab = button.dataset.tab;
        this._saveActiveTab(this._activeTab);
        this._render();
      });
    });

    this.querySelectorAll("[data-service]").forEach((button) => {
      button.addEventListener("click", () => {
        this._callAlarmService(
          button.dataset.service,
          button.dataset.entity || this._config.entity,
          button.dataset.name || null,
          button.dataset.actionLabel || null
        );
      });
    });

    this.querySelectorAll("[data-spc-service]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (this._config.confirm_actions && button.dataset.confirm && !window.confirm(button.dataset.confirm)) {
          return;
        }
        await this._hass.callService("spc_flexc", button.dataset.spcService, {});
      });
    });

    this.querySelectorAll("[data-door-entity]").forEach((button) => {
      button.addEventListener("click", () => {
        this._callDoorButton(
          button.dataset.doorEntity,
          button.dataset.doorName || this._t("door.fallback_name"),
          button.dataset.doorAction || this._t("action.execute")
        );
      });
    });
  }
}

class SpcFlexCCardEditor extends HTMLElement {
  setConfig(config) {
    const nextConfig = {
      show_controls: true,
      confirm_actions: true,
      ...config,
    };
    const previousConfig = this._config;
    this._config = nextConfig;

    // Home Assistant may echo config-changed back through setConfig.
    // Do not replace focused inputs when the visible settings are unchanged.
    if (
      !previousConfig ||
      previousConfig.entity !== nextConfig.entity ||
      previousConfig.name !== nextConfig.name ||
      previousConfig.show_controls !== nextConfig.show_controls ||
      previousConfig.confirm_actions !== nextConfig.confirm_actions
    ) {
      this._render();
    }
  }

  set hass(hass) {
    const wasReady = Boolean(this._hass);
    this._hass = hass;
    // State updates are frequent: rebuilding the editor would close an open
    // dropdown and reset a field while the user is typing.
    if (!wasReady) {
      this._render();
    }
  }

  _escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _t(key, variables = {}, fallback = key) {
    if (typeof spcFlexCTranslate === "function") {
      return spcFlexCTranslate(this._hass, key, variables, fallback);
    }
    return fallback;
  }

  _changed() {
    const config = {
      ...this._config,

      entity:
        this.querySelector("#entity")?.value || "",

      name:
        this.querySelector("#name")?.value || undefined,

      show_controls: Boolean(
        this.querySelector("#show_controls")?.checked
      ),

      confirm_actions: Boolean(
        this.querySelector("#confirm_actions")?.checked
      ),
    };

    this._config = config;

    this.dispatchEvent(
      new CustomEvent(
        "config-changed",
        {
          detail: { config },
          bubbles: true,
          composed: true,
        }
      )
    );
  }

  _render() {
    if (!this._config || !this._hass) {
      return;
    }

    const options = Object.keys(this._hass.states)
      .filter((id) => id.startsWith("alarm_control_panel."))
      .map((id) => {
        const stateObj = this._hass.states[id];
        const name = stateObj?.attributes?.friendly_name || id;

        return `
          <option
            value="${this._escapeHtml(id)}"
            ${id === this._config.entity ? "selected" : ""}
          >
            ${this._escapeHtml(name)}
            (${this._escapeHtml(id)})
          </option>
        `;
      })
      .join("");

    this.innerHTML = `
      <style>
        .editor {
          display: grid;
          gap: 16px;
        }

        label {
          display: grid;
          gap: 6px;
        }

        input,
        select {
          box-sizing: border-box;
          width: 100%;
          padding: 9px;
        }

        .toggle {
          display: flex;
          align-items: center;
          gap: 9px;
        }

        .toggle input {
          width: auto;
        }

        .help {
          color: var(--secondary-text-color);
          font-size: 12px;
          line-height: 1.4;
        }
      </style>

      <div class="editor">
        <label>
          ${this._t("editor.entity")}
          <select id="entity">
            <option value="">${this._t("editor.select_entity")}</option>
            ${options}
          </select>
        </label>

        <label>
          ${this._t("editor.name")}
          <input
            id="name"
            type="text"
            value="${this._escapeHtml(this._config.name || "")}"
            placeholder="SPC FlexC"
          >
        </label>

        <label class="toggle">
          <input
            id="show_controls"
            type="checkbox"
            ${this._config.show_controls !== false ? "checked" : ""}
          >
          ${this._t("editor.show_controls")}
        </label>

        <label class="toggle">
          <input
            id="confirm_actions"
            type="checkbox"
            ${this._config.confirm_actions !== false ? "checked" : ""}
          >
          ${this._t("editor.confirm_actions")}
        </label>

        <div class="help">
          ${this._t("editor.help")}
        </div>
      </div>
    `;

    this.querySelectorAll("input, select").forEach((element) => {
      element.addEventListener("change", () => this._changed());
      element.addEventListener("input", () => this._changed());
    });
  }
}

if (!customElements.get("spc-flexc-card")) {
  customElements.define("spc-flexc-card", SpcFlexCCard);
}

if (!customElements.get("spc-flexc-card-editor")) {
  customElements.define("spc-flexc-card-editor", SpcFlexCCardEditor);
}

window.customCards = window.customCards || [];

if (!window.customCards.some((card) => card.type === "spc-flexc-card")) {
  window.customCards.push({
    type: "spc-flexc-card",
    name: "SPC FlexC Card",
    description: "",
    preview: true,
    documentationURL:
      "https://github.com/minimicro34/ha-spc-flexc-card",
  });
}

console.info(
  `%c SPC FLEXC CARD %c ${CARD_VERSION} `,
  "color:white;background:#1565c0;font-weight:700;",
  "color:#1565c0;background:white;font-weight:700;"
);

/* SPC FlexC Card v1.0.5 extensions: Mapping Gates, door supervision and zone inhibition. */

const spcFlexCBaseLoadActiveTab = SpcFlexCCard.prototype._loadActiveTab;
const spcFlexCBaseGetZones = SpcFlexCCard.prototype._getZones;
const spcFlexCBaseGetDoors = SpcFlexCCard.prototype._getDoors;
const spcFlexCBaseStyles = SpcFlexCCard.prototype._styles;
const spcFlexCBaseRender = SpcFlexCCard.prototype._render;

SpcFlexCCard.prototype._loadActiveTab = function (entityId) {
  const value = spcFlexCBaseLoadActiveTab.call(this, entityId);
  if (value) return value;

  const key = this._activeTabStorageKey(entityId);
  if (!key) return null;

  try {
    return window.localStorage.getItem(key) === "outputs" ? "outputs" : null;
  } catch {
    return null;
  }
};

SpcFlexCCard.prototype._getMappingGates = function () {
  if (!this._hass) return [];

  const scoped = this._scopedStates(true);
  // Never scan all Home Assistant entities if the selected SPC scope is unavailable.
  const candidates = scoped;

  return candidates
    .filter(({ entityId, stateObj, registryEntry }) => {
      if (!entityId.startsWith("switch.")) return false;
      const attrs = stateObj?.attributes || {};
      const uniqueId = String(registryEntry?.unique_id || "");
      return attrs.mg_id != null || /_mapping_gate_\d+$/.test(uniqueId);
    })
    .map(({ entityId, stateObj, registryEntry }) => {
      const attrs = stateObj?.attributes || {};
      const uniqueId = String(registryEntry?.unique_id || "");
      const match = uniqueId.match(/_mapping_gate_(\d+)$/);
      const mgId = attrs.mg_id ?? match?.[1] ?? null;
      return {
        entityId,
        id: mgId,
        name:
          attrs.mg_name ||
          attrs.friendly_name ||
          (mgId != null ? this._t("output.name", { id: mgId }) : entityId),
        state: stateObj.state,
      };
    })
    .sort((a, b) => Number(a.id) - Number(b.id));
};

SpcFlexCCard.prototype._getZones = function () {
  const zones = spcFlexCBaseGetZones.call(this);
  if (!this._hass || !zones.length) return zones;

  const byId = new Map(zones.map((zone) => [String(zone.zoneId), zone]));
  const scoped = this._scopedStates(true);
  // Never scan all Home Assistant entities if the selected SPC scope is unavailable.
  const candidates = scoped;

  for (const { entityId, stateObj, registryEntry } of candidates) {
    const attrs = stateObj?.attributes || {};
    const uniqueId = String(registryEntry?.unique_id || "");

    if (entityId.startsWith("switch.")) {
      const match = uniqueId.match(/_zone_(\d+)_inhibition$/);
      const zoneId = attrs.zone_id ?? match?.[1] ?? null;

      if (zoneId == null || (!match && attrs.zone_id == null)) continue;

      const zone = byId.get(String(zoneId));
      if (!zone) continue;

      zone.inhibited = stateObj.state === "on";
      zone.inhibitionEntityId = entityId;
      continue;
    }

    if (entityId.startsWith("button.")) {
      const match = uniqueId.match(/_zone_(\d+)_restore$/);
      if (!match && attrs.restore_allowed == null) continue;
      const zoneId = attrs.zone_id ?? match?.[1] ?? null;
      if (zoneId == null) continue;

      const zone = byId.get(String(zoneId));
      if (!zone) continue;

      zone.restoreEntityId = entityId;
      zone.restoreAllowed =
        attrs.restore_allowed === true ||
        attrs.restore_allowed === 1 ||
        attrs.restore_allowed === "1";
      zone.restoreAvailable =
        zone.restoreAllowed && stateObj.state !== "unavailable";
    }
  }

  return zones;
};

SpcFlexCCard.prototype._renderZoneRow = function (zone) {
  const stateInfo = this._zoneStateInfo(zone);
  const inhibited = zone.inhibited === true;
  const visualClass = stateInfo.className;

  return `
    <div class="zone-row${inhibited ? " zone-row-inhibited" : ""}">
      <div class="zone-icon ${visualClass}">
        <ha-icon icon="${this._escapeHtml(this._zoneIcon(zone))}"></ha-icon>
      </div>

      <div class="zone-main">
        <div class="zone-name">${this._escapeHtml(zone.name)}</div>
        <div class="zone-area">
          ${this._escapeHtml(this._areaName(zone.areaId))}
          ${inhibited ? `<span class="zone-operating-badge zone-inhibited">${this._t("zone.inhibited")}</span>` : ""}
        </div>
      </div>

      <div class="zone-state ${visualClass}">
        ${this._escapeHtml(stateInfo.label)}
      </div>

      ${this._config.show_controls === false || !zone.restoreAvailable ? "" : `
        <button type="button" class="zone-restore-button"
          data-zone-restore-entity="${this._escapeHtml(zone.restoreEntityId)}"
          data-zone-restore-name="${this._escapeHtml(zone.name)}">
          ${this._t("action.restore")}
        </button>
      `}
    </div>
  `;
};

SpcFlexCCard.prototype._getDoors = function () {
  const doors = spcFlexCBaseGetDoors.call(this);
  const byId = new Map(doors.map((door) => [String(door.id), door]));

  for (const { stateObj } of this._scopedStates(true)) {
    const attrs = stateObj?.attributes || {};
    if (attrs.door_id == null) continue;
    const door = byId.get(String(attrs.door_id));
    if (!door) continue;
    door.dpsInput = attrs.dps_input ?? door.dpsInput ?? null;
    door.drsInput = attrs.drs_input ?? door.drsInput ?? null;
  }

  return doors;
};

SpcFlexCCard.prototype._doorModeLabel = function (mode) {
  const value = Number(mode);
  if (value === 0) return this._t("state.normal");
  if (value === 1) return this._t("door.access_forbidden");
  if (value === 2) return this._t("door.free_access");
  return mode == null ? "—" : String(mode);
};

SpcFlexCCard.prototype._renderDoors = function () {
  const doors = this._getDoors();
  if (!doors.length) {
    return `
      <div class="empty-state">
        <ha-icon icon="mdi:door-closed-lock"></ha-icon>
        <div>${this._t("door.none")}</div>
      </div>
    `;
  }

  return `
    <div class="door-list">
      ${doors.map((door) => `
        <div class="door-card">
          <div class="door-header">
            <div>
              <div class="door-title">${this._escapeHtml(door.name)}</div>
              <div class="door-areas">${this._escapeHtml(this._doorAreasLabel(door))}</div>
            </div>
            <ha-icon class="door-icon" icon="mdi:door"></ha-icon>
          </div>
          <div class="door-state-grid door-supervision-grid">
            <div class="door-state-card">
              <div class="door-state-label">${this._t("door.status")}</div>
              <div class="door-state-value">${this._escapeHtml(door.status ?? "—")}</div>
            </div>
            <div class="door-state-card">
              <div class="door-state-label">${this._t("door.mode")}</div>
              <div class="door-state-value">${this._escapeHtml(this._doorModeLabel(door.mode))}</div>
            </div>
            <div class="door-state-card">
              <div class="door-state-label">${this._t("door.dps")}</div>
              <div class="door-state-value">${this._escapeHtml(door.dpsInput ?? "—")}</div>
            </div>
            <div class="door-state-card">
              <div class="door-state-label">${this._t("door.drs")}</div>
              <div class="door-state-value">${this._escapeHtml(door.drsInput ?? "—")}</div>
            </div>
          </div>
          ${door.zoneName ? `
            <div class="door-zone">
              <ha-icon icon="mdi:shield-home-outline"></ha-icon>
              <span>${this._t("zone.name", { id: door.zoneId ?? "" })}${door.zoneId != null ? " · " : ""}${this._escapeHtml(door.zoneName)}</span>
            </div>
          ` : ""}
          <div class="door-raw-note">
            ${this._t("door.supervision_note")}
          </div>
        </div>
      `).join("")}
    </div>
  `;
};

SpcFlexCCard.prototype._renderOutputs = function () {
  const outputs = this._getMappingGates();
  if (!outputs.length) {
    return `
      <div class="empty-state">
        <ha-icon icon="mdi:electric-switch"></ha-icon>
        <div>${this._t("output.none")}</div>
      </div>
    `;
  }

  return `
    <div class="outputs-view">
      <div class="group-title">${this._t("tab.outputs")} <span>${outputs.length}</span></div>
      <div class="output-list">
        ${outputs.map((output) => {
          const isOn = output.state === "on";
          const unavailable = ["unknown", "unavailable"].includes(output.state);
          const stateLabel = output.state === "unavailable"
            ? this._t("state.unavailable")
            : output.state === "unknown"
              ? this._t("state.unknown_short")
              : isOn
                ? this._t("state.on")
                : this._t("state.off");
          return `
            <div class="output-row">
              <div class="output-icon ${unavailable ? "muted" : isOn ? "ok" : "muted"}">
                <ha-icon icon="mdi:electric-switch"></ha-icon>
              </div>
              <div class="output-main">
                <div class="output-name">${this._escapeHtml(output.name)}</div>
                <div class="output-id">${this._t("output.mapping_gate")} ${this._escapeHtml(output.id ?? "—")}</div>
              </div>
              <div class="output-state ${unavailable ? "muted" : isOn ? "ok" : "muted"}">
                ${this._escapeHtml(stateLabel)}
              </div>
              ${this._config.show_controls === false ? "" : `
                <div class="output-controls">
                  <button type="button" class="output-button${isOn ? " active" : ""}"
                    data-mg-entity="${this._escapeHtml(output.entityId)}"
                    data-mg-name="${this._escapeHtml(output.name)}" data-mg-action="on">${this._t("state.on")}</button>
                  <button type="button" class="output-button${!isOn && !unavailable ? " active" : ""}"
                    data-mg-entity="${this._escapeHtml(output.entityId)}"
                    data-mg-name="${this._escapeHtml(output.name)}" data-mg-action="off">${this._t("state.off")}</button>
                </div>
              `}
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
};

SpcFlexCCard.prototype._renderTabs = function () {
  // A fixed view (the SPC app shows one view per place) has no tab row.
  if (this._config?.view) {
    this._activeTab = this._config.view;
    return "";
  }
  const hasDoors = this._getDoors().length > 0;
  const hasOutputs = this._getMappingGates().length > 0;
  if (this._activeTab === "doors" && !hasDoors) this._activeTab = "system";
  const scopePending = !this._panelEntityIds();
  if (this._activeTab === "outputs" && !hasOutputs && !scopePending) this._activeTab = "system";

  const tabs = [
    ["system", this._t("tab.general")],
    ...(hasDoors ? [["doors", this._t("tab.doors")]] : []),
    ["areas", this._t("tab.areas")],
    ["zones", this._t("tab.detectors")],
    ...(hasOutputs || (scopePending && this._activeTab === "outputs") ? [["outputs", this._t("tab.outputs")]] : []),
    ["technical", this._t("tab.system")],
  ];

  return `<div class="tabs">${tabs.map(([id, label]) => `
    <button type="button" class="tab ${this._activeTab === id ? "active" : ""}" data-tab="${id}">
      ${this._escapeHtml(label)}
    </button>
  `).join("")}</div>`;
};

SpcFlexCCard.prototype._renderActiveView = function () {
  switch (this._activeTab) {
    case "areas": return this._renderAreas();
    case "zones": return this._renderZones();
    case "doors": return this._getDoors().length ? this._renderDoors() : this._renderSystem();
    case "outputs": return !this._panelEntityIds()
      ? `<div class="empty-state"><ha-icon icon="mdi:progress-clock"></ha-icon><div>${this._t("zone.loading", {}, "Chargement des entités SPC…")}</div></div>`
      : this._renderOutputs();
    case "technical": return this._renderTechnicalSystem();
    case "system":
    default: return this._renderSystem();
  }
};

SpcFlexCCard.prototype._callZoneRestore = async function (entityId, name) {
  if (!this._hass || !entityId) return;
  if (!this._panelEntityIds()?.has(entityId)) {
    console.warn("SPC FlexC Card: blocked cross-panel action", entityId);
    return;
  }
  const prompt = this._t("confirm.restore_zone", { name });
  if (this._config.confirm_actions && !window.confirm(prompt)) return;
  await this._hass.callService("button", "press", { entity_id: entityId });
};

SpcFlexCCard.prototype._callMappingGate = async function (entityId, name, action) {
  if (!this._hass || !entityId || !["on", "off"].includes(action)) return;
  if (!this._panelEntityIds()?.has(entityId)) {
    console.warn("SPC FlexC Card: blocked cross-panel action", entityId);
    return;
  }
  const actionLabel = action === "on" ? this._t("action.activate") : this._t("action.deactivate");
  const prompt = this._t("confirm.mapping_gate", { action: actionLabel, name });
  if (this._config.confirm_actions && !window.confirm(prompt)) return;
  await this._hass.callService("switch", action === "on" ? "turn_on" : "turn_off", {
    entity_id: entityId,
  });
};

SpcFlexCCard.prototype._styles = function () {
  return `${spcFlexCBaseStyles.call(this)}
    <style>
      .zone-operating-badge {
        display:inline-flex;
        align-items:center;
        margin-left:7px;
        padding:1px 6px;
        border:1px solid currentColor;
        border-radius:999px;
        font-size:9px;
        font-weight:800;
        letter-spacing:.04em;
        line-height:1.5;
        vertical-align:1px;
      }
      .zone-row-inhibited {
        box-shadow:inset 3px 0 0 color-mix(in srgb,currentColor 55%,transparent);
      }
      .zone-row:has(> .zone-restore-button) {
        grid-template-columns:46px minmax(0,1fr) auto auto;
      }
      .zone-restore-button {
        min-width:max-content;
        white-space:nowrap;
        justify-self:end;
        appearance:none;
        padding:7px 10px;
        border:1px solid var(--warning-color,#ff9800);
        border-radius:8px;
        background:var(--card-background-color);
        color:var(--warning-color,#ff9800);
        cursor:pointer;
        font:inherit;
        font-size:12px;
        font-weight:700;
      }
      .outputs-view { display:grid; gap:12px; }
      .output-list { display:grid; gap:7px; }
      .output-row {
        display:grid;
        grid-template-columns:46px minmax(0,1fr) auto auto;
        align-items:center;
        gap:12px;
        min-height:58px;
        padding:8px 12px;
        border-radius:10px;
        background:var(--secondary-background-color,rgba(127,127,127,.08));
      }
      .output-icon { display:flex; align-items:center; justify-content:center; }
      .output-icon ha-icon { --mdc-icon-size:28px; }
      .output-main { min-width:0; }
      .output-name { overflow:hidden; font-weight:600; text-overflow:ellipsis; white-space:nowrap; }
      .output-id { margin-top:2px; color:var(--secondary-text-color); font-size:11px; }
      .output-state { min-width:34px; font-weight:700; text-align:right; }
      .output-controls { display:flex; gap:6px; }
      .output-button {
        appearance:none;
        min-width:48px;
        padding:7px 10px;
        border:1px solid var(--divider-color);
        border-radius:8px;
        background:var(--card-background-color);
        color:var(--primary-text-color);
        cursor:pointer;
        font:inherit;
        font-size:12px;
        font-weight:700;
      }
      .output-button.active { border-color:var(--primary-color); color:var(--primary-color); }
      .door-supervision-grid { grid-template-columns:repeat(4,minmax(0,1fr)); }
      @media (max-width:700px) {
        .output-row { grid-template-columns:40px minmax(0,1fr) auto; }
        .output-controls { grid-column:2 / -1; }
        .door-supervision-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
      }
    </style>`;
};

SpcFlexCCard.prototype._render = function () {
  spcFlexCBaseRender.call(this);
  this.querySelectorAll("[data-zone-restore-entity]").forEach((button) => {
    button.addEventListener("click", () => {
      this._callZoneRestore(
        button.dataset.zoneRestoreEntity,
        button.dataset.zoneRestoreName || this._t("zone.name", { id: "" })
      );
    });
  });
  this.querySelectorAll("[data-mg-entity]").forEach((button) => {
    button.addEventListener("click", () => {
      this._callMappingGate(
        button.dataset.mgEntity,
        button.dataset.mgName || this._t("output.fallback_name"),
        button.dataset.mgAction
      );
    });
  });
};

/* SPC FlexC Card zone isolation extension. */

const spcFlexCZoneIsolationBaseGetZones = SpcFlexCCard.prototype._getZones;
const spcFlexCZoneIsolationBaseRenderZoneRow = SpcFlexCCard.prototype._renderZoneRow;
const spcFlexCZoneIsolationBaseStyles = SpcFlexCCard.prototype._styles;
const spcFlexCZoneIsolationBaseRender = SpcFlexCCard.prototype._render;

SpcFlexCCard.prototype._getZones = function () {
  const zones = spcFlexCZoneIsolationBaseGetZones.call(this);
  if (!this._hass || !zones.length) return zones;

  const byId = new Map(zones.map((zone) => [String(zone.zoneId), zone]));
  const scoped = this._scopedStates(true);
  // Never scan all Home Assistant entities if the selected SPC scope is unavailable.
  const candidates = scoped;

  // spc-flexc-outputs predates the isolation switch and historically accepted
  // every switch carrying zone_id as an inhibition switch. Once isolation was
  // added, that allowed the two switch states to overwrite each other depending
  // on registry iteration order. Rebuild both operating states from their exact
  // integration unique IDs so inhibition and isolation remain independent.
  for (const zone of zones) {
    zone.inhibited = false;
    zone.inhibitionEntityId = null;
    zone.isolated = false;
    zone.isolationEntityId = null;
  }

  for (const { entityId, stateObj, registryEntry } of candidates) {
    if (!entityId.startsWith("switch.")) continue;

    const attrs = stateObj?.attributes || {};
    const uniqueId = String(registryEntry?.unique_id || "");
    const inhibitionMatch = uniqueId.match(/_zone_(\d+)_inhibition$/);
    const isolationMatch = uniqueId.match(/_zone_(\d+)_isolation$/);

    if (!inhibitionMatch && !isolationMatch) continue;

    const zoneId = attrs.zone_id ?? inhibitionMatch?.[1] ?? isolationMatch?.[1];
    const zone = byId.get(String(zoneId));
    if (!zone) continue;

    if (inhibitionMatch) {
      zone.inhibited = stateObj.state === "on";
      zone.inhibitionEntityId = entityId;
    }

    if (isolationMatch) {
      zone.isolated = stateObj.state === "on";
      zone.isolationEntityId = entityId;
    }
  }

  return zones;
};

SpcFlexCCard.prototype._zoneIsIsolated = function (zone) {
  return zone?.isolated === true;
};

SpcFlexCCard.prototype._renderZoneRow = function (zone) {
  if (!this._zoneIsIsolated(zone)) {
    return spcFlexCZoneIsolationBaseRenderZoneRow.call(this, zone);
  }

  return `
    <div class="zone-row zone-row-isolated">
      <div class="zone-icon danger">
        <ha-icon icon="${this._escapeHtml(this._zoneIcon(zone))}"></ha-icon>
      </div>

      <div class="zone-main">
        <div class="zone-name">${this._escapeHtml(zone.name)}</div>
        <div class="zone-area">
          ${this._escapeHtml(this._areaName(zone.areaId))}
          <span class="zone-operating-badge zone-isolated">${this._t("state.isolated")}</span>
        </div>
      </div>

      <div class="zone-state danger">
        ${this._escapeHtml(this._t("state.isolated"))}
      </div>
    </div>
  `;
};

SpcFlexCCard.prototype._zoneOperatingCounts = function (zones) {
  const normalZones = zones.filter(
    (zone) => zone.zoneType !== "tamper" && zone.deviceClass !== "tamper"
  );
  const isolated = normalZones.filter((zone) => this._zoneIsIsolated(zone)).length;
  const inhibited = normalZones.filter(
    (zone) => zone.inhibited === true && !this._zoneIsIsolated(zone)
  ).length;
  const active = normalZones.filter(
    (zone) => zone.state === "on" && !this._zoneIsIsolated(zone)
  ).length;

  return { normalZones, isolated, inhibited, active };
};

SpcFlexCCard.prototype._renderZoneOperatingBadges = function (counts) {
  return [
    counts.isolated
      ? `<span class="danger">${counts.isolated} ${this._t("state.isolated")}</span>`
      : "",
    counts.inhibited
      ? `<span class="zone-inhibited">${this._tCount("group.inhibited_count", counts.inhibited)}</span>`
      : "",
  ].join("");
};

SpcFlexCCard.prototype._updateZoneOperatingSummaries = function () {
  const zones = this._getZones();
  if (!zones.length) return;

  const globalCounts = this._zoneOperatingCounts(zones);
  const globalBadges = this._renderZoneOperatingBadges(globalCounts);

  // General view: keep detector activity visible for inhibited zones, suppress
  // isolated-zone activity, and surface both operating states explicitly.
  const systemSummary = this.querySelector(".system-view .system-summary");
  if (systemSummary && globalBadges) {
    systemSummary.insertAdjacentHTML(
      "beforeend",
      `<span class="zone-operating-summary"> · ${globalBadges}</span>`
    );
  }

  const detectorCard = this.querySelectorAll(".system-view .summary-card")[1];
  const detectorLabel = detectorCard?.querySelector(".summary-label");
  if (detectorLabel) {
    detectorLabel.innerHTML = `
      ${this._t("tab.detectors")}
      ${globalCounts.active ? `<span class="warning"> · ${this._tCount("group.active_count", globalCounts.active)}</span>` : ""}
      ${globalCounts.inhibited ? `<span class="zone-inhibited"> · ${this._tCount("group.inhibited_count", globalCounts.inhibited)}</span>` : ""}
      ${globalCounts.isolated ? `<span class="danger"> · ${globalCounts.isolated} ${this._t("state.isolated")}</span>` : ""}
    `;
  }

  // Areas view: operating states are informational only. They never hide or
  // disable the area's alarm controls; the SPC panel remains authoritative.
  this.querySelectorAll(".area-card").forEach((card) => {
    const areaId = card.querySelector("[data-area-id]")?.dataset.areaId;
    if (areaId == null) return;

    const areaZones = zones.filter(
      (zone) => String(zone.areaId) === String(areaId)
    );
    const counts = this._zoneOperatingCounts(areaZones);
    const badges = this._renderZoneOperatingBadges(counts);

    const headerState = card.querySelector(".area-card-toggle-state");
    if (headerState && badges) {
      headerState.insertAdjacentHTML(
        "afterbegin",
        `<span class="area-zone-operating-summary">${badges}</span>`
      );
    }

    const meta = card.querySelector(".area-meta");
    if (meta) {
      const tampers = areaZones.filter(
        (zone) => zone.zoneType === "tamper" || zone.deviceClass === "tamper"
      );
      const activeTampers = tampers.filter(
        (zone) =>
          !this._zoneIsIsolated(zone) &&
          (zone.state === "on" || zone.eventTamper === true)
      ).length;

      meta.innerHTML = `
        <span>${this._tCount("group.detector_count", counts.normalZones.length)}</span>
        ${counts.active ? `<span class="warning">${this._tCount("group.active_count", counts.active)}</span>` : ""}
        ${counts.inhibited ? `<span class="zone-inhibited">${this._tCount("group.inhibited_count", counts.inhibited)}</span>` : ""}
        ${counts.isolated ? `<span class="danger">${counts.isolated} ${this._t("state.isolated")}</span>` : ""}
        ${!counts.active && !counts.inhibited && !counts.isolated ? `<span class="ok">${this._t("group.rest")}</span>` : ""}
        ${activeTampers ? `<span class="danger">${this._t("area.tamper")}</span>` : ""}
      `;
    }
  });
};

SpcFlexCCard.prototype._styles = function () {
  return `${spcFlexCZoneIsolationBaseStyles.call(this)}
    <style>
      .zone-row-isolated {
        box-shadow:inset 3px 0 0 var(--error-color,#db4437);
        background:color-mix(in srgb,var(--error-color,#db4437) 9%,transparent);
      }
      .zone-row-isolated .zone-name,
      .zone-row-isolated .zone-area,
      .zone-isolated {
        color:var(--error-color,#db4437);
      }
      .zone-operating-summary,
      .area-zone-operating-summary {
        display:inline-flex;
        align-items:center;
        gap:6px;
      }
      .area-zone-operating-summary {
        flex-wrap:wrap;
        justify-content:flex-end;
        font-size:12px;
        font-weight:700;
      }
    </style>`;
};

SpcFlexCCard.prototype._render = function () {
  spcFlexCZoneIsolationBaseRender.call(this);
  this._updateZoneOperatingSummaries();
};

/* SPC FlexC Card v1.0.5 zone grouping extension. */

const spcFlexCZoneGroupsBaseStyles = SpcFlexCCard.prototype._styles;
const spcFlexCZoneGroupsBaseRender = SpcFlexCCard.prototype._render;

SpcFlexCCard.prototype._zoneGroupsStorageKey = function () {
  const entity = this._config?.entity;
  return entity ? `spc-flexc-card:${entity}:zone-groups` : null;
};

SpcFlexCCard.prototype._loadZoneGroupStates = function () {
  if (this._spcZoneGroupStates) return this._spcZoneGroupStates;

  this._spcZoneGroupStates = {};
  const key = this._zoneGroupsStorageKey();
  if (!key) return this._spcZoneGroupStates;

  try {
    const raw = window.localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        this._spcZoneGroupStates = parsed;
      }
    }
  } catch {
    // Keep in-memory state when persistent browser storage is unavailable.
  }

  return this._spcZoneGroupStates;
};

SpcFlexCCard.prototype._saveZoneGroupStates = function () {
  const key = this._zoneGroupsStorageKey();
  if (!key) return;

  try {
    window.localStorage.setItem(
      key,
      JSON.stringify(this._spcZoneGroupStates || {})
    );
  } catch {
    // Home Assistant can still keep the state until the card is recreated.
  }
};

SpcFlexCCard.prototype._zoneGroupExpanded = function (areaId) {
  const states = this._loadZoneGroupStates();
  const key = String(areaId);

  if (Object.prototype.hasOwnProperty.call(states, key)) {
    return states[key] === true;
  }

  // Start every group collapsed until the user explicitly opens it.
  return false;
};

SpcFlexCCard.prototype._setZoneGroupExpanded = function (areaId, expanded) {
  const states = this._loadZoneGroupStates();
  states[String(areaId)] = Boolean(expanded);
  this._saveZoneGroupStates();
};

SpcFlexCCard.prototype._zoneIsInhibited = function (zone) {
  return zone?.inhibited === true;
};

SpcFlexCCard.prototype._getZoneGroups = function () {
  const zones = this._getZones();
  const areas = this._getAreas();
  const groups = new Map();

  for (const area of areas) {
    groups.set(String(area.id), {
      id: String(area.id),
      name: area.name,
      numericId: area.numericId,
      zones: [],
    });
  }

  for (const zone of zones) {
    const key = String(zone.areaId);
    if (!groups.has(key)) {
      groups.set(key, {
        id: key,
        name: this._areaName(zone.areaId),
        numericId: Number(zone.areaId),
        zones: [],
      });
    }
    groups.get(key).zones.push(zone);
  }

  return Array.from(groups.values())
    .filter((group) => group.zones.length > 0)
    .sort((a, b) => {
      if (Number.isFinite(a.numericId) && Number.isFinite(b.numericId)) {
        return a.numericId - b.numericId;
      }
      return a.name.localeCompare(b.name);
    });
};

SpcFlexCCard.prototype._renderZones = function () {
  const groups = this._getZoneGroups();
  const totalZones = groups.reduce((count, group) => count + group.zones.length, 0);

  if (!totalZones) {
    return `
      <div class="empty-state">
        <ha-icon icon="mdi:motion-sensor-off"></ha-icon>
        <div>${this._t("zone.none")}</div>
      </div>
    `;
  }

  const allExpanded = groups.every((group) =>
    this._zoneGroupExpanded(group.id)
  );

  return `
    <div class="zones-view grouped-zones-view">
      <div class="zone-groups-toolbar">
        <div class="group-title">
          ${this._t("group.detectors")}
          <span>${totalZones}</span>
        </div>
        <button
          type="button"
          class="zone-groups-toggle-all"
          data-zone-groups-action="${allExpanded ? "collapse" : "expand"}"
        >
          ${this._t(allExpanded ? "group.collapse_all" : "group.expand_all")}
        </button>
      </div>

      <div class="zone-groups-list">
        ${groups.map((group) => {
          const expanded = this._zoneGroupExpanded(group.id);
          const normalZones = group.zones.filter(
            (zone) => zone.zoneType !== "tamper" && zone.deviceClass !== "tamper"
          );
          const tampers = group.zones.filter(
            (zone) => zone.zoneType === "tamper" || zone.deviceClass === "tamper"
          );
          const isolatedZones = group.zones.filter((zone) =>
            this._zoneIsIsolated?.(zone) === true
          ).length;
          const inhibitedZones = group.zones.filter((zone) =>
            this._zoneIsInhibited(zone) && this._zoneIsIsolated?.(zone) !== true
          ).length;
          // Inhibition does not suppress the detector's physical activity in
          // the UI. Isolation does: an isolated zone is outside normal
          // supervision and its activity is intentionally not summarized.
          const activeZones = normalZones.filter(
            (zone) =>
              zone.state === "on" &&
              this._zoneIsIsolated?.(zone) !== true
          ).length;
          const activeTampers = tampers.filter(
            (zone) =>
              this._zoneIsIsolated?.(zone) !== true &&
              (zone.state === "on" || zone.eventTamper === true)
          ).length;
          const zoneTamperAlerts = group.zones.filter((zone) => zone.eventTamper === true).length;
          const zoneTroubleAlerts = group.zones.filter((zone) => zone.eventTrouble === true).length;
          const unavailable = group.zones.filter(
            (zone) => ["unknown", "unavailable"].includes(zone.state)
          ).length;

          return `
            <section class="zone-group${expanded ? " expanded" : " collapsed"}">
              <button
                type="button"
                class="zone-group-header"
                data-zone-group-id="${this._escapeHtml(group.id)}"
                aria-expanded="${expanded ? "true" : "false"}"
              >
                <ha-icon
                  class="zone-group-chevron"
                  icon="${expanded ? "mdi:chevron-down" : "mdi:chevron-right"}"
                ></ha-icon>

                <div class="zone-group-title-wrap">
                  <div class="zone-group-title">${this._escapeHtml(group.name)}</div>
                  <div class="zone-group-meta">
                    ${this._tCount("group.detector_count", normalZones.length)}
                    ${tampers.length ? ` · ${this._tCount("group.tamper_count", tampers.length)}` : ""}
                  </div>
                </div>

                <div class="zone-group-summary">
                  ${zoneTamperAlerts ? `<span class="zone-tamper-alert">${zoneTamperAlerts} ${this._t("zone.alert_tamper")}</span>` : ""}
                  ${zoneTroubleAlerts ? `<span class="zone-trouble-alert">${zoneTroubleAlerts} ${this._t("zone.alert_trouble")}</span>` : ""}
                  ${isolatedZones ? `<span class="danger">${isolatedZones} ${this._t("state.isolated")}</span>` : ""}
                  ${inhibitedZones ? `<span class="zone-inhibited">${this._tCount("group.inhibited_count", inhibitedZones)}</span>` : ""}
                  ${activeZones ? `<span class="warning">${this._tCount("group.active_count", activeZones)}</span>` : ""}
                  ${activeTampers ? `<span class="danger">${this._tCount("group.fault_count", activeTampers)}</span>` : ""}
                  ${unavailable ? `<span class="muted">${this._tCount("group.unavailable_count", unavailable)}</span>` : ""}
                  ${!isolatedZones && !inhibitedZones && !activeZones && !activeTampers && !zoneTamperAlerts && !zoneTroubleAlerts && !unavailable ? `<span class="ok">${this._t("group.rest")}</span>` : ""}
                </div>
              </button>

              ${expanded ? `
                <div class="zone-group-content">
                  ${normalZones.length ? `
                    <div class="zone-list">
                      ${normalZones.map((zone) => this._renderZoneRow(zone)).join("")}
                    </div>
                  ` : ""}

                  ${tampers.length ? `
                    <div class="group-title tamper-title">
                      ${this._t("group.tampers")}
                      <span>${tampers.length}</span>
                    </div>
                    <div class="zone-list tamper-list">
                      ${tampers.map((zone) => this._renderZoneRow(zone)).join("")}
                    </div>
                  ` : ""}
                </div>
              ` : ""}
            </section>
          `;
        }).join("")}
      </div>
    </div>
  `;
};

SpcFlexCCard.prototype._styles = function () {
  return `${spcFlexCZoneGroupsBaseStyles.call(this)}
    <style>
      .zone-inhibited { color:var(--spc-flexc-inhibited-color,#f6b73c); }
      .zone-groups-toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; }
      .zone-groups-toggle-all, .zone-group-header { appearance:none; border:0; font:inherit; color:inherit; cursor:pointer; }
      .zone-groups-toggle-all { padding:6px 9px; border-radius:8px; background:var(--secondary-background-color,rgba(127,127,127,.08)); color:var(--primary-color); font-size:12px; font-weight:700; }
      .zone-groups-list { display:grid; gap:10px; }
      .zone-group { overflow:hidden; border:1px solid var(--divider-color); border-radius:12px; }
      .zone-group-header { display:grid; grid-template-columns:28px minmax(0,1fr) auto; align-items:center; gap:10px; width:100%; padding:12px; background:var(--secondary-background-color,rgba(127,127,127,.06)); text-align:left; }
      .zone-group-header:hover { background:var(--secondary-background-color,rgba(127,127,127,.1)); }
      .zone-group-chevron { --mdc-icon-size:22px; color:var(--secondary-text-color); }
      .zone-group-title-wrap { min-width:0; }
      .zone-group-title { overflow:hidden; font-size:15px; font-weight:700; text-overflow:ellipsis; white-space:nowrap; }
      .zone-group-meta { margin-top:2px; color:var(--secondary-text-color); font-size:11px; }
      .zone-group-summary { display:flex; justify-content:flex-end; flex-wrap:wrap; gap:4px 9px; font-size:12px; font-weight:700; text-align:right; }
      .zone-group-content { display:grid; gap:8px; padding:9px; }
      .zone-tamper-alert { color:#fb923c; font-weight:600; }
      .zone-trouble-alert { color:#c4b5fd; font-weight:600; }
      .zone-tamper-alert ha-icon, .zone-trouble-alert ha-icon { --mdc-icon-size:16px; vertical-align:middle; }
      .zone-group-content .tamper-title { margin:8px 3px 0; }
      @media (max-width:520px) {
        .zone-group-header { grid-template-columns:24px minmax(0,1fr); }
        .zone-group-summary { grid-column:2; justify-content:flex-start; text-align:left; }
        .zone-groups-toolbar { align-items:flex-start; }
      }
    </style>`;
};

SpcFlexCCard.prototype._render = function () {
  spcFlexCZoneGroupsBaseRender.call(this);

  this.querySelectorAll("[data-zone-group-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const areaId = button.dataset.zoneGroupId;
      const expanded = button.getAttribute("aria-expanded") === "true";
      this._setZoneGroupExpanded(areaId, !expanded);
      this._render();
    });
  });

  this.querySelectorAll("[data-zone-groups-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const expand = button.dataset.zoneGroupsAction === "expand";
      const groups = this._getZoneGroups();
      for (const group of groups) this._setZoneGroupExpanded(group.id, expand);
      this._render();
    });
  });
};

/* SPC FlexC Card v1.0.5 translations. */

const SPC_FLEXC_CARD_TRANSLATIONS = {
  fr: {
    "area.all": "Tous les secteurs",
    "area.name_full": "Secteur {id} : {name}",
    "action.clear_alerts": "Acquitter (effacer les alarmes)",
    "confirm.clear_alerts": "Acquitter et effacer toutes les alarmes de la centrale ?",
    "system.pir_diagnostics": "Diagnostic PIR",
    "system.pir_slow_reads": "lectures lentes (1 h)",
    "system.pir_maximum": "Durée maximale",
    "system.pir_empty": "Aucune lecture PIR lente sur la dernière heure",
    "system.pir_disabled": "Diagnostic PIR désactivé",
    "system.pir_unavailable": "Diagnostic PIR indisponible",
    "system.pir_unavailable_hint": "Le capteur de diagnostic PIR est actuellement indisponible.",
    "system.pir_enable_hint": "Activez l’entité « PIR slow reads (1h) » dans Paramètres → Appareils et services → SPC FlexC → Entités.",
    "card.description": "Carte de contrôle visuelle pour l’intégration Home Assistant SPC FlexC.",
    "card.entity_not_found": "Entité introuvable : {entity}",
    "tab.general": "Général",
    "tab.areas": "Secteurs",
    "tab.detectors": "Détecteurs",
    "tab.doors": "Portes",
    "tab.outputs": "Sorties",
    "tab.system": "Système",
    "state.disarmed": "Désarmée",
    "state.disarmed_masc": "Désarmé",
    "state.armed": "Armée",
    "state.armed_masc": "Armé",
    "state.part_a": "Partiel A",
    "state.part_b": "Partiel B",
    "state.partial": "Partiel",
    "state.alarm": "ALARME",
    "state.arming": "Armement…",
    "state.disarming": "Désarmement…",
    "state.pending": "Temporisation",
    "state.unavailable": "Indisponible",
    "state.unknown": "État inconnu",
    "state.mixed": "Armement mixte",
    "state.unknown_short": "Inconnu",
    "state.normal": "Normal",
    "state.on": "Activé",
    "state.off": "Désactivé",
    "state.connected": "Connectée",
    "state.disconnected": "Déconnectée",
    "state.ok": "OK",
    "state.inactive": "Inactif",
    "state.fault": "Défaut",
    "state.inhibited": "Inhibé",
    "state.not_inhibited": "Non inhibé",
    "state.isolated": "Isolé",
    "state.not_isolated": "Non isolé",
    "zone.alert_tamper": "Sabotage",
    "zone.alert_trouble": "Défaut",
    "system.event_history": "Historique des événements FlexC",
    "system.event_count_one": "événement",
    "system.event_count_many": "événements",
    "system.area": "Secteur",
    "system.zone": "Zone",
    "system.event_enable_hint": "Pour afficher l’historique, activez l’entité de diagnostic « Last FlexC event ID » dans Paramètres → Appareils et services → Entités, puis rechargez l’intégration si nécessaire.",
    "system.wireless_events": "Événements Wireless",
    "system.event_observation": "Événements observés uniquement — pas des états d’alarme permanents.",
    "system.no_recent_events": "Aucun événement récent",
    "system.event_unknown": "Événement non documenté",
    "zone.motion": "Mouvement",
    "zone.rest": "Repos",
    "zone.open": "Ouvert",
    "zone.closed": "Fermé",
    "zone.smoke": "Fumée détectée",
    "zone.heat": "Chaleur détectée",
    "zone.active": "Actif",
    "zone.tamper": "AUTOPROTECTION",
    "zone.inhibited": "Inhibé",
    "zone.none": "Aucune zone SPC découverte.",
    "zone.loading": "Chargement des entités SPC…",
    "zone.name": "Zone {id}",
    "area.none": "Aucun secteur SPC disponible.",
    "area.name": "Secteur {id}",
    "area.last_set": "Dernier armement",
    "area.last_unset": "Dernier désarmement",
    "area.tamper": "Autoprotection",
    "door.none": "Aucune porte SPC découverte.",
    "door.name": "Porte {id}",
    "door.fallback_name": "Porte SPC",
    "door.status": "État",
    "door.mode": "Mode",
    "door.dps": "DPS",
    "door.drs": "DRS",
    "door.access_forbidden": "Accès interdit",
    "door.free_access": "Accès libre",
    "door.unknown_area": "Association secteur inconnue",
    "door.supervision_note": "Supervision FlexC uniquement. Les commandes de mode de porte ne sont pas présentées comme une commande physique de serrure.",
    "door.raw_note": "État et Mode sont affichés tels que fournis par SPC tant que leur signification n’est pas validée sur matériel réel.",
    "output.none": "Aucune sortie SPC (Mapping Gate) découverte.",
    "output.name": "Sortie {id}",
    "output.fallback_name": "Sortie SPC",
    "output.mapping_gate": "Mapping Gate",
    "group.detectors": "Détecteurs",
    "group.tampers": "Autoprotections",
    "group.expand_all": "Tout développer",
    "group.collapse_all": "Tout réduire",
    "group.rest": "Au repos",
    "group.detector_count.one": "{count} détecteur",
    "group.detector_count.other": "{count} détecteurs",
    "group.area_count.one": "{count} secteur",
    "group.area_count.other": "{count} secteurs",
    "group.tamper_count.one": "{count} autoprotection",
    "group.tamper_count.other": "{count} autoprotections",
    "group.active_count.one": "{count} Actif",
    "group.active_count.other": "{count} Actifs",
    "group.inhibited_count.one": "{count} Inhibé",
    "group.inhibited_count.other": "{count} Inhibés",
    "group.fault_count.one": "{count} défaut",
    "group.fault_count.other": "{count} défauts",
    "group.unavailable_count.one": "{count} indisponible",
    "group.unavailable_count.other": "{count} indisponibles",
    "group.in_fault": "{count} en défaut",
    "group.no_area": "Aucun secteur",
    "group.no_detector": "Aucun détecteur",
    "system.health": "État et défauts",
    "system.connection": "Connexion FlexC",
    "system.state_unknown": "État non déterminé",
    "system.entity_missing": "Entité non exposée",
    "system.engineer_active": "Mode ingénieur actif",
    "system.engineer_detail": "L’état est remonté en temps réel par la centrale.",
    "system.active_faults": "Défauts actifs",
    "system.no_fault": "Aucun défaut actif",
    "system.faults_unknown": "Défauts système non déterminés : métadonnées indisponibles.",
    "system.card": "Carte SPC FlexC",
    "system.panel": "Centrale",
    "system.manufacturer": "Fabricant",
    "system.model": "Modèle",
    "system.firmware": "Firmware",
    "system.hardware": "Matériel",
    "system.serial": "N° de série",
    "system.power": "Alimentation",
    "system.ac_frequency": "Fréquence secteur",
    "system.battery_voltage": "Tension batterie",
    "system.aux_voltage": "Tension auxiliaire",
    "system.aux_current": "Courant auxiliaire",
    "system.communication": "Communication FlexC",
    "system.state": "État",
    "system.ats_used": "ATS utilisé",
    "system.last_tx": "Dernière transmission réussie",
    "system.xbus": "X-BUS",
    "system.xbus_id": "ID X-BUS",
    "system.sia_address": "Adresse SIA",
    "system.tamper": "Autoprotection",
    "system.tamper_isolation": "Isolement autoprotection",
    "system.rf": "RF",
    "system.modem": "Modem",
    "action.disarm": "Désarmer",
    "action.full_arm": "Armement total",
    "action.arm": "Armer",
    "action.activate": "Activer",
    "action.deactivate": "Désactiver",
    "action.execute": "Exécuter la commande",
    "action.door_momentary": "Ouverture momentanée",
    "action.door_permanent": "Ouverture permanente",
    "action.door_normal": "Retour au mode normal",
    "action.door_lock": "Verrouiller",
    "action.restore": "Restaurer",
    "confirm.restore_zone": "Restaurer la zone {name} ?",
    "confirm.generic": "Exécuter l'action sur {name} ?",
    "confirm.disarm": "Désarmer {name} ?",
    "confirm.full_arm": "Armer complètement {name} ?",
    "confirm.part_set": "Activer {action} sur {name} ?",
    "confirm.mapping_gate": "{action} — {name} ?",
    "confirm.door": "{action} — {name} ?",
    "editor.entity": "Entité d'alarme",
    "editor.select_entity": "Sélectionner une entité",
    "editor.name": "Nom de la carte",
    "editor.show_controls": "Afficher les commandes d'alarme",
    "editor.confirm_actions": "Confirmer les actions d'armement/désarmement",
    "editor.help": "Les secteurs sont récupérés depuis l'entité d'alarme. Les détecteurs SPC sont découverts automatiquement parmi les binary_sensor possédant les attributs zone_id, area_id et spc_zone_type. Les diagnostics et informations techniques sont rattachés à la même intégration via les registres Home Assistant quand ceux-ci sont disponibles.",
  },
  sv: {
    "area.all": "Alla områden",
    "area.name_full": "Område {id}: {name}",
    "action.clear_alerts": "Kvittera (återställ alla larm)",
    "confirm.clear_alerts": "Kvittera och återställ alla larm på centralen?",
    "system.pir_diagnostics": "PIR-diagnostik",
    "system.pir_slow_reads": "långsamma läsningar (1 h)",
    "system.pir_maximum": "Längsta tid",
    "system.pir_empty": "Inga långsamma PIR-läsningar senaste timmen",
    "system.pir_disabled": "PIR-diagnostik avstängd",
    "system.pir_unavailable": "PIR-diagnostik inte tillgänglig",
    "system.pir_unavailable_hint": "PIR-diagnostiksensorn är inte tillgänglig just nu.",
    "system.pir_enable_hint": "Slå på entiteten « PIR slow reads (1h) » under Inställningar → Enheter och tjänster → SPC FlexC → Entiteter.",
    "card.description": "Larmkort för SPC FlexC-integrationen i Home Assistant.",
    "card.entity_not_found": "Entiteten finns inte: {entity}",
    "tab.general": "Översikt",
    "tab.areas": "Områden",
    "tab.detectors": "Sektioner",
    "tab.doors": "Dörrar",
    "tab.outputs": "Utgångar",
    "tab.system": "System",
    "state.disarmed": "Frånkopplad",
    "state.disarmed_masc": "Frånkopplad",
    "state.armed": "Tillkopplad",
    "state.armed_masc": "Tillkopplad",
    "state.part_a": "Deltillkoppling A",
    "state.part_b": "Deltillkoppling B",
    "state.partial": "Delvis till",
    "state.alarm": "LARM",
    "state.arming": "Tillkopplar…",
    "state.disarming": "Frånkopplar…",
    "state.pending": "Väntar",
    "state.unavailable": "Inte tillgänglig",
    "state.unknown": "Okänt läge",
    "state.mixed": "Delvis till",
    "state.unknown_short": "Okänd",
    "state.normal": "Normal",
    "state.on": "På",
    "state.off": "Av",
    "state.connected": "Ansluten",
    "state.disconnected": "Frånkopplad",
    "state.ok": "OK",
    "state.inactive": "Inaktiv",
    "state.fault": "Fel",
    "state.inhibited": "Spärrad",
    "state.not_inhibited": "Inte spärrad",
    "state.isolated": "Isolerad",
    "state.not_isolated": "Inte isolerad",
    "zone.alert_tamper": "Sabotage",
    "zone.alert_trouble": "Fel",
    "system.event_history": "FlexC-händelser",
    "system.event_count_one": "händelse",
    "system.event_count_many": "händelser",
    "system.area": "Område",
    "system.zone": "Sektion",
    "system.event_enable_hint": "Slå på diagnostikentiteten ”Senaste FlexC-händelse-id” under Inställningar → Enheter och tjänster → Entiteter för att visa händelser, och ladda om integrationen vid behov.",
    "system.wireless_events": "Trådlösa händelser",
    "system.event_observation": "Bara observerade händelser – inte bestående larmlägen.",
    "system.no_recent_events": "Inga händelser nyligen",
    "system.event_unknown": "Odokumenterad händelse",
    "zone.motion": "Rörelse",
    "zone.rest": "Vila",
    "zone.open": "Öppen",
    "zone.closed": "Stängd",
    "zone.smoke": "Rök",
    "zone.heat": "Värme",
    "zone.active": "Aktiv",
    "zone.tamper": "SABOTAGE",
    "zone.inhibited": "Spärrad",
    "zone.none": "Ingen SPC-sektion hittad.",
    "zone.loading": "Läser in SPC-entiteter…",
    "zone.name": "Sektion {id}",
    "area.none": "Inget SPC-område tillgängligt.",
    "area.name": "Område {id}",
    "area.last_set": "Senast tillkopplad",
    "area.last_unset": "Senast frånkopplad",
    "area.tamper": "Sabotage",
    "door.none": "Ingen SPC-dörr hittad.",
    "door.name": "Dörr {id}",
    "door.fallback_name": "SPC-dörr",
    "door.status": "Status",
    "door.mode": "Läge",
    "door.dps": "DPS Dörrkontakt",
    "door.drs": "DRS Öppnaknapp",
    "door.access_forbidden": "Passage nekad",
    "door.free_access": "Fri passage",
    "door.unknown_area": "Okänt område",
    "door.supervision_note": "Övervakning via FlexC. Dörrlägen visas inte som fysiska låskommandon.",
    "door.raw_note": "Status och läge visas som centralen rapporterar dem.",
    "output.none": "Ingen SPC-utgång (Mapping gate) hittad.",
    "output.name": "Utgång {id}",
    "output.fallback_name": "SPC-utgång",
    "output.mapping_gate": "Mapping gate",
    "group.detectors": "Sektioner",
    "group.tampers": "Sabotage",
    "group.expand_all": "Fäll ut alla",
    "group.collapse_all": "Fäll ihop alla",
    "group.rest": "Vila",
    "group.detector_count.one": "{count} sektion",
    "group.detector_count.other": "{count} sektioner",
    "group.area_count.one": "{count} område",
    "group.area_count.other": "{count} områden",
    "group.tamper_count.one": "{count} sabotage",
    "group.tamper_count.other": "{count} sabotage",
    "group.active_count.one": "{count} aktiv",
    "group.active_count.other": "{count} aktiva",
    "group.inhibited_count.one": "{count} spärrad",
    "group.inhibited_count.other": "{count} spärrade",
    "group.fault_count.one": "{count} fel",
    "group.fault_count.other": "{count} fel",
    "group.unavailable_count.one": "{count} inte tillgänglig",
    "group.unavailable_count.other": "{count} inte tillgängliga",
    "group.in_fault": "{count} med fel",
    "group.no_area": "Inget område",
    "group.no_detector": "Ingen sektion",
    "system.health": "Läge och fel",
    "system.connection": "FlexC-anslutning",
    "system.state_unknown": "Läget inte tillgängligt",
    "system.entity_missing": "Entiteten finns inte",
    "system.engineer_active": "Installatörsläge aktivt",
    "system.engineer_detail": "Läget rapporteras direkt av centralen.",
    "system.active_faults": "Aktiva fel",
    "system.no_fault": "Inga aktiva fel",
    "system.faults_unknown": "Systemfel inte tillgängliga.",
    "system.card": "SPC FlexC-kort",
    "system.panel": "Central",
    "system.manufacturer": "Tillverkare",
    "system.model": "Modell",
    "system.firmware": "Firmware",
    "system.hardware": "Hårdvara",
    "system.serial": "Serienummer",
    "system.power": "Ström",
    "system.ac_frequency": "230VAC tidssynk",
    "system.battery_voltage": "Batterispänning",
    "system.aux_voltage": "AUX-utgång, spänning",
    "system.aux_current": "AUX-utgång, ström",
    "system.communication": "FlexC-kommunikation",
    "system.state": "Läge",
    "system.ats_used": "ATS som används",
    "system.last_tx": "Senast lyckade sändning",
    "system.xbus": "X-BUS",
    "system.xbus_id": "X-BUS-id",
    "system.sia_address": "SIA-adress",
    "system.tamper": "Sabotage",
    "system.tamper_isolation": "Sabotage isolerad",
    "system.rf": "Trådlöst",
    "system.modem": "Modem",
    "action.disarm": "Frånkoppla",
    "action.full_arm": "Tillkoppla",
    "action.arm": "Tillkoppla",
    "action.activate": "Aktivera",
    "action.deactivate": "Avaktivera",
    "action.execute": "Kör",
    "action.door_momentary": "Momentan",
    "action.door_permanent": "Lås upp",
    "action.door_normal": "Normal",
    "action.door_lock": "Blockera",
    "action.restore": "Återställ",
    "confirm.restore_zone": "Återställ sektion {name}?",
    "confirm.generic": "Utför åtgärden på {name}?",
    "confirm.disarm": "Frånkoppla {name}?",
    "confirm.full_arm": "Tillkoppla {name}?",
    "confirm.part_set": "Aktivera {action} på {name}?",
    "confirm.mapping_gate": "{action} – {name}?",
    "confirm.door": "{action} – {name}?",
    "editor.entity": "Larmentitet",
    "editor.select_entity": "Välj en entitet",
    "editor.name": "Kortets namn",
    "editor.show_controls": "Visa larmknappar",
    "editor.confirm_actions": "Bekräfta till- och frånkoppling",
    "editor.help": "Områden läses från larmentiteten. SPC-sektioner hittas automatiskt bland binary_sensor-entiteter med zone_id, area_id och spc_zone_type.",
  },
  en: {
    "area.all": "All areas",
    "area.name_full": "Area {id}: {name}",
    "action.clear_alerts": "Acknowledge (clear all alerts)",
    "confirm.clear_alerts": "Acknowledge and clear all alerts on the panel?",
    "system.pir_diagnostics": "PIR diagnostics",
    "system.pir_slow_reads": "slow reads (1 h)",
    "system.pir_maximum": "Maximum duration",
    "system.pir_empty": "No slow PIR reads in the last hour",
    "system.pir_disabled": "PIR diagnostics disabled",
    "system.pir_unavailable": "PIR diagnostics unavailable",
    "system.pir_unavailable_hint": "The PIR diagnostic sensor is currently unavailable.",
    "system.pir_enable_hint": "Enable the « PIR slow reads (1h) » entity in Settings → Devices & services → SPC FlexC → Entities.",
    "card.description": "Visual alarm control card for the SPC FlexC Home Assistant integration.",
    "card.entity_not_found": "Entity not found: {entity}",
    "tab.general": "General",
    "tab.areas": "Areas",
    "tab.detectors": "Detectors",
    "tab.doors": "Doors",
    "tab.outputs": "Outputs",
    "tab.system": "System",
    "state.disarmed": "Disarmed",
    "state.disarmed_masc": "Disarmed",
    "state.armed": "Armed",
    "state.armed_masc": "Armed",
    "state.part_a": "Part Set A",
    "state.part_b": "Part Set B",
    "state.partial": "Part set",
    "state.alarm": "ALARM",
    "state.arming": "Arming…",
    "state.disarming": "Disarming…",
    "state.pending": "Pending",
    "state.unavailable": "Unavailable",
    "state.unknown": "Unknown state",
    "state.mixed": "Partly set",
    "state.unknown_short": "Unknown",
    "state.normal": "Normal",
    "state.on": "On",
    "state.off": "Off",
    "state.connected": "Connected",
    "state.disconnected": "Disconnected",
    "state.ok": "OK",
    "state.inactive": "Inactive",
    "state.fault": "Fault",
    "state.inhibited": "Inhibited",
    "state.not_inhibited": "Not inhibited",
    "state.isolated": "Isolated",
    "state.not_isolated": "Not isolated",
    "zone.alert_tamper": "Tamper",
    "zone.alert_trouble": "Trouble",
    "system.event_history": "FlexC event history",
    "system.event_count_one": "event",
    "system.event_count_many": "events",
    "system.area": "Area",
    "system.zone": "Zone",
    "system.event_enable_hint": "To display event history, enable the diagnostic entity “Last FlexC event ID” under Settings → Devices & services → Entities, then reload the integration if needed.",
    "system.wireless_events": "Wireless events",
    "system.event_observation": "Observed events only — not persistent alarm states.",
    "system.no_recent_events": "No recent events",
    "system.event_unknown": "Undocumented event",
    "zone.motion": "Motion",
    "zone.rest": "Idle",
    "zone.open": "Open",
    "zone.closed": "Closed",
    "zone.smoke": "Smoke detected",
    "zone.heat": "Heat detected",
    "zone.active": "Active",
    "zone.tamper": "TAMPER",
    "zone.inhibited": "Inhibited",
    "zone.none": "No SPC zone discovered.",
    "zone.loading": "Loading SPC entities…",
    "zone.name": "Zone {id}",
    "area.none": "No SPC area available.",
    "area.name": "Area {id}",
    "area.last_set": "Last arm",
    "area.last_unset": "Last disarm",
    "area.tamper": "Tamper",
    "door.none": "No SPC door discovered.",
    "door.name": "Door {id}",
    "door.fallback_name": "SPC door",
    "door.status": "Status",
    "door.mode": "Mode",
    "door.dps": "DPS",
    "door.drs": "DRS",
    "door.access_forbidden": "Access forbidden",
    "door.free_access": "Free access",
    "door.unknown_area": "Unknown area association",
    "door.supervision_note": "FlexC supervision only. Door mode commands are not presented as physical lock commands.",
    "door.raw_note": "Status and Mode are displayed as provided by SPC until their meaning is validated on real hardware.",
    "output.none": "No SPC output (Mapping Gate) discovered.",
    "output.name": "Output {id}",
    "output.fallback_name": "SPC output",
    "output.mapping_gate": "Mapping Gate",
    "group.detectors": "Detectors",
    "group.tampers": "Tampers",
    "group.expand_all": "Expand all",
    "group.collapse_all": "Collapse all",
    "group.rest": "Idle",
    "group.detector_count.one": "{count} detector",
    "group.detector_count.other": "{count} detectors",
    "group.area_count.one": "{count} area",
    "group.area_count.other": "{count} areas",
    "group.tamper_count.one": "{count} tamper",
    "group.tamper_count.other": "{count} tampers",
    "group.active_count.one": "{count} Active",
    "group.active_count.other": "{count} Active",
    "group.inhibited_count.one": "{count} Inhibited",
    "group.inhibited_count.other": "{count} Inhibited",
    "group.fault_count.one": "{count} fault",
    "group.fault_count.other": "{count} faults",
    "group.unavailable_count.one": "{count} unavailable",
    "group.unavailable_count.other": "{count} unavailable",
    "group.in_fault": "{count} in fault",
    "group.no_area": "No area",
    "group.no_detector": "No detector",
    "system.health": "State and faults",
    "system.connection": "FlexC connection",
    "system.state_unknown": "State unavailable",
    "system.entity_missing": "Entity not exposed",
    "system.engineer_active": "Engineer mode active",
    "system.engineer_detail": "The state is reported in real time by the panel.",
    "system.active_faults": "Active faults",
    "system.no_fault": "No active fault",
    "system.faults_unknown": "System faults unavailable: metadata is not available.",
    "system.card": "SPC FlexC Card",
    "system.panel": "Panel",
    "system.manufacturer": "Manufacturer",
    "system.model": "Model",
    "system.firmware": "Firmware",
    "system.hardware": "Hardware",
    "system.serial": "Serial number",
    "system.power": "Power",
    "system.ac_frequency": "AC frequency",
    "system.battery_voltage": "Battery voltage",
    "system.aux_voltage": "Auxiliary voltage",
    "system.aux_current": "Auxiliary current",
    "system.communication": "FlexC communication",
    "system.state": "State",
    "system.ats_used": "ATS used",
    "system.last_tx": "Last successful transmission",
    "system.xbus": "X-BUS",
    "system.xbus_id": "X-BUS ID",
    "system.sia_address": "SIA address",
    "system.tamper": "Tamper",
    "system.tamper_isolation": "Tamper isolation",
    "system.rf": "RF",
    "system.modem": "Modem",
    "action.disarm": "Disarm",
    "action.full_arm": "Full set",
    "action.arm": "Arm",
    "action.activate": "Activate",
    "action.deactivate": "Deactivate",
    "action.execute": "Run command",
    "action.door_momentary": "Open momentarily",
    "action.door_permanent": "Open permanently",
    "action.door_normal": "Return to normal mode",
    "action.door_lock": "Lock",
    "action.restore": "Restore",
    "confirm.restore_zone": "Restore zone {name}?",
    "confirm.generic": "Run the action on {name}?",
    "confirm.disarm": "Disarm {name}?",
    "confirm.full_arm": "Full set {name}?",
    "confirm.part_set": "Activate {action} on {name}?",
    "confirm.mapping_gate": "{action} — {name}?",
    "confirm.door": "{action} — {name}?",
    "editor.entity": "Alarm entity",
    "editor.select_entity": "Select an entity",
    "editor.name": "Card name",
    "editor.show_controls": "Show alarm controls",
    "editor.confirm_actions": "Confirm arm/disarm actions",
    "editor.help": "Areas are read from the alarm entity. SPC detectors are discovered automatically from binary_sensor entities exposing zone_id, area_id and spc_zone_type. Diagnostics and technical information are associated with the same integration through the Home Assistant registries when available.",
  },
};

function spcFlexCFormatTranslation(template, variables = {}) {
  let result = String(template ?? "");

  for (const [name, value] of Object.entries(variables)) {
    result = result.split(`{${name}}`).join(String(value));
  }

  return result;
}

function spcFlexCLanguage(hass) {
  try {
    const choice = localStorage.getItem("spc-flexc-language");
    if (choice === "sv" || choice === "en") return choice;
  } catch (err) {
    // Fall back to Home Assistant's language.
  }
  const language = String(
    hass?.locale?.language || navigator.language || "en"
  ).toLowerCase();

  return language.startsWith("fr") ? "fr" : language.startsWith("sv") ? "sv" : "en";
}

function spcFlexCTranslate(hass, key, variables = {}, fallback = key) {
  const language = spcFlexCLanguage(hass);
  const template =
    SPC_FLEXC_CARD_TRANSLATIONS[language]?.[key] ??
    SPC_FLEXC_CARD_TRANSLATIONS.en[key] ??
    fallback;

  return spcFlexCFormatTranslation(template, variables);
}

const spcFlexCCardRegistration = window.customCards?.find(
  (card) => card.type === "spc-flexc-card"
);

if (spcFlexCCardRegistration) {
  spcFlexCCardRegistration.description = spcFlexCTranslate(
    null,
    "card.description"
  );
}

/* SPC FlexC Card responsive area cards and wide-layout helpers. */

const spcFlexCAreaCardsBaseRenderAreas = SpcFlexCCard.prototype._renderAreas;
const spcFlexCAreaCardsBaseStyles = SpcFlexCCard.prototype._styles;
const spcFlexCAreaCardsBaseRender = SpcFlexCCard.prototype._render;

SpcFlexCCard.prototype._areaCardStorageKey = function (
  entityId = this._config?.entity
) {
  if (!entityId) return null;
  return `spc-flexc-card:${entityId}:area-cards`;
};

SpcFlexCCard.prototype._loadAreaCardStates = function () {
  const key = this._areaCardStorageKey();
  if (!key) return {};

  try {
    const parsed = JSON.parse(window.localStorage.getItem(key) || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? parsed
      : {};
  } catch {
    return {};
  }
};

SpcFlexCCard.prototype._saveAreaCardStates = function (states) {
  const key = this._areaCardStorageKey();
  if (!key) return;

  try {
    window.localStorage.setItem(key, JSON.stringify(states));
  } catch {
    // Keep the current in-memory rendering usable when storage is unavailable.
  }
};

SpcFlexCCard.prototype._areaCardExpanded = function (areaId) {
  const states = this._loadAreaCardStates();
  return states[String(areaId)] === true;
};

SpcFlexCCard.prototype._setAreaCardExpanded = function (areaId, expanded) {
  const states = this._loadAreaCardStates();
  states[String(areaId)] = expanded === true;
  this._saveAreaCardStates(states);
};

SpcFlexCCard.prototype._setAllAreaCardsExpanded = function (expanded) {
  const states = this._loadAreaCardStates();
  for (const area of this._getAreas()) {
    states[String(area.id)] = expanded === true;
  }
  this._saveAreaCardStates(states);
};

SpcFlexCCard.prototype._renderAreas = function () {
  const areas = this._getAreas();
  const zones = this._getZones();

  if (!areas.length) {
    return spcFlexCAreaCardsBaseRenderAreas.call(this);
  }

  return `
    <div class="areas-view">
      <div class="area-toolbar">
        <button type="button" class="area-toolbar-button" data-area-action="expand-all">
          <ha-icon icon="mdi:unfold-more-horizontal"></ha-icon>
          <span>${this._t("group.expand_all")}</span>
        </button>
        <button type="button" class="area-toolbar-button" data-area-action="collapse-all">
          <ha-icon icon="mdi:unfold-less-horizontal"></ha-icon>
          <span>${this._t("group.collapse_all")}</span>
        </button>
      </div>

      <div class="list area-list">
        ${areas
          .map((area) => {
            const areaZones = zones.filter(
              (zone) => String(zone.areaId) === String(area.id)
            );

            const normalZones = areaZones.filter(
              (zone) =>
                zone.zoneType !== "tamper" &&
                zone.deviceClass !== "tamper"
            );

            const tampers = areaZones.filter(
              (zone) =>
                zone.zoneType === "tamper" ||
                zone.deviceClass === "tamper"
            );

            const isolatedZones = normalZones.filter(
              (zone) => this._zoneIsIsolated?.(zone) === true
            ).length;

            const inhibitedZones = normalZones.filter(
              (zone) =>
                zone.inhibited === true &&
                this._zoneIsIsolated?.(zone) !== true
            ).length;

            const activeZones = normalZones.filter(
              (zone) =>
                zone.state === "on" &&
                zone.inhibited !== true &&
                this._zoneIsIsolated?.(zone) !== true
            ).length;

            const activeTampers = tampers.filter(
              (zone) =>
                zone.inhibited !== true &&
                this._zoneIsIsolated?.(zone) !== true &&
                (zone.state === "on" || zone.eventTamper === true)
            ).length;

            const areaEntity = this._getAreaAlarmEntity(area.id);
            const mode =
              areaEntity?.stateObj?.attributes?.mode_name ??
              area.modeName ??
              areaEntity?.stateObj?.attributes?.mode ??
              area.mode ??
              "unknown";

            const renderedState = areaEntity?.stateObj?.state || null;
            const stateClass = renderedState
              ? this._stateClass(renderedState)
              : this._modeClass(mode);

            const icon = renderedState
              ? this._stateIcon(renderedState)
              : stateClass === "ok"
                ? "mdi:lock-open-variant"
                : "mdi:lock";

            const label =
              renderedState === "armed_home"
                ? this._partSetLabel(areaEntity, "a")
                : renderedState === "armed_night"
                  ? this._partSetLabel(areaEntity, "b")
                  : renderedState === "disarmed"
                    ? this._t("state.disarmed_masc")
                    : renderedState
                      ? this._stateLabel(renderedState)
                      : this._modeLabel(mode);

            const expanded = this._areaCardExpanded(area.id);

            return `
              <div class="area-card ${expanded ? "expanded" : "collapsed"}">
                <button
                  type="button"
                  class="area-card-toggle"
                  data-area-id="${this._escapeHtml(area.id)}"
                  aria-expanded="${expanded ? "true" : "false"}"
                >
                  <span class="area-card-title">${this._escapeHtml(area.name)}</span>
                  <span class="area-card-toggle-state">
                    <span class="badge ${stateClass}">${this._escapeHtml(label)}</span>
                    <ha-icon class="area-card-chevron" icon="mdi:chevron-down"></ha-icon>
                  </span>
                </button>

                ${
                  expanded
                    ? `
                      <div class="area-card-body">
                        <div class="area-lock">
                          <ha-icon class="${stateClass}" icon="${this._escapeHtml(icon)}"></ha-icon>
                        </div>

                        <div class="area-meta">
                          <span>${this._tCount("group.detector_count", normalZones.length)}</span>
                          ${isolatedZones ? `<span class="danger">${isolatedZones} ${this._t("state.isolated")}</span>` : ""}
                          ${inhibitedZones ? `<span class="zone-inhibited">${this._tCount("group.inhibited_count", inhibitedZones)}</span>` : ""}
                          ${
                            activeZones
                              ? `<span class="warning">${this._tCount("group.active_count", activeZones)}</span>`
                              : !isolatedZones && !inhibitedZones
                                ? `<span class="ok">${this._t("group.rest")}</span>`
                                : ""
                          }
                          ${
                            activeTampers
                              ? `<span class="danger">${this._t("area.tamper")}</span>`
                              : ""
                          }
                        </div>

                        ${this._lastAreaChange(areaEntity?.stateObj)}
                        ${this._renderAreaControls(area, areaEntity)}
                      </div>
                    `
                    : ""
                }
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
};

SpcFlexCCard.prototype._styles = function () {
  return `${spcFlexCAreaCardsBaseStyles.call(this)}
    <style>
      .areas-view {
        display: grid;
        gap: 14px;
      }

      .area-toolbar {
        display: flex;
        justify-content: flex-end;
        flex-wrap: wrap;
        gap: 8px;
      }

      .area-toolbar-button,
      .area-card-toggle {
        appearance: none;
        border: 0;
        background: transparent;
        color: var(--primary-text-color);
        cursor: pointer;
        font: inherit;
      }

      .area-toolbar-button {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 7px 10px;
        border: 1px solid var(--divider-color);
        border-radius: 9px;
        color: var(--secondary-text-color);
        font-size: 12px;
        font-weight: 600;
      }

      .area-toolbar-button:hover {
        color: var(--primary-text-color);
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.08));
      }

      .area-toolbar-button ha-icon {
        --mdc-icon-size: 18px;
      }

      .area-list {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        align-items: start;
      }

      .area-card {
        padding: 0;
        overflow: hidden;
      }

      .area-card-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        width: 100%;
        padding: 18px;
        text-align: left;
      }

      .area-card-toggle:hover {
        background: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
      }

      .area-card-toggle-state {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
      }

      .area-card-toggle .badge {
        text-align: right;
      }

      .area-card-chevron {
        --mdc-icon-size: 22px;
        flex: 0 0 auto;
        color: var(--secondary-text-color);
        transition: transform 0.15s ease;
      }

      .area-card.expanded .area-card-chevron {
        transform: rotate(180deg);
      }

      .area-card-body {
        padding: 0 18px 18px;
        border-top: 1px solid color-mix(in srgb, var(--divider-color) 55%, transparent);
      }

      .door-list,
      .output-list,
      .technical-system-view {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }

      .technical-system-view {
        align-items: start;
      }

      .technical-system-view > .technical-section {
        min-width: 0;
      }

      .output-list {
        gap: 14px;
      }

      .output-row {
        grid-template-columns: 40px minmax(0, 1fr) auto;
        align-content: start;
      }

      .output-controls {
        grid-column: 2 / -1;
      }

      @media (max-width: 700px) {
        .area-list,
        .door-list,
        .output-list,
        .technical-system-view {
          grid-template-columns: 1fr;
        }

        .area-toolbar {
          justify-content: stretch;
        }

        .area-toolbar-button {
          flex: 1 1 auto;
          justify-content: center;
        }
      }
    </style>`;
};

SpcFlexCCard.prototype._render = function () {
  spcFlexCAreaCardsBaseRender.call(this);

  this.querySelectorAll("[data-area-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const areaId = button.dataset.areaId;
      const expanded = button.getAttribute("aria-expanded") === "true";
      this._setAreaCardExpanded(areaId, !expanded);
      this._render();
    });
  });

  this.querySelectorAll("[data-area-action]").forEach((button) => {
    button.addEventListener("click", () => {
      this._setAllAreaCardsExpanded(button.dataset.areaAction === "expand-all");
      this._render();
    });
  });
};

/* SPC FlexC Card communication diagnostics. */

const spcFlexCCommunicationBaseStyles = SpcFlexCCard.prototype._styles;
const spcFlexCCommunicationBaseRender = SpcFlexCCard.prototype._render;

SpcFlexCCard.prototype._styles = function () {
  return `${spcFlexCCommunicationBaseStyles.call(this)}
    <style>
      .atp-card {
        overflow: hidden;
      }

      .atp-card > summary {
        list-style: none;
      }

      .atp-card > summary::-webkit-details-marker {
        display: none;
      }

      .atp-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        cursor: pointer;
        user-select: none;
      }

      .atp-title-main {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
      }

      .atp-title-main::before {
        content: "▸";
        color: var(--secondary-text-color);
        font-size: 12px;
        line-height: 1;
        transition: transform 120ms ease;
      }

      .atp-card[open] .atp-title-main::before {
        transform: rotate(90deg);
      }

      .atp-card-body {
        padding-top: 4px;
      }
    </style>`;
};

SpcFlexCCard.prototype._renderFlexcCommunication = function () {
  const atsList = this._getFlexcCommunication();
  if (!atsList.length) return "";

  return `
    <div class="technical-section">
      <div class="technical-section-title">${this._t("system.communication")}</div>
      <div class="ats-list">
        ${atsList
          .map((ats) => {
            const atsLabel = ats.ungrouped
              ? ats.name
              : `ATS ${ats.id ?? "?"}${
                  ats.name ? ` — ${ats.name}` : ""
                }`;

            return `
              <div class="ats-card">
                <div class="ats-title">${this._escapeHtml(atsLabel)}</div>
                ${ats.atps.length
                  ? `<div class="atp-list">
                      ${ats.atps
                        .map((atp) => {
                          const atpLabel = `ATP ${atp.displayId ?? "?"}${
                            atp.name ? ` — ${atp.name}` : ""
                          }`;
                          const stateInfo = this._atpStateLabel(atp);
                          const formattedTx = this._formatDateTime(
                            atp.lastTxOkTimestamp
                          );
                          const atpKey = `${ats.id ?? "ungrouped"}:${atp.id ?? atp.displayId ?? "unknown"}`;

                          return `
                            <details class="atp-card" data-atp-key="${this._escapeHtml(atpKey)}">
                              <summary class="atp-title">
                                <span class="atp-title-main">${this._escapeHtml(atpLabel)}</span>
                                ${stateInfo
                                  ? `<span class="${stateInfo.className}">${this._escapeHtml(stateInfo.label)}</span>`
                                  : ""}
                              </summary>
                              <div class="atp-card-body">
                                ${stateInfo
                                  ? this._technicalLine(
                                      this._t("system.state"),
                                      stateInfo.label,
                                      stateInfo.className
                                    )
                                  : ""}
                                ${ats.ungrouped
                                  ? ""
                                  : this._technicalLine(
                                      this._t("system.ats_used"),
                                      atsLabel
                                    )}
                                ${this._technicalLine(
                                  this._t("system.last_tx"),
                                  formattedTx
                                )}
                              </div>
                            </details>
                          `;
                        })
                        .join("")}
                    </div>`
                  : ""}
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
};

SpcFlexCCard.prototype._render = function () {
  const openAtps = new Set(
    Array.from(this.querySelectorAll("details.atp-card[open][data-atp-key]"))
      .map((details) => details.dataset.atpKey)
      .filter(Boolean)
  );

  spcFlexCCommunicationBaseRender.call(this);

  if (!openAtps.size) {
    return;
  }

  for (const details of this.querySelectorAll("details.atp-card[data-atp-key]")) {
    if (openAtps.has(details.dataset.atpKey)) {
      details.open = true;
    }
  }
};

/* SPC FlexC Card X-BUS diagnostics. */

const spcFlexCXBusBaseStyles = SpcFlexCCard.prototype._styles;
const spcFlexCXBusBaseTechnicalSystem = SpcFlexCCard.prototype._renderTechnicalSystem;
const spcFlexCXBusBaseRender = SpcFlexCCard.prototype._render;

SpcFlexCCard.prototype._styles = function () {
  return `${spcFlexCXBusBaseStyles.call(this)}
    <style>
      .xbus-card { overflow:hidden; }
      .xbus-card > summary { list-style:none; }
      .xbus-card > summary::-webkit-details-marker { display:none; }
      .xbus-title { cursor:pointer; user-select:none; }
      .xbus-title-main { display:flex; align-items:center; gap:8px; min-width:0; }
      .xbus-title-main::before { content:"▸"; color:var(--secondary-text-color); font-size:12px; line-height:1; transition:transform 120ms ease; }
      .xbus-card[open] .xbus-title-main::before { transform:rotate(90deg); }
      .xbus-title-text { display:flex; flex-direction:column; min-width:0; }
      .xbus-title-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .xbus-title-model { color:var(--secondary-text-color); font-size:11px; font-weight:500; line-height:1.25; }
      .xbus-card-body { padding-top:4px; }
    </style>`;
};

SpcFlexCCard.prototype._xBusDeviceRegistryMap = function () {
  const scope = this._diagnosticScope;
  const devices = scope?.devices;
  if (!(devices instanceof Map)) return new Map();
  return devices;
};

SpcFlexCCard.prototype._xBusModelFromDiagnostics = function (device) {
  const type = Number(device.deviceType);
  const inputs = Number(device.inputCount);
  const outputs = Number(device.outputCount);

  if (type === 1) return "SPC Keypad";
  if (type === 7) return "SPC Comfort Keypad";
  if (type === 6 && inputs === 4 && outputs === 2) return "SPCA210";
  if (type === 2 && inputs === 8 && outputs === 2) return "SPCE650";
  if (type === 2 && inputs === 0 && outputs === 8) return "SPCE450";
  return null;
};

SpcFlexCCard.prototype._xBusModelLabel = function (model) {
  const value = String(model || "").trim();
  if (!value) return null;

  const language = String(this._hass?.locale?.language || navigator.language || "en")
    .toLowerCase();
  if (!language.startsWith("fr")) return value;

  return {
    "SPC Keypad": "Clavier SPC",
    "SPC Comfort Keypad": "Clavier confort SPC",
    SPCE650: "Transpondeur E/S SPCE650",
    SPCE450: "Transpondeur de sorties SPCE450",
    SPCA210: "Transpondeur de porte SPCA210",
  }[value] || value;
};

SpcFlexCCard.prototype._getXBusDevices = function () {
  const devices = new Map();
  const registryDevices = Array.isArray(this._diagnosticScope?.devices)
    ? this._diagnosticScope.devices
    : [];
  const registryDeviceMap = new Map(
    registryDevices.map((device) => [device.id, device])
  );

  const ensureDevice = (identity, deviceId) => {
    const key = String(identity);
    if (!devices.has(key)) {
      devices.set(key, {
        key,
        id: deviceId,
        name: null,
        model: null,
        deviceType: null,
        inputCount: null,
        outputCount: null,
        serialNumber: null,
        version: null,
        siaAddress: null,
        tamperFault: null,
        tamperInhibited: null,
        tamperIsolated: null,
        entities: [],
      });
    }
    return devices.get(key);
  };

  for (const { entityId, stateObj, registryEntry } of this._scopedStates(true)) {
    const attrs = stateObj?.attributes || {};
    const uniqueId = String(registryEntry?.unique_id || "");
    const match = uniqueId.match(/_xbus_([0-9A-Fa-f]+)_(.+)$/);
    const registryDevice = registryDeviceMap.get(registryEntry?.device_id);
    const serialNumber =
      attrs.serial_number ?? registryDevice?.serial_number ?? match?.[1] ?? null;
    const deviceId = attrs.xbus_device_id ?? null;
    const identity = serialNumber ?? deviceId;

    if (identity === null || identity === undefined) continue;

    const device = ensureDevice(identity, deviceId);
    const field = match?.[2] || null;

    device.name = attrs.xbus_device_name || attrs.name || device.name;
    device.model = registryDevice?.model || attrs.model || device.model;
    device.deviceType = attrs.device_type ?? device.deviceType;
    device.inputCount = attrs.input_count ?? device.inputCount;
    device.outputCount = attrs.output_count ?? device.outputCount;
    device.serialNumber = serialNumber ?? device.serialNumber;
    device.version = attrs.version ?? registryDevice?.sw_version ?? device.version;
    device.siaAddress = attrs.sia_address ?? device.siaAddress;

    if (attrs.tamper_fault !== undefined && attrs.tamper_fault !== null) device.tamperFault = attrs.tamper_fault === true;
    if (attrs.tamper_inhibited !== undefined && attrs.tamper_inhibited !== null) device.tamperInhibited = attrs.tamper_inhibited === true;
    if (attrs.tamper_isolated !== undefined && attrs.tamper_isolated !== null) device.tamperIsolated = attrs.tamper_isolated === true;
    if (field === "tamper_fault") {
      if (stateObj.state === "on") device.tamperFault = true;
      if (stateObj.state === "off") device.tamperFault = false;
    }
    if (field === "tamper_inhibited") {
      if (stateObj.state === "on") device.tamperInhibited = true;
      if (stateObj.state === "off") device.tamperInhibited = false;
    }
    if (field === "tamper_isolated") {
      if (stateObj.state === "on") device.tamperIsolated = true;
      if (stateObj.state === "off") device.tamperIsolated = false;
    }

    device.entities.push({ entityId, stateObj, field });
  }

  for (const device of devices.values()) {
    device.model ||= this._xBusModelFromDiagnostics(device);
  }

  return Array.from(devices.values()).sort((a, b) => {
    const idOrder =
      Number(a.id ?? Number.MAX_SAFE_INTEGER) -
      Number(b.id ?? Number.MAX_SAFE_INTEGER);
    if (idOrder) return idOrder;
    return String(a.serialNumber || a.key).localeCompare(
      String(b.serialNumber || b.key)
    );
  });
};

SpcFlexCCard.prototype._xBusEntityValue = function (entity) {
  const { field, stateObj } = entity;
  if (field === "tamper_fault") {
    if (stateObj.state === "on") return { value:this._t("state.fault"), className:"danger" };
    if (stateObj.state === "off") return { value:this._t("state.ok"), className:"ok" };
  }
  if (field === "tamper_inhibited") {
    if (stateObj.state === "on") return { value:this._t("state.inhibited"), className:"zone-inhibited" };
    if (stateObj.state === "off") return { value:this._t("state.not_inhibited"), className:"ok" };
  }
  if (field === "tamper_isolated") {
    if (stateObj.state === "on") return { value:this._t("state.isolated"), className:"warning" };
    if (stateObj.state === "off") return { value:this._t("state.not_isolated"), className:"ok" };
  }
  return { value:this._valueWithUnit(stateObj), className:"" };
};

SpcFlexCCard.prototype._xBusEntityLabel = function (device, entity) {
  const friendlyName = String(entity.stateObj?.attributes?.friendly_name || entity.entityId).trim();
  if (!device.name) return friendlyName;
  const prefix = `${device.name} `;
  return friendlyName.startsWith(prefix) ? friendlyName.slice(prefix.length) : friendlyName;
};

SpcFlexCCard.prototype._renderXBusDevices = function () {
  const devices = this._getXBusDevices();
  if (!devices.length) return "";
  const fieldOrder = ["tamper_fault","tamper_inhibited","tamper_isolated","aux_voltage","aux_current","device_type","hardware_id","input_count","output_count","rf_type","rf_version","reader_type","position_1","position_2","psu_type","sia_address","status_raw","input_raw","alert_raw","inhibit_raw","isolate_raw"];
  const order = new Map(fieldOrder.map((field, index) => [field, index]));

  return `<div class="technical-section xbus-section"><div class="technical-section-title">${this._t("system.xbus")}</div><div class="xbus-list">${devices.map((device) => {
    const title = device.name || `X-BUS ${device.id}`;
    const model = this._xBusModelLabel(device.model);
    const fault = device.tamperFault === true;
    const inhibited = device.tamperInhibited === true;
    const isolated = device.tamperIsolated === true;
    const headerStates = [
      device.tamperFault === true ? `<span class="danger">${this._t("state.fault")}</span>` : "",
      device.tamperInhibited === true ? `<span class="zone-inhibited">${this._t("state.inhibited")}</span>` : "",
      device.tamperIsolated === true ? `<span class="danger">${this._t("state.isolated")}</span>` : "",
    ].filter(Boolean).join(" ");
    const rows = device.entities.filter((entity) => entity.field && entity.field !== "diagnostics").sort((a,b) => {
      const aOrder=order.get(a.field) ?? Number.MAX_SAFE_INTEGER;
      const bOrder=order.get(b.field) ?? Number.MAX_SAFE_INTEGER;
      return aOrder-bOrder || a.field.localeCompare(b.field);
    }).map((entity) => {
      const state=this._xBusEntityValue(entity);
      if (state.value === null || state.value === undefined) return "";
      return this._technicalLine(this._xBusEntityLabel(device,entity),state.value,state.className);
    }).join("");

    return `<details class="xbus-card" data-xbus-key="${this._escapeHtml(String(device.key))}"><summary class="xbus-title"><span class="xbus-title-main"><span class="xbus-title-text"><span class="xbus-title-name">${this._escapeHtml(title)}</span>${model ? `<span class="xbus-title-model">${this._escapeHtml(model)}</span>` : ""}</span></span>${headerStates || (device.tamperFault === false && device.tamperInhibited !== true && device.tamperIsolated !== true ? `<span class="ok">${this._t("state.ok")}</span>` : "")}</summary><div class="xbus-card-body">${this._technicalLine(this._t("system.xbus_id"),device.id)}${this._technicalLine(this._t("system.serial"),device.serialNumber)}${this._technicalLine(this._t("system.firmware"),device.version)}${rows}</div></details>`;
  }).join("")}</div></div>`;
};

SpcFlexCCard.prototype._renderTechnicalSystem = function () {
  const html = spcFlexCXBusBaseTechnicalSystem.call(this);
  const deviceNames = this._getXBusDevices().map((device) => String(device.name || "").trim()).filter(Boolean);
  if (!html || !deviceNames.length || typeof DOMParser === "undefined") return html;
  const documentNode = new DOMParser().parseFromString(`<body>${html}</body>`,"text/html");
  for (const section of documentNode.querySelectorAll(".technical-section")) {
    const title=section.querySelector(".technical-section-title")?.textContent?.trim();
    if (title !== this._t("system.rf")) continue;
    for (const row of section.querySelectorAll(".technical-row")) {
      const label=row.querySelector(".technical-label")?.textContent?.trim() || "";
      const belongsToXBus=deviceNames.some((deviceName) => label === deviceName || label.startsWith(`${deviceName} `));
      if (belongsToXBus) row.remove();
    }
    if (!section.querySelector(".technical-row")) section.remove();
  }
  return documentNode.body.innerHTML;
};

SpcFlexCCard.prototype._render = function () {
  const openXBusDevices = new Set(Array.from(this.querySelectorAll("details.xbus-card[open][data-xbus-key]")).map((details) => details.dataset.xbusKey).filter(Boolean));
  spcFlexCXBusBaseRender.call(this);
  if (!openXBusDevices.size) return;
  for (const details of this.querySelectorAll("details.xbus-card[data-xbus-key]")) {
    if (openXBusDevices.has(details.dataset.xbusKey)) details.open = true;
  }
};

/* SPC FlexC Card container-responsive layout. */

const spcFlexCResponsiveBaseStyles = SpcFlexCCard.prototype._styles;
const spcFlexCResponsiveBaseGridOptions = SpcFlexCCard.prototype.getGridOptions;
const spcFlexCResponsiveBaseTechnicalSystem = SpcFlexCCard.prototype._renderTechnicalSystem;

SpcFlexCCard.prototype.getGridOptions = function () {
  const baseOptions = spcFlexCResponsiveBaseGridOptions
    ? spcFlexCResponsiveBaseGridOptions.call(this)
    : {};

  return {
    ...baseOptions,
    columns: "full",
  };
};

SpcFlexCCard.prototype._renderTechnicalSystem = function () {
  const html = spcFlexCResponsiveBaseTechnicalSystem.call(this);

  if (!html || typeof DOMParser === "undefined") {
    return html;
  }

  const documentNode = new DOMParser().parseFromString(
    `<body>${html}</body>`,
    "text/html"
  );
  const root = documentNode.querySelector(".technical-system-view");

  if (!root) {
    return html;
  }

  const columns = [[], [], []];
  const communicationTitle = this._t("system.communication");
  const xbusTitle = this._t("system.xbus");
  const rfTitle = this._t("system.rf");
  const modemTitle = this._t("system.modem");

  for (const section of Array.from(root.children)) {
    const title = section
      .querySelector(".technical-section-title")
      ?.textContent?.trim();

    if (title === xbusTitle) {
      columns[1].push(section.outerHTML);
    } else if (title === communicationTitle) {
      columns[2].push(section.outerHTML);
    } else if (title === rfTitle || title === modemTitle) {
      columns[0].push(section.outerHTML);
    } else {
      columns[0].push(section.outerHTML);
    }
  }

  return `
    <div class="technical-system-view technical-system-columns">
      <div class="technical-system-column technical-system-column-main">
        ${columns[0].join("")}
      </div>
      <div class="technical-system-column technical-system-column-xbus">
        ${columns[1].join("")}
      </div>
      <div class="technical-system-column technical-system-column-communication">
        ${columns[2].join("")}
      </div>
    </div>
  `;
};

SpcFlexCCard.prototype._styles = function () {
  return `${spcFlexCResponsiveBaseStyles.call(this)}
    <style>
      .card {
        container-type: inline-size;
        container-name: spc-flexc-card;
      }

      .area-list,
      .door-list,
      .output-list,
      .technical-system-view {
        grid-template-columns: 1fr;
      }

      .technical-system-column {
        display: grid;
        gap: 18px;
        align-content: start;
        min-width: 0;
      }

      .technical-row {
        grid-template-columns: 1fr;
        gap: 2px;
      }

      .technical-value {
        text-align: left;
      }

      .xbus-card,
      .ats-card,
      .atp-card,
      .door-card,
      .output-row,
      .area-card {
        min-width: 0;
      }

      @container spc-flexc-card (min-width: 840px) {
        .area-list,
        .door-list,
        .output-list,
        .technical-system-view {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .technical-row {
          grid-template-columns: minmax(130px, 0.7fr) minmax(0, 1.3fr);
          gap: 14px;
        }

        .technical-value {
          text-align: right;
        }
      }
    </style>`;
};

/* Preserve expanded diagnostic sections across Home Assistant updates. */
const spcSystemDetailsRender = SpcFlexCCard.prototype._render;
SpcFlexCCard.prototype._render = function () {
  const open = new Set(Array.from(this.querySelectorAll("details.system-detail-card[open]"))
    .map((node) => node.dataset.systemDetailKey).filter(Boolean));
  spcSystemDetailsRender.call(this);
  this.querySelectorAll("details.system-detail-card").forEach((node) => {
    if (open.has(node.dataset.systemDetailKey)) node.open = true;
  });
};

const spcSystemDetailsStyles = SpcFlexCCard.prototype._styles;
SpcFlexCCard.prototype._styles = function () {
  return `${spcSystemDetailsStyles.call(this)}
    <style>
      .system-detail-card { border:1px solid var(--divider-color); border-radius:12px; padding:10px 12px; margin-top:8px; overflow:hidden; }
      .system-detail-card > summary { cursor:pointer; list-style:none; display:flex; align-items:center; gap:8px; font-weight:600; }
      .system-detail-card > summary::-webkit-details-marker { display:none; }
      .system-detail-card > summary::before { content:"▸"; color:var(--secondary-text-color); transition:transform 120ms ease; }
      .system-detail-card[open] > summary::before { transform:rotate(90deg); }
      .system-detail-body { padding-top:10px; }
    </style>`;
};

/* SPC FlexC Card render scheduler. */

const spcFlexCImmediateRender = SpcFlexCCard.prototype._render;
const spcFlexCBaseDisconnectedCallback =
  SpcFlexCCard.prototype.disconnectedCallback;

SpcFlexCCard.prototype._showCardVersion = function () {
  if (this.querySelector(".spc-card-version")) {
    return;
  }

  const panelSection =
    this.querySelector('[data-technical-section="panel"]') ||
    Array.from(this.querySelectorAll(".technical-section")).find(
      (section) =>
        section.querySelector(".technical-section-title")?.textContent.trim() ===
        this._t("system.panel")
    );

  if (!panelSection) {
    return;
  }

  const versionRow = document.createElement("div");
  versionRow.className = "technical-row spc-card-version";
  versionRow.innerHTML = `
    <div class="technical-label">${this._escapeHtml(this._t("system.card"))}</div>
    <div class="technical-value">${this._escapeHtml(CARD_VERSION)}</div>
  `;

  panelSection
    .querySelector(".technical-section-title")
    ?.insertAdjacentElement("afterend", versionRow);
};

SpcFlexCCard.prototype._captureScrollPositions = function () {
  const positions = [];
  const seen = new Set();
  let node = this;

  while (node) {
    const parent = node.parentElement || node.getRootNode?.()?.host || null;
    if (!parent || seen.has(parent)) {
      break;
    }

    seen.add(parent);

    if (
      parent.scrollHeight > parent.clientHeight ||
      parent.scrollWidth > parent.clientWidth
    ) {
      positions.push({
        element: parent,
        top: parent.scrollTop,
        left: parent.scrollLeft,
      });
    }

    node = parent;
  }

  const scrollingElement = document.scrollingElement;
  if (scrollingElement && !seen.has(scrollingElement)) {
    positions.push({
      element: scrollingElement,
      top: scrollingElement.scrollTop,
      left: scrollingElement.scrollLeft,
    });
  }

  return positions;
};

SpcFlexCCard.prototype._restoreScrollPositions = function (positions) {
  for (const position of positions || []) {
    const { element, top, left } = position;
    if (!element?.isConnected) {
      continue;
    }

    if (element.scrollTop !== top) {
      element.scrollTop = top;
    }
    if (element.scrollLeft !== left) {
      element.scrollLeft = left;
    }
  }
};

SpcFlexCCard.prototype._render = function () {
  if (this._spcRenderFrame != null) {
    return;
  }

  const render = () => {
    this._spcRenderFrame = null;
    this._spcRenderUsesAnimationFrame = false;

    const scrollPositions = this._captureScrollPositions();

    // The base renderer now preserves the connected tab strip on routine updates.
    const previousHaCard = this.querySelector(":scope > ha-card");
    // Preserve scroll position when the tab strip must actually be replaced.
    const previousTabsScrollLeft = previousHaCard?.querySelector(".tabs")?.scrollLeft ?? 0;
    // The legacy renderer replaces the complete card DOM with innerHTML on
    // every HA update. Keep the host at its current rendered height while the
    // replacement custom elements are attached/upgraded. Without this guard,
    // the dashboard briefly reflows and produces a visible vertical jump on
    // every tab, even when the user's scrollTop is restored afterwards.
    const previousMinHeight = this.style.minHeight;
    const renderedHeight = this.getBoundingClientRect().height;
    if (renderedHeight > 0) {
      this.style.minHeight = `${renderedHeight}px`;
    }

    spcFlexCImmediateRender.call(this);

    // Restore the horizontal tab position after the old shell is reattached
    // (or after the new shell replaces it on a tab change).
    const restoreTabsScroll = () => {
      const tabs = this.querySelector(":scope > ha-card .tabs");
      if (tabs && tabs.scrollLeft !== previousTabsScrollLeft) {
        tabs.scrollLeft = previousTabsScrollLeft;
      }
    };
    restoreTabsScroll();
    this._showCardVersion();
    this._restoreScrollPositions(scrollPositions);

    if (this._spcScrollRestoreFrame != null &&
        typeof window.cancelAnimationFrame === "function") {
      window.cancelAnimationFrame(this._spcScrollRestoreFrame);
    }

    this._spcScrollRestoreFrame = window.requestAnimationFrame?.(() => {
      this._spcScrollRestoreFrame = null;
      restoreTabsScroll();
      this._restoreScrollPositions(scrollPositions);

      // Release the temporary layout lock only after the replacement DOM has
      // had a frame to settle. Restore scroll once more after releasing it in
      // case the new content legitimately has a different height.
      this.style.minHeight = previousMinHeight;
      this._spcLayoutReleaseFrame = window.requestAnimationFrame?.(() => {
        this._spcLayoutReleaseFrame = null;
        this._restoreScrollPositions(scrollPositions);
      }) ?? null;
    }) ?? null;
  };

  if (typeof window.requestAnimationFrame === "function") {
    this._spcRenderUsesAnimationFrame = true;
    this._spcRenderFrame = window.requestAnimationFrame(render);
  } else {
    this._spcRenderUsesAnimationFrame = false;
    this._spcRenderFrame = window.setTimeout(render, 0);
  }
};

SpcFlexCCard.prototype.disconnectedCallback = function () {
  if (this._spcRenderFrame != null) {
    if (
      this._spcRenderUsesAnimationFrame &&
      typeof window.cancelAnimationFrame === "function"
    ) {
      window.cancelAnimationFrame(this._spcRenderFrame);
    } else {
      window.clearTimeout(this._spcRenderFrame);
    }

    this._spcRenderFrame = null;
    this._spcRenderUsesAnimationFrame = false;
  }

  if (
    this._spcScrollRestoreFrame != null &&
    typeof window.cancelAnimationFrame === "function"
  ) {
    window.cancelAnimationFrame(this._spcScrollRestoreFrame);
    this._spcScrollRestoreFrame = null;
  }

  if (
    this._spcLayoutReleaseFrame != null &&
    typeof window.cancelAnimationFrame === "function"
  ) {
    window.cancelAnimationFrame(this._spcLayoutReleaseFrame);
    this._spcLayoutReleaseFrame = null;
  }

  this.style.minHeight = "";
  spcFlexCBaseDisconnectedCallback.call(this);
};

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

// The panel's system settings (READ_INTRUDER_CFG, decoded by the
// integration into the sensor's "settings" attribute) with the web page's
// names (Konfiguration > System) and units. Mapped on 2026-11-13.

// The web page's balancing (EOL) list, value = EOL.
const SPC_EOL_SV = { 0: "Ingen", 1: "Enkel bal 1K0", 18: "Enkel bal 1K5", 2: "Enkel bal 2K2", 29: "Enkel bal 3K3", 3: "Enkel bal 4K7", 19: "Enkel bal 10K", 20: "Enkel bal 12K", 15: "Dubbel 1K / 470R", 4: "Dubbel 1K / 1K", 23: "Dubbel 1K0 / 2K2", 22: "Dubbel 1K5 / 2K2", 30: "Dubbel 10K / 1K8", 5: "Dubbel 2K2 / 2K2", 21: "Dubbel 2K2 / 4K7", 13: "Dubbel 2K7 / 8K2", 24: "Dubbel 2K2 / 10K", 10: "Dubbel 3K0 / 3K0", 11: "Dubbel 3K3 / 3K3", 14: "Dubbel 3K9 / 8K2", 6: "Dubbel 4K7 / 2K2", 9: "Dubbel 4K7 / 4K7", 12: "Dubbel 5K6 / 5K6", 8: "Dubbel 6K8 / 4K7", 25: "Dubbel 10K / 10K", 7: "Mask 1K 1K 6K8", 16: "Mask 1K 1K 2K2", 17: "Mask 4K7 4K7 2K2", 26: "Mask 1K 1K 3K", 27: "Mask 1K 1K 12K", 28: "Mask 4K7 4K7 10K" };
const SPC_EOL_EN = { 0: "None", 1: "Single 1K0", 18: "Single 1K5", 2: "Single 2K2", 29: "Single 3K3", 3: "Single 4K7", 19: "Single 10K", 20: "Single 12K", 15: "Double 1K / 470R", 4: "Double 1K / 1K", 23: "Double 1K0 / 2K2", 22: "Double 1K5 / 2K2", 30: "Double 10K / 1K8", 5: "Double 2K2 / 2K2", 21: "Double 2K2 / 4K7", 13: "Double 2K7 / 8K2", 24: "Double 2K2 / 10K", 10: "Double 3K0 / 3K0", 11: "Double 3K3 / 3K3", 14: "Double 3K9 / 8K2", 6: "Double 4K7 / 2K2", 9: "Double 4K7 / 4K7", 12: "Double 5K6 / 5K6", 8: "Double 6K8 / 4K7", 25: "Double 10K / 10K", 7: "Mask 1K 1K 6K8", 16: "Mask 1K 1K 2K2", 17: "Mask 4K7 4K7 2K2", 26: "Mask 1K 1K 3K", 27: "Mask 1K 1K 12K", 28: "Mask 4K7 4K7 10K" };

const SPC_SETTINGS_TEXT = {
  sv: {
    settings: "Centralens inställningar", standard: "Standard", options: "Systemalternativ",
    choices: "Val", timers: "Timers", yes: "Ja", no: "Nej",
    units: { min: "min", s: "s", h: "tim", d: "dagar", "": "" },
    standardNames: { continent: "Kontinent", region: "Region", type: "Typ", grade: "Klass" },
    optionNames: {
      bellonfirst: "Siren vid första larm", retrigger: "Siren återstart", open_zones: "Visa öppna sektioner",
      always_state: "Visa alltid status", autorestore: "Automatisk återställning", coded_restore: "Kodad återställning",
      keyfob_restore: "Återställning via fjärrkontroll", restore_on_unset: "Återställ vid frånkoppling",
      engineer_restore: "Installatörsåterställning", bellfts: "Siren vid tillkopplingsfel",
      strobefts: "Blixtljus vid tillkopplingsfel", alert_forbid_set: "Förbjud Tillkoppling med fel",
      alarmexit: "Larm vid utpassage", alarm_entry: "Larm vid inpassage", final_exit: "Kontinuerligt sista utgång",
      offline_tamper: "Offline sabotage", alarm_on_ftc: "Larm vid rapporterat fel",
      report_full_engineer: "Rapportera i inst läge", outputs_full_engineer: "Utgångar i installatörsläge",
      eng_allow_exit: "Installatör avslut", duress_retrigger: "Återstarta hotlarm", panic_retrigger: "Återstarta bråklarm",
      suspicion_audible: "Misstanke ljudande larm", seismic_test_on_set: "Test av seismiska vid Tillkoppl.",
      callcs_enable: "Meddelande till LC", hide_bypass_message: "Dölj förbikoppling",
      log_keypad_access: "Logga manöverpanelåtkomst", offline_cameras: "Visa kameror",
      aex_no_led: "Audioexpander LED", silence_audio_ver: "Tystnad vid Audioverifiering",
      reader_leds: "C-app styr läsar LEDs",
    },
    choiceNames: {
      parta_name: "Namn på Deltillkoppling A", partb_name: "Namn på Deltillkoppling B", pindigits: "PIN-siffror",
      duress: "Användare Hotlarm", doormode_set: "Dörrläge vid Tillkopplat", doormode_unset: "Dörrläge vid Frånkopplat",
      eol: "Balansering", zonenobells: "Inga sirener sektionsattribut", watchdog_output_mode: "Watchdog Utgångsläge",
      antimaskset: "Antimask Tillkoppling", antimaskunset: "Antimask Frånkoppling",
      outofboundset: "Ogiltig EOL vid till", outofboundunset: "Ogiltig EOL vid från",
      zoneunstableset: "Sektion ostabil till", zoneunstableunset: "Sektion ostabil från",
    },
    choiceValues: {
      eol: SPC_EOL_SV,
      continent: { 0: "Europa", 1: "Asien", 2: "Nordamerika", 3: "Sydamerika", 4: "Oceanien" },
      region: { 6: "Sverige" },
      type: { 0: "Privatmarknaden", 2: "Finansiell" },
      grade: { 0: "Installatörens konfiguration" },
      duress: { 0: "Inaktiverad", 1: "KOD +1", 2: "KOD +2" },
      doormode_set: { 0: "Standard", 1: "Kort och PIN-kod", 2: "Kort eller PIN" },
      doormode_unset: { 0: "Standard", 1: "Kort och PIN-kod", 2: "Kort eller PIN" },
      zonenobells: { 1: "Ingen siren", 2: "Ingen intern siren", 3: "Ingen extern siren" },
      watchdog_output_mode: { 0: "Inaktivera", 1: "Aktiverad", 2: "Pulsad", 3: "Aktiverad inverterat",
        4: "Aktiverad + Rapportering (10s)", 5: "Aktiverad + Rapportering (60s)" },
      antimaskset: { 0: "Inaktiverad", 1: "Sabotage", 2: "Antimask", 3: "Larm" },
      antimaskunset: { 0: "Inaktiverad", 1: "Sabotage", 2: "Antimask", 3: "Larm" },
      outofboundset: { 0: "Inaktiverad", 1: "Sabotage", 2: "Antimask" },
      outofboundunset: { 0: "Inaktiverad", 1: "Sabotage", 2: "Antimask" },
      zoneunstableset: { 0: "Inaktiverad", 1: "Sabotage", 2: "Antimask" },
      zoneunstableunset: { 0: "Inaktiverad", 1: "Sabotage", 2: "Antimask" },
    },
    timerNames: {
      intbell: "Interna sirener", extbell: "Externa sirener", extbellstrobe: "Externt siren/blixtljus",
      extbelldelay: "Extern siren fördröjning", chime: "Ding-Dong", confirm: "Bekräfta", confirm_holdup: "Överfallslarm",
      dialer: "Uppringare fördröjning", dialerpartset: "Deltillkoppling uppringningsfördröjning",
      alarm_abort: "Larm Avbrutet", setting_auth: "Tillkopplingstillstånd", finalexit: "Sista utgång",
      fullsetbell: "Siren vid tillkoppling", fullsetstrobe: "Blixtljus vid tillkoppling", failtoset: "Tillkopplingsfel",
      delayed_unset_buzzer: "Fördröjd frånkoppling summertid", doubleknock: "Dubbel aktivering", soak: "Registrering",
      seismic_autotest: "Seismisk testintervall", seismic_test_duration: "Seismisk testtid",
      auto_restore_delay: "Autoåterställningsfördröjning", alarm_lockout_test_duration: "Blockera åtkomst efter larm",
      mains: "Fel 230V AC fördröjning", rf_jam_delay: "RF Störning fördröjning", engtime: "Installatörsläge",
      engautologout: "Installatörs autoutloggning", rkd: "Manöverpanel/Indikering timeout",
      rkd_language: "Manöverpanelsspråk", fire_prealarm: "Brand förlarm", fire_recognition: "Brand upptäckt",
      user_pin_validity_peroid: "Pin giltig", user_pin_changes_limit: "Pin ändringsbegränsning",
      user_pin_change_warning_time: "Pin varning", user_pin_code_lockout: "Kod spärrad",
      user_pin_code_lockout2: "Kod spärrad 2", user_pin_code_lockout_time: "Spärrtid", rfoutputtime: "RF Utgångstid",
      timesynctime: "Tidssynkgräns", net_timeout: "Länk timeout", video_timeout: "Kamera offline", frequent: "Frekvent",
      duress_reset_time: "Aktivera hotkod tyst", holdup_reset_time: "Överfall/Bråklarm tyst",
    },
  },
  en: {
    settings: "Panel settings", standard: "Standard", options: "System options", choices: "Choices",
    timers: "Timers", yes: "Yes", no: "No",
    units: { min: "min", s: "s", h: "h", d: "days", "": "" },
    standardNames: { continent: "Continent", region: "Region", type: "Type", grade: "Grade" },
    optionNames: {
      bellonfirst: "Bells on first alarm", retrigger: "Bell retrigger", open_zones: "Show open zones",
      always_state: "Always show state", autorestore: "Auto restore", coded_restore: "Coded restore",
      keyfob_restore: "Restore by keyfob", restore_on_unset: "Restore on unset", engineer_restore: "Engineer restore",
      bellfts: "Bell on fail to set", strobefts: "Strobe on fail to set", alert_forbid_set: "Forbid set with faults",
      alarmexit: "Alarm on exit", alarm_entry: "Alarm on entry", final_exit: "Continuous final exit",
      offline_tamper: "Offline tamper", alarm_on_ftc: "Alarm on reported fault",
      report_full_engineer: "Report in engineer mode", outputs_full_engineer: "Outputs in engineer mode",
      eng_allow_exit: "Engineer exit", duress_retrigger: "Duress retrigger", panic_retrigger: "Panic retrigger",
      suspicion_audible: "Audible suspicion alarm", seismic_test_on_set: "Seismic test on set",
      callcs_enable: "Message to ARC", hide_bypass_message: "Hide bypass message",
      log_keypad_access: "Log keypad access", offline_cameras: "Show cameras", aex_no_led: "Audio expander LED",
      silence_audio_ver: "Silence on audio verification", reader_leds: "App controls reader LEDs",
    },
    choiceNames: {
      parta_name: "Part set A name", partb_name: "Part set B name", pindigits: "PIN digits", duress: "User duress",
      doormode_set: "Door mode when set", doormode_unset: "Door mode when unset", eol: "End of line",
      zonenobells: "No bells zone attribute", watchdog_output_mode: "Watchdog output mode",
      antimaskset: "Anti-mask when set", antimaskunset: "Anti-mask when unset",
      outofboundset: "Invalid EOL when set", outofboundunset: "Invalid EOL when unset",
      zoneunstableset: "Unstable zone when set", zoneunstableunset: "Unstable zone when unset",
    },
    choiceValues: {
      eol: SPC_EOL_EN,
      continent: { 0: "Europe", 1: "Asia", 2: "North America", 3: "South America", 4: "Oceania" },
      region: { 6: "Sweden" },
      type: { 0: "Domestic", 2: "Financial" },
      grade: { 0: "Installer's configuration" },
      duress: { 0: "Disabled", 1: "PIN +1", 2: "PIN +2" },
      doormode_set: { 0: "Standard", 1: "Card and PIN", 2: "Card or PIN" },
      doormode_unset: { 0: "Standard", 1: "Card and PIN", 2: "Card or PIN" },
      zonenobells: { 1: "No bells", 2: "No internal bell", 3: "No external bell" },
      watchdog_output_mode: { 0: "Disabled", 1: "Enabled", 2: "Pulsed", 3: "Enabled inverted",
        4: "Enabled + reporting (10s)", 5: "Enabled + reporting (60s)" },
      antimaskset: { 0: "Disabled", 1: "Tamper", 2: "Anti-mask", 3: "Alarm" },
      antimaskunset: { 0: "Disabled", 1: "Tamper", 2: "Anti-mask", 3: "Alarm" },
      outofboundset: { 0: "Disabled", 1: "Tamper", 2: "Anti-mask" },
      outofboundunset: { 0: "Disabled", 1: "Tamper", 2: "Anti-mask" },
      zoneunstableset: { 0: "Disabled", 1: "Tamper", 2: "Anti-mask" },
      zoneunstableunset: { 0: "Disabled", 1: "Tamper", 2: "Anti-mask" },
    },
    timerNames: {
      intbell: "Internal bells", extbell: "External bells", extbellstrobe: "External bell/strobe",
      extbelldelay: "External bell delay", chime: "Chime", confirm: "Confirm", confirm_holdup: "Hold-up confirm",
      dialer: "Dialler delay", dialerpartset: "Dialler delay part set", alarm_abort: "Alarm abort",
      setting_auth: "Setting authorisation", finalexit: "Final exit", fullsetbell: "Bell on full set",
      fullsetstrobe: "Strobe on full set", failtoset: "Fail to set", delayed_unset_buzzer: "Delayed unset buzzer",
      doubleknock: "Double knock", soak: "Soak test", seismic_autotest: "Seismic test interval",
      seismic_test_duration: "Seismic test duration", auto_restore_delay: "Auto restore delay",
      alarm_lockout_test_duration: "Access lockout after alarm", mains: "Mains fault delay",
      rf_jam_delay: "RF jamming delay", engtime: "Engineer mode", engautologout: "Engineer auto logout",
      rkd: "Keypad timeout", rkd_language: "Keypad language", fire_prealarm: "Fire pre-alarm",
      fire_recognition: "Fire recognition", user_pin_validity_peroid: "PIN validity",
      user_pin_changes_limit: "PIN change limit", user_pin_change_warning_time: "PIN warning",
      user_pin_code_lockout: "Code lockout", user_pin_code_lockout2: "Code lockout 2",
      user_pin_code_lockout_time: "Lockout time", rfoutputtime: "RF output time", timesynctime: "Time sync limit",
      net_timeout: "Link timeout", video_timeout: "Camera offline", frequent: "Frequent",
      duress_reset_time: "Duress silent", holdup_reset_time: "Hold-up/panic silent",
    },
  },
};

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
