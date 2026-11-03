import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Meus ingressos",
  robots: { index: false, follow: false }, // link pessoal: não indexar
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
