import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TerminalWindow } from "../components/TerminalWindow";
import { PythonSnake } from "../components/PythonSnake";
import { COLORS } from "../utils/colors";
import { FONT_MONO, FONT_UI } from "../utils/fonts";
import { SPRING_SMOOTH, SPRING_BOUNCY } from "../utils/easings";

const COMMAND = "$ make onboard";

const FEATURES = [
  { label: "Rename", angle: -60 },
  { label: "Deps", angle: -20 },
  { label: "Env", angle: 20 },
  { label: "Hooks", angle: 60 },
  { label: "Media", angle: 100 },
  { label: "Jules", angle: 140 },
];

export const Scene1_SnakeOnboard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Terminal fade in
  const terminalOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Snake entrance from left
  const snakeProgress = spring({
    frame,
    fps,
    config: SPRING_BOUNCY,
    delay: 8,
  });
  const snakeX = interpolate(snakeProgress, [0, 1], [-80, 0]);

  // Typing animation - start at frame 18, type one char every 2 frames
  const typingStart = 18;
  const charsVisible = Math.min(
    Math.max(0, Math.floor((frame - typingStart) / 2)),
    COMMAND.length
  );
  const typedText = COMMAND.slice(0, charsVisible);
  const showCursor = frame >= typingStart && frame % 8 < 5;

  // Feature labels appear after typing finishes
  const typingEnd = typingStart + COMMAND.length * 2;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.BG_PRIMARY,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          opacity: terminalOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
        }}
      >
        {/* Snake + Terminal row */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ transform: `translateX(${snakeX}px)` }}>
            <PythonSnake size={64} />
          </div>
          <TerminalWindow width={380} height={140} title="onboard">
            <div
              style={{
                fontFamily: FONT_MONO,
                fontSize: 15,
                color: COLORS.ACCENT_GREEN,
              }}
            >
              {typedText}
              {showCursor && (
                <span style={{ color: COLORS.TEXT_PRIMARY }}>|</span>
              )}
            </div>
          </TerminalWindow>
        </div>

        {/* Feature labels branching out */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: 8,
            maxWidth: 460,
          }}
        >
          {FEATURES.map((feat, i) => {
            const delay = typingEnd + i * 4;
            const labelProgress = spring({
              frame,
              fps,
              config: SPRING_BOUNCY,
              delay,
            });
            const scale = labelProgress;
            const opacity = labelProgress;

            return (
              <div
                key={feat.label}
                style={{
                  transform: `scale(${scale})`,
                  opacity,
                  backgroundColor: COLORS.BG_SECONDARY,
                  border: `1px solid ${COLORS.ACCENT_GREEN}`,
                  borderRadius: 6,
                  padding: "4px 12px",
                  fontFamily: FONT_UI,
                  fontSize: 13,
                  fontWeight: 600,
                  color: COLORS.ACCENT_GREEN,
                }}
              >
                {feat.label}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
