import React from "react";
import { COLORS } from "../utils/colors";

type DatabaseIconProps = {
  size?: number;
  style?: React.CSSProperties;
};

export const DatabaseIcon: React.FC<DatabaseIconProps> = ({
  size = 50,
  style,
}) => {
  return (
    <svg width={size} height={size * 1.2} viewBox="0 0 50 60" style={style}>
      {/* Top ellipse */}
      <ellipse cx={25} cy={12} rx={20} ry={8} fill={COLORS.BG_SECONDARY} stroke={COLORS.ACCENT_GREEN} strokeWidth={2} />
      {/* Body */}
      <path
        d="M5 12 L5 48 C5 53, 15 58, 25 58 C35 58, 45 53, 45 48 L45 12"
        fill={COLORS.BG_SECONDARY}
        stroke={COLORS.ACCENT_GREEN}
        strokeWidth={2}
      />
      {/* Middle ring */}
      <ellipse cx={25} cy={30} rx={20} ry={8} fill="none" stroke={COLORS.ACCENT_GREEN_LIGHT} strokeWidth={1.5} opacity={0.4} />
      {/* Bottom ring */}
      <ellipse cx={25} cy={48} rx={20} ry={8} fill="none" stroke={COLORS.ACCENT_GREEN_LIGHT} strokeWidth={1.5} opacity={0.4} />
    </svg>
  );
};
