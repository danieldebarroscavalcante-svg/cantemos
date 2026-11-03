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
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
