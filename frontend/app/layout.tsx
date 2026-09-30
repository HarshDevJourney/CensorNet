import "./globals.css";
import type { Metadata } from "next";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Video Censorship",
  description: "Stream while it processes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
