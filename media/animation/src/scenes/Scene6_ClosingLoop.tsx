import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { PythonSnake } from "../components/PythonSnake";
import { COLORS } from "../utils/colors";
import { FONT_UI } from "../utils/fonts";
import { SPRING_SMOOTH } from "../utils/easings";

const ICONS = [
  { label: "Onboard", color: COLORS.ACCENT_GREEN, emoji: ">" },
  { label: "Docs", color: COLORS.ACCENT_GREEN, emoji: "D" },
  { label: "Auth", color: COLORS.ACCENT_YELLOW, emoji: "K" },
  { label: "AI", color: COLORS.ACCENT_YELLOW_BRIGHT, emoji: "W" },
  { label: "Server", color: COLORS.ACCENT_GREEN_LIGHT, emoji: "S" },
  { label: "DB", color: COLORS.ACCENT_BLUE, emoji: "B" },
];

export const Scene6_ClosingLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Icons converge into ring
  const ringProgress = spring({
    frame,
    fps,
    config: SPRING_SMOOTH,
  });

  // Cross-fade to loop back (last ~10 frames)
  const loopFade = interpolate(frame, [15, 24], [1, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Snake scale
  const snakeScale = spring({
    frame,
    fps,
    config: { damping: 15 },
  });

  const centerX = 300;
  const centerY = 200;
  const ringRadius = 90;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.BG_PRIMARY,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ opacity: loopFade }}>
        {/* Center snake */}
        <div
          style={{
            position: "absolute",
            left: centerX - 32,
            top: centerY - 32,
            transform: `scale(${snakeScale})`,
          }}
        >
          <PythonSnake size={64} />
        </div>

        {/* Feature icons in a ring */}
        {ICONS.map((icon, i) => {
          const angle = (i / ICONS.length) * Math.PI * 2 - Math.PI / 2;
          const startX = centerX + Math.cos(angle) * 200;
          const startY = centerY + Math.sin(angle) * 200;
          const endX = centerX + Math.cos(angle) * ringRadius;
          const endY = centerY + Math.sin(angle) * ringRadius;

          const x = interpolate(ringProgress, [0, 1], [startX, endX]);
          const y = interpolate(ringProgress, [0, 1], [startY, endY]);

          // Slow rotation of the ring
          const rotationAngle = frame * 0.8;
          const rotatedAngle = angle + (rotationAngle * Math.PI) / 180;
          const finalX =
            centerX +
            Math.cos(rotatedAngle) *
              ringRadius *
              ringProgress;
          const finalY =
            centerY +
            Math.sin(rotatedAngle) *
              ringRadius *
              ringProgress;

          const displayX = ringProgress < 0.95 ? x : finalX;
          const displayY = ringProgress < 0.95 ? y : finalY;

          return (
            <div
              key={icon.label}
              style={{
                position: "absolute",
                left: displayX - 20,
                top: displayY - 20,
                width: 40,
                height: 40,
                borderRadius: "50%",
                backgroundColor: COLORS.BG_SECONDARY,
                border: `2px solid ${icon.color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: ringProgress,
              }}
            >
              <span
                style={{
                  fontFamily: FONT_UI,
                  fontSize: 14,
                  fontWeight: 700,
                  color: icon.color,
                }}
              >
                {icon.emoji}
              </span>
            </div>
          );
        })}

        {/* Project name */}
        <div
          style={{
            position: "absolute",
            bottom: 40,
            left: 0,
            right: 0,
            textAlign: "center",
            fontFamily: FONT_UI,
            fontSize: 18,
            fontWeight: 700,
            color: COLORS.TEXT_PRIMARY,
            opacity: interpolate(ringProgress, [0.5, 1], [0, 1], {
              extrapolateRight: "clamp",
              extrapolateLeft: "clamp",
            }),
          }}
        >
          Python-Template
        </div>
      </div>
    </AbsoluteFill>
  );
};
