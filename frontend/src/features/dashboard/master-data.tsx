"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Location = { id: string; name: string; kind: string; latitude: string | null; longitude: string | null };
type Health = Record<string, { status: string; provider?: string; reason?: string }>;
type Table = { id: string; name: string; versions: { id: string; version: number; valid_from: string; valid_until:string|null; is_active: boolean; configuration:{rate_per_km?:string} }[] };

export function MasterData() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [health, setHealth] = useState<Health>({});
  const [tables, setTables] = useState<Table[]>([]);
  const [message, setMessage] = useState("");
  const refresh = useCallback(async () => {
    const [places, status, freight] = await Promise.all([
      api<Location[]>("/locations"), api<Health>("/integrations/health"), api<Table[]>("/freight-tables"),
    ]);
    setLocations(places); setHealth(status); setTables(freight);
  }, []);
  useEffect(() => { queueMicrotask(() => void refresh()); }, [refresh]);
  async function location(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    await api("/locations", { method: "POST", body: JSON.stringify({ ...data, latitude: data.latitude ? Number(data.latitude) : null, longitude: data.longitude ? Number(data.longitude) : null }) });
    form.reset(); setMessage("Localização cadastrada."); await refresh();
  }
  async function table(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget;
    await api("/freight-tables", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) });
    form.reset(); setMessage("Tabela criada."); await refresh();
  }
  async function version(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form));
    await api("/freight-tables/" + data.table_id + "/versions", { method: "POST", body: JSON.stringify({ version: Number(data.version), valid_from: data.valid_from, valid_until: data.valid_until || null, rate_per_km: Number(data.rate_per_km), is_active: data.is_active === "on" }) });
    form.reset(); setMessage("Versão registrada."); await refresh();
  }
  async function editLocation(item:Location){
    const name=window.prompt("Nome da localização",item.name);if(!name)return;
    const latitude=window.prompt("Latitude (vazio remove)",item.latitude||"");
    const longitude=window.prompt("Longitude (vazio remove)",item.longitude||"");
    try{await api("/locations/"+item.id,{method:"PATCH",body:JSON.stringify({name,kind:item.kind,latitude:latitude?Number(latitude):null,longitude:longitude?Number(longitude):null,source:"MANUAL"})});setMessage("Localização atualizada.");await refresh()}catch(reason){setMessage(reason instanceof Error?reason.message:"Falha ao atualizar localização.")}
  }
  async function editVersion(tableId:string,item:Table["versions"][number]){
    const rate=window.prompt("Tarifa homologada por km",item.configuration.rate_per_km||"");if(!rate)return;
    try{await api("/freight-tables/"+tableId+"/versions/"+item.id,{method:"PATCH",body:JSON.stringify({valid_from:item.valid_from,valid_until:item.valid_until,rate_per_km:Number(rate),is_active:item.is_active})});setMessage("Versão atualizada.");await refresh()}catch(reason){setMessage(reason instanceof Error?reason.message:"Falha ao atualizar versão.")}
  }
  return <main className="app-shell operations-shell">
    <header className="app-header"><div><span className="eyebrow">Administração</span><h1>Cadastros mestres</h1></div><Link href="/dashboard">Voltar ao portal</Link></header>
    {message ? <div className="alert success" role="status">{message}</div> : null}
    <div className="two-columns">
      <section className="form-card"><h2>Nova localização</h2><form className="form-grid one" onSubmit={event => void location(event)}><label>Nome<input name="name" minLength={2} required /></label><label>Tipo<select name="kind"><option value="PRODUTOR">Produtor</option><option value="UNIDADE">Unidade</option><option value="BASE">Base</option></select></label><label>Latitude<input name="latitude" type="number" min="-90" max="90" step="0.000001" /></label><label>Longitude<input name="longitude" type="number" min="-180" max="180" step="0.000001" /></label><button className="primary">Cadastrar</button></form></section>
      <section className="content-card"><h2>Localizações</h2>{locations.map(item => <div className="list-row" key={item.id}><div><strong>{item.name}</strong><span>{item.kind}{item.latitude ? " · " + item.latitude + ", " + item.longitude : " · coordenadas pendentes"}</span></div><button type="button" onClick={()=>void editLocation(item)}>Editar</button></div>)}</section>
    </div>
    <div className="two-columns">
      <section className="form-card"><h2>Nova tabela Frimesa</h2><form className="form-grid one" onSubmit={event => void table(event)}><label>Nome<input name="name" minLength={3} required /></label><button>Criar tabela</button></form>{tables.map(item => <div key={item.id}><div className="list-row"><div><strong>{item.name}</strong><span>{item.versions.length} versões</span></div></div>{item.versions.map(rule=><div className="list-row" key={rule.id}><div><strong>Versão {rule.version}{rule.is_active?" · ativa":""}</strong><span>Desde {rule.valid_from} · R$ {rule.configuration.rate_per_km||"não configurado"}/km</span></div><button type="button" onClick={()=>void editVersion(item.id,rule)}>Editar</button></div>)}</div>)}</section>
      <section className="form-card"><h2>Nova versão vigente</h2><form className="form-grid one" onSubmit={event => void version(event)}><label>Tabela<select name="table_id" required><option value="">Selecione</option>{tables.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Versão<input name="version" type="number" min="1" required /></label><label>Início<input name="valid_from" type="date" required /></label><label>Fim<input name="valid_until" type="date" /></label><label>Tarifa por km<input name="rate_per_km" type="number" min="0.0001" step="0.0001" required /></label><label><input name="is_active" type="checkbox" /> Ativar</label><button className="primary">Registrar versão</button></form></section>
    </div>
    <section className="content-card"><h2>Saúde das integrações</h2>{Object.entries(health).map(([name, item]) => <div className="list-row" key={name}><div><strong>{name.toUpperCase()}</strong><span>{item.provider || item.reason || "Portal"}</span></div><span className="badge">{item.status}</span></div>)}</section>
  </main>;
}
