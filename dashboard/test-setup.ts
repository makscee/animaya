// Bun test preload: neutralize "server-only" so server modules can be imported
// from the test runner (which is neither client nor RSC).
import { mock } from "bun:test";

mock.module("server-only", () => ({}));
