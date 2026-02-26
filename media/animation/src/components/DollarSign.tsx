import React from "react";
import { COLORS } from "../utils/colors";
import { FONT_MONO } from "../utils/fonts";

type DollarSignProps = {
  opacity?: number;
  style?: React.CSSProperties;
};

export const DollarSign: React.FC<DollarSignProps> = ({
  opacity = 1,
  style,
}) => {
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 22,
        fontWeight: 700,
        color: COLORS.ACCENT_GREEN,
        opacity,
        ...style,
      }}
    >
      $
    </span>
  );
};
