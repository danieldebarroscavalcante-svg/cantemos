import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "EVENTMER",
    short_name: "EVENTMER",
    description: "Inscrições, ingressos e credenciamento de eventos.",
    start_url: "/",
    display: "standalone",
    background_color: "#fafaf9",
    theme_color: "#4338ca",
    lang: "pt-BR",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
