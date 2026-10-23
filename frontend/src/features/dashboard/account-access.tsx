"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type AuthUser, type UserRole } from "@/lib/api";
import { KeyRound, PencilLine } from "lucide-react";

const roleLabels: Record<UserRole, string> = {
  ADMIN: "Administrador",
  MANAGER: "Gestor",
  OPERATOR: "Operação",
  FINANCIAL: "Financeiro",
  VIEWER: "Consulta",
};

const roleHelp: Record<UserRole, string> = {
  ADMIN: "Acesso completo, inclusive usuários.",
  MANAGER: "Opera viagens e acompanha o financeiro.",
  OPERATOR: "Cargas, frota, motoristas e viagens.",
  FINANCIAL: "Custos, fretes e cobranças.",
  VIEWER: "Consulta os dados sem alterar cadastros.",
};

export function AccountView({ user, onUpdated }: { user: AuthUser; onUpdated: (user: AuthUser) => void }) {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setSaving(true); setError(""); setMessage("");
    const data = new FormData(form);
    const email = String(data.get("email"));
    try {
      const updated = await api<AuthUser>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          name: String(data.get("name")),
          email,
          current_password: email === user.email ? undefined : String(data.get("current_password")),
        }),
      });
      onUpdated(updated);
      setMessage("Seus dados de acesso foram atualizados.");
      form.reset();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível atualizar seus dados.");
    } finally { setSaving(false); }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true); setError(""); setMessage("");
    const data = new FormData(event.currentTarget);
    const next = String(data.get("new_password"));
    if (next !== String(data.get("confirm_password"))) {
      setError("A confirmação da nova senha não confere."); setSaving(false); return;
    }
    try {
      await api<AuthUser>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({current_password: String(data.get("current_password")), new_password: next}),
      });
      sessionStorage.removeItem("transboes_token");
      sessionStorage.setItem("transboes_login_notice", "Senha alterada. Entre novamente com a nova senha.");
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível alterar a senha.");
      setSaving(false);
    }
  }

  return <>
    {error ? <div className="alert error" role="alert">{error}</div> : null}
    {message ? <div className="alert success" role="status">{message}</div> : null}
    <section className="account-summary"><span className="profile-initials">{initials(user.name)}</span><div><strong>{user.name}</strong><span>{user.email}</span><small>{roleLabels[user.role]}</small></div></section>
    <div className="two-columns">
      <section className="form-card"><div className="form-heading"><span className="form-icon"><PencilLine size={20}/></span><div><h3>Dados do login</h3><p>O e-mail será usado para entrar no sistema.</p></div></div><form className="form-grid one" onSubmit={saveProfile}><label>Nome<input name="name" defaultValue={user.name} required minLength={2}/></label><label>E-mail<input name="email" type="email" defaultValue={user.email} required/></label><label>Senha atual <small>Necessária somente ao trocar o e-mail.</small><input name="current_password" type="password" autoComplete="current-password"/></label><button className="primary" disabled={saving}>Salvar meus dados</button></form></section>
      <section className="form-card"><div className="form-heading"><span className="form-icon"><KeyRound size={20}/></span><div><h3>Trocar senha</h3><p>As sessões abertas em outros aparelhos serão encerradas.</p></div></div><form className="form-grid one" onSubmit={changePassword}><label>Senha atual<input name="current_password" type="password" autoComplete="current-password" required/></label><label>Nova senha<input name="new_password" type="password" autoComplete="new-password" minLength={8} required/></label><label>Confirmar nova senha<input name="confirm_password" type="password" autoComplete="new-password" minLength={8} required/></label><button className="primary" disabled={saving}>Alterar senha</button></form></section>
    </div>
  </>;
}

export function UsersView({ currentUser }: { currentUser: AuthUser }) {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true); setError("");
    try { setUsers(await api<AuthUser[]>("/users")); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar os usuários."); }
    finally { setLoading(false); }
  }
  useEffect(() => { queueMicrotask(() => void load()); }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    const form = event.currentTarget;
    const data: Record<string, unknown> = Object.fromEntries(new FormData(form).entries());
    try {
      await api("/users", {method: "POST", body: JSON.stringify(data)});
      form.reset(); setMessage("Acesso criado. Entregue o e-mail e a senha inicial ao funcionário."); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível criar o acesso."); }
  }

  async function update(event: FormEvent<HTMLFormElement>, userId: string) {
    event.preventDefault(); setError(""); setMessage("");
    const form = event.currentTarget;
    const data: Record<string, unknown> = Object.fromEntries(new FormData(form).entries());
    if (!data.password) delete data.password;
    data.is_active = data.is_active === "true";
    try {
      await api(`/users/${userId}`, {method: "PATCH", body: JSON.stringify(data)});
      setMessage("Acesso atualizado. Alterações de senha encerram as sessões antigas."); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível atualizar o acesso."); }
  }

  return <>
    {error ? <div className="alert error" role="alert">{error}</div> : null}
    {message ? <div className="alert success" role="status">{message}</div> : null}
    <section className="guided-note"><span>1</span><div><strong>Cada pessoa deve usar seu próprio acesso</strong><p>Assim, as ações ficam registradas no nome correto e um funcionário pode ser desativado sem trocar a senha de todos.</p></div></section>
    <details className="form-card" open={!users.some(user => user.id !== currentUser.id)}><summary>Novo funcionário</summary><form className="form-grid" onSubmit={create}><label>Nome completo<input name="name" required minLength={2}/></label><label>E-mail de acesso<input name="email" type="email" required/></label><label>Senha inicial<input name="password" type="password" minLength={8} autoComplete="new-password" required/></label><label>Perfil<select name="role" defaultValue="OPERATOR">{roles().map(role => <option value={role} key={role}>{roleLabels[role]} — {roleHelp[role]}</option>)}</select></label><button className="primary wide">Criar acesso</button></form></details>
    <section className="content-card"><div className="section-title"><div><h2>Acessos cadastrados</h2><p>{users.filter(user => user.is_active).length} ativos</p></div></div>{loading ? <div className="empty">Carregando usuários…</div> : users.map(user => <details className="user-row" key={user.id}><summary><span className="profile-initials small">{initials(user.name)}</span><span><strong>{user.name}{user.id === currentUser.id ? " (você)" : ""}</strong><small>{user.email} · {roleLabels[user.role]}</small></span><span className={`badge badge-${user.is_active ? "ativo" : "inativo"}`}>{user.is_active ? "Ativo" : "Inativo"}</span></summary><form className="form-grid" onSubmit={event => void update(event, user.id)}><label>Nome<input name="name" defaultValue={user.name} required/></label><label>E-mail<input name="email" type="email" defaultValue={user.email} required/></label><label>Perfil<select name="role" defaultValue={user.role} disabled={user.id === currentUser.id}>{roles().map(role => <option value={role} key={role}>{roleLabels[role]}</option>)}</select>{user.id === currentUser.id ? <input type="hidden" name="role" value="ADMIN"/> : null}</label><label>Situação<select name="is_active" defaultValue={String(user.is_active)} disabled={user.id === currentUser.id}><option value="true">Ativo</option><option value="false">Inativo</option></select>{user.id === currentUser.id ? <input type="hidden" name="is_active" value="true"/> : null}</label><label className="wide">Nova senha <small>Deixe em branco para manter a senha atual.</small><input name="password" type="password" minLength={8} autoComplete="new-password"/></label><button className="primary wide">Salvar alterações</button></form></details>)}</section>
  </>;
}

function roles(): UserRole[] { return ["ADMIN", "MANAGER", "OPERATOR", "FINANCIAL", "VIEWER"]; }
export function roleLabel(role: UserRole) { return roleLabels[role]; }
export function initials(name: string) { return name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase() || "US"; }
