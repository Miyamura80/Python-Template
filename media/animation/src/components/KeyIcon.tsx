import React from "react";
import { COLORS } from "../utils/colors";

type KeyIconProps = {
  size?: number;
  label?: string;
  style?: React.CSSProperties;
};

export const KeyIcon: React.FC<KeyIconProps> = ({
  size = 40,
  label,
  style,
}) => {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, ...style }}>
      <svg width={size} height={size * 0.5} viewBox="0 0 40 20">
        {/* Key head (circle) */}
        <circle cx={8} cy={10} r={7} fill="none" stroke={COLORS.ACCENT_YELLOW} strokeWidth={2} />
        <circle cx={8} cy={10} r={3} fill={COLORS.ACCENT_YELLOW} />
        {/* Key shaft */}
        <line x1={15} y1={10} x2={36} y2={10} stroke={COLORS.ACCENT_YELLOW} strokeWidth={2} />
        {/* Key teeth */}
        <line x1={28} y1={10} x2={28} y2={15} stroke={COLORS.ACCENT_YELLOW} strokeWidth={2} />
        <line x1={34} y1={10} x2={34} y2={14} stroke={COLORS.ACCENT_YELLOW} strokeWidth={2} />
      </svg>
      {label && (
        <span
          style={{
            fontSize: 11,
            fontFamily: "Fira Code, monospace",
            color: COLORS.ACCENT_YELLOW,
            fontWeight: 600,
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
};
