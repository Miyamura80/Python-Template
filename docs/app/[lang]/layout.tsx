import { RootProvider } from "fumadocs-ui/provider/next";
import { Archivo } from "next/font/google";
import { defineI18nUI } from "fumadocs-ui/i18n";
import { i18n } from "@/lib/i18n";

const archivo = Archivo({
  subsets: ["latin", "latin-ext"],
  weight: ["500"],
  display: "swap",
});

const { provider } = defineI18nUI(i18n, {
  translations: {
    en: {
      displayName: "English",
    },
    zh: {
      displayName: "中文",
      toc: "目录",
      search: "搜索文档",
      lastUpdate: "最后更新于",
      searchNoResult: "没有结果",
      previousPage: "上一页",
      nextPage: "下一页",
      chooseLanguage: "选择语言",
      chooseTheme: "选择主题",
      editOnGithub: "在 GitHub 上编辑",
      tocNoHeadings: "无标题",
    },
    es: {
      displayName: "Español",
      toc: "En esta página",
      search: "Buscar documentación",
      lastUpdate: "Última actualización",
      searchNoResult: "Sin resultados",
      previousPage: "Página anterior",
      nextPage: "Página siguiente",
      chooseLanguage: "Elegir idioma",
      chooseTheme: "Elegir tema",
      editOnGithub: "Editar en GitHub",
      tocNoHeadings: "Sin encabezados",
    },
    ja: {
      displayName: "日本語",
      toc: "目次",
      search: "ドキュメントを検索",
      lastUpdate: "最終更新",
      searchNoResult: "結果なし",
      previousPage: "前のページ",
      nextPage: "次のページ",
      chooseLanguage: "言語を選択",
      chooseTheme: "テーマを選択",
      editOnGithub: "GitHub で編集",
      tocNoHeadings: "見出しなし",
    },
  },
});

export default async function Layout({
  params,
  children,
}: {
  params: Promise<{ lang: string }>;
  children: React.ReactNode;
}) {
  const { lang } = await params;
  return (
    <html lang={lang} className={archivo.className} suppressHydrationWarning>
      <body className="flex flex-col min-h-screen" suppressHydrationWarning>
        <RootProvider i18n={provider(lang)}>{children}</RootProvider>
      </body>
    </html>
  );
}
