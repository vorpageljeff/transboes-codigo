"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Detail = {
  load: { reference:string;customer:string;product:string;origin:string;destination:string;status:string;notes:string|null;freight_value:string|null };
  versions: {id:string;version:number;action:string;reason:string|null;created_at:string;snapshot:Record<string,unknown>}[];
};

export function LoadDetail({ id }: { id: string }) {
  const [detail,setDetail]=useState<Detail|null>(null),[error,setError]=useState(""),[notice,setNotice]=useState("");
  const refresh=useCallback(async()=>{try{setDetail(await api<Detail>("/loads/"+id))}catch(reason){setError(reason instanceof Error?reason.message:"Falha ao carregar carga.")}},[id]);
  useEffect(()=>{queueMicrotask(()=>void refresh())},[refresh]);
  async function cancel(event:FormEvent<HTMLFormElement>){event.preventDefault();const data=Object.fromEntries(new FormData(event.currentTarget));if(data.confirmation!=="CANCELAR"){setError("Digite CANCELAR para confirmar.");return}if(!window.confirm("Confirma o cancelamento definitivo desta carga?"))return;delete data.confirmation;try{await api("/loads/"+id+"/cancel",{method:"POST",body:JSON.stringify(data)});setNotice("Carga cancelada com histórico preservado.");await refresh()}catch(reason){setError(reason instanceof Error?reason.message:"Falha ao cancelar.")}}
  return <main className="app-shell operations-shell"><header className="app-header"><div><span className="eyebrow">Carga</span><h1>{detail?.load.reference||"Carregando…"}</h1></div><Link href="/dashboard?tab=cargas">Voltar às cargas</Link></header>{error?<div className="alert error" role="alert">{error}</div>:null}{notice?<div className="alert success" role="status">{notice}</div>:null}{detail?<><section className="content-card"><h2>{detail.load.customer} · {detail.load.product}</h2><p>{detail.load.origin} → {detail.load.destination}</p><p>Situação: <strong>{detail.load.status}</strong> · Frete: {detail.load.freight_value||"não informado"}</p>{detail.load.notes?<p>{detail.load.notes}</p>:null}</section>{detail.load.status!=="CANCELADA"?<section className="form-card"><h2>Cancelar carga</h2><p>Esta ação afeta a operação e o financeiro. O histórico será preservado.</p><form className="form-grid one" onSubmit={event=>void cancel(event)}><label>Motivo<textarea name="reason" minLength={5} required/></label><label>Digite CANCELAR para confirmar<input name="confirmation" pattern="CANCELAR" required/></label><button className="danger-link">Confirmar cancelamento</button></form></section>:null}<section className="content-card"><h2>Histórico de versões</h2>{detail.versions.map(item=><div className="list-row" key={item.id}><div><strong>Versão {item.version} · {item.action}</strong><span>{new Date(item.created_at).toLocaleString("pt-BR")}{item.reason?" · "+item.reason:""}</span></div></div>)}{!detail.versions.length?<div className="empty">Esta carga ainda não possui alterações anteriores.</div>:null}</section></>:null}</main>;
}
