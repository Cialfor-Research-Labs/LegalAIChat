function getDefaultApiBase(): string {
  const { protocol, hostname } = window.location;
  const isLocalBrowser = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '';

  if (isLocalBrowser) {
    return 'http://localhost:9001';
  }

  const resolvedProtocol = protocol === 'https:' ? 'https:' : 'http:';
  return `${resolvedProtocol}//${hostname}/tllac-api`;
}

function getApiBase(): string {
  const configuredBase = import.meta.env.VITE_V1_API_BASE?.trim();
  if (!configuredBase) {
    return getDefaultApiBase();
  }

  const backendOrigin = `${window.location.protocol}//${window.location.hostname}`;
  return new URL(configuredBase, backendOrigin).toString().replace(/\/$/, '');
}

export const betaConfig = {
  label: 'V1.0 Beta',
  releaseStage: 'Beta',
  dataMode: 'Secure matter workspace — connected to V1 backend',
  apiBase: getApiBase(),
} as const;
