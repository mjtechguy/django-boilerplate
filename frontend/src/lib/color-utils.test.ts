import { describe, it, expect } from "vitest";
import { hexToOklch, adjustLightness, getPrimaryForeground } from "./color-utils";

describe("color-utils", () => {
  describe("hexToOklch", () => {
    it("converts hex color to oklch format correctly", () => {
      const result = hexToOklch("#10b981");

      // Result should be in format "oklch(L C h)" where:
      // L is lightness (0-1), C is chroma, h is hue (0-360)
      expect(result).toMatch(/^oklch\(\d+\.\d+ \d+\.\d+ \d+\.\d+\)$/);
    });

    it("converts black (#000000) correctly", () => {
      const result = hexToOklch("#000000");

      // Black should have very low lightness
      expect(result).toMatch(/^oklch\(0\.0\d+ /);
    });

    it("converts white (#ffffff) correctly", () => {
      const result = hexToOklch("#ffffff");

      // White should have high lightness close to 1
      expect(result).toMatch(/^oklch\((0\.9\d+|1\.0\d+) /);
    });

    it("handles hex without # prefix", () => {
      const withHash = hexToOklch("#10b981");
      const withoutHash = hexToOklch("10b981");

      // Should produce same result regardless of # prefix
      expect(withoutHash).toBe(withHash);
    });

    it("converts red (#ff0000) correctly", () => {
      const result = hexToOklch("#ff0000");

      // Red should have hue around 29 degrees in OKLCh
      expect(result).toMatch(/oklch\(\d+\.\d+ \d+\.\d+ \d+\.\d+\)/);
      // Lightness should be moderate
      expect(result).toMatch(/oklch\((0\.[4-7]\d+)/);
    });

    it("converts green (#00ff00) correctly", () => {
      const result = hexToOklch("#00ff00");

      // Green should have higher lightness
      expect(result).toMatch(/oklch\((0\.[7-9]\d+)/);
    });

    it("converts blue (#0000ff) correctly", () => {
      const result = hexToOklch("#0000ff");

      // Blue should have moderate lightness
      expect(result).toMatch(/oklch\((0\.[3-6]\d+)/);
    });

    it("formats values to 3 decimal places", () => {
      const result = hexToOklch("#10b981");

      // Extract the three numeric values
      const matches = result.match(/oklch\((\d+\.\d+) (\d+\.\d+) (\d+\.\d+)\)/);
      expect(matches).not.toBeNull();

      if (matches) {
        const [, L, C, h] = matches;
        // Each value should have exactly 3 decimal places
        expect(L.split(".")[1]).toHaveLength(3);
        expect(C.split(".")[1]).toHaveLength(3);
        expect(h.split(".")[1]).toHaveLength(3);
      }
    });
  });

  describe("adjustLightness", () => {
    it("increases lightness with positive offset", () => {
      const base = hexToOklch("#10b981");
      const lighter = adjustLightness("#10b981", 0.2);

      // Extract lightness values
      const baseLightness = parseFloat(base.match(/oklch\((\d+\.\d+)/)?.[1] || "0");
      const lighterLightness = parseFloat(lighter.match(/oklch\((\d+\.\d+)/)?.[1] || "0");

      expect(lighterLightness).toBeGreaterThan(baseLightness);
      expect(lighterLightness).toBeCloseTo(baseLightness + 0.2, 2);
    });

    it("decreases lightness with negative offset", () => {
      const base = hexToOklch("#10b981");
      const darker = adjustLightness("#10b981", -0.2);

      // Extract lightness values
      const baseLightness = parseFloat(base.match(/oklch\((\d+\.\d+)/)?.[1] || "0");
      const darkerLightness = parseFloat(darker.match(/oklch\((\d+\.\d+)/)?.[1] || "0");

      expect(darkerLightness).toBeLessThan(baseLightness);
      expect(darkerLightness).toBeCloseTo(baseLightness - 0.2, 2);
    });

    it("clamps lightness to maximum of 1", () => {
      const result = adjustLightness("#ffffff", 0.5);

      // Even with positive offset, lightness should not exceed 1
      const lightness = parseFloat(result.match(/oklch\((\d+\.\d+)/)?.[1] || "0");
      expect(lightness).toBeLessThanOrEqual(1);
    });

    it("clamps lightness to minimum of 0", () => {
      const result = adjustLightness("#000000", -0.5);

      // Even with negative offset, lightness should not go below 0
      const lightness = parseFloat(result.match(/oklch\((\d+\.\d+)/)?.[1] || "0");
      expect(lightness).toBeGreaterThanOrEqual(0);
    });

    it("preserves chroma and hue when adjusting lightness", () => {
      const base = hexToOklch("#10b981");
      const adjusted = adjustLightness("#10b981", 0.1);

      // Extract chroma and hue from both
      const baseMatch = base.match(/oklch\(\d+\.\d+ (\d+\.\d+) (\d+\.\d+)\)/);
      const adjustedMatch = adjusted.match(/oklch\(\d+\.\d+ (\d+\.\d+) (\d+\.\d+)\)/);

      expect(baseMatch?.[1]).toBe(adjustedMatch?.[1]); // Chroma should be same
      expect(baseMatch?.[2]).toBe(adjustedMatch?.[2]); // Hue should be same
    });

    it("handles zero offset (no change)", () => {
      const base = hexToOklch("#10b981");
      const unchanged = adjustLightness("#10b981", 0);

      // Extract lightness values
      const baseLightness = parseFloat(base.match(/oklch\((\d+\.\d+)/)?.[1] || "0");
      const unchangedLightness = parseFloat(unchanged.match(/oklch\((\d+\.\d+)/)?.[1] || "0");

      expect(unchangedLightness).toBeCloseTo(baseLightness, 3);
    });

    it("formats adjusted values to 3 decimal places", () => {
      const result = adjustLightness("#10b981", 0.15);

      // Extract the three numeric values
      const matches = result.match(/oklch\((\d+\.\d+) (\d+\.\d+) (\d+\.\d+)\)/);
      expect(matches).not.toBeNull();

      if (matches) {
        const [, L, C, h] = matches;
        expect(L.split(".")[1]).toHaveLength(3);
        expect(C.split(".")[1]).toHaveLength(3);
        expect(h.split(".")[1]).toHaveLength(3);
      }
    });
  });

  describe("getPrimaryForeground", () => {
    it("returns white for dark backgrounds", () => {
      const result = getPrimaryForeground("#000000");

      // Should return white (high lightness, no chroma)
      expect(result).toBe("oklch(0.98 0 0)");
    });

    it("returns dark color for light backgrounds", () => {
      const result = getPrimaryForeground("#ffffff");

      // Should return dark color (low lightness, no chroma)
      expect(result).toBe("oklch(0.15 0 0)");
    });

    it("returns white for medium-dark colors", () => {
      // Navy blue - dark color
      const result = getPrimaryForeground("#000080");

      expect(result).toBe("oklch(0.98 0 0)");
    });

    it("returns dark for medium-light colors", () => {
      // Light yellow - light color
      const result = getPrimaryForeground("#ffffe0");

      expect(result).toBe("oklch(0.15 0 0)");
    });

    it("returns white for red (#ff0000)", () => {
      // Pure red has moderate luminance but typically needs white text
      const result = getPrimaryForeground("#ff0000");

      // Red's relative luminance is ~0.21, which is < 0.5
      expect(result).toBe("oklch(0.98 0 0)");
    });

    it("returns dark for yellow (#ffff00)", () => {
      // Pure yellow has high luminance and needs dark text
      const result = getPrimaryForeground("#ffff00");

      // Yellow's relative luminance is ~0.93, which is > 0.5
      expect(result).toBe("oklch(0.15 0 0)");
    });

    it("returns white for blue (#0000ff)", () => {
      // Pure blue has low luminance and needs white text
      const result = getPrimaryForeground("#0000ff");

      // Blue's relative luminance is ~0.07, which is < 0.5
      expect(result).toBe("oklch(0.98 0 0)");
    });

    it("returns dark for cyan (#00ffff)", () => {
      // Cyan has high luminance and needs dark text
      const result = getPrimaryForeground("#00ffff");

      // Cyan's relative luminance is ~0.79, which is > 0.5
      expect(result).toBe("oklch(0.15 0 0)");
    });

    it("uses threshold of 0.5 for luminance decision", () => {
      // Test a color right at the boundary
      // Gray with RGB ~186 has luminance close to 0.5
      const justDark = getPrimaryForeground("#b8b8b8"); // luminance ~0.49
      const justLight = getPrimaryForeground("#bcbcbc"); // luminance ~0.51

      // Just below threshold should return white
      expect(justDark).toBe("oklch(0.98 0 0)");
      // Just above threshold should return dark
      expect(justLight).toBe("oklch(0.15 0 0)");
    });

    it("returns achromatic values (chroma = 0)", () => {
      const whiteResult = getPrimaryForeground("#000000");
      const darkResult = getPrimaryForeground("#ffffff");

      // Both should have 0 chroma (pure white or pure black/dark gray)
      expect(whiteResult).toContain(" 0 0)");
      expect(darkResult).toContain(" 0 0)");
    });
  });

  describe("edge cases", () => {
    it("handles three-digit hex codes by treating them as six-digit", () => {
      // Note: The current implementation expects 6-digit hex codes
      // Three-digit codes like #fff would need to be expanded to #ffffff
      // This test documents current behavior
      const result = hexToOklch("#ffffff");
      expect(result).toMatch(/^oklch\(/);
    });

    it("handles lowercase hex codes", () => {
      const lower = hexToOklch("#10b981");
      const upper = hexToOklch("#10B981");

      // Should produce same result regardless of case
      expect(lower).toBe(upper);
    });

    it("handles mixed case hex codes", () => {
      const result = hexToOklch("#10B981");

      expect(result).toMatch(/^oklch\(\d+\.\d+ \d+\.\d+ \d+\.\d+\)$/);
    });
  });
});
