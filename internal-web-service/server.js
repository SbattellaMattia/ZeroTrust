const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;

// Demo in-memory profile
const profile = {
  name: "Demo",
  bio: "Profilo demo"
};

// JSON only for state changes to reduce CSRF surface (no urlencoded forms)
app.use(express.json());

app.use((req, res, next) => {
  // Headers forwarded by Envoy from OPA
  const lvl = (req.get('x-access-level') || process.env.DEFAULT_ACCESS_LEVEL || 'limited').toLowerCase();
  const user = req.get('x-user') || process.env.DEFAULT_USER || 'demo';
  const score = req.get('x-score') || process.env.DEFAULT_SCORE || '';

  req.access = {
    level: lvl === 'full' ? 'full' : 'limited',
    canEdit: lvl === 'full',
    user,
    score
  };
  next();
});

// Static UI
app.use(express.static(path.join(__dirname, 'public')));

// Profile read - restituisce user, access level e bio
app.get('/api/profile', (req, res) => {
  res.json({
    user: req.access.user,
    accessLevel: req.access.level,
    canEdit: req.access.canEdit,
    bio: profile.bio,
    score: req.access.score,
  });
});

// Endpoint di diagnostica: restituisce gli header e l'access calcolato
app.get('/api/echo', (req, res) => {
  res.json({
    access: req.access,           // { level, canEdit, user }
    headers: req.headers          // tutti i request headers visti dall'app
  });
});

// Profile update (only if full and Content-Type: application/json)
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

// Health
app.get('/healthz', (_req, res) => res.status(200).send('ok'));

app.listen(PORT, () => {
  console.log(`internal-service listening on ${PORT}`);
});
