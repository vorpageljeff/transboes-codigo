"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type Trip={status:string;started_at:string|null;completed_at:string|null;load:{reference:string;origin:string;destination:string;distance_km?:string|null;freight_value:string|null};vehicle:{plate:string;model:string;odometer_km:number};driver:{name:string}};
type Event={id:string;status:string;note:string;evidence_reference:string|null;occurred_at:string;odometer_km:number|null;distance_km:string|null};
function elapsed(start:string|null,end:string|null){if(!start)return "Não iniciada";const minutes=Math.max(0,Math.round((new Date(end||Date.now()).getTime()-new Date(start).getTime())/60000));return Math.floor(minutes/60)+"h "+minutes%60+"min"}

export function TripDetail({id}:{id:string}){
  const [trip,setTrip]=useState<Trip|null>(null),[events,setEvents]=useState<Event[]>([]),[error,setError]=useState("");
  const refresh=useCallback(async()=>{try{const [detail,timeline]=await Promise.all([api<Trip>("/trips/"+id),api<Event[]>("/trips/"+id+"/events")]);setTrip(detail);setEvents(timeline)}catch(reason){setError(reason instanceof Error?reason.message:"Falha ao carregar viagem.")}},[id]);
  useEffect(()=>{queueMicrotask(()=>void refresh())},[refresh]);
  const odometers=useMemo(()=>events.map(item=>item.odometer_km).filter((value):value is number=>value!==null),[events]);
  const measuredDistance=odometers.length>1?Math.max(...odometers)-Math.min(...odometers):null;
  return <main className="app-shell operations-shell"><header className="app-header"><div><span className="eyebrow">Viagem</span><h1>{trip?.load.reference||"Carregando…"}</h1></div><Link href="/dashboard?tab=viagens">Voltar às viagens</Link></header>{error?<div className="alert error" role="alert">{error}</div>:null}{trip?<><section className="metrics"><article><strong>{trip.status}</strong><span>Situação</span></article><article><strong>{elapsed(trip.started_at,trip.completed_at)}</strong><span>Tempo de rota</span></article><article><strong>{measuredDistance===null?"Pendente":measuredDistance+" km"}</strong><span>Distância por hodômetro</span></article><article><strong>{trip.load.freight_value||"Pendente"}</strong><span>Valor do frete</span></article></section><section className="content-card"><h2>{trip.load.origin} → {trip.load.destination}</h2><p>{trip.driver.name} · {trip.vehicle.plate} · {trip.vehicle.model}</p><p>Distância planejada: {trip.load.distance_km||"não informada"} km · Hodômetro atual: {trip.vehicle.odometer_km} km</p></section><section className="content-card"><h2>Timeline</h2>{events.map(item=><div className="list-row" key={item.id}><div><strong>{item.status}</strong><span>{new Date(item.occurred_at).toLocaleString("pt-BR")} · {item.note||"Sem observação"}{item.odometer_km!==null?" · "+item.odometer_km+" km":""}</span>{item.evidence_reference?<small>Comprovante: {item.evidence_reference}</small>:null}</div></div>)}{!events.length?<div className="empty">Nenhum evento registrado.</div>:null}</section></>:null}</main>;
}
