import React from "react";
import { COLORS } from "../utils/colors";

type TerminalWindowProps = {
  children: React.ReactNode;
  width?: number;
  height?: number;
  title?: string;
};

export const TerminalWindow: React.FC<TerminalWindowProps> = ({
  children,
  width = 440,
  height = 260,
  title = "Terminal",
}) => {
  const titleBarHeight = 32;
  const dotSize = 10;
  const dotGap = 7;
  const dotY = titleBarHeight / 2;

  return (
    <div
      style={{
        width,
        height,
        borderRadius: 10,
        overflow: "hidden",
        backgroundColor: COLORS.BG_SECONDARY,
        border: `1px solid ${COLORS.BORDER}`,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          height: titleBarHeight,
          backgroundColor: COLORS.BG_PRIMARY,
          display: "flex",
          alignItems: "center",
          paddingLeft: 12,
          paddingRight: 12,
          gap: dotGap,
          flexShrink: 0,
        }}
      >
        <svg width={dotSize} height={dotSize}>
          <circle cx={dotSize / 2} cy={dotSize / 2} r={dotSize / 2} fill="#f85149" />
        </svg>
        <svg width={dotSize} height={dotSize}>
          <circle cx={dotSize / 2} cy={dotSize / 2} r={dotSize / 2} fill="#d29922" />
        </svg>
        <svg width={dotSize} height={dotSize}>
          <circle cx={dotSize / 2} cy={dotSize / 2} r={dotSize / 2} fill="#3fb950" />
        </svg>
        <span
          style={{
            flex: 1,
            textAlign: "center",
            color: COLORS.TEXT_SECONDARY,
            fontSize: 12,
            fontFamily: "Inter, sans-serif",
          }}
        >
          {title}
        </span>
      </div>
      <div
        style={{
          flex: 1,
          padding: 16,
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-start",
        }}
      >
        {children}
      </div>
    </div>
  );
};
