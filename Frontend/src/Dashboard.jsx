/**
 * frontend/src/components/Dashboard.jsx
 * VERSION COMPLÈTE ET CORRIGÉE
 */

import React, { useState, useEffect } from 'react';
import { attendanceAPI, studentsAPI } from './api_service';


const COLORS = {
  primary: '#4F46E5',
  primaryLight: '#EEF2FF',
  red: '#FF0033',
  redLight: '#FFE6E6',
  green: '#00D4A5',
  greenLight: '#E6FFF8',
  textMain: '#1E293B',
  textMuted: '#64748B',
  border: '#E2E8F0',
  background: '#F8FAFC',
  surface: '#FFFFFF',
};

const Dashboard = ({ addNotification }) => {
  const [stats, setStats] = useState({
    active_students: 0,
    present_today: 0,
    absent_today: 0,
    total_records: 0,
    avg_confidence: 0,
    max_confidence: 0,
    min_confidence: 0,
  });

  const [attendanceLog, setAttendanceLog] = useState([]);
  const [statusList, setStatusList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showAll, setShowAll] = useState(false);
  const [manualLoading, setManualLoading] = useState({});

  /**
   * ✅ FONCTION CORRIGÉE: deepExtract
   * Descend dans la structure de réponse correctement
   */
  const deepExtract = (res, key = null) => {
    if (!res) return key ? [] : {};
    
    let data = res.data || res;

    // Descend UN seul niveau si success et data existent
    if (data.success && data.data) {
      data = data.data;
    }

    // Retourne la clé demandée ou les données complètes
    return key ? (data[key] || []) : data;
  };

  /**
   * Gérer la présence manuelle (bouton du prof)
   */
  const handleManualAttendance = async (studentId, isPresent) => {
    // 🔄 Activer loading pour ce student
    setManualLoading((prev) => ({ ...prev, [studentId]: true }));

    try {
      const response = await attendanceAPI.manualAttendance(studentId, isPresent);

      if (response.success) {
        // ✅ Message succès
        addNotification(
          response.data?.message || `Étudiant marqué ${isPresent ? 'PRÉSENT' : 'ABSENT'}`,
          'success'
        );

        // 🔥 ✅ FIX PRINCIPAL : mise à jour IMMÉDIATE UI
        setStatusList((prev) =>
          prev.map((s) =>
            s.student_id === studentId
              ? { ...s, present: isPresent }
              : s
          )
        );

        //  (optionnel mais recommandé) sync avec backend
        // ne bloque pas l'UI
        loadData();

      } else {
        addNotification(
          response.error || 'Erreur lors de la mise à jour',
          'error'
        );
      }
    } catch (err) {
      console.error('Error handling manual attendance:', err);
      addNotification('Erreur système', 'error');
    } finally {
      // 🔄 Désactiver loading
      setManualLoading((prev) => ({ ...prev, [studentId]: false }));
    }
  };

  /**
   * ✅ FONCTION CORRIGÉE: loadData
   * Gère correctement l'extraction et le logging
   */
  const loadData = async () => {
    try {
      setError(null);
      setLoading(true);

      console.log("[DASHBOARD] Starting data load...");

      // Appels API en parallèle
      const [studentRes, attendanceRes, logRes, statusRes] = await Promise.all([
        studentsAPI.getStats(),
        attendanceAPI.getStats(),
        attendanceAPI.getTodayLog(),
        attendanceAPI.getStatus(),
      ]);

      // Extraction des données
      const studentData = deepExtract(studentRes);
      const attendanceData = deepExtract(attendanceRes);
      const logData = deepExtract(logRes, 'records');
      const statusData = deepExtract(statusRes, 'students');

      console.log("[DASHBOARD] Extracted studentData:", studentData);
      console.log("[DASHBOARD] Extracted attendanceData:", attendanceData);
      console.log("[DASHBOARD] Extracted logData:", logData);
      console.log("[DASHBOARD] Extracted statusData:", statusData);

      // Extraction des nombres clés
      const activeStudents = Number(studentData.active_students) || 0;
      const presentToday = Number(deepExtract(statusRes).present_today) || 0;

      console.log("[DASHBOARD] activeStudents:", activeStudents);
      console.log("[DASHBOARD] presentToday:", presentToday);
      console.log("[DASHBOARD] attendanceLog count:", Array.isArray(logData) ? logData.length : 0);

      // Mise à jour du state
      setStats({
        active_students: activeStudents,
        present_today: presentToday,
        absent_today: Math.max(0, activeStudents - presentToday),
        total_records: Number(attendanceData.total_records) || logData.length || 0,
        avg_confidence: Number(attendanceData.avg_confidence) || 0,
        max_confidence: Number(attendanceData.max_confidence) || 0,
        min_confidence: Number(attendanceData.min_confidence) || 0,
      });

      setAttendanceLog(Array.isArray(logData) ? logData : []);
      setStatusList(Array.isArray(statusData) ? statusData : []);

      setLastUpdated(new Date().toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }));

      console.log("[DASHBOARD] Data load complete ✅");

    } catch (err) {
      console.error("[DASHBOARD] Error:", err);
      setError(err.message || "Erreur de connexion au serveur");
      if (addNotification) addNotification("Erreur lors du chargement du dashboard", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <div style={styles.loading}>Chargement du tableau de bord...</div>;
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.errorCard}>
          <h3 style={styles.errorTitle}>Erreur de synchronisation</h3>
          <p style={styles.errorText}>{error}</p>
          <button 
            onClick={handleRefresh} 
            style={styles.retryBtn}
            disabled={refreshing}
          >
            {refreshing ? 'Rafraîchissement...' : 'Réessayer'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* HEADER */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Tableau de Bord</h2>
          <p style={styles.subtitle}>
            Suivi des présences en temps réel • Dernière mise à jour : {lastUpdated || '—'}
          </p>
        </div>
        <button 
          onClick={handleRefresh} 
          style={styles.refreshBtn} 
          disabled={refreshing}
        >
          {refreshing ? 'Actualisation...' : 'Actualiser'}
        </button>
      </div>

      {/* STATISTIQUES */}
      <div style={styles.statsGrid}>
        <StatCard label="Étudiants inscrits" value={stats.active_students} accent={COLORS.primary} />
        <StatCard label="Présents aujourd'hui" value={stats.present_today} accent={COLORS.green} />
        <StatCard label="Absents aujourd'hui" value={stats.absent_today} accent={COLORS.red} />
        <StatCard 
          label="Taux de présence" 
          value={stats.active_students > 0 ? `${((stats.present_today / stats.active_students) * 100).toFixed(1)}%` : '0%'} 
          accent={stats.present_today / stats.active_students >= 0.75 ? COLORS.green : COLORS.red}
        />
      </div>

      <div style={styles.mainGrid}>
        {/* DERNIERS SCANS */}
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Derniers scans aujourd'hui</h3>
          {attendanceLog.length === 0 ? (
            <div style={styles.emptyState}>
              Aucune présence enregistrée aujourd'hui.
              <br />
              <small style={{ fontSize: '0.85rem', marginTop: '10px', display: 'block' }}>
                ({attendanceLog.length} scans)
              </small>
            </div>
          ) : (
            <div role="table" style={styles.table}>
              <div style={styles.tableHeader}>
                <div style={{ flex: 2 }}>Étudiant</div>
                <div style={{ flex: 1 }}>Confiance</div>
                <div style={{ flex: 1 }}>Heure</div>
              </div>
              {attendanceLog.slice(0, showAll ? attendanceLog.length : 10).map((record, index) => (
                <div key={index} style={styles.tableRow}>
                  <div style={{ flex: 2, fontWeight: 500 }}>
                    {record.student || record.name || 'Inconnu'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <ConfidenceBadge confidence={record.confidence} />
                  </div>
                  <div style={{ flex: 1, color: COLORS.textMuted }}>
                
                    {record.timestamp || '—'}

                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={styles.tableInfo}>
            <span>Total aujourd'hui : {attendanceLog.length} scans</span>
            {attendanceLog.length > 10 && (
              <button onClick={() => setShowAll(!showAll)} style={styles.viewMoreBtn}>
                {showAll ? "Voir moins" : "Voir plus"}
              </button>
            )}
          </div>
        </div>

        {/* ANALYSE DU PIPELINE */}
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Analyse du pipeline</h3>
          <div style={styles.summaryBox}>
            <SummaryItem 
              label="Total scans aujourd'hui" 
              value={stats.total_records} 
              color={COLORS.primary} 
            />
            <SummaryItem 
              label="Précision moyenne" 
              value={stats.avg_confidence ? `${(stats.avg_confidence * 100).toFixed(1)}%` : 'N/A'} 
              color={COLORS.green} 
            />
            <SummaryItem 
              label="Meilleure précision" 
              value={stats.max_confidence ? `${(stats.max_confidence * 100).toFixed(1)}%` : 'N/A'} 
              color={COLORS.green} 
            />
            <SummaryItem 
              label="Précision minimale" 
              value={stats.min_confidence ? `${(stats.min_confidence * 100).toFixed(1)}%` : 'N/A'} 
              color={COLORS.red} 
            />
          </div>
        </div>
      </div>
      
      {/* LISTE DES ÉTUDIANTS */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Liste des étudiants</h3>
        {statusList.length === 0 ? (
          <div style={styles.emptyState}>Aucun étudiant trouvé.</div>
        ) : (
          <div role="table" style={styles.table}>
            <div style={styles.tableHeader}>
              <div style={{ flex: 2 }}>Nom</div>
              <div style={{ flex: 2 }}>Email</div>
              <div style={{ flex: 1.5 }}>Statut</div>
              <div style={{ flex: 2 }}>Action</div>
            </div>
            {statusList.map((student, index) => (
              <div key={student.student_id || index} style={styles.tableRow}>
                <div style={{ flex: 2, fontWeight: 500 }}>
                  {student.name || 'Inconnu'}
                </div>
                <div style={{ flex: 2, color: COLORS.textMuted }}>
                  {student.email || '—'}
                </div>
                <div style={{ flex: 1.5 }}>
                  <StatusBadge present={student.present} />
                </div>
                {/* ✅ NOUVELLE COLONNE: BOUTONS D'ACTION */}
                <div style={{ flex: 2, display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => handleManualAttendance(student.student_id, true)}
                    disabled={manualLoading[student.student_id] || student.present}
                    style={{
                      ...styles.actionButton,
                      ...styles.actionButtonPresent,
                      ...(student.present ? styles.actionButtonDisabled : {}),
                      opacity: manualLoading[student.student_id] ? 0.6 : 1,
                    }}
                    title={student.present ? 'Déjà présent' : 'Marquer présent'}
                  >
                    {manualLoading[student.student_id] ? '...' : '✓ Présent'}
                  </button>
                  <button
                    onClick={() => handleManualAttendance(student.student_id, false)}
                    disabled={manualLoading[student.student_id] || !student.present}
                    style={{
                      ...styles.actionButton,
                      ...styles.actionButtonAbsent,
                      ...(!student.present ? styles.actionButtonDisabled : {}),
                      opacity: manualLoading[student.student_id] ? 0.6 : 1,
                    }}
                    title={!student.present ? 'Déjà absent' : 'Marquer absent'}
                  >
                    {manualLoading[student.student_id] ? '...' : '✗ Absent'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div style={styles.tableInfo}>
          <span>
            Total : {statusList.length} étudiants • {statusList.filter(s => s.present).length} présents
          </span>
        </div>
        </div>
    </div>
    
  );
};

/* ==================== SOUS-COMPOSANTS ==================== */
const StatCard = ({ label, value, accent }) => (
  <div style={{
    ...styles.statCard,
    borderLeft: `6px solid ${accent}`,
    boxShadow: `0 10px 25px -5px ${accent}25`
  }}>
    <p style={styles.statLabel}>{label}</p>
    <p style={{ ...styles.statValue, color: accent }}>{value}</p>
  </div>
);

const ConfidenceBadge = ({ confidence = 0 }) => {
  const score = Number(confidence);
  const perc = (score * 100).toFixed(0);
  let color = COLORS.red, bg = COLORS.redLight;
  if (score > 0.7) { color = COLORS.green; bg = COLORS.greenLight; }
  else if (score > 0.4) { color = COLORS.primary; bg = COLORS.primaryLight; }

  return (
    <span style={{
      padding: '6px 14px',
      backgroundColor: bg,
      color,
      borderRadius: '9999px',
      fontSize: '0.82rem',
      fontWeight: 700
    }}>
      {perc}%
    </span>
  );
};

const StatusBadge = ({ present }) => (
  <span style={{
    padding: '7px 18px',
    backgroundColor: present ? COLORS.greenLight : COLORS.redLight,
    color: present ? '#0A7A5E' : '#C53030',
    borderRadius: '9999px',
    fontSize: '0.84rem',
    fontWeight: 700
  }}>
    {present ? 'PRÉSENT' : 'ABSENT'}
  </span>
);

const SummaryItem = ({ label, value, color }) => (
  <div style={styles.summaryItem}>
    <p style={styles.summaryLabel}>{label}</p>
    <p style={{ ...styles.summaryValue, color }}>{value}</p>
  </div>
);

/* ==================== STYLES ==================== */
const styles = {
  container: { 
    padding: '40px 35px', 
    maxWidth: '1300px', 
    margin: '0 auto', 
    backgroundColor: COLORS.background 
  },
  
  header: { 
    display: 'flex', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    marginBottom: '40px' 
  },
  
  title: { 
    margin: 0, 
    fontSize: '2.4rem', 
    fontWeight: 800, 
    color: COLORS.textMain 
  },
  
  subtitle: { 
    margin: '8px 0 0 0', 
    color: COLORS.textMuted, 
    fontSize: '1.05rem' 
  },
  
  refreshBtn: { 
    padding: '14px 32px', 
    backgroundColor: COLORS.primary, 
    color: 'white', 
    border: 'none', 
    borderRadius: '12px', 
    cursor: 'pointer', 
    fontWeight: 700 
  },

  statsGrid: { 
    display: 'grid', 
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', 
    gap: '24px', 
    marginBottom: '48px' 
  },
  
  statCard: { 
    padding: '28px 24px', 
    backgroundColor: COLORS.surface, 
    borderRadius: '16px' 
  },
  
  statLabel: { 
    margin: 0, 
    fontSize: '0.85rem', 
    color: COLORS.textMuted, 
    fontWeight: 600, 
    textTransform: 'uppercase' 
  },
  
  statValue: { 
    margin: '10px 0 0 0', 
    fontSize: '2.1rem', 
    fontWeight: 800 
  },

  mainGrid: { 
    display: 'grid', 
    gridTemplateColumns: '2fr 1fr', 
    gap: '28px', 
    marginBottom: '40px' 
  },
  
  section: { 
    backgroundColor: COLORS.surface, 
    borderRadius: '18px', 
    padding: '32px', 
    boxShadow: '0 10px 30px rgba(0,0,0,0.07)', 
    border: `1px solid ${COLORS.border}` 
  },
  
  sectionTitle: { 
    margin: '0 0 24px 0', 
    fontSize: '1.25rem', 
    fontWeight: 700, 
    color: COLORS.textMain 
  },

  table: { 
    width: '100%' 
  },
  
  tableHeader: { 
    display: 'flex', 
    padding: '14px 0', 
    borderBottom: `2px solid ${COLORS.border}`, 
    color: COLORS.textMuted, 
    fontWeight: 600, 
    fontSize: '0.92rem' 
  },
  
  tableRow: { 
    display: 'flex', 
    padding: '16px 0', 
    borderBottom: `1px solid ${COLORS.border}`, 
    alignItems: 'center' 
  },

  tableInfo: { 
    marginTop: '16px', 
    fontSize: '0.9rem', 
    color: COLORS.textMuted, 
    display: 'flex', 
    justifyContent: 'space-between', 
    alignItems: 'center' 
  },
  
  viewMoreBtn: { 
    backgroundColor: 'transparent', 
    border: `2px solid ${COLORS.primary}`, 
    color: COLORS.primary, 
    padding: '8px 20px', 
    borderRadius: '8px', 
    cursor: 'pointer', 
    fontWeight: 600 
  },

  summaryBox: { 
    display: 'flex', 
    flexDirection: 'column', 
    gap: '18px' 
  },
  
  summaryItem: { 
    padding: '20px', 
    backgroundColor: COLORS.primaryLight, 
    borderRadius: '12px', 
    borderLeft: `5px solid ${COLORS.primary}` 
  },
  
  summaryLabel: { 
    margin: 0, 
    fontSize: '0.88rem', 
    color: COLORS.textMuted 
  },
  
  summaryValue: { 
    margin: '8px 0 0 0', 
    fontSize: '1.55rem', 
    fontWeight: 700 
  },

  emptyState: { 
    padding: '60px 20px', 
    textAlign: 'center', 
    color: COLORS.textMuted, 
    fontStyle: 'italic' 
  },
  
  errorCard: { 
    padding: '50px 40px', 
    textAlign: 'center', 
    backgroundColor: COLORS.redLight, 
    borderRadius: '16px', 
    border: `2px solid ${COLORS.red}` 
  },
  
  errorTitle: { 
    color: COLORS.red, 
    marginBottom: '12px' 
  },
  
  errorText: { 
    color: '#991B1B', 
    marginBottom: '16px' 
  },
  
  retryBtn: { 
    marginTop: '20px', 
    padding: '14px 32px', 
    backgroundColor: COLORS.red, 
    color: 'white', 
    border: 'none', 
    borderRadius: '12px', 
    cursor: 'pointer', 
    fontWeight: 700 
  },
  
  loading: { 
    padding: '100px', 
    textAlign: 'center', 
    fontSize: '1.3rem', 
    color: COLORS.textMuted 
  },
  
  actionButton: { 
    padding: '6px 12px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.75rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'center',
    whiteSpace: 'nowrap',
  },

  actionButtonPresent: {
    backgroundColor: COLORS.greenLight,
    color: '#0A7A5E',
    border: `2px solid ${COLORS.green}`,
  },

  actionButtonAbsent: {
    backgroundColor: COLORS.redLight,
    color: '#C53030',
    border: `2px solid ${COLORS.red}`,
  },

  actionButtonDisabled: {
    cursor: 'not-allowed',
    opacity: 0.5,
    backgroundColor: COLORS.border,
    color: COLORS.textMuted,
    border: `2px solid ${COLORS.border}`,
  },

};

export default Dashboard;
