import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { setAuthToken } from '../api/client';
import type { AuthState } from '../types';

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
  });

  useEffect(() => {
    // Check if user is already logged in
    const storedAuth = localStorage.getItem('auth');
    if (storedAuth) {
      try {
        const auth = JSON.parse(storedAuth);
        setAuthState(auth);
        setAuthToken(auth.token);
      } catch (e) {
        localStorage.removeItem('auth');
      }
    }
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    // Simple auth for local development
    // In production, this would call your auth API
    if (username === 'admin' && password === 'admin') {
      const auth = {
        isAuthenticated: true,
        user: username,
        token: 'local-dev-token', // In production, this would come from the API
      };
      setAuthState({
        isAuthenticated: true,
        user: username,
      });
      localStorage.setItem('auth', JSON.stringify(auth));
      setAuthToken(auth.token);
      return true;
    }
    return false;
  };

  const logout = () => {
    setAuthState({
      isAuthenticated: false,
      user: null,
    });
    localStorage.removeItem('auth');
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider value={{ ...authState, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
