"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { TrackingShareButton } from "@/features/tracking/tracking-share-button";
import { Check, CheckCircle2, Circle, ExternalLink, MapPin } from "lucide-react";

type Vehicle = { id: string; plate: string; model: string; status: string };
type Trip = { id: string; scheduled_at: string; status: string; load: { reference: string; origin: string; destination: string }; vehicle: Vehicle; driver: { name: string; phone?: string | null } };
type Position = { id: string; vehicle_id: string; latitude: string; longitude: string; accuracy_m: string | null; speed_kmh: string | null; heading: string | null; captured_at: string; source: string };

const statusLabel: Record<string, string> = {
  PLANEJADA: "Saída pendente", EM_ANDAMENTO: "Em viagem", CONCLUIDA: "Concluída",
  CANCELADA: "Cancelada", DISPONIVEL: "Disponível", RESERVADO: "Reservado",
  EM_ROTA: "Em rota", MANUTENCAO: "Em manutenção", INATIVO: "Inativo",
};

function ChecklistItem({ done, children }: { done: boolean; children: React.ReactNode }) {
  return <li className={done ? "done" : ""}><span aria-hidden="true">{done ? <Check size={14}/> : <Circle size={12}/>}</span>{children}</li>;
}

function ageLabel(capturedAt: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(capturedAt).getTime()) / 1000));
  if (seconds < 60) return "agora";
  if (seconds < 3600) return `há ${Math.floor(seconds / 60)} min`;
  if (seconds < 86400) return `há ${Math.floor(seconds / 3600)} h`;
  return `há ${Math.floor(seconds / 86400)} dia(s)`;
}

function mapEmbedUrl(position: Position) {
  const lat = Number(position.latitude);
  const lng = Number(position.longitude);
  const delta = 0.012;
  const bbox = [lng - delta, lat - delta, lng + delta, lat + delta].join(",");
  return `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${lat}%2C${lng}`;
}

function googleMapsUrl(position: Position) {
  return `https://www.google.com/maps/search/?api=1&query=${position.latitude}%2C${position.longitude}`;
}

export function FleetTracking({ trips, vehicles, onStatusChange, onProgramTrip }: { trips: Trip[]; vehicles: Vehicle[]; onStatusChange: (path: string, status: string) => void; onProgramTrip: () => void }) {
  const activeTrips = trips.filter(trip => trip.status === "PLANEJADA" || trip.status === "EM_ANDAMENTO");
  const activeByVehicle = new Map(activeTrips.map(trip => [trip.vehicle.id, trip]));
  const [positions, setPositions] = useState<Position[]>([]);
  const [selectedVehicleId, setSelectedVehicleId] = useState(activeTrips[0]?.vehicle.id ?? vehicles[0]?.id ?? "");
  const [sharing, setSharing] = useState(false);
  const [trackingMessage, setTrackingMessage] = useState("");
  const watchId = useRef<number | null>(null);
  const lastSentAt = useRef(0);

  const loadPositions = useCallback(async () => {
    try { setPositions(await api<Position[]>("/tracking/positions/latest")); } catch { /* Keep the last known positions. */ }
  }, []);

  useEffect(() => {
    queueMicrotask(() => void loadPositions());
    const interval = window.setInterval(() => void loadPositions(), 10_000);
    const refreshWhenVisible = () => { if (document.visibilityState === "visible") void loadPositions(); };
    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [loadPositions]);

  useEffect(() => () => {
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
  }, []);

  const selectedPosition = useMemo(
    () => positions.find(position => position.vehicle_id === selectedVehicleId),
    [positions, selectedVehicleId],
  );

  function stopSharing(message = "Compartilhamento encerrado neste aparelho.") {
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    setSharing(false);
    setTrackingMessage(message);
  }

  function startSharing() {
    if (!selectedVehicleId) { setTrackingMessage("Cadastre e selecione um caminhão primeiro."); return; }
    if (!navigator.geolocation) { setTrackingMessage("Este aparelho não oferece localização pelo navegador."); return; }
    setTrackingMessage("Aguardando autorização de localização…");
    lastSentAt.current = 0;
    watchId.current = navigator.geolocation.watchPosition(async ({ coords, timestamp }) => {
      if (Date.now() - lastSentAt.current < 15_000) return;
      lastSentAt.current = Date.now();
      try {
        const saved = await api<Position>("/tracking/positions", {
          method: "POST",
          body: JSON.stringify({ vehicle_id: selectedVehicleId, latitude: coords.latitude, longitude: coords.longitude, accuracy_m: coords.accuracy, speed_kmh: coords.speed === null ? null : Math.max(0, coords.speed * 3.6), heading: coords.heading, captured_at: new Date(timestamp).toISOString() }),
        });
        setPositions(current => [saved, ...current.filter(position => position.vehicle_id !== saved.vehicle_id)]);
        setSharing(true);
        setTrackingMessage(`Localização enviada ${ageLabel(saved.captured_at)}. Mantenha esta página aberta.`);
      } catch (error) {
        setTrackingMessage(error instanceof Error ? error.message : "Não foi possível enviar a localização.");
      }
    }, error => {
      const messages: Record<number, string> = { 1: "Permissão de localização negada. Libere o acesso nas configurações do navegador.", 2: "O celular não conseguiu determinar a localização.", 3: "A localização demorou demais. Tente novamente em um local aberto." };
      stopSharing(messages[error.code] ?? "Não foi possível acessar a localização.");
    }, { enableHighAccuracy: true, maximumAge: 5_000, timeout: 20_000 });
  }

  return <>
    <div className="page-title"><span className="eyebrow">Operação em andamento</span><h2>Acompanhar frota</h2><p>Veja a posição dos caminhões e o que precisa acontecer em seguida.</p></div>
    <section className="tracking-live content-card">
      <div className="tracking-live-head"><div><span className="live-kicker"><i className={sharing ? "is-live" : ""}/>Rastreamento pelo celular</span><h2>Localização da frota</h2><p>Para testar, abra esta tela no celular que está no caminhão e compartilhe a localização.</p></div><div className="tracking-controls"><label>Caminhão<select value={selectedVehicleId} disabled={sharing} onChange={event => setSelectedVehicleId(event.target.value)}><option value="">Selecione</option>{vehicles.map(vehicle => <option key={vehicle.id} value={vehicle.id}>{vehicle.plate} · {vehicle.model}</option>)}</select></label>{sharing ? <button type="button" className="danger-link" onClick={() => stopSharing()}>Parar localização</button> : <button type="button" className="primary" onClick={startSharing}>Compartilhar minha localização</button>}</div></div>
      {trackingMessage ? <p className="tracking-message" role="status">{trackingMessage}</p> : null}
      {selectedPosition ? <div className="fleet-map-layout"><div className="fleet-map"><iframe title="Mapa da localização selecionada" src={mapEmbedUrl(selectedPosition)} loading="lazy"/><span>Mapa por OpenStreetMap</span></div><aside className="position-detail"><span className="vehicle-plate">{vehicles.find(vehicle => vehicle.id === selectedPosition.vehicle_id)?.plate ?? "Veículo"}</span><strong>{Number(selectedPosition.speed_kmh ?? 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} km/h</strong><p>Atualizado {ageLabel(selectedPosition.captured_at)}</p><small>Precisão aproximada: {Number(selectedPosition.accuracy_m ?? 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} m</small><a className="primary compact" href={googleMapsUrl(selectedPosition)} target="_blank" rel="noreferrer">Abrir no Google Maps <ExternalLink size={15}/></a></aside></div> : <div className="map-empty"><span aria-hidden="true"><MapPin size={30}/></span><h3>Nenhuma posição recebida</h3><p>Selecione um caminhão e toque em “Compartilhar minha localização” no celular.</p></div>}
    </section>
    <section className="tracking-summary" aria-label="Resumo da frota"><article><strong>{activeTrips.length}</strong><span>viagens para acompanhar</span></article><article><strong>{positions.length}</strong><span>veículos com localização</span></article><article><strong>{vehicles.filter(vehicle => vehicle.status === "MANUTENCAO").length}</strong><span>em manutenção</span></article></section>
    <section className="section-heading"><div><span className="eyebrow">Prioridade agora</span><h3>Viagens ativas</h3></div>{activeTrips.length === 0 ? <button type="button" className="primary compact" onClick={onProgramTrip}>Programar viagem</button> : null}</section>
    <div className="tracking-grid">{activeTrips.map(trip => { const started = trip.status === "EM_ANDAMENTO"; const position = positions.find(item => item.vehicle_id === trip.vehicle.id); return <article className="tracking-card" key={trip.id}><div className="tracking-card-head"><div><span className="vehicle-plate">{trip.vehicle.plate}</span><h3>{trip.load.origin} <span aria-hidden="true">→</span> {trip.load.destination}</h3></div><span className={`badge badge-${trip.status.toLowerCase()}`}>{statusLabel[trip.status]}</span></div><p className="tracking-meta">Carga {trip.load.reference} · {trip.driver.name}<br/>Saída prevista: {new Date(trip.scheduled_at).toLocaleString("pt-BR")}</p>{position ? <button type="button" className="position-pill" onClick={() => setSelectedVehicleId(trip.vehicle.id)}><MapPin size={14}/> Posição atualizada {ageLabel(position.captured_at)}</button> : <span className="position-pill stale">Sem localização recebida</span>}<TrackingShareButton trip={trip}/><div className="progress-line" aria-label={started ? "Viagem em andamento" : "Viagem aguardando saída"}><span className="complete"/><span className={started ? "complete" : ""}/><span/></div><ol className="trip-checklist" aria-label={`Checklist da viagem ${trip.load.reference}`}><ChecklistItem done>Veículo, motorista e carga confirmados</ChecklistItem><ChecklistItem done={started}>Saída registrada</ChecklistItem><ChecklistItem done={false}>Entrega e retorno confirmados</ChecklistItem></ol><div className="next-action"><div><small>Próxima ação</small><strong>{started ? "Confirmar entrega" : "Registrar saída"}</strong></div><button type="button" className="primary compact" onClick={() => onStatusChange(`/trips/${trip.id}/status`, started ? "CONCLUIDA" : "EM_ANDAMENTO")}>{started ? "Concluir viagem" : "Iniciar viagem"}</button></div></article>; })}{activeTrips.length === 0 ? <div className="empty-state"><span aria-hidden="true"><CheckCircle2 size={22}/></span><h3>Nenhuma viagem aguardando ação</h3><p>Quando uma viagem for programada, o checklist aparecerá aqui.</p></div> : null}</div>
    <section className="content-card"><div className="section-title"><div><h2>Situação de todos os caminhões</h2><p>Disponibilidade e horário da última posição recebida.</p></div></div><div className="vehicle-status-grid">{vehicles.map(vehicle => { const trip = activeByVehicle.get(vehicle.id); const position = positions.find(item => item.vehicle_id === vehicle.id); return <article key={vehicle.id}><div><strong>{vehicle.plate}</strong><span>{vehicle.model}</span></div><span className={`badge badge-${vehicle.status.toLowerCase()}`}>{statusLabel[vehicle.status] ?? vehicle.status}</span><small>{position ? `Localização ${ageLabel(position.captured_at)}` : trip ? `${trip.driver.name} · sem localização` : "Sem localização"}</small></article>; })}</div>{vehicles.length === 0 ? <p className="empty">Nenhum caminhão cadastrado.</p> : null}</section>
  </>;
}
