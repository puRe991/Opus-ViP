const form = document.querySelector('#analyze-form');
const clipsEl = document.querySelector('#clips');
const errorEl = document.querySelector('#error');
const exportBtn = document.querySelector('#export');
let currentProject = null;

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorEl.textContent = '';
  clipsEl.className = 'clips empty';
  clipsEl.textContent = 'Analyse läuft …';
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.querySelector('#name').value,
        targetDuration: Number(document.querySelector('#duration').value),
        transcript: document.querySelector('#transcript').value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Analyse fehlgeschlagen');
    currentProject = payload;
    renderClips(payload.clips || []);
    exportBtn.disabled = false;
  } catch (error) {
    clipsEl.className = 'clips empty';
    clipsEl.textContent = 'Keine Ergebnisse.';
    errorEl.textContent = error.message;
    exportBtn.disabled = true;
  }
});

exportBtn.addEventListener('click', () => {
  if (!currentProject) return;
  const blob = new Blob([JSON.stringify(currentProject, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement('a'), { href: url, download: `${currentProject.id}.json` });
  link.click();
  URL.revokeObjectURL(url);
});

function renderClips(clips) {
  if (!clips.length) {
    clipsEl.className = 'clips empty';
    clipsEl.textContent = 'Keine geeigneten Clip-Kandidaten gefunden.';
    return;
  }
  clipsEl.className = 'clips';
  clipsEl.innerHTML = clips.map((clip) => `
    <article class="clip">
      <header><div><p class="time">${formatTime(clip.start)}–${formatTime(clip.end)} · ${clip.duration}s</p><h3>${escapeHtml(clip.title)}</h3></div><div class="score" style="--score:${clip.score}">${clip.score}</div></header>
      <p class="hook">${escapeHtml(clip.hook)}</p>
      <ul class="rationale">${clip.rationale.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    </article>`).join('');
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
  const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${mins}:${secs}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}
