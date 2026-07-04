/* ─────────────────────────────────────────────────────────────
 * RTL utilities — direction, Arabic detection, number formatting.
 * ───────────────────────────────────────────────────────────── */

/**
 * Get text direction for a given language code.
 */
export function getDirection(language: string): "rtl" | "ltr" {
  return language === "ar" ? "rtl" : "ltr";
}

/**
 * Detect if text is primarily Arabic based on Unicode range.
 */
export function isArabic(text: string): boolean {
  const arabicChars = text.match(/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/g);
  if (!arabicChars) return false;
  // If > 30% of non-space chars are Arabic, treat as Arabic
  const nonSpace = text.replace(/\s/g, "");
  return arabicChars.length / nonSpace.length > 0.3;
}

/**
 * Format a number with thousands separators.
 *
 * Latin digits in BOTH languages (1,234,567): chart axes, tooltips, tables
 * and KPI cards must all read as one system — mixing ٦٣٨٫٤ next to 1.2M
 * on the same screen breaks that. Labels stay localized; digits don't.
 */
export function formatNumber(
  num: number | string | null | undefined,
  _language: string = "en",
): string {
  if (num == null) return "—";
  const value = typeof num === "string" ? parseFloat(num.replace(/,/g, "")) : num;
  if (isNaN(value)) return String(num);

  // Format with appropriate decimal places
  if (Number.isInteger(value)) {
    return value.toLocaleString("en-US");
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

/**
 * Format currency (EGP).
 */
export function formatCurrency(
  num: number | string | null | undefined,
  language: string = "en",
): string {
  if (num == null) return "—";
  const value = typeof num === "string" ? parseFloat(num) : num;
  if (isNaN(value)) return String(num);

  const formatted = formatNumber(value, language);
  return language === "ar" ? `${formatted} ج.م` : `EGP ${formatted}`;
}
