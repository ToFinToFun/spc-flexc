# FlexC event table

Every event the SPC panel can send over FlexC, as listed by the panel itself
(web page: **Communications → FlexC → Event Profiles →** view a profile **→ Show
Complete Event Table**) on an SPC4300 with firmware 3.14.1. The integration uses
these names (`custom_components/spc_flexc/flexc/event_table.py`): Swedish when
Home Assistant runs in Swedish, otherwise English. Events 3502, 3503, 3506 and
3507 show the site's own Partset names on a panel; the default names are given
here.

608 events.

| ID | English | Swedish | Address type | SIA | CID |
|---|---|---|---|---|---|
| 1000 | Burglary Alarm [Alarm Zone] | Inbrottslarm [Larm SEKTION] | Zone ID | BA | 130/1 |
| 1001 | Burglary Alarm [Entry/Exit Zone] | Inbrottslarm [In/utpassering SEKTION] | Zone ID | BA | 134/1 |
| 1002 | Burglary Alarm [Exit Term Zone] | Inbrottslarm [Utpasseringstid SEKTION] | Zone ID | BA | – |
| 1003 | Zone alarm [Fire alarm Zone] | Sektionslarm [Brandlarm SEKTION] | Zone ID | FA | 110/1 |
| 1004 | Burglary Alarm [Fire Exit Zone] | Inbrottslarm [Nödutgång SEKTION] | Zone ID | BA | 130/1 |
| 1005 | Zone alarm [Line Zone] | Sektionslarm [Linje SEKTION] | Zone ID | LT | 351/1 |
| 1006 | Zone alarm [Panic Zone] | Sektionslarm [Bråklarm SEKTION] | Zone ID | PA | 120/1 |
| 1007 | Zone alarm [Holdup Zone] | Sektionslarm [Överfall SEKTION] | Zone ID | HA | 120/1 |
| 1008 | Zone alarm [Tamper Zone] | Sektionslarm [SABOTAGE SEKTION] | Zone ID | TA | 137/1 |
| 1009 | Zone alarm [Tech Zone] | Sektionslarm [Tekniskt larm SEKTION] | Zone ID | UA | 150/1 |
| 1010 | Zone alarm [Medical Zone] | Sektionslarm [Medicinskt SEKTION] | Zone ID | MA | 100/1 |
| 1011 | Zone alarm [Keyarm Zone] | Sektionslarm [Nyckeltillkoppling SEKTION] | Zone ID | BA | – |
| 1012 | Zone alarm [Unused Zone] | Sektionslarm [Används ej SEKTION] | Zone ID | – | – |
| 1013 | Zone alarm [Shunt Zone] | Sektionslarm [Förbikopplare SEKTION] | Zone ID | BA | – |
| 1014 | Zone alarm [X-Shunt Zone] | Sektionslarm [X-förbikopplare SEKTION] | Zone ID | BA | – |
| 1015 | Zone alarm [Detector Fault Zone] | Sektionslarm [Detektorfel SEKTION] | Zone ID | BT | 380/1 |
| 1016 | Zone alarm [Lock Supervision Zone] | Sektionslarm [Låskontroll SEKTION] | Zone ID | BA | 130/1 |
| 1017 | Burglary Alarm [Seismic Zone] | Inbrottslarm [Seismisk SEKTION] | Zone ID | BA | 130/1 |
| 1019 | Zone alarm [Holdup Fault Zone] | Sektionslarm [Överfall fel SEKTION] | Zone ID | HT | 376/1 |
| 1020 | Zone alarm [Warning Fault Zone] | Sektionslarm [Varning fel SEKTION] | Zone ID | YA | 380/1 |
| 1021 | Zone alarm [Setting authorisation Zone] | Sektionslarm [Tillkopplingstillstånd SEKTION] | Zone ID | – | – |
| 1022 | Burglary Alarm [Lock element Zone] | Inbrottslarm [Lås element SEKTION] | Zone ID | – | – |
| 1023 | Burglary Alarm [Glass Break Zone] | Inbrottslarm [Glaskross SEKTION] | Zone ID | BA | 130/1 |
| 1024 | Zone alarm [Water Zone] | Sektionslarm [Vatten SEKTION] | Zone ID | WA | 154/1 |
| 1025 | Zone alarm [Heat Zone] | Sektionslarm [Värme SEKTION] | Zone ID | KA | 158/1 |
| 1026 | Zone alarm [Fridge/Freezer Zone] | Sektionslarm [Kyl/frys SEKTION] | Zone ID | ZA | 152/1 |
| 1027 | Zone alarm [Gas Zone] | Sektionslarm [Gas SEKTION] | Zone ID | GA | 151/1 |
| 1028 | Zone alarm [Sprinkler Zone] | Sektionslarm [Sprinkler SEKTION] | Zone ID | SA | 213/1 |
| 1029 | Zone alarm [CO Zone] | Sektionslarm [CO SEKTION] | Zone ID | CY | 162/1 |
| 1100 | Burglary Restoral [Alarm Zone] | Inbrott återställning [Larm SEKTION] | Zone ID | BR | 130/3 |
| 1101 | Burglary Restoral [Entry/Exit Zone] | Inbrott återställning [In/utpassering SEKTION] | Zone ID | BR | 130/3 |
| 1102 | Burglary Restoral [Exit Term Zone] | Inbrott återställning [Utpasseringstid SEKTION] | Zone ID | BR | – |
| 1103 | Zone restore [Fire Restoral Zone] | Sektion återst. [Brandlarm återställning SEKTION] | Zone ID | FR | 110/3 |
| 1104 | Burglary Restoral [Fire Exit Zone] | Inbrott återställning [Nödutgång SEKTION] | Zone ID | BR | 130/3 |
| 1105 | Zone restore [Line Zone] | Sektion återst. [Linje SEKTION] | Zone ID | LR | 351/3 |
| 1106 | Zone restore [Panic Zone] | Sektion återst. [Bråklarm SEKTION] | Zone ID | PR | 120/3 |
| 1107 | Zone restore [Holdup Zone] | Sektion återst. [Överfall SEKTION] | Zone ID | HR | 120/3 |
| 1108 | Zone restore [Tamper Zone] | Sektion återst. [SABOTAGE SEKTION] | Zone ID | TR | 137/3 |
| 1109 | Zone restore [Tech Zone] | Sektion återst. [Tekniskt larm SEKTION] | Zone ID | UR | 150/3 |
| 1110 | Zone restore [Medical Zone] | Sektion återst. [Medicinskt SEKTION] | Zone ID | MR | 100/3 |
| 1111 | Zone restore [Keyarm Zone] | Sektion återst. [Nyckeltillkoppling SEKTION] | Zone ID | BR | – |
| 1112 | Zone restore [Unused Zone] | Sektion återst. [Används ej SEKTION] | Zone ID | – | – |
| 1113 | Zone restore [Shunt Zone] | Sektion återst. [Förbikopplare SEKTION] | Zone ID | BR | – |
| 1114 | Zone restore [X-Shunt Zone] | Sektion återst. [X-förbikopplare SEKTION] | Zone ID | BR | – |
| 1115 | Zone restore [Detector Fault Zone] | Sektion återst. [Detektorfel SEKTION] | Zone ID | BJ | 380/3 |
| 1116 | Zone restore [Lock Supervision Zone] | Sektion återst. [Låskontroll SEKTION] | Zone ID | – | – |
| 1117 | Burglary Restoral [Seismic Zone] | Inbrott återställning [Seismisk SEKTION] | Zone ID | BR | 130/3 |
| 1119 | Zone restore [Holdup Fault Zone] | Sektion återst. [Överfall fel SEKTION] | Zone ID | HJ | 376/3 |
| 1120 | Zone restore [Warning Fault Zone] | Sektion återst. [Varning fel SEKTION] | Zone ID | YH | 380/3 |
| 1121 | Zone restore [Setting authorisation Zone] | Sektion återst. [Tillkopplingstillstånd SEKTION] | Zone ID | – | – |
| 1122 | Burglary Restoral [Lock element Zone] | Inbrott återställning [Lås element SEKTION] | Zone ID | BR | 130/3 |
| 1123 | Burglary Restoral [Glass Break Zone] | Inbrott återställning [Glaskross SEKTION] | Zone ID | BR | 130/3 |
| 1124 | Zone restore [Water Zone] | Sektion återst. [Vatten SEKTION] | Zone ID | WH | 154/3 |
| 1125 | Zone restore [Heat Zone] | Sektion återst. [Värme SEKTION] | Zone ID | KH | 158/3 |
| 1126 | Zone restore [Fridge/Freezer Zone] | Sektion återst. [Kyl/frys SEKTION] | Zone ID | ZH | 152/3 |
| 1127 | Zone restore [Gas Zone] | Sektion återst. [Gas SEKTION] | Zone ID | GH | 151/3 |
| 1128 | Zone restore [Sprinkler Zone] | Sektion återst. [Sprinkler SEKTION] | Zone ID | SH | 213/3 |
| 1129 | Zone restore [CO Zone] | Sektion återst. [CO SEKTION] | Zone ID | CH | 162/3 |
| 1200 | Zone tamper [Alarm Zone] | Sektionsabotage [Larm SEKTION] | Zone ID | BT | 144/1 |
| 1201 | Zone tamper [Entry/Exit Zone] | Sektionsabotage [In/utpassering SEKTION] | Zone ID | BT | 144/1 |
| 1202 | Zone tamper [Exit Term Zone] | Sektionsabotage [Utpasseringstid SEKTION] | Zone ID | BT | 144/1 |
| 1203 | Zone tamper [Fire Zone] | Sektionsabotage [Brand SEKTION] | Zone ID | FT | 144/1 |
| 1204 | Zone tamper [Fire Exit Zone] | Sektionsabotage [Nödutgång SEKTION] | Zone ID | BT | 144/1 |
| 1205 | Zone tamper [Line Zone] | Sektionsabotage [Linje SEKTION] | Zone ID | BT | 144/1 |
| 1206 | Zone tamper [Panic Zone] | Sektionsabotage [Bråklarm SEKTION] | Zone ID | PT | 144/1 |
| 1207 | Zone tamper [Holdup Zone] | Sektionsabotage [Överfall SEKTION] | Zone ID | HT | 144/1 |
| 1208 | Zone tamper [Tamper Zone] | Sektionsabotage [SABOTAGE SEKTION] | Zone ID | TA | 144/1 |
| 1209 | Zone tamper [Tech Zone] | Sektionsabotage [Tekniskt larm SEKTION] | Zone ID | UT | 144/1 |
| 1210 | Zone tamper [Medical Zone] | Sektionsabotage [Medicinskt SEKTION] | Zone ID | MT | 144/1 |
| 1211 | Zone tamper [Keyarm Zone] | Sektionsabotage [Nyckeltillkoppling SEKTION] | Zone ID | BT | 144/1 |
| 1212 | Zone tamper [Unused Zone] | Sektionsabotage [Används ej SEKTION] | Zone ID | – | 144/1 |
| 1213 | Zone tamper [Shunt Zone] | Sektionsabotage [Förbikopplare SEKTION] | Zone ID | BT | 144/1 |
| 1214 | Zone tamper [X-Shunt Zone] | Sektionsabotage [X-förbikopplare SEKTION] | Zone ID | BT | 144/1 |
| 1215 | Zone tamper [Detector Fault Zone] | Sektionsabotage [Detektorfel SEKTION] | Zone ID | BT | 144/1 |
| 1216 | Zone tamper [Lock Supervision Zone] | Sektionsabotage [Låskontroll SEKTION] | Zone ID | UT | 144/1 |
| 1217 | Zone tamper [Seismic Zone] | Sektionsabotage [Seismisk SEKTION] | Zone ID | BT | 144/1 |
| 1218 | Zone tamper [All Okay Zone] | Sektionsabotage [Allt OK SEKTION] | Zone ID | – | 144/1 |
| 1219 | Zone tamper [Holdup Fault Zone] | Sektionsabotage [Överfall fel SEKTION] | Zone ID | HT | 144/1 |
| 1220 | Zone tamper [Warning Fault Zone] | Sektionsabotage [Varning fel SEKTION] | Zone ID | YA | 144/1 |
| 1221 | Zone tamper [Setting authorisation Zone] | Sektionsabotage [Tillkopplingstillstånd SEKTION] | Zone ID | UT | 144/1 |
| 1222 | Zone tamper [Lock element Zone] | Sektionsabotage [Lås element SEKTION] | Zone ID | UT | 144/1 |
| 1223 | Zone tamper [Glass Break Zone] | Sektionsabotage [Glaskross SEKTION] | Zone ID | BT | 144/1 |
| 1300 | Zone tamper Restore [Alarm Zone] | Sektionsabotage återställd [Larm SEKTION] | Zone ID | BJ | 144/3 |
| 1301 | Zone tamper Restore [Entry/Exit Zone] | Sektionsabotage återställd [In/utpassering SEKTION] | Zone ID | BJ | 144/3 |
| 1302 | Zone tamper Restore [Exit Term Zone] | Sektionsabotage återställd [Utpasseringstid SEKTION] | Zone ID | BJ | 144/3 |
| 1303 | Zone tamper Restore [Fire Zone] | Sektionsabotage återställd [Brand SEKTION] | Zone ID | FJ | 144/3 |
| 1304 | Zone tamper Restore [Fire Exit Zone] | Sektionsabotage återställd [Nödutgång SEKTION] | Zone ID | BJ | 144/3 |
| 1305 | Zone tamper Restore [Line Zone] | Sektionsabotage återställd [Linje SEKTION] | Zone ID | BJ | 144/3 |
| 1306 | Zone tamper Restore [Panic Zone] | Sektionsabotage återställd [Bråklarm SEKTION] | Zone ID | PJ | 144/3 |
| 1307 | Zone tamper Restore [Holdup Zone] | Sektionsabotage återställd [Överfall SEKTION] | Zone ID | HJ | 144/3 |
| 1308 | Zone tamper Restore [Tamper Zone] | Sektionsabotage återställd [SABOTAGE SEKTION] | Zone ID | TR | 144/3 |
| 1309 | Zone tamper Restore [Tech Zone] | Sektionsabotage återställd [Tekniskt larm SEKTION] | Zone ID | UJ | 144/3 |
| 1310 | Zone tamper Restore [Medical Zone] | Sektionsabotage återställd [Medicinskt SEKTION] | Zone ID | MJ | 144/3 |
| 1311 | Zone tamper Restore [Keyarm Zone] | Sektionsabotage återställd [Nyckeltillkoppling SEKTION] | Zone ID | BJ | 144/3 |
| 1312 | Zone tamper Restore [Unused Zone] | Sektionsabotage återställd [Används ej SEKTION] | Zone ID | – | 144/3 |
| 1313 | Zone tamper Restore [Shunt Zone] | Sektionsabotage återställd [Förbikopplare SEKTION] | Zone ID | BJ | 144/3 |
| 1314 | Zone tamper Restore [X-Shunt Zone] | Sektionsabotage återställd [X-förbikopplare SEKTION] | Zone ID | BJ | 144/3 |
| 1315 | Zone tamper Restore [Detector Fault Zone] | Sektionsabotage återställd [Detektorfel SEKTION] | Zone ID | BJ | 144/3 |
| 1316 | Zone tamper Restore [Lock Supervision Zone] | Sektionsabotage återställd [Låskontroll SEKTION] | Zone ID | UJ | 144/3 |
| 1317 | Zone tamper Restore [Seismic Zone] | Sektionsabotage återställd [Seismisk SEKTION] | Zone ID | BJ | 144/3 |
| 1318 | Zone tamper Restore [All Okay Zone] | Sektionsabotage återställd [Allt OK SEKTION] | Zone ID | TR | 144/3 |
| 1319 | Zone tamper Restore [Holdup Fault Zone] | Sektionsabotage återställd [Överfall fel SEKTION] | Zone ID | HJ | 144/3 |
| 1320 | Zone tamper Restore [Warning Fault Zone] | Sektionsabotage återställd [Varning fel SEKTION] | Zone ID | YH | 144/3 |
| 1321 | Zone tamper Restore [Setting authorisation Zone] | Sektionsabotage återställd [Tillkopplingstillstånd SEKTION] | Zone ID | UJ | 144/3 |
| 1322 | Zone tamper Restore [Lock element Zone] | Sektionsabotage återställd [Lås element SEKTION] | Zone ID | UJ | 144/3 |
| 1323 | Zone tamper Restore [Glass Break Zone] | Sektionsabotage återställd [Glaskross SEKTION] | Zone ID | BJ | 144/3 |
| 1400 | Zone inhibit [Alarm Zone] | Sektion spärrad [Larm SEKTION] | Zone ID | BB | 570/1 |
| 1401 | Zone inhibit [Entry/Exit Zone] | Sektion spärrad [In/utpassering SEKTION] | Zone ID | BB | 570/1 |
| 1402 | Zone inhibit [Exit Term Zone] | Sektion spärrad [Utpasseringstid SEKTION] | Zone ID | BB | 570/1 |
| 1403 | Zone inhibit [Fire Zone] | Sektion spärrad [Brand SEKTION] | Zone ID | FB | 570/1 |
| 1404 | Zone inhibit [Fire Exit Zone] | Sektion spärrad [Nödutgång SEKTION] | Zone ID | BB | 570/1 |
| 1405 | Zone inhibit [Line Zone] | Sektion spärrad [Linje SEKTION] | Zone ID | UB | 570/1 |
| 1406 | Zone inhibit [Panic Zone] | Sektion spärrad [Bråklarm SEKTION] | Zone ID | PB | 570/1 |
| 1407 | Zone inhibit [Holdup Zone] | Sektion spärrad [Överfall SEKTION] | Zone ID | HB | 570/1 |
| 1408 | Zone inhibit [Tamper Zone] | Sektion spärrad [SABOTAGE SEKTION] | Zone ID | TB | 570/1 |
| 1409 | Zone inhibit [Tech Zone] | Sektion spärrad [Tekniskt larm SEKTION] | Zone ID | UB | 570/1 |
| 1410 | Zone inhibit [Medical Zone] | Sektion spärrad [Medicinskt SEKTION] | Zone ID | MB | 570/1 |
| 1411 | Zone inhibit [Keyarm Zone] | Sektion spärrad [Nyckeltillkoppling SEKTION] | Zone ID | BB | 570/1 |
| 1412 | Zone inhibit [Unused Zone] | Sektion spärrad [Används ej SEKTION] | Zone ID | – | 570/1 |
| 1413 | Zone inhibit [Shunt Zone] | Sektion spärrad [Förbikopplare SEKTION] | Zone ID | BB | 570/1 |
| 1414 | Zone inhibit [X-Shunt Zone] | Sektion spärrad [X-förbikopplare SEKTION] | Zone ID | BB | 570/1 |
| 1415 | Zone inhibit [Detector Fault Zone] | Sektion spärrad [Detektorfel SEKTION] | Zone ID | BB | 570/1 |
| 1416 | Zone inhibit [Lock Supervision Zone] | Sektion spärrad [Låskontroll SEKTION] | Zone ID | UB | 570/1 |
| 1417 | Zone inhibit [Seismic Zone] | Sektion spärrad [Seismisk SEKTION] | Zone ID | BB | 570/1 |
| 1418 | Zone inhibit [All Okay Zone] | Sektion spärrad [Allt OK SEKTION] | Zone ID | UB | 570/1 |
| 1419 | Zone inhibit [Holdup Fault Zone] | Sektion spärrad [Överfall fel SEKTION] | Zone ID | BB | 570/1 |
| 1420 | Zone inhibit [Warning Fault Zone] | Sektion spärrad [Varning fel SEKTION] | Zone ID | BB | 570/1 |
| 1421 | Zone inhibit [Setting authorisation Zone] | Sektion spärrad [Tillkopplingstillstånd SEKTION] | Zone ID | UB | 570/1 |
| 1422 | Zone inhibit [Lock element Zone] | Sektion spärrad [Lås element SEKTION] | Zone ID | UB | 570/1 |
| 1423 | Zone inhibit [Glass Break Zone] | Sektion spärrad [Glaskross SEKTION] | Zone ID | BB | 570/1 |
| 1500 | Zone deinhibit [Alarm Zone] | Sektion ej spärrad [Larm SEKTION] | Zone ID | BU | 570/3 |
| 1501 | Zone deinhibit [Entry/Exit Zone] | Sektion ej spärrad [In/utpassering SEKTION] | Zone ID | BU | 570/3 |
| 1502 | Zone deinhibit [Exit Term Zone] | Sektion ej spärrad [Utpasseringstid SEKTION] | Zone ID | BU | 570/3 |
| 1503 | Zone deinhibit [Fire Zone] | Sektion ej spärrad [Brand SEKTION] | Zone ID | FU | 570/3 |
| 1504 | Zone deinhibit [Fire Exit Zone] | Sektion ej spärrad [Nödutgång SEKTION] | Zone ID | BU | 570/3 |
| 1505 | Zone deinhibit [Line Zone] | Sektion ej spärrad [Linje SEKTION] | Zone ID | UU | 570/3 |
| 1506 | Zone deinhibit [Panic Zone] | Sektion ej spärrad [Bråklarm SEKTION] | Zone ID | PU | 570/3 |
| 1507 | Zone deinhibit [Holdup Zone] | Sektion ej spärrad [Överfall SEKTION] | Zone ID | HU | 570/3 |
| 1508 | Zone deinhibit [Tamper Zone] | Sektion ej spärrad [SABOTAGE SEKTION] | Zone ID | TU | 570/3 |
| 1509 | Zone deinhibit [Tech Zone] | Sektion ej spärrad [Tekniskt larm SEKTION] | Zone ID | UU | 570/3 |
| 1510 | Zone deinhibit [Medical Zone] | Sektion ej spärrad [Medicinskt SEKTION] | Zone ID | MU | 570/3 |
| 1511 | Zone deinhibit [Keyarm Zone] | Sektion ej spärrad [Nyckeltillkoppling SEKTION] | Zone ID | BU | 570/3 |
| 1512 | Zone deinhibit [Unused Zone] | Sektion ej spärrad [Används ej SEKTION] | Zone ID | – | 570/3 |
| 1513 | Zone deinhibit [Shunt Zone] | Sektion ej spärrad [Förbikopplare SEKTION] | Zone ID | BU | 570/3 |
| 1514 | Zone deinhibit [X-Shunt Zone] | Sektion ej spärrad [X-förbikopplare SEKTION] | Zone ID | BU | 570/3 |
| 1515 | Zone deinhibit [Detector Fault Zone] | Sektion ej spärrad [Detektorfel SEKTION] | Zone ID | BU | 570/3 |
| 1516 | Zone deinhibit [Lock Supervision Zone] | Sektion ej spärrad [Låskontroll SEKTION] | Zone ID | UU | 570/3 |
| 1517 | Zone deinhibit [Seismic Zone] | Sektion ej spärrad [Seismisk SEKTION] | Zone ID | BU | 570/3 |
| 1518 | Zone deinhibit [All Okay Zone] | Sektion ej spärrad [Allt OK SEKTION] | Zone ID | UU | 570/3 |
| 1519 | Zone deinhibit [Holdup Fault Zone] | Sektion ej spärrad [Överfall fel SEKTION] | Zone ID | BU | 570/3 |
| 1520 | Zone deinhibit [Warning Fault Zone] | Sektion ej spärrad [Varning fel SEKTION] | Zone ID | BU | 570/3 |
| 1521 | Zone deinhibit [Setting authorisation Zone] | Sektion ej spärrad [Tillkopplingstillstånd SEKTION] | Zone ID | UU | 570/3 |
| 1522 | Zone deinhibit [Lock element Zone] | Sektion ej spärrad [Lås element SEKTION] | Zone ID | UU | 570/3 |
| 1523 | Zone deinhibit [Glass Break Zone] | Sektion ej spärrad [Glaskross SEKTION] | Zone ID | BU | 570/3 |
| 1600 | Zone isolate [Alarm Zone] | Sektion isolerad [Larm SEKTION] | Zone ID | BB | 570/1 |
| 1601 | Zone isolate [Entry/Exit Zone] | Sektion isolerad [In/utpassering SEKTION] | Zone ID | BB | 570/1 |
| 1602 | Zone isolate [Exit Term Zone] | Sektion isolerad [Utpasseringstid SEKTION] | Zone ID | BB | 570/1 |
| 1603 | Zone isolate [Fire Zone] | Sektion isolerad [Brand SEKTION] | Zone ID | FB | 570/1 |
| 1604 | Zone isolate [Fire Exit Zone] | Sektion isolerad [Nödutgång SEKTION] | Zone ID | BB | 570/1 |
| 1605 | Zone isolate [Line Zone] | Sektion isolerad [Linje SEKTION] | Zone ID | UB | 570/1 |
| 1606 | Zone isolate [Panic Zone] | Sektion isolerad [Bråklarm SEKTION] | Zone ID | PB | 570/1 |
| 1607 | Zone isolate [Holdup Zone] | Sektion isolerad [Överfall SEKTION] | Zone ID | HB | 570/1 |
| 1608 | Zone isolate [Tamper Zone] | Sektion isolerad [SABOTAGE SEKTION] | Zone ID | TB | 570/1 |
| 1609 | Zone isolate [Tech Zone] | Sektion isolerad [Tekniskt larm SEKTION] | Zone ID | UB | 570/1 |
| 1610 | Zone isolate [Medical Zone] | Sektion isolerad [Medicinskt SEKTION] | Zone ID | MB | 570/1 |
| 1611 | Zone isolate [Keyarm Zone] | Sektion isolerad [Nyckeltillkoppling SEKTION] | Zone ID | BB | 570/1 |
| 1612 | Zone isolate [Unused Zone] | Sektion isolerad [Används ej SEKTION] | Zone ID | – | 570/1 |
| 1613 | Zone isolate [Shunt Zone] | Sektion isolerad [Förbikopplare SEKTION] | Zone ID | BB | 570/1 |
| 1614 | Zone isolate [X-Shunt Zone] | Sektion isolerad [X-förbikopplare SEKTION] | Zone ID | BB | 570/1 |
| 1615 | Zone isolate [Detector Fault Zone] | Sektion isolerad [Detektorfel SEKTION] | Zone ID | BB | 570/1 |
| 1616 | Zone isolate [Lock Supervision Zone] | Sektion isolerad [Låskontroll SEKTION] | Zone ID | UB | 570/1 |
| 1617 | Zone isolate [Seismic Zone] | Sektion isolerad [Seismisk SEKTION] | Zone ID | BB | 570/1 |
| 1618 | Zone isolate [All Okay Zone] | Sektion isolerad [Allt OK SEKTION] | Zone ID | UB | 570/1 |
| 1619 | Zone isolate [Holdup Fault Zone] | Sektion isolerad [Överfall fel SEKTION] | Zone ID | BB | 570/1 |
| 1620 | Zone isolate [Warning Fault Zone] | Sektion isolerad [Varning fel SEKTION] | Zone ID | BB | 570/1 |
| 1621 | Zone isolate [Setting authorisation Zone] | Sektion isolerad [Tillkopplingstillstånd SEKTION] | Zone ID | UB | 570/1 |
| 1622 | Zone isolate [Lock element Zone] | Sektion isolerad [Lås element SEKTION] | Zone ID | UB | 570/1 |
| 1623 | Zone isolate [Glass Break Zone] | Sektion isolerad [Glaskross SEKTION] | Zone ID | BB | 570/1 |
| 1700 | Zone deisolate [Alarm Zone] | Sektion ej isolerad [Larm SEKTION] | Zone ID | BU | 570/3 |
| 1701 | Zone deisolate [Entry/Exit Zone] | Sektion ej isolerad [In/utpassering SEKTION] | Zone ID | BU | 570/3 |
| 1702 | Zone deisolate [Exit Term Zone] | Sektion ej isolerad [Utpasseringstid SEKTION] | Zone ID | BU | 570/3 |
| 1703 | Zone deisolate [Fire Zone] | Sektion ej isolerad [Brand SEKTION] | Zone ID | FU | 570/3 |
| 1704 | Zone deisolate [Fire Exit Zone] | Sektion ej isolerad [Nödutgång SEKTION] | Zone ID | BU | 570/3 |
| 1705 | Zone deisolate [Line Zone] | Sektion ej isolerad [Linje SEKTION] | Zone ID | UU | 570/3 |
| 1706 | Zone deisolate [Panic Zone] | Sektion ej isolerad [Bråklarm SEKTION] | Zone ID | PU | 570/3 |
| 1707 | Zone deisolate [Holdup Zone] | Sektion ej isolerad [Överfall SEKTION] | Zone ID | HU | 570/3 |
| 1708 | Zone deisolate [Tamper Zone] | Sektion ej isolerad [SABOTAGE SEKTION] | Zone ID | TU | 570/3 |
| 1709 | Zone deisolate [Tech Zone] | Sektion ej isolerad [Tekniskt larm SEKTION] | Zone ID | UU | 570/3 |
| 1710 | Zone deisolate [Medical Zone] | Sektion ej isolerad [Medicinskt SEKTION] | Zone ID | MU | 570/3 |
| 1711 | Zone deisolate [Keyarm Zone] | Sektion ej isolerad [Nyckeltillkoppling SEKTION] | Zone ID | BU | 570/3 |
| 1712 | Zone deisolate [Unused Zone] | Sektion ej isolerad [Används ej SEKTION] | Zone ID | – | 570/3 |
| 1713 | Zone deisolate [Shunt Zone] | Sektion ej isolerad [Förbikopplare SEKTION] | Zone ID | BU | 570/3 |
| 1714 | Zone deisolate [X-Shunt Zone] | Sektion ej isolerad [X-förbikopplare SEKTION] | Zone ID | BU | 570/3 |
| 1715 | Zone deisolate [Detector Fault Zone] | Sektion ej isolerad [Detektorfel SEKTION] | Zone ID | BU | 570/3 |
| 1716 | Zone deisolate [Lock Supervision Zone] | Sektion ej isolerad [Låskontroll SEKTION] | Zone ID | UU | 570/3 |
| 1717 | Zone deisolate [Seismic Zone] | Sektion ej isolerad [Seismisk SEKTION] | Zone ID | BU | 570/3 |
| 1718 | Zone deisolate [All Okay Zone] | Sektion ej isolerad [Allt OK SEKTION] | Zone ID | UU | 570/3 |
| 1719 | Zone deisolate [Holdup Fault Zone] | Sektion ej isolerad [Överfall fel SEKTION] | Zone ID | BU | 570/3 |
| 1720 | Zone deisolate [Warning Fault Zone] | Sektion ej isolerad [Varning fel SEKTION] | Zone ID | BU | 570/3 |
| 1721 | Zone deisolate [Setting authorisation Zone] | Sektion ej isolerad [Tillkopplingstillstånd SEKTION] | Zone ID | UU | 570/3 |
| 1722 | Zone deisolate [Lock element Zone] | Sektion ej isolerad [Lås element SEKTION] | Zone ID | UU | 570/3 |
| 1723 | Zone deisolate [Glass Break Zone] | Sektion ej isolerad [Glaskross SEKTION] | Zone ID | BU | 570/3 |
| 1800 | Trouble [Alarm Zone] | Antimask [Larm SEKTION] | Zone ID | UT | 150/1 |
| 1801 | Trouble [Entry/Exit Zone] | Antimask [In/utpassering SEKTION] | Zone ID | UT | 150/1 |
| 1802 | Trouble [Exit Term Zone] | Antimask [Utpasseringstid SEKTION] | Zone ID | UT | 150/1 |
| 1803 | Trouble [Fire Zone] | Antimask [Brand SEKTION] | Zone ID | UT | 150/1 |
| 1804 | Trouble [Fire Exit Zone] | Antimask [Nödutgång SEKTION] | Zone ID | UT | 150/1 |
| 1805 | Trouble [Line Zone] | Antimask [Linje SEKTION] | Zone ID | UT | 150/1 |
| 1806 | Trouble [Panic Zone] | Antimask [Bråklarm SEKTION] | Zone ID | UT | 150/1 |
| 1807 | Trouble [Holdup Zone] | Antimask [Överfall SEKTION] | Zone ID | UT | 150/1 |
| 1808 | Trouble [Tamper Zone] | Antimask [SABOTAGE SEKTION] | Zone ID | UT | 150/1 |
| 1809 | Trouble [Tech Zone] | Antimask [Tekniskt larm SEKTION] | Zone ID | UT | 150/1 |
| 1810 | Trouble [Medical Zone] | Antimask [Medicinskt SEKTION] | Zone ID | UT | 150/1 |
| 1811 | Trouble [Keyarm Zone] | Antimask [Nyckeltillkoppling SEKTION] | Zone ID | UT | 150/1 |
| 1812 | Trouble [Unused Zone] | Antimask [Används ej SEKTION] | Zone ID | – | 150/1 |
| 1813 | Trouble [Shunt Zone] | Antimask [Förbikopplare SEKTION] | Zone ID | UT | 150/1 |
| 1814 | Trouble [X-Shunt Zone] | Antimask [X-förbikopplare SEKTION] | Zone ID | UT | 150/1 |
| 1815 | Trouble [Detector Fault Zone] | Antimask [Detektorfel SEKTION] | Zone ID | UT | 150/1 |
| 1816 | Trouble [Lock Supervision Zone] | Antimask [Låskontroll SEKTION] | Zone ID | UT | 150/1 |
| 1817 | Trouble [Seismic Zone] | Antimask [Seismisk SEKTION] | Zone ID | UT | 150/1 |
| 1818 | Trouble [All Okay Zone] | Antimask [Allt OK SEKTION] | Zone ID | UT | 150/1 |
| 1819 | Trouble [Holdup Fault Zone] | Antimask [Överfall fel SEKTION] | Zone ID | UT | 150/1 |
| 1820 | Trouble [Warning Fault Zone] | Antimask [Varning fel SEKTION] | Zone ID | UT | 150/1 |
| 1821 | Trouble [Setting authorisation Zone] | Antimask [Tillkopplingstillstånd SEKTION] | Zone ID | UT | 150/1 |
| 1822 | Trouble [Lock element Zone] | Antimask [Lås element SEKTION] | Zone ID | UT | 150/1 |
| 1823 | Trouble [Glass Break Zone] | Antimask [Glaskross SEKTION] | Zone ID | UT | 150/1 |
| 1900 | Trouble restore [Alarm Zone] | Antimask återställd [Larm SEKTION] | Zone ID | UJ | 150/3 |
| 1901 | Trouble restore [Entry/Exit Zone] | Antimask återställd [In/utpassering SEKTION] | Zone ID | UJ | 150/3 |
| 1902 | Trouble restore [Exit Term Zone] | Antimask återställd [Utpasseringstid SEKTION] | Zone ID | UJ | 150/3 |
| 1903 | Trouble restore [Fire Zone] | Antimask återställd [Brand SEKTION] | Zone ID | UJ | 150/3 |
| 1904 | Trouble restore [Fire Exit Zone] | Antimask återställd [Nödutgång SEKTION] | Zone ID | UJ | 150/3 |
| 1905 | Trouble restore [Line Zone] | Antimask återställd [Linje SEKTION] | Zone ID | UJ | 150/3 |
| 1906 | Trouble restore [Panic Zone] | Antimask återställd [Bråklarm SEKTION] | Zone ID | UJ | 150/3 |
| 1907 | Trouble restore [Holdup Zone] | Antimask återställd [Överfall SEKTION] | Zone ID | UJ | 150/3 |
| 1908 | Trouble restore [Tamper Zone] | Antimask återställd [SABOTAGE SEKTION] | Zone ID | UJ | 150/3 |
| 1909 | Trouble restore [Tech Zone] | Antimask återställd [Tekniskt larm SEKTION] | Zone ID | UJ | 150/3 |
| 1910 | Trouble restore [Medical Zone] | Antimask återställd [Medicinskt SEKTION] | Zone ID | UJ | 150/3 |
| 1911 | Trouble restore [Keyarm Zone] | Antimask återställd [Nyckeltillkoppling SEKTION] | Zone ID | UJ | 150/3 |
| 1912 | Trouble restore [Unused Zone] | Antimask återställd [Används ej SEKTION] | Zone ID | UJ | 150/3 |
| 1913 | Trouble restore [Shunt Zone] | Antimask återställd [Förbikopplare SEKTION] | Zone ID | UJ | 150/3 |
| 1914 | Trouble restore [X-Shunt Zone] | Antimask återställd [X-förbikopplare SEKTION] | Zone ID | UJ | 150/3 |
| 1915 | Trouble restore [Detector Fault Zone] | Antimask återställd [Detektorfel SEKTION] | Zone ID | UJ | 150/3 |
| 1916 | Trouble restore [Lock Supervision Zone] | Antimask återställd [Låskontroll SEKTION] | Zone ID | UJ | 150/3 |
| 1917 | Trouble restore [Seismic Zone] | Antimask återställd [Seismisk SEKTION] | Zone ID | UJ | 150/3 |
| 1918 | Trouble restore [All Okay Zone] | Antimask återställd [Allt OK SEKTION] | Zone ID | UJ | 150/3 |
| 1919 | Trouble restore [Holdup Fault Zone] | Antimask återställd [Överfall fel SEKTION] | Zone ID | UJ | 150/3 |
| 1920 | Trouble restore [Warning Fault Zone] | Antimask återställd [Varning fel SEKTION] | Zone ID | UJ | 150/3 |
| 1921 | Trouble restore [Setting authorisation Zone] | Antimask återställd [Tillkopplingstillstånd SEKTION] | Zone ID | UJ | 150/3 |
| 1922 | Trouble restore [Lock element Zone] | Antimask återställd [Lås element SEKTION] | Zone ID | UJ | 150/3 |
| 1923 | Trouble restore [Glass Break Zone] | Antimask återställd [Glaskross SEKTION] | Zone ID | UJ | 150/3 |
| 2000 | Zone walked [Alarm Zone] | Sektion gångtestad [Larm SEKTION] | Zone ID | TP | 613/1 |
| 2001 | Zone walked [Entry/Exit Zone] | Sektion gångtestad [In/utpassering SEKTION] | Zone ID | TP | 613/1 |
| 2002 | Zone walked [Exit Term Zone] | Sektion gångtestad [Utpasseringstid SEKTION] | Zone ID | TP | – |
| 2003 | Zone walked [Fire Zone] | Sektion gångtestad [Brand SEKTION] | Zone ID | TP | 614/1 |
| 2004 | Zone walked [Fire Exit Zone] | Sektion gångtestad [Nödutgång SEKTION] | Zone ID | TP | – |
| 2005 | Zone walked [Line Zone] | Sektion gångtestad [Linje SEKTION] | Zone ID | TP | – |
| 2006 | Zone walked [Panic Zone] | Sektion gångtestad [Bråklarm SEKTION] | Zone ID | TP | 615/1 |
| 2007 | Zone walked [Holdup Zone] | Sektion gångtestad [Överfall SEKTION] | Zone ID | TP | – |
| 2008 | Zone walked [Tamper Zone] | Sektion gångtestad [SABOTAGE SEKTION] | Zone ID | TP | 613/1 |
| 2009 | Zone walked [Tech Zone] | Sektion gångtestad [Tekniskt larm SEKTION] | Zone ID | TP | – |
| 2010 | Zone walked [Medical Zone] | Sektion gångtestad [Medicinskt SEKTION] | Zone ID | TP | – |
| 2011 | Zone walked [Keyarm Zone] | Sektion gångtestad [Nyckeltillkoppling SEKTION] | Zone ID | TP | – |
| 2012 | Zone walked [Unused Zone] | Sektion gångtestad [Används ej SEKTION] | Zone ID | TP | – |
| 2013 | Zone walked [Shunt Zone] | Sektion gångtestad [Förbikopplare SEKTION] | Zone ID | TP | – |
| 2014 | Zone walked [X-Shunt Zone] | Sektion gångtestad [X-förbikopplare SEKTION] | Zone ID | TP | – |
| 2015 | Zone walked [Detector Fault Zone] | Sektion gångtestad [Detektorfel SEKTION] | Zone ID | TP | – |
| 2016 | Zone walked [Lock Supervision Zone] | Sektion gångtestad [Låskontroll SEKTION] | Zone ID | TP | – |
| 2017 | Zone walked [Seismic Zone] | Sektion gångtestad [Seismisk SEKTION] | Zone ID | TP | 613/1 |
| 2018 | Zone walked [All Okay Zone] | Sektion gångtestad [Allt OK SEKTION] | Zone ID | TP | – |
| 2019 | Zone walked [Holdup Fault Zone] | Sektion gångtestad [Överfall fel SEKTION] | Zone ID | TP | – |
| 2020 | Zone walked [Warning Fault Zone] | Sektion gångtestad [Varning fel SEKTION] | Zone ID | TP | – |
| 2021 | Zone walked [Setting authorisation Zone] | Sektion gångtestad [Tillkopplingstillstånd SEKTION] | Zone ID | TP | – |
| 2022 | Zone walked [Lock element Zone] | Sektion gångtestad [Lås element SEKTION] | Zone ID | TP | – |
| 2023 | Zone walked [Glass Break Zone] | Sektion gångtestad [Glaskross SEKTION] | Zone ID | TP | – |
| 2024 | SEISMIC TEST OK | SEISMISK TEST OK | Zone ID | BX | 750/1 |
| 2025 | SEISMIC TEST FAIL | SEISMISK TEST FEL | Zone ID | BF | 751/1 |
| 2100 | Zone input open | Sektionsingång öppen | Zone ID | ZO | – |
| 2101 | Zone input closed | Sektionsingång sluten | Zone ID | ZC | – |
| 2102 | Zone input shorted | Sektionsingång kortsluten | Zone ID | ZX | – |
| 2103 | Zone input disconnected | Sektionsingång bortkopplad | Zone ID | ZD | – |
| 2104 | Zone input masked | Sektionsingång antimask | Zone ID | ZM | – |
| 2105 | Zone input fault | Sektionsingångsfel | Zone ID | ZF | – |
| 2106 | Zone input unstable | Sektionsingång ostabil | Zone ID | ZN | – |
| 2107 | Zone input out of bounds | Sektionsingång ogiltigt värde | Zone ID | – | – |
| 2108 | Zone Low battery | Sektion lågt batteri | Zone ID | XT | – |
| 2109 | Zone Low battery - Restored | Sektion lågt batteri återställd | Zone ID | XR | – |
| 2110 | Zone input open | Sektionsingång öppen | Zone ID | ZO | – |
| 2111 | Zone input closed | Sektionsingång sluten | Zone ID | ZC | – |
| 2112 | Zone input shorted | Sektionsingång kortsluten | Zone ID | ZX | – |
| 2113 | Zone input disconnected | Sektionsingång bortkopplad | Zone ID | ZD | – |
| 2114 | Zone input masked | Sektionsingång antimask | Zone ID | ZM | – |
| 2115 | Zone input fault | Sektionsingångsfel | Zone ID | ZF | – |
| 2116 | Zone input unstable | Sektionsingång ostabil | Zone ID | ZN | – |
| 2117 | Zone input out of bounds | Sektionsingång ogiltigt värde | Zone ID | – | – |
| 3000 | Entry Granted | Inpassage godkänd | Door ID | DG | – |
| 3001 | Entry Denied | Inpassage nekad | Door ID | DD | – |
| 3002 | Exit Granted | Utpassage godkänd | Door ID | DG | – |
| 3003 | Exit Denied | Utpassage nekad | Door ID | DD | – |
| 3004 | Door Open too long | Dörr öppen för länge | Door ID | DN | – |
| 3005 | Left open | Lämnad öppen | Door ID | DN | – |
| 3006 | Door Forced Open | Forcerad öppning | Door ID | DF | – |
| 3007 | Door Normal | Dörr i normalläge | Door ID | DO | – |
| 3008 | Door Locked | Dörr låst | Door ID | DC | – |
| 3009 | Door Unlocked | Dörr olåst | Door ID | DO | – |
| 3010 | Door Open | Dörr öppen | Door ID | DO | – |
| 3011 | Door Closed | Dörr stängd | Door ID | – | – |
| 3012 | Door Release | DRS Öppnaknapp | Door ID | DX | – |
| 3013 | Alarm restore | LARMÅTERSTÄLL. | Door ID | DR | – |
| 3014 | Unknown card | Okänt kort | Door ID | AU | – |
| 3015 | Reader locked | Läsare spärrad | Door ID | RL | – |
| 3016 | Reader unlocked | Läsare olåst | Door ID | RG | – |
| 3500 | Alarm Confirmed | Larm Veriferat | Area ID | BV | 139/1 |
| 3501 | Unset | Frånkoppla | Area ID | OG | 401/1 |
| 3502 | Partset A | Deltillkoppling A | Area ID | NL | 456/3 |
| 3503 | Partset B | Deltillkoppling B | Area ID | NL | 456/3 |
| 3504 | Fullset | Tillkoppla | Area ID | CG | 401/3 |
| 3505 | Remote Unset | Fjärr Frånkoppla | User ID | OQ | – |
| 3506 | Remote Partset A | Fjärr Deltillkoppling A | Area ID | – | – |
| 3507 | Remote Partset B | Fjärr Deltillkoppling B | Area ID | – | – |
| 3508 | Remote Fullset | Fjärr Tillkoppla | User ID | CQ | – |
| 3509 | Keyarm [Unset Zone] | Nyckeltillkoppling [Frånkoppla SEKTION] | Zone ID | OS | – |
| 3510 | Keyarm [Fullset Zone] | Nyckeltillkoppling [Tillkoppla SEKTION] | Zone ID | CS | – |
| 3511 | Fail to Set | Tillkopplingsfel | Area ID | CI | 454/1 |
| 3512 | Entry timeout | TIMEOUT FÖR INPASSERINGSTID | Area ID | – | – |
| 3513 | Late to Set | Sen tillkoppling | Area ID | OT | 452/1 |
| 3514 | Late to unset | Sen frånkoppling | Area ID | CT | 452/1 |
| 3515 | Post alarm Unset | Efter larm Frånkoppla | Area ID | OG | 401/1 |
| 3516 | Early to set | Tidig tillkoppling | User ID | CK | 451/3 |
| 3517 | Early to unset | Tidig frånkoppling | User ID | OK | 451/1 |
| 3518 | Area Alarm Abort | Område Larm Avbrutet | User ID | BC | 406/1 |
| 3519 | Area Walk test Start | Område Gångtest | Area ID | ZK | 607/1 |
| 3520 | Area Walk test End | Område Gångtest | Area ID | TC | 607/3 |
| 3521 | All Areas Fullset | Alla områden Tillkoppla | Area ID | CL | – |
| 3522 | All Areas Unset | Alla områden Frånkoppla | Area ID | OP | – |
| 3523 | Confirmed holdup | Överfallslarm | Area ID | HV | 129/1 |
| 3524 | Entry Timer Started | Inpasseringstimer startad | Area ID | – | – |
| 3525 | Auto Set | Automatisk Tillkoppling | Area ID | CP | 403/3 |
| 3526 | Auto Unset | Automatisk Frånkoppling | Area ID | OA | 403/1 |
| 3527 | Unset Delayed START | Frånkoppling fördröjd START | Area ID | – | – |
| 3528 | Unset Delayed CANCELLED | Frånkoppling fördröjd AVBRUTEN | Area ID | – | – |
| 4000 | User Duress | Användare Hotlarm | User ID | HA | 121/1 |
| 4001 | User Duress Restore | Användare Hotlarm Återställ | User ID | HR | 121/3 |
| 4002 | USER PANIC | ANVÄNDARE BRÅKLARM | User ID | PA | 120/1 |
| 4003 | User accessing | Användare loggar in | User ID | JP | – |
| 4004 | User accessing end | Användare loggar ut | User ID | ZG | – |
| 4005 | Fob low batt Fault | FOB LÅGT BATTERI Fel | User ID | XT | – |
| 4006 | Fob low batt Restore | FOB LÅGT BATTERI Återställ | User ID | XR | – |
| 4007 | User code changed | Användarkod ändrad | User ID | JV | – |
| 4008 | USER PANIC Restore | ANVÄNDARE BRÅKLARM Återställ | User ID | PR | 120/3 |
| 4009 | User Medic | Användarmedicinskt larm | User ID | MA | 100/1 |
| 4010 | User Medic Restore | Användarmedicinskt larm Återställ | User ID | MR | 100/3 |
| 4011 | User Holdup | Användaröverfall | User ID | HA | 120/1 |
| 4012 | User Holdup Restore | Användaröverfall Återställ | User ID | HR | 120/3 |
| 4013 | User Webpass Changed | Användarwebbkod ändrad | User ID | JV | – |
| 4014 | Grant Access | Bevilja åtkomst | User ID | – | – |
| 4015 | Engineer access revoked | Installatörsläge upphävt | User ID | – | – |
| 4100 | MDT PANIC | MDT BRÅKLARM | User ID | PA | 120/1 |
| 4101 | MDT TILT | MDT TILT | User ID | MA | 100/1 |
| 4102 | MDT BELT | MDT BÄLTE | User ID | HA | 120/1 |
| 4103 | Man down panic Restore | Man down bråklarm Återställ | User ID | PR | 120/3 |
| 4104 | MDT TILT Restore | MDT TILT Återställ | User ID | MR | 100/3 |
| 4105 | MDT BELT Restore | MDT BÄLTE Återställ | User ID | HR | 120/3 |
| 4106 | MDT TAMPER | MDT SABOTAGE | User ID | – | – |
| 4200 | WPA Panic | WPA BRÅKL. | WPA ID | PA | 120/1 |
| 4201 | WPA Panic Restore | WPA BRÅKL. Återställ | WPA ID | PR | 120/3 |
| 4202 | WPA Holdup | WPA ÖF | WPA ID | HA | 120/1 |
| 4203 | WPA Holdup Restore | WPA ÖF Återställ | WPA ID | HR | 120/3 |
| 4204 | WPA suspicion | WPA MISSTANKE | WPA ID | – | – |
| 4205 | WPA suspicion Restore | WPA MISSTANKE Återställ | WPA ID | – | – |
| 4206 | WPA Medical | WPA Medicin larm | WPA ID | MA | 100/1 |
| 4207 | WPA Medical Restore | WPA Medicin larm Återställ | WPA ID | MR | 100/3 |
| 5000 | PSU Mains Fault | PSU 230V AC Fel | - | AT | 301/1 |
| 5001 | PSU Mains Restore | PSU 230V AC Återställ | - | AR | 301/3 |
| 5002 | PSU Mains Inhibit | PSU 230V AC Spärra | - | – | – |
| 5003 | PSU Mains Deinhibit | PSU 230V AC Ta bort bortkoppling | - | – | – |
| 5004 | PSU Mains Isolate | PSU 230V AC Isolera | - | – | – |
| 5005 | PSU Mains Deisolate | PSU 230V AC Ta bort isolering | - | – | – |
| 5006 | PSU Battery Fault | PSU Batteri Fel | - | YT | 311/1 |
| 5007 | PSU Battery Restore | PSU Batteri Återställ | - | YR | 311/3 |
| 5008 | PSU Battery Inhibit | PSU Batteri Spärra | - | – | – |
| 5009 | PSU Battery Deinhibit | PSU Batteri Ta bort bortkoppling | - | – | – |
| 5010 | PSU Battery Isolate | PSU Batteri Isolera | - | – | – |
| 5011 | PSU Battery Deisolate | PSU Batteri Ta bort isolering | - | – | – |
| 5012 | PSU EXT Fuse Fault | PSU EXT säkring Fel | - | YP | 312/1 |
| 5013 | PSU EXT Fuse Restore | PSU EXT säkring Återställ | - | YQ | 312/3 |
| 5014 | PSU EXT Fuse Inhibit | PSU EXT säkring Spärra | - | – | – |
| 5015 | PSU EXT Fuse Deinhibit | PSU EXT säkring Ta bort bortkoppling | - | – | – |
| 5016 | PSU EXT Fuse Isolate | PSU EXT säkring Isolera | - | – | – |
| 5017 | PSU EXT Fuse Deisolate | PSU EXT säkring Ta bort isolering | - | – | – |
| 5018 | PSU INT Fuse Fault | PSU INT säkring Fel | - | YP | 312/1 |
| 5019 | PSU INT Fuse Restore | PSU INT säkring Återställ | - | YQ | 312/3 |
| 5020 | PSU INT Fuse Inhibit | PSU INT säkring Spärra | - | – | – |
| 5021 | PSU INT Fuse Deinhibit | PSU INT säkring Ta bort bortkoppling | - | – | – |
| 5022 | PSU INT Fuse Isolate | PSU INT säkring Isolera | - | – | – |
| 5023 | PSU INT Fuse Deisolate | PSU INT säkring Ta bort isolering | - | – | – |
| 5024 | PSU Aux. Fuse Fault | PSU AUX-utgång, säkring Fel | - | YP | 312/1 |
| 5025 | PSU Aux. Fuse Restore | PSU AUX-utgång, säkring Återställ | - | YQ | 312/3 |
| 5026 | PSU Aux. Fuse Inhibit | PSU AUX-utgång, säkring Spärra | - | – | – |
| 5027 | PSU Aux. Fuse Deinhibit | PSU AUX-utgång, säkring Ta bort bortkoppling | - | – | – |
| 5028 | PSU Aux. Fuse Isolate | PSU AUX-utgång, säkring Isolera | - | – | – |
| 5029 | PSU Aux. Fuse Deisolate | PSU AUX-utgång, säkring Ta bort isolering | - | – | – |
| 5030 | PSU Fault Fault | PSU Fel Fel | - | YP | 300/1 |
| 5031 | PSU Fault Restore | PSU Fel Återställ | - | YQ | 300/3 |
| 5032 | PSU Fault Inhibit | PSU Fel Spärra | - | – | – |
| 5033 | PSU Fault Deinhibit | PSU Fel Ta bort bortkoppling | - | – | – |
| 5034 | PSU Fault Isolate | PSU Fel Isolera | - | – | – |
| 5035 | PSU Fault Deisolate | PSU Fel Ta bort isolering | - | – | – |
| 5036 | PSU Output fault | PSU utgångsfel | Expander | OU | – |
| 5037 | PSU Output ok | PSU utgång ok | Expander | OV | – |
| 5038 | PSU Low Voltage Trouble | PSU låg volt fel | Expander | XB | – |
| 5039 | PSU Low Voltage Restoral | PSU låg volt återställd | Expander | XC | – |
| 5040 | Low battery Fault | Lågt batteri Fel | Expander | XD | – |
| 5041 | Low battery Restore | Lågt batteri Återställ | Expander | XG | – |
| 5042 | PSU Discharged | PSU urladdad | Expander | XK | – |
| 5100 | RF JAM Fault | RF-STÖR. Fel | - | XQ | 344/1 |
| 5101 | RF JAM Restore | RF-STÖR. Återställ | - | XH | 344/3 |
| 5102 | RF JAM Inhibit | RF-STÖR. Spärra | - | – | – |
| 5103 | RF JAM Deinhibit | RF-STÖR. Ta bort bortkoppling | - | – | – |
| 5104 | RF JAM Isolate | RF-STÖR. Isolera | - | – | – |
| 5105 | RF JAM Deisolate | RF-STÖR. Ta bort isolering | - | – | – |
| 5106 | Antenna Tamper Fault | Antennsabotage Fel | - | XS | – |
| 5107 | Antenna Tamper Restore | Antennsabotage Återställ | - | XJ | – |
| 5108 | Antenna Tamper Inhibit | Antennsabotage Spärra | - | – | – |
| 5109 | Antenna Tamper Deinhibit | Antennsabotage Ta bort bortkoppling | - | – | – |
| 5110 | Antenna Tamper Isolate | Antennsabotage Isolera | - | – | – |
| 5111 | Antenna Tamper Deisolate | Antennsabotage Ta bort isolering | - | – | – |
| 5200 | Bell Tamper Fault | Sirensabotage Fel | - | YA | 320/1 |
| 5201 | Bell Tamper Restore | Sirensabotage Återställ | - | YH | 320/3 |
| 5202 | Bell Tamper Inhibit | Sirensabotage Spärra | - | – | – |
| 5203 | Bell Tamper Deinhibit | Sirensabotage Ta bort bortkoppling | - | – | – |
| 5204 | Bell Tamper Isolate | Sirensabotage Isolera | - | – | – |
| 5205 | Bell Tamper Deisolate | Sirensabotage Ta bort isolering | - | – | – |
| 5206 | Cabinet Tamper Fault | Kapslingssabotage Fel | - | TA | 137/1 |
| 5207 | Cabinet Tamper Restore | Kapslingssabotage Återställ | - | TR | 137/3 |
| 5208 | Cabinet Tamper Inhibit | Kapslingssabotage Spärra | - | – | – |
| 5209 | Cabinet Tamper Deinhibit | Kapslingssabotage Ta bort bortkoppling | - | – | – |
| 5210 | Cabinet Tamper Isolate | Kapslingssabotage Isolera | - | – | – |
| 5211 | Cabinet Tamper Deisolate | Kapslingssabotage Ta bort isolering | - | – | – |
| 5212 | AUX 1 Tamper Fault | AUX-UTG 1, SAB Fel | - | TA | 137/1 |
| 5213 | AUX 1 Tamper Restore | AUX-UTG 1, SAB Återställ | - | TR | 137/3 |
| 5214 | AUX 1 Tamper Inhibit | AUX-UTG 1, SAB Spärra | - | – | – |
| 5215 | AUX 1 Tamper Deinhibit | AUX-UTG 1, SAB Ta bort bortkoppling | - | – | – |
| 5216 | AUX 1 Tamper Isolate | AUX-UTG 1, SAB Isolera | - | – | – |
| 5217 | AUX 1 Tamper Deisolate | AUX-UTG 1, SAB Ta bort isolering | - | – | – |
| 5218 | AUX 2 Tamper Fault | AUX-UTG 2, SAB Fel | - | TA | 137/1 |
| 5219 | AUX 2 Tamper Restore | AUX-UTG 2, SAB Återställ | - | TR | 137/3 |
| 5220 | AUX 2 Tamper Inhibit | AUX-UTG 2, SAB Spärra | - | – | – |
| 5221 | AUX 2 Tamper Deinhibit | AUX-UTG 2, SAB Ta bort bortkoppling | - | – | – |
| 5222 | AUX 2 Tamper Isolate | AUX-UTG 2, SAB Isolera | - | – | – |
| 5223 | AUX 2 Tamper Deisolate | AUX-UTG 2, SAB Ta bort isolering | - | – | – |
| 5300 | XBUS cable fault | X-BUS-kabelfel | - | ES | 333/1 |
| 5301 | XBUS cable fault Restore | X-BUS-kabelfel Återställ | - | EJ | 333/3 |
| 5302 | XBUS cable fault Inhibit | X-BUS-kabelfel Spärra | - | – | – |
| 5303 | XBUS cable fault Deinhibit | X-BUS-kabelfel Ta bort bortkoppling | - | – | – |
| 5304 | XBUS cable fault Isolate | X-BUS-kabelfel Isolera | - | – | – |
| 5305 | XBUS cable fault Deisolate | X-BUS-kabelfel Ta bort isolering | - | – | – |
| 5306 | XBUS comms lost Fault | XBUS KOMM. AVBR. Fel | Expander | EM | 333/1 |
| 5307 | XBUS comms lost Restore | XBUS KOMM. AVBR. Återställ | Expander | EN | 333/3 |
| 5308 | XBUS comms lost Inhibit | XBUS KOMM. AVBR. Spärra | Expander | – | – |
| 5309 | XBUS comms lost Deinhibit | XBUS KOMM. AVBR. Ta bort bortkoppling | Expander | – | – |
| 5310 | XBUS comms lost Isolate | XBUS KOMM. AVBR. Isolera | Expander | – | – |
| 5311 | XBUS comms lost Deisolate | XBUS KOMM. AVBR. Ta bort isolering | Expander | – | – |
| 5312 | XBUS tamper Fault | XBUS, SABOTAGE Fel | Expander | ES | 341/1 |
| 5313 | XBUS tamper Restore | XBUS, SABOTAGE Återställ | Expander | EJ | 341/3 |
| 5314 | XBUS tamper Inhibit | XBUS, SABOTAGE Spärra | Expander | – | – |
| 5315 | XBUS tamper Deinhibit | XBUS, SABOTAGE Ta bort bortkoppling | Expander | – | – |
| 5316 | XBUS tamper Isolate | XBUS, SABOTAGE Isolera | Expander | – | – |
| 5317 | XBUS tamper Deisolate | XBUS, SABOTAGE Ta bort isolering | Expander | – | – |
| 5318 | XBUS fuse fault | XBUS, SÄKR. FEL | Expander | ET | 333/1 |
| 5319 | XBUS fuse fault Restore | XBUS, SÄKR. FEL Återställ | Expander | ER | 333/3 |
| 5320 | XBUS fuse fault Inhibit | XBUS, SÄKR. FEL Spärra | Expander | – | – |
| 5321 | XBUS fuse fault Deinhibit | XBUS, SÄKR. FEL Ta bort bortkoppling | Expander | – | – |
| 5322 | XBUS fuse fault Isolate | XBUS, SÄKR. FEL Isolera | Expander | – | – |
| 5323 | XBUS fuse fault Deisolate | XBUS, SÄKR. FEL Ta bort isolering | Expander | – | – |
| 5324 | XBUS mains fault | XBUS, NÄTFEL | Expander | AT | 342/1 |
| 5325 | XBUS mains fault Restore | XBUS, NÄTFEL Återställ | Expander | AR | 342/3 |
| 5326 | XBUS mains fault Inhibit | XBUS, NÄTFEL Spärra | Expander | – | – |
| 5327 | XBUS mains fault Deinhibit | XBUS, NÄTFEL Ta bort bortkoppling | Expander | – | – |
| 5328 | XBUS mains fault Isolate | XBUS, NÄTFEL Isolera | Expander | – | – |
| 5329 | XBUS mains fault Deisolate | XBUS, NÄTFEL Ta bort isolering | Expander | – | – |
| 5330 | XBUS battery Fault | X-BUS, BATTERI Fel | Expander | ET | 338/1 |
| 5331 | XBUS battery Restore | X-BUS, BATTERI Återställ | Expander | ER | 338/3 |
| 5332 | XBUS battery Inhibit | X-BUS, BATTERI Spärra | Expander | – | – |
| 5333 | XBUS battery Deinhibit | X-BUS, BATTERI Ta bort bortkoppling | Expander | – | – |
| 5334 | XBUS battery Isolate | X-BUS, BATTERI Isolera | Expander | – | – |
| 5335 | XBUS battery Deisolate | X-BUS, BATTERI Ta bort isolering | Expander | – | – |
| 5336 | XBUS rf jamming Fault | XBUS, RF-STÖR. Fel | Expander | XQ | 344/1 |
| 5337 | XBUS rf jamming Restore | XBUS, RF-STÖR. Återställ | Expander | XH | 344/3 |
| 5338 | XBUS rf jamming Inhibit | XBUS, RF-STÖR. Spärra | Expander | – | – |
| 5339 | XBUS rf jamming Deinhibit | XBUS, RF-STÖR. Ta bort bortkoppling | Expander | – | – |
| 5340 | XBUS rf jamming Isolate | XBUS, RF-STÖR. Isolera | Expander | – | – |
| 5341 | XBUS rf jamming Deisolate | XBUS, RF-STÖR. Ta bort isolering | Expander | – | – |
| 5342 | X-BUS Antenna Tamper Fault | X-BUS Antennsabotage Fel | Expander | XS | 341/1 |
| 5343 | X-BUS Antenna Tamper Restore | X-BUS Antennsabotage Återställ | Expander | XJ | 341/3 |
| 5344 | X-BUS Antenna Tamper Inhibit | X-BUS Antennsabotage Spärra | Expander | – | – |
| 5345 | X-BUS Antenna Tamper Deinhibit | X-BUS Antennsabotage Ta bort bortkoppling | Expander | – | – |
| 5346 | X-BUS Antenna Tamper Isolate | X-BUS Antennsabotage Isolera | Expander | – | – |
| 5347 | X-BUS Antenna Tamper Deisolate | X-BUS Antennsabotage Ta bort isolering | Expander | – | – |
| 5348 | XBUS panic Alarm | XBUS, BRÅKLARM Larm | Expander | PA | 120/1 |
| 5349 | XBUS panic Restore | XBUS, BRÅKLARM Återställ | Expander | PR | 120/3 |
| 5350 | XBUS fire Alarm | XBUS, BRAND Larm | Expander | FA | 110/1 |
| 5351 | XBUS fire Restore | XBUS, BRAND Återställ | Expander | FR | 110/3 |
| 5352 | XBUS medical Alarm | XBUS, MEDICIN Larm | Expander | MA | 100/1 |
| 5353 | XBUS medical Restore | XBUS, MEDICIN Återställ | Expander | MR | 100/3 |
| 5354 | XBUS PSU Fault | XBUS, PSU-FEL | Expander | ET | 330/1 |
| 5355 | XBUS PSU Fault Restore | XBUS, PSU-FEL Återställ | Expander | ER | 330/3 |
| 5356 | XBUS PSU Fault Inhibit | XBUS, PSU-FEL Spärra | Expander | – | – |
| 5357 | XBUS PSU Fault Deinhibit | XBUS, PSU-FEL Ta bort bortkoppling | Expander | – | – |
| 5358 | XBUS PSU Fault Isolate | XBUS, PSU-FEL Isolera | Expander | – | – |
| 5359 | XBUS PSU Fault Deisolate | XBUS, PSU-FEL Ta bort isolering | Expander | – | – |
| 5360 | Keypad locked | Manöverpanel LÅST | Expander | ZE | – |
| 5361 | Keypad Not Locked Out | Manöverpanel Inte spärrad | Expander | KG | – |
| 5362 | WEB locked | WEB LÅST | - | WW | – |
| 5363 | WEB Not Locked Out | WEB Inte spärrad | - | WX | – |
| 6000 | Network Fail | Nätverksfel | - | XY | – |
| 6001 | Network Restoral | Nätverk återställd | - | XZ | – |
| 6002 | FlexC ATP Down | FlexC ATP Ned | ATP ID | NT | – |
| 6003 | FlexC ATP Up | FlexC ATP EDP kontakt | ATP ID | NR | – |
| 6004 | FlexC ATS Down | FlexC ATS Ned | - | YC | – |
| 6005 | FlexC ATS Up | FlexC ATS EDP kontakt | - | YK | – |
| 6006 | FlexC Manual Test | FlexC Manuellt test | User ID | RX | 601/1 |
| 6007 | FlexC Automatic Testcall Active | FlexC Automatisk testsignal Aktiv | ATP ID | RP | 602/1 |
| 6008 | EDP Receiver Down | EDP mottagare Ned | EDP Receiver ID | NT | – |
| 6009 | EDP Receiver Up | EDP mottagare EDP kontakt | EDP Receiver ID | NR | – |
| 6010 | EDP Manual Test | EDP Manuellt test | EDP Receiver ID | RX | 601/1 |
| 6011 | EDP Automatic Testcall | EDP Automatisk testsignal | EDP Receiver ID | RP | 602/1 |
| 6012 | Modem Manual Test | Modem Manuellt test | User ID | RX | 601/1 |
| 6013 | Modem Automatic Testcall | Modem Automatisk testsignal | Modem ID | RP | 602/1 |
| 6015 | FlexC Automatic Testcall | FlexC Automatisk testsignal | ATP ID | RP | 602/1 |
| 6100 | Modem 1 Fault | Modem 1, fel | Modem ID | YS | 351/1 |
| 6101 | Modem 1 Fault Restore | Modem 1, fel Återställ | Modem ID | YK | 351/3 |
| 6102 | Modem 1 Fault Inhibit | Modem 1, fel Spärra | Modem ID | – | – |
| 6103 | Modem 1 Fault Deinhibit | Modem 1, fel Ta bort bortkoppling | Modem ID | – | – |
| 6104 | Modem 1 Fault Isolate | Modem 1, fel Isolera | Modem ID | – | – |
| 6105 | Modem 1 Fault Deisolate | Modem 1, fel Ta bort isolering | Modem ID | – | – |
| 6106 | Modem 1 Line Fault | Modem 1, linjefel | Modem ID | LT | 351/1 |
| 6107 | Modem 1 Line Fault Restore | Modem 1, linjefel Återställ | Modem ID | LR | 351/3 |
| 6108 | Modem 1 Line Fault Inhibit | Modem 1, linjefel Spärra | Modem ID | – | – |
| 6109 | Modem 1 Line Fault Deinhibit | Modem 1, linjefel Ta bort bortkoppling | Modem ID | – | – |
| 6110 | Modem 1 Line Fault Isolate | Modem 1, linjefel Isolera | Modem ID | – | – |
| 6111 | Modem 1 Line Fault Deisolate | Modem 1, linjefel Ta bort isolering | Modem ID | – | – |
| 6112 | Modem 2 Fault | Modem 2, fel | Modem ID | YS | 352/1 |
| 6113 | Modem 2 Fault Restore | Modem 2, fel Återställ | Modem ID | YK | 351/3 |
| 6114 | Modem 2 Line Fault | Modem 2, linjefel | Modem ID | LT | 352/1 |
| 6115 | Modem 2 Line Fault Restore | Modem 2, linjefel Återställ | Modem ID | LR | 351/3 |
| 6116 | Modem 2 Fault Inhibit | Modem 2, fel Spärra | Modem ID | – | – |
| 6117 | Modem 2 Fault Deinhibit | Modem 2, fel Ta bort bortkoppling | Modem ID | – | – |
| 6118 | Modem 2 Fault Isolate | Modem 2, fel Isolera | Modem ID | – | – |
| 6119 | Modem 2 Fault Deisolate | Modem 2, fel Ta bort isolering | Modem ID | – | – |
| 6120 | Modem 2 Line Fault Inhibit | Modem 2, linjefel Spärra | Modem ID | – | – |
| 6121 | Modem 2 Line Fault Deinhibit | Modem 2, linjefel Ta bort bortkoppling | Modem ID | – | – |
| 6122 | Modem 2 Line Fault Isolate | Modem 2, linjefel Isolera | Modem ID | – | – |
| 6123 | Modem 2 Line Fault Deisolate | Modem 2, linjefel Ta bort isolering | Modem ID | – | – |
| 7000 | System boot | SYSTEMSTART | - | RR | 305/1 |
| 7001 | User Code Tamper | Användare Kod försök | - | JA | 461/1 |
| 7002 | Date Changed | Ändra datum | - | JT | 625/1 |
| 7003 | Engineer Enabled | Installatör aktiverad | - | LB | 466/1 |
| 7004 | Engineer Disabled | Installatör inaktiverad | - | LX | 466/3 |
| 7005 | Hardware fault | HÅRDVARUFEL | - | HF | – |
| 7006 | Alert (Close Alert) | Larm (Stäng Larm) | Alert ID | SD | – |
| 7007 | Alert (Open Alert) | Larm (Öppen Larm) | Alert ID | SO | – |
| 7008 | Alert (X-BUS Alert Expander) | Larm (X-BUS Larm Expansionenhet) | Alert ID | NB | – |
| 7009 | Alert (X-BUS Alert Expander) | Larm (X-BUS Larm Expansionenhet) | Alert ID | NO | – |
| 7010 | Code Tamper System | Kod försök System | - | JA | 461/1 |
| 7011 | Configuration changed | KONFIGURATION ÄNDRAD | - | – | – |
| 7012 | Code Tamper X-BUS | Kod försök X-BUS | Expander | JA | 461/1 |
| 7013 | Mapping gate ON | Mapping gate PÅ | - | – | – |
| 7014 | Mapping gate OFF | Mapping gate AV | - | – | – |
| 8000 | Camera Offline | Kamera offline | Camera ID | CV | – |
| 8001 | Camera Online | Kamera online | Camera ID | CU | – |
| 8002 | Service Engineer Access Request | Service installatör åtkomst begärd | User ID | SE | – |
| 8003 | Hold-up Information | Överfalls information | - | HD | – |
| 8004 | Wireless Lost Event | Trådlös tappad händelse | Zone ID | BZ | 147/1 |
| 8005 | Wireless Supervision Restore | Återställ trådlös övervakning | Zone ID | WZ | 147/3 |
| 8006 | Two Way Wireless Tamper | Tvåvägs trådlös sabotage | Area ID | TA | 137/1 |
| 8007 | Two Way Wireless Tamper Restore | Tvåvägs trådlös sabotage Återställ | Area ID | TR | 137/3 |
| 8008 | Two Way Wireless Tamper Inhibit | Tvåvägs trådlös sabotage Spärra | Area ID | – | – |
| 8009 | Two Way Wireless Tamper Deinhibit | Tvåvägs trådlös sabotage Ta bort bortkoppling | Area ID | – | – |
| 8010 | Two Way Wireless Tamper Isolate | Tvåvägs trådlös sabotage Isolera | Area ID | – | – |
| 8011 | Two Way Wireless Tamper Deisolate | Tvåvägs trådlös sabotage Ta bort isolering | Area ID | – | – |
| 8012 | Two way wireless low battery | Tvåvägs trådlös lågt batteri | Area ID | XT | – |
| 8013 | Two way wireless low battery Battery Restoral | Tvåvägs trådlös lågt batteri Batteriåterställning | Area ID | XR | – |
| 8014 | Two Way Wireless Trouble | Tvåvägs trådlös fel | Area ID | UT | 150/1 |
| 8015 | Two Way Wireless Trouble Restore | Tvåvägs trådlös fel Återställ | Area ID | UJ | 150/3 |
| 8016 | Two Way Wireless Trouble Inhibit | Tvåvägs trådlös fel Spärra | Area ID | – | – |
| 8017 | Two Way Wireless Trouble Deinhibit | Tvåvägs trådlös fel Ta bort bortkoppling | Area ID | – | – |
| 8018 | Two Way Wireless Trouble Isolate | Tvåvägs trådlös fel Isolera | Area ID | – | – |
| 8019 | Two Way Wireless Trouble Deisolate | Tvåvägs trådlös fel Ta bort isolering | Area ID | – | – |
| 8020 | Two Way Wireless DC Supply | Tvåvägs trådlös DC spänning | Area ID | AT | – |
| 8021 | Two Way Wireless DC Supply Restore | Tvåvägs trådlös DC spänning Återställ | Area ID | AT | – |
| 8022 | Two Way Wireless DC Supply Inhibit | Tvåvägs trådlös DC spänning Spärra | Area ID | – | – |
| 8023 | Two Way Wireless DC Supply Deinhibit | Tvåvägs trådlös DC spänning Ta bort bortkoppling | Area ID | – | – |
| 8024 | Two Way Wireless DC Supply Isolate | Tvåvägs trådlös DC spänning Isolera | Area ID | – | – |
| 8025 | Two Way Wireless DC Supply Deisolate | Tvåvägs trådlös DC spänning Ta bort isolering | Area ID | – | – |
| 8026 | Two Way Wireless Medical Alarm | Tvåvägs trådlös Medicinskt Larm | Area ID | MA | 100/1 |
| 8027 | Two Way Wireless Medical Restore | Tvåvägs trådlös Medicinskt Återställ | Area ID | MR | 100/3 |
| 8028 | Two Way Wireless Fire Alarm | Tvåvägs trådlös Brand Larm | Area ID | FA | 110/1 |
| 8029 | Two Way Wireless Fire Restore | Tvåvägs trådlös Brand Återställ | Area ID | FR | 110/3 |
| 8030 | Two Way Wireless Panic Alarm | Tvåvägs trådlös Bråklarm Larm | Area ID | PA | 120/1 |
| 8031 | Two Way Wireless Panic Restore | Tvåvägs trådlös Bråklarm Återställ | Area ID | PR | 120/3 |
| 8032 | Two Way Wireless code tamper Alarm | Tvåvägs trådlös kodsabotage Larm | Area ID | JA | 461/1 |
| 8033 | Two Way Wireless code tamper Restore | Tvåvägs trådlös kodsabotage Återställ | Area ID | JA | 461/3 |
| 8034 | Two Way Wireless code tamper Inhibit | Tvåvägs trådlös kodsabotage Spärra | Area ID | – | – |
| 8035 | Two Way Wireless code tamper Deinhibit | Tvåvägs trådlös kodsabotage Ta bort bortkoppling | Area ID | – | – |
| 8036 | Two Way Wireless code tamper Isolate | Tvåvägs trådlös kodsabotage Isolera | Area ID | – | – |
| 8037 | Two Way Wireless code tamper Deisolate | Tvåvägs trådlös kodsabotage Ta bort isolering | Area ID | – | – |
| 8038 | Keypad locked | Manöverpanel LÅST | Area ID | ZE | – |
| 8039 | Keypad Not Locked Out | Manöverpanel Inte spärrad | Area ID | KG | – |
