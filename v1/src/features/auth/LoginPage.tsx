import React, { FormEvent, useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowRight, Loader2, Scale, ShieldCheck } from 'lucide-react';
import { exchangeLaunchToken, loginV1, saveSession, V1AuthResult } from '../../core/api';

interface LoginPageProps {
  onAuthenticated: (result: V1AuthResult) => void;
}

type LoginStep = 'idle' | 'loading' | 'error';

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [step, setStep]         = useState<LoginStep>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const emailRef = useRef<HTMLInputElement>(null);

  // ── SSO exchange: if a launch token arrives via URL ?lt=… or #lt=… ──────────
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace('#', ''));
    const launchToken = params.get('lt') ?? hashParams.get('lt');

    if (!launchToken) return;

    // Remove the token from the URL immediately so it is not bookmarkable.
    const clean = window.location.pathname + window.location.hash.replace(/lt=[^&]+&?/, '');
    window.history.replaceState(null, '', clean);

    setStep('loading');
    exchangeLaunchToken(launchToken)
      .then((result) => {
        saveSession(result.access_token, result.user);
        onAuthenticated(result);
      })
      .catch((err: Error) => {
        setStep('error');
        setErrorMsg(err.message || 'Launch token exchange failed. Please log in manually.');
      });
  }, [onAuthenticated]);

  useEffect(() => {
    emailRef.current?.focus();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) return;

    setStep('loading');
    setErrorMsg('');

    try {
      const result = await loginV1(email.trim(), password);
      saveSession(result.access_token, result.user);
      onAuthenticated(result);
    } catch (err) {
      setStep('error');
      setErrorMsg((err as Error).message || 'Login failed. Please try again.');
    }
  }

  const isLoading = step === 'loading';

  return (
    <div className="login-shell">
      <div className="login-card">

        {/* Brand */}
        <div className="login-brand">
          <div className="login-brand-mark">V</div>
          <div>
            <strong>VIDHI AI</strong>
            <span>V1.0 Beta</span>
          </div>
        </div>

        <div className="login-divider" />

        {/* Heading */}
        <div className="login-heading">
          <h1>Sign in to Beta</h1>
          <p>Access the V1 matter workspace and Case Agent.</p>
        </div>

        {/* Error banner */}
        {step === 'error' && (
          <div className="login-error" role="alert">
            <AlertCircle size={15} />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Exchange loading state */}
        {isLoading && email === '' && (
          <div className="login-exchange-notice">
            <Loader2 size={16} className="spin" />
            <span>Authenticating via launch token…</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate>
          <div className="login-field">
            <label htmlFor="v1-email">Email address</label>
            <input
              id="v1-email"
              ref={emailRef}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@firm.com"
              disabled={isLoading}
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="v1-password">Password</label>
            <input
              id="v1-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={isLoading}
              required
            />
          </div>

          <button
            type="submit"
            className="login-submit"
            disabled={isLoading || !email.trim() || !password}
          >
            {isLoading ? (
              <>
                <Loader2 size={15} className="spin" />
                Signing in…
              </>
            ) : (
              <>
                Sign in
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {/* Footer trust signals */}
        <div className="login-footer">
          <Scale size={13} />
          <span>Indian Legal AI · Beta access only</span>
          <span className="login-footer-dot" />
          <ShieldCheck size={13} />
          <span>Encrypted session</span>
        </div>

      </div>
    </div>
  );
}
