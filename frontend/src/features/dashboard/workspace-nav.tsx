"use client";

import Link from "next/link";
import {
  CalendarRange, ClipboardCheck, FileBarChart, FileUp, LayoutDashboard,
  MoreHorizontal, PackageCheck, Settings, Truck, UsersRound, WalletCards,
  type LucideIcon,
} from "lucide-react";

export type WorkspaceTab =
  | "inicio" | "cargas" | "acompanhar" | "viagens" | "frota"
  | "financeiro" | "cobrancas" | "importacoes" | "operacao"
  | "mobile" | "usuarios" | "conta" | "mais";

type NavItem = { id: WorkspaceTab; label: string; shortLabel?: string; icon: LucideIcon };

const operationItems: NavItem[] = [
  { id: "inicio", label: "Visão geral", shortLabel: "Início", icon: LayoutDashboard },
  { id: "cargas", label: "Cargas", shortLabel: "Cargas", icon: PackageCheck },
  { id: "viagens", label: "Viagens", shortLabel: "Viagens", icon: CalendarRange },
  { id: "frota", label: "Frota", shortLabel: "Frota", icon: Truck },
];

const managementItems: NavItem[] = [
  { id: "financeiro", label: "Financeiro", icon: WalletCards },
  { id: "operacao", label: "Manutenção", icon: ClipboardCheck },
  { id: "cobrancas", label: "Relatórios", icon: FileBarChart },
];

const administrativeItems: NavItem[] = [
  { id: "importacoes", label: "Importações", icon: FileUp },
  { id: "usuarios", label: "Usuários e acessos", shortLabel: "Usuários", icon: UsersRound },
  { id: "mais", label: "Configurações", icon: Settings },
];

const managementTabs: WorkspaceTab[] = ["financeiro", "cobrancas", "importacoes", "operacao", "mobile", "usuarios", "conta", "mais", "acompanhar"];

function NavButton({ item, active, onChange }: { item: NavItem; active: boolean; onChange: (tab: WorkspaceTab) => void }) {
  const Icon = item.icon;
  return <button type="button" className={active ? "active" : ""} aria-current={active ? "page" : undefined} onClick={() => onChange(item.id)}><Icon className="nav-icon" size={18} strokeWidth={1.8} aria-hidden="true"/><span>{item.label}</span></button>;
}

export function WorkspaceNav({ active, onChange, isAdmin }: { active: WorkspaceTab; onChange: (tab: WorkspaceTab) => void; isAdmin: boolean }) {
  return <aside className="workspace-sidebar">
    <div className="sidebar-brand"><span className="brand-mark">TB</span><div><strong>Trans Boes</strong><small>Central operacional</small></div></div>
    <nav aria-label="Navegação principal">
      <span className="nav-group-label">Operação</span>
      {operationItems.map(item => <NavButton key={item.id} item={item} active={active === item.id} onChange={onChange}/>)}
      <span className="nav-group-label">Gestão</span>
      {managementItems.map(item => <NavButton key={item.id} item={item} active={active === item.id} onChange={onChange}/>)}
      <span className="nav-group-label">Administrativo</span>
      {administrativeItems.filter(item => item.id !== "usuarios" || isAdmin).map(item => <NavButton key={item.id} item={item} active={active === item.id} onChange={onChange}/>)}
      <Link className="sidebar-route-link" href="/dashboard/cadastros"><Settings className="nav-icon" size={18} aria-hidden="true"/><span>Cadastros mestres</span></Link>
    </nav>
    <div className="sidebar-help"><strong>Operação conectada</strong><span>Dados atualizados automaticamente para apoiar decisões da equipe.</span></div>
  </aside>;
}

export function WorkspaceMobileNav({ active, onChange }: { active: WorkspaceTab; onChange: (tab: WorkspaceTab) => void }) {
  const mobileItems = operationItems.filter(item => ["inicio", "cargas", "frota"].includes(item.id));
  return <nav className="bottom-nav main-nav" aria-label="Navegação principal no celular">
    {mobileItems.map(item => { const Icon = item.icon; return <button type="button" key={item.id} className={active === item.id ? "active" : ""} aria-current={active === item.id ? "page" : undefined} onClick={() => onChange(item.id)}><Icon className="nav-icon" size={18} strokeWidth={1.8} aria-hidden="true"/><span>{item.shortLabel ?? item.label}</span></button>; })}
    <button type="button" className={managementTabs.includes(active) || active === "viagens" ? "active" : ""} onClick={() => onChange("mais")}><MoreHorizontal className="nav-icon" size={19} aria-hidden="true"/><span>Gestão</span></button>
  </nav>;
}
