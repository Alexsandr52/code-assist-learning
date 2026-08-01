import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Code Learn Assist",
  description: "Practice Python library syntax by typing short code fragments."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}

