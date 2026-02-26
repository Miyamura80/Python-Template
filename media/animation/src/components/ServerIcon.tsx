import React from "react";
import { COLORS } from "../utils/colors";

type ServerIconProps = {
  size?: number;
  style?: React.CSSProperties;
};

export const ServerIcon: React.FC<ServerIconProps> = ({
  size = 60,
  style,
}) => {
  const w = size;
  const h = size * 1.2;

  return (
    <svg width={w} height={h} viewBox="0 0 50 60" style={style}>
      {/* Rack body */}
      <rect x={5} y={5} width={40} height={50} rx={4} fill={COLORS.BG_SECONDARY} stroke={COLORS.ACCENT_GREEN} strokeWidth={2} />
      {/* Slot 1 */}
      <rect x={10} y={10} width={30} height={12} rx={2} fill={COLORS.BG_PRIMARY} />
      <circle cx={15} cy={16} r={2} fill={COLORS.ACCENT_GREEN} />
      <line x1={22} y1={16} x2={36} y2={16} stroke={COLORS.BORDER} strokeWidth={2} />
      {/* Slot 2 */}
      <rect x={10} y={26} width={30} height={12} rx={2} fill={COLORS.BG_PRIMARY} />
      <circle cx={15} cy={32} r={2} fill={COLORS.ACCENT_YELLOW} />
      <line x1={22} y1={32} x2={36} y2={32} stroke={COLORS.BORDER} strokeWidth={2} />
      {/* Slot 3 */}
      <rect x={10} y={42} width={30} height={10} rx={2} fill={COLORS.BG_PRIMARY} />
      <circle cx={15} cy={47} r={2} fill={COLORS.ACCENT_GREEN} />
      <line x1={22} y1={47} x2={36} y2={47} stroke={COLORS.BORDER} strokeWidth={2} />
    </svg>
  );
};
