const defaultApiUrl = process.env.NODE_ENV === "production"
  ? "https://api.2.25.189.129.nip.io/api/v1"
  : "http://localhost:8000/api/v1";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? defaultApiUrl;

export type UserRole = "ADMIN" | "MANAGER" | "OPERATOR" | "FINANCIAL" | "VIEWER";
export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/auth/login`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ email, password })});
  if (!response.ok) throw new Error(response.status === 401 ? "E-mail ou senha inválidos." : "Não foi possível entrar. Tente novamente.");
  return response.json() as Promise<LoginResponse>;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem("transboes_token");
  if (!token) throw new Error("Sua sessão expirou. Entre novamente.");
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    cache: options.cache ?? "no-store",
    headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`, ...options.headers},
  });
  if (response.status === 401) {
    sessionStorage.removeItem("transboes_token");
    window.location.replace("/");
    throw new Error("Sua sessão expirou. Entre novamente.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const validationMessage = Array.isArray(body.detail) && typeof body.detail[0]?.msg === "string"
      ? body.detail[0].msg.replace(/^Value error, /, "")
      : null;
    throw new Error(typeof body.detail === "string" ? body.detail : validationMessage ?? "Não foi possível concluir a operação.");
  }
  return response.json() as Promise<T>;
}
