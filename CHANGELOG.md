# Changelog

All notable changes to this repository are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This repository starts from
[minimicro34/ha-spc-flexc](https://github.com/minimicro34/ha-spc-flexc)
v1.1.5-beta.17. For the history before that, see the
[upstream changelog](https://github.com/minimicro34/ha-spc-flexc/blob/main/CHANGELOG.md).

## [2.0.0-beta.6] - 2026-11-26

### Changed

- System alert names are the panel's own, in English and Swedish, as on its
  *Status → System Alerts* page (for example *Controller Mains Fault* /
  *Centralapparat, nätspänningsfel*, *Code Tamper* / *Kod försök*); the
  inhibit and isolate switches and the SPC FlexC System card follow (card
  1.2.13).

## [2.0.0-beta.5] - 2026-11-26

### Changed

- Event names come from the panel's own complete event table: all 608 FlexC
  events, in Swedish when Home Assistant runs in Swedish and otherwise in
  English (`flexc/event_table.py`). This replaces 67 hand-written English
  descriptions, so several names change to the panel's wording (for example
  *Door Forced Open*, *Zone input open*, *Two Way Wireless Panic Alarm*).
  The panel's own event text (`EV_DESC`) is still shown first when an event
  carries it.

### Added

- [docs/EVENT_TABLE.md](docs/EVENT_TABLE.md): every event ID with its English
  and Swedish name, address type, SIA and Contact ID code, read from an
  SPC4300 with firmware 3.14.1.

## [2.0.0-beta.4] - 2026-11-26

### Changed

- Zone device class: the zone type decides only when it says what the
  detector is (fire, glass break, water, ...). Otherwise a word in the zone
  name (English, Swedish, French, also cut at 16 characters) decides, so a door
  contact or window of type *Alarm* is no longer shown as motion. Without a
  word, Alarm zones stay motion and Entry/Exit zones opening. Idea from
  henrikekblad/spc-flexc-home-assistant.
- Zone type 29 is CO (carbon monoxide, device class CO), not CO2; types 12
  (*Unused*) and 17 (*Seismic*, device class vibration) added. The
  `spc_zone_type` attribute says `co` instead of `co2`.

### Added

- [docs/panel-setup.md](docs/panel-setup.md): step-by-step panel setup with
  screenshots, adapted from Henrik Ekblad's guide (MIT licensed).

## [2.0.0-beta.3] - 2026-11-26

### Changed

- One entity per panel fault. When the panel answers `CMD_STATUS_PANEL`, the
  system alert sensors (`binary_sensor.spc_system_alert_mains_fault`,
  `_battery_fault`, `_cabinet_tamper`) are the only ones for mains, battery
  and cabinet tamper; they have the current state from start-up. The
  event-only *Mains fault*, *Battery fault* and *Panel tamper* sensors, which
  stayed *Unknown* until an event arrived, are removed from the entity
  registry. Panels without `CMD_STATUS_PANEL` keep them.
- A mains, battery or panel tamper event (5000/5001, 5006/5007, 5206/5207)
  reads `CMD_STATUS_PANEL` again at once instead of waiting for the next
  minute.
- The not-ready reason when arming reads the same faults from the system
  alerts.

**Upgrading from minimicro34/ha-spc-flexc:** `binary_sensor.*_mains_fault`,
`*_battery_fault` and `*_panel_tamper` disappear on panels that answer
`CMD_STATUS_PANEL`; use the system alert sensors instead.

## [2.0.0-beta.2] - 2026-11-26

Brings in every code change from upstream
[minimicro34/ha-spc-flexc](https://github.com/minimicro34/ha-spc-flexc)
v1.1.5 to v1.1.9, with their tests. Thanks to minimicro34, and to @psyclan for
the key-derived IV investigation.

### Fixed

- Panels that use a key-derived AES IV (seen on SPC4300 firmware 3.12.0) now
  connect: the IV is chosen after SHA-1 validation of an incoming frame and
  reused for the session; the historical IV stays the default (upstream 1.1.6).
- Home Assistant 2026.12 `DeviceInfo` deprecation: the parent device is set as
  a dataclass attribute where supported, with the dictionary form kept for
  older versions (upstream 1.1.9).
- PIR slow-read warnings are not raised during the first 30 seconds of zone
  polling; the readings are still kept in the diagnostic history, now with the
  log level used (upstream 1.1.7 and 1.1.8).

### Changed

- SPC FlexC Card 1.2.12: the PIR diagnostics list shows the log level of each
  slow read.

## [2.0.0-beta.1] - 2026-11-26

### Fixed

- `set_calendar` no longer clears the calendar's times: `EDIT_CALENDAR`
  empties all three week types on the panel, so the times are sent back with
  `EDIT_CALENDAR_WEEK` before the configuration is saved.

- Configuration changes over FlexC (`edit_user`, `add_user`,
  `delete_user`, the profile services, `set_calendar`,
  `set_calendar_week`) are saved with `CMD_SAVE_CONFIG` right after the
  change. Before, the panel restarted within about a minute with
  "configuration checksum invalid" and dropped the change. Checked on the
  panel with a user rename.

- Commands with characters outside ASCII (for example a Swedish calendar
  name) failed before being sent; they are now sent as XML character
  references, as the panel sends them.
- Long FlexC replies (over `0x2800` bytes, for example access, system and
  event logs) arrive complete. Each DATA part is acknowledged with the number
  of bytes received so far. Before, the panel resent the second part until the
  session timed out: the reply was cut off and the commands after it (zone,
  door, X-BUS, Mapping Gate reads) timed out.
- Event `3010` is described as **Door opened**, as the panel reports it, not
  as "Door open too long".
- Doors are named after their zone, because `DOOR_STATUS` has no door name.
- `DOOR_STATUS` fields sent by SPC4300 firmware 3.16 are read:
  `AREA_SIDE_2`, `AREA_SIDE_2_NAME`, `UNLOCK_ALLOWED`, `MOMENTARY_ALLOWED`.
  Door buttons follow these flags.
- Doors found at discovery get their full status at once, not only after the
  first poll.

### Changed

- Wireless: a "Wireless receiver" device with one sensor per wireless
  sensor heard (last heard, signal, battery), the wireless log in
  `get_log`, and the wireless zones on the receiver (chosen in the options).
- The integration follows the panel: when the panel's configuration changes
  (names, zones, doors, areas, X-BUS), it reloads and reads everything
  again. Zones show which board and input they are on.
- Devices follow the installation: X-BUS keypads, I/O expanders and door
  controllers are devices under the panel, doors are devices under their
  door controller, and zones sit on the board their input is on. Areas,
  users, calendars and logs are logical and live on the panel; the former
  area devices are removed. A door's controller can be chosen in the
  options. Entity IDs are unchanged.

- Door words follow the panel: the door mode sensor state `locked` is now
  `blocked` (Blockerad), and the door buttons are Momentary open, Unlock,
  Normal and Block. The access log names types 8 (`forced_open`) and 10
  (`door_blocked`). The lock entity and the four door actions were checked on
  the panel.

- Entity names use translation keys, and the English translation is complete.
- The door mode sensor is an enum with the states Door Normal, Door Locked and
  Door Unlocked.
- Repository metadata, links and code owner point to this repository. The
  upstream signed-release workflow is not included.

### Added

- Activity log: commands HA sends, the panel's answers, panel events and new
  lines of the panel's system and access logs in one timeline. Fired as
  `spc_flexc_activity` (shown in the logbook), kept for 30 days and returned
  by `spc_flexc.get_activity`. Names are shown; PINs and card numbers never.
- `spc_flexc.add_calendar` (name, week types and week type 1 times) and
  `spc_flexc.delete_calendar`, checked on the panel.
- Calendar exception days: read (`exceptions` on the calendar entities, and
  their times replace the week times in the calendar events) and
  `spc_flexc.add_calendar_exception`, `edit_calendar_exception`,
  `delete_calendar_exception`; checked on the panel.
- **Capabilities** diagnostic sensor: every function with its status
  (works, untested, not built, no hardware, refused by the panel, needs an
  engineer login) and what the panel says about the command login.
- Setup explains every field and what the logins are used for.
- **SPC FlexC Activity** card (`custom:spc-flexc-activity-card`): the
  activity log as a live, coloured timeline with filters per source.
- `get_unknown_cards` checked on the panel: `UNKNOWN_CARD` records with
  `DOOR_ID`, `CARD_FORMAT`, `SITE_CODE`, `CARD_NO` (masked),
  `LAST_PRESENTED` and `PRESENTED_COUNT`.

- **Users** sensor (`GET_USER_CONFIG`, read when the user list changes),
  without codes, card numbers or web passwords.
- `spc_flexc.edit_user` (`EDIT_USER`, read-modify-write of name, profiles and
  validity dates; secrets stay unchanged and are never stored).
- `spc_flexc.set_pin`: changes a user's PIN (the panel stores it as the PIN
  XOR a key per user number). Saved with `SAVE_CONFIG` and read back.
  Checked on the panel with a test user.
- Per-user PIN management: `spc_flexc.enable_pin_management` stores a
  user's key with the owner's consent (the current PIN), so `set_pin` needs
  no current PIN and `add_user` can set a PIN; `disable_pin_management`
  forgets it. The Users sensor shows `pin_managed`. Keys are kept in Home
  Assistant's private storage only.
- `spc_flexc.add_user` takes a PIN and `spc_flexc.delete_user` saves the
  configuration; both checked on the panel with a test user.
- **User profiles** sensor (`GET_USER_PROFILE_CONFIG USER_PROFILE_ID="0"`,
  read when users or configuration change) with name, areas, calendar, door
  settings and rights masks of each profile. Checked on the panel.
- `spc_flexc.get_user_status` (`GET_USER_STATUS`): failed PIN attempts, last
  PIN change, number of PIN changes and user alerts. Checked on the panel.
- `spc_flexc.edit_user_profile` (read-modify-write of name, areas, calendar
  and doors), `spc_flexc.add_user_profile` and
  `spc_flexc.delete_user_profile`, checked on the panel with a test profile.
- **Panel settings** diagnostic sensor from `READ_INTRUDER_CFG`, with all of
  the panel's system options and timers (read when the configuration
  changes).
- `spc_flexc.set_calendar` (`EDIT_CALENDAR`: name and week types). Checked on
  the panel.
- `get_log` reads the FlexC ATP log and ATP network log (`atp`,
  `atp_network`; `ATS_ID` + `ATP_SEQ_ID`, verified).
- **Untested, disabled by default:** Silence bells button
  (`CMD_SILENCE_ALL_BELLS`), Inhibit/Isolate switches per system alert
  (`CMD_ALERT_CONTROL`, verified by reading the panel status back) and an ATP
  test call button (`CMD_REQUEST_FLEXC_MANUAL_TEST`).
- Panel calendars as Home Assistant calendar entities (`GET_CALENDAR_CONFIG`,
  read at start-up and after configuration changes).
- `spc_flexc.set_calendar_week` (`EDIT_CALENDAR_WEEK`). Checked on the panel.
- `CMD_STATUS_PANEL` is read with every panel update: one **System alert**
  binary sensor per panel system alert (17, bits mapped on an SPC4300) and an
  **Ethernet** connectivity sensor. If the panel or command profile does not
  allow the command, it is skipped.
- `get_log` also reads the FlexC ATS network log (`ats_network`).
- **Lock** entity per door (lock = Door Normal, unlock = Door Unlocked,
  open = momentary), unlocked while Entry granted is on, open from the door
  contact.
- Optional engineer login in the configuration and reconfiguration dialogs.
  When it is set, an **Engineer mode control** switch enters and exits full
  engineer mode (`CMD_ENTER_FULL_ENGINEER_MODE` / `CMD_EXIT_FULL_ENGINEER_MODE`,
  sent once). An empty login is not stored.
- Diagnostic sensors: **Clock offset** (panel clock minus Home Assistant
  time), **Configuration changed**, **Users changed** and **Active alerts**
  (with the alert list as an attribute).
- Services `spc_flexc.set_clock` (`CMD_SET_CLOCK`, set the panel clock to Home
  Assistant's local time) and `spc_flexc.clear_alerts`
  (`CMD_CLEAR_ALL_ALERTS`). Each command is sent once and its reply checked.
  Not yet re-verified on a panel with this integration.
- `spc_flexc.get_log` service: reads the access (per door), system, zone (per
  zone) or FlexC ATS event log and returns the entries newest first. Card
  numbers are never returned.
- Mapping Gate on/off events (7013/7014) update the Mapping Gate at once.
- Descriptions for events seen on the panel: area set/unset (3501–3504),
  keypad login/logout (4003/4004), network and EDP receiver faults
  (6000/6001, 6008/6009), date changed (7002), engineer mode (7003/7004) and
  Mapping Gate on/off (7013/7014).
- Every panel event is fired as `spc_flexc_event` on the Home Assistant event
  bus, with the panel's text, SIA code, area, zone, door and user, and is
  described in the logbook.
- **Entry granted** binary sensor per door, on for the door's `GRANTED_TIME`
  after event 3000. FlexC does not report the lock relay itself.
- **Door contact** open/closed binary sensor from `DPS_INPUT`.
- `GET_DOOR_CONFIG` is read once per door after discovery, for `GRANTED_TIME`.
- Door events update the door at once: 3007/3008/3009 set the mode,
  3010/3011 set the door position.
- Swedish translation, using the panel's Swedish terms.
- `docs/FLEXC_PROTOCOL.md`: FLEXML envelope, result codes, status, control and
  configuration commands, events and their fields, and the mapping to Home
  Assistant entities, each marked *Checked on panel*, *Re-verify* or *Code
  only*.

### Validation

- Checked against a Vanderbilt SPC4300 with firmware 3.14.1; what is verified
  per function and per FlexC command is in [docs/STATUS.md](docs/STATUS.md)
  and [docs/FLEXC_PROTOCOL.md](docs/FLEXC_PROTOCOL.md).
- 624 automated tests pass; Ruff lint and format checks pass.
