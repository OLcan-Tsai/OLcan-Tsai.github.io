(() => {
  'use strict';

  const ENDPOINT = 'https://olcan-pulse-collector.tlcon2006.chatgpt.site/api/collect';
  const VISITOR_KEY = 'pulse_visitor_id';
  const SESSION_KEY = 'pulse_session_id';
  const HEARTBEAT_SECONDS = 15;

  if (navigator.doNotTrack === '1' || window.doNotTrack === '1') return;

  function randomId(prefix) {
    try {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      const value = btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
      return `${prefix}_${value}`;
    } catch {
      return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 14)}`;
    }
  }

  function storedId(storage, key, prefix) {
    try {
      let value = storage.getItem(key);
      if (!value) {
        value = randomId(prefix);
        storage.setItem(key, value);
      }
      return value;
    } catch {
      return randomId(prefix);
    }
  }

  const visitorId = storedId(localStorage, VISITOR_KEY, 'v');
  const sessionId = storedId(sessionStorage, SESSION_KEY, 's');
  let eventId = '';
  let activeSeconds = 0;
  let lastPath = '';

  function payload(type) {
    return {
      type,
      eventId,
      visitorId,
      sessionId,
      path: `${location.pathname}${location.search}`.slice(0, 300),
      title: document.title.slice(0, 240),
      referrer: document.referrer,
      language: navigator.language,
      screenWidth: window.screen?.width || window.innerWidth || 0,
      duration: activeSeconds,
    };
  }

  function send(body, beacon = false) {
    const data = JSON.stringify(body);
    if (beacon && navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([data], { type: 'text/plain;charset=UTF-8' }));
      return;
    }
    fetch(ENDPOINT, {
      method: 'POST',
      mode: 'cors',
      cache: 'no-store',
      keepalive: true,
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      body: data,
    }).catch(() => {});
  }

  function heartbeat(beacon = false) {
    if (!eventId) return;
    send(payload('heartbeat'), beacon);
  }

  function trackPage() {
    const path = `${location.pathname}${location.search}`;
    if (path === lastPath) return;
    if (eventId) heartbeat(true);
    lastPath = path;
    eventId = randomId('e');
    activeSeconds = 0;
    send(payload('pageview'));
  }

  setInterval(() => {
    if (document.visibilityState !== 'visible') return;
    activeSeconds += HEARTBEAT_SECONDS;
    heartbeat();
  }, HEARTBEAT_SECONDS * 1000);

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') heartbeat(true);
  });
  window.addEventListener('pagehide', () => heartbeat(true));
  window.addEventListener('popstate', () => setTimeout(trackPage, 0));
  document.addEventListener('pjax:complete', () => setTimeout(trackPage, 0));

  trackPage();
})();
