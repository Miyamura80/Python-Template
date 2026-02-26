import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { LockIcon } from "../components/LockIcon";
import { KeyIcon } from "../components/KeyIcon";
import { VultureBird } from "../components/VultureBird";
import { CodeLine } from "../components/CodeLine";
import { COLORS } from "../utils/colors";
import { FONT_UI } from "../utils/fonts";
import { SPRING_SMOOTH, SPRING_BOUNCY } from "../utils/easings";

const API_KEYS = ["OPENAI", "GEMINI", "STRIPE"];
const DEAD_CODE = [
  "def old_handler():",
  "  return legacy_call()",
  "  # deprecated v1",
];

export const Scene3_AuthVulture: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Lock drop in
  const lockProgress = spring({
    frame,
    fps,
    config: SPRING_BOUNCY,
  });
  const lockY = interpolate(lockProgress, [0, 1], [-60, 0]);

  // Vulture swoop from top-right
  const vultureDelay = 30;
  const vultureProgress = spring({
    frame,
    fps,
    config: SPRING_SMOOTH,
    delay: vultureDelay,
  });
  const vultureX = interpolate(vultureProgress, [0, 1], [80, 0]);
  const vultureY = interpolate(vultureProgress, [0, 1], [-60, 0]);

  // Vulture pecking animation
  const peckFrame = Math.max(0, frame - vultureDelay - 20);
  const peckRotation = Math.sin(peckFrame * 0.5) * 8;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.BG_PRIMARY,
        flexDirection: "row",
      }}
    >
      {/* Left side - Auth */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          borderRight: `1px solid ${COLORS.BORDER}`,
          padding: 20,
        }}
      >
        <div
          style={{
            fontFamily: FONT_UI,
            fontSize: 14,
            fontWeight: 600,
            color: COLORS.TEXT_PRIMARY,
            marginBottom: 16,
            opacity: interpolate(frame, [0, 10], [0, 1], {
              extrapolateRight: "clamp",
              extrapolateLeft: "clamp",
            }),
          }}
        >
          .env Secrets
        </div>

        <div style={{ transform: `translateY(${lockY}px)` }}>
          <LockIcon size={40} />
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
            marginTop: 16,
          }}
        >
          {API_KEYS.map((key, i) => {
            const keyProgress = spring({
              frame,
              fps,
              config: SPRING_BOUNCY,
              delay: 12 + i * 6,
            });
            return (
              <div
                key={key}
                style={{
                  transform: `scale(${keyProgress})`,
                  opacity: keyProgress,
                }}
              >
                <KeyIcon size={32} label={key} />
              </div>
            );
          })}
        </div>
      </div>

      {/* Right side - Dead code + Vulture */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: 20,
          position: "relative",
        }}
      >
        <div
          style={{
            fontFamily: FONT_UI,
            fontSize: 14,
            fontWeight: 600,
            color: COLORS.TEXT_PRIMARY,
            marginBottom: 16,
            opacity: interpolate(frame, [0, 10], [0, 1], {
              extrapolateRight: "clamp",
              extrapolateLeft: "clamp",
            }),
          }}
        >
          Dead Code Cleanup
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            marginBottom: 12,
          }}
        >
          {DEAD_CODE.map((line, i) => {
            const lineDelay = 10 + i * 6;
            const lineOpacity = interpolate(
              frame,
              [lineDelay, lineDelay + 8],
              [0, 1],
              { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
            );

            const strikeDelay = vultureDelay + 15 + i * 8;
            const strikeProgress = interpolate(
              frame,
              [strikeDelay, strikeDelay + 10],
              [0, 1],
              { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
            );

            const fadeOut = strikeProgress > 0.8 ? 0.3 : 1;

            return (
              <CodeLine
                key={i}
                text={line}
                strikethrough={strikeProgress}
                opacity={lineOpacity * fadeOut}
              />
            );
          })}
        </div>

        {/* Vulture */}
        <div
          style={{
            transform: `translate(${vultureX}px, ${vultureY}px) rotate(${peckRotation}deg)`,
            opacity: vultureProgress,
          }}
        >
          <VultureBird size={50} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
