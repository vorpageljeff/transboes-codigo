import { LoginForm } from "@/features/auth/login-form";

export default function LoginPage() {
  return <main className="login-shell"><section className="brand-panel"><span className="eyebrow">Central operacional</span><h1>Trans Boes</h1><p>Programação, frota e viagens em uma visão simples.</p></section><section className="login-card"><div><span className="eyebrow">Acesso seguro</span><h2>Bom trabalho.</h2><p>Entre para acompanhar a operação de hoje.</p></div><LoginForm /></section></main>;
}

