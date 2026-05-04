/**
 * frontend/src/components/App.jsx
 * VERSION FINALE - Couleur #00BFFF + Barre de recherche améliorée
 */

import React, { useState, useEffect, useRef } from 'react';
import Login from './pages/Login';
import Dashboard from './Dashboard';
import Enrollment from './Enrollment';
import CameraRecognition from './CameraRecognition';
import authService from './auth_service';
import { studentsAPI } from './api_service';

const COLORS = {
  primary: '#00BFFF',        // Bleu ciel brillant (comme demandé)
  primaryDark: '#0099CC',
  secondary: '#3B82F6',
  success: '#10B981',
  error: '#EF4444',
  background: '#F8FAFC',
  surface: '#FFFFFF',
  sidebar: 'linear-gradient(180deg, #00BFFF, #0099CC)', // Dégradé avec #00BFFF
  textMain: '#1E293B',
  textMuted: '#64748B',
  border: '#E2E8F0',
};

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [currentView, setCurrentView] = useState('dashboard');
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);

  const [sidebarOpen, setSidebarOpen] = useState(true);

  const debounceRef = useRef(null);

  useEffect(() => {
    try {
      authService.initialize();
      const user = authService.getUser();

      if (authService.isAuthenticated() && user) {
        setCurrentUser(user);
        setIsAuthenticated(true);
      }
    } catch (err) {
      console.error('Auth init error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const addNotification = (message, type = 'info') => {
    const id = Date.now();
    setNotifications((prev) => [...prev, { id, message, type }]);

    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, 4000);
  };

  const resetAppState = () => {
    setSearchQuery('');
    setSearchResults([]);
    setShowResults(false);
    setNotifications([]);
    setCurrentView('dashboard');
  };

  const handleSearch = (value) => {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!value || value.trim().length < 2) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setSearchLoading(true);

    debounceRef.current = setTimeout(async () => {
      try {
        const result = await studentsAPI.search(value);
        if (result.success) {
          setSearchResults(result.data?.results || []);
          setShowResults(true);
        }
      } catch (err) {
        console.error(err);
        addNotification('Erreur lors de la recherche', 'error');
      } finally {
        setSearchLoading(false);
      }
    }, 400);
  };

  const handleSelectStudent = (student) => {
    if (!student) return;
    const name = student.name || 'Inconnu';
    setSearchQuery(name);
    setShowResults(false);
    addNotification(`Étudiant sélectionné : ${name}`, 'success');
  };

  const handleLoginSuccess = (user) => {
    setCurrentUser(user);
    setIsAuthenticated(true);
    addNotification(`Bienvenue ${user.first_name || user.username || 'Utilisateur'}`, 'success');
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error(err);
    }
    setCurrentUser(null);
    setIsAuthenticated(false);
    resetAppState();
    addNotification('Déconnexion réussie', 'info');
  };

  if (loading) {
    return <div style={styles.loadingScreen}>Chargement de l'application...</div>;
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  const username = currentUser?.first_name || currentUser?.username || 'Utilisateur';
  const role = currentUser?.role || (currentUser?.is_superuser ? 'Administrateur' : 'Utilisateur');

  return (
    <div style={styles.appWrapper}>
      {/* SIDEBAR avec #00BFFF */}
      {sidebarOpen && (
        <aside style={styles.sidebar}>
          <div style={styles.brand}>
            <div style={styles.brandIcon}></div>
            <h1 style={styles.brandName}>Attendance OS</h1>
          </div>

          <nav style={styles.nav}>
            <NavItem
              icon=""
              label="Tableau de Bord"
              active={currentView === 'dashboard'}
              onClick={() => setCurrentView('dashboard')}
            />
            <NavItem
              icon="👤"
              label="Enrôlement"
              active={currentView === 'enrollment'}
              onClick={() => setCurrentView('enrollment')}
            />
            <NavItem
              icon="📸"
              label="Reconnaissance Faciale"
              active={currentView === 'camera'}
              onClick={() => setCurrentView('camera')}
            />
          </nav>

          <div style={styles.userSection}>
            <div style={styles.userAvatar}>👨‍💼</div>
            <div style={styles.userInfo}>
              <div style={styles.userName}>{username}</div>
              <div style={styles.userRole}>{role}</div>
            </div>
          </div>

          <button onClick={handleLogout} style={styles.logoutBtn}>
            Déconnexion
          </button>
        </aside>
      )}

      {/* MAIN CONTENT */}
      <main style={styles.main}>
        <header style={styles.topBar}>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} style={styles.menuBtn}>
            ☰
          </button>

          {/* BARRE DE RECHERCHE AMÉLIORÉE */}
          <div style={{ position: 'relative', width: '460px' }}>
            <div style={styles.searchBar}>
              <span style={styles.searchIcon}></span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Rechercher un étudiant par nom ou email..."
                style={styles.searchInput}
              />
              {searchLoading && <span style={styles.loadingIndicator}>●●●</span>}
            </div>

            {showResults && (
              <div style={styles.searchDropdown}>
                {searchResults.length === 0 ? (
                  <div style={styles.emptyResult}>Aucun résultat trouvé</div>
                ) : (
                  searchResults.map((student, index) => (
                    <div
                      key={index}
                      style={styles.searchResultItem}
                      onClick={() => handleSelectStudent(student)}
                    >
                      <div style={{ fontWeight: 600 }}>{student.name}</div>
                      <div style={{ fontSize: '0.85rem', color: COLORS.textMuted }}>
                        ID: {student.student_id}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </header>

        <div style={styles.contentArea}>
          {currentView === 'dashboard' && <Dashboard addNotification={addNotification} />}
          {currentView === 'enrollment' && <Enrollment addNotification={addNotification} />}
          {currentView === 'camera' && <CameraRecognition addNotification={addNotification} />}
        </div>
      </main>

      {/* NOTIFICATIONS */}
      <div style={styles.toastContainer}>
        {notifications.map((notif) => (
          <div
            key={notif.id}
            style={{
              ...styles.toast,
              backgroundColor:
                notif.type === 'success' ? COLORS.success :
                notif.type === 'error' ? COLORS.error : COLORS.primary,
            }}
          >
            {notif.message}
          </div>
        ))}
      </div>
    </div>
  );
};

/* ==================== NAV ITEM ==================== */
const NavItem = ({ icon, label, active, onClick }) => (
  <div
    onClick={onClick}
    style={{
      ...styles.navItem,
      backgroundColor: active ? 'rgba(255,255,255,0.25)' : 'transparent',
      color: active ? '#FFFFFF' : 'rgba(255,255,255,0.85)',
      borderLeft: active ? `4px solid #FFFFFF` : '4px solid transparent',
    }}
  >
    <span style={{ fontSize: '1.4rem', marginRight: '14px' }}>{icon}</span>
    {label}
  </div>
);

/* ==================== STYLES ==================== */
const styles = {
  loadingScreen: {
    height: '100vh',
    display: 'grid',
    placeItems: 'center',
    background: COLORS.background,
    fontSize: '1.1rem',
    color: COLORS.textMuted,
  },

  appWrapper: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
    background: COLORS.background,
  },

  sidebar: {
    width: 280,
    background: COLORS.sidebar,
    color: 'white',
    padding: '28px 20px',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '4px 0 25px rgba(0,0,0,0.15)',
  },

  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    marginBottom: 45,
  },

  brandIcon: {
    width: 54,
    height: 54,
    background: 'rgba(255,255,255,0.25)',
    borderRadius: 14,
    display: 'grid',
    placeItems: 'center',
    fontSize: 28,
    backdropFilter: 'blur(8px)',
  },

  brandName: {
    fontSize: 23,
    fontWeight: 700,
    margin: 0,
    letterSpacing: '-0.5px',
  },

  nav: { flex: 1 },

  navItem: {
    padding: '16px 18px',
    marginBottom: 8,
    borderRadius: 12,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    fontSize: 16,
    fontWeight: 500,
    transition: 'all 0.3s ease',
  },

  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    background: 'rgba(255,255,255,0.15)',
    borderRadius: 14,
    marginBottom: 24,
  },

  userAvatar: { fontSize: 32 },

  userInfo: { flex: 1 },

  userName: { fontWeight: 600, fontSize: 15.5 },
  userRole: { fontSize: 13, opacity: 0.85 },

  logoutBtn: {
    padding: '14px 20px',
    background: 'rgba(255,255,255,0.2)',
    color: 'white',
    border: 'none',
    borderRadius: 12,
    cursor: 'pointer',
    fontWeight: 600,
  },

  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },

  topBar: {
    padding: '20px 28px',
    background: COLORS.surface,
    borderBottom: `1px solid ${COLORS.border}`,
    display: 'flex',
    alignItems: 'center',
    gap: 20,
    boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  },

  menuBtn: {
    fontSize: 28,
    padding: '8px 14px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    borderRadius: 10,
  },

  // ==================== BARRE DE RECHERCHE AMÉLIORÉE ====================
  searchBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    background: 'linear-gradient(90deg, #F8FAFC, #F1F5F9)',
    borderRadius: 16,
    padding: '14px 18px',
    width: '100%',
    boxShadow: '0 4px 15px rgba(0, 191, 255, 0.15)', // Ombre bleue légère
    border: `2px solid transparent`,
    transition: 'all 0.3s ease',
  },

  searchIcon: {
    color: COLORS.primary,
    fontSize: 20,
  },

  searchInput: {
    border: 'none',
    outline: 'none',
    background: 'transparent',
    width: '100%',
    fontSize: 15.5,
    color: COLORS.textMain,
  },

  loadingIndicator: {
    color: COLORS.primary,
    animation: 'pulse 1.5s infinite',
  },

  searchDropdown: {
    position: 'absolute',
    top: '72px',
    left: 0,
    width: '100%',
    background: 'white',
    border: `1px solid ${COLORS.border}`,
    borderRadius: 14,
    boxShadow: '0 20px 30px -10px rgba(0, 191, 255, 0.25)',
    maxHeight: 340,
    overflowY: 'auto',
    zIndex: 100,
  },

  searchResultItem: {
    padding: '16px 20px',
    cursor: 'pointer',
    borderBottom: `1px solid ${COLORS.border}`,
    transition: 'background 0.2s',
  },

  emptyResult: {
    padding: '24px',
    textAlign: 'center',
    color: COLORS.textMuted,
  },

  contentArea: {
    flex: 1,
    padding: 28,
    overflowY: 'auto',
    background: COLORS.background,
  },

  toastContainer: {
    position: 'fixed',
    bottom: 28,
    right: 28,
    zIndex: 200,
  },

  toast: {
    color: 'white',
    padding: '16px 22px',
    marginTop: 12,
    borderRadius: 12,
    boxShadow: '0 15px 25px -5px rgba(0,0,0,0.2)',
    minWidth: 300,
    fontWeight: 500,
  },
};

export default App;