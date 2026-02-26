import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS } from "../utils/colors";
import { FONT_MONO, FONT_UI } from "../utils/fonts";
import { SPRING_SMOOTH } from "../utils/easings";

const BANNER_TEXT = "Python-Template";

const CODE_FRAGMENTS = [
  "{", "}", "def", ">>>", "import", "class", "lambda", "async",
  "await", "yield", "self", "->", "**", "[]", "()", "for",
  "if", "try", "with", "pass",
];

// Deterministic scatter positions for each particle
const PARTICLE_POSITIONS = CODE_FRAGMENTS.map((_, i) => ({
  startX: ((i * 137 + 50) % 480) + 60,
  startY: ((i * 97 + 30) % 280) + 60,
}));

// Star sparkle positions along banner border
const STAR_POSITIONS = [
  { x: 70, y: 155 }, { x: 180, y: 140 }, { x: 310, y: 140 },
  { x: 430, y: 155 }, { x: 440, y: 220 }, { x: 330, y: 270 },
  { x: 190, y: 270 }, { x: 70, y: 240 },
];

const FourPointStar: React.FC<{ x: number; y: number; size: number; opacity: number }> = ({
  x, y, size, opacity,
}) => (
  <svg
    style={{ position: "absolute", left: x - size, top: y - size, opacity }}
    width={size * 2}
    height={size * 2}
    viewBox="0 0 20 20"
  >
    <path
      d="M10 0 L12 8 L20 10 L12 12 L10 20 L8 12 L0 10 L8 8 Z"
      fill={COLORS.ACCENT_YELLOW_BRIGHT}
    />
  </svg>
);

export const Scene4_BannerGeneration: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title fade in (frames 0-10)
  const titleOpacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Banner scale (frames 15-35)
  const bannerScale = spring({
    frame: Math.max(0, frame - 15),
    fps,
    config: SPRING_SMOOTH,
  });

  // Gradient angle animation
  const gradientAngle = interpolate(frame, [15, 59], [90, 190], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Banner glow pulse
  const glowIntensity = interpolate(
    Math.sin(frame * 0.15),
    [-1, 1],
    [8, 20],
  );

  // Typewriter effect (frames 22-45)
  const typingStart = 22;
  const charsVisible = Math.min(
    Math.max(0, Math.floor((frame - typingStart) / 1.5)),
    BANNER_TEXT.length,
  );
  const typedTitle = BANNER_TEXT.slice(0, charsVisible);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.BG_PRIMARY,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Section title */}
      <div
        style={{
          position: "absolute",
          top: 30,
          fontFamily: FONT_UI,
          fontSize: 16,
          fontWeight: 600,
          color: COLORS.TEXT_PRIMARY,
          opacity: titleOpacity,
        }}
      >
        AI Banner Generation
      </div>

      {/* Code fragment particles */}
      {CODE_FRAGMENTS.map((frag, i) => {
        const pos = PARTICLE_POSITIONS[i];
        const centerX = 300;
        const centerY = 200;

        // Particle appearance (frames 0-10)
        const appearOpacity = interpolate(frame, [i * 0.5, i * 0.5 + 8], [0, 1], {
          extrapolateRight: "clamp",
          extrapolateLeft: "clamp",
        });

        // Convergence (frames 8-30, staggered per particle)
        const convergeStart = 8 + i * 0.8;
        const convergeProgress = spring({
          frame: Math.max(0, frame - convergeStart),
          fps,
          config: { damping: 20, stiffness: 80 },
        });

        const currentX = interpolate(convergeProgress, [0, 1], [pos.startX, centerX]);
        const currentY = interpolate(convergeProgress, [0, 1], [pos.startY, centerY]);

        // Color transition: grey fades out, green fades in
        const greyOpacity = interpolate(convergeProgress, [0, 0.6], [1, 0], {
          extrapolateRight: "clamp",
          extrapolateLeft: "clamp",
        });
        const greenOpacity = interpolate(convergeProgress, [0.3, 0.8], [0, 1], {
          extrapolateRight: "clamp",
          extrapolateLeft: "clamp",
        });

        // Fade out as they reach center
        const fadeOut = interpolate(convergeProgress, [0.7, 1], [1, 0], {
          extrapolateRight: "clamp",
          extrapolateLeft: "clamp",
        });

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: currentX,
              top: currentY,
              opacity: appearOpacity * fadeOut,
              fontFamily: FONT_MONO,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            <span style={{ color: COLORS.TEXT_SECONDARY, opacity: greyOpacity, position: "absolute" }}>
              {frag}
            </span>
            <span style={{ color: COLORS.ACCENT_GREEN, opacity: greenOpacity }}>
              {frag}
            </span>
          </div>
        );
      })}

      {/* Banner rectangle with gradient */}
      <div
        style={{
          width: 440,
          height: 120,
          borderRadius: 12,
          overflow: "hidden",
          position: "relative",
          transform: `scale(${bannerScale})`,
          boxShadow: `0 0 ${glowIntensity}px ${glowIntensity / 2}px ${COLORS.ACCENT_GREEN}40`,
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            background: `linear-gradient(${gradientAngle}deg, ${COLORS.ACCENT_GREEN}, ${COLORS.ACCENT_YELLOW}, ${COLORS.ACCENT_GREEN})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              fontFamily: FONT_MONO,
              fontSize: 28,
              fontWeight: 700,
              color: COLORS.TEXT_PRIMARY,
              textShadow: `0 0 12px ${COLORS.ACCENT_GREEN}80, 0 2px 8px rgba(0,0,0,0.4)`,
            }}
          >
            {typedTitle}
            {frame >= typingStart && frame % 8 < 5 && (
              <span style={{ opacity: 0.7 }}>|</span>
            )}
          </span>
        </div>
      </div>

      {/* Star sparkles along banner border */}
      {STAR_POSITIONS.map((star, i) => {
        const sparkleStart = 32 + i * 3;
        const sparkleOpacity = interpolate(
          frame,
          [sparkleStart, sparkleStart + 4, sparkleStart + 12, sparkleStart + 20],
          [0, 1, 0.6, 0],
          { extrapolateRight: "clamp", extrapolateLeft: "clamp" },
        );
        const sparkleSize = 6 + Math.sin(frame * 0.3 + i * 2) * 2;

        return (
          <FourPointStar
            key={i}
            x={star.x}
            y={star.y}
            size={sparkleSize}
            opacity={sparkleOpacity}
          />
        );
      })}
    </AbsoluteFill>
  );
};
