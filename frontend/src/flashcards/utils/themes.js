/**
 * Shared per-character color themes, light + dark variants.
 * Single source of truth — screens should import getTheme() rather than
 * defining their own local THEMES objects (which had drifted out of sync
 * across files before this).
 */

export const LIGHT_THEMES = {
  BOLT:  { bg: "#EEF4FB", bgGradient: "linear-gradient(160deg, #EAF2FC 0%, #D2E4F7 55%, #BFD8F2 100%)", card: "#DDEAF7", text: "#1A3A5C", sub: "#4A7AA5", accent: "#5B9BD5" },
  ZARA:  { bg: "#F5EEFB", bgGradient: "linear-gradient(160deg, #F7EEFC 0%, #E9D3F5 55%, #DCC0F0 100%)", card: "#EDD8F7", text: "#3A1A5C", sub: "#7A4AA5", accent: "#B57ED5" },
  NOVA:  { bg: "#EEF7EF", bgGradient: "linear-gradient(160deg, #EEFAF0 0%, #D0EDD8 55%, #B9E4C4 100%)", card: "#D5EDDA", text: "#1A3A1C", sub: "#3A7A4A", accent: "#6BBF7A" },
  BEEP:  { bg: "#FDF6E8", bgGradient: "linear-gradient(160deg, #FEF9EC 0%, #FBE8B6 55%, #F7DA8C 100%)", card: "#FAE8B8", text: "#3A2A00", sub: "#7A5A10", accent: "#E8B84B" },
  ECHO:  { bg: "#FBF0EC", bgGradient: "linear-gradient(160deg, #FDF1EC 0%, #F6D2C0 55%, #F0B79D 100%)", card: "#F5D5C8", text: "#3A1200", sub: "#8A3A20", accent: "#E87B5A" },
  MIRA:  { bg: "#EAF7F7", bgGradient: "linear-gradient(160deg, #ECFAFA 0%, #C4EDED 55%, #A3E1E1 100%)", card: "#C8EAEA", text: "#003A3A", sub: "#1A6A6A", accent: "#4ABFBF" },
  DEFAULT: { bg: "#FDF6F0", bgGradient: "linear-gradient(160deg, #FDEDEA 0%, #FDF3DD 30%, #FBFAE0 55%, #E9F6EA 75%, #E2F5F2 100%)", card: "#FCF7F0", text: "#3A2E2C", sub: "#9A7A6A", accent: "#E8825A" },
};

export const DARK_THEMES = {
  BOLT:  { bg: "#0F1A24", bgGradient: "linear-gradient(160deg, #0F1A24 0%, #142433 55%, #1A2C3D 100%)", card: "#1A2C3D", text: "#BFE0FF", sub: "#7FAEDB", accent: "#5B9BD5" },
  ZARA:  { bg: "#1C1424", bgGradient: "linear-gradient(160deg, #1C1424 0%, #251A31 55%, #2E1F3D 100%)", card: "#2E1F3D", text: "#EBD4FF", sub: "#C09CE8", accent: "#C293E0" },
  NOVA:  { bg: "#10190F", bgGradient: "linear-gradient(160deg, #10190F 0%, #172415 55%, #1D2E1B 100%)", card: "#1D2E1B", text: "#C9F0CC", sub: "#8ECB94", accent: "#6BBF7A" },
  BEEP:  { bg: "#211B08", bgGradient: "linear-gradient(160deg, #211B08 0%, #2E250C 55%, #3A2E0F 100%)", card: "#3A2E0F", text: "#FDE9A8", sub: "#D9B85C", accent: "#E8B84B" },
  ECHO:  { bg: "#20120A", bgGradient: "linear-gradient(160deg, #20120A 0%, #2E190E 55%, #3A1F12 100%)", card: "#3A1F12", text: "#FBD3BE", sub: "#E29A73", accent: "#E87B5A" },
  MIRA:  { bg: "#0A1B1B", bgGradient: "linear-gradient(160deg, #0A1B1B 0%, #0F2323 55%, #122B2B 100%)", card: "#122B2B", text: "#BFEFEF", sub: "#6FC7C7", accent: "#4ABFBF" },
  DEFAULT: { bg: "#1A1512", bgGradient: "linear-gradient(160deg, #2A1418 0%, #2A2014 30%, #262A14 55%, #14261E 75%, #14232A 100%)", card: "#241D19", text: "#F0DCCF", sub: "#B08F7A", accent: "#E8825A" },
};

export function getTheme(character, darkMode) {
  const palette = darkMode ? DARK_THEMES : LIGHT_THEMES;
  const key = (character || "DEFAULT").toUpperCase();
  return palette[key] || palette.DEFAULT;
}

/**
 * Generic translucent card/surface background, independent of character
 * accent color — for the many "rgba(255,255,255,X)" card backgrounds used
 * across screens that need a dark equivalent rather than white.
 */
export function getSurface(darkMode, opacity = 0.9) {
  return darkMode ? `rgba(30,24,20,${opacity})` : `rgba(255,255,255,${opacity})`;
}

export const DARK_MODE_STORAGE_KEY = "vaaksiddhi_dark_mode";

export function getStoredDarkMode() {
  try {
    return localStorage.getItem(DARK_MODE_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function setStoredDarkMode(value) {
  try {
    localStorage.setItem(DARK_MODE_STORAGE_KEY, value ? "true" : "false");
  } catch {
    // ignore storage errors (e.g. private browsing)
  }
}
