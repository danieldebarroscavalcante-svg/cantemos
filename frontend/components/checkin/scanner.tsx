"use client";

import { useEffect, useRef, useState } from "react";

type Props = { onScan: (value: string) => void; paused: boolean };

/** Câmera traseira lendo QR Codes continuamente (qr-scanner usa BarcodeDetector ou WebWorker). */
export function Scanner({ onScan, paused }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const scannerRef = useRef<import("qr-scanner").default | null>(null);
  const onScanRef = useRef(onScan);
  const [error, setError] = useState<string | null>(null);
  onScanRef.current = onScan;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { default: QrScanner } = await import("qr-scanner");
      if (cancelled || !videoRef.current) return;
      const scanner = new QrScanner(
        videoRef.current,
        (result) => onScanRef.current(result.data),
        {
          preferredCamera: "environment",
          maxScansPerSecond: 8,
          highlightScanRegion: true,
          highlightCodeOutline: true,
          returnDetailedScanResult: true,
          // Analisa 90% do centro da imagem (o padrão é 2/3): lê mesmo com o QR bem perto da câmera.
          calculateScanRegion: (video) => {
            const size = Math.round(0.9 * Math.min(video.videoWidth, video.videoHeight));
            return {
              x: Math.round((video.videoWidth - size) / 2),
              y: Math.round((video.videoHeight - size) / 2),
              width: size,
              height: size,
              downScaledWidth: 480,
              downScaledHeight: 480,
            };
          },
        },
      );
      scannerRef.current = scanner;
      try {
        await scanner.start();
      } catch {
        if (!cancelled)
          setError(
            "Não foi possível abrir a câmera. Permita o acesso à câmera nas configurações do navegador, ou use a busca por nome.",
          );
      }
    })();
    return () => {
      cancelled = true;
      scannerRef.current?.destroy();
      scannerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const scanner = scannerRef.current;
    if (!scanner) return;
    if (paused) scanner.pause();
    else scanner.start().catch(() => undefined);
  }, [paused]);

  return (
    <div className="relative overflow-hidden rounded-2xl bg-black">
      <video
        ref={videoRef}
        className="aspect-[3/4] w-full object-cover md:aspect-video"
        muted
        playsInline
      />
      {error && (
        <p className="absolute inset-0 grid place-items-center bg-bg/80 p-6 text-center text-strong">
          {error}
        </p>
      )}
    </div>
  );
}
