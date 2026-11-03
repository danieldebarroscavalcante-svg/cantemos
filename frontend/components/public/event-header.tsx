import { formatEventDate, formatTime, mapsUrl } from "@/lib/format";
import type { PublicEvent } from "@/lib/api";

export function EventHeader({
  event,
  compact = false,
}: {
  event: PublicEvent;
  compact?: boolean;
}) {
  const place = [event.venue_name, event.venue_address]
    .filter(Boolean)
    .join(" · ");
  return (
    <header className="space-y-4">
      <div>
        <p className="eyebrow">EVENTMER</p>
        <h1
          className={
            compact
              ? "text-3xl font-normal leading-tight text-strong"
              : "title-display"
          }
        >
          {event.title}
        </h1>
        {event.subtitle && (
          <p className="mt-1 text-lg text-muted">{event.subtitle}</p>
        )}
      </div>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-border bg-surface p-4">
          <dt className="text-sm text-muted">Quando</dt>
          <dd className="font-semibold">{formatEventDate(event.starts_at)}</dd>
          <dd className="text-muted">
            Início às {formatTime(event.starts_at)}
            {event.doors_open_at &&
              ` · portas às ${formatTime(event.doors_open_at)}`}
          </dd>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-4">
          <dt className="text-sm text-muted">Onde</dt>
          {place ? (
            <>
              <dd className="font-semibold">
                {event.venue_name ?? event.venue_address}
              </dd>
              {event.venue_name && event.venue_address && (
                <dd className="text-muted">{event.venue_address}</dd>
              )}
              <dd>
                <a
                  href={mapsUrl(place)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-primary underline"
                >
                  Abrir no mapa
                </a>
              </dd>
            </>
          ) : (
            <dd className="text-muted">Local a confirmar</dd>
          )}
        </div>
      </dl>
    </header>
  );
}
