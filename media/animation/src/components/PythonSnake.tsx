import React from "react";
import { COLORS } from "../utils/colors";

type PythonSnakeProps = {
  size?: number;
  style?: React.CSSProperties;
};

export const PythonSnake: React.FC<PythonSnakeProps> = ({
  size = 80,
  style,
}) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      style={style}
    >
      {/* Shadow layer for depth */}
      <path
        d="M50 15 C70 15, 82 30, 76 46 C70 62, 54 56, 50 66 C46 76, 30 82, 24 71 C18 60, 30 50, 40 50 C50 50, 56 44, 50 34 C44 24, 34 24, 34 34"
        fill="none"
        stroke={COLORS.BG_PRIMARY}
        strokeWidth={14}
        strokeLinecap="round"
        opacity={0.3}
      />
      {/* Body coil */}
      <path
        d="M50 15 C70 15, 82 30, 76 46 C70 62, 54 56, 50 66 C46 76, 30 82, 24 71 C18 60, 30 50, 40 50 C50 50, 56 44, 50 34 C44 24, 34 24, 34 34"
        fill="none"
        stroke={COLORS.ACCENT_GREEN}
        strokeWidth={10}
        strokeLinecap="round"
      />
      {/* Belly highlight */}
      <path
        d="M50 15 C70 15, 82 30, 76 46 C70 62, 54 56, 50 66 C46 76, 30 82, 24 71 C18 60, 30 50, 40 50 C50 50, 56 44, 50 34 C44 24, 34 24, 34 34"
        fill="none"
        stroke={COLORS.ACCENT_GREEN_LIGHT}
        strokeWidth={4}
        strokeLinecap="round"
        opacity={0.6}
      />
      {/* Tail taper */}
      <line
        x1={34}
        y1={34}
        x2={31}
        y2={40}
        stroke={COLORS.ACCENT_GREEN}
        strokeWidth={3}
        strokeLinecap="round"
      />
      {/* Scale dots */}
      <circle cx={72} cy={35} r={1.5} fill={COLORS.ACCENT_YELLOW} opacity={0.3} />
      <circle cx={50} cy={60} r={1.5} fill={COLORS.ACCENT_YELLOW} opacity={0.3} />
      <circle cx={30} cy={64} r={1.5} fill={COLORS.ACCENT_YELLOW} opacity={0.3} />
      {/* Head - ellipse for snout shape */}
      <ellipse cx={50} cy={15} rx={11} ry={9} fill={COLORS.ACCENT_GREEN} />
      {/* Head sheen */}
      <ellipse cx={49} cy={13} rx={7} ry={5} fill={COLORS.ACCENT_GREEN_LIGHT} opacity={0.4} />
      {/* Eyes */}
      <circle cx={45} cy={13} r={3} fill={COLORS.TEXT_PRIMARY} />
      <circle cx={55} cy={13} r={3} fill={COLORS.TEXT_PRIMARY} />
      <circle cx={45.8} cy={13.5} r={1.2} fill={COLORS.BG_PRIMARY} />
      <circle cx={55.8} cy={13.5} r={1.2} fill={COLORS.BG_PRIMARY} />
      {/* Eye shine highlights */}
      <circle cx={44} cy={12} r={0.8} fill="white" />
      <circle cx={54} cy={12} r={0.8} fill="white" />
      {/* Tongue */}
      <path
        d="M50 24 L50 30 L47 34 M50 30 L53 34"
        fill="none"
        stroke={COLORS.ACCENT_RED}
        strokeWidth={1.5}
        strokeLinecap="round"
      />
    </svg>
  );
};
