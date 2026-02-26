import { Composition } from "remotion";
import { PythonTemplateAnimation } from "./compositions/PythonTemplateAnimation";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="PythonTemplateAnimation"
      component={PythonTemplateAnimation}
      durationInFrames={300}
      fps={30}
      width={600}
      height={400}
    />
  );
};
