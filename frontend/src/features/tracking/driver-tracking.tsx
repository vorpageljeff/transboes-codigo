"use client";

import { useEffect, useRef, useState } from "react";
import { API_URL } from "@/lib/api";

type SharedTrip = {
  driver_name: string;
  vehicle_plate: string;
  vehicle_model: string;
  load_reference: string;
  origin: string;
  destination: string;
  scheduled_at: string;
  status: string;
  expires_at: string;
};

async function publicApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Não foi possível continuar.");
  }
  return response.json() as Promise<T>;
}

export function DriverTracking({ token }: { token: string }) {
  const [trip, setTrip] = useState<SharedTrip | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [sharing, setSharing] = useState(false);
  const [lastSent, setLastSent] = useState<Date | null>(null);
  const watchId = useRef<number | null>(null);
  const lastSentAt = useRef(0);

  useEffect(() => {
    queueMicrotask(async () => {
      try { setTrip(await publicApi<SharedTrip>(`/tracking/share/${token}`)); }
      catch (reason) { setError(reason instanceof Error ? reason.message : "Link inválido."); }
    });
  }, [token]);

  useEffect(() => () => {
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
  }, []);

  function stop(messageText = "Compartilhamento encerrado.") {
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    setSharing(false);
    setMessage(messageText);
  }

  function start() {
    if (!navigator.geolocation) { setError("Este celular não oferece localização pelo navegador."); return; }
    setError("");
    setMessage("Aguardando autorização do celular…");
    lastSentAt.current = 0;
    watchId.current = navigator.geolocation.watchPosition(async ({ coords, timestamp }) => {
      if (Date.now() - lastSentAt.current < 15_000) return;
      lastSentAt.current = Date.now();
      try {
        await publicApi(`/tracking/share/${token}/positions`, {
          method: "POST",
          body: JSON.stringify({ latitude: coords.latitude, longitude: coords.longitude, accuracy_m: coords.accuracy, speed_kmh: coords.speed === null ? null : Math.max(0, coords.speed * 3.6), heading: coords.heading, captured_at: new Date(timestamp).toISOString() }),
        });
        setSharing(true);
        setLastSent(new Date());
        setMessage("Localização enviada. Mantenha esta página aberta durante a viagem.");
      } catch (reason) {
        stop(reason instanceof Error ? reason.message : "Não foi possível enviar a localização.");
      }
    }, locationError => {
      const messages: Record<number, string> = { 1: "Localização bloqueada. Permita o acesso nas configurações do navegador.", 2: "O celular não encontrou sua localização.", 3: "A localização demorou demais. Tente novamente em um local aberto." };
      stop(messages[locationError.code] ?? "Não foi possível acessar a localização.");
    }, { enableHighAccuracy: true, maximumAge: 5_000, timeout: 20_000 });
  }

  return <main className="driver-tracking-shell">
    <header className="driver-brand"><span>TB</span><div><strong>Trans Boes</strong><small>Acompanhamento de viagem</small></div></header>
    {error ? <section className="driver-tracking-card driver-error"><span>!</span><h1>Não foi possível abrir</h1><p>{error}</p></section> : !trip ? <section className="driver-tracking-card"><p>Carregando sua viagem…</p></section> : <section className="driver-tracking-card">
      <span className="eyebrow">Olá, {trip.driver_name.split(" ")[0]}</span>
      <h1>Compartilhe sua localização</h1>
      <p>A central acompanhará somente esta viagem enquanto esta página estiver aberta.</p>
      <div className="driver-trip-route"><span>{trip.origin}</span><b>→</b><span>{trip.destination}</span></div>
      <div className="driver-vehicle"><span>Veículo</span><strong>{trip.vehicle_plate}</strong><small>{trip.vehicle_model} · carga {trip.load_reference}</small></div>
      <div className={`sharing-status ${sharing ? "active" : ""}`}><i/><div><strong>{sharing ? "Localização ativa" : "Localização parada"}</strong><small>{lastSent ? `Último envio às ${lastSent.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : "Nenhuma posição enviada"}</small></div></div>
      {message ? <p className="driver-message" role="status">{message}</p> : null}
      {sharing ? <button type="button" className="driver-stop" onClick={() => stop()}>Parar compartilhamento</button> : <button type="button" className="driver-start" onClick={start}>Iniciar compartilhamento</button>}
      <small className="driver-privacy">Você pode parar quando quiser. O link deixa de funcionar quando a viagem é encerrada.</small>
    </section>}
  </main>;
}
