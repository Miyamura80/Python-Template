import React from "react";
import { COLORS } from "../utils/colors";

type DocumentIconProps = {
  size?: number;
  color?: string;
  style?: React.CSSProperties;
};

export const DocumentIcon: React.FC<DocumentIconProps> = ({
  size = 50,
  color = COLORS.ACCENT_GREEN,
  style,
}) => {
  return (
    <svg width={size} height={size} viewBox="0 0 50 60" style={style}>
      {/* Page body */}
      <path
        d="M5 5 L35 5 L45 15 L45 55 L5 55 Z"
        fill={COLORS.BG_SECONDARY}
        stroke={color}
        strokeWidth={2}
      />
      {/* Corner fold */}
      <path d="M35 5 L35 15 L45 15" fill={color} opacity={0.3} />
      <path
        d="M35 5 L35 15 L45 15"
        fill="none"
        stroke={color}
        strokeWidth={2}
      />
      {/* Text lines */}
      <line x1={12} y1={25} x2={38} y2={25} stroke={color} strokeWidth={2} opacity={0.5} />
      <line x1={12} y1={33} x2={34} y2={33} stroke={color} strokeWidth={2} opacity={0.5} />
      <line x1={12} y1={41} x2={30} y2={41} stroke={color} strokeWidth={2} opacity={0.5} />
    </svg>
  );
};
