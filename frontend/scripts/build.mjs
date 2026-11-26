import { readFile, writeFile, mkdir } from "node:fs/promises";
import { SOURCES, bundle } from "./sources.mjs";

const packageMetadata = JSON.parse(await readFile("package.json", "utf8"));
const CARD_VERSION = packageMetadata.version;
const lock = JSON.parse(await readFile("package-lock.json", "utf8"));
lock.version = CARD_VERSION;
lock.packages[""].version = CARD_VERSION;
await writeFile("package-lock.json", `${JSON.stringify(lock, null, 2)}\n`, "utf8");

const sources = await Promise.all(SOURCES.map((path) => readFile(path, "utf8")));
await mkdir("../custom_components/spc_flexc/www", { recursive: true });
await writeFile("../custom_components/spc_flexc/www/ha-spc-flexc-card.js", bundle(sources, CARD_VERSION), "utf8");
console.log(`Built ha-spc-flexc-card.js v${CARD_VERSION}`);
