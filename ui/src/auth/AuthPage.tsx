import React, { useState } from 'react';
import { LogIn, ShieldCheck, UserPlus } from 'lucide-react';

type AuthMode = 'login' | 'register';

export interface AuthFormValue {
  fullName: string;
  email: string;
  password: string;
}

interface AuthPageProps {
  onSubmit: (mode: AuthMode, value: AuthFormValue) => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
}

export const AuthPage: React.FC<AuthPageProps> = ({ onSubmit, isSubmitting, error }) => {
  const [mode, setMode] = useState<AuthMode>('login');
  const [form, setForm] = useState<AuthFormValue>({
    fullName: '',
    email: '',
    password: '',
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleChange = (key: keyof AuthFormValue, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleModeChange = (nextMode: AuthMode) => {
    setMode(nextMode);
    setLocalError(null);
    setConfirmPassword('');
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);

    if (mode === 'register' && form.password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    await onSubmit(mode, form);
  };

  return (
    <div className="min-h-screen bg-surface text-on-surface" data-theme="dark">
      <div className="atmosphere" />
      <div className="atmosphere-glow" />
      <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4 py-10">
        <div className="grid w-full max-w-5xl gap-8 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="flex flex-col justify-center rounded-[28px] border border-outline-variant/60 bg-surface-container-low/80 p-8 shadow-ambient backdrop-blur-xl md:p-10">
            <div className="status-pill mb-5 w-fit">
              <ShieldCheck size={14} />
              Encrypted legal chat workspace
            </div>
            <h1 className="mb-4 text-4xl font-semibold tracking-tight text-on-surface">
              Secure legal sessions with account-based chat history.
            </h1>
            <p className="max-w-xl text-base leading-7 text-on-surface-variant">
              Sign in to revisit earlier chats, start fresh sessions from the sidebar, and keep
              stored conversations encrypted in the backend.
            </p>
          </section>

          <section className="glass-panel rounded-[28px] p-6 md:p-8">
            <div className="mb-6 flex rounded-2xl border border-outline-variant/70 bg-surface-container-low p-1">
              <button
                type="button"
                onClick={() => handleModeChange('login')}
                className={[
                  'flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition',
                  mode === 'login'
                    ? 'bg-primary text-on-primary shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface',
                ].join(' ')}
              >
                Login
              </button>
              <button
                type="button"
                onClick={() => handleModeChange('register')}
                className={[
                  'flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition',
                  mode === 'register'
                    ? 'bg-primary text-on-primary shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface',
                ].join(' ')}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {mode === 'register' && (
                <div>
                  <label className="field-label">Full name</label>
                  <input
                    className="text-field"
                    value={form.fullName}
                    onChange={(event) => handleChange('fullName', event.target.value)}
                    placeholder="Aarav Sharma"
                    autoComplete="name"
                    required
                  />
                </div>
              )}

              <div>
                <label className="field-label">Email</label>
                <input
                  type="email"
                  className="text-field"
                  value={form.email}
                  onChange={(event) => handleChange('email', event.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </div>

              <div>
                <label className="field-label">Password</label>
                <input
                  type="password"
                  className="text-field"
                  value={form.password}
                  onChange={(event) => handleChange('password', event.target.value)}
                  placeholder="Minimum 8 characters"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  required
                />
              </div>

              {mode === 'register' && (
                <div>
                  <label className="field-label">Re-enter password</label>
                  <input
                    type="password"
                    className="text-field"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Re-enter your password"
                    autoComplete="new-password"
                    required
                  />
                </div>
              )}

              {localError || error ? (
                <div className="rounded-2xl border border-error/40 bg-error/10 px-4 py-3 text-sm text-error">
                  {localError || error}
                </div>
              ) : null}

              <button type="submit" className="primary-button w-full" disabled={isSubmitting}>
                {mode === 'login' ? <LogIn size={16} /> : <UserPlus size={16} />}
                {isSubmitting ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
};
