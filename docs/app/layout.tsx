import "./global.css";
import type { Metadata } from "next";

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

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
