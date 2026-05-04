/**
 * frontend/src/pages/Login.jsx - PAGE DE CONNEXION
 * Login / Register avec validation + JWT auth
 */

import React, { useState } from 'react';
import authService from '../auth_service';

const COLORS = {
  primary: '#4F46E5',
  danger: '#EF4444',
  success: '#10B981',
  textMain: '#1E293B',
  textMuted: '#64748B',
  border: '#E2E8F0',
  background: '#F8FAFC',
};

const Login = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [loginData, setLoginData] = useState({
    username: '',
    password: '',
  });

  const [registerData, setRegisterData] = useState({
    username: '',
    email: '',
    password: '',
    passwordConfirm: '',
    firstName: '',
  });

  /**
   * LOGIN
   */
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const result = await authService.login(
      loginData.username,
      loginData.password
    );

    setLoading(false);

    if (result.success) {
      onLoginSuccess(result.user);
    } else {
      setError(result.error || 'Erreur de connexion');
    }
  };

  /**
   * REGISTER
   */
  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (registerData.password !== registerData.passwordConfirm) {
      setLoading(false);
      return setError('Les mots de passe ne correspondent pas');
    }

    if (registerData.password.length < 8) {
      setLoading(false);
      return setError('Le mot de passe doit contenir au moins 8 caractères');
    }

    const result = await authService.register(
      registerData.username,
      registerData.email,
      registerData.password,
      registerData.passwordConfirm,
      registerData.firstName
    );

    setLoading(false);

    if (result.success) {
      onLoginSuccess(result.user);
    } else {
      setError(result.error || 'Erreur d’inscription');
    }
  };

  /**
   * SWITCH TAB
   */
  const switchTab = () => {
    setIsRegister(!isRegister);
    setError(null);

    setLoginData({ username: '', password: '' });
    setRegisterData({
      username: '',
      email: '',
      password: '',
      passwordConfirm: '',
      firstName: '',
    });
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {/* HEADER */}
        <div style={styles.header}>
          <div style={styles.logo}>A</div>
          <h1 style={styles.title}>Attendance System</h1>
        </div>

        {/* TABS */}
        <div style={styles.tabs}>
          <button
            onClick={switchTab}
            style={{
              ...styles.tab,
              borderBottom: !isRegister
                ? `2px solid ${COLORS.primary}`
                : 'none',
              color: !isRegister ? COLORS.primary : COLORS.textMuted,
            }}
          >
            Connexion
          </button>

          <button
            onClick={switchTab}
            style={{
              ...styles.tab,
              borderBottom: isRegister
                ? `2px solid ${COLORS.primary}`
                : 'none',
              color: isRegister ? COLORS.primary : COLORS.textMuted,
            }}
          >
            Inscription
          </button>
        </div>

        {/* ERROR */}
        {error && (
          <div style={styles.errorBox}>{error}</div>
        )}

        {/* LOGIN */}
        {!isRegister ? (
          <form onSubmit={handleLogin} style={styles.form}>
            <input
              aria-label="username"
              autoComplete="off"
              placeholder="Nom d'utilisateur"
              value={loginData.username}
              onChange={(e) =>
                setLoginData({ ...loginData, username: e.target.value })
              }
              style={styles.input}
            />

            <input
              aria-label="password"
              type="password"
              autoComplete="off"
              placeholder="Mot de passe"
              value={loginData.password}
              onChange={(e) =>
                setLoginData({ ...loginData, password: e.target.value })
              }
              style={styles.input}
            />

            <button
              disabled={loading}
              style={styles.button}
              type="submit"
            >
              {loading ? 'Connexion...' : 'Se connecter'}
            </button>
          </form>
        ) : (
          /* REGISTER */
          <form onSubmit={handleRegister} style={styles.form}>
            <input
              aria-label="username"
              autoComplete="off"
              placeholder="Nom d'utilisateur"
              value={registerData.username}
              onChange={(e) =>
                setRegisterData({ ...registerData, username: e.target.value })
              }
              style={styles.input}
            />

            <input
              aria-label="email"
              type="email"
              autoComplete="off"
              placeholder="Email"
              value={registerData.email}
              onChange={(e) =>
                setRegisterData({ ...registerData, email: e.target.value })
              }
              style={styles.input}
            />

            <input
              aria-label="firstname"
              autoComplete="off"
              placeholder="Prénom"
              value={registerData.firstName}
              onChange={(e) =>
                setRegisterData({
                  ...registerData,
                  firstName: e.target.value,
                })
              }
              style={styles.input}
            />

            <input
              aria-label="password"
              type="password"
              autoComplete="off"
              placeholder="Mot de passe"
              value={registerData.password}
              onChange={(e) =>
                setRegisterData({
                  ...registerData,
                  password: e.target.value,
                })
              }
              style={styles.input}
            />

            <input
              aria-label="confirm password"
              type="password"
              autoComplete="off"
              placeholder="Confirmer mot de passe"
              value={registerData.passwordConfirm}
              onChange={(e) =>
                setRegisterData({
                  ...registerData,
                  passwordConfirm: e.target.value,
                })
              }
              style={styles.input}
            />

            <button
              disabled={loading}
              style={styles.button}
              type="submit"
            >
              {loading ? 'Inscription...' : 'S’inscrire'}
            </button>
          </form>
        )}

        {/* FOOTER */}
        <p style={styles.footer}>
          {isRegister
            ? 'Déjà un compte ?'
            : 'Pas encore de compte ?'}{' '}
          <button onClick={switchTab} style={styles.link}>
            {isRegister ? 'Connexion' : 'Inscription'}
          </button>
        </p>
      </div>
    </div>
  );
};

/**
 * STYLES
 */
const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: COLORS.background,
  },

  card: {
    width: 420,
    background: 'white',
    padding: 30,
    borderRadius: 12,
    boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
  },

  header: {
    textAlign: 'center',
    marginBottom: 20,
  },

  logo: {
    width: 50,
    height: 50,
    borderRadius: 10,
    background: COLORS.primary,
    color: 'white',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    fontWeight: 'bold',
    margin: '0 auto',
  },

  title: {
    fontSize: 18,
    marginTop: 10,
    color: COLORS.textMain,
  },

  tabs: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: 20,
  },

  tab: {
    flex: 1,
    padding: 10,
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontWeight: 'bold',
  },

  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },

  input: {
    padding: 10,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 6,
    outline: 'none',
  },

  button: {
    padding: 12,
    background: COLORS.primary,
    color: 'white',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    fontWeight: 'bold',
  },

  errorBox: {
    background: '#FEE2E2',
    color: '#991B1B',
    padding: 10,
    borderRadius: 6,
    marginBottom: 10,
  },

  footer: {
    marginTop: 15,
    textAlign: 'center',
    fontSize: 14,
    color: COLORS.textMuted,
  },

  link: {
    background: 'none',
    border: 'none',
    color: COLORS.primary,
    cursor: 'pointer',
    fontWeight: 'bold',
  },
};

export default Login;