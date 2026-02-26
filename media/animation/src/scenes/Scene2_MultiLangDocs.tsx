import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { DocumentIcon } from "../components/DocumentIcon";
import { LanguageBadge } from "../components/LanguageBadge";
import { PythonSnake } from "../components/PythonSnake";
import { COLORS } from "../utils/colors";
import { FONT_UI } from "../utils/fonts";
import { SPRING_BOUNCY, SPRING_SMOOTH } from "../utils/easings";

const LANGUAGES: Array<{ lang: "ES" | "JA" | "ZH"; x: number; y: number }> = [
  { lang: "ES", x: -140, y: 50 },
  { lang: "JA", x: 0, y: 90 },
  { lang: "ZH", x: 140, y: 50 },
];

export const Scene2_MultiLangDocs: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Center doc entrance
  const docProgress = spring({
    frame,
    fps,
    config: SPRING_SMOOTH,
  });

  // Sparkle particles
  const sparkles = Array.from({ length: 8 }, (_, i) => {
    const angle = (i / 8) * Math.PI * 2;
    const radius = interpolate(frame, [10, 35], [20, 70], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    });
    const sparkleOpacity = interpolate(frame, [10, 25, 40], [0, 0.8, 0], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    });
    return {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      opacity: sparkleOpacity,
    };
  });

  // Snake peek in top-right
  const snakePeek = spring({
    frame,
    fps,
    config: SPRING_BOUNCY,
    delay: 20,
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.BG_PRIMARY,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 24,
          fontFamily: FONT_UI,
          fontSize: 16,
          fontWeight: 600,
          color: COLORS.TEXT_PRIMARY,
          opacity: interpolate(frame, [0, 10], [0, 1], {
            extrapolateRight: "clamp",
            extrapolateLeft: "clamp",
          }),
        }}
      >
        Auto-Translated Docs
      </div>

      {/* Center English document */}
      <div
        style={{
          transform: `scale(${docProgress})`,
          position: "relative",
        }}
      >
        <DocumentIcon size={60} color={COLORS.ACCENT_GREEN} />
        <div
          style={{
            position: "absolute",
            bottom: -18,
            left: "50%",
            transform: "translateX(-50%)",
            fontFamily: FONT_UI,
            fontSize: 11,
            fontWeight: 700,
            color: COLORS.ACCENT_GREEN,
          }}
        >
          EN
        </div>
      </div>

      {/* Sparkle particles */}
      {sparkles.map((s, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: 300 + s.x - 3,
            top: 200 + s.y - 3,
            width: 6,
            height: 6,
            borderRadius: "50%",
            backgroundColor: COLORS.ACCENT_YELLOW,
            opacity: s.opacity,
          }}
        />
      ))}

      {/* Translated copies pop outward */}
      {LANGUAGES.map((item, i) => {
        const delay = 15 + i * 8;
        const progress = spring({
          frame,
          fps,
          config: SPRING_BOUNCY,
          delay,
        });

        return (
          <div
            key={item.lang}
            style={{
              position: "absolute",
              left: 300 + item.x * progress - 25,
              top: 170 + item.y * progress,
              transform: `scale(${progress})`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
            }}
          >
            <DocumentIcon size={45} color={COLORS.TEXT_SECONDARY} />
            <LanguageBadge lang={item.lang} />
          </div>
        );
      })}

      {/* Snake peek top-right */}
      <div
        style={{
          position: "absolute",
          top: interpolate(snakePeek, [0, 1], [-50, 8]),
          right: 16,
          opacity: snakePeek,
        }}
      >
        <PythonSnake size={44} />
      </div>
    </AbsoluteFill>
  );
};
