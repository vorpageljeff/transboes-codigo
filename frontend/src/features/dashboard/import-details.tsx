"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Run={id:string;filename:string;status:string;total_rows:number;imported_rows:number;duplicate_rows:number;error_rows:number;created_at:string};
type Row={row_number:number;external_id:string|null;status:string;errors:string;style_markers:string};
type Detail=Run&{rows:Row[]};

export function ImportDetails(){
  const [runs,setRuns]=useState<Run[]>([]),[detail,setDetail]=useState<Detail|null>(null),[error,setError]=useState("");
  const refresh=useCallback(async()=>{try{setRuns(await api<Run[]>("/imports"))}catch(reason){setError(reason instanceof Error?reason.message:"Falha ao carregar importações.")}},[]);
  useEffect(()=>{queueMicrotask(()=>void refresh())},[refresh]);
  async function open(id:string){try{setDetail(await api<Detail>("/imports/"+id))}catch(reason){setError(reason instanceof Error?reason.message:"Falha ao carregar linhas.")}}
  return <main className="app-shell operations-shell"><header className="app-header"><div><span className="eyebrow">Importações</span><h1>Resultado por linha</h1></div><Link href="/dashboard?tab=importacoes">Voltar às importações</Link></header>{error?<div className="alert error" role="alert">{error}</div>:null}<div className="two-columns"><section className="content-card"><h2>Execuções</h2>{runs.map(run=><button type="button" className="list-row" key={run.id} onClick={()=>void open(run.id)}><span><strong>{run.filename}</strong><small>{new Date(run.created_at).toLocaleString("pt-BR")} · {run.imported_rows} importadas · {run.error_rows} erros</small></span><span className="badge">{run.status}</span></button>)}</section><section className="content-card"><h2>Linhas</h2>{detail?.rows.map(row=>{let errors:string[]=[];try{errors=JSON.parse(row.errors)}catch{}return <div className="list-row" key={row.row_number}><div><strong>Linha {row.row_number} · {row.external_id||"sem identificador"}</strong><span>{errors.length?errors.join("; "):"Processada sem erro"}{row.style_markers!=="[]"?" · marcação visual detectada":""}</span></div><span className="badge">{row.status}</span></div>})}{!detail?<div className="empty">Selecione uma execução para conferir cada linha.</div>:null}</section></div></main>;
}
