/**
 * frontend/src/auth_service.js - VERSION COMPLÈTE ET À JOUR
 * ✅ EXPORT API INSTANCE (FIX CRITIQUE)
 * Gère l'authentification JWT complète
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';

// ✅ INSTANCE AXIOS - À EXPORTER!
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

// Interceptors
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log(`📤 [${config.method?.toUpperCase()}] ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => {
    console.log(`✅ [${response.status}] ${response.config.url}`);
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.clear();
      window.location.href = '/';
    }
    console.error('❌ API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

class AuthService {
  /**
   * ============ LOGIN ============
   */
  async login(username, password) {
    try {
      console.log('🔐 [AUTH] Login attempt:', { username });

      const response = await api.post('/auth/login/', {
        username,
        password
      });

      console.log('✅ [AUTH] Login successful!', response.data);

      const { access, refresh, user } = response.data;

      localStorage.setItem(ACCESS_TOKEN_KEY, access);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

      return { 
        success: true, 
        user 
      };
    } catch (error) {
      const errorMsg = error.response?.data?.error || 
                       error.response?.data?.message || 
                       error.message || 
                       'Login failed';
      
      console.error('❌ [AUTH] Login failed:', errorMsg);
      
      return {
        success: false,
        error: errorMsg
      };
    }
  }

  /**
   * ============ REGISTER ============
   */
  async register(username, email, password, passwordConfirm, firstName = '') {
    try {
      console.log('🆕 [AUTH] Registration attempt:', { username, email });

      if (password !== passwordConfirm) {
        return {
          success: false,
          error: 'Passwords do not match'
        };
      }

      if (password.length < 8) {
        return {
          success: false,
          error: 'Password must be at least 8 characters'
        };
      }

      const response = await api.post('/auth/register/', {
        username,
        email,
        password,
        password_confirm: passwordConfirm,
        first_name: firstName
      });

      console.log('✅ [AUTH] Registration successful!', response.data);

      const { access, refresh, user } = response.data;

      localStorage.setItem(ACCESS_TOKEN_KEY, access);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

      return { 
        success: true, 
        user 
      };
    } catch (error) {
      const errorMsg = error.response?.data?.error || 
                       error.response?.data?.message || 
                       error.message || 
                       'Registration failed';
      
      console.error('❌ [AUTH] Registration failed:', errorMsg);
      
      return {
        success: false,
        error: errorMsg
      };
    }
  }

  /**
   * ============ LOGOUT ============
   */
  async logout() {
    try {
      console.log('🚪 [AUTH] Logout attempt...');

      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

      if (refreshToken) {
        try {
          await api.post('/auth/logout/', {
            refresh: refreshToken
          });
        } catch (err) {
          console.warn('⚠️ [AUTH] Logout notification failed', err.message);
        }
      }

      this.clearAuth();
      
      console.log('✅ [AUTH] Logout successful!');
      
      return { success: true };
    } catch (error) {
      console.error('❌ [AUTH] Logout error:', error.message);
      this.clearAuth();
      return { success: true };
    }
  }

  /**
   * ============ REFRESH TOKEN ============
   */
  async refreshToken() {
    try {
      console.log('🔄 [AUTH] Refreshing token...');

      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

      if (!refreshToken) {
        console.warn('⚠️ [AUTH] No refresh token found');
        this.clearAuth();
        return { success: false };
      }

      const response = await api.post('/auth/refresh/', {
        refresh: refreshToken
      });

      console.log('✅ [AUTH] Token refreshed!');

      const { access } = response.data;

      localStorage.setItem(ACCESS_TOKEN_KEY, access);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

      return { 
        success: true, 
        access 
      };
    } catch (error) {
      console.error('❌ [AUTH] Token refresh failed:', error.message);
      this.clearAuth();
      return { success: false };
    }
  }

  /**
   * ============ GET CURRENT USER ============
   */
  async getCurrentUser() {
    try {
      console.log('👤 [AUTH] Fetching current user...');

      const response = await api.get('/auth/me/');
      
      console.log('✅ [AUTH] Current user fetched!');
      
      return response.data;
    } catch (error) {
      console.error('❌ [AUTH] Get current user failed:', error.message);
      return null;
    }
  }

  /**
   * ============ TOKEN MANAGEMENT ============
   */
  getToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  isAuthenticated() {
    return !!localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  getUser() {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  }

  setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  /**
   * ============ CLEANUP ============
   */
  clearAuth() {
    console.log('🗑️ [AUTH] Clearing auth data...');
    
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    
    delete api.defaults.headers.common['Authorization'];
  }

  /**
   * ============ INITIALIZATION ============
   */
  initialize() {
    console.log('⚙️ [AUTH] Initializing auth service...');

    const token = this.getToken();
    const user = this.getUser();

    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      console.log('✅ [AUTH] Token restored from storage');
    }

    if (user) {
      console.log(`✅ [AUTH] User restored: ${user.username}`);
    }

    return {
      isAuthenticated: !!token,
      user
    };
  }

  /**
   * ============ TOKEN EXPIRY CHECK ============
   */
  isTokenExpired() {
    try {
      const token = this.getToken();
      if (!token) return true;

      const parts = token.split('.');
      if (parts.length !== 3) return true;

      const payload = JSON.parse(atob(parts[1]));
      const expirationTime = payload.exp * 1000;

      return Date.now() >= expirationTime;
    } catch (error) {
      console.error('Error checking token expiry:', error);
      return true;
    }
  }

  /**
   * ============ ENSURE AUTHENTICATED ============
   */
  async ensureAuthenticated() {
    const isAuth = this.isAuthenticated();
    
    if (!isAuth) {
      return { authenticated: false, user: null };
    }

    if (this.isTokenExpired()) {
      console.warn('⚠️ [AUTH] Token expired, attempting refresh...');
      const result = await this.refreshToken();
      if (!result.success) {
        return { authenticated: false, user: null };
      }
    }

    const user = this.getUser() || await this.getCurrentUser();
    return { 
      authenticated: true, 
      user 
    };
  }
}

export default new AuthService();