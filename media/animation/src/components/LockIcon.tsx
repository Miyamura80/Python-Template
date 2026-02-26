import React from "react";
import { COLORS } from "../utils/colors";

type LockIconProps = {
  size?: number;
  style?: React.CSSProperties;
};

export const LockIcon: React.FC<LockIconProps> = ({ size = 50, style }) => {
  return (
    <svg width={size} height={size} viewBox="0 0 40 50" style={style}>
      {/* Shackle */}
      <path
        d="M10 20 L10 14 C10 7, 20 0, 30 7 L30 20"
        fill="none"
        stroke={COLORS.ACCENT_YELLOW}
        strokeWidth={4}
        strokeLinecap="round"
      />
      {/* Lock body */}
      <rect
        x={5}
        y={20}
        width={30}
        height={25}
        rx={4}
        fill={COLORS.ACCENT_YELLOW}
      />
      {/* Keyhole */}
      <circle cx={20} cy={30} r={4} fill={COLORS.BG_PRIMARY} />
      <rect x={18} y={32} width={4} height={7} rx={1} fill={COLORS.BG_PRIMARY} />
    </svg>
  );
};
