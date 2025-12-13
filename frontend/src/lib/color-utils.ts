/**
 * Color conversion utilities for dynamic theming.
 * Converts hex colors to OKLCh color space for CSS variables.
 */

/**
 * Convert hex color to RGB values.
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const cleaned = hex.replace("#", "");
  const r = parseInt(cleaned.slice(0, 2), 16) / 255;
  const g = parseInt(cleaned.slice(2, 4), 16) / 255;
  const b = parseInt(cleaned.slice(4, 6), 16) / 255;
  return { r, g, b };
}

/**
 * Convert linear RGB to OKLab.
 */
function linearRgbToOklab(r: number, g: number, b: number): { L: number; a: number; b: number } {
  // Convert sRGB to linear RGB
  const toLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  const lr = toLinear(r);
  const lg = toLinear(g);
  const lb = toLinear(b);

  // Convert to OKLab
  const l_ = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
  const m_ = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
  const s_ = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);

  return {
    L: 0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
    a: 1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
    b: 0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
  };
}

/**
 * Convert OKLab to OKLCh.
 */
function oklabToOklch(L: number, a: number, b: number): { L: number; C: number; h: number } {
  const C = Math.sqrt(a * a + b * b);
  let h = (Math.atan2(b, a) * 180) / Math.PI;
  if (h < 0) h += 360;
  return { L, C, h };
}

/**
 * Convert hex color to OKLCh CSS value.
 * @param hex - Hex color string (e.g., "#10b981")
 * @returns OKLCh CSS value (e.g., "oklch(0.696 0.17 162.48)")
 */
export function hexToOklch(hex: string): string {
  const { r, g, b } = hexToRgb(hex);
  const lab = linearRgbToOklab(r, g, b);
  const lch = oklabToOklch(lab.L, lab.a, lab.b);

  // Format to 3 decimal places
  const L = lch.L.toFixed(3);
  const C = lch.C.toFixed(3);
  const h = lch.h.toFixed(3);

  return `oklch(${L} ${C} ${h})`;
}

/**
 * Generate a lighter/darker variant of a color.
 * @param hex - Base hex color
 * @param lightnessOffset - Amount to adjust lightness (-1 to 1)
 */
export function adjustLightness(hex: string, lightnessOffset: number): string {
  const { r, g, b } = hexToRgb(hex);
  const lab = linearRgbToOklab(r, g, b);
  const lch = oklabToOklch(lab.L, lab.a, lab.b);

  // Adjust lightness, clamping to valid range
  const newL = Math.max(0, Math.min(1, lch.L + lightnessOffset));

  return `oklch(${newL.toFixed(3)} ${lch.C.toFixed(3)} ${lch.h.toFixed(3)})`;
}

/**
 * Generate primary color foreground (text color for buttons).
 * Returns white or black depending on primary color brightness.
 */
export function getPrimaryForeground(hex: string): string {
  const { r, g, b } = hexToRgb(hex);
  // Use relative luminance formula
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  // Return white for dark colors, dark for light colors
  return luminance < 0.5 ? "oklch(0.98 0 0)" : "oklch(0.15 0 0)";
}
