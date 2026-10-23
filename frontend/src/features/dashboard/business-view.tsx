"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Load = {id:string;reference:string};
type Case = {id:string;load_id:string;status:string;claim_amount:string;received_amount:string;reason:string;evidence_reference:string};
const money = (v:string|number) => new Intl.NumberFormat("pt-BR", {style:"currency",currency:"BRL"}).format(Number(v));
export function BusinessView({loads}:{loads:Load[]}) {
  const [cases,setCases]=useState<Case[]>([]);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const reload=useCallback(async()=>{try{setCases(await api<Case[]>("/collections"))}catch(e){setError(String(e))}},[]);
  useEffect(()=>{queueMicrotask(()=>void reload())},[reload]);
  async function save(event:FormEvent<HTMLFormElement>,id?:string){
    event.preventDefault();setBusy(true);setError("");
    const form=event.currentTarget;
    const data=Object.fromEntries(new FormData(form));
    if(data.status!=="RECEBIDA"){delete data.received_amount;delete data.receipt_reference;}
    try{await api(id?`/collections/${id}`:"/collections",{method:id?"PATCH":"POST",body:JSON.stringify(data)});form.reset();await reload()}catch(e){setError(e instanceof Error?e.message:"Não foi possível salvar")}finally{setBusy(false)}
  }
  return <section className="content-card"><h2>Conferência e recebimento</h2><p>Revise a diferença antes de cobrar. Registre a referência do romaneio ou comprovante para permitir conferência posterior.</p><p><strong>Recebimentos registrados: {money(cases.reduce((n,c)=>n+Number(c.received_amount),0))}</strong></p>{error&&<p role="alert">{error}</p>}
    <details className="form-card"><summary>Abrir acompanhamento</summary><form className="form-grid" onSubmit={e=>void save(e)}><label>Carga<select name="load_id" required>{loads.filter(l=>!cases.some(c=>c.load_id===l.id)).map(l=><option key={l.id} value={l.id}>{l.reference}</option>)}</select></label><label>Valor a revisar<input name="claim_amount" type="number" min="0.01" step="0.01" required/></label><label>Motivo<textarea name="reason" minLength={5} required/></label><label>Referência do documento<input name="evidence_reference" minLength={3} required/></label><button disabled={busy}>Registrar revisão</button></form></details>
    {cases.map(c=><article className="content-card" key={c.id}><h3>{loads.find(l=>l.id===c.load_id)?.reference??c.load_id} · {c.status}</h3><p>{c.reason}</p><p>{money(c.claim_amount)} · Documento: {c.evidence_reference}</p>{["EM_REVISAO","COBRADA"].includes(c.status)&&<form className="form-grid" onSubmit={e=>void save(e,c.id)}><label>Próximo passo<select name="status">{c.status==="EM_REVISAO"?<option value="COBRADA">Cobrança realizada</option>:<option value="RECEBIDA">Recebimento confirmado</option>}<option value="JUSTIFICADA">Diferença justificada / encerrada</option></select></label><label>Observação<input name="note" minLength={5} required/></label>{c.status==="COBRADA"&&<><label>Valor recebido<input type="number" name="received_amount" min="0" step="0.01"/></label><label>Referência do comprovante<input name="receipt_reference"/></label></>}<button disabled={busy}>Salvar acompanhamento</button></form>}</article>)}
  </section>
}
