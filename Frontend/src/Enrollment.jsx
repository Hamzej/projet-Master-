/**
 * frontend/src/components/Enrollment.jsx - VERSION PREMIUM ATTRACTIVE
 * Champ fichier personnalisé + Design moderne
 */

import React, { useState } from 'react';
import { studentsAPI } from './api_service';

const COLORS = {
  primary: '#1E40AF',
  primaryLight: '#DBEAFE',
  accent: '#10B981',
  accentLight: '#A7F3D0',
  danger: '#EF4444',
  dangerLight: '#FEE2E2',
  textMain: '#0F172A',
  textMuted: '#64748B',
  border: '#CBD5E1',
  surface: '#FFFFFF'
};

const Enrollment = ({ addNotification }) => {
  const [formData, setFormData] = useState({ name: '', email: '', level: '', filiere: '' });
  const [files, setFiles] = useState([]);  // ✅ Array au lieu d'un fichier
  const [previews, setPreviews] = useState([]);  // ✅ Array de previews
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('info');

  const showMessage = (msg, type = 'info') => {
    setMessage(String(msg));
    setMessageType(type);
    if (type === 'success' || type === 'error') {
      setTimeout(() => setMessage(null), 5000);
    }
  };

   const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    
    if (selectedFiles.length === 0) return;

    // Valider que ce sont des images
    const validFiles = selectedFiles.filter((file) => {
      if (!file.type.startsWith("image/")) {
        showMessage(`${file.name} n'est pas une image`, "error");
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) return;

    // ✅ Ajouter les fichiers aux fichiers existants
    const newFiles = [...files, ...validFiles];
    setFiles(newFiles);

    // Générer les previews
    const newPreviews = [];
    validFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (typeof event.target?.result === 'string') {
          newPreviews.push({
            id: Date.now() + Math.random(),
            src: event.target.result,
            name: file.name
          });
          if (newPreviews.length === validFiles.length) {
            setPreviews([...previews, ...newPreviews]);
          }
        }
      };
      reader.readAsDataURL(file);
    });
  };

  // ✅ NOUVELLE FONCTION: Retirer une photo
  const handleRemovePhoto = (photoId) => {
    const index = previews.findIndex((p) => p.id === photoId);
    if (index !== -1) {
      const newPreviews = previews.filter((_, i) => i !== index);
      const newFiles = files.filter((_, i) => i !== index);
      setFiles(newFiles);
      setPreviews(newPreviews);
      showMessage("Photo supprimée", "info");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const name = formData.name.trim();
    const email = formData.email?.trim() || null;
    const level = formData.level;
    const filiere = formData.filiere;

    // ✅ Vérifier qu'il y a au moins une photo
    if (!name || files.length === 0 || !level || !filiere) {
      showMessage("Nom, au moins une photo, niveau et filière requis", "error");
      return;
    }

    setLoading(true);

    try {
      showMessage("Envoi en cours...", "info");

      console.log("FILES:", files.length, "| LEVEL:", level, "| FILIERE:", filiere);
      
      // ✅ Passer le array de fichiers au lieu d'un seul
      const response = await studentsAPI.enrollFromImage(
        name,
        email,
        files,  // ← Array de fichiers
        level,
        filiere
      );

      if (response.success) {
        const summary = response.data.enrollment_summary;
        const summaryMsg = `${summary.success}/${summary.total_photos} photos enregistrées`;
        
        showMessage(
          `${response.data.name} enrôlé! ${summaryMsg}`,
          "success"
        );
        addNotification(`${response.data.name} enrôlé`, 'success');

        // ✅ Réinitialiser le formulaire
        setFormData({ name: '', email: '', level: '', filiere: '' });
        setFiles([]);
        setPreviews([]);
      } else {
        throw new Error(response.error || "Erreur inconnue");
      }

    } catch (err) {
      const errorMsg = err.message || "Erreur serveur";
      showMessage(`❌ ${errorMsg}`, "error");
      addNotification(`❌ ${errorMsg}`, 'error');
    }

    setLoading(false);
  };

  const messageColors = {
    success: { bg: COLORS.accentLight, text: '#166534', border: COLORS.accent },
    error: { bg: COLORS.dangerLight, text: COLORS.danger, border: COLORS.danger },
    info: { bg: COLORS.primaryLight, text: COLORS.primary, border: COLORS.primary }
  };

  const msgColor = messageColors[messageType];

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <h2 style={styles.title}>Enrôlement d'un étudiant</h2>
        </div>

        {message && (
          <div style={{
            ...styles.message,
            backgroundColor: msgColor.bg,
            color: msgColor.text,
            borderLeft: `5px solid ${msgColor.border}`
          }}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="text"
            placeholder="Nom complet"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            style={styles.input}
            disabled={loading}
            required
          />

          <input
            type="email"
            placeholder="Email (optionnel)"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            style={styles.input}
            disabled={loading}
          />

          <div style={styles.selectRow}>
            <select
              value={formData.level}
              onChange={(e) => setFormData({ ...formData, level: e.target.value })}
              style={styles.select}
              disabled={loading}
              required
            >
              <option value="">Niveau</option>
              <option value="L1">L1</option>
              <option value="L2">L2</option>
              <option value="L3">L3</option>
              <option value="M1">M1</option>
              <option value="M2">M2</option>
              <option value="D1">D1</option>
              <option value="D2">D2</option>
            </select>

            <input
              type="text"
              placeholder="Filière"
              value={formData.filiere}
              onChange={(e) => setFormData({ ...formData, filiere: e.target.value })}
              style={styles.input}
              disabled={loading}
              required
            />
          </div>

          {/* Champ fichier personnalisé - MULTI-PHOTOS */}
          <div style={styles.fileUploadArea}>
            <label style={styles.fileLabel}>
              <span style={styles.uploadIcon}>📸</span>
              Choisir des photos (minimum 1)
              <input
                type="file"
                accept="image/*"
                multiple 
                onChange={handleFileSelect}
                disabled={loading}
                style={styles.hiddenInput}
              />
            </label>
            {files.length > 0 && (
              <p style={styles.fileCount}>
                {files.length} photo{files.length > 1 ? 's' : ''} sélectionnée{files.length > 1 ? 's' : ''}
              </p>
            )}
          </div>

          {/* ✅ AFFICHER TOUTES LES PREVIEWS */}
          {previews.length > 0 && (
            <div style={styles.previewsContainer}>
              {previews.map((preview, index) => (
                <div key={preview.id} style={styles.previewItem}>
                  <img src={preview.src} alt={`Preview ${index + 1}`} style={styles.preview} />
                  <button
                    type="button"
                    onClick={() => handleRemovePhoto(preview.id)}
                    disabled={loading}
                    style={styles.removeButton}
                    title="Retirer cette photo"
                  >
                    ✕
                  </button>
                  <p style={styles.photoLabel}>Photo {index + 1}</p>
                </div>
              ))}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.button,
              opacity: loading ? 0.8 : 1
            }}
          >
            {loading ? "Traitement en cours..." : "Enrôler l'étudiant"}
          </button>
        </form>
      </div>
    </div>
  );
};

const styles = {
  container: { maxWidth: "560px", margin: "40px auto", padding: "20px" },
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: "24px",
    overflow: "hidden",
    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.15)",
    border: `1px solid ${COLORS.border}`
  },
  header: {
    background: `linear-gradient(135deg, ${COLORS.primary} 0%, #3B82F6 100%)`,
    padding: "28px 35px",
    color: "white"
  },
  title: { margin: 0, fontSize: "28px", fontWeight: "700", textAlign: "center" },
  form: { padding: "35px", display: "flex", flexDirection: "column", gap: "20px" },
  input: {
    padding: "15px 18px",
    borderRadius: "12px",
    border: `1px solid ${COLORS.border}`,
    fontSize: "15.5px",
    outline: "none",
    backgroundColor: "#F8FAFC"
  },
  selectRow: { display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: "16px" },
  select: {
    padding: "15px 18px",
    borderRadius: "12px",
    border: `1px solid ${COLORS.border}`,
    fontSize: "15.5px",
    backgroundColor: "#F8FAFC",
    outline: "none"
  },

  /* === Champ fichier personnalisé === */
  fileUploadArea: {
    textAlign: "center"
  },
  fileLabel: {
    display: "block",
    padding: "20px 24px",
    border: `2px dashed ${COLORS.accent}`,
    borderRadius: "16px",
    backgroundColor: "#F0FDF4",
    cursor: "pointer",
    transition: "all 0.3s ease",
    fontSize: "16px",
    fontWeight: "600",
    color: COLORS.accent
  },
  uploadIcon: {
    display: "block",
    fontSize: "28px",
    marginBottom: "8px"
  },
  hiddenInput: {
    display: "none"
  },
  fileName: {
    marginTop: "10px",
    fontSize: "14px",
    color: COLORS.textMuted,
    fontWeight: "500"
  },

  previewWrapper: {
    borderRadius: "16px",
    overflow: "hidden",
    boxShadow: "0 15px 25px -5px rgba(16, 185, 129, 0.2)",
    border: `2px solid ${COLORS.accentLight}`
  },
  preview: { width: "100%", height: "auto", display: "block" },

  button: {
    marginTop: "10px",
    padding: "18px",
    fontSize: "17px",
    fontWeight: "600",
    border: "none",
    borderRadius: "14px",
    background: `linear-gradient(135deg, ${COLORS.primary} 0%, #2563EB 100%)`,
    color: "white",
    cursor: "pointer",
    transition: "all 0.3s ease",
    boxShadow: "0 10px 15px -3px rgba(30, 64, 175, 0.3)"
  },
  message: {
    padding: "16px 20px",
    borderRadius: "12px",
    fontSize: "15.5px",
    fontWeight: "500",
    marginBottom: "10px"
  },

  
  fileCount: {
    marginTop: "10px",
    fontSize: "15px",
    color: COLORS.accent,
    fontWeight: "600"
  },

  previewsContainer: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
    gap: "15px",
    marginBottom: "20px"
  },

  previewItem: {
    position: "relative",
    borderRadius: "12px",
    overflow: "hidden",
    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
    border: `2px solid ${COLORS.accentLight}`
  },

  removeButton: {
    position: "absolute",
    top: "5px",
    right: "5px",
    width: "28px",
    height: "28px",
    padding: 0,
    border: "none",
    borderRadius: "50%",
    backgroundColor: COLORS.danger,
    color: "white",
    fontSize: "16px",
    fontWeight: "bold",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.2s",
    opacity: 0.8
  },

  photoLabel: {
    position: "absolute",
    bottom: "5px",
    left: "5px",
    right: "5px",
    margin: 0,
    padding: "3px 6px",
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    color: "white",
    fontSize: "12px",
    borderRadius: "4px",
    textAlign: "center"
  }
};

export default Enrollment;