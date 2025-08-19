(() => {
  const $ = (q) => document.querySelector(q);
  const apiBaseInput = $('#api-base-url');
  const saveApiBtn = $('#save-api-url');
  const healthBtn = $('#btn-health');
  const healthStatus = $('#health-status');
  const regEmail = $('#reg-email');
  const regUsername = $('#reg-username');
  const regPassword = $('#reg-password');
  const btnRegister = $('#btn-register');
  const loginEmail = $('#login-email');
  const loginPassword = $('#login-password');
  const btnLogin = $('#btn-login');
  const apiKeyInput = $('#api-key');
  const saveApiKeyBtn = $('#save-api-key');
  const clearApiKeyBtn = $('#clear-api-key');
  const modelSelect = $('#model-select');
  const refreshModelsBtn = $('#refresh-models');
  const promptEl = $('#prompt');
  const btnGenerate = $('#btn-generate');
  const genStatus = $('#gen-status');
  const output = $('#output');
  const maxTokens = $('#max-tokens');
  const temperature = $('#temperature');
  const topP = $('#top-p');
  const btnUsage = $('#btn-usage');
  const usage = $('#usage');

  const state = {
    apiBase: localStorage.getItem('apiBase') || 'http://localhost:8000',
    apiKey: localStorage.getItem('apiKey') || ''
  };

  function setApiBase(v){
    state.apiBase = v.trim();
    localStorage.setItem('apiBase', state.apiBase);
    apiBaseInput.value = state.apiBase;
  }
  function setApiKey(v){
    state.apiKey = v.trim();
    localStorage.setItem('apiKey', state.apiKey);
    apiKeyInput.value = state.apiKey;
  }

  setApiBase(state.apiBase);
  setApiKey(state.apiKey);

  async function api(path, opts = {}){
    const url = state.apiBase.replace(/\/$/, '') + path;
    const headers = Object.assign(
      { 'Content-Type': 'application/json' },
      state.apiKey ? { 'Authorization': `Bearer ${state.apiKey}` } : {},
      opts.headers || {}
    );
    const res = await fetch(url, { ...opts, headers });
    const text = await res.text();
    let json = null;
    try { json = text ? JSON.parse(text) : null; } catch {}
    if (!res.ok) {
      throw new Error(json && json.detail ? json.detail : `${res.status} ${res.statusText}`);
    }
    return json;
  }

  async function refreshModels(){
    try {
      const data = await api('/api/v1/models');
      const models = data.models || [];
      modelSelect.innerHTML = '';
      for(const m of models){
        const opt = document.createElement('option');
        opt.value = m.id || m.name || m;
        opt.textContent = m.display_name || m.name || m.id || m;
        modelSelect.appendChild(opt);
      }
    } catch (e){
      console.error(e);
      alert('Failed to fetch models: ' + e.message);
    }
  }

  async function checkHealth(){
    healthStatus.textContent = 'Checking...';
    try {
      const h = await api('/health');
      healthStatus.textContent = `Status: ${h.status} • v${h.version}`;
    } catch(e){
      healthStatus.textContent = `Status: error • ${e.message}`;
    }
  }

  async function doRegister(){
    btnRegister.disabled = true;
    try{
      const body = {
        email: regEmail.value.trim(),
        username: regUsername.value.trim(),
        password: regPassword.value
      };
      const r = await api('/auth/register', { method:'POST', body: JSON.stringify(body) });
      if (r.api_key) setApiKey(r.api_key);
      alert('Registered. API key saved.');
    } catch(e){
      alert('Register failed: ' + e.message);
    } finally {
      btnRegister.disabled = false;
    }
  }

  async function doLogin(){
    btnLogin.disabled = true;
    try{
      const body = { email: loginEmail.value.trim(), password: loginPassword.value };
      const r = await api('/auth/login', { method:'POST', body: JSON.stringify(body) });
      if (r.api_key) setApiKey(r.api_key);
      alert('Login success. API key saved.');
    } catch(e){
      alert('Login failed: ' + e.message);
    } finally {
      btnLogin.disabled = false;
    }
  }

  async function doGenerate(){
    output.textContent = '';
    genStatus.textContent = 'Generating...';
    btnGenerate.disabled = true;
    try{
      const body = {
        prompt: promptEl.value,
        max_tokens: Number(maxTokens.value) || 256,
        temperature: Number(temperature.value) || 0.7,
        top_p: Number(topP.value) || 0.9,
        model: modelSelect.value || undefined
      };
      const r = await api('/api/v1/generate', { method:'POST', body: JSON.stringify(body) });
      output.textContent = r.text || '';
      genStatus.textContent = `Model: ${r.model} • Provider: ${r.provider}`;
    } catch(e){
      genStatus.textContent = 'Error';
      alert('Generation failed: ' + e.message);
    } finally{
      btnGenerate.disabled = false;
    }
  }

  async function fetchUsage(){
    usage.textContent = 'Loading...';
    try{
      const r = await api('/api/v1/usage');
      usage.textContent = JSON.stringify(r, null, 2);
    } catch(e){
      usage.textContent = 'Error: ' + e.message;
    }
  }

  // Wire up events
  saveApiBtn.addEventListener('click', () => setApiBase(apiBaseInput.value));
  healthBtn.addEventListener('click', checkHealth);
  btnRegister.addEventListener('click', doRegister);
  btnLogin.addEventListener('click', doLogin);
  saveApiKeyBtn.addEventListener('click', () => setApiKey(apiKeyInput.value));
  clearApiKeyBtn.addEventListener('click', () => setApiKey(''));
  refreshModelsBtn.addEventListener('click', refreshModels);
  btnGenerate.addEventListener('click', doGenerate);
  btnUsage.addEventListener('click', fetchUsage);

  // Initial
  apiBaseInput.value = state.apiBase;
  apiKeyInput.value = state.apiKey;
  refreshModels();
  checkHealth();
})();


