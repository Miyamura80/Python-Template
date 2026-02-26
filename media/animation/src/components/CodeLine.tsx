import React from "react";
import { COLORS } from "../utils/colors";
import { FONT_MONO } from "../utils/fonts";

type CodeLineProps = {
  text: string;
  strikethrough?: number;
  opacity?: number;
  style?: React.CSSProperties;
};

export const CodeLine: React.FC<CodeLineProps> = ({
  text,
  strikethrough = 0,
  opacity = 1,
  style,
}) => {
  return (
    <div
      style={{
        fontFamily: FONT_MONO,
        fontSize: 13,
        color: COLORS.TEXT_PRIMARY,
        opacity,
        position: "relative",
        display: "inline-block",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {text}
      {strikethrough > 0 && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: "50%",
            height: 2,
            width: `${strikethrough * 100}%`,
            backgroundColor: COLORS.ACCENT_RED,
            transform: "translateY(-50%)",
          }}
        />
      )}
    </div>
  );
};
