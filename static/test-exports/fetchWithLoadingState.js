// Standalone test export for fetchWithLoadingState (no optional chaining, no external deps)
export async function fetchWithLoadingState(url, options = {}, buttonElOrId = null) {
  let btn = null;
  if (typeof buttonElOrId === 'string' && typeof document !== 'undefined') {
    btn = document.getElementById(buttonElOrId);
  } else if (buttonElOrId && buttonElOrId.nodeType === 1) {
    btn = buttonElOrId;
  }
  try {
    if (btn) {
      btn.setAttribute('data-loading', 'true');
      btn.disabled = true;
    }
    const response = await fetch(url, options);
    let data = {};
    try { data = await response.json(); } catch (e) { data = {}; }
    if (!response.ok) {
      throw new Error((data && data.message) || ('Erreur HTTP ' + response.status));
    }
    return data;
  } finally {
    if (btn) {
      btn.removeAttribute('data-loading');
      btn.disabled = false;
    }
  }
}
