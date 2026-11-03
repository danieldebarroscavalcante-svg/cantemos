"use client";

import QRCode from "qrcode";
import { useEffect, useState } from "react";

/** QR Code em SVG, nítido em qualquer tela. Fundo branco fixo para leitura no modo escuro. */
export function QrCode({
  value,
  label,
  size = 220,
}: {
  value: string;
  label: string;
  size?: number;
}) {
  const [svg, setSvg] = useState<string | null>(null);

  useEffect(() => {
    QRCode.toString(value, {
      type: "svg",
      margin: 2,
      errorCorrectionLevel: "M",
    })
      .then(setSvg)
      .catch(() => setSvg(null));
  }, [value]);

  return (
    <div
      role="img"
      aria-label={label}
      className="mx-auto aspect-square rounded-xl bg-white p-1 [&_svg]:h-full [&_svg]:w-full"
      style={{ width: size, maxWidth: "100%" }}
      // SVG gerado localmente pela biblioteca a partir de um token assinado.
      dangerouslySetInnerHTML={svg ? { __html: svg } : undefined}
    />
  );
}
