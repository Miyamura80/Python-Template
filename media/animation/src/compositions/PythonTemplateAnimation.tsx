import React from "react";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { Scene1_SnakeOnboard } from "../scenes/Scene1_SnakeOnboard";
import { Scene2_MultiLangDocs } from "../scenes/Scene2_MultiLangDocs";
import { Scene3_AuthVulture } from "../scenes/Scene3_AuthVulture";
import { Scene4_BannerGeneration } from "../scenes/Scene4_BannerGeneration";
import { Scene5_ServerDB } from "../scenes/Scene5_ServerDB";
import { Scene6_ClosingLoop } from "../scenes/Scene6_ClosingLoop";

// Scene durations and transition overlap
// With 5 transitions of 15 frames each, total = sum(durations) - 5*15
// We want 300 frames total.
// 75 + 65 + 85 + 60 + 60 + 30 = 375
// 375 - 5*15 = 375 - 75 = 300 frames total

const TRANSITION_DURATION = 15;

export const PythonTemplateAnimation: React.FC = () => {
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={75}>
        <Scene1_SnakeOnboard />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_DURATION })}
      />

      <TransitionSeries.Sequence durationInFrames={65}>
        <Scene2_MultiLangDocs />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_DURATION })}
      />

      <TransitionSeries.Sequence durationInFrames={85}>
        <Scene3_AuthVulture />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_DURATION })}
      />

      <TransitionSeries.Sequence durationInFrames={60}>
        <Scene4_BannerGeneration />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_DURATION })}
      />

      <TransitionSeries.Sequence durationInFrames={60}>
        <Scene5_ServerDB />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_DURATION })}
      />

      <TransitionSeries.Sequence durationInFrames={30}>
        <Scene6_ClosingLoop />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
