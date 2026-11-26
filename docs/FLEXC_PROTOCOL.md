# FlexC / FLEXML command reference

This page lists the FLEXML commands that SPC FlexC sends to an SPC panel, and
other status and control commands that have been tried on a panel. It is not
an official Vanderbilt specification. Each entry says how much it has been
checked.

**Checked on panel** means a physical SPC panel has answered the command as
described. The *Evidence* column says where the result is recorded: a
captured reply in the tests, a code comment, a Validation section in
`CHANGELOG.md`, or the read-only **baseline of 2026-11-06** (replies captured
through the local probe service). **Re-verify** means an earlier manual
session reported it working, but the result is not recorded and has not been
repeated since. **Code only** means the command is implemented and
unit-tested against sample replies, but no panel result is recorded yet.

Reference panel: SPC4300, firmware 3.14.1 (later 3.16.1), used mainly for
access control.

Commands that read or change users, user profiles, PINs or cards, and how
any of these are encoded, are deliberately left out of this page.

## Envelope

Every request is one authenticated envelope. It can carry one command or a
batch of commands of the same kind:

```xml
<FLEXML_CMD VER="1.0" PANEL_USERNAME="…" PANEL_PASSWORD="…">
  <CMD_GET_ZONE_STATUS ZONE_ID="1" />
  <CMD_GET_ZONE_STATUS ZONE_ID="2" />
</FLEXML_CMD>
```

The username and password belong to the SPC Command Profile user configured
for FlexC. Attribute values are XML-escaped (`flexc/flexml.py`). What a
command may do is limited by the rights of that user on the panel.

Each command `CMD_X` is answered by a `REPLY_X` element inside a
`FLEXML_REPLY` root:

```xml
<FLEXML_REPLY VER="1.0">
  <REPLY_DOOR_CONTROL RESULT="0" CMD_RESULT="OK"></REPLY_DOOR_CONTROL>
</FLEXML_REPLY>
```

Status: **Checked on panel**. The reply above is a captured SPC4300 reply
(`tests/test_flexml.py`). An unknown command is answered with
`<REPLY_[null] RESULT="103" CMD_RESULT="ERROR"/>` (baseline 2026-11-06).

Some control replies also carry a result per object, for example
`<MG_CONTROL MG_ID="1" RESULT="0"/>`. The integration checks that the ID in
the reply matches the request.

### Result codes

`0` and `103` are confirmed by the 2026-11-06 baseline. The other codes were
reported by an earlier manual session and are to be re-verified.

| `RESULT` | Meaning |
| --- | --- |
| `0` | OK (`CMD_RESULT="OK"`) |
| `12`, `102` | Missing or invalid parameter. During discovery, `102` for an ID marks the end of the ID range. |
| `13` | Object not found |
| `15`, `16` | Calendar parameter error |
| `17` | Not available on this panel, or the record is incomplete. Not a permission error. |
| `20` | Nothing to restore (`ZONE_CONTROL` restore on a zone that is not in alarm) |
| `52` | Needs engineer authentication |
| `54` | Authentication failed |
| `75` | Unknown alert (`ALERT_CONTROL` with the alert number instead of the SYSALERT bit) |
| `78` | Not allowed in installer mode (`AREA_CHANGE_MODE`, both logins, 2026-11-13) |
| `65` | Not allowed: the command is not ticked in the ATS's Command Profile (checked 2026-11-13 by unticking `GET_WIRELESS_LOG` for a moment), or the command login lacks the right (e.g. `GRANT_ENGINEER_ACCESS` is ticked but answers `65`) |
| `103` | Unknown command |

The integration treats every non-zero code except `102` during discovery as a
failure and raises `FlexMLReplyError` with the code.

### Transport

FLEXML travels inside FlexC DATA messages (`flexc/connection.py`). An
application reply longer than `0x2800` (10240) bytes is split into several
DATA messages. The first part has the "new message" flag set and the total
application length in its data header; later parts carry `0x2800` there.

Each part must be acknowledged with the **number of application bytes
received so far** (10240, 20480, …, up to the total) in the first four bytes
of the cloned data header. If the panel gets any other value it sends the same
part again until the command times out, and commands queued behind it time
out as well. Status: **Checked on panel** (2026-11-09, a 21811-byte
`GET_FLEXC_ATS_EVENT_LOG` reply arrived in three parts, complete).

## Status reads

| Command | Attributes | Reply element | Used by integration | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| `CMD_GET_PANEL_SUMMARY` | none | `PANEL_SUMMARY` | yes | Checked on panel | baseline 2026-11-06 |
| `CMD_GET_AREA_STATUS` | `AREA_ID` | `AREA_STATUS` | yes | Checked on panel | baseline 2026-11-06, areas 1–4 |
| `CMD_GET_AREA_CHANGE_MODE_STATUS` | `AREA_ID`, `MODE` | `AREA_CHANGE_MODE_STATUS` | yes, precheck before arming | Checked on panel | baseline 2026-11-06 |
| `CMD_GET_ZONE_STATUS` | `ZONE_ID` | `ZONE_STATUS` | yes | Checked on panel | CHANGELOG 1.1.3, 1.1.4 |
| `CMD_GET_DOOR_STATUS` | `DOOR_ID` | `DOOR_STATUS` | yes | Checked on panel | baseline 2026-11-06, doors 1–3 |
| `CMD_GET_MG_STATUS` | `MG_ID` (`0` returns every Mapping Gate) | `MG_STATUS` | yes | Checked on panel | baseline 2026-11-06 |
| `CMD_GET_ALERT_STATUS` | none | one `ALERT` (`EV_ID`, `STATE`) per active alert; none when there are no alerts | yes, Active alerts sensor | Checked on panel | baseline 2026-11-06 (empty) |
| `CMD_STATUS_XBUS` | none | X-BUS device list | yes | Checked on panel | baseline 2026-11-06; CHANGELOG 1.1.1 |
| `CMD_GET_FLEXC_ATS_STATUS` | `ATS_ID` | `FLEXC_ATS_STATUS` with `FLEXC_ATP_STATUS` children | yes | Checked on panel | baseline 2026-11-06 |
| `CMD_GET_ETHERNET_STATUS` | none | `ETHERNET_STATUS` | no | Checked on panel | baseline 2026-11-06 |
| `CMD_GET_MODEM_STATUS` | `MODEM_ID` | | no | Re-verify | |
| `CMD_STATUS_ZONE` | | | no | **Not supported** | baseline 2026-11-06: `RESULT="103"` (unknown command) |

Other read commands found on 2026-11-09 by trying names: `GET_VZONE_STATUS`
accepts `VZONE_ID` (1–3 answer `RESULT="0"` with no data, 40 answers `102`);
`GET_ZONE_CONFIG` answers `RESULT="17"` with or without `ZONE_ID`;
`GET_MODEM_STATUS` and `GET_MODEM_LOG` answer `17` (no modem fitted). These
names answered `103` (unknown): `GET_OUTPUT_STATUS`, `STATUS_OUTPUTS`,
`GET_KEYPAD_STATUS`, `GET_EXPANDER_STATUS`, `GET_TRIGGER_STATUS`,
`GET_SYSTEM_STATUS`, `GET_FAULT_STATUS`, `GET_SIREN_STATUS`,
`GET_LOCK_STATUS`, `GET_MAPPING_GATE_STATUS`, `STATUS_DOORS`, `STATUS_AREAS`,
`STATUS_SYSALERT` and about sixty others. No command for output (relay) state
has been found.

`GET_ZONE_STATUS ZONE_ID="1"` on the reference panel returned `RESULT="0"`
with no `ZONE_STATUS` element (baseline 2026-11-06), so a missing object is
not always reported as `102`.

### Fields seen in the baseline

| Element | Fields |
| --- | --- |
| `AREA_STATUS` | `AREA_ID`, `AREA_NAME`, `MODE`, `PARTSETA_ENABLE`, `PARTSETB_ENABLE`, `PARTSETA_NAME`, `PARTSETB_NAME`, `NOT_READY_SET` or `NOT_READY_UNSET` (a reason code, e.g. `10006`), `INTERNAL_BELLS`, `EXTERNAL_BELLS` |
| `AREA_CHANGE_MODE_STATUS` | `AREA_ID`, `REASON_0` |
| `MG_STATUS` | `MG_ID`, `MG_NAME`, `STATE` |
| `ETHERNET_STATUS` | `FITTED`, `STATE`, `DHCP_ENABLED`, `MAC_ADDRESS`, `IP_ADDRESS`, `NETMASK`, `GATEWAY`, `TX_PACKETS`, `TX_BYTES`, `RX_PACKETS`, `RX_BYTES` |
| `PANEL_SUMMARY` | `SPC_TYPE`, `SPC_VARIANT`, `SPC_SERIAL_NO`, `SPC_FW_VERSION`, `SPC_HW_VERSION`, `SPC_HW_VDS`, `INSTALLATION_ID`, `INSTALLATION_NAME`, `INSTALLATION_DATE`, `INSTALLER_NAME`, `INSTALLER_PHONE`, `SPC_BATT_VOLT`, `SPC_AUX_VOLT`, `SPC_AUX_CURR`, `SPC_AC_FREQ`, `SPC_TIME` (panel clock, `HHMMSSDDMMYYYY`), `SPC_RF_TYPE`, `SPC_RF_VERSION`, `ENG_MODE`, `PARTA_NAME`, `PARTB_NAME`, `PIN_DIGITS`, `INTR_GRADE`, `INTR_REGION`, `GLOBAL_MODE`, `TIME_SYSCFG`/`CRC_SYSCFG` (last configuration change), `TIME_USERS`/`CRC_USERS` (last user change), `LICENSE_KEY`, `MANUFACTURE_ACCESS`, `ENGINEER_ACCESS`, `INTERNAL_BELLS`, `EXTERNAL_BELLS` |
| `FLEXC_ATS_STATUS` | `ATS_ID`, `ATS_NAME`, `REGISTRATION_ID`, `ATP_COUNT`, `ATS_STATUS`, `ATS_STATE`, `EVENT_LOG_COUNT` |
| `FLEXC_ATP_STATUS` | `ATP_SEQ_ID`, `ATP_ID`, `ATP_UID`, `ATP_NAME`, `ATP_STATE`, `ATP_CONNECT_STATE`, `ATP_STATUS`, `LAST_TX_OK_TIMESTAMP` (`HHMMSSDDMMYYYY`) |

Areas, zones and doors are discovered by batching status requests over an ID
range until the panel answers `RESULT="102"`.

The integration also reads each user's **name** (and nothing else) to show who
armed or disarmed an area. That command is outside the scope of this page.

### Configuration reads

| Command | Attributes | Contents | Status |
| --- | --- | --- | --- |
| `CMD_GET_DOOR_CONFIG` (used by the integration) | `DOOR_ID` | `DOOR_CONFIG` (`ATTRIB`, `GRANTED_TIME`, `DENY_TIME`, `OPEN_TIME`, `LEFT_TIME`, `EXT_TIME`, `ESCORT_TIME`, `DOOR_SIDE_1`, `FIRE_AREA`), then one `DOOR_TRIGGER_CONFIG` (`ACTION`, `TRIGGER`, `EDGE`) per trigger | Checked on panel (baseline 2026-11-06) |
| `CMD_GET_CALENDAR_CONFIG` | | Calendars | Re-verify |

All times in `DOOR_CONFIG` are in seconds. `GRANTED_TIME` is how long the
lock relay stays energised after an Entry Granted.

### Logs

| Command | Attributes | Notes | Status |
| --- | --- | --- | --- |
| `CMD_GET_ZONE_LOG` | `ZONE_ID` | `ZONE_LOG_EVENT`: `TIME`, `ZONE_ID`, `INPUT`, `RESISTANCE`; 155 entries for one zone | Checked on panel (2026-11-09) |
| `CMD_GET_ACCESS_LOG` | `DOOR_ID` | `ACCESS_LOG_EVENT`: `TIME`, `TYPE`, `DETAIL`, `DOOR_ID`, `DOOR_NAME`, `USER_ID`, `USER_NAME`, `LOG_TEXT`; oldest first, 901 entries (127 kB) in one reply | Checked on panel (2026-11-09) |
| `CMD_GET_SYSTEM_LOG` | | `SYSTEM_LOG_EVENT`: `TIME`, `TEXT`, `RAW` (16 hex digits); oldest first, 1000 entries | Checked on panel (2026-11-09) |
| `CMD_GET_FLEXC_ATS_EVENT_LOG` | `ATS_ID` | `ATS_EVENT_LOG`: the event fields (see *Event fields*) plus `CID_CODE`, `CID_QUAL`, `KEYPAD_ID`, `KEYPAD_NAME`, `MG_ID`, `MG_NAME`, `ACC_DENIED_REASON`, and for event 3014 `CARD_FORMAT`, `CARD_BIT_COUNT`, `CARD_NUM`; newest first, 100 entries | Checked on panel (2026-11-09) |
| `CMD_GET_MODEM_LOG` | `MODEM_ID` | | Re-verify |

`GET_ACCESS_LOG` entry `TYPE` values; all seen types mapped 2026-11-13 from
the entries' own `LOG_TEXT` and the web page's Passerlogg:

| `TYPE` | Meaning |
| --- | --- |
| `1` | Granted |
| `2` | Denied (`DETAIL` `4` invalid PIN, `6` door locked, `7` invalid card format, `8` card not in the system, `10` outside time/date limit) |
| `5` | Door release (DRS) |
| `6` | Door open too long ("Dörr öppen för länge") |
| `8` | Forced open |
| `9` | Door normal |
| `10` | Door locked (blocked) |
| `11` | Door unlocked |
| `20` | Invalid format |
| `24` | Unknown card ("Okänt kort") |
| `25` | Locked out after wrong codes: the web page shows "Spärrad pga felaktig kod", although `LOG_TEXT` says "Inpassage godkänd" |

### `DOOR_STATUS` fields

Fields sent by the reference panel (baseline 2026-11-06, doors 1–3):
`DOOR_ID`, `DPS_INPUT` (door position), `DRS_INPUT` (door release),
`STATUS`, `MODE`, `READER1_FORMAT`, `READER2_FORMAT`, `ZONE_ID`, `ZONE_NAME`,
`AREA_ID`, `AREA_NAME`, `ENTRY_EXIT`, `LOCK_ALLOWED`, `UNLOCK_ALLOWED`,
`MOMENTARY_ALLOWED`. A door between two areas also has `AREA_SIDE_2` and
`AREA_SIDE_2_NAME`. No door name is sent.

The integration also looks for `DOOR_NAME`/`NAME`, `DOOR_MODE`,
`AREA_SIDE_1`, `AREA_SIDE_1_NAME` and `NORMAL_ALLOWED`, which this panel does
not send, and does not yet read `AREA_SIDE_2`, `UNLOCK_ALLOWED` or
`MOMENTARY_ALLOWED`. All fields are kept unchanged in the `raw` dictionary.

Because no door name is sent, the integration names the door after its zone.

| `DOOR_MODE` | Meaning | Status |
| --- | --- | --- |
| `0` | Normal | Checked on panel |
| `1` | Locked | Checked on panel |
| `2` | Unlocked (free access) | Checked on panel |

The web interface shows these as Door Normal, Door Locked and Door Unlocked
(`sensor.py`). `DOOR_MODE` is the door's *mode*, not the lock relay: in mode
Normal the relay is energised only for `GRANTED_TIME` after an Entry Granted.
See [Pending panel checks](#pending-panel-checks).

### `CMD_GET_AREA_CHANGE_MODE_STATUS` reasons

The reason is sent as `REASON_0`. `0` means the area can change to the
requested mode. `10006` means the panel is in engineer mode (baseline
2026-11-06, panel in engineer mode). Other non-zero values mean the area is not
ready; the integration reports the zone that prevents arming when the panel
names one.

## Control commands

The integration never retries these blindly. It retries only when a fresh
status read proves that the first attempt had no effect.

| Command | Attributes | Values | Used by integration | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| `CMD_AREA_CHANGE_MODE` | `AREA_ID`, `MODE` | `0` Unset, `1` Part Set A, `2` Part Set B, `3` Full Set | yes | Checked on panel | CHANGELOG 1.1.3 |
| `CMD_ZONE_CONTROL` | `ZONE_ID`, `ACTION` | `0` inhibit, `1` de-inhibit, `2` isolate, `3` de-isolate, `4` restore | yes | Checked on panel | CHANGELOG 1.1.3; `tests/test_zone_control.py` |
| `CMD_DOOR_CONTROL` | `DOOR_ID`, `ACTION` | `5` open momentarily, `6` open permanently (unlock), `7` normal, `8` lock | yes | Checked on panel | `tests/test_flexml.py` |
| `CMD_MG_CONTROL` | `MG_ID`, `ACTION` | `0` off, `1` on | yes | Checked on panel | `tests/test_mapping_gates.py` |
| `CMD_CLEAR_ALL_ALERTS` | none | | yes, service `clear_alerts` | Checked on panel | 2026-11-09: `RESULT="0"` (no alerts were active) |
| `CMD_SET_CLOCK` | `TIME="HHMMSSDDMMYYYY"` (local time) | | yes, service `set_clock` | Checked on panel | 2026-11-09: clock offset went from −50 s to −1 s; the panel sent event 7002 |
| `CMD_ENTER_FULL_ENGINEER_MODE` / `CMD_EXIT_FULL_ENGINEER_MODE` | none | | yes, Engineer mode control switch (optional engineer login) | Re-verify | Reported to work only with engineer credentials; otherwise `RESULT="52"`. |

`CMD_DOOR_CONTROL` actions 6, 7 and 8 set `DOOR_MODE` 2, 0 and 1. Action 5 is
a short pulse with no lasting mode to check.

`CMD_GRANT_ENGINEER_ACCESS` and `CMD_REVOKE_ENGINEER_ACCESS` were reported to
return `RESULT="65"` (not allowed). Re-verify.

## Users

Words for logins and modes (user and profile rights, engineer =
Programtekniker, Full/Soft Engineer mode = installatörsläge, global profiles): see `docs/STATUS.md`, *Words for logins and
modes*.

`GET_USER_CONFIG` returns `USER_CONFIG` records with `USER_ID`, `GID`,
`NAME`, `PIN` (encoded), `CARD_NO`, `CARD_ATTRIB`, `USER_ATTRIB`,
`CARD_NO` (decimal, as the web page shows it; `0` = no card), `CARD_ATTRIB` (hex bits, mapped 2026-11-11: `02` extended time, `04` PIN bypass, `08` priority, `10` escort, `20` custodian, `40` card blocked; `01` not seen), `START_DATE`, `END_DATE` (day number, 1 January 2000 = 1; `0` = no date limit; checked 2026-11-11: web page 1 Dec 2026 - 24 Dec 2026 read back as `9832`/`9855`), `LANGUAGE` (7 = Swedish),
`USER_PROFILE_1`…`USER_PROFILE_5` (`0` = unused) and `WEBPASS_DATA`.
`USER_ID="0"` returns all users. `GET_USER_STATUS` returns
`INVALID_PIN_COUNT`, `LAST_PIN_CHANGE`, `PIN_CHANGE_COUNT`, group-side masks
and user alert flags.

`GET_USER_STATUS USER_ID="n"` answers one `GET_USER_STATUS` element (some
attribute names carry a space before `=`): `GROUP_SIDE_MASK`,
`GROUP_SIDE_VALID_MASK`, `INVALID_PIN_COUNT`, `USER_ALERTS_STATE`,
`USER_ALERTS_STATUS`, `USER_ALERTS_ACCEPTED`, `FOB_LOW_BATTERY_COUNT`,
`FOB_LOW_DATE_FIRST`, `LAST_PIN_CHANGE` (`HHMMSSDDMMYYYY`; `...2000` or
`...2015` with day `01` 01 means never) and `PIN_CHANGE_COUNT`.

### User profiles

`GET_USER_PROFILE_CONFIG` needs `USER_PROFILE_ID`; `0` returns every
profile, an unused ID an empty reply, and without the attribute (or with
`ID`, `PROFILE_ID`, `PROFILE`, `USER_PROFILE`) the answer is `102`. Read on
the reference panel 2026-11-10 (six profiles):

```xml
<USER_PROFILE_CONFIG USER_PROFILE_ID="3" GID="0" NAME="..." AREAS="0000000000000003"
  USER_RIGHTS="00000000" USER_RIGHTS2="00000000" CALENDAR="0" SITE_CODE="0"
  DOOR1="2" DOOR3="2" />
```

- `AREAS`: 16 hex digits, bit `n-1` = area `n`.
- `USER_RIGHTS`, `USER_RIGHTS2`: 8 hex digits each, mapped 2026-11-13 (see
  the table below).
- `CALENDAR`: calendar ID, `0` = none. `SITE_CODE` is the web page's site
  code field.
- `DOOR<n>`: the profile's "Passage / Kalender" for door n: `0` = 24 timmar
  (always), `1`-`64` = by that calendar; the attribute is left out for
  "Inget tillträde" (no access). Checked against all six profiles' web
  pages and by setting door 1 to calendar 3 on a test profile (2026-11-13).

Profile rights, mapped 2026-11-13 on a test profile (7) by ticking one right
at a time on the web page (Användare > Användarprofiler > Ändra) and
reading the profile back; the six real profiles match their web pages.

| Bit | Web page (Swedish) |
|---|---|
| `USER_RIGHTS 0x00000001` | Frånkoppla |
| `0x00000002` | Deltillkoppl. A |
| `0x00000004` | Deltillkoppl. B |
| `0x00000008` | Tillkoppla |
| `0x00000010` | Återställ |
| `0x00000020` | Spärra |
| `0x00000040` | Sirentest |
| `0x00000080` | Ding-Dong |
| `0x00000100` | Gångtest |
| `0x00000200` | Ställa in datum |
| `0x00000400` | Läsa logg |
| `0x00000800` | Användare (configure users) |
| `0x00001000` | Installatör (grant installer access) |
| `0x00002000` | Uppgradera (grant upgrade access) |
| `0x00004000` | Webbåtkomst |
| `0x00008000` | X10 |
| `0x00010000` | Ändra PIN (own PIN) |
| `0x00020000` | Tvångstillkoppla |
| `0x00040000` | SMS |
| `0x00080000` | Isolera |
| `0x00100000` | Fördröj autotillkoppling |
| `0x00200000` | Dörrkontroll (lock/unlock doors) |
| `0x00400000` | Utgångar |
| `0x00800000` | Förbikopplarfördröjning |
| `0x01000000` | WPA Test |
| `0x04000000` | Visa video |
| `0x08000000` | RF utgång |
| `0x10000000` | Seismisk test |
| `0x20000000` | Skapa Anv [master] (change every user) |
| `0x40000000` | Skapa Användarprofiler |
| `0x80000000` | Skapa Kalender |
| `USER_RIGHTS2 0x00000001` | Skapa Dörrar |
| `USER_RIGHTS2 0x00000002` | Nivå 3 åtkomst |

Not seen: `USER_RIGHTS 0x02000000`. The integration's `add_user_profile`,
`edit_user_profile` and `delete_user_profile` services were run on test
profile 7 on 2026-11-13 (edit name, areas and a door; delete; add; delete)
and each change showed at once on the web page and over FlexC.

`EDIT_USER_PROFILE`, `ADD_USER_PROFILE` and `DELETE_USER_PROFILE` are built
the same way as the user commands (whole record / ID only) and work
(checked 2026-11-10 with a new profile 7).

`ADD_USER` works with the whole record and the PIN encoded with the key of
that user number (checked 2026-11-10 on test user 65, followed by
`SAVE_CONFIG`); the reply carries `<USER_RESULT USER_ID="65" RESULT="0"/>`.
The key stays the same for a user number across delete and add, so it can be
learned once from a known code. `DELETE_USER USER_ID` + `SAVE_CONFIG` works.
`59` means the PIN was encoded with the wrong key.

Earlier tries: `ADD_USER` (not working then): `12` without `USER_ID`, `17` without `PIN`,
`59` with a `PIN` in any format tried. `PIN` is stored as 8 hex digits, the
PIN as an integer XOR a key that belongs to the user number. See `docs/STATUS.md`.

**Save every configuration change:** send `CMD_SAVE_CONFIG` (no attributes)
right after `EDIT_USER`, `ADD_USER`, `EDIT_CALENDAR` and the other
configuration commands. Without it the change stays in memory only, the
panel logs "configuration checksum invalid" within about a minute, restarts
and reloads the last saved configuration (checked on the reference panel,
2026-11-10; see `docs/STATUS.md`). With it the log shows
"Sparar centralens konfiguration" and the change stays. `RESULT="56"` was
seen once while such a restart began (the new name was also used by
another user).

`EDIT_USER` needs the whole record (a partial one answered `17` in an earlier
session). Send it back without `WEBPASS_DATA`: the web password is tied to the
user name, and leaving it out keeps the web login working. Renaming a user
breaks its web login until it is renamed back.

## Calendars

`GET_CALENDAR_CONFIG` without attributes returns all calendars (checked on
panel, 2026-11-10):

```xml
<CALENDARS>
  <CALENDAR ID="2" GID="0" NAME="..." WEEK_TYPES="1111...1" />
  <CALENDAR_WEEK CALENDAR="2" WEEK="1" SUN="06:00;23:00" MON="06:00;23:00" ... />
  <CALENDAR_WEEK CALENDAR="2" WEEK="2" SUN="" ... />
  <CALENDAR_WEEK CALENDAR="2" WEEK="3" SUN="" ... />
</CALENDARS>
```

`WEEK_TYPES` has one digit per week of the year (53) giving the week type
(1–3) for that week. A day holds periods `start;end` separated by spaces;
`--:--` as end means no end time (the web interface shows a single time);
`24:00` is the end of the day. Exception days were not present on the
reference panel, so their element is not known.

`EDIT_CALENDAR_WEEK` takes the same attributes as a `CALENDAR_WEEK` row:
`CALENDAR`, `WEEK` and all seven days (checked on panel 2026-11-10: an entry
in the unused week type 3 was written, read back and cleared).
`EDIT_CALENDAR` takes the attributes of a `CALENDAR` element: `ID`, `GID`,
`NAME` and `WEEK_TYPES` (checked: a calendar was renamed and renamed back,
including a name with "ä"). Names outside ASCII are sent as XML character
references (`&#228;`), as the panel sends them.

The reference panel allows **at most 4 calendars** and has 4 (the web
interface says so when "Lägg till" is pressed, 2026-11-10). That explains
`13` for `ADD_CALENDAR` with `ID` 5, 6 or 64: there is no free calendar.
**`DELETE_CALENDAR ID` and `ADD_CALENDAR ID GID NAME WEEK_TYPES` work**
(checked 2026-11-10: calendar 4 deleted and added again with the same
number, then its week times set with `EDIT_CALENDAR_WEEK`, then
`SAVE_CONFIG`; the result matched a copy taken before). A new calendar has
no times, so `add_calendar` sends them right after. The web interface gives a
new calendar the first free number and sends `name` and `week1..week53`.
Deleting a calendar may drop it from doors, areas or profiles that use it.

**Exception days** (checked 2026-11-10; the owner made one in the web
interface, then it was edited, deleted and added again over FlexC, each
followed by `SAVE_CONFIG`). `GET_CALENDAR_CONFIG` returns one element per
exception:

```xml
<CALENDAR_EXCEPT ID="1" GID="0" NAME="..." START="010127" END="010127"
  TIMES="13:00;14:00" CALENDARS="0D00000000000000" />
```

- An exception is shared: `CALENDARS` is a 16-hex-digit mask, byte n-1
  from the left for calendars 8(n-1)+1..8n, lowest bit first
  (`0D...` = calendars 1, 3 and 4).
- `START`/`END` are `DDMMYY`; the panel sets `END` to `START` when the end
  is earlier. `TIMES` uses the week-day period format, at most 4 periods
  (the web form has `on1..4`/`off1..4`).
- `ADD_CALEX` and `EDIT_CALEX` take all these attributes; `DELETE_CALEX`
  takes `ID`. The web form sends `name`, `day1/month1/year1`,
  `day2/month2/year2` (month from 0), `on1..4`, `off1..4`, `cal<n>=1`.

Earlier tries without these attributes:

| Command | Attributes sent | `RESULT` |
| --- | --- | --- |
| `ADD_CALENDAR` | `NAME`, with or without `WEEK_TYPES`, `GID`, `CALENDAR` | `15` |
| `ADD_CALENDAR` | `ID` (0) + `NAME` | `15` |
| `ADD_CALENDAR` | `ID` (5, 6 or 64) + `NAME` (+ `GID`, `WEEK_TYPES`) | `13` |
| `ADD_CALEX` | none, `CALENDAR`, `CALENDAR` + `DATE`, `CALENDAR` + `START` + `END` | `12` |
| `ADD_CALEX` | `ID` = 2 | `16` |

## Zone configuration

Tests on 2026-11-10, all against zone 999, which does not exist, so no zone
could change:

| Command | Login | Engineer mode | `RESULT` |
| --- | --- | --- | --- |
| `EDIT_ZONE ZONE_ID="999"` | command user | off | `65` (not allowed) |
| `EDIT_ZONE ZONE_ID="999"` | command user | on | `65` |
| `EDIT_ZONE ZONE_ID="999"` | engineer | off | `65` |
| `EDIT_ZONE ZONE_ID="999"` | engineer | **on** | **`12`** (missing parameters) |
| `GET_ZONE_CONFIG`, with `ZONE_ID` 25, 0 or none | command user or engineer | off or on | `17` |

So `EDIT_ZONE` is accepted only from an engineer login while the panel is in
full engineer mode (`ENTER_FULL_ENGINEER_MODE`, also over FlexC). The zone
is given as **`ID`**: with `ZONE_ID` the answer stays `12` whatever else is
sent (`NAME`/`ZONE_NAME`, `TYPE`/`ZONE_TYPE`, `AREA_ID`/`AREA`), while
`ID="999"` + `NAME` answers `16` (invalid value: zone 999 does not exist).
The other attributes can only be found with a real zone. `GET_ZONE_CONFIG` is not supported on firmware
3.14.1 (`17` in every case), so the current settings cannot be read back
before an edit; `GET_ZONE_STATUS` gives only name, type, area and the
inhibit/isolate permissions. Until the attributes are known, never send
`EDIT_ZONE` for a real zone: an incomplete record may overwrite settings, as
`EDIT_HOLDUP_CONFIG` did.

Next step: only on an unused zone, with the owner's go-ahead, because a
partial record may overwrite that zone's settings.

### EDIT_ZONE (found 2026-11-13)

`EDIT_ZONE` takes the **whole record as `GET_ZONE_CONFIG` returns it**, with
the zone given as `ID`:

```xml
<CMD_EDIT_ZONE ID="40" TYPE="9" NAME="..." ATTRIB="00000080" KEYARM_FUNC="3"
  AREA="1" TECHDELAY="50" />
```

- Only the engineer login with the panel in installer mode may send it;
  otherwise `65` (command login in either mode, engineer in normal mode).
- An accepted change gets an **empty `<FLEXML_REPLY>` without a reply
  element**. `SAVE_CONFIG` must follow, as for every configuration change.
  (Earlier tries with `ID` sent the unchanged record, so the empty reply
  looked like a failure.)
- A record with a field missing (`ID` plus one field) is refused with `17`
  and changes nothing, so a partial record cannot overwrite settings.
- With `ZONE_ID` instead of `ID` the answer is `12`.
- Checked on the virtual zone 40, one field at a time, each read back and
  set back: `NAME`, `TYPE` (9 to 0), `ATTRIB` (`log` bit), `AREA` (1 to 2),
  `KEYARM_FUNC` (3 to 1), `TECHDELAY` (49 to 50). The system log shows
  `GET_ZONE_CONFIG` too as "Ändra sektionskonfigurering".
- The integration's `edit_zone` reads the record, changes only the given
  fields, sends it whole with the engineer login, saves and reads it back;
  `get_zone_config` returns the record with type, attributes and key-arm
  function by name.

**Update 2026-11-11: `GET_ZONE_CONFIG` works with `ID`** (not `ZONE_ID`),
with the normal command login and engineer mode off. Without an attribute it
answers `17`. Reply:

```xml
<REPLY_GET_ZONE_CONFIG RESULT="0" CMD_RESULT="OK"><ZONES>
  <ZONE ID="25" TYPE="1" NAME="..." ATTRIB="00000484" KEYARM_FUNC="3"
        AREA="1" TECHDELAY="0" />
</ZONES></REPLY_GET_ZONE_CONFIG>
```

Read for all 18 zones of the reference panel. `KEYARM_FUNC` was 3 on every
zone; `TECHDELAY` 0 except the virtual zone (49). These are most likely the
fields `EDIT_ZONE` takes, so an edit can send the whole record read back
with one field changed.

Mapped 2026-11-13 against the web page (Konfiguration > Ingångar), by
changing one attribute at a time on the web page, reading the zone back
over FlexC and setting it back; all 18 zones match their web pages.

`TYPE` is the web page's Sektionstyp value: 0 Larm, 1 In/utpassering,
2 Utpasseringstid, 3 Brand, 4 Nödutgång, 5 Linje, 6 Bråklarm, 7 Överfall,
8 Sabotage, 9 Tekniskt larm, 10 Medicinskt, 11 Nyckeltillkoppling,
12 Används ej, 13 Förbikopplare, 14 X-förbikopplare, 15 Detektorfel,
16 Låskontroll, 17 Seismisk, 18 Allt OK, 19 Överfall fel, 20 Varning fel,
21 Tillkopplingstillstånd, 22 Lås element, 23 Glaskross, 24 Vatten,
25 Värme, 26 Kyl/frys, 27 Gas, 28 Sprinkler, 29 CO, 30 In/utpassering 2.

`KEYARM_FUNC` (key-arm zones): 3 Tillkoppla, 1 Deltillkoppling A,
2 Deltillkoppling B. `TECHDELAY` is the web page's delay field on
technical zones.

`ATTRIB` bits (the web page shows only the attributes of the zone's type):

| Bit | Web page (Swedish) | Meaning |
|---|---|---|
| `0x00000001` | Följande | access (follows entry/exit timer) |
| `0x00000002` | Uteslut A | excluded in partset A |
| `0x00000004` | Uteslut B | excluded in partset B |
| `0x00000008` | 24 timmar | alarms in every mode |
| `0x00000010` | Lokal | alarm not reported |
| `0x00000020` | Dubbel aktivering | double knock |
| `0x00000040` | Ding-Dong | chime |
| `0x00000080` | Spärra | user may inhibit |
| `0x00000100` | Normalt öppen | detector normally open |
| `0x00000200` | Tyst | silent |
| `0x00000400` | Logg | log every state change |
| `0x00000800` | Endast öppen | key arm on open only (pulse) |
| `0x00001000` | Endast rapport | fire: report only |
| `0x00002000` | Sista utgång | final exit |
| `0x00004000` | Tillkoppling aktiverad | key arm sets |
| `0x00008000` | Frånkoppling aktiverat | key arm unsets |
| `0x00010000` | Förbikopplare | inhibited by an active shunt zone |
| `0x00020000` | Rapport | report open/close |
| `0x00040000` | Visa | show on keypad |
| `0x00080000` | Hörbar | keypad buzzer |
| `0x00200000` | Rapportera vid tillkopplad | report open/close when set |
| `0x00400000` | Frekvent | must open within the frequent period |
| `0x00800000` | Förlarm | fire pre-alarm |
| `0x01000000` | Upptäckt | fire recognition time |
| `0x02000000` | Nödutgång öppen | shown open when setting |
| `0x08000000` | Frånkoppling lokalt | report only when set |
| `0x10000000` | Fördröjd | key arm delayed |
| `0x20000000` | TVÅNGSTILLKOPPLA | forced set allowed |
| `0x40000000` | Automatisk återställning | auto restore |
| `0x80000000` | Ingen siren | no bells |

Not seen: `0x00100000`, `0x04000000`. The web page's zone list posts to
`secure.htm?page=zones&action=update&zone=1` (`att_editN` opens zone N's
attributes); the attribute form posts every field with `save=Spara` to
`secure.htm?page=zones&action=update&zone=N&att=1`.

## Command catalogue

The panel's **Command Profile** page (engineer web interface, Communications →
FlexC → Command Profile) lists every FlexC command the panel knows, with one
checkbox to allow it and one to log it. The checkbox names
(`chk_cmd_en_<COMMAND>`) give the exact command names; there are 105. The
table groups them as the page does and says what this integration does with
each. Results are from the reference panel on 2026-11-10.

Status words used below:

- **used** – implemented and checked on the panel;
- **used, untested** – implemented from a qualified guess, not yet run on a
  panel (entities disabled by default);
- **not built** – the command exists (name known from the panel), but the
  integration does not implement it and it is untested. Anyone may build it;
  the *Status* text says what is known, including any risk (for example that
  a command could switch FlexC off or reset the panel);
- **not available** – the reference panel lacks the hardware.

| Group | Command | Page label | Status |
| --- | --- | --- | --- |
| System | `GET_PANEL_SUMMARY` | Get Panel Summary | used |
| System | `SET_CLOCK` | Set the System Time and Date | used (`set_clock`) |
| System | `GRANT_ENGINEER_ACCESS`, `REVOKE_ENGINEER_ACCESS` | Grant / Revoke Engineer Access | not built. `GRANT` answers `65` with the command login and with the engineer login (2026-11-13), although it is ticked in the Command Profile: granting is the user right "Installatör" (`USER_RIGHTS 0x1000`), and the command login is not a panel user with a profile. `REVOKE` not sent (it could lock out the engineer) |
| System | `GRANT_MANU_ACCESS`, `REVOKE_MANU_ACCESS` | Grant / Revoke Manufacturing Access | not built; never sent |
| System | `ENTER_FULL_ENGINEER_MODE`, `EXIT_FULL_ENGINEER_MODE` | Enter / Exit Full Engineer Mode | used (engineer login) |
| Intruder | `GET_AREA_STATUS` | Get the Area Status | used |
| Intruder | `GET_AREA_CHANGE_MODE_STATUS` | Get the Change Mode Status of an Area | used |
| Intruder | `AREA_CHANGE_MODE` | Change the mode (Set/Unset) of an Area | used |
| Intruder | `GET_ALERT_STATUS` | Get Status of Panel Alerts | used |
| Intruder | `ALERT_CONTROL` | Perform actions on Alerts | used (Inhibit/Isolate switches, enabled by default since 2026-11-13). Checked 2026-11-13 on the network fault: `ALERT_ID` is the **SYSALERT bit** (24), not the alert number (38 answers `75`); `ACTION` 0 inhibit, 1 de-inhibit, 2 isolate, 3 de-isolate, each seen in `STATUS_PANEL` and set back |
| Intruder | `SILENCE_ALL_BELLS` | Silence Bells | used (Silence bells button); answers `0` without attributes (2026-11-13, no bells were sounding) |
| Intruder | `GET_ZONE_STATUS` | Get Zone Status | used |
| Intruder | `ZONE_CONTROL` | Control a Zone | used |
| Intruder | `GET_SYSTEM_LOG` | Get the System Log | used (`get_log`) |
| Intruder | `GET_ZONE_LOG` | Get the Log for a Zone | used (`get_log`) |
| Intruder | `GET_WIRELESS_LOG` | Get the Wireless Log | used (`get_log` `wireless`, wireless sensors); needs any `SENSOR_ID` (ignored; `102` without), returns `WIRELESS_LOG_EVENT SENSOR_ID TIME STATUS BATTERY SIGNAL RECEIVER_ID` for all sensors; checked 2026-11-11 |
| Intruder | `GET_HOLDUP_CONFIG`, `EDIT_HOLDUP_CONFIG` | Get / Edit Hold-up DATA | not built. `GET_HOLDUP_CONFIG` answers `0` (hold-up keywords and phone numbers). `EDIT_HOLDUP_CONFIG` without attributes overwrote the fields in an earlier session; send the full record read back if it is ever built |
| Output | `GET_MG_STATUS` | Get Mapping Gate Status | used |
| Output | `MG_CONTROL` | Control Mapping Gates | used |
| User | `GET_USER_CONFIG` | Get the configuration of a User | used (Users sensor; `USER_ID="0"` lists all) |
| User | `EDIT_USER` | Edit a User | used (`edit_user`, read-modify-write without `WEBPASS_DATA`) |
| User | `ADD_USER`, `DELETE_USER` | Add / Delete a User | `DELETE_USER` used (`delete_user`, checked); `ADD_USER` checked with an encoded PIN through the probe, integration service still without PIN |
| User | `GET_USER_PROFILE_CONFIG` | Get user profile configuration | used (User profiles sensor); needs `USER_PROFILE_ID` (`0` = all), `102` without it |
| User | `EDIT_USER_PROFILE`, `ADD_USER_PROFILE`, `DELETE_USER_PROFILE` | Edit / Add / Delete a user profile | used (`edit_user_profile` read-modify-write, `add_user_profile`, `delete_user_profile`); checked on panel 2026-11-10 with `SAVE_CONFIG` |
| User | `GET_USER_STATUS` | Get user status | used (`get_user_status`); `USER_ID` |
| User | `GET_UNKNOWN_CARDS` | Get unknown cards | used (`get_unknown_cards`, no attributes; checked 2026-11-10): `UNKNOWN_CARD` with `DOOR_ID`, `CARD_FORMAT`, `SITE_CODE`, `CARD_NO`, `LAST_PRESENTED` (`DD/MM/YYYY HH:MM`), `LAST_PRESENTED_TS14`, `PRESENTED_COUNT`; card number, format and site code are masked |
| User | `VERIFY_USER_ON_PANEL` | Verify a user on the panel | used (engineer login: the panel must answer `ENGINEER="1"`). Checks the login it is sent with, not a PIN: the command login answers `USER_ID="9995" ENGINEER="0"`, the engineer `USER_ID="9999" ENGINEER="1"`; `USER_ID`/`PIN` attributes are ignored |
| User | `CHANGE_USERS_OWN_PIN` | Change own PIN | not built; answered `16` with plain and encoded PINs; `set_pin` (`EDIT_USER`) is used instead |
| User | `CLEAR_ALL_ALERTS` | Clear all alerts | used (`clear_alerts`); the system log calls it "Återställ alla larm" (reset all alarms) |
| Calendar | `GET_CALENDAR_CONFIG` | Get the configuration of a Calendar | used (calendar entities); checked on panel |
| Calendar | `EDIT_CALENDAR_WEEK` | Edit a Calendar Week | used (`set_calendar_week`); checked on panel 2026-11-10 (unused week type 3 set and cleared) |
| Calendar | `EDIT_CALENDAR` | Edit a Calendar | used (`set_calendar`); checked on panel 2026-11-10 with `ID`, `GID`, `NAME`, `WEEK_TYPES` and `SAVE_CONFIG`. **It clears the times of all three week types**, so `set_calendar` sends them back with `EDIT_CALENDAR_WEEK` before saving |
| Calendar | `ADD_CALENDAR`, `DELETE_CALENDAR` | Add / Delete a calendar | used (`add_calendar`, `delete_calendar`); checked on panel 2026-11-10; at most 4 calendars on the reference panel |
| Calendar | `ADD_CALEX`, `EDIT_CALEX`, `DELETE_CALEX` | Exception-day changes | used (`add_calendar_exception`, `edit_calendar_exception`, `delete_calendar_exception`); checked on panel 2026-11-10 |
| Communication | `GET_ETHERNET_STATUS` | Get the status of the Ethernet | not built (the same data comes from `STATUS_PANEL`) |
| Communication | `GET_MODEM_STATUS`, `GET_MODEM_LOG` | Modem status and log | not available (`17`, no modem) |
| Communication | `GET_ARC_LOG` | Get the log for an ARC receiver | not available (`17`) |
| FlexC | `GET_FLEXC_ATS_STATUS` | Get the status of a FlexC ATS | used |
| FlexC | `GET_FLEXC_ATS_NETWORK_LOG` | Get the Network Log for a FlexC ATS | used (`get_log`); `ATS_ID` (`ATS_NETWORK_LOG`: `ATS_ID`, `MSG_ID`, `TIMESTAMP`, `NETWORK_LOG_MESSAGE`) |
| FlexC | `GET_FLEXC_ATS_EVENT_LOG` | Get the Event Log for a FlexC ATS | used (`get_log`) |
| FlexC | `GET_FLEXC_ATP_LOG`, `GET_FLEXC_ATP_NETWORK_LOG` | ATP log and network log | used (`get_log`); checked on panel with `ATS_ID` + `ATP_SEQ_ID` (`ATP_LOG`: `MSG_ID`, `DATA`, `TIMESTAMP`, `ATP_LOG_MESSAGE`; `ATP_NETWORK_LOG`: `MSG_ID`, `TIMESTAMP`, `NETWORK_LOG_MESSAGE`) |
| FlexC | `EXPORT/IMPORT_FLEXC_ATS_FILE`, `DELETE_FLEXC_ATS`, `DELETE_FLEXC_ATP`, `DELETE_EVENT_PROFILE`, `DELETE_FLEXML_PROFILE`, `REQUEST_FLEXC_UPDATE_ENCKEY` | FlexC administration | not built; risk: deleting ATS/ATP/profiles or replacing the key can switch FlexC off |
| FlexC | `REQUEST_FLEXC_MANUAL_TEST` | Request a testcall for a FlexC ATP | used (test call button); answers `0` with `ATS_ID` + `ATP_SEQ_ID` (2026-11-13, ATS 2 ATP 1) |
| Access control | `GET_DOOR_CONFIG` | Get the Configuration for a Door | used |
| Access control | `GET_DOOR_STATUS` | Get the Status of a Door | used |
| Access control | `DOOR_CONTROL` | Control a Door | used |
| Access control | `GET_ACCESS_LOG` | Get the Access Log | used (`get_log`) |
| Camera | `GET_CAMERA_IMAGE` | Get a Camera Image | not available (`102`; no camera) |
| Verification | `GET_VZONE_STATUS`, `GET_VZONE_DATA`, `SEND_VZONE_DATA` | Verification zones | not available (no verification zones configured) |
| Virtual keypad | `VIRTUAL_KEYPAD_CONTROL` | Control keypad (web page: "Virtuell manöverpanel kommandon – Styr MAP") | not built; not available on the reference panel: answers `17` without attributes and with `KEYPAD_ID`, `ID`, `KEYPAD`, `XBUS_ID`, `NODE_ID`, `KEY`, `ACTION` or `CMD`, with the command and the engineer login, in normal and installer mode (2026-11-13). The web page has no virtual keypad setting (only the two X-BUS keypads, MAP Huset 1 and MAP Garaget 2) and the licence page lists no options. It is ticked in the SPC Connect command profile, so it may only work through an SPC Connect ATS |
| File | `SAVE_CONFIG` | Save the panel configuration | used: sent without attributes after every configuration change; checked on the panel 2026-11-10 (log: "Sparar centralens konfiguration") |
| File | `UPGRADE_PANEL_FIRMWARE`, `UPGRADE_PERIPHERAL_FIRMWARE`, `UPLOAD_FILE`, `DOWNLOAD_FILE`, `RESET_PANEL` | File and reset commands | not built; risk: firmware, configuration files and panel reset |
| Legacy | `STATUS_PANEL` | Get Panel Status | used (system alert and Ethernet sensors); `SYSINFO`, `PSU`, `SYSALERT` masks, `MODEM`, `ETHERNETINFO` |
| Legacy | `READ_PANEL_INFO` | Get Panel Info | not built; answers `0` (`INFO`) |
| Legacy | `READ_CONFIG_HEADERS` | Get Headers of Configuration Files | not built; answers `0` (`TIME_SYSCFG`, `CRC_SYSCFG`, `TIME_USERS`, `CRC_USERS`) |
| Legacy | `READ_LANG_CFG` | Get Language Configuration | used (installed languages for users); answers `0` (`LANGUAGE_STATUS`) |
| Legacy | `READ_INTRUDER_CFG` | Get Intruder Configuration | used (Panel settings sensor); `INTRUDER` with system options and timers |
| Legacy | `READ_AREAS_CFG` | Get the Area Configuration | not built; `12` without attributes |
| Legacy | `STATUS_XBUS` | Get Status of X-BUS Devices | used |
| Legacy | `RECONFIG_XBUS` | Reconfiguration Xbus | not built; risk: re-addresses the X-BUS devices |
| Legacy | `ADD/EDIT/DELETE/GET_USER_PACE`, `_FOB`, `_SMS`, `_TWW_TAG`, `GET_UNKNOWN_*` | User devices | not built. 2026-11-13: `GET_USER_FOB/PACE/SMS/TWW_TAG_CONFIG USER_ID` answer `17` (no hardware or modem); `GET_UNKNOWN_FOB/PACE/TWW_TAG_CONFIG` answer `0` with an empty list |
| Legacy | `EDIT_ZONE`, `GET_ZONE_CONFIG` | Edit Zone / Edit Zone Config | used (`edit_zone`, `get_zone_config`); checked 2026-11-13, see *EDIT_ZONE (found 2026-11-13)* |

### System alerts in `STATUS_PANEL`

`SYSALERT` carries four 32-bit hex masks (`INPUT`, `ALERT`, `INHIBIT`,
`ISOLATE`) and `INHIBIT_ALLOWED_<bit value>` / `ISOLATE_ALLOWED_<bit value>`
flags. The bit of each alert was mapped on the reference panel (2026-11-04,
over EDP, by inhibiting each alert); it is not the alert's ID.

| Alert ID | Bit | Alert |
| --- | --- | --- |
| 0 | 0 | Controller Mains Fault |
| 1 | 1 | Controller Battery Fault |
| 2 | 21 | Controller PSU Fault |
| 3 | 2 | Controller Aux. Fuse Fault |
| 4 | 3 | Controller External Bell Fuse Fault |
| 5 | 4 | Controller Internal Bell Fuse Fault |
| 6 | 5 | Bell Tamper |
| 7 | 6 | Controller Cabinet Tamper |
| 8 | 7 | Controller Aux. Tamper 1 |
| 9 | 8 | Controller Aux. Tamper 2 |
| 10 | 9 | Controller Antenna Tamper |
| 11 | 10 | Controller RF Jamming |
| 16 | 16 | Fail to communicate |
| 20 | 15 | X-BUS Cable Fault |
| 36 | 22 | Code Tamper |
| 37 | 23 | Ethernet link |
| 38 | 24 | Network Fault |

## Unsolicited events

The names, address types, SIA and Contact ID codes of all 608 event IDs, as
the panel lists them, are in [EVENT_TABLE.md](EVENT_TABLE.md).

The panel pushes `EVENT` records with an `EV_ID` and, depending on the event,
`AREA_ID`, `ZONE_ID` or `DOOR_ID`. The integration keeps only these numeric
identifiers. It does not store or log other event fields, because they can
contain user details.

*Seen on panel* means an earlier session saw the event in the panel's FlexC
ATS event log; these are to be re-verified by receiving them in the
integration. *Checked on panel* means it is recorded in `CHANGELOG.md` or the
baseline.

### Area and intrusion

| `EV_ID` | Meaning | Status |
| --- | --- | --- |
| 1000, 1001 | Intrusion alarm (1001 is also sent for a zone confirmed in alarm after entry delay) | Code only |
| 3501 | Area unset | Seen on panel (CHANGELOG) |
| 3502 | Area Part Set A | Seen on panel |
| 3503 | Area Part Set B | Code only |
| 3504 | Area Full Set | Seen on panel (CHANGELOG) |

### Zones

| `EV_ID` | Meaning | Status |
| --- | --- | --- |
| 2100, 2101 | Zone input active / restored (open / closed) | Seen on panel |

### Doors

| `EV_ID` | Meaning (SIA code) | Status |
| --- | --- | --- |
| 3000 | Entry granted (DG) | Checked on panel (2026-11-06) |
| 3001 | Entry denied (DD) | Seen on panel |
| 3002 | Exit granted | Code only |
| 3003 | Exit denied | Code only |
| 3004 | Door open too long | Code only |
| 3005 | Door left open | Code only |
| 3006 | Door forced | Code only |
| 3007 | Door mode Normal | Seen on panel |
| 3008 | Door mode Locked | Seen on panel |
| 3009 | Door mode Unlocked | Seen on panel |
| 3010 | Door opened (door position input became open) | Checked on panel (2026-11-06) |
| 3011 | Door closed | Checked on panel (2026-11-06) |
| 3012 | Door release: the exit button (REX/DRS) was pressed (DX); the integration then refreshes that door's status. Leaving through the door normally gives 3012 and 3010 almost at once. | Checked on panel (2026-11-06) |
| 3013 | Door alarm restored | Code only |
| 3014 | Unknown card | Code only |
| 3015 | Reader locked | Code only |
| 3016 | Reader unlocked | Code only |

### Users, panel and communication

| `EV_ID` | Meaning | Status |
| --- | --- | --- |
| 4003, 4004 | User logged in / out at a keypad; fields `USER_ID`, `USER_NAME`, `KEYPAD_ID`, `KEYPAD_NAME`, `AREA_ID`, `AREA_NAME` (only `USER_ID` is used, to confirm a PIN key) | Checked on panel (2026-11-10) |
| 5312 | X-BUS physical tamper fault | Checked on panel (CHANGELOG 1.1.1) |
| 5314, 5315 | X-BUS tamper inhibited / de-inhibited | Checked on panel (CHANGELOG 1.1.1) |
| 5316, 5317 | X-BUS tamper isolated / de-isolated | Checked on panel (CHANGELOG 1.1.1) |
| 6000, 6001 | Network fault / restored | Seen on panel |
| 6008, 6009 | EDP receiver down / up | Seen on panel |
| 7002 | Date and time changed (after `CMD_SET_CLOCK`, with the command user as `USER_ID`) | Checked on panel (2026-11-09) |
| 7003, 7004 | Engineer mode on / off | Seen on panel |
| 7011 | Configuration changed | Seen on panel |
| 7013, 7014 | Mapping Gate on / off | Seen on panel |

### Event fields

Door event fields received on 2026-11-06 (`EV_ID` 3000, 3010, 3011, 3012):
`EV_ID`, `EV_SEQ`, `EV_GRP`, `EV_DESC` (text in the panel's language),
`TIMESTAMP` (`HHMMSSDDMMYYYY`, panel clock), `DOOR_ID`, `DOOR_NAME`,
`AREA_ID`, `AREA_NAME`, and on most events `SIA_CODE` and `SIA_ADDRESS`.
Entry Granted (`3000`) also carries `USER_ID` and `USER_NAME`; the
integration does not keep them. Unlike `DOOR_STATUS`, door events carry the
door's name.

Sequence for one card at door 3: `3000` and `3012` with the same timestamp,
`3010` 2 s later when the door was opened, `3011` 6 s after that when it
closed.

The full list of event IDs the integration knows is `FLEXC_EVENT_DESCRIPTIONS`
in `custom_components/spc_flexc/sensor.py`.

## Mapping to Home Assistant entities

| Panel object | Source | Entities |
| --- | --- | --- |
| Panel | `PANEL_SUMMARY`, events 7003/7004 | Device info (model, firmware); panel `alarm_control_panel`; panel sensor; engineer mode binary sensor; FlexC connection binary sensor; optional last event ID diagnostic sensor |
| Area | `AREA_STATUS`, events 35xx and 1000/1001 | `alarm_control_panel` per area (arm/disarm via `CMD_AREA_CHANGE_MODE`) |
| Zone | `ZONE_STATUS`, zone events | Binary sensor per zone plus tamper/trouble diagnostics; inhibition and isolation switches and a restore button via `CMD_ZONE_CONTROL` |
| Door | `DOOR_STATUS`, `DOOR_CONFIG`, events 30xx | Door status sensor; door mode sensor (`normal`/`blocked`/`unlocked`, also set by events 3007–3009); Door open binary sensor (`DPS_INPUT`, also set by events 3010/3011); Entry granted binary sensor (event 3000 for `GRANTED_TIME`); buttons Momentary open, Unlock, Normal and Block (`CMD_DOOR_CONTROL` 5–8), unavailable when the matching `*_ALLOWED` flag is `0` |
| Every event | `EVENT` | `spc_flexc_event` on the event bus and in the logbook |
| Mapping Gate | `MG_STATUS` | Switch via `CMD_MG_CONTROL` |
| X-BUS device | `STATUS_XBUS`, events 531x | Tamper fault, inhibition and isolation binary sensors; aux voltage, aux current, diagnostic and inventory sensors |
| FlexC ATS | `FLEXC_ATS_STATUS` | Active path and last transmission sensors; ATP fault binary sensor |

## Pending panel checks

### Lock relay after Entry Granted

On the reference panel, the lock relay of door 3 is a door-controller output
set to follow *Door 3 – Entry Granted*, with `GRANTED_TIME=3`. An external
input wired to that relay goes on for exactly 3 s on every Entry Granted and
does not react to the exit button (DRS). Neither FlexC nor EDP has so far been
seen to report the state of that output.

Question: does any `DOOR_STATUS` field change while the relay is energised,
and which fields does event `3000` carry?

Method (read-only):

1. `GET_DOOR_CONFIG DOOR_ID=3` to confirm `GRANTED_TIME`.
2. `GET_DOOR_STATUS DOOR_ID=3` with the door at rest.
3. Present a valid card, so the panel sends `3000` and energises the relay.
4. `GET_DOOR_STATUS DOOR_ID=3` again within `GRANTED_TIME`, and once after.
5. Compare the replies, and the field names of the `3000` event.

Fallback if no field changes: derive the relay state from event `3000` for
`DOOR_ID` 3 plus `GRANTED_TIME` seconds.

Result (2026-11-06):

- `GET_DOOR_CONFIG DOOR_ID=3` confirms `GRANTED_TIME="3"`.
- Doors 1 and 2 report `DRS_INPUT="1"` at rest (2026-11-12); the owner
  says their exit button is not pressed and the input is probably inverted.
  `DOOR_CONFIG ATTRIB`: door 1 `00603002`, door 2 `00601000`, door 3
  (`DRS_INPUT="0"` at rest) `0520A212`. Set on doors 1 and 2 but not on 3:
  `0x00400000` and `0x00001000`. Mapped 2026-11-13: `0x00001000` is the
  web page's "DRS Öppnaknapp NO" (exit button normally open), ticked on
  doors 1 and 2. Unticking it on door 2 did not change `DRS_INPUT` at once
  (still `1`); the input may only be re-evaluated when it changes. Both
  doors have DRS EOL "Ingen", which (owner) means a plain unbalanced
  contact, not a missing button. **Explained 2026-11-14:** `DRS_INPUT` and
  `DPS_INPUT` are the contact's state (1 open), which the web page shows as
  "DRS Öppnaknapp Öppen/Stängd"; doors 1 and 2 have normally open buttons
  (open at rest, closed when pressed, checked by the owner on Garageport),
  door 3 a normally closed one. Pressed = contact state differs from the
  rest state given by `ATTRIB 0x1000` (DRS NO); door open likewise with
  `0x0800` (DPS NO). Events 3010/3011 report the door, not the contact.
  See *Door ATTRIB bits* below.
- Door sides (2026-11-13, door 2): the web page's "Område på dörrsida"
  for the entry reader is `DOOR_CONFIG DOOR_SIDE_0`, for the exit reader
  `DOOR_SIDE_1`, with the web page's area number (left out for Ingen).
  A door controller has two readers: either entry and exit on one door
  (door type Utpassering, `ATTRIB 0x20000000`) or two doors. **`DOOR_STATUS`
  reports the side one higher**: area 1 set on the web page reads
  `AREA_SIDE_1="2"`, area 3 reads `AREA_SIDE_2="4"`, so door 3's exit side
  (web page: area 1 Huset) shows as area 2 Garaget. Use `DOOR_CONFIG`
  for the side areas.
- `DOOR_STATUS` at rest: `DPS_INPUT="0" DRS_INPUT="0" STATUS="0" MODE="0"`.
- About 2.9 s after `3000` reached Home Assistant, and again 5 s later, only
  `DPS_INPUT` had changed (to `1`, door open). `STATUS`, `MODE` and
  `DRS_INPUT` were unchanged.
- `DOOR_STATUS` has no field for the lock relay or any other output.

Conclusion: FlexC does not report the lock relay state in `DOOR_STATUS`. The
first read came near the end of the 3 s window, so a change of `STATUS` during
the pulse cannot be fully ruled out, but no field is a candidate. Use the
fallback: treat the relay as energised for `GRANTED_TIME` seconds after
`3000` for that door.

## Door ATTRIB bits (mapped 2026-11-13)

`GET_DOOR_CONFIG` `ATTRIB` is a 32-bit hex mask of the web page's door
options (Konfiguration > Dörrar > Ändra). Mapped on door 2 by ticking one
option at a time on the web page, reading the record back over FlexC and
setting it back; doors 1 and 3 match their web pages bit for bit.

| Bit | Web page (Swedish) | Meaning |
|---|---|---|
| `0x00000002` | Kort och PIN-kod | card and PIN required |
| `0x00000004` | Endast PIN-kod | PIN only |
| `0x00000008` | PIN-kod för utpassage | PIN required to exit |
| `0x00000010` | PIN-kod för frånkoppling | PIN required to set/unset |
| `0x00000020` | Förebygg passback | anti-passback |
| `0x00000040` | Soft passback | log passback only |
| `0x00000080` | Vittne | escort required |
| `0x00000100` | Ledsagare | custodian |
| `0x00000200` | Nödsituation | unlock on fire in the door's area |
| `0x00000800` | DPS Dörrkontakt NO | door contact normally open |
| `0x00001000` | DRS Öppnaknapp NO | exit button normally open |
| `0x00002000` | Summer | door controller buzzer on forced/left open |
| `0x00004000` | Ignorera forcerad | ignore door forced |
| `0x00008000` | Frånkoppling utifrån | unset by card at entry reader |
| `0x00010000` | Frånkoppling inifrån | unset by card at exit reader |
| `0x00020000` | Tillkoppling utifrån | set by card twice at entry reader |
| `0x00040000` | Tillkoppling inifrån | set by card twice at exit reader |
| `0x00080000` | Förregla | interlock |
| `0x00100000` | Använd prefix | set with prefix key |
| `0x00200000` | PIN-kod eller kort | PIN or card |
| `0x00400000` | Kod försök | invalid cards count towards code tamper |
| `0x00800000` | DRS Ingen knapp | exit button ignored |
| `0x01000000` | Nödläge någon | unlock on fire in any area |
| `0x02000000` | Förbikoppla larm | pass allowed while area set |
| `0x04000000` | Tvångstillkoppling | forced set from entry reader |
| `0x08000000` | Kort för utpassage | card to exit |
| `0x10000000` | Dubbelverifiering | two users required |
| `0x20000000` | Dörrtyp Utpassering (radio; Inpassering = clear) | door has an exit reader |
| `0x80000000` | DRS puls | exit button as a pulse |

Not seen: `0x00000001`, `0x00000400`, `0x40000000`. "Dubbel låser upp"
(double card unlocks) changed no `ATTRIB` bit. The timers map to
`GRANTED_TIME` (Passage beviljad), `DENY_TIME`, `OPEN_TIME`, `LEFT_TIME`
(minutes), `EXT_TIME`, `ESCORT_TIME`. Not in `DOOR_CONFIG`: EOL resistors,
door group, the per-option calendars, the DPS delay and the locked/unlocked
calendars.

The web page's door form posts every field with `save=Spara` to
`secure.htm?page=doors&door=N&edit_door=1&door=N` and answers "Konfig.filen
sparad, OK"; it works with the engineer web login without installer mode.

## Door triggers and fire areas (mapped 2026-11-13)

`DOOR_TRIGGER_CONFIG` rows are the web page's Avancerad > Orsak & effekt
entries for the door: `TRIGGER` is the trigger number in the Händelser list
(Avancerad > Orsak & effekt > Händelser), `EDGE` 1 Positiv, 0 Negativ, and
`ACTION` 0 Dörr till normalläge, 1 Momentan access, 2 Lås dörr (blockerad),
3 Lås upp dörr (olåst). Door 1's `3/4/1` is "trigger 4, positive edge,
unlock". Read from the web page; no change was needed.

`DOOR_CONFIG FIRE_AREA` is a mask of areas, bit 0 = area 1, set by the
per-area option "firedoor_N" on the area's page (Konfiguration > Områden >
Ändra: a fire in this area unlocks door N). On the reference panel areas 1
and 4 have it for doors 1-3, so every door reads `...0009`. Checked by
ticking door 2 on area 2: door 2 read `...000B`, then set back.

`READ_AREAS_CFG` still answers `12` in installer mode, with no attributes,
`ID` or `AREA_ID` (2026-11-13). The area options are on the web page's area
form (`secure.htm?page=area_edit&area=N&action=update`).

## Web page notes

- A GET of `secure.htm?page=eng_mode` **toggles installer mode** (the web
  page's toggle in the header). It is not a read. Found 2026-11-13 when a
  read sweep fetched it; the panel was set back with the same link.
- Most configuration forms (doors, zones, zone attributes, areas) save with
  the engineer web login only in installer mode; the web page then answers
  "Konfig.filen sparad, OK".
- The area list page has delete buttons (`deleteN`) next to `editN`; never
  post those.
- Some selects carry two `SELECTED` options (seen on the profile door
  calendars); a browser posts the last one.
- The zone list (Konfiguration > Ingångar) is only shown in installer mode.

## Logins and modes (checked 2026-11-13)

Every read command was sent in four ways: the command login (9995) and the
engineer login (9999), each with the panel in normal mode and in installer
mode (entered and left with the integration's `set_engineer_mode`). All 46
reads gave the same `RESULT` and the same record shape in all four; only
values that report the mode differ (`GET_PANEL_SUMMARY ENG_MODE`,
`STATUS_PANEL ENGMODE`, `VERIFY_USER_ON_PANEL ENGINEER`). Reads that fail
fail everywhere: `READ_AREAS_CFG` `12`; `GET_MODEM_STATUS`,
`GET_MODEM_LOG`, `GET_ARC_LOG` and the user device reads `17`;
`GET_CAMERA_IMAGE`, `GET_VZONE_STATUS`, `GET_VZONE_DATA` `102`.

Writes, as no-ops or set back at once (door 2, zone 40, area 4):

| Command | Command login, normal | Engineer, normal | Engineer, installer mode | Command login, installer mode |
|---|---|---|---|---|
| `DOOR_CONTROL` | `0` | `0` | `0` | `0` |
| `ZONE_CONTROL` inhibit/de-inhibit/isolate/de-isolate | `0` | `0` | `0` | `0` |
| `ZONE_CONTROL` restore (zone not in alarm) | `20` | `20` | `20` | `20` |
| `AREA_CHANGE_MODE` | `0` | `0` | **`78`** | **`78`** |
| `EDIT_ZONE` (whole record) | `65` | `65` | `12` / empty reply | `65` |
| `GRANT_ENGINEER_ACCESS` | `65` | `65` | – | – |
| Configuration on the web page | – | – | saves | – |

So only `EDIT_ZONE` needs the engineer login and installer mode, and only
area set/unset is refused in installer mode. The engineer-only rows for
`EDIT_ZONE` are from 2026-11-06 and 2026-11-13.

## READ_INTRUDER_CFG against the web page (2026-11-13)

The timers on Konfiguration > System > Timers all match `INTRUDER` (44
fields compared, every value equal). Units differ: the web page shows the
bell and confirmation times in **minutes**, FlexC sends **seconds**
(`INTBELLTIME`, `EXTBELLTIME`, `EXTBELLSTROBETIME` 900 = 15 min;
`CONFIRMTIME` 1800 = 30 min). The rest are the same unit on both: delays and
lockouts in seconds (`CODE_LOCKOUT_TIME` 900), `FREQUENTTIME` and
`SEISMIC_AUTOTEST_TIME` in hours, `USER_VALID_PIN_TIME` in days. Field pairs:
`chime`/`CHIMETIME`, `doubleknock`/`DKTIME`, `failtoset`/`FTSTIME`,
`rkd`/`RKDTIMEOUT`, `engautologout`/`ENGINEER_AUTO_OUT`, `net_timeout`/
`NET_FAIL_TIME`, `video_timeout`/`CAMERA_OFFLINE`,
`alarm_lockout_test_duration`/`ALARM_LOCKOUT_TIME`, `confirm_holdup`/
`HOLDUP_CONFIRM`; the others have the same name. The web page's separate
"external bell delay when part set" has no own FlexC field.

System options (Konfiguration > System > Systemalternativ), mapped
2026-11-13 by ticking one at a time on the web page in installer mode,
reading `READ_INTRUDER_CFG` back (the change shows after a few seconds) and
setting it back; the page and `INTRUDER` read back as at the start.

| Field / bit | Web page (Swedish) |
|---|---|
| `MODE 0x00000008` | Siren återstart |
| `MODE 0x00000010` | Siren vid första larm |
| `MODE 0x00000040` | Visa öppna sektioner |
| `MODE 0x00000200` | Automatisk återställning |
| `MODE 0x00002000` | Siren vid tillkopplingsfel |
| `MODE 0x00004000` | Blixtljus vid tillkopplingsfel |
| `MODE 0x00040000` | Kodad återställning |
| `MODE 0x00080000` | Visa alltid status |
| `MODE 0x00200000` | Meddelande till LC |
| `MODE 0x00400000` | Återställning via fjärrkontroll |
| `MODE 0x01000000` | Återställ vid frånkoppling |
| `MODE 0x02000000` | Offline sabotage |
| `MODE 0x04000000` | Installatörsåterställning |
| `MODE 0x10000000` | Larm vid utpassage |
| `MODE 0x40000000` | Misstanke ljudande larm |
| `MODE 0x80000000` | Visa kameror |
| `MODE_EXT 0x00000001` | Förbjud Tillkoppling med fel |
| `MODE_EXT 0x00000002` | Test av seismiska vid Tillkoppl. |
| `MODE_EXT 0x00000004` | Återstarta hotlarm |
| `MODE_EXT 0x00000008` | Återstarta bråklarm |
| `MODE_EXT 0x00000010` | Audioexpander LED |
| `MODE_EXT 0x00000020` | Installatör avslut |
| `MODE_EXT 0x00000040` | Tystnad vid Audioverifiering |
| `MODE_EXT 0x00000080` | C-app styr läsar LEDs |
| `MODE_EXT 0x00000100` | Rapportera i inst läge |
| `MODE_EXT 0x00000200` | Larm vid rapporterat fel |
| `MODE_EXT 0x00000400` | Larm vid inpassage |
| `MODE_EXT 0x00000800` | Dölj förbikoppling |
| `MODE_EXT 0x00002000` | Logga manöverpanelåtkomst |
| `MODE_EXT 0x00008000` | Kontinuerligt sista utgång |
| `OUTPUTS_FULL_ENG` 1 | Utgångar i installatörsläge |

"Ignorera platskod" changed nothing in `INTRUDER`. Not changed on purpose
(they could lock out the engineer or change how codes and users work):
Installatör, Tillverkare, PACE-PIN, Återställ kort, SPC Manager, VdS and the
two EOL options. `MODE` bits `0x00000002`, `0x00020000` and `0x00100000` are
set on the reference panel and belong to one of those or to something else.

Choices with the same value on the web page and in `INTRUDER`:
`WATCHDOG_OUTPUT_MODE`, `ANTIMASK_SET`/`_UNSET` (0 off, 1 tamper, 2
anti-mask, 3 alarm), `OUT_OF_BOUNDS_MODE_SET`/`_UNSET` and
`UNSTABLE_MODE_SET`/`_UNSET` (0 off, 1 tamper, 2 anti-mask), `EOL` (the web
page's balancing list), `ZONE_NO_BELL_ATTR` (1 no bells, 2 no internal, 3 no
external), `DURESS` (0 off, 1 PIN+1, 2 PIN+2), `DOOR_MODE_SET`/`_UNSET` (0
standard, 1 card and PIN, 2 card or PIN), `PIN` (number of PIN digits),
`NAMEA`/`NAMEB` (part set names). Standard page (read only, never changed:
changing region or grade can reset defaults): `CONTINENT` 0 Europe, `REGION`
6 Sweden, `TYPE` 2 Financial (0 Domestic), `GRADE` 0 installer's
configuration.

The integration decodes all of this into the Panel settings sensor's
`settings` attribute (web page names as keys, timers in the web page's
units), and the system card shows it as "Centralens inställningar".
