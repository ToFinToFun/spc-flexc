// The card sources in bundle order. The core card comes first (it carries
// CARD_VERSION on its first line); the shared UI base comes before the cards
// built on it, and the app last.
export const SOURCES = [
  "src/ha-spc-flexc-card.js",
  "src/spc-flexc-outputs.js",
  "src/spc-flexc-zone-isolation.js",
  "src/spc-flexc-zone-groups.js",
  "src/spc-flexc-i18n.js",
  "src/spc-flexc-area-cards.js",
  "src/spc-flexc-communication.js",
  "src/spc-flexc-xbus.js",
  "src/spc-flexc-responsive.js",
  "src/spc-flexc-render-scheduler.js",
  "src/spc-flexc-activity.js",
  "src/spc-flexc-ui.js",
  "src/spc-flexc-users.js",
  "src/spc-flexc-calendars.js",
  "src/spc-flexc-profiles.js",
  "src/spc-flexc-logs.js",
  "src/spc-flexc-settings-text.js",
  "src/spc-flexc-system.js",
  "src/spc-flexc-zones.js",
  "src/spc-flexc-doors.js",
  "src/spc-flexc-app.js",
];

export function bundle(sources, version) {
  const [core, ...rest] = sources;
  const head = core.replace(/^const CARD_VERSION = "[^"]+";/, `const CARD_VERSION = "${version}";`).trimEnd();
  const parts = rest.map((source, index) => (index === rest.length - 1 ? source.trimStart() : source.trim()));
  return [head, ...parts].join("\n\n");
}
