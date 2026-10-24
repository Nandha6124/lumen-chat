import { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";
import AuthForm from "./components/AuthForm.jsx";
import Chat from "./components/Chat.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(getToken()));

  // On load, validate a stored token so a refresh keeps the user logged in.
  useEffect(() => {
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setChecking(false));
  }, []);

  const handleAuth = async (mode, email, password) => {
    const { access_token } = await (mode === "login" ? api.login : api.register)(email, password);
    setToken(access_token);
    setUser(await api.me());
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  if (checking) return <div className="center muted">Loading…</div>;
  return user ? <Chat user={user} onLogout={logout} /> : <AuthForm onSubmit={handleAuth} />;
}
