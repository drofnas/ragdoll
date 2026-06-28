import { describe, expect, it } from "vitest";

import { formatRelativeAgeShort } from "./formatting";

describe("formatRelativeAgeShort", () => {
  const now = new Date("2026-06-24T12:00:00Z").getTime();

  it("returns a fallback for missing or invalid dates", () => {
    expect(formatRelativeAgeShort(null, now)).toBe("?");
    expect(formatRelativeAgeShort(undefined, now)).toBe("?");
    expect(formatRelativeAgeShort("not-a-date", now)).toBe("?");
  });

  it("formats future and sub-minute dates as now", () => {
    expect(formatRelativeAgeShort("2026-06-24T12:00:30Z", now)).toBe("now");
    expect(formatRelativeAgeShort("2026-06-24T11:59:31Z", now)).toBe("now");
  });

  it("formats elapsed dates with compact units", () => {
    expect(formatRelativeAgeShort("2026-06-24T11:59:00Z", now)).toBe("1m");
    expect(formatRelativeAgeShort("2026-06-24T10:00:00Z", now)).toBe("2h");
    expect(formatRelativeAgeShort("2026-06-18T12:00:00Z", now)).toBe("6d");
    expect(formatRelativeAgeShort("2026-06-10T12:00:00Z", now)).toBe("2w");
    expect(formatRelativeAgeShort("2026-03-26T12:00:00Z", now)).toBe("3mo");
    expect(formatRelativeAgeShort("2024-06-24T12:00:00Z", now)).toBe("2y");
  });
});
