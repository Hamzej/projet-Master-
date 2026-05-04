/**
 * frontend/src/components/CameraRecognition.jsx
 * Version Professionnelle - Interface attractive et robuste
 * - Navigation header
 * - Image showcase
 * - Capture vidéo en direct
 * - Gestion complète des cas d'erreur
 */

import React, { useState, useRef, useEffect } from 'react';
import { attendanceAPI } from './api_service';

const COLORS = {
  primary: '#4F46E5',
  primaryDark: '#3730A3',
  primaryLight: '#EEF2FF',
  success: '#10B981',
  successLight: '#DCFCE7',
  danger: '#EF4444',
  dangerLight: '#FEE2E2',
  warning: '#F59E0B',
  warningLight: '#FEF3C7',
  textMain: '#1E293B',
  textMuted: '#64748B',
  border: '#E2E8F0',
  borderLight: '#F1F5F9',
  surface: '#FFFFFF',
  background: '#F8FAFC',
  overlay: 'rgba(0, 0, 0, 0.5)',
};

const CameraRecognition = ({ addNotification }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('camera');
  const [stats, setStats] = useState({ success: 0, failed: 0 });
  const [autoMode, setAutoMode] = useState(false);


  // ================= GESTION CAMÉRA =================
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setStreaming(true);
      }
    } catch (err) {
      console.error('Erreur caméra:', err);
      addNotification('Impossible d\'accéder à la caméra. Vérifiez les permissions.', 'error');
    }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((track) => track.stop());
      setStreaming(false);
    }
  };

  // ================= CAPTURE IMAGE =================
  const captureImage = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    const base64 = canvas.toDataURL('image/jpeg', 0.95);
    setCapturedImage(base64);
    setResult(null);
  };

  // ================= RECONNAISSANCE =================
  const recognizeFace = async () => {
    if (!capturedImage) {
      addNotification('Veuillez capturer une image avant la reconnaissance', 'error');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await attendanceAPI.recognize(capturedImage);

      if (response.success) {
        const resultData = {
          status: 'success',
          data: response.data,
        };
        setResult(resultData);
        setStats((prev) => ({ ...prev, success: prev.success + 1 }));
        addNotification(
          `Étudiant ${response.data.student} reconnu et ajouté à la liste des présents.`,
          'success'
        );

      } else if (response.confidence && response.confidence < 0.5) {
        const resultData = {
          status: 'lowconfidence',
          data: response.data,
        };
        setResult(resultData);
        addNotification('Visage détecté mais confiance faible', 'warning');
      } else if (response.error?.includes('No faces')) {
        const resultData = {
          status: 'noface',
          error: 'Aucun visage détecté. Assurez-vous d\'être bien centré et éclairé.',
        };
        setResult(resultData);
        setStats((prev) => ({ ...prev, failed: prev.failed + 1 }));
        addNotification('Aucun visage détecté', 'error');
      } else {
        const resultData = {
          status: 'nomatch',
          data: response.data,
        };
        setResult(resultData);
        setStats((prev) => ({ ...prev, failed: prev.failed + 1 }));
        addNotification('Visage inconnu dans la base de données', 'warning');
      }
    } catch (err) {
      console.error('Erreur reconnaissance:', err);
      const resultData = {
        status: 'error',
        error: err.message || 'Erreur lors de la reconnaissance',
      };
      setResult(resultData);
      setStats((prev) => ({ ...prev, failed: prev.failed + 1 }));
      addNotification(`Erreur: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // ================= CLEANUP =================
  useEffect(() => {
    return () => stopCamera();
  }, []);
  useEffect(() => {
    let intervalId;

    if (autoMode && streaming) {
      // toutes les 5 secondes
      intervalId = setInterval(() => {
        captureImage();
        recognizeFace();
      }, 8000);
    }

    // nettoyage quand on désactive Auto ou qu'on quitte le composant
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [autoMode, streaming]);

  // ================= RENDER PRINCIPAL =================
  return (
    <div style={styles.container}>
      {/* ============= HEADER NAVIGATION ============= */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.logo}>Reconnaissance Faciale</h1>
          <nav style={styles.nav}>
            <button
              style={{
                ...styles.navButton,
                ...(activeTab === 'camera' ? styles.navButtonActive : {}),
              }}
              onClick={() => setActiveTab('camera')}
            >
              Capture
            </button>
            <button
              style={{
                ...styles.navButton,
                ...(activeTab === 'stats' ? styles.navButtonActive : {}),
              }}
              onClick={() => setActiveTab('stats')}
            >
              Statistiques
            </button>
            <button
              style={{
                ...styles.navButton,
                ...(activeTab === 'about' ? styles.navButtonActive : {}),
              }}
              onClick={() => setActiveTab('about')}
            >
              À propos
            </button>
          </nav>
        </div>
      </header>

      {/* ============= CONTENU PRINCIPAL ============= */}
      <main style={styles.main}>
        {activeTab === 'camera' && (
          <section style={styles.cameraSection}>
            <div style={{ position: "relative", display: "inline-block" }}>
                <img 
                  src="/rec.png" 
                  alt="Reconnaissance faciale" 
                  style={{
                    width: "1200px",
                    borderRadius: "12px",
                    boxShadow: "0 8px 20px rgba(16, 185, 129, 0.6)",
                    border: "3px solid #10B981"
                  }} 
                />
                <div 
                  style={{
                    position: "absolute",
                    top: "40%",          // distance depuis le haut
                    left: "45%",          // centré horizontalement
                    transform: "translate(-50%, -50%)",
                    color: "#40f00a",    
                    textShadow: "2px 2px 6px rgba(0,0,0,0.6)" // ombre pour lisibilité
                  }}
                >
                 <p style={styles.showcaseText}>
                    Système de reconnaissance faciale en temps réel
                  </p>
                  <p style={styles.showcaseSubtext}>
                    Capture vidéo directe et traitement instantané
                  </p>
                </div>
            </div>

            {/* SECTION CAMÉRA */}
            <div style={styles.cameraCard}>
              <h2 style={styles.sectionTitle}>Capture Vidéo</h2>

              {/* VIDEO */}
              <div style={styles.videoWrapper}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={styles.video}
                />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
                {!streaming && <div style={styles.videoPlaceholder}>Caméra inactive</div>}
              </div>
              {/* CONTRÔLES */}
              <div style={styles.controlsGrid}>
                {!streaming ? (
                  <button onClick={startCamera} style={{ ...styles.button, ...styles.buttonSuccess }}>
                    Démarrer caméra
                  </button>
                ) : (
                  <button onClick={stopCamera} style={{ ...styles.button, ...styles.buttonDanger }}>
                    Arrêter caméra
                  </button>
                )}

                <button
                  onClick={captureImage}
                  style={{ ...styles.button, ...styles.buttonPrimary }}
                  disabled={!streaming}
                >
                  Capturer
                </button>

                <button
                  onClick={recognizeFace}
                  style={{ ...styles.button, ...styles.buttonPrimary }}
                  disabled={!capturedImage || loading}
                >
                  {loading ? 'Traitement...' : 'Reconnaître'}
                </button>

                {capturedImage && (
                  <button
                    onClick={() => setCapturedImage(null)}
                    style={{ ...styles.button, ...styles.buttonSecondary }}
                  >
                    Recommencer
                  </button>
                )}
                <button
                  onClick={() => setAutoMode(!autoMode)}
                  style={{ ...styles.button, ...styles.buttonPrimary }}
                  disabled={!streaming}
                >
                  {autoMode ? "Arrêter Auto" : "Auto"}
              </button>
              </div>
              {/* INSTRUCTIONS */}
              <div style={styles.instructionBox}>
                <h3 style={styles.instructionTitle}>Instructions</h3>
                <ul style={styles.instructionList}>
                  <li>Cliquez sur "Démarrer caméra" pour activer votre caméra</li>
                  <li>Centrez votre visage dans le cadre</li>
                  <li>Assurez-vous d'une bonne luminosité</li>
                  <li>Cliquez sur "Capturer" pour prendre une photo</li>
                  <li>Cliquez sur "Reconnaître" pour traiter l'image</li>
                </ul>
              </div>
              {/* APERÇU IMAGE CAPTURÉE */}
              {capturedImage && (
                <div style={styles.previewSection}>
                  <h3 style={styles.previewTitle}>Image capturée</h3>
                  <div style={styles.previewContainer}>
                    <img src={capturedImage} alt="Aperçu capturé" style={styles.previewImage} />
                  </div>
                </div>
              )}
            </div>

            {/* RÉSULTATS */}
            {result && (
              <div style={styles.resultCard}>
                {result.status === 'success' && (
                  <div style={styles.successBox}>
                    <div style={styles.resultHeader}>
                      <h3 style={styles.resultTitle}>Reconnaissance réussie</h3>
                    </div>
                    <div style={styles.resultContent}>
                      <div style={styles.resultRow}>
                        <span style={styles.resultLabel}>Nom:</span>
                        <span style={styles.resultValue}>
                          {result.data.student || result.data.student_name}
                        </span>
                      </div>
                      <div style={styles.resultRow}>
                        <span style={styles.resultLabel}>Email:</span>
                        <span style={styles.resultValue}>
                          {result.data.email || 'Non disponible'}
                        </span>
                      </div>
                      <div style={styles.resultRow}>
                        <span style={styles.resultLabel}>Confiance:</span>
                        <span style={styles.resultValue}>
                          {result.data.confidence
                            ? `${(result.data.confidence * 100).toFixed(1)}%`
                            : 'N/A'}
                        </span>
                      </div>
                      <div style={styles.resultRow}>
                        <span style={styles.resultLabel}>ID Présence:</span>
                        <span style={styles.resultValue}>
                          {result.data.attendance_id || 'N/A'}
                        </span>
                      </div>
                      <div style={styles.resultRow}>
                        <span style={styles.resultLabel}>Heure:</span>
                        <span style={styles.resultValue}>
                          {result.data.timestamp ?? "Non disponible"}
                        </span>
                      </div>
                      <div style={styles.resultRow}>
                          <span style={styles.resultLabel}>Statut:</span>
                          <span style={styles.resultValue}>
                            {result.status === 'success' ? "Présent" : "Absent"}
                          </span>
                        </div>
              
                      <div style={{ display: 'flex', gap: '20px', marginTop: 20 }}>
                        <div>
                          <h4>Photo capturée</h4>
                          <img
                            src={capturedImage}
                            alt="Photo capturée"
                            style={{ maxWidth: '200px', borderRadius: '8px', border: '2px solid #10B981', marginLeft:'5%' }}
                          />
                        </div>
                        <div>
                          <h4>Photo enregistrée</h4>
                          <img
                            src={result.data?.photo_path}
                            alt="Photo enregistrée"
                            style={{ maxWidth: '200px', borderRadius: '8px', border: '2px solid #4F46E5' }}
                          />
                        </div>
                        </div>
                    </div>
                  </div>
                )}

                {result.status === 'lowconfidence' && (
                  <div style={styles.warningBox}>
                    <h3 style={styles.warningTitle}>Confiance faible</h3>
                    <p style={styles.warningMessage}>
                      Visage détecté mais la confiance est insuffisante. Veuillez vous rapprocher
                      et réessayer.
                    </p>
                  </div>
                )}

                {result.status === 'nomatch' && (
                  <div style={styles.warningBox}>
                    <h3 style={styles.warningTitle}>Visage inconnu</h3>
                    <p style={styles.warningMessage}>
                      Ce visage n'a pas été reconnu dans la base de données. Veuillez vous
                      enregistrer d'abord.
                    </p>
                  </div>
                )}

                {result.status === 'noface' && (
                  <div style={styles.errorBox}>
                    <h3 style={styles.errorTitle}>Aucun visage détecté</h3>
                    <p style={styles.errorMessage}>{result.error}</p>
                  </div>
                )}

                {result.status === 'error' && (
                  <div style={styles.errorBox}>
                    <h3 style={styles.errorTitle}>Erreur</h3>
                    <p style={styles.errorMessage}>{result.error}</p>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {activeTab === 'stats' && (
          <section style={styles.statsSection}>
            <h2 style={styles.sectionTitle}>Statistiques de session</h2>
            <div style={styles.statsGrid}>
              <div style={styles.statCard}>
                <div style={styles.statNumber}>{stats.success}</div>
                <div style={styles.statLabel}>Reconnaissances réussies</div>
              </div>
              <div style={styles.statCard}>
                <div style={styles.statNumber}>{stats.failed}</div>
                <div style={styles.statLabel}>Reconnaissances échouées</div>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'about' && (
          <section style={styles.aboutSection}>
            <h2 style={styles.sectionTitle}>À propos du système</h2>
            <div style={styles.aboutContent}>
              <h3 style={styles.aboutTitle}>Reconnaissance faciale avancée</h3>
              <p style={styles.aboutText}>
                Ce système de reconnaissance faciale ne réalise pas lui‑même l’analyse des visages dans l’interface. 
                L’application web capture simplement une image via la caméra et l’envoie au serveur.
                 C’est ensuite le pipeline côté backend qui effectue la détection et la reconnaissance grâce aux algorithmes spécialisés, puis renvoie le résultat à l’interface. 
                 Ainsi, l’interface sert de point d’accès visuel et interactif, tandis que le traitement intelligent est assuré par le pipeline
              </p>
              <h3 style={styles.aboutTitle}>Caractéristiques</h3>
              <ul style={styles.aboutList}>
                <li>I Capture vidéo en haute résolution depuis la caméra.</li>
                <li>Transmission sécurisée des images vers le serveur.</li>
                <li>TDétection automatique des visages par le pipeline backend.</li>
                <li>Reconnaissance et comparaison avec la base de données d’enregistrement.</li>
                <li>Affichage instantané du statut : Présent ou Absent.</li>
                <li>Statistiques de session (succès / échecs) visibles en temps réel.</li>
                <li>Interface moderne, intuitive et entièrement traduite en français.</li>
              </ul>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

// ================= STYLES =================
const styles = {
  container: {
    backgroundColor: COLORS.background,
    minHeight: '100vh',
    fontFamily: "'Segoe UI', 'Roboto', sans-serif",
  },

  header: {
    backgroundColor: COLORS.surface,
    borderBottom: `1px solid ${COLORS.border}`,
    position: 'sticky',
    top: 0,
    zIndex: 100,
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
  },

  headerContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: '70px',
  },

  logo: {
    fontSize: '24px',
    fontWeight: '700',
    color: COLORS.textMain,
    margin: 0,
    letterSpacing: '-0.5px',
  },

  nav: {
    display: 'flex',
    gap: '8px',
  },

  navButton: {
    padding: '8px 16px',
    backgroundColor: 'transparent',
    color: COLORS.textMuted,
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
  },

  navButtonActive: {
    backgroundColor: COLORS.primaryLight,
    color: COLORS.primary,
  },

  main: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '40px 24px',
  },

  cameraSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '32px',
  },


  showcaseIcon: {
    width: '80px',
    height: '80px',
    color: COLORS.primary,
    marginBottom: '20px',
    opacity: 0.8,
  },

  showcaseText: {
    fontSize: '28px',
    fontWeight: '700',
    margin: '0 0 12px 0',
    textShadow: '0 3px 12px rgba(0, 0, 0, 0.4)',
    letterSpacing: '-0.5px',
  },

  showcaseSubtext: {         // centré horizontalement
    fontSize: '16px',
    color: '#fffb00',
    margin: 0,
    textShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
    fontWeight: '700',
  },

  cameraCard: {
    backgroundColor: COLORS.surface,
    borderRadius: '12px',
    padding: '32px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
  },

  sectionTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: COLORS.textMain,
    margin: '0 0 24px 0',
    paddingBottom: '12px',
    borderBottom: `2px solid ${COLORS.border}`,
  },

  videoWrapper: {
    position: 'relative',
    backgroundColor: '#000',
    borderRadius: '8px',
    overflow: 'hidden',
    marginBottom: '24px',
    aspectRatio: '16 /9',
  },

  video: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },

  videoPlaceholder: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.border,
    color: COLORS.textMuted,
    fontSize: '14px',
    fontWeight: '500',
  },

  instructionBox: {
    backgroundColor: COLORS.primaryLight,
    border: `1px solid ${COLORS.border}`,
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '24px',
  },

  instructionTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: COLORS.primary,
    margin: '0 0 12px 0',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },

  instructionList: {
    margin: 0,
    paddingLeft: '20px',
    fontSize: '13px',
    color: COLORS.textMain,
    lineHeight: '1.8',
  },

  controlsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: '12px',
    marginBottom: '24px',
  },

  button: {
    padding: '12px 20px',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'center',
    marginTop: '20px'
  },

  buttonPrimary: {
    backgroundColor: COLORS.primary,
    color: 'white',
  },

  buttonSuccess: {
    backgroundColor: COLORS.success,
    color: 'white',
  },

  buttonDanger: {
    backgroundColor: COLORS.danger,
    color: 'white',
  },

  buttonSecondary: {
    backgroundColor: COLORS.border,
    color: COLORS.textMain,
  },

  previewSection: {
    marginTop: '24px',
    paddingTop: '24px',
    borderTop: `1px solid ${COLORS.border}`,
  },

  previewTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: COLORS.textMain,
    margin: '0 0 16px 0',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },

  previewContainer: {
    display: 'flex',
    justifyContent: 'center',
  },

  previewImage: {
    maxWidth: '300px',
    maxHeight: '300px',
    borderRadius: '8px',
    border: `2px solid ${COLORS.border}`,
  },

  resultCard: {
    backgroundColor: COLORS.surface,
    borderRadius: '12px',
    padding: '32px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
  },

  successBox: {
    borderLeft: `4px solid ${COLORS.success}`,
  },

  resultHeader: {
    marginBottom: '20px',
  },

  resultTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: COLORS.success,
    margin: 0,
  },

  resultContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },

  resultRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: '12px',
    borderBottom: `1px solid ${COLORS.border}`,
  },

  resultLabel: {
    fontSize: '14px',
    fontWeight: '600',
    color: COLORS.textMuted,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },

  resultValue: {
    fontSize: '14px',
    color: COLORS.textMain,
    fontWeight: '500',
  },

  photoSection: {
    marginTop: '20px',
    textAlign: 'center',
  },

  studentPhoto: {
    width: '120px',
    height: '120px',
    borderRadius: '8px',
    objectFit: 'cover',
    border: `2px solid ${COLORS.border}`,
  },

  warningBox: {
    backgroundColor: COLORS.warningLight,
    border: `1px solid ${COLORS.warning}`,
    borderRadius: '8px',
    padding: '20px',
    borderLeft: `4px solid ${COLORS.warning}`,
  },

  warningTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#92400E',
    margin: '0 0 8px 0',
  },

  warningMessage: {
    fontSize: '14px',
    color: '#78350F',
    margin: 0,
    lineHeight: '1.6',
  },

  errorBox: {
    backgroundColor: COLORS.dangerLight,
    border: `1px solid ${COLORS.danger}`,
    borderRadius: '8px',
    padding: '20px',
    borderLeft: `4px solid ${COLORS.danger}`,
  },

  errorTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#991B1B',
    margin: '0 0 8px 0',
  },

  errorMessage: {
    fontSize: '14px',
    color: '#7F1D1D',
    margin: 0,
    lineHeight: '1.6',
  },

  statsSection: {
    backgroundColor: COLORS.surface,
    borderRadius: '12px',
    padding: '32px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
  },

  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '20px',
    marginTop: '24px',
  },

  statCard: {
    backgroundColor: COLORS.primaryLight,
    borderRadius: '8px',
    padding: '24px',
    textAlign: 'center',
    border: `1px solid ${COLORS.border}`,
  },

  statNumber: {
    fontSize: '32px',
    fontWeight: '700',
    color: COLORS.primary,
    margin: '0 0 8px 0',
  },

  statLabel: {
    fontSize: '14px',
    color: COLORS.textMuted,
    margin: 0,
    fontWeight: '500',
  },

  aboutSection: {
    backgroundColor: COLORS.surface,
    borderRadius: '12px',
    padding: '32px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
  },

  aboutContent: {
    marginTop: '24px',
  },

  aboutTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: COLORS.textMain,
    margin: '24px 0 12px 0',
  },

  aboutText: {
    fontSize: '14px',
    color: COLORS.textMuted,
    lineHeight: '1.8',
    margin: 0,
  },

  aboutList: {
    fontSize: '14px',
    color: COLORS.textMuted,
    lineHeight: '2',
    paddingLeft: '20px',
    margin: 0,
  },
};

export default CameraRecognition;
