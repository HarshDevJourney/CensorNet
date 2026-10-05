import "./globals.css";
import type { Metadata } from "next";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/instrument-sans";
import Nav from "@/components/layout/Nav";
import Footer from "@/components/layout/Footer";
import SiteBackground from "@/components/layout/SiteBackground";

export const metadata: Metadata = {
  title: "CensorNet",
  description: "Censor video intelligently while it processes.",
};

/** Runs before paint: apply the saved theme (or the OS preference) so there is no light flash. */
const themeInit = `(function(){try{var t=localStorage.getItem("theme");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){}})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="flex min-h-screen flex-col">
        <SiteBackground />
        <Nav />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
