import React from "react";
import { COLORS } from "../utils/colors";
import { FONT_UI } from "../utils/fonts";

type LanguageBadgeProps = {
  lang: "ES" | "JA" | "ZH";
  style?: React.CSSProperties;
};

const FLAG_EMOJI: Record<string, string> = {
  ES: "\u{1F1EA}\u{1F1F8}",
  JA: "\u{1F1EF}\u{1F1F5}",
  ZH: "\u{1F1E8}\u{1F1F3}",
};

export const LanguageBadge: React.FC<LanguageBadgeProps> = ({
  lang,
  style,
}) => {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 4,
        backgroundColor: COLORS.BG_SECONDARY,
        border: `1px solid ${COLORS.ACCENT_GREEN}`,
        color: COLORS.TEXT_PRIMARY,
        fontFamily: FONT_UI,
        fontWeight: 700,
        fontSize: 12,
        padding: "3px 8px",
        borderRadius: 4,
        letterSpacing: 1,
        ...style,
      }}
    >
      <span style={{ fontSize: 14, lineHeight: 1 }}>{FLAG_EMOJI[lang]}</span>
      {lang}
    </div>
  );
};
