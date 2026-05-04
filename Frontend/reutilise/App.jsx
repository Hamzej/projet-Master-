/**
 * App Component - Main application with navigation
 * Interface complète avec sidebar et pages
 */

import React, { useState } from "react";
import Dashboard from "./Dashboard";
import Enrollment from "./Enrollment";
import CameraRecognition from "./CameraRecognition";

const COLORS = {
  primary: "#4F46E5",
  background: "#F8FAFC",
  surface: "#FFFFFF",
  textMain: "#1E293B",
  textMuted: "#64748B",
  border: "#E2E8F0",
  sidebar: "#1E293B"
};

const App = () => {
  const [currentView, setCurrentView] = useState("dashboard");
  const [notifications, setNotifications] = useState([]);

  const addNotification = (message, type = "info") => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 4000);
  };

  return (
    <div style={styles.appWrapper}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.brand}>
          <div style={styles.brandIcon}>Σ</div>
          <h2 style={styles.brandName}>Attendance OS</h2>
        </div>

        <nav style={styles.sideNav}>
          <NavItem
            active={currentView === "dashboard"}
            onClick={() => setCurrentView("dashboard")}
            icon="📊"
            label="Dashboard"
          />
          <NavItem
            active={currentView === "enrollment"}
            onClick={() => setCurrentView("enrollment")}
            icon="➕"
            label="Enrôlement"
          />
          <NavItem
            active={currentView === "camera"}
            onClick={() => setCurrentView("camera")}
            icon="📷"
            label="Reconnaissance"
          />
        </nav>

        <div style={styles.userProfile}>
          <div style={styles.avatar}>A</div>
          <div>
            <div style={styles.userName}>Admin</div>
            <div style={styles.userRole}>Superuser</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main style={styles.main}>
        <header style={styles.topBar}>
          <div style={styles.searchBar}>
            <span>🔍</span>
            <input
              style={styles.searchInput}
              placeholder="Rechercher un étudiant..."
            />
          </div>
          <div style={styles.topActions}>
            <button style={styles.iconBtn}>🔔</button>
            <button style={styles.iconBtn}>⚙️</button>
          </div>
        </header>

        <div style={styles.content}>
          {/* Page Title */}
          <header style={styles.pageHeader}>
            <h1 style={styles.pageTitle}>
              {currentView === "dashboard" && "Vue d'ensemble"}
              {currentView === "enrollment" && "Nouvel Étudiant"}
              {currentView === "camera" && "Reconnaissance en direct"}
            </h1>
            <p style={styles.pageSubtitle}>
              Système de surveillance biométrique actif
            </p>
          </header>

          {/* Pages */}
          {currentView === "dashboard" && (
            <Dashboard />
          )}
          {currentView === "enrollment" && (
            <Enrollment onSuccess={() => addNotification("✅ Étudiant enrôlé avec succès!", "success")} />
          )}
          {currentView === "camera" && (
            <CameraRecognition />
          )}
        </div>
      </main>

      {/* Notifications Toast */}
      <div style={styles.toastContainer}>
        {notifications.map(notif => (
          <Toast key={notif.id} message={notif.message} type={notif.type} />
        ))}
      </div>

      {/* Global Styles */}
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(400px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background-color: ${COLORS.background};
        }

        input, select, textarea {
          font-family: inherit;
        }

        input:focus, select:focus, textarea:focus {
          outline: none;
        }

        button:hover {
          opacity: 0.9;
        }

        button:disabled {
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

/**
 * ============ SUB-COMPONENTS ============
 */

const NavItem = ({ active, icon, label, onClick }) => (
  <div
    onClick={onClick}
    style={{
      ...styles.navItem,
      backgroundColor: active ? COLORS.primary + "15" : "transparent",
      color: active ? COLORS.primary : COLORS.textMuted,
      borderLeft: active ? `4px solid ${COLORS.primary}` : "4px solid transparent"
    }}
  >
    <span style={styles.navIcon}>{icon}</span>
    {label}
  </div>
);

const Toast = ({ message, type }) => {
  const bgColor = {
    success: "#DCFCE7",
    error: "#FEE2E2",
    info: "#DBEAFE",
    warning: "#FEF3C7"
  }[type] || "#F1F5F9";

  const textColor = {
    success: "#166534",
    error: "#991B1B",
    info: "#0C4A6E",
    warning: "#92400E"
  }[type] || "#475569";

  return (
    <div
      style={{
        ...styles.toast,
        backgroundColor: bgColor,
        color: textColor
      }}
    >
      {message}
    </div>
  );
};

/**
 * ============ STYLES ============
 */
const styles = {
  appWrapper: {
    display: "flex",
    minHeight: "100vh",
    backgroundColor: COLORS.background
  },

  // SIDEBAR
  sidebar: {
    width: "280px",
    backgroundColor: COLORS.sidebar,
    color: "white",
    display: "flex",
    flexDirection: "column",
    position: "fixed",
    height: "100vh",
    overflowY: "auto"
  },
  brand: {
    padding: "30px 24px",
    display: "flex",
    alignItems: "center",
    gap: "12px"
  },
  brandIcon: {
    width: "40px",
    height: "40px",
    backgroundColor: COLORS.primary,
    borderRadius: "8px",
    display: "grid",
    placeItems: "center",
    fontWeight: "bold",
    fontSize: "1.3rem"
  },
  brandName: {
    margin: 0,
    fontSize: "1.1rem",
    fontWeight: 700
  },
  sideNav: {
    flex: 1,
    padding: "0 12px"
  },
  navItem: {
    display: "flex",
    alignItems: "center",
    padding: "12px 16px",
    cursor: "pointer",
    borderRadius: "0 8px 8px 0",
    marginBottom: "4px",
    transition: "all 0.2s",
    fontWeight: 500,
    fontSize: "0.95rem"
  },
  navIcon: {
    marginRight: "12px",
    fontSize: "1.2rem"
  },
  userProfile: {
    padding: "20px",
    backgroundColor: "#0F172A",
    display: "flex",
    alignItems: "center",
    gap: "12px"
  },
  avatar: {
    width: "40px",
    height: "40px",
    backgroundColor: COLORS.primary,
    color: "white",
    borderRadius: "50%",
    display: "grid",
    placeItems: "center",
    fontWeight: "bold"
  },
  userName: {
    margin: 0,
    fontWeight: 600,
    fontSize: "0.9rem"
  },
  userRole: {
    margin: "2px 0 0 0",
    fontSize: "0.75rem",
    color: "#94A3B8"
  },

  // MAIN
  main: {
    marginLeft: "280px",
    flex: 1,
    display: "flex",
    flexDirection: "column"
  },

  // TOP BAR
  topBar: {
    height: "70px",
    backgroundColor: COLORS.surface,
    borderBottom: `1px solid ${COLORS.border}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 40px",
    position: "sticky",
    top: 0,
    zIndex: 10
  },
  searchBar: {
    display: "flex",
    alignItems: "center",
    backgroundColor: "#F1F5F9",
    padding: "8px 16px",
    borderRadius: "8px",
    width: "400px",
    gap: "8px"
  },
  searchInput: {
    border: "none",
    background: "transparent",
    width: "100%",
    fontSize: "0.9rem",
    outline: "none"
  },
  topActions: {
    display: "flex",
    gap: "12px"
  },
  iconBtn: {
    width: "40px",
    height: "40px",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    backgroundColor: "transparent",
    cursor: "pointer",
    fontSize: "1.2rem",
    transition: "all 0.2s"
  },

  // CONTENT
  content: {
    padding: "40px",
    flex: 1,
    overflowY: "auto"
  },
  pageHeader: {
    marginBottom: "30px"
  },
  pageTitle: {
    margin: 0,
    fontSize: "1.8rem",
    fontWeight: 800,
    color: COLORS.textMain
  },
  pageSubtitle: {
    margin: "8px 0 0 0",
    color: COLORS.textMuted,
    fontSize: "0.95rem"
  },

  // TOAST CONTAINER
  toastContainer: {
    position: "fixed",
    bottom: "30px",
    right: "30px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    zIndex: 1000
  },
  toast: {
    padding: "16px 24px",
    borderRadius: "8px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    fontWeight: 500,
    animation: "slideIn 0.3s ease-out",
    maxWidth: "400px"
  }
};

export default App;
