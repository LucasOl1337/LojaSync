import { FormEvent, useEffect, useState } from "react";

import App from "./App";
import { bootstrapAuth, changePassword, fetchAuthSession, login, logout } from "./api";
import type { AuthSessionResponse } from "./types";

type ScreenMode = "loading" | "login" | "setup" | "app";

const MIN_PASSWORD_HINT = 8;

export default function AuthShell() {
  const [session, setSession] = useState<AuthSessionResponse | null>(null);
  const [mode, setMode] = useState<ScreenMode>("loading");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const [nextPasswordConfirm, setNextPasswordConfirm] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [passwordPanelOpen, setPasswordPanelOpen] = useState(false);

  async function refreshSession() {
    setMode("loading");
    setError(null);
    try {
      const current = await fetchAuthSession();
      setSession(current);
      if (!current.auth_enabled) {
        setMode("app");
        return;
      }
      if (current.bootstrap_required) {
        setMode("setup");
        return;
      }
      setMode(current.authenticated ? "app" : "login");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Nao foi possivel validar a sessao.");
      setMode("login");
    }
  }

  useEffect(() => {
    void refreshSession();
  }, []);

  async function handleSetup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (password !== confirmPassword) {
      setError("As senhas precisam ser iguais.");
      return;
    }
    setBusy("setup");
    try {
      await bootstrapAuth(password);
      setPassword("");
      setConfirmPassword("");
      await refreshSession();
      setMessage("Senha inicial configurada com sucesso.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Nao foi possivel configurar a senha.");
    } finally {
      setBusy(null);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setBusy("login");
    try {
      await login(password);
      setPassword("");
      await refreshSession();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Nao foi possivel entrar.");
    } finally {
      setBusy(null);
    }
  }

  async function handleLogout() {
    setError(null);
    setMessage(null);
    setBusy("logout");
    try {
      await logout();
      setSession(null);
      setPasswordPanelOpen(false);
      setCurrentPassword("");
      setNextPassword("");
      setNextPasswordConfirm("");
      await refreshSession();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Nao foi possivel sair.");
      setBusy(null);
    }
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (nextPassword !== nextPasswordConfirm) {
      setError("A nova senha e a confirmacao precisam ser iguais.");
      return;
    }
    setBusy("change-password");
    try {
      await changePassword(currentPassword, nextPassword);
      setCurrentPassword("");
      setNextPassword("");
      setNextPasswordConfirm("");
      setPasswordPanelOpen(false);
      setMessage("Senha alterada. Entre novamente com a nova senha.");
      await refreshSession();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Nao foi possivel atualizar a senha.");
    } finally {
      setBusy(null);
    }
  }

  if (mode === "app" && session && !session.auth_enabled) {
    return <App />;
  }

  if (mode === "loading") {
    return (
      <div className="authGateShell">
        <div className="authCard">
          <span className="authEyebrow">LojaSync Security</span>
          <h1>Preparando acesso seguro</h1>
          <p>Validando sua sessao e as configuracoes iniciais do sistema.</p>
        </div>
      </div>
    );
  }

  if (mode === "setup" || mode === "login") {
    const isSetup = mode === "setup";
    return (
      <div className="authGateShell">
        <form className="authCard" onSubmit={isSetup ? handleSetup : handleLogin}>
          <span className="authEyebrow">{isSetup ? "Primeira configuracao" : "Acesso administrativo"}</span>
          <h1>{isSetup ? "Defina a senha mestre do LojaSync" : "Entrar no LojaSync"}</h1>
          <p>
            {isSetup
              ? `Proteja o painel com uma senha de pelo menos ${MIN_PASSWORD_HINT} caracteres antes de liberar o uso da equipe.`
              : "Use a senha administrativa para liberar o painel de vendas e automacao."}
          </p>

          <label className="authField">
            <span>{isSetup ? "Nova senha" : "Senha"}</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={isSetup ? "new-password" : "current-password"}
              placeholder={isSetup ? "Crie uma senha forte" : "Digite sua senha"}
            />
          </label>

          {isSetup ? (
            <label className="authField">
              <span>Confirmar senha</span>
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                placeholder="Repita a senha"
              />
            </label>
          ) : null}

          {error ? <div className="message error">{error}</div> : null}
          {message ? <div className="message success">{message}</div> : null}

          <button className="primaryButton authSubmitButton" type="submit" disabled={Boolean(busy)}>
            {busy ? "Processando..." : isSetup ? "Salvar senha e entrar" : "Entrar"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="securedShell">
      <header className="securityBar">
        <div>
          <span className="authEyebrow">Sessao protegida</span>
          <strong>{session?.user || "admin"}</strong>
        </div>
        <div className="securityBarActions">
          <button className="ghostButton" type="button" onClick={() => setPasswordPanelOpen((current) => !current)}>
            Trocar senha
          </button>
          <button className="ghostButton" type="button" onClick={() => void handleLogout()} disabled={busy === "logout"}>
            {busy === "logout" ? "Saindo..." : "Sair"}
          </button>
        </div>
      </header>

      {passwordPanelOpen ? (
        <form className="securityPanel" onSubmit={handleChangePassword}>
          <label className="authField">
            <span>Senha atual</span>
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          <label className="authField">
            <span>Nova senha</span>
            <input
              type="password"
              value={nextPassword}
              onChange={(event) => setNextPassword(event.target.value)}
              autoComplete="new-password"
            />
          </label>
          <label className="authField">
            <span>Confirmar nova senha</span>
            <input
              type="password"
              value={nextPasswordConfirm}
              onChange={(event) => setNextPasswordConfirm(event.target.value)}
              autoComplete="new-password"
            />
          </label>
          <div className="securityPanelActions">
            <button className="ghostButton" type="button" onClick={() => setPasswordPanelOpen(false)}>
              Fechar
            </button>
            <button className="primaryButton" type="submit" disabled={busy === "change-password"}>
              {busy === "change-password" ? "Salvando..." : "Atualizar senha"}
            </button>
          </div>
        </form>
      ) : null}

      {error ? <div className="authInlineMessage message error">{error}</div> : null}
      {message ? <div className="authInlineMessage message success">{message}</div> : null}

      <App />
    </div>
  );
}
