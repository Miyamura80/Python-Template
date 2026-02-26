import React from "react";
import { COLORS } from "../utils/colors";

type VultureBirdProps = {
  size?: number;
  style?: React.CSSProperties;
};

export const VultureBird: React.FC<VultureBirdProps> = ({
  size = 60,
  style,
}) => {
  return (
    <svg width={size} height={size} viewBox="0 0 60 60" style={style}>
      {/* Body */}
      <ellipse cx={30} cy={38} rx={14} ry={12} fill={COLORS.TEXT_SECONDARY} />
      {/* Head */}
      <circle cx={42} cy={22} r={8} fill={COLORS.ACCENT_RED} opacity={0.8} />
      {/* Neck */}
      <path
        d="M36 30 Q40 26, 42 22"
        fill="none"
        stroke={COLORS.TEXT_SECONDARY}
        strokeWidth={5}
      />
      {/* Beak */}
      <path
        d="M48 20 L56 23 L48 25"
        fill={COLORS.ACCENT_YELLOW}
      />
      {/* Eye */}
      <circle cx={44} cy={20} r={2} fill={COLORS.BG_PRIMARY} />
      <circle cx={44.5} cy={20} r={1} fill={COLORS.TEXT_PRIMARY} />
      {/* Wing */}
      <path
        d="M20 32 Q12 20, 8 28 Q14 26, 20 36"
        fill={COLORS.TEXT_SECONDARY}
        opacity={0.7}
      />
      {/* Tail feathers */}
      <path
        d="M16 42 L8 48 M18 44 L12 52"
        fill="none"
        stroke={COLORS.TEXT_SECONDARY}
        strokeWidth={2}
        strokeLinecap="round"
      />
    </svg>
  );
};
