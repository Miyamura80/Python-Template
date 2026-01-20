import { RootProvider } from 'fumadocs-ui/provider/next';
import './global.css';
import { Archivo } from 'next/font/google';

const archivo = Archivo({
  subsets: ['latin'],
  weight: ['500'],
});

export default function Layout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="en" className={archivo.className} suppressHydrationWarning>
      <body className="flex flex-col min-h-screen" suppressHydrationWarning>
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
