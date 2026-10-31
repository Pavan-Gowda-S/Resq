import { describe, expect, it } from "vitest";
import { extractIncident, nearestDistrict, stageFromStatus } from "@/lib/resq-data";

describe("SOS auto-extraction", () => {
  it("detects flood and counts", () => {
    const r = extractIncident("Water is rising, 6 people in our house and 2 are trapped on the roof");
    expect(r.hazard).toBe("Flood");
    expect(r.affected).toBe(6);
    expect(r.trapped).toBe(2);
  });
  it("detects landslide from Malayalam", () => {
    expect(extractIncident("ഉരുൾ പൊട്ടി").hazard).toBe("Landslide");
  });
});

describe("tracking stages", () => {
  it("maps backend statuses to the 5-stage stepper", () => {
    expect(stageFromStatus("REPORTED")).toBe(0);
    expect(stageFromStatus("DISPATCHING")).toBe(2);
    expect(stageFromStatus("RESOLVED")).toBe(4);
  });
});

describe("GPS district", () => {
  it("resolves Meppadi coords to Wayanad", () => {
    expect(nearestDistrict(11.55, 76.13)).toBe("Wayanad");
  });
});
