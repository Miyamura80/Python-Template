import { RootProvider } from "fumadocs-ui/provider/next";
import "./global.css";
import { Archivo } from "next/font/google";
import type { Metadata } from "next";

const archivo = Archivo({
  subsets: ["latin"],
  weight: ["500"],
});

export const metadata: Metadata = {
  title: "Python Template Documentation",
  description: "Super-opinionated Python stack for fast development",
  icons: {
    icon: [
      {
        url: "/favicon.ico",
      },
      {
        url: "/icon-light.png",
        media: "(prefers-color-scheme: light)",
      },
      {
        url: "/icon-dark.png",
        media: "(prefers-color-scheme: dark)",
      },
    ],
    apple: "/icon-light.png",
  },
};

export default function Layout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="en" className={archivo.className} suppressHydrationWarning>
      <body className="flex flex-col min-h-screen" suppressHydrationWarning>
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
