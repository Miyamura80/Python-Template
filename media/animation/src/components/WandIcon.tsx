import React from "react";
import { COLORS } from "../utils/colors";

type WandIconProps = {
  size?: number;
  style?: React.CSSProperties;
};

export const WandIcon: React.FC<WandIconProps> = ({ size = 50, style }) => {
  return (
    <svg width={size} height={size} viewBox="0 0 50 50" style={style}>
      {/* Wand body */}
      <line
        x1={10}
        y1={40}
        x2={38}
        y2={12}
        stroke={COLORS.ACCENT_GREEN}
        strokeWidth={3}
        strokeLinecap="round"
      />
      {/* Wand tip */}
      <circle cx={38} cy={12} r={3} fill={COLORS.ACCENT_YELLOW} />
      {/* Sparkles */}
      <path
        d="M42 5 L43 8 L46 9 L43 10 L42 13 L41 10 L38 9 L41 8 Z"
        fill={COLORS.ACCENT_YELLOW}
      />
      <path
        d="M48 15 L48.5 17 L50.5 17.5 L48.5 18 L48 20 L47.5 18 L45.5 17.5 L47.5 17 Z"
        fill={COLORS.ACCENT_YELLOW}
        opacity={0.7}
      />
      <path
        d="M35 3 L35.5 5 L37.5 5.5 L35.5 6 L35 8 L34.5 6 L32.5 5.5 L34.5 5 Z"
        fill={COLORS.ACCENT_YELLOW}
        opacity={0.5}
      />
    </svg>
  );
};
