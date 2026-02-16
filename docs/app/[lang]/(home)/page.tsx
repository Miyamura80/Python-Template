import { DynamicLink } from "fumadocs-core/dynamic-link";

const greetings: Record<string, string> = {
  en: "Hello World",
  zh: "你好世界",
  es: "Hola Mundo",
  ja: "こんにちは世界",
};

const descriptions: Record<string, string> = {
  en: "You can open",
  zh: "你可以打开",
  es: "Puedes abrir",
  ja: "開くことができます",
};

const docsText: Record<string, string> = {
  en: "and see the documentation.",
  zh: "查看文档。",
  es: "y ver la documentación.",
  ja: "でドキュメントを確認できます。",
};

export default async function HomePage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  return (
    <div className="flex flex-col justify-center text-center flex-1">
      <h1 className="text-2xl font-bold mb-4">
        {greetings[lang] ?? greetings.en}
      </h1>
      <p>
        {descriptions[lang] ?? descriptions.en}{" "}
        <DynamicLink
          href="/[lang]/docs"
          className="font-medium underline"
        >
          /docs
        </DynamicLink>{" "}
        {docsText[lang] ?? docsText.en}
      </p>
    </div>
  );
}
