"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const saved = sessionStorage.getItem("transboes_login_notice");
    if (saved) { queueMicrotask(() => setNotice(saved)); sessionStorage.removeItem("transboes_login_notice"); }
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setLoading(true);
    const data = new FormData(event.currentTarget);
    try { const result = await login(String(data.get("email")), String(data.get("password"))); sessionStorage.setItem("transboes_token", result.access_token); router.push("/dashboard"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Falha inesperada."); }
    finally { setLoading(false); }
  }
  return <form onSubmit={submit}>{notice?<div className="alert success" role="status">{notice}</div>:null}<label htmlFor="email">E-mail</label><input id="email" name="email" type="email" autoComplete="username" required placeholder="seuemail@empresa.com.br"/><label htmlFor="password">Senha</label><input id="password" name="password" type="password" autoComplete="current-password" minLength={8} required/><div className="form-error" role="alert">{error}</div><button type="submit" disabled={loading}>{loading ? "Entrando…" : "Entrar"}</button></form>;
}
