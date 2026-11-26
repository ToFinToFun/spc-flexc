"""FlexC event table of the SPC panel.

Generated from the panel's own complete event table (web page: Communications >
FlexC > Event Profiles > view a profile > Show Complete Event Table) on an
SPC4300 with firmware 3.14.1, in English and Swedish. Event 3502, 3503, 3506
and 3507 carry the site's own Partset names on the panel; the panel's default
names are used here. See docs/EVENT_TABLE.md.
"""

from typing import NamedTuple


class EventInfo(NamedTuple):
    """One row of the panel's event table."""

    en: str
    sv: str
    address_type: str
    sia: str | None
    cid: str | None


EVENT_TABLE: dict[int, EventInfo] = {
    1000: EventInfo(
        "Burglary Alarm [Alarm Zone]",
        "Inbrottslarm [Larm SEKTION]",
        "Zone ID",
        "BA",
        "130/1",
    ),
    1001: EventInfo(
        "Burglary Alarm [Entry/Exit Zone]",
        "Inbrottslarm [In/utpassering SEKTION]",
        "Zone ID",
        "BA",
        "134/1",
    ),
    1002: EventInfo(
        "Burglary Alarm [Exit Term Zone]",
        "Inbrottslarm [Utpasseringstid SEKTION]",
        "Zone ID",
        "BA",
        None,
    ),
    1003: EventInfo(
        "Zone alarm [Fire alarm Zone]",
        "Sektionslarm [Brandlarm SEKTION]",
        "Zone ID",
        "FA",
        "110/1",
    ),
    1004: EventInfo(
        "Burglary Alarm [Fire Exit Zone]",
        "Inbrottslarm [Nödutgång SEKTION]",
        "Zone ID",
        "BA",
        "130/1",
    ),
    1005: EventInfo(
        "Zone alarm [Line Zone]",
        "Sektionslarm [Linje SEKTION]",
        "Zone ID",
        "LT",
        "351/1",
    ),
    1006: EventInfo(
        "Zone alarm [Panic Zone]",
        "Sektionslarm [Bråklarm SEKTION]",
        "Zone ID",
        "PA",
        "120/1",
    ),
    1007: EventInfo(
        "Zone alarm [Holdup Zone]",
        "Sektionslarm [Överfall SEKTION]",
        "Zone ID",
        "HA",
        "120/1",
    ),
    1008: EventInfo(
        "Zone alarm [Tamper Zone]",
        "Sektionslarm [SABOTAGE SEKTION]",
        "Zone ID",
        "TA",
        "137/1",
    ),
    1009: EventInfo(
        "Zone alarm [Tech Zone]",
        "Sektionslarm [Tekniskt larm SEKTION]",
        "Zone ID",
        "UA",
        "150/1",
    ),
    1010: EventInfo(
        "Zone alarm [Medical Zone]",
        "Sektionslarm [Medicinskt SEKTION]",
        "Zone ID",
        "MA",
        "100/1",
    ),
    1011: EventInfo(
        "Zone alarm [Keyarm Zone]",
        "Sektionslarm [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BA",
        None,
    ),
    1012: EventInfo(
        "Zone alarm [Unused Zone]",
        "Sektionslarm [Används ej SEKTION]",
        "Zone ID",
        None,
        None,
    ),
    1013: EventInfo(
        "Zone alarm [Shunt Zone]",
        "Sektionslarm [Förbikopplare SEKTION]",
        "Zone ID",
        "BA",
        None,
    ),
    1014: EventInfo(
        "Zone alarm [X-Shunt Zone]",
        "Sektionslarm [X-förbikopplare SEKTION]",
        "Zone ID",
        "BA",
        None,
    ),
    1015: EventInfo(
        "Zone alarm [Detector Fault Zone]",
        "Sektionslarm [Detektorfel SEKTION]",
        "Zone ID",
        "BT",
        "380/1",
    ),
    1016: EventInfo(
        "Zone alarm [Lock Supervision Zone]",
        "Sektionslarm [Låskontroll SEKTION]",
        "Zone ID",
        "BA",
        "130/1",
    ),
    1017: EventInfo(
        "Burglary Alarm [Seismic Zone]",
        "Inbrottslarm [Seismisk SEKTION]",
        "Zone ID",
        "BA",
        "130/1",
    ),
    1019: EventInfo(
        "Zone alarm [Holdup Fault Zone]",
        "Sektionslarm [Överfall fel SEKTION]",
        "Zone ID",
        "HT",
        "376/1",
    ),
    1020: EventInfo(
        "Zone alarm [Warning Fault Zone]",
        "Sektionslarm [Varning fel SEKTION]",
        "Zone ID",
        "YA",
        "380/1",
    ),
    1021: EventInfo(
        "Zone alarm [Setting authorisation Zone]",
        "Sektionslarm [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        None,
        None,
    ),
    1022: EventInfo(
        "Burglary Alarm [Lock element Zone]",
        "Inbrottslarm [Lås element SEKTION]",
        "Zone ID",
        None,
        None,
    ),
    1023: EventInfo(
        "Burglary Alarm [Glass Break Zone]",
        "Inbrottslarm [Glaskross SEKTION]",
        "Zone ID",
        "BA",
        "130/1",
    ),
    1024: EventInfo(
        "Zone alarm [Water Zone]",
        "Sektionslarm [Vatten SEKTION]",
        "Zone ID",
        "WA",
        "154/1",
    ),
    1025: EventInfo(
        "Zone alarm [Heat Zone]",
        "Sektionslarm [Värme SEKTION]",
        "Zone ID",
        "KA",
        "158/1",
    ),
    1026: EventInfo(
        "Zone alarm [Fridge/Freezer Zone]",
        "Sektionslarm [Kyl/frys SEKTION]",
        "Zone ID",
        "ZA",
        "152/1",
    ),
    1027: EventInfo(
        "Zone alarm [Gas Zone]", "Sektionslarm [Gas SEKTION]", "Zone ID", "GA", "151/1"
    ),
    1028: EventInfo(
        "Zone alarm [Sprinkler Zone]",
        "Sektionslarm [Sprinkler SEKTION]",
        "Zone ID",
        "SA",
        "213/1",
    ),
    1029: EventInfo(
        "Zone alarm [CO Zone]", "Sektionslarm [CO SEKTION]", "Zone ID", "CY", "162/1"
    ),
    1100: EventInfo(
        "Burglary Restoral [Alarm Zone]",
        "Inbrott återställning [Larm SEKTION]",
        "Zone ID",
        "BR",
        "130/3",
    ),
    1101: EventInfo(
        "Burglary Restoral [Entry/Exit Zone]",
        "Inbrott återställning [In/utpassering SEKTION]",
        "Zone ID",
        "BR",
        "130/3",
    ),
    1102: EventInfo(
        "Burglary Restoral [Exit Term Zone]",
        "Inbrott återställning [Utpasseringstid SEKTION]",
        "Zone ID",
        "BR",
        None,
    ),
    1103: EventInfo(
        "Zone restore [Fire Restoral Zone]",
        "Sektion återst. [Brandlarm återställning SEKTION]",
        "Zone ID",
        "FR",
        "110/3",
    ),
    1104: EventInfo(
        "Burglary Restoral [Fire Exit Zone]",
        "Inbrott återställning [Nödutgång SEKTION]",
        "Zone ID",
        "BR",
        "130/3",
    ),
    1105: EventInfo(
        "Zone restore [Line Zone]",
        "Sektion återst. [Linje SEKTION]",
        "Zone ID",
        "LR",
        "351/3",
    ),
    1106: EventInfo(
        "Zone restore [Panic Zone]",
        "Sektion återst. [Bråklarm SEKTION]",
        "Zone ID",
        "PR",
        "120/3",
    ),
    1107: EventInfo(
        "Zone restore [Holdup Zone]",
        "Sektion återst. [Överfall SEKTION]",
        "Zone ID",
        "HR",
        "120/3",
    ),
    1108: EventInfo(
        "Zone restore [Tamper Zone]",
        "Sektion återst. [SABOTAGE SEKTION]",
        "Zone ID",
        "TR",
        "137/3",
    ),
    1109: EventInfo(
        "Zone restore [Tech Zone]",
        "Sektion återst. [Tekniskt larm SEKTION]",
        "Zone ID",
        "UR",
        "150/3",
    ),
    1110: EventInfo(
        "Zone restore [Medical Zone]",
        "Sektion återst. [Medicinskt SEKTION]",
        "Zone ID",
        "MR",
        "100/3",
    ),
    1111: EventInfo(
        "Zone restore [Keyarm Zone]",
        "Sektion återst. [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BR",
        None,
    ),
    1112: EventInfo(
        "Zone restore [Unused Zone]",
        "Sektion återst. [Används ej SEKTION]",
        "Zone ID",
        None,
        None,
    ),
    1113: EventInfo(
        "Zone restore [Shunt Zone]",
        "Sektion återst. [Förbikopplare SEKTION]",
        "Zone ID",
        "BR",
        None,
    ),
    1114: EventInfo(
        "Zone restore [X-Shunt Zone]",
        "Sektion återst. [X-förbikopplare SEKTION]",
        "Zone ID",
        "BR",
        None,
    ),
    1115: EventInfo(
        "Zone restore [Detector Fault Zone]",
        "Sektion återst. [Detektorfel SEKTION]",
        "Zone ID",
        "BJ",
        "380/3",
    ),
    1116: EventInfo(
        "Zone restore [Lock Supervision Zone]",
        "Sektion återst. [Låskontroll SEKTION]",
        "Zone ID",
        None,
        None,
    ),
    1117: EventInfo(
        "Burglary Restoral [Seismic Zone]",
        "Inbrott återställning [Seismisk SEKTION]",
        "Zone ID",
        "BR",
        "130/3",
    ),
    1119: EventInfo(
        "Zone restore [Holdup Fault Zone]",
        "Sektion återst. [Överfall fel SEKTION]",
        "Zone ID",
        "HJ",
        "376/3",
    ),
    1120: EventInfo(
        "Zone restore [Warning Fault Zone]",
        "Sektion återst. [Varning fel SEKTION]",
        "Zone ID",
        "YH",
        "380/3",
    ),
    1121: EventInfo(
        "Zone restore [Setting authorisation Zone]",
        "Sektion återst. [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        None,
        None,
    ),
    1122: EventInfo(
        "Burglary Restoral [Lock element Zone]",
        "Inbrott återställning [Lås element SEKTION]",
        "Zone ID",
        "BR",
        "130/3",
    ),
    1123: EventInfo(
        "Burglary Restoral [Glass Break Zone]",
        "Inbrott återställning [Glaskross SEKTION]",
        "Zone ID",
        "BR",
        "130/3",
    ),
    1124: EventInfo(
        "Zone restore [Water Zone]",
        "Sektion återst. [Vatten SEKTION]",
        "Zone ID",
        "WH",
        "154/3",
    ),
    1125: EventInfo(
        "Zone restore [Heat Zone]",
        "Sektion återst. [Värme SEKTION]",
        "Zone ID",
        "KH",
        "158/3",
    ),
    1126: EventInfo(
        "Zone restore [Fridge/Freezer Zone]",
        "Sektion återst. [Kyl/frys SEKTION]",
        "Zone ID",
        "ZH",
        "152/3",
    ),
    1127: EventInfo(
        "Zone restore [Gas Zone]",
        "Sektion återst. [Gas SEKTION]",
        "Zone ID",
        "GH",
        "151/3",
    ),
    1128: EventInfo(
        "Zone restore [Sprinkler Zone]",
        "Sektion återst. [Sprinkler SEKTION]",
        "Zone ID",
        "SH",
        "213/3",
    ),
    1129: EventInfo(
        "Zone restore [CO Zone]",
        "Sektion återst. [CO SEKTION]",
        "Zone ID",
        "CH",
        "162/3",
    ),
    1200: EventInfo(
        "Zone tamper [Alarm Zone]",
        "Sektionsabotage [Larm SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1201: EventInfo(
        "Zone tamper [Entry/Exit Zone]",
        "Sektionsabotage [In/utpassering SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1202: EventInfo(
        "Zone tamper [Exit Term Zone]",
        "Sektionsabotage [Utpasseringstid SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1203: EventInfo(
        "Zone tamper [Fire Zone]",
        "Sektionsabotage [Brand SEKTION]",
        "Zone ID",
        "FT",
        "144/1",
    ),
    1204: EventInfo(
        "Zone tamper [Fire Exit Zone]",
        "Sektionsabotage [Nödutgång SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1205: EventInfo(
        "Zone tamper [Line Zone]",
        "Sektionsabotage [Linje SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1206: EventInfo(
        "Zone tamper [Panic Zone]",
        "Sektionsabotage [Bråklarm SEKTION]",
        "Zone ID",
        "PT",
        "144/1",
    ),
    1207: EventInfo(
        "Zone tamper [Holdup Zone]",
        "Sektionsabotage [Överfall SEKTION]",
        "Zone ID",
        "HT",
        "144/1",
    ),
    1208: EventInfo(
        "Zone tamper [Tamper Zone]",
        "Sektionsabotage [SABOTAGE SEKTION]",
        "Zone ID",
        "TA",
        "144/1",
    ),
    1209: EventInfo(
        "Zone tamper [Tech Zone]",
        "Sektionsabotage [Tekniskt larm SEKTION]",
        "Zone ID",
        "UT",
        "144/1",
    ),
    1210: EventInfo(
        "Zone tamper [Medical Zone]",
        "Sektionsabotage [Medicinskt SEKTION]",
        "Zone ID",
        "MT",
        "144/1",
    ),
    1211: EventInfo(
        "Zone tamper [Keyarm Zone]",
        "Sektionsabotage [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1212: EventInfo(
        "Zone tamper [Unused Zone]",
        "Sektionsabotage [Används ej SEKTION]",
        "Zone ID",
        None,
        "144/1",
    ),
    1213: EventInfo(
        "Zone tamper [Shunt Zone]",
        "Sektionsabotage [Förbikopplare SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1214: EventInfo(
        "Zone tamper [X-Shunt Zone]",
        "Sektionsabotage [X-förbikopplare SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1215: EventInfo(
        "Zone tamper [Detector Fault Zone]",
        "Sektionsabotage [Detektorfel SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1216: EventInfo(
        "Zone tamper [Lock Supervision Zone]",
        "Sektionsabotage [Låskontroll SEKTION]",
        "Zone ID",
        "UT",
        "144/1",
    ),
    1217: EventInfo(
        "Zone tamper [Seismic Zone]",
        "Sektionsabotage [Seismisk SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1218: EventInfo(
        "Zone tamper [All Okay Zone]",
        "Sektionsabotage [Allt OK SEKTION]",
        "Zone ID",
        None,
        "144/1",
    ),
    1219: EventInfo(
        "Zone tamper [Holdup Fault Zone]",
        "Sektionsabotage [Överfall fel SEKTION]",
        "Zone ID",
        "HT",
        "144/1",
    ),
    1220: EventInfo(
        "Zone tamper [Warning Fault Zone]",
        "Sektionsabotage [Varning fel SEKTION]",
        "Zone ID",
        "YA",
        "144/1",
    ),
    1221: EventInfo(
        "Zone tamper [Setting authorisation Zone]",
        "Sektionsabotage [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UT",
        "144/1",
    ),
    1222: EventInfo(
        "Zone tamper [Lock element Zone]",
        "Sektionsabotage [Lås element SEKTION]",
        "Zone ID",
        "UT",
        "144/1",
    ),
    1223: EventInfo(
        "Zone tamper [Glass Break Zone]",
        "Sektionsabotage [Glaskross SEKTION]",
        "Zone ID",
        "BT",
        "144/1",
    ),
    1300: EventInfo(
        "Zone tamper Restore [Alarm Zone]",
        "Sektionsabotage återställd [Larm SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1301: EventInfo(
        "Zone tamper Restore [Entry/Exit Zone]",
        "Sektionsabotage återställd [In/utpassering SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1302: EventInfo(
        "Zone tamper Restore [Exit Term Zone]",
        "Sektionsabotage återställd [Utpasseringstid SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1303: EventInfo(
        "Zone tamper Restore [Fire Zone]",
        "Sektionsabotage återställd [Brand SEKTION]",
        "Zone ID",
        "FJ",
        "144/3",
    ),
    1304: EventInfo(
        "Zone tamper Restore [Fire Exit Zone]",
        "Sektionsabotage återställd [Nödutgång SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1305: EventInfo(
        "Zone tamper Restore [Line Zone]",
        "Sektionsabotage återställd [Linje SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1306: EventInfo(
        "Zone tamper Restore [Panic Zone]",
        "Sektionsabotage återställd [Bråklarm SEKTION]",
        "Zone ID",
        "PJ",
        "144/3",
    ),
    1307: EventInfo(
        "Zone tamper Restore [Holdup Zone]",
        "Sektionsabotage återställd [Överfall SEKTION]",
        "Zone ID",
        "HJ",
        "144/3",
    ),
    1308: EventInfo(
        "Zone tamper Restore [Tamper Zone]",
        "Sektionsabotage återställd [SABOTAGE SEKTION]",
        "Zone ID",
        "TR",
        "144/3",
    ),
    1309: EventInfo(
        "Zone tamper Restore [Tech Zone]",
        "Sektionsabotage återställd [Tekniskt larm SEKTION]",
        "Zone ID",
        "UJ",
        "144/3",
    ),
    1310: EventInfo(
        "Zone tamper Restore [Medical Zone]",
        "Sektionsabotage återställd [Medicinskt SEKTION]",
        "Zone ID",
        "MJ",
        "144/3",
    ),
    1311: EventInfo(
        "Zone tamper Restore [Keyarm Zone]",
        "Sektionsabotage återställd [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1312: EventInfo(
        "Zone tamper Restore [Unused Zone]",
        "Sektionsabotage återställd [Används ej SEKTION]",
        "Zone ID",
        None,
        "144/3",
    ),
    1313: EventInfo(
        "Zone tamper Restore [Shunt Zone]",
        "Sektionsabotage återställd [Förbikopplare SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1314: EventInfo(
        "Zone tamper Restore [X-Shunt Zone]",
        "Sektionsabotage återställd [X-förbikopplare SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1315: EventInfo(
        "Zone tamper Restore [Detector Fault Zone]",
        "Sektionsabotage återställd [Detektorfel SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1316: EventInfo(
        "Zone tamper Restore [Lock Supervision Zone]",
        "Sektionsabotage återställd [Låskontroll SEKTION]",
        "Zone ID",
        "UJ",
        "144/3",
    ),
    1317: EventInfo(
        "Zone tamper Restore [Seismic Zone]",
        "Sektionsabotage återställd [Seismisk SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1318: EventInfo(
        "Zone tamper Restore [All Okay Zone]",
        "Sektionsabotage återställd [Allt OK SEKTION]",
        "Zone ID",
        "TR",
        "144/3",
    ),
    1319: EventInfo(
        "Zone tamper Restore [Holdup Fault Zone]",
        "Sektionsabotage återställd [Överfall fel SEKTION]",
        "Zone ID",
        "HJ",
        "144/3",
    ),
    1320: EventInfo(
        "Zone tamper Restore [Warning Fault Zone]",
        "Sektionsabotage återställd [Varning fel SEKTION]",
        "Zone ID",
        "YH",
        "144/3",
    ),
    1321: EventInfo(
        "Zone tamper Restore [Setting authorisation Zone]",
        "Sektionsabotage återställd [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UJ",
        "144/3",
    ),
    1322: EventInfo(
        "Zone tamper Restore [Lock element Zone]",
        "Sektionsabotage återställd [Lås element SEKTION]",
        "Zone ID",
        "UJ",
        "144/3",
    ),
    1323: EventInfo(
        "Zone tamper Restore [Glass Break Zone]",
        "Sektionsabotage återställd [Glaskross SEKTION]",
        "Zone ID",
        "BJ",
        "144/3",
    ),
    1400: EventInfo(
        "Zone inhibit [Alarm Zone]",
        "Sektion spärrad [Larm SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1401: EventInfo(
        "Zone inhibit [Entry/Exit Zone]",
        "Sektion spärrad [In/utpassering SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1402: EventInfo(
        "Zone inhibit [Exit Term Zone]",
        "Sektion spärrad [Utpasseringstid SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1403: EventInfo(
        "Zone inhibit [Fire Zone]",
        "Sektion spärrad [Brand SEKTION]",
        "Zone ID",
        "FB",
        "570/1",
    ),
    1404: EventInfo(
        "Zone inhibit [Fire Exit Zone]",
        "Sektion spärrad [Nödutgång SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1405: EventInfo(
        "Zone inhibit [Line Zone]",
        "Sektion spärrad [Linje SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1406: EventInfo(
        "Zone inhibit [Panic Zone]",
        "Sektion spärrad [Bråklarm SEKTION]",
        "Zone ID",
        "PB",
        "570/1",
    ),
    1407: EventInfo(
        "Zone inhibit [Holdup Zone]",
        "Sektion spärrad [Överfall SEKTION]",
        "Zone ID",
        "HB",
        "570/1",
    ),
    1408: EventInfo(
        "Zone inhibit [Tamper Zone]",
        "Sektion spärrad [SABOTAGE SEKTION]",
        "Zone ID",
        "TB",
        "570/1",
    ),
    1409: EventInfo(
        "Zone inhibit [Tech Zone]",
        "Sektion spärrad [Tekniskt larm SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1410: EventInfo(
        "Zone inhibit [Medical Zone]",
        "Sektion spärrad [Medicinskt SEKTION]",
        "Zone ID",
        "MB",
        "570/1",
    ),
    1411: EventInfo(
        "Zone inhibit [Keyarm Zone]",
        "Sektion spärrad [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1412: EventInfo(
        "Zone inhibit [Unused Zone]",
        "Sektion spärrad [Används ej SEKTION]",
        "Zone ID",
        None,
        "570/1",
    ),
    1413: EventInfo(
        "Zone inhibit [Shunt Zone]",
        "Sektion spärrad [Förbikopplare SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1414: EventInfo(
        "Zone inhibit [X-Shunt Zone]",
        "Sektion spärrad [X-förbikopplare SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1415: EventInfo(
        "Zone inhibit [Detector Fault Zone]",
        "Sektion spärrad [Detektorfel SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1416: EventInfo(
        "Zone inhibit [Lock Supervision Zone]",
        "Sektion spärrad [Låskontroll SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1417: EventInfo(
        "Zone inhibit [Seismic Zone]",
        "Sektion spärrad [Seismisk SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1418: EventInfo(
        "Zone inhibit [All Okay Zone]",
        "Sektion spärrad [Allt OK SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1419: EventInfo(
        "Zone inhibit [Holdup Fault Zone]",
        "Sektion spärrad [Överfall fel SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1420: EventInfo(
        "Zone inhibit [Warning Fault Zone]",
        "Sektion spärrad [Varning fel SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1421: EventInfo(
        "Zone inhibit [Setting authorisation Zone]",
        "Sektion spärrad [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1422: EventInfo(
        "Zone inhibit [Lock element Zone]",
        "Sektion spärrad [Lås element SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1423: EventInfo(
        "Zone inhibit [Glass Break Zone]",
        "Sektion spärrad [Glaskross SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1500: EventInfo(
        "Zone deinhibit [Alarm Zone]",
        "Sektion ej spärrad [Larm SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1501: EventInfo(
        "Zone deinhibit [Entry/Exit Zone]",
        "Sektion ej spärrad [In/utpassering SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1502: EventInfo(
        "Zone deinhibit [Exit Term Zone]",
        "Sektion ej spärrad [Utpasseringstid SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1503: EventInfo(
        "Zone deinhibit [Fire Zone]",
        "Sektion ej spärrad [Brand SEKTION]",
        "Zone ID",
        "FU",
        "570/3",
    ),
    1504: EventInfo(
        "Zone deinhibit [Fire Exit Zone]",
        "Sektion ej spärrad [Nödutgång SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1505: EventInfo(
        "Zone deinhibit [Line Zone]",
        "Sektion ej spärrad [Linje SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1506: EventInfo(
        "Zone deinhibit [Panic Zone]",
        "Sektion ej spärrad [Bråklarm SEKTION]",
        "Zone ID",
        "PU",
        "570/3",
    ),
    1507: EventInfo(
        "Zone deinhibit [Holdup Zone]",
        "Sektion ej spärrad [Överfall SEKTION]",
        "Zone ID",
        "HU",
        "570/3",
    ),
    1508: EventInfo(
        "Zone deinhibit [Tamper Zone]",
        "Sektion ej spärrad [SABOTAGE SEKTION]",
        "Zone ID",
        "TU",
        "570/3",
    ),
    1509: EventInfo(
        "Zone deinhibit [Tech Zone]",
        "Sektion ej spärrad [Tekniskt larm SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1510: EventInfo(
        "Zone deinhibit [Medical Zone]",
        "Sektion ej spärrad [Medicinskt SEKTION]",
        "Zone ID",
        "MU",
        "570/3",
    ),
    1511: EventInfo(
        "Zone deinhibit [Keyarm Zone]",
        "Sektion ej spärrad [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1512: EventInfo(
        "Zone deinhibit [Unused Zone]",
        "Sektion ej spärrad [Används ej SEKTION]",
        "Zone ID",
        None,
        "570/3",
    ),
    1513: EventInfo(
        "Zone deinhibit [Shunt Zone]",
        "Sektion ej spärrad [Förbikopplare SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1514: EventInfo(
        "Zone deinhibit [X-Shunt Zone]",
        "Sektion ej spärrad [X-förbikopplare SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1515: EventInfo(
        "Zone deinhibit [Detector Fault Zone]",
        "Sektion ej spärrad [Detektorfel SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1516: EventInfo(
        "Zone deinhibit [Lock Supervision Zone]",
        "Sektion ej spärrad [Låskontroll SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1517: EventInfo(
        "Zone deinhibit [Seismic Zone]",
        "Sektion ej spärrad [Seismisk SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1518: EventInfo(
        "Zone deinhibit [All Okay Zone]",
        "Sektion ej spärrad [Allt OK SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1519: EventInfo(
        "Zone deinhibit [Holdup Fault Zone]",
        "Sektion ej spärrad [Överfall fel SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1520: EventInfo(
        "Zone deinhibit [Warning Fault Zone]",
        "Sektion ej spärrad [Varning fel SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1521: EventInfo(
        "Zone deinhibit [Setting authorisation Zone]",
        "Sektion ej spärrad [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1522: EventInfo(
        "Zone deinhibit [Lock element Zone]",
        "Sektion ej spärrad [Lås element SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1523: EventInfo(
        "Zone deinhibit [Glass Break Zone]",
        "Sektion ej spärrad [Glaskross SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1600: EventInfo(
        "Zone isolate [Alarm Zone]",
        "Sektion isolerad [Larm SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1601: EventInfo(
        "Zone isolate [Entry/Exit Zone]",
        "Sektion isolerad [In/utpassering SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1602: EventInfo(
        "Zone isolate [Exit Term Zone]",
        "Sektion isolerad [Utpasseringstid SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1603: EventInfo(
        "Zone isolate [Fire Zone]",
        "Sektion isolerad [Brand SEKTION]",
        "Zone ID",
        "FB",
        "570/1",
    ),
    1604: EventInfo(
        "Zone isolate [Fire Exit Zone]",
        "Sektion isolerad [Nödutgång SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1605: EventInfo(
        "Zone isolate [Line Zone]",
        "Sektion isolerad [Linje SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1606: EventInfo(
        "Zone isolate [Panic Zone]",
        "Sektion isolerad [Bråklarm SEKTION]",
        "Zone ID",
        "PB",
        "570/1",
    ),
    1607: EventInfo(
        "Zone isolate [Holdup Zone]",
        "Sektion isolerad [Överfall SEKTION]",
        "Zone ID",
        "HB",
        "570/1",
    ),
    1608: EventInfo(
        "Zone isolate [Tamper Zone]",
        "Sektion isolerad [SABOTAGE SEKTION]",
        "Zone ID",
        "TB",
        "570/1",
    ),
    1609: EventInfo(
        "Zone isolate [Tech Zone]",
        "Sektion isolerad [Tekniskt larm SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1610: EventInfo(
        "Zone isolate [Medical Zone]",
        "Sektion isolerad [Medicinskt SEKTION]",
        "Zone ID",
        "MB",
        "570/1",
    ),
    1611: EventInfo(
        "Zone isolate [Keyarm Zone]",
        "Sektion isolerad [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1612: EventInfo(
        "Zone isolate [Unused Zone]",
        "Sektion isolerad [Används ej SEKTION]",
        "Zone ID",
        None,
        "570/1",
    ),
    1613: EventInfo(
        "Zone isolate [Shunt Zone]",
        "Sektion isolerad [Förbikopplare SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1614: EventInfo(
        "Zone isolate [X-Shunt Zone]",
        "Sektion isolerad [X-förbikopplare SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1615: EventInfo(
        "Zone isolate [Detector Fault Zone]",
        "Sektion isolerad [Detektorfel SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1616: EventInfo(
        "Zone isolate [Lock Supervision Zone]",
        "Sektion isolerad [Låskontroll SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1617: EventInfo(
        "Zone isolate [Seismic Zone]",
        "Sektion isolerad [Seismisk SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1618: EventInfo(
        "Zone isolate [All Okay Zone]",
        "Sektion isolerad [Allt OK SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1619: EventInfo(
        "Zone isolate [Holdup Fault Zone]",
        "Sektion isolerad [Överfall fel SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1620: EventInfo(
        "Zone isolate [Warning Fault Zone]",
        "Sektion isolerad [Varning fel SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1621: EventInfo(
        "Zone isolate [Setting authorisation Zone]",
        "Sektion isolerad [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1622: EventInfo(
        "Zone isolate [Lock element Zone]",
        "Sektion isolerad [Lås element SEKTION]",
        "Zone ID",
        "UB",
        "570/1",
    ),
    1623: EventInfo(
        "Zone isolate [Glass Break Zone]",
        "Sektion isolerad [Glaskross SEKTION]",
        "Zone ID",
        "BB",
        "570/1",
    ),
    1700: EventInfo(
        "Zone deisolate [Alarm Zone]",
        "Sektion ej isolerad [Larm SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1701: EventInfo(
        "Zone deisolate [Entry/Exit Zone]",
        "Sektion ej isolerad [In/utpassering SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1702: EventInfo(
        "Zone deisolate [Exit Term Zone]",
        "Sektion ej isolerad [Utpasseringstid SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1703: EventInfo(
        "Zone deisolate [Fire Zone]",
        "Sektion ej isolerad [Brand SEKTION]",
        "Zone ID",
        "FU",
        "570/3",
    ),
    1704: EventInfo(
        "Zone deisolate [Fire Exit Zone]",
        "Sektion ej isolerad [Nödutgång SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1705: EventInfo(
        "Zone deisolate [Line Zone]",
        "Sektion ej isolerad [Linje SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1706: EventInfo(
        "Zone deisolate [Panic Zone]",
        "Sektion ej isolerad [Bråklarm SEKTION]",
        "Zone ID",
        "PU",
        "570/3",
    ),
    1707: EventInfo(
        "Zone deisolate [Holdup Zone]",
        "Sektion ej isolerad [Överfall SEKTION]",
        "Zone ID",
        "HU",
        "570/3",
    ),
    1708: EventInfo(
        "Zone deisolate [Tamper Zone]",
        "Sektion ej isolerad [SABOTAGE SEKTION]",
        "Zone ID",
        "TU",
        "570/3",
    ),
    1709: EventInfo(
        "Zone deisolate [Tech Zone]",
        "Sektion ej isolerad [Tekniskt larm SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1710: EventInfo(
        "Zone deisolate [Medical Zone]",
        "Sektion ej isolerad [Medicinskt SEKTION]",
        "Zone ID",
        "MU",
        "570/3",
    ),
    1711: EventInfo(
        "Zone deisolate [Keyarm Zone]",
        "Sektion ej isolerad [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1712: EventInfo(
        "Zone deisolate [Unused Zone]",
        "Sektion ej isolerad [Används ej SEKTION]",
        "Zone ID",
        None,
        "570/3",
    ),
    1713: EventInfo(
        "Zone deisolate [Shunt Zone]",
        "Sektion ej isolerad [Förbikopplare SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1714: EventInfo(
        "Zone deisolate [X-Shunt Zone]",
        "Sektion ej isolerad [X-förbikopplare SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1715: EventInfo(
        "Zone deisolate [Detector Fault Zone]",
        "Sektion ej isolerad [Detektorfel SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1716: EventInfo(
        "Zone deisolate [Lock Supervision Zone]",
        "Sektion ej isolerad [Låskontroll SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1717: EventInfo(
        "Zone deisolate [Seismic Zone]",
        "Sektion ej isolerad [Seismisk SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1718: EventInfo(
        "Zone deisolate [All Okay Zone]",
        "Sektion ej isolerad [Allt OK SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1719: EventInfo(
        "Zone deisolate [Holdup Fault Zone]",
        "Sektion ej isolerad [Överfall fel SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1720: EventInfo(
        "Zone deisolate [Warning Fault Zone]",
        "Sektion ej isolerad [Varning fel SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1721: EventInfo(
        "Zone deisolate [Setting authorisation Zone]",
        "Sektion ej isolerad [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1722: EventInfo(
        "Zone deisolate [Lock element Zone]",
        "Sektion ej isolerad [Lås element SEKTION]",
        "Zone ID",
        "UU",
        "570/3",
    ),
    1723: EventInfo(
        "Zone deisolate [Glass Break Zone]",
        "Sektion ej isolerad [Glaskross SEKTION]",
        "Zone ID",
        "BU",
        "570/3",
    ),
    1800: EventInfo(
        "Trouble [Alarm Zone]", "Antimask [Larm SEKTION]", "Zone ID", "UT", "150/1"
    ),
    1801: EventInfo(
        "Trouble [Entry/Exit Zone]",
        "Antimask [In/utpassering SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1802: EventInfo(
        "Trouble [Exit Term Zone]",
        "Antimask [Utpasseringstid SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1803: EventInfo(
        "Trouble [Fire Zone]", "Antimask [Brand SEKTION]", "Zone ID", "UT", "150/1"
    ),
    1804: EventInfo(
        "Trouble [Fire Exit Zone]",
        "Antimask [Nödutgång SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1805: EventInfo(
        "Trouble [Line Zone]", "Antimask [Linje SEKTION]", "Zone ID", "UT", "150/1"
    ),
    1806: EventInfo(
        "Trouble [Panic Zone]", "Antimask [Bråklarm SEKTION]", "Zone ID", "UT", "150/1"
    ),
    1807: EventInfo(
        "Trouble [Holdup Zone]", "Antimask [Överfall SEKTION]", "Zone ID", "UT", "150/1"
    ),
    1808: EventInfo(
        "Trouble [Tamper Zone]", "Antimask [SABOTAGE SEKTION]", "Zone ID", "UT", "150/1"
    ),
    1809: EventInfo(
        "Trouble [Tech Zone]",
        "Antimask [Tekniskt larm SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1810: EventInfo(
        "Trouble [Medical Zone]",
        "Antimask [Medicinskt SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1811: EventInfo(
        "Trouble [Keyarm Zone]",
        "Antimask [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1812: EventInfo(
        "Trouble [Unused Zone]",
        "Antimask [Används ej SEKTION]",
        "Zone ID",
        None,
        "150/1",
    ),
    1813: EventInfo(
        "Trouble [Shunt Zone]",
        "Antimask [Förbikopplare SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1814: EventInfo(
        "Trouble [X-Shunt Zone]",
        "Antimask [X-förbikopplare SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1815: EventInfo(
        "Trouble [Detector Fault Zone]",
        "Antimask [Detektorfel SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1816: EventInfo(
        "Trouble [Lock Supervision Zone]",
        "Antimask [Låskontroll SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1817: EventInfo(
        "Trouble [Seismic Zone]",
        "Antimask [Seismisk SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1818: EventInfo(
        "Trouble [All Okay Zone]",
        "Antimask [Allt OK SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1819: EventInfo(
        "Trouble [Holdup Fault Zone]",
        "Antimask [Överfall fel SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1820: EventInfo(
        "Trouble [Warning Fault Zone]",
        "Antimask [Varning fel SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1821: EventInfo(
        "Trouble [Setting authorisation Zone]",
        "Antimask [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1822: EventInfo(
        "Trouble [Lock element Zone]",
        "Antimask [Lås element SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1823: EventInfo(
        "Trouble [Glass Break Zone]",
        "Antimask [Glaskross SEKTION]",
        "Zone ID",
        "UT",
        "150/1",
    ),
    1900: EventInfo(
        "Trouble restore [Alarm Zone]",
        "Antimask återställd [Larm SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1901: EventInfo(
        "Trouble restore [Entry/Exit Zone]",
        "Antimask återställd [In/utpassering SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1902: EventInfo(
        "Trouble restore [Exit Term Zone]",
        "Antimask återställd [Utpasseringstid SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1903: EventInfo(
        "Trouble restore [Fire Zone]",
        "Antimask återställd [Brand SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1904: EventInfo(
        "Trouble restore [Fire Exit Zone]",
        "Antimask återställd [Nödutgång SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1905: EventInfo(
        "Trouble restore [Line Zone]",
        "Antimask återställd [Linje SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1906: EventInfo(
        "Trouble restore [Panic Zone]",
        "Antimask återställd [Bråklarm SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1907: EventInfo(
        "Trouble restore [Holdup Zone]",
        "Antimask återställd [Överfall SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1908: EventInfo(
        "Trouble restore [Tamper Zone]",
        "Antimask återställd [SABOTAGE SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1909: EventInfo(
        "Trouble restore [Tech Zone]",
        "Antimask återställd [Tekniskt larm SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1910: EventInfo(
        "Trouble restore [Medical Zone]",
        "Antimask återställd [Medicinskt SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1911: EventInfo(
        "Trouble restore [Keyarm Zone]",
        "Antimask återställd [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1912: EventInfo(
        "Trouble restore [Unused Zone]",
        "Antimask återställd [Används ej SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1913: EventInfo(
        "Trouble restore [Shunt Zone]",
        "Antimask återställd [Förbikopplare SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1914: EventInfo(
        "Trouble restore [X-Shunt Zone]",
        "Antimask återställd [X-förbikopplare SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1915: EventInfo(
        "Trouble restore [Detector Fault Zone]",
        "Antimask återställd [Detektorfel SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1916: EventInfo(
        "Trouble restore [Lock Supervision Zone]",
        "Antimask återställd [Låskontroll SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1917: EventInfo(
        "Trouble restore [Seismic Zone]",
        "Antimask återställd [Seismisk SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1918: EventInfo(
        "Trouble restore [All Okay Zone]",
        "Antimask återställd [Allt OK SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1919: EventInfo(
        "Trouble restore [Holdup Fault Zone]",
        "Antimask återställd [Överfall fel SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1920: EventInfo(
        "Trouble restore [Warning Fault Zone]",
        "Antimask återställd [Varning fel SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1921: EventInfo(
        "Trouble restore [Setting authorisation Zone]",
        "Antimask återställd [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1922: EventInfo(
        "Trouble restore [Lock element Zone]",
        "Antimask återställd [Lås element SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    1923: EventInfo(
        "Trouble restore [Glass Break Zone]",
        "Antimask återställd [Glaskross SEKTION]",
        "Zone ID",
        "UJ",
        "150/3",
    ),
    2000: EventInfo(
        "Zone walked [Alarm Zone]",
        "Sektion gångtestad [Larm SEKTION]",
        "Zone ID",
        "TP",
        "613/1",
    ),
    2001: EventInfo(
        "Zone walked [Entry/Exit Zone]",
        "Sektion gångtestad [In/utpassering SEKTION]",
        "Zone ID",
        "TP",
        "613/1",
    ),
    2002: EventInfo(
        "Zone walked [Exit Term Zone]",
        "Sektion gångtestad [Utpasseringstid SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2003: EventInfo(
        "Zone walked [Fire Zone]",
        "Sektion gångtestad [Brand SEKTION]",
        "Zone ID",
        "TP",
        "614/1",
    ),
    2004: EventInfo(
        "Zone walked [Fire Exit Zone]",
        "Sektion gångtestad [Nödutgång SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2005: EventInfo(
        "Zone walked [Line Zone]",
        "Sektion gångtestad [Linje SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2006: EventInfo(
        "Zone walked [Panic Zone]",
        "Sektion gångtestad [Bråklarm SEKTION]",
        "Zone ID",
        "TP",
        "615/1",
    ),
    2007: EventInfo(
        "Zone walked [Holdup Zone]",
        "Sektion gångtestad [Överfall SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2008: EventInfo(
        "Zone walked [Tamper Zone]",
        "Sektion gångtestad [SABOTAGE SEKTION]",
        "Zone ID",
        "TP",
        "613/1",
    ),
    2009: EventInfo(
        "Zone walked [Tech Zone]",
        "Sektion gångtestad [Tekniskt larm SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2010: EventInfo(
        "Zone walked [Medical Zone]",
        "Sektion gångtestad [Medicinskt SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2011: EventInfo(
        "Zone walked [Keyarm Zone]",
        "Sektion gångtestad [Nyckeltillkoppling SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2012: EventInfo(
        "Zone walked [Unused Zone]",
        "Sektion gångtestad [Används ej SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2013: EventInfo(
        "Zone walked [Shunt Zone]",
        "Sektion gångtestad [Förbikopplare SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2014: EventInfo(
        "Zone walked [X-Shunt Zone]",
        "Sektion gångtestad [X-förbikopplare SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2015: EventInfo(
        "Zone walked [Detector Fault Zone]",
        "Sektion gångtestad [Detektorfel SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2016: EventInfo(
        "Zone walked [Lock Supervision Zone]",
        "Sektion gångtestad [Låskontroll SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2017: EventInfo(
        "Zone walked [Seismic Zone]",
        "Sektion gångtestad [Seismisk SEKTION]",
        "Zone ID",
        "TP",
        "613/1",
    ),
    2018: EventInfo(
        "Zone walked [All Okay Zone]",
        "Sektion gångtestad [Allt OK SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2019: EventInfo(
        "Zone walked [Holdup Fault Zone]",
        "Sektion gångtestad [Överfall fel SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2020: EventInfo(
        "Zone walked [Warning Fault Zone]",
        "Sektion gångtestad [Varning fel SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2021: EventInfo(
        "Zone walked [Setting authorisation Zone]",
        "Sektion gångtestad [Tillkopplingstillstånd SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2022: EventInfo(
        "Zone walked [Lock element Zone]",
        "Sektion gångtestad [Lås element SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2023: EventInfo(
        "Zone walked [Glass Break Zone]",
        "Sektion gångtestad [Glaskross SEKTION]",
        "Zone ID",
        "TP",
        None,
    ),
    2024: EventInfo("SEISMIC TEST OK", "SEISMISK TEST OK", "Zone ID", "BX", "750/1"),
    2025: EventInfo("SEISMIC TEST FAIL", "SEISMISK TEST FEL", "Zone ID", "BF", "751/1"),
    2100: EventInfo("Zone input open", "Sektionsingång öppen", "Zone ID", "ZO", None),
    2101: EventInfo(
        "Zone input closed", "Sektionsingång sluten", "Zone ID", "ZC", None
    ),
    2102: EventInfo(
        "Zone input shorted", "Sektionsingång kortsluten", "Zone ID", "ZX", None
    ),
    2103: EventInfo(
        "Zone input disconnected", "Sektionsingång bortkopplad", "Zone ID", "ZD", None
    ),
    2104: EventInfo(
        "Zone input masked", "Sektionsingång antimask", "Zone ID", "ZM", None
    ),
    2105: EventInfo("Zone input fault", "Sektionsingångsfel", "Zone ID", "ZF", None),
    2106: EventInfo(
        "Zone input unstable", "Sektionsingång ostabil", "Zone ID", "ZN", None
    ),
    2107: EventInfo(
        "Zone input out of bounds",
        "Sektionsingång ogiltigt värde",
        "Zone ID",
        None,
        None,
    ),
    2108: EventInfo("Zone Low battery", "Sektion lågt batteri", "Zone ID", "XT", None),
    2109: EventInfo(
        "Zone Low battery - Restored",
        "Sektion lågt batteri återställd",
        "Zone ID",
        "XR",
        None,
    ),
    2110: EventInfo("Zone input open", "Sektionsingång öppen", "Zone ID", "ZO", None),
    2111: EventInfo(
        "Zone input closed", "Sektionsingång sluten", "Zone ID", "ZC", None
    ),
    2112: EventInfo(
        "Zone input shorted", "Sektionsingång kortsluten", "Zone ID", "ZX", None
    ),
    2113: EventInfo(
        "Zone input disconnected", "Sektionsingång bortkopplad", "Zone ID", "ZD", None
    ),
    2114: EventInfo(
        "Zone input masked", "Sektionsingång antimask", "Zone ID", "ZM", None
    ),
    2115: EventInfo("Zone input fault", "Sektionsingångsfel", "Zone ID", "ZF", None),
    2116: EventInfo(
        "Zone input unstable", "Sektionsingång ostabil", "Zone ID", "ZN", None
    ),
    2117: EventInfo(
        "Zone input out of bounds",
        "Sektionsingång ogiltigt värde",
        "Zone ID",
        None,
        None,
    ),
    3000: EventInfo("Entry Granted", "Inpassage godkänd", "Door ID", "DG", None),
    3001: EventInfo("Entry Denied", "Inpassage nekad", "Door ID", "DD", None),
    3002: EventInfo("Exit Granted", "Utpassage godkänd", "Door ID", "DG", None),
    3003: EventInfo("Exit Denied", "Utpassage nekad", "Door ID", "DD", None),
    3004: EventInfo(
        "Door Open too long", "Dörr öppen för länge", "Door ID", "DN", None
    ),
    3005: EventInfo("Left open", "Lämnad öppen", "Door ID", "DN", None),
    3006: EventInfo("Door Forced Open", "Forcerad öppning", "Door ID", "DF", None),
    3007: EventInfo("Door Normal", "Dörr i normalläge", "Door ID", "DO", None),
    3008: EventInfo("Door Locked", "Dörr låst", "Door ID", "DC", None),
    3009: EventInfo("Door Unlocked", "Dörr olåst", "Door ID", "DO", None),
    3010: EventInfo("Door Open", "Dörr öppen", "Door ID", "DO", None),
    3011: EventInfo("Door Closed", "Dörr stängd", "Door ID", None, None),
    3012: EventInfo("Door Release", "DRS Öppnaknapp", "Door ID", "DX", None),
    3013: EventInfo("Alarm restore", "LARMÅTERSTÄLL.", "Door ID", "DR", None),
    3014: EventInfo("Unknown card", "Okänt kort", "Door ID", "AU", None),
    3015: EventInfo("Reader locked", "Läsare spärrad", "Door ID", "RL", None),
    3016: EventInfo("Reader unlocked", "Läsare olåst", "Door ID", "RG", None),
    3500: EventInfo("Alarm Confirmed", "Larm Veriferat", "Area ID", "BV", "139/1"),
    3501: EventInfo("Unset", "Frånkoppla", "Area ID", "OG", "401/1"),
    3502: EventInfo("Partset A", "Deltillkoppling A", "Area ID", "NL", "456/3"),
    3503: EventInfo("Partset B", "Deltillkoppling B", "Area ID", "NL", "456/3"),
    3504: EventInfo("Fullset", "Tillkoppla", "Area ID", "CG", "401/3"),
    3505: EventInfo("Remote Unset", "Fjärr Frånkoppla", "User ID", "OQ", None),
    3506: EventInfo(
        "Remote Partset A", "Fjärr Deltillkoppling A", "Area ID", None, None
    ),
    3507: EventInfo(
        "Remote Partset B", "Fjärr Deltillkoppling B", "Area ID", None, None
    ),
    3508: EventInfo("Remote Fullset", "Fjärr Tillkoppla", "User ID", "CQ", None),
    3509: EventInfo(
        "Keyarm [Unset Zone]",
        "Nyckeltillkoppling [Frånkoppla SEKTION]",
        "Zone ID",
        "OS",
        None,
    ),
    3510: EventInfo(
        "Keyarm [Fullset Zone]",
        "Nyckeltillkoppling [Tillkoppla SEKTION]",
        "Zone ID",
        "CS",
        None,
    ),
    3511: EventInfo("Fail to Set", "Tillkopplingsfel", "Area ID", "CI", "454/1"),
    3512: EventInfo(
        "Entry timeout", "TIMEOUT FÖR INPASSERINGSTID", "Area ID", None, None
    ),
    3513: EventInfo("Late to Set", "Sen tillkoppling", "Area ID", "OT", "452/1"),
    3514: EventInfo("Late to unset", "Sen frånkoppling", "Area ID", "CT", "452/1"),
    3515: EventInfo(
        "Post alarm Unset", "Efter larm Frånkoppla", "Area ID", "OG", "401/1"
    ),
    3516: EventInfo("Early to set", "Tidig tillkoppling", "User ID", "CK", "451/3"),
    3517: EventInfo("Early to unset", "Tidig frånkoppling", "User ID", "OK", "451/1"),
    3518: EventInfo(
        "Area Alarm Abort", "Område Larm Avbrutet", "User ID", "BC", "406/1"
    ),
    3519: EventInfo(
        "Area Walk test Start", "Område Gångtest", "Area ID", "ZK", "607/1"
    ),
    3520: EventInfo("Area Walk test End", "Område Gångtest", "Area ID", "TC", "607/3"),
    3521: EventInfo(
        "All Areas Fullset", "Alla områden Tillkoppla", "Area ID", "CL", None
    ),
    3522: EventInfo(
        "All Areas Unset", "Alla områden Frånkoppla", "Area ID", "OP", None
    ),
    3523: EventInfo("Confirmed holdup", "Överfallslarm", "Area ID", "HV", "129/1"),
    3524: EventInfo(
        "Entry Timer Started", "Inpasseringstimer startad", "Area ID", None, None
    ),
    3525: EventInfo("Auto Set", "Automatisk Tillkoppling", "Area ID", "CP", "403/3"),
    3526: EventInfo("Auto Unset", "Automatisk Frånkoppling", "Area ID", "OA", "403/1"),
    3527: EventInfo(
        "Unset Delayed START", "Frånkoppling fördröjd START", "Area ID", None, None
    ),
    3528: EventInfo(
        "Unset Delayed CANCELLED",
        "Frånkoppling fördröjd AVBRUTEN",
        "Area ID",
        None,
        None,
    ),
    4000: EventInfo("User Duress", "Användare Hotlarm", "User ID", "HA", "121/1"),
    4001: EventInfo(
        "User Duress Restore", "Användare Hotlarm Återställ", "User ID", "HR", "121/3"
    ),
    4002: EventInfo("USER PANIC", "ANVÄNDARE BRÅKLARM", "User ID", "PA", "120/1"),
    4003: EventInfo("User accessing", "Användare loggar in", "User ID", "JP", None),
    4004: EventInfo("User accessing end", "Användare loggar ut", "User ID", "ZG", None),
    4005: EventInfo(
        "Fob low batt Fault", "FOB LÅGT BATTERI Fel", "User ID", "XT", None
    ),
    4006: EventInfo(
        "Fob low batt Restore", "FOB LÅGT BATTERI Återställ", "User ID", "XR", None
    ),
    4007: EventInfo("User code changed", "Användarkod ändrad", "User ID", "JV", None),
    4008: EventInfo(
        "USER PANIC Restore", "ANVÄNDARE BRÅKLARM Återställ", "User ID", "PR", "120/3"
    ),
    4009: EventInfo("User Medic", "Användarmedicinskt larm", "User ID", "MA", "100/1"),
    4010: EventInfo(
        "User Medic Restore",
        "Användarmedicinskt larm Återställ",
        "User ID",
        "MR",
        "100/3",
    ),
    4011: EventInfo("User Holdup", "Användaröverfall", "User ID", "HA", "120/1"),
    4012: EventInfo(
        "User Holdup Restore", "Användaröverfall Återställ", "User ID", "HR", "120/3"
    ),
    4013: EventInfo(
        "User Webpass Changed", "Användarwebbkod ändrad", "User ID", "JV", None
    ),
    4014: EventInfo("Grant Access", "Bevilja åtkomst", "User ID", None, None),
    4015: EventInfo(
        "Engineer access revoked", "Installatörsläge upphävt", "User ID", None, None
    ),
    4100: EventInfo("MDT PANIC", "MDT BRÅKLARM", "User ID", "PA", "120/1"),
    4101: EventInfo("MDT TILT", "MDT TILT", "User ID", "MA", "100/1"),
    4102: EventInfo("MDT BELT", "MDT BÄLTE", "User ID", "HA", "120/1"),
    4103: EventInfo(
        "Man down panic Restore",
        "Man down bråklarm Återställ",
        "User ID",
        "PR",
        "120/3",
    ),
    4104: EventInfo("MDT TILT Restore", "MDT TILT Återställ", "User ID", "MR", "100/3"),
    4105: EventInfo(
        "MDT BELT Restore", "MDT BÄLTE Återställ", "User ID", "HR", "120/3"
    ),
    4106: EventInfo("MDT TAMPER", "MDT SABOTAGE", "User ID", None, None),
    4200: EventInfo("WPA Panic", "WPA BRÅKL.", "WPA ID", "PA", "120/1"),
    4201: EventInfo(
        "WPA Panic Restore", "WPA BRÅKL. Återställ", "WPA ID", "PR", "120/3"
    ),
    4202: EventInfo("WPA Holdup", "WPA ÖF", "WPA ID", "HA", "120/1"),
    4203: EventInfo("WPA Holdup Restore", "WPA ÖF Återställ", "WPA ID", "HR", "120/3"),
    4204: EventInfo("WPA suspicion", "WPA MISSTANKE", "WPA ID", None, None),
    4205: EventInfo(
        "WPA suspicion Restore", "WPA MISSTANKE Återställ", "WPA ID", None, None
    ),
    4206: EventInfo("WPA Medical", "WPA Medicin larm", "WPA ID", "MA", "100/1"),
    4207: EventInfo(
        "WPA Medical Restore", "WPA Medicin larm Återställ", "WPA ID", "MR", "100/3"
    ),
    5000: EventInfo("PSU Mains Fault", "PSU 230V AC Fel", "-", "AT", "301/1"),
    5001: EventInfo("PSU Mains Restore", "PSU 230V AC Återställ", "-", "AR", "301/3"),
    5002: EventInfo("PSU Mains Inhibit", "PSU 230V AC Spärra", "-", None, None),
    5003: EventInfo(
        "PSU Mains Deinhibit", "PSU 230V AC Ta bort bortkoppling", "-", None, None
    ),
    5004: EventInfo("PSU Mains Isolate", "PSU 230V AC Isolera", "-", None, None),
    5005: EventInfo(
        "PSU Mains Deisolate", "PSU 230V AC Ta bort isolering", "-", None, None
    ),
    5006: EventInfo("PSU Battery Fault", "PSU Batteri Fel", "-", "YT", "311/1"),
    5007: EventInfo("PSU Battery Restore", "PSU Batteri Återställ", "-", "YR", "311/3"),
    5008: EventInfo("PSU Battery Inhibit", "PSU Batteri Spärra", "-", None, None),
    5009: EventInfo(
        "PSU Battery Deinhibit", "PSU Batteri Ta bort bortkoppling", "-", None, None
    ),
    5010: EventInfo("PSU Battery Isolate", "PSU Batteri Isolera", "-", None, None),
    5011: EventInfo(
        "PSU Battery Deisolate", "PSU Batteri Ta bort isolering", "-", None, None
    ),
    5012: EventInfo("PSU EXT Fuse Fault", "PSU EXT säkring Fel", "-", "YP", "312/1"),
    5013: EventInfo(
        "PSU EXT Fuse Restore", "PSU EXT säkring Återställ", "-", "YQ", "312/3"
    ),
    5014: EventInfo("PSU EXT Fuse Inhibit", "PSU EXT säkring Spärra", "-", None, None),
    5015: EventInfo(
        "PSU EXT Fuse Deinhibit",
        "PSU EXT säkring Ta bort bortkoppling",
        "-",
        None,
        None,
    ),
    5016: EventInfo("PSU EXT Fuse Isolate", "PSU EXT säkring Isolera", "-", None, None),
    5017: EventInfo(
        "PSU EXT Fuse Deisolate", "PSU EXT säkring Ta bort isolering", "-", None, None
    ),
    5018: EventInfo("PSU INT Fuse Fault", "PSU INT säkring Fel", "-", "YP", "312/1"),
    5019: EventInfo(
        "PSU INT Fuse Restore", "PSU INT säkring Återställ", "-", "YQ", "312/3"
    ),
    5020: EventInfo("PSU INT Fuse Inhibit", "PSU INT säkring Spärra", "-", None, None),
    5021: EventInfo(
        "PSU INT Fuse Deinhibit",
        "PSU INT säkring Ta bort bortkoppling",
        "-",
        None,
        None,
    ),
    5022: EventInfo("PSU INT Fuse Isolate", "PSU INT säkring Isolera", "-", None, None),
    5023: EventInfo(
        "PSU INT Fuse Deisolate", "PSU INT säkring Ta bort isolering", "-", None, None
    ),
    5024: EventInfo(
        "PSU Aux. Fuse Fault", "PSU AUX-utgång, säkring Fel", "-", "YP", "312/1"
    ),
    5025: EventInfo(
        "PSU Aux. Fuse Restore", "PSU AUX-utgång, säkring Återställ", "-", "YQ", "312/3"
    ),
    5026: EventInfo(
        "PSU Aux. Fuse Inhibit", "PSU AUX-utgång, säkring Spärra", "-", None, None
    ),
    5027: EventInfo(
        "PSU Aux. Fuse Deinhibit",
        "PSU AUX-utgång, säkring Ta bort bortkoppling",
        "-",
        None,
        None,
    ),
    5028: EventInfo(
        "PSU Aux. Fuse Isolate", "PSU AUX-utgång, säkring Isolera", "-", None, None
    ),
    5029: EventInfo(
        "PSU Aux. Fuse Deisolate",
        "PSU AUX-utgång, säkring Ta bort isolering",
        "-",
        None,
        None,
    ),
    5030: EventInfo("PSU Fault Fault", "PSU Fel Fel", "-", "YP", "300/1"),
    5031: EventInfo("PSU Fault Restore", "PSU Fel Återställ", "-", "YQ", "300/3"),
    5032: EventInfo("PSU Fault Inhibit", "PSU Fel Spärra", "-", None, None),
    5033: EventInfo(
        "PSU Fault Deinhibit", "PSU Fel Ta bort bortkoppling", "-", None, None
    ),
    5034: EventInfo("PSU Fault Isolate", "PSU Fel Isolera", "-", None, None),
    5035: EventInfo(
        "PSU Fault Deisolate", "PSU Fel Ta bort isolering", "-", None, None
    ),
    5036: EventInfo("PSU Output fault", "PSU utgångsfel", "Expander", "OU", None),
    5037: EventInfo("PSU Output ok", "PSU utgång ok", "Expander", "OV", None),
    5038: EventInfo(
        "PSU Low Voltage Trouble", "PSU låg volt fel", "Expander", "XB", None
    ),
    5039: EventInfo(
        "PSU Low Voltage Restoral", "PSU låg volt återställd", "Expander", "XC", None
    ),
    5040: EventInfo("Low battery Fault", "Lågt batteri Fel", "Expander", "XD", None),
    5041: EventInfo(
        "Low battery Restore", "Lågt batteri Återställ", "Expander", "XG", None
    ),
    5042: EventInfo("PSU Discharged", "PSU urladdad", "Expander", "XK", None),
    5100: EventInfo("RF JAM Fault", "RF-STÖR. Fel", "-", "XQ", "344/1"),
    5101: EventInfo("RF JAM Restore", "RF-STÖR. Återställ", "-", "XH", "344/3"),
    5102: EventInfo("RF JAM Inhibit", "RF-STÖR. Spärra", "-", None, None),
    5103: EventInfo(
        "RF JAM Deinhibit", "RF-STÖR. Ta bort bortkoppling", "-", None, None
    ),
    5104: EventInfo("RF JAM Isolate", "RF-STÖR. Isolera", "-", None, None),
    5105: EventInfo("RF JAM Deisolate", "RF-STÖR. Ta bort isolering", "-", None, None),
    5106: EventInfo("Antenna Tamper Fault", "Antennsabotage Fel", "-", "XS", None),
    5107: EventInfo(
        "Antenna Tamper Restore", "Antennsabotage Återställ", "-", "XJ", None
    ),
    5108: EventInfo("Antenna Tamper Inhibit", "Antennsabotage Spärra", "-", None, None),
    5109: EventInfo(
        "Antenna Tamper Deinhibit",
        "Antennsabotage Ta bort bortkoppling",
        "-",
        None,
        None,
    ),
    5110: EventInfo(
        "Antenna Tamper Isolate", "Antennsabotage Isolera", "-", None, None
    ),
    5111: EventInfo(
        "Antenna Tamper Deisolate", "Antennsabotage Ta bort isolering", "-", None, None
    ),
    5200: EventInfo("Bell Tamper Fault", "Sirensabotage Fel", "-", "YA", "320/1"),
    5201: EventInfo(
        "Bell Tamper Restore", "Sirensabotage Återställ", "-", "YH", "320/3"
    ),
    5202: EventInfo("Bell Tamper Inhibit", "Sirensabotage Spärra", "-", None, None),
    5203: EventInfo(
        "Bell Tamper Deinhibit", "Sirensabotage Ta bort bortkoppling", "-", None, None
    ),
    5204: EventInfo("Bell Tamper Isolate", "Sirensabotage Isolera", "-", None, None),
    5205: EventInfo(
        "Bell Tamper Deisolate", "Sirensabotage Ta bort isolering", "-", None, None
    ),
    5206: EventInfo(
        "Cabinet Tamper Fault", "Kapslingssabotage Fel", "-", "TA", "137/1"
    ),
    5207: EventInfo(
        "Cabinet Tamper Restore", "Kapslingssabotage Återställ", "-", "TR", "137/3"
    ),
    5208: EventInfo(
        "Cabinet Tamper Inhibit", "Kapslingssabotage Spärra", "-", None, None
    ),
    5209: EventInfo(
        "Cabinet Tamper Deinhibit",
        "Kapslingssabotage Ta bort bortkoppling",
        "-",
        None,
        None,
    ),
    5210: EventInfo(
        "Cabinet Tamper Isolate", "Kapslingssabotage Isolera", "-", None, None
    ),
    5211: EventInfo(
        "Cabinet Tamper Deisolate",
        "Kapslingssabotage Ta bort isolering",
        "-",
        None,
        None,
    ),
    5212: EventInfo("AUX 1 Tamper Fault", "AUX-UTG 1, SAB Fel", "-", "TA", "137/1"),
    5213: EventInfo(
        "AUX 1 Tamper Restore", "AUX-UTG 1, SAB Återställ", "-", "TR", "137/3"
    ),
    5214: EventInfo("AUX 1 Tamper Inhibit", "AUX-UTG 1, SAB Spärra", "-", None, None),
    5215: EventInfo(
        "AUX 1 Tamper Deinhibit", "AUX-UTG 1, SAB Ta bort bortkoppling", "-", None, None
    ),
    5216: EventInfo("AUX 1 Tamper Isolate", "AUX-UTG 1, SAB Isolera", "-", None, None),
    5217: EventInfo(
        "AUX 1 Tamper Deisolate", "AUX-UTG 1, SAB Ta bort isolering", "-", None, None
    ),
    5218: EventInfo("AUX 2 Tamper Fault", "AUX-UTG 2, SAB Fel", "-", "TA", "137/1"),
    5219: EventInfo(
        "AUX 2 Tamper Restore", "AUX-UTG 2, SAB Återställ", "-", "TR", "137/3"
    ),
    5220: EventInfo("AUX 2 Tamper Inhibit", "AUX-UTG 2, SAB Spärra", "-", None, None),
    5221: EventInfo(
        "AUX 2 Tamper Deinhibit", "AUX-UTG 2, SAB Ta bort bortkoppling", "-", None, None
    ),
    5222: EventInfo("AUX 2 Tamper Isolate", "AUX-UTG 2, SAB Isolera", "-", None, None),
    5223: EventInfo(
        "AUX 2 Tamper Deisolate", "AUX-UTG 2, SAB Ta bort isolering", "-", None, None
    ),
    5300: EventInfo("XBUS cable fault", "X-BUS-kabelfel", "-", "ES", "333/1"),
    5301: EventInfo(
        "XBUS cable fault Restore", "X-BUS-kabelfel Återställ", "-", "EJ", "333/3"
    ),
    5302: EventInfo(
        "XBUS cable fault Inhibit", "X-BUS-kabelfel Spärra", "-", None, None
    ),
    5303: EventInfo(
        "XBUS cable fault Deinhibit",
        "X-BUS-kabelfel Ta bort bortkoppling",
        "-",
        None,
        None,
    ),
    5304: EventInfo(
        "XBUS cable fault Isolate", "X-BUS-kabelfel Isolera", "-", None, None
    ),
    5305: EventInfo(
        "XBUS cable fault Deisolate",
        "X-BUS-kabelfel Ta bort isolering",
        "-",
        None,
        None,
    ),
    5306: EventInfo(
        "XBUS comms lost Fault", "XBUS KOMM. AVBR. Fel", "Expander", "EM", "333/1"
    ),
    5307: EventInfo(
        "XBUS comms lost Restore",
        "XBUS KOMM. AVBR. Återställ",
        "Expander",
        "EN",
        "333/3",
    ),
    5308: EventInfo(
        "XBUS comms lost Inhibit", "XBUS KOMM. AVBR. Spärra", "Expander", None, None
    ),
    5309: EventInfo(
        "XBUS comms lost Deinhibit",
        "XBUS KOMM. AVBR. Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5310: EventInfo(
        "XBUS comms lost Isolate", "XBUS KOMM. AVBR. Isolera", "Expander", None, None
    ),
    5311: EventInfo(
        "XBUS comms lost Deisolate",
        "XBUS KOMM. AVBR. Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5312: EventInfo(
        "XBUS tamper Fault", "XBUS, SABOTAGE Fel", "Expander", "ES", "341/1"
    ),
    5313: EventInfo(
        "XBUS tamper Restore", "XBUS, SABOTAGE Återställ", "Expander", "EJ", "341/3"
    ),
    5314: EventInfo(
        "XBUS tamper Inhibit", "XBUS, SABOTAGE Spärra", "Expander", None, None
    ),
    5315: EventInfo(
        "XBUS tamper Deinhibit",
        "XBUS, SABOTAGE Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5316: EventInfo(
        "XBUS tamper Isolate", "XBUS, SABOTAGE Isolera", "Expander", None, None
    ),
    5317: EventInfo(
        "XBUS tamper Deisolate",
        "XBUS, SABOTAGE Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5318: EventInfo("XBUS fuse fault", "XBUS, SÄKR. FEL", "Expander", "ET", "333/1"),
    5319: EventInfo(
        "XBUS fuse fault Restore",
        "XBUS, SÄKR. FEL Återställ",
        "Expander",
        "ER",
        "333/3",
    ),
    5320: EventInfo(
        "XBUS fuse fault Inhibit", "XBUS, SÄKR. FEL Spärra", "Expander", None, None
    ),
    5321: EventInfo(
        "XBUS fuse fault Deinhibit",
        "XBUS, SÄKR. FEL Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5322: EventInfo(
        "XBUS fuse fault Isolate", "XBUS, SÄKR. FEL Isolera", "Expander", None, None
    ),
    5323: EventInfo(
        "XBUS fuse fault Deisolate",
        "XBUS, SÄKR. FEL Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5324: EventInfo("XBUS mains fault", "XBUS, NÄTFEL", "Expander", "AT", "342/1"),
    5325: EventInfo(
        "XBUS mains fault Restore", "XBUS, NÄTFEL Återställ", "Expander", "AR", "342/3"
    ),
    5326: EventInfo(
        "XBUS mains fault Inhibit", "XBUS, NÄTFEL Spärra", "Expander", None, None
    ),
    5327: EventInfo(
        "XBUS mains fault Deinhibit",
        "XBUS, NÄTFEL Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5328: EventInfo(
        "XBUS mains fault Isolate", "XBUS, NÄTFEL Isolera", "Expander", None, None
    ),
    5329: EventInfo(
        "XBUS mains fault Deisolate",
        "XBUS, NÄTFEL Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5330: EventInfo(
        "XBUS battery Fault", "X-BUS, BATTERI Fel", "Expander", "ET", "338/1"
    ),
    5331: EventInfo(
        "XBUS battery Restore", "X-BUS, BATTERI Återställ", "Expander", "ER", "338/3"
    ),
    5332: EventInfo(
        "XBUS battery Inhibit", "X-BUS, BATTERI Spärra", "Expander", None, None
    ),
    5333: EventInfo(
        "XBUS battery Deinhibit",
        "X-BUS, BATTERI Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5334: EventInfo(
        "XBUS battery Isolate", "X-BUS, BATTERI Isolera", "Expander", None, None
    ),
    5335: EventInfo(
        "XBUS battery Deisolate",
        "X-BUS, BATTERI Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5336: EventInfo(
        "XBUS rf jamming Fault", "XBUS, RF-STÖR. Fel", "Expander", "XQ", "344/1"
    ),
    5337: EventInfo(
        "XBUS rf jamming Restore", "XBUS, RF-STÖR. Återställ", "Expander", "XH", "344/3"
    ),
    5338: EventInfo(
        "XBUS rf jamming Inhibit", "XBUS, RF-STÖR. Spärra", "Expander", None, None
    ),
    5339: EventInfo(
        "XBUS rf jamming Deinhibit",
        "XBUS, RF-STÖR. Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5340: EventInfo(
        "XBUS rf jamming Isolate", "XBUS, RF-STÖR. Isolera", "Expander", None, None
    ),
    5341: EventInfo(
        "XBUS rf jamming Deisolate",
        "XBUS, RF-STÖR. Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5342: EventInfo(
        "X-BUS Antenna Tamper Fault",
        "X-BUS Antennsabotage Fel",
        "Expander",
        "XS",
        "341/1",
    ),
    5343: EventInfo(
        "X-BUS Antenna Tamper Restore",
        "X-BUS Antennsabotage Återställ",
        "Expander",
        "XJ",
        "341/3",
    ),
    5344: EventInfo(
        "X-BUS Antenna Tamper Inhibit",
        "X-BUS Antennsabotage Spärra",
        "Expander",
        None,
        None,
    ),
    5345: EventInfo(
        "X-BUS Antenna Tamper Deinhibit",
        "X-BUS Antennsabotage Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5346: EventInfo(
        "X-BUS Antenna Tamper Isolate",
        "X-BUS Antennsabotage Isolera",
        "Expander",
        None,
        None,
    ),
    5347: EventInfo(
        "X-BUS Antenna Tamper Deisolate",
        "X-BUS Antennsabotage Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5348: EventInfo(
        "XBUS panic Alarm", "XBUS, BRÅKLARM Larm", "Expander", "PA", "120/1"
    ),
    5349: EventInfo(
        "XBUS panic Restore", "XBUS, BRÅKLARM Återställ", "Expander", "PR", "120/3"
    ),
    5350: EventInfo("XBUS fire Alarm", "XBUS, BRAND Larm", "Expander", "FA", "110/1"),
    5351: EventInfo(
        "XBUS fire Restore", "XBUS, BRAND Återställ", "Expander", "FR", "110/3"
    ),
    5352: EventInfo(
        "XBUS medical Alarm", "XBUS, MEDICIN Larm", "Expander", "MA", "100/1"
    ),
    5353: EventInfo(
        "XBUS medical Restore", "XBUS, MEDICIN Återställ", "Expander", "MR", "100/3"
    ),
    5354: EventInfo("XBUS PSU Fault", "XBUS, PSU-FEL", "Expander", "ET", "330/1"),
    5355: EventInfo(
        "XBUS PSU Fault Restore", "XBUS, PSU-FEL Återställ", "Expander", "ER", "330/3"
    ),
    5356: EventInfo(
        "XBUS PSU Fault Inhibit", "XBUS, PSU-FEL Spärra", "Expander", None, None
    ),
    5357: EventInfo(
        "XBUS PSU Fault Deinhibit",
        "XBUS, PSU-FEL Ta bort bortkoppling",
        "Expander",
        None,
        None,
    ),
    5358: EventInfo(
        "XBUS PSU Fault Isolate", "XBUS, PSU-FEL Isolera", "Expander", None, None
    ),
    5359: EventInfo(
        "XBUS PSU Fault Deisolate",
        "XBUS, PSU-FEL Ta bort isolering",
        "Expander",
        None,
        None,
    ),
    5360: EventInfo("Keypad locked", "Manöverpanel LÅST", "Expander", "ZE", None),
    5361: EventInfo(
        "Keypad Not Locked Out", "Manöverpanel Inte spärrad", "Expander", "KG", None
    ),
    5362: EventInfo("WEB locked", "WEB LÅST", "-", "WW", None),
    5363: EventInfo("WEB Not Locked Out", "WEB Inte spärrad", "-", "WX", None),
    6000: EventInfo("Network Fail", "Nätverksfel", "-", "XY", None),
    6001: EventInfo("Network Restoral", "Nätverk återställd", "-", "XZ", None),
    6002: EventInfo("FlexC ATP Down", "FlexC ATP Ned", "ATP ID", "NT", None),
    6003: EventInfo("FlexC ATP Up", "FlexC ATP EDP kontakt", "ATP ID", "NR", None),
    6004: EventInfo("FlexC ATS Down", "FlexC ATS Ned", "-", "YC", None),
    6005: EventInfo("FlexC ATS Up", "FlexC ATS EDP kontakt", "-", "YK", None),
    6006: EventInfo(
        "FlexC Manual Test", "FlexC Manuellt test", "User ID", "RX", "601/1"
    ),
    6007: EventInfo(
        "FlexC Automatic Testcall Active",
        "FlexC Automatisk testsignal Aktiv",
        "ATP ID",
        "RP",
        "602/1",
    ),
    6008: EventInfo(
        "EDP Receiver Down", "EDP mottagare Ned", "EDP Receiver ID", "NT", None
    ),
    6009: EventInfo(
        "EDP Receiver Up", "EDP mottagare EDP kontakt", "EDP Receiver ID", "NR", None
    ),
    6010: EventInfo(
        "EDP Manual Test", "EDP Manuellt test", "EDP Receiver ID", "RX", "601/1"
    ),
    6011: EventInfo(
        "EDP Automatic Testcall",
        "EDP Automatisk testsignal",
        "EDP Receiver ID",
        "RP",
        "602/1",
    ),
    6012: EventInfo(
        "Modem Manual Test", "Modem Manuellt test", "User ID", "RX", "601/1"
    ),
    6013: EventInfo(
        "Modem Automatic Testcall",
        "Modem Automatisk testsignal",
        "Modem ID",
        "RP",
        "602/1",
    ),
    6015: EventInfo(
        "FlexC Automatic Testcall",
        "FlexC Automatisk testsignal",
        "ATP ID",
        "RP",
        "602/1",
    ),
    6100: EventInfo("Modem 1 Fault", "Modem 1, fel", "Modem ID", "YS", "351/1"),
    6101: EventInfo(
        "Modem 1 Fault Restore", "Modem 1, fel Återställ", "Modem ID", "YK", "351/3"
    ),
    6102: EventInfo(
        "Modem 1 Fault Inhibit", "Modem 1, fel Spärra", "Modem ID", None, None
    ),
    6103: EventInfo(
        "Modem 1 Fault Deinhibit",
        "Modem 1, fel Ta bort bortkoppling",
        "Modem ID",
        None,
        None,
    ),
    6104: EventInfo(
        "Modem 1 Fault Isolate", "Modem 1, fel Isolera", "Modem ID", None, None
    ),
    6105: EventInfo(
        "Modem 1 Fault Deisolate",
        "Modem 1, fel Ta bort isolering",
        "Modem ID",
        None,
        None,
    ),
    6106: EventInfo(
        "Modem 1 Line Fault", "Modem 1, linjefel", "Modem ID", "LT", "351/1"
    ),
    6107: EventInfo(
        "Modem 1 Line Fault Restore",
        "Modem 1, linjefel Återställ",
        "Modem ID",
        "LR",
        "351/3",
    ),
    6108: EventInfo(
        "Modem 1 Line Fault Inhibit", "Modem 1, linjefel Spärra", "Modem ID", None, None
    ),
    6109: EventInfo(
        "Modem 1 Line Fault Deinhibit",
        "Modem 1, linjefel Ta bort bortkoppling",
        "Modem ID",
        None,
        None,
    ),
    6110: EventInfo(
        "Modem 1 Line Fault Isolate",
        "Modem 1, linjefel Isolera",
        "Modem ID",
        None,
        None,
    ),
    6111: EventInfo(
        "Modem 1 Line Fault Deisolate",
        "Modem 1, linjefel Ta bort isolering",
        "Modem ID",
        None,
        None,
    ),
    6112: EventInfo("Modem 2 Fault", "Modem 2, fel", "Modem ID", "YS", "352/1"),
    6113: EventInfo(
        "Modem 2 Fault Restore", "Modem 2, fel Återställ", "Modem ID", "YK", "351/3"
    ),
    6114: EventInfo(
        "Modem 2 Line Fault", "Modem 2, linjefel", "Modem ID", "LT", "352/1"
    ),
    6115: EventInfo(
        "Modem 2 Line Fault Restore",
        "Modem 2, linjefel Återställ",
        "Modem ID",
        "LR",
        "351/3",
    ),
    6116: EventInfo(
        "Modem 2 Fault Inhibit", "Modem 2, fel Spärra", "Modem ID", None, None
    ),
    6117: EventInfo(
        "Modem 2 Fault Deinhibit",
        "Modem 2, fel Ta bort bortkoppling",
        "Modem ID",
        None,
        None,
    ),
    6118: EventInfo(
        "Modem 2 Fault Isolate", "Modem 2, fel Isolera", "Modem ID", None, None
    ),
    6119: EventInfo(
        "Modem 2 Fault Deisolate",
        "Modem 2, fel Ta bort isolering",
        "Modem ID",
        None,
        None,
    ),
    6120: EventInfo(
        "Modem 2 Line Fault Inhibit", "Modem 2, linjefel Spärra", "Modem ID", None, None
    ),
    6121: EventInfo(
        "Modem 2 Line Fault Deinhibit",
        "Modem 2, linjefel Ta bort bortkoppling",
        "Modem ID",
        None,
        None,
    ),
    6122: EventInfo(
        "Modem 2 Line Fault Isolate",
        "Modem 2, linjefel Isolera",
        "Modem ID",
        None,
        None,
    ),
    6123: EventInfo(
        "Modem 2 Line Fault Deisolate",
        "Modem 2, linjefel Ta bort isolering",
        "Modem ID",
        None,
        None,
    ),
    7000: EventInfo("System boot", "SYSTEMSTART", "-", "RR", "305/1"),
    7001: EventInfo("User Code Tamper", "Användare Kod försök", "-", "JA", "461/1"),
    7002: EventInfo("Date Changed", "Ändra datum", "-", "JT", "625/1"),
    7003: EventInfo("Engineer Enabled", "Installatör aktiverad", "-", "LB", "466/1"),
    7004: EventInfo("Engineer Disabled", "Installatör inaktiverad", "-", "LX", "466/3"),
    7005: EventInfo("Hardware fault", "HÅRDVARUFEL", "-", "HF", None),
    7006: EventInfo("Alert (Close Alert)", "Larm (Stäng Larm)", "Alert ID", "SD", None),
    7007: EventInfo("Alert (Open Alert)", "Larm (Öppen Larm)", "Alert ID", "SO", None),
    7008: EventInfo(
        "Alert (X-BUS Alert Expander)",
        "Larm (X-BUS Larm Expansionenhet)",
        "Alert ID",
        "NB",
        None,
    ),
    7009: EventInfo(
        "Alert (X-BUS Alert Expander)",
        "Larm (X-BUS Larm Expansionenhet)",
        "Alert ID",
        "NO",
        None,
    ),
    7010: EventInfo("Code Tamper System", "Kod försök System", "-", "JA", "461/1"),
    7011: EventInfo("Configuration changed", "KONFIGURATION ÄNDRAD", "-", None, None),
    7012: EventInfo("Code Tamper X-BUS", "Kod försök X-BUS", "Expander", "JA", "461/1"),
    7013: EventInfo("Mapping gate ON", "Mapping gate PÅ", "-", None, None),
    7014: EventInfo("Mapping gate OFF", "Mapping gate AV", "-", None, None),
    8000: EventInfo("Camera Offline", "Kamera offline", "Camera ID", "CV", None),
    8001: EventInfo("Camera Online", "Kamera online", "Camera ID", "CU", None),
    8002: EventInfo(
        "Service Engineer Access Request",
        "Service installatör åtkomst begärd",
        "User ID",
        "SE",
        None,
    ),
    8003: EventInfo("Hold-up Information", "Överfalls information", "-", "HD", None),
    8004: EventInfo(
        "Wireless Lost Event", "Trådlös tappad händelse", "Zone ID", "BZ", "147/1"
    ),
    8005: EventInfo(
        "Wireless Supervision Restore",
        "Återställ trådlös övervakning",
        "Zone ID",
        "WZ",
        "147/3",
    ),
    8006: EventInfo(
        "Two Way Wireless Tamper", "Tvåvägs trådlös sabotage", "Area ID", "TA", "137/1"
    ),
    8007: EventInfo(
        "Two Way Wireless Tamper Restore",
        "Tvåvägs trådlös sabotage Återställ",
        "Area ID",
        "TR",
        "137/3",
    ),
    8008: EventInfo(
        "Two Way Wireless Tamper Inhibit",
        "Tvåvägs trådlös sabotage Spärra",
        "Area ID",
        None,
        None,
    ),
    8009: EventInfo(
        "Two Way Wireless Tamper Deinhibit",
        "Tvåvägs trådlös sabotage Ta bort bortkoppling",
        "Area ID",
        None,
        None,
    ),
    8010: EventInfo(
        "Two Way Wireless Tamper Isolate",
        "Tvåvägs trådlös sabotage Isolera",
        "Area ID",
        None,
        None,
    ),
    8011: EventInfo(
        "Two Way Wireless Tamper Deisolate",
        "Tvåvägs trådlös sabotage Ta bort isolering",
        "Area ID",
        None,
        None,
    ),
    8012: EventInfo(
        "Two way wireless low battery",
        "Tvåvägs trådlös lågt batteri",
        "Area ID",
        "XT",
        None,
    ),
    8013: EventInfo(
        "Two way wireless low battery Battery Restoral",
        "Tvåvägs trådlös lågt batteri Batteriåterställning",
        "Area ID",
        "XR",
        None,
    ),
    8014: EventInfo(
        "Two Way Wireless Trouble", "Tvåvägs trådlös fel", "Area ID", "UT", "150/1"
    ),
    8015: EventInfo(
        "Two Way Wireless Trouble Restore",
        "Tvåvägs trådlös fel Återställ",
        "Area ID",
        "UJ",
        "150/3",
    ),
    8016: EventInfo(
        "Two Way Wireless Trouble Inhibit",
        "Tvåvägs trådlös fel Spärra",
        "Area ID",
        None,
        None,
    ),
    8017: EventInfo(
        "Two Way Wireless Trouble Deinhibit",
        "Tvåvägs trådlös fel Ta bort bortkoppling",
        "Area ID",
        None,
        None,
    ),
    8018: EventInfo(
        "Two Way Wireless Trouble Isolate",
        "Tvåvägs trådlös fel Isolera",
        "Area ID",
        None,
        None,
    ),
    8019: EventInfo(
        "Two Way Wireless Trouble Deisolate",
        "Tvåvägs trådlös fel Ta bort isolering",
        "Area ID",
        None,
        None,
    ),
    8020: EventInfo(
        "Two Way Wireless DC Supply",
        "Tvåvägs trådlös DC spänning",
        "Area ID",
        "AT",
        None,
    ),
    8021: EventInfo(
        "Two Way Wireless DC Supply Restore",
        "Tvåvägs trådlös DC spänning Återställ",
        "Area ID",
        "AT",
        None,
    ),
    8022: EventInfo(
        "Two Way Wireless DC Supply Inhibit",
        "Tvåvägs trådlös DC spänning Spärra",
        "Area ID",
        None,
        None,
    ),
    8023: EventInfo(
        "Two Way Wireless DC Supply Deinhibit",
        "Tvåvägs trådlös DC spänning Ta bort bortkoppling",
        "Area ID",
        None,
        None,
    ),
    8024: EventInfo(
        "Two Way Wireless DC Supply Isolate",
        "Tvåvägs trådlös DC spänning Isolera",
        "Area ID",
        None,
        None,
    ),
    8025: EventInfo(
        "Two Way Wireless DC Supply Deisolate",
        "Tvåvägs trådlös DC spänning Ta bort isolering",
        "Area ID",
        None,
        None,
    ),
    8026: EventInfo(
        "Two Way Wireless Medical Alarm",
        "Tvåvägs trådlös Medicinskt Larm",
        "Area ID",
        "MA",
        "100/1",
    ),
    8027: EventInfo(
        "Two Way Wireless Medical Restore",
        "Tvåvägs trådlös Medicinskt Återställ",
        "Area ID",
        "MR",
        "100/3",
    ),
    8028: EventInfo(
        "Two Way Wireless Fire Alarm",
        "Tvåvägs trådlös Brand Larm",
        "Area ID",
        "FA",
        "110/1",
    ),
    8029: EventInfo(
        "Two Way Wireless Fire Restore",
        "Tvåvägs trådlös Brand Återställ",
        "Area ID",
        "FR",
        "110/3",
    ),
    8030: EventInfo(
        "Two Way Wireless Panic Alarm",
        "Tvåvägs trådlös Bråklarm Larm",
        "Area ID",
        "PA",
        "120/1",
    ),
    8031: EventInfo(
        "Two Way Wireless Panic Restore",
        "Tvåvägs trådlös Bråklarm Återställ",
        "Area ID",
        "PR",
        "120/3",
    ),
    8032: EventInfo(
        "Two Way Wireless code tamper Alarm",
        "Tvåvägs trådlös kodsabotage Larm",
        "Area ID",
        "JA",
        "461/1",
    ),
    8033: EventInfo(
        "Two Way Wireless code tamper Restore",
        "Tvåvägs trådlös kodsabotage Återställ",
        "Area ID",
        "JA",
        "461/3",
    ),
    8034: EventInfo(
        "Two Way Wireless code tamper Inhibit",
        "Tvåvägs trådlös kodsabotage Spärra",
        "Area ID",
        None,
        None,
    ),
    8035: EventInfo(
        "Two Way Wireless code tamper Deinhibit",
        "Tvåvägs trådlös kodsabotage Ta bort bortkoppling",
        "Area ID",
        None,
        None,
    ),
    8036: EventInfo(
        "Two Way Wireless code tamper Isolate",
        "Tvåvägs trådlös kodsabotage Isolera",
        "Area ID",
        None,
        None,
    ),
    8037: EventInfo(
        "Two Way Wireless code tamper Deisolate",
        "Tvåvägs trådlös kodsabotage Ta bort isolering",
        "Area ID",
        None,
        None,
    ),
    8038: EventInfo("Keypad locked", "Manöverpanel LÅST", "Area ID", "ZE", None),
    8039: EventInfo(
        "Keypad Not Locked Out", "Manöverpanel Inte spärrad", "Area ID", "KG", None
    ),
}


def event_description(event_id: int | None, language: str | None = None) -> str | None:
    """Return the panel's name for an event, in Swedish or else English."""
    if event_id is None:
        return None
    info = EVENT_TABLE.get(event_id)
    if info is None:
        return None
    if isinstance(language, str) and language.lower().startswith("sv"):
        return info.sv
    return info.en
