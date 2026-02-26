import { loadFont as loadFiraCode } from "@remotion/google-fonts/FiraCode";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

const firaCode = loadFiraCode("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

const inter = loadInter("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
});

export const FONT_MONO = firaCode.fontFamily;
export const FONT_UI = inter.fontFamily;
