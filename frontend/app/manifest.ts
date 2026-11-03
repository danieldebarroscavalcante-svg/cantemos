import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "EVENTMER",
    short_name: "EVENTMER",
    description: "Inscrições, ingressos e credenciamento de eventos.",
    start_url: "/",
    display: "standalone",
    background_color: "#000000", // --bg-base
    theme_color: "#000000", // --bg-base
    lang: "pt-BR",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
