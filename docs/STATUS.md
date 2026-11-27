# Status

What works, what is verified on a real panel, what is built but untested,
and what is left. The per-command status is in
[FLEXC_PROTOCOL.md](FLEXC_PROTOCOL.md), section *Command catalogue*; this page
is the summary.

## Reference system

Everything marked *verified* was checked on this installation:

| Component | Model | Firmware |
| --- | --- | --- |
| Panel | Vanderbilt SPC4300 (hardware 1.4) | 3.14.1 - R.42341 |
| Door controllers | 2 × SPCA210 2-door expander (3 doors) | 2.05 |
| I/O expanders | 2 × SPCE650 (8 inputs / 2 outputs) | 1.11 |
| Keypads | SPC Comfort Keypad, SPC Keypad | 2.01, 2.09 |
| Home Assistant | Home Assistant OS | 2026.11 |

Four areas, three doors, a few wireless detectors. No modem, fobs, PACE, TWW
tags, camera or verification zones. Other SPC models (SPC4000, SPC5000,
SPC6000) and firmware versions use the same FlexC protocol but are not tested;
reports are welcome.

## Summary

The panel's Command Profile lists 105 FlexC commands.

| Status | Commands |
| --- | --- |
| Used by the integration and checked on the reference panel | 54 |
| Not available on the reference panel (modem, ARC, camera, verification zones) | 7 |
| Not built: user fob/PACE/TWW tag/SMS (the reference panel has no such hardware) | 19 |
| Not built: file, firmware, reset, FlexC administration, X-BUS reconfiguration (can disrupt the panel) | 13 |
| Not built: other (see *Left to do*) | 12 |

### Verified on the reference panel

- FlexC link: handshake, AES-256, chunked long replies, reconnects.
- Status: panel, areas, zones, doors, Mapping Gates, system alerts, X-BUS,
  FlexC ATS/ATP, Ethernet, power supply.
- Alarm: set/unset per area and globally, part set, arming errors.
- Zones: inhibit, isolate, restore; zone configuration (`EDIT_ZONE`, needs the
  engineer login in full engineer mode).
- Doors: Normal, Unlocked, Momentary, Blocked; entry granted/denied, door
  contact, exit button, who unlocked, last passage.
- Mapping Gates: read and control.
- System alerts: inhibit/isolate per alert, clear alerts, silence bells,
  ATP test call.
- Users: list, edit, add, delete, PIN change, PIN management, cards, unknown
  cards, user status, user profiles.
- Calendars: read, edit, week types, add/delete, exception days.
- Logs: system, access per door, zone, wireless, FlexC ATS/ATP.
- Panel clock (`set_clock`), panel settings (`READ_INTRUDER_CFG`), languages.
- Engineer login: full engineer mode on/off.
- Events: every FlexC event is fired as `spc_flexc_event` and shown in the
  logbook and the activity card.

### Not available on the reference panel

Modem status and log, ARC log, camera image, verification zones, virtual
keypad (`17` on this panel), user fobs/PACE/TWW tags/SMS.

## Important panel behaviour

**Save every configuration change.** A FlexC change to users, profiles,
calendars or zones is only held in the panel's memory. Unless
`CMD_SAVE_CONFIG` follows, the panel's checksum check fails within about a
minute and it restarts with the last saved configuration: the change is lost
and the alarm system is interrupted. The integration sends `SAVE_CONFIG`
right after every configuration change. After a write, the system log shows
"Saving panel configuration" and no system start.

**Never send a partial edit.** `EDIT_USER` and `EDIT_CALENDAR` need the whole
record read back first. `EDIT_HOLDUP_CONFIG` without attributes overwrote
the hold-up fields once. `EDIT_CALENDAR` clears the times of all three week
types, so `set_calendar` sends them back with `EDIT_CALENDAR_WEEK`.

**PINs.** The panel stores each PIN as 8 hex digits: the PIN as an integer
XOR a key that belongs to the user number. The key stays the same for a
user number across delete and add. A wrong key gives result `59`.
`VERIFY_USER_ON_PANEL` checks the login it is sent with, not a PIN, so a PIN
cannot be checked over FlexC; the next keypad login (event `4003`) confirms
it.

**Engineer mode.** In engineer mode the panel refuses many commands and
other web logins. `ENTER_FULL_ENGINEER_MODE` / `EXIT_FULL_ENGINEER_MODE` work
only with the engineer login.

## Words for logins and modes

From Vanderbilt's SPC installation and configuration manual (*Engineer
modes*, *Engineer PINs*, *Adding/Editing User Profiles*), with the Swedish
names the panel shows.

**Engineer (Swedish: Programtekniker).** The installer login. Only the
engineer can enter the engineer modes. The optional engineer login in the
config entry means this login. The normal command login is not an engineer;
the *Engineer mode control* switch exists only when an engineer login is
configured.

**Engineer modes (Swedish: installatörsläge).** *Full Engineer* disables all
alarm settings, reports and output programming; alerts, faults and tampers
must be isolated or cleared before leaving it. *Soft Engineer* has fewer
programming functions and does not affect outputs.

**User (Swedish: Användare).** A panel user; what it may do comes from the
rights in its user profiles (*Limited*, *Standard*, *Manager*). Changing
users and codes needs no engineer mode: the right *Users* (Manager) may
create and edit users with the same or fewer rights.

**Command profile (Swedish: Kommandoprofil).** The FlexC setting that decides
which commands an ATS login may send. Commands from the command login are
logged as user 9995 "Command profile …"; 9995 is not in the user list.

**Global profiles.** Cannot be edited in the browser, only in SPC Manager.
The `GID` attribute in user, profile and calendar records is probably this
global ID (`0` = local); not confirmed.

## Left to do

1. Read-only configuration: `READ_PANEL_INFO` and `READ_CONFIG_HEADERS`
   answer but repeat the panel summary; `READ_AREAS_CFG` needs an unknown
   attribute.
2. Hold-up configuration (`GET_HOLDUP_CONFIG` / `EDIT_HOLDUP_CONFIG`).
3. Fob, PACE, TWW tag and SMS commands (needs a panel with that hardware).
4. A capabilities view listing every function as: works; untested; not
   allowed in the Command Profile; needs the engineer login; not built;
   hardware missing.
5. Three system alerts that the panel's status page lists are not mapped to a
   `SYSALERT` bit yet: *User Duress*, *User RF FOB Panic* and *Wireless Two Way
   Devices Require Relearning*.
6. Detector type of wireless zones (*Magnetic contact*, *Smoke detector*, *PIR*):
   the panel's web page shows it, but no FlexC command reports it so far.
7. Upstream: the long-reply acknowledgement and the `CMD_STATUS_PANEL` fault
   read are merged in [minimicro34/ha-spc-flexc](https://github.com/minimicro34/ha-spc-flexc)
   v1.1.10 (#20, #21); the panel logs are offered in #25, the door and access
   information next.

Not planned without a backup and great care, because they can switch FlexC
off or disrupt the panel: deleting ATS/ATP/profiles, replacing the FlexC
key, firmware upload, file upload/download, panel reset, `RECONFIG_XBUS`,
engineer and manufacturer access grants.
