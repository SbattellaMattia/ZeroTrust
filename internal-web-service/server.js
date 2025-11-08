const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;

// Profilo demo in memoria (non persistente)
const profile = {
  name: "Demo",
  bio: "Profilo demo"
};

// Parsing JSON per richieste API
app.use(express.json());

// Middleware: estrazione header da OPA / Envoy
app.use((req, res, next) => {
  // Legge i valori passati da OPA tramite Envoy
  const lvl = (req.get('x-access-level') || process.env.DEFAULT_ACCESS_LEVEL || 'limited').toLowerCase();
  const user = req.get('x-user') || process.env.DEFAULT_USER || 'demo';
  const score = req.get('x-score') || process.env.DEFAULT_SCORE || '';
  const roles = req.get('x-roles') ? req.get('x-roles').split(',') : [];

  // Legge IP reale dal nuovo header x-src-ip (inviato da OPA)
  const ip = req.get('x-src-ip') || req.socket.remoteAddress;

  req.access = {
    level: lvl === 'full' ? 'full' : 'limited',
    canEdit: lvl === 'full',
    user,
    score,
    ip,
    roles
  };

  next();
});

// Servizio statico (frontend)
app.use(express.static(path.join(__dirname, 'public')));

// Endpoint: lettura profilo
app.get('/api/profile', (req, res) => {
  res.json({
    user: req.access.user,
    roles: req.access.roles,
    ip: req.access.ip,
    accessLevel: req.access.level,
    canEdit: req.access.canEdit,
    bio: profile.bio,
    score: req.access.score
  });
});

// Endpoint diagnostico (utile per debugging)
app.get('/api/echo', (req, res) => {
  res.json({
    access: req.access,   // { user, roles, ip, level, canEdit, score }
    headers: req.headers  // Tutti gli header HTTP ricevuti
  });
});

// Endpoint: modifica bio (consentita solo con accesso "full")
app.put('/api/profile', (req, res) => {
  if (!req.access.canEdit) {
    return res.status(403).json({ error: 'Forbidden: limited access' });
  }

  const ct = (req.headers['content-type'] || '').toLowerCase();
  if (!ct.startsWith('application/json')) {
    return res.status(415).json({ error: 'Unsupported Media Type: use application/json' });
  }

  const { bio } = req.body || {};
  if (typeof bio !== 'string' || bio.length === 0 || bio.length > 500) {
    return res.status(400).json({ error: 'Invalid bio' });
  }

  profile.bio = bio;
  return res.json({
    ok: true,
    user: req.access.user,
    accessLevel: req.access.level,
    bio: profile.bio
  });
});

// Health check
app.get('/healthz', (_req, res) => res.status(200).send('ok'));

// Avvio server
app.listen(PORT, () => {
  console.log(`internal-service listening on ${PORT}`);
});