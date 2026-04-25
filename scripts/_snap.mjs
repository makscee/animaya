// Screenshot any path on the LXC dashboard with voidnet HMAC headers set
// context-wide, so all page + XHR requests pass through the middleware
// voidnet branch exactly like a real browser behind voidnet-api would.
//
// Args: <path> <outfile>
//   eg. node _snap.mjs /modules/git-versioning /tmp/shot.png
import { chromium } from "playwright";
import crypto from "node:crypto";
import fs from "node:fs";

const [, , rawPath = "/", out = "/tmp/snap.png"] = process.argv;

const env = fs.readFileSync("/home/maks-test/animaya/.env", "utf8");
const secret = /VOIDNET_HMAC_SECRET=(.+)/.exec(env)[1].trim();
const owner = /OWNER_TELEGRAM_ID=(.+)/.exec(env)[1].trim();
const userId = "45";
const handle = "maks-test";
const ts = String(Math.floor(Date.now() / 1000));
const sig = crypto
  .createHmac("sha256", secret)
  .update(`${userId}|${handle}|${owner}|${ts}`)
  .digest("hex");

const browser = await chromium.launch();
const ctx = await browser.newContext({
  extraHTTPHeaders: {
    "x-voidnet-user-id": userId,
    "x-voidnet-handle": handle,
    "x-voidnet-telegram-id": owner,
    "x-voidnet-timestamp": ts,
    "x-voidnet-signature": sig,
  },
  viewport: { width: 1280, height: 900 },
});
const page = await ctx.newPage();
await page.goto(`http://127.0.0.1:8090${rawPath}`, { waitUntil: "networkidle" });
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log(out);
