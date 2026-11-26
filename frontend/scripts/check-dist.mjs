import { readFile } from "node:fs/promises";
import { SOURCES, bundle } from "./sources.mjs";

const packageMetadata = JSON.parse(await readFile("package.json", "utf8"));
const CARD_VERSION = packageMetadata.version;
const sources = await Promise.all(SOURCES.map((path) => readFile(path, "utf8")));
const distribution = await readFile("../custom_components/spc_flexc/www/ha-spc-flexc-card.js", "utf8");

if (bundle(sources, CARD_VERSION) !== distribution) {
  console.error("ha-spc-flexc-card.js is out of date. Run: npm run build");
  process.exit(1);
}

console.log(`Distribution file v${CARD_VERSION} is up to date.`);
