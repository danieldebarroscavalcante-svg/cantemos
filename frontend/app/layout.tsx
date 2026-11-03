import type { Metadata, Viewport } from "next";
import "@fontsource-variable/sora";
import "@/styles/tokens.css";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "EVENTMER", template: "%s · EVENTMER" },
  description: "Inscrições, ingressos e credenciamento de eventos.",
  applicationName: "EVENTMER",
  appleWebApp: { capable: true, title: "EVENTMER", statusBarStyle: "black" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    // Mesmo valor de --bg-base (metadados não aceitam variáveis CSS).
    { color: "#000000" },
  ],
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="min-h-dvh font-sans antialiased">{children}</body>
    </html>
  );
}
