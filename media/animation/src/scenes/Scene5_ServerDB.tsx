import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ServerIcon } from "../components/ServerIcon";
import { DatabaseIcon } from "../components/DatabaseIcon";
import { COLORS } from "../utils/colors";
import { FONT_MONO, FONT_UI } from "../utils/fonts";
import { SPRING_SMOOTH, SPRING_BOUNCY } from "../utils/easings";

export const Scene5_ServerDB: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Server entrance
  const serverProgress = spring({
    frame,
    fps,
    config: SPRING_SMOOTH,
  });

  // Database entrance
  const dbProgress = spring({
    frame,
    fps,
    config: SPRING_SMOOTH,
    delay: 12,
  });

  // Connection line (dashed, animated)
  const connectionProgress = interpolate(frame, [18, 35], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Dollar signs streaming from server
  const dollars = Array.from({ length: 6 }, (_, i) => {
    const startFrame = 15 + i * 7;
    const progress = Math.max(0, frame - startFrame) / 25;
    const x = interpolate(progress, [0, 1], [200, 340], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    });
    const y = 140 + Math.sin(progress * Math.PI * 2 + i) * 15;
    const opacity = interpolate(progress, [0, 0.2, 0.8, 1], [0, 1, 1, 0], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    });
    return { x, y, opacity };
  });

  // Data packets traveling along connection
  const packets = Array.from({ length: 4 }, (_, i) => {
    const startFrame = 25 + i * 10;
    const progress = Math.max(0, frame - startFrame) / 18;
    const t = Math.min(1, progress);
    const x = interpolate(t, [0, 1], [230, 370]);
    const y = 255;
    const opacity = interpolate(t, [0, 0.1, 0.9, 1], [0, 1, 1, 0], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    });
    return { x, y, opacity };
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
        Infrastructure Ready
      </div>

      {/* Server */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 140,
          transform: `scale(${serverProgress})`,
          opacity: serverProgress,
        }}
      >
        <ServerIcon size={60} />
        <div
          style={{
            textAlign: "center",
            fontFamily: FONT_UI,
            fontSize: 11,
            color: COLORS.TEXT_SECONDARY,
            marginTop: 4,
          }}
        >
          Server
        </div>
      </div>

      {/* Database */}
      <div
        style={{
          position: "absolute",
          right: 120,
          top: 150,
          transform: `scale(${dbProgress})`,
          opacity: dbProgress,
        }}
      >
        <DatabaseIcon size={50} />
        <div
          style={{
            textAlign: "center",
            fontFamily: FONT_UI,
            fontSize: 11,
            color: COLORS.TEXT_SECONDARY,
            marginTop: 4,
          }}
        >
          Database
        </div>
      </div>

      {/* Connection line */}
      <svg
        style={{ position: "absolute", top: 0, left: 0 }}
        width={600}
        height={400}
      >
        <line
          x1={230}
          y1={255}
          x2={230 + 140 * connectionProgress}
          y2={255}
          stroke={COLORS.ACCENT_GREEN}
          strokeWidth={2}
          strokeDasharray="6 4"
          strokeDashoffset={-frame * 2}
        />
      </svg>

      {/* Dollar signs */}
      {dollars.map((d, i) => (
        <span
          key={`d-${i}`}
          style={{
            position: "absolute",
            left: d.x,
            top: d.y,
            fontFamily: FONT_MONO,
            fontSize: 18,
            fontWeight: 700,
            color: COLORS.ACCENT_GREEN,
            opacity: d.opacity,
          }}
        >
          $
        </span>
      ))}

      {/* Data packets */}
      {packets.map((p, i) => (
        <div
          key={`p-${i}`}
          style={{
            position: "absolute",
            left: p.x,
            top: p.y - 3,
            width: 6,
            height: 6,
            borderRadius: "50%",
            backgroundColor: COLORS.ACCENT_YELLOW,
            opacity: p.opacity,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
