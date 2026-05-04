/**
 * frontend/src/api_service.js - SERVICE API ALIGNÉ
 * Synchronisé avec StudentViewSet et AttendanceViewSet (urls_complete.py)
 */

import { api } from './auth_service';

/**
 * ======================
 * UTILS
 * ======================
 */

/**
 * Nettoyage robuste du Base64
 */
const cleanBase64 = (base64String) => {
  if (!base64String) return '';
  const commaIndex = base64String.indexOf(',');
  return commaIndex !== -1 
    ? base64String.substring(commaIndex + 1) 
    : base64String;
};

/**
 * Extracteur d'erreurs uniforme
 */
const getErrorMessage = (error, fallback) => {
  return (
    error?.response?.data?.error ||
    error?.response?.data?.message ||
    error?.message ||
    fallback
  );
};

/**
 * ======================
 * STUDENTS API
 * ======================
 */
export const studentsAPI = {
  /**
   * Enroll student from image
   * Route: POST /api/students/enroll_from_image/
   */

  enrollFromImage: async (name, email, files, level, filiere) => {
    try {
      // Accepter fichier unique ou array de fichiers
      const fileArray = Array.isArray(files) ? files : [files];
      
      // Convertir tous les fichiers en base64
      const imagesBase64 = await Promise.all(
        fileArray.map((file) => 
          new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
          })
        )
      );

      console.log(`[STUDENTS][ENROLL] Processing ${imagesBase64.length} image(s)`);

      const response = await api.post('/students/enroll_from_image/', {
        name,
        email: email || '',
        level,          
        filiere,        
        images_base64: imagesBase64.map(cleanBase64),  // ✅ ARRAY de photos
      });

      console.log('[STUDENTS][ENROLL] Success:', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      const errorMsg = getErrorMessage(error, 'Enrollment failed');
      console.error('[STUDENTS][ENROLL] Error:', errorMsg);
      return { success: false, error: errorMsg };
    }
  },


  /**
   * Get all students
   * Route: GET /api/students/
   */
  getAll: async () => {
    try {
      const response = await api.get('/students/');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: getErrorMessage(error, 'Failed to fetch students') };
    }
  },

  /**
   * Search students
   * Route: POST /api/students/search/
   */
  search: async (query) => {
    try {
      const response = await api.post('/students/search/', { query });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: getErrorMessage(error, 'Search failed') };
    }
  },

  /**
   * Get student stats
   * Route: GET /api/students/stats/
   */
  getStats: async () => {
    try {
      const response = await api.get('/students/stats/');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: getErrorMessage(error, 'Failed to fetch stats') };
    }
  },
};

/**
 * ======================
 * ATTENDANCE API
 * ======================
 */
export const attendanceAPI = {
  /**
   * Recognize face from image
   * Route: POST /api/attendance/recognize/
   */
  recognize: async (imageBase64) => {
    try {
      const response = await api.post('/attendance/recognize/', {
        image_base64: cleanBase64(imageBase64),
      });
      console.log('[ATTENDANCE][RECOGNIZE] Success:', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      // Cas 404 (Inconnu) géré par views_optimized.py
      if (error.response?.status === 404) {
        console.warn('[ATTENDANCE][RECOGNIZE] No match');
        return {
          success: false,
          isNoMatch: true,
          data: error.response.data,
        };
      }
      return { success: false, error: getErrorMessage(error, 'Recognition error') };
    }
  },

  /**
   * Get today's attendance log
   * Route: GET /api/attendance/
   */
  getTodayLog: async () => {
    try {
      const response = await api.get('/attendance/');
      return response.data;   // ← renvoie directement l'objet du backend
    } catch (error) {
      return { success: false, error: getErrorMessage(error, 'Failed to fetch log') };
    }
  },

  /**
   * Get attendance stats
   * Route: GET /api/attendance/stats/
   */
  getStats: async () => {
    try {
      const response = await api.get('/attendance/stats/');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: getErrorMessage(error, 'Failed to fetch stats') };
    }
  },

  /**
   * Get attendance status (Present/Absent)
   * Route: GET /api/attendance/status/
   */
  getStatus: async () => {
    try {
      const response = await api.get('/attendance/status/');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: getErrorMessage(error, 'Failed to fetch status') };
    }
  },

  /**
   * Get student attendance history
   * Route: GET /api/attendance/student_history/
   */
  getHistory: async (studentId, days = 30) => {
    try {
      const response = await api.get('/attendance/student_history/', {
        params: { student_id: studentId, days },
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: getErrorMessage(error, 'Failed to fetch history') };
    }
  },
  /**
   * Set manual attendance (Prof manually marks student present/absent)
   * Route: POST /api/attendance/manual_attendance/
   */
  manualAttendance: async (studentId, isPresent) => {
    try {
      const response = await api.post('/attendance/manual_attendance/', {
        student_id: studentId,
        is_present: isPresent,
      });
      console.log('[ATTENDANCE][MANUAL]', isPresent ? 'PRESENT' : 'ABSENT', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      const errorMsg = getErrorMessage(error, 'Failed to set attendance');
      console.error('[ATTENDANCE][MANUAL] Error:', errorMsg);
      return { success: false, error: errorMsg };
    }
  },

};

export default {
  studentsAPI,
  attendanceAPI,
};