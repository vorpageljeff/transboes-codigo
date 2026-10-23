"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { MessageCircle } from "lucide-react";

type ShareableTrip = {
  id: string;
  status: string;
  driver: { name: string; phone?: string | null };
};

export function TrackingShareButton({ trip }: { trip: ShareableTrip }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function send() {
    setBusy(true);
    setMessage("");
    const popup = window.open("about:blank", "_blank");
    try {
      const share = await api<{ token: string; driver_name: string; driver_phone: string | null; vehicle_plate: string; origin: string; destination: string }>(`/tracking/trips/${trip.id}/shares`, { method: "POST" });
      const link = `${window.location.origin}/rastrear/${share.token}`;
      const text = `Olá, ${share.driver_name}! Acompanhe a viagem ${share.origin} → ${share.destination} com o veículo ${share.vehicle_plate}. Abra este link e autorize a localização: ${link}`;
      let phone = (share.driver_phone ?? "").replace(/\D/g, "");
      if (phone.length === 10 || phone.length === 11) phone = `55${phone}`;
      const whatsapp = `https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
      if (popup) popup.location.href = whatsapp;
      else window.location.href = whatsapp;
      setMessage("Link criado e aberto no WhatsApp.");
    } catch (reason) {
      popup?.close();
      setMessage(reason instanceof Error ? reason.message : "Não foi possível criar o link.");
    } finally {
      setBusy(false);
    }
  }

  if (trip.status !== "PLANEJADA" && trip.status !== "EM_ANDAMENTO") return null;
  return <div className="share-trip-action"><button type="button" className="whatsapp-button" disabled={busy} onClick={() => void send()}><MessageCircle size={16} aria-hidden="true"/>{busy ? "Preparando…" : "Enviar rastreio no WhatsApp"}</button>{message ? <small role="status">{message}</small> : null}</div>;
}
