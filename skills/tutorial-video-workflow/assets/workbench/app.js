const $ = (selector) => document.querySelector(selector);
const player = $('#player');
let state = null;
let history = [];
let future = [];
let selectedId = null;
let selectedWords = new Set();
let saveTimer = null;
let currentIndex = 0;
let pixelsPerSecond = 20;

const clone = (value) => JSON.parse(JSON.stringify(value));
const fmt = (seconds) => {
  const value = Math.max(0, Number(seconds) || 0);
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${(value % 60).toFixed(2).padStart(5, '0')}`;
};
const clipDuration = (clip) => (clip.sourceEnd - clip.sourceStart) / (clip.speed || 1);
const activeVideo = () => state.tracks.video.filter((clip) => clip.enabled !== false);
function excludedRangesFor(clip) {
  if (clip.assetId !== state.transcript.assetId) return [];
  const ranges = [
    ...state.transcript.segments.filter((segment) => segment.deleted).map((segment) => [segment.start, segment.end]),
    ...allWords().filter((word) => word.deleted).map((word) => [word.start, word.end]),
    ...state.cuts.filter((cut) => cut.assetId === clip.assetId).map((cut) => [cut.start, cut.end]),
  ].filter(([start, end]) => end > clip.sourceStart && start < clip.sourceEnd)
    .map(([start, end]) => [Math.max(start, clip.sourceStart), Math.min(end, clip.sourceEnd)])
    .sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const range of ranges) {
    if (merged.length && range[0] <= merged.at(-1)[1] + .02) merged.at(-1)[1] = Math.max(merged.at(-1)[1], range[1]);
    else merged.push([...range]);
  }
  return merged;
}
const effectiveClipDuration = (clip) => clipDuration(clip) - excludedRangesFor(clip).reduce((total, [start, end]) => total + (end - start) / (clip.speed || 1), 0);
const sequenceDuration = () => activeVideo().reduce((total, clip) => total + effectiveClipDuration(clip), 0);
const allItems = () => ['video', 'audio', 'captions'].flatMap((type) => state.tracks[type]);
const currentItem = () => allItems().find((item) => item.id === selectedId);
const currentVideo = () => state.tracks.video.find((item) => item.id === selectedId) || state.tracks.video.find((item) => item.id === player.dataset.clipId);
const allWords = () => state.transcript.segments.flatMap((segment) => segment.words);

function checkpoint() {
  history.push(clone(state));
  if (history.length > 80) history.shift();
  future = [];
}

function mutate(action) {
  checkpoint();
  action();
  state.updatedAt = new Date().toISOString();
  updateTimelinePositions();
  render();
  scheduleSave();
}

function toast(message) {
  const element = $('#toast');
  element.textContent = message;
  element.classList.add('show');
  setTimeout(() => element.classList.remove('show'), 1800);
}

async function load() {
  const response = await fetch('/api/project');
  if (!response.ok) throw new Error(await response.text());
  state = await response.json();
  state.cuts ||= [];
  for (const segment of state.transcript.segments) segment.deleted ??= false;
  $('#projectTitle').textContent = state.title || '视频粗剪工作台';
  updateTimelinePositions();
  render();
  loadClip(0);
  $('#saveState').textContent = '已载入';
  $('#saveState').classList.add('saved');
}

function scheduleSave() {
  clearTimeout(saveTimer);
  $('#saveState').textContent = '保存中…';
  $('#saveState').classList.remove('saved');
  saveTimer = setTimeout(save, 420);
}

async function save() {
  const response = await fetch('/api/project', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state) });
  $('#saveState').textContent = response.ok ? '已自动保存' : '保存失败';
  $('#saveState').classList.toggle('saved', response.ok);
}

function updateTimelinePositions() {
  let cursor = 0;
  for (const clip of activeVideo()) {
    clip.timelineStart = cursor;
    const audio = state.tracks.audio.find((item) => item.linkId === clip.linkId);
    if (audio) audio.timelineStart = cursor;
    cursor += effectiveClipDuration(clip);
  }
  const transcriptAsset = state.transcript.assetId;
  for (const caption of state.tracks.captions) {
    const host = activeVideo().find((clip) => clip.assetId === transcriptAsset && caption.sourceStart >= clip.sourceStart && caption.sourceEnd <= clip.sourceEnd);
    caption.timelineStart = host ? host.timelineStart + (caption.sourceStart - host.sourceStart) / (host.speed || 1) : null;
  }
  for (const asset of state.assets) asset.inTimeline = state.tracks.video.some((clip) => clip.assetId === asset.id && clip.enabled !== false);
}

function render() {
  renderMediaBin();
  renderSentenceCuts();
  renderTranscript();
  renderTimeline();
  renderInspector();
  $('#assetCount').textContent = state.assets.length;
  $('#durationBadge').textContent = `${sequenceDuration().toFixed(1)} 秒`;
  $('#undoBtn').disabled = !history.length;
  $('#redoBtn').disabled = !future.length;
}

function renderMediaBin() {
  const root = $('#mediaBin');
  root.innerHTML = '';
  for (const asset of state.assets) {
    const card = document.createElement('article');
    card.className = 'media-card';
    const used = state.tracks.video.some((clip) => clip.assetId === asset.id && clip.enabled !== false);
    card.innerHTML = `<div class="media-thumb">${asset.role === 'primary' ? 'MAIN' : 'VIDEO'}</div><div><div class="media-name" title="${asset.name}">${asset.name}</div><div class="media-meta">${fmt(asset.duration)} · ${asset.role === 'primary' ? '主素材' : '辅助素材'}</div><div class="media-actions"><button data-preview>预览</button><button data-add ${used ? 'disabled' : ''}>${used ? '已在时间线' : '加入主线'}</button></div></div>`;
    card.querySelector('[data-preview]').onclick = () => previewAsset(asset);
    card.querySelector('[data-add]').onclick = () => addAssetToTimeline(asset);
    root.append(card);
  }
}

function renderSentenceCuts() {
  const root = $('#sentenceCuts');
  root.innerHTML = '';
  if (!state.transcript.segments.length) {
    root.innerHTML = '<p class="panel-help">没有可编辑的句子。</p>';
    return;
  }
  for (const [index, segment] of state.transcript.segments.entries()) {
    const card = document.createElement('article');
    card.className = `sentence-cut${segment.deleted ? ' deleted' : ''}`;
    const text = segment.words.map((word) => word.text).join('');
    card.innerHTML = `<div class="sentence-cut-top"><span>句 ${String(index + 1).padStart(2, '0')} · ${fmt(segment.start)}–${fmt(segment.end)}</span><span class="sentence-cut-status">${segment.deleted ? '已删除' : '保留'}</span></div><p class="sentence-cut-text"></p><div class="media-actions"><button data-play>播放本句</button><button data-toggle class="${segment.deleted ? '' : 'danger'}">${segment.deleted ? '恢复本句' : '删除本句'}</button></div>`;
    card.querySelector('.sentence-cut-text').textContent = text || '（无文字）';
    card.querySelector('[data-play]').onclick = () => seekSource(segment.start);
    card.querySelector('[data-toggle]').onclick = () => mutate(() => { segment.deleted = !segment.deleted; });
    root.append(card);
  }
}

function previewAsset(asset) {
  selectedId = null;
  player.dataset.clipId = '';
  player.dataset.pendingTime = '0';
  player.src = `/api/media/${encodeURIComponent(asset.id)}`;
  $('#emptyPlayer').style.display = 'none';
  renderInspector();
}

function addAssetToTimeline(asset) {
  if (!asset.duration) return toast('无法读取素材时长');
  mutate(() => {
    const suffix = Date.now().toString(36);
    const linkId = `media-link-${suffix}`;
    const video = { id: `v-${suffix}`, assetId: asset.id, label: asset.name, sourceStart: 0, sourceEnd: asset.duration, enabled: true, linkId, speed: 1, volume: 1 };
    const audio = { id: `a-${suffix}`, assetId: asset.id, label: `${asset.name} 音频`, sourceStart: 0, sourceEnd: asset.duration, enabled: true, linkId, volume: 1 };
    state.tracks.video.push(video);
    state.tracks.audio.push(audio);
    selectedId = video.id;
  });
  toast('已加入主时间线末尾');
}

function loadClip(index, offset = 0) {
  const clips = activeVideo();
  if (!clips.length) return;
  if (index >= clips.length) return player.pause();
  currentIndex = Math.max(0, index);
  const clip = clips[currentIndex];
  selectedId = clip.id;
  player.dataset.pendingTime = String(Math.max(clip.sourceStart, clip.sourceStart + offset));
  player.dataset.clipId = clip.id;
  player.src = `/api/media/${encodeURIComponent(clip.assetId)}`;
  $('#emptyPlayer').style.display = 'none';
  render();
}

function renderTranscript() {
  const root = $('#transcript');
  root.innerHTML = '';
  for (const segment of state.transcript.segments) {
    const row = document.createElement('div');
    row.className = `sentence${segment.deleted ? ' deleted' : ''}`;
    const time = document.createElement('button');
    time.className = 'sentence-time';
    time.textContent = fmt(segment.start);
    time.onclick = () => seekSource(segment.start);
    row.append(time);
    for (const word of segment.words) {
      const button = document.createElement('button');
      button.className = `word${word.deleted ? ' deleted' : ''}${selectedWords.has(word.id) ? ' selected' : ''}`;
      button.textContent = word.text;
      button.dataset.wordId = word.id;
      button.onclick = (event) => {
        if (event.shiftKey && selectedWords.size) selectWordRange(word.id);
        else if (event.metaKey || event.ctrlKey) selectedWords.has(word.id) ? selectedWords.delete(word.id) : selectedWords.add(word.id);
        else { selectedWords.clear(); selectedWords.add(word.id); seekSource(word.start); }
        renderTranscript();
      };
      row.append(button);
    }
    root.append(row);
  }
}

function selectWordRange(id) {
  const words = allWords();
  const last = [...selectedWords].at(-1);
  const a = words.findIndex((word) => word.id === last);
  const b = words.findIndex((word) => word.id === id);
  if (a < 0 || b < 0) return;
  for (let index = Math.min(a, b); index <= Math.max(a, b); index++) selectedWords.add(words[index].id);
}

function seekSource(time) {
  const index = activeVideo().findIndex((clip) => clip.assetId === state.transcript.assetId && time >= clip.sourceStart && time < clip.sourceEnd);
  if (index >= 0) loadClip(index, time - activeVideo()[index].sourceStart);
}

function renderTimeline() {
  const root = $('#timeline');
  root.innerHTML = '';
  const total = Math.max(sequenceDuration(), 30);
  const canvasWidth = Math.max(total * pixelsPerSecond, root.clientWidth - 82);
  const ruler = document.createElement('div');
  ruler.className = 'ruler-row';
  ruler.innerHTML = '<div class="track-label">TIME</div>';
  const rulerCanvas = document.createElement('div');
  rulerCanvas.className = 'track-canvas';
  rulerCanvas.style.width = `${canvasWidth}px`;
  for (let second = 0; second <= total; second += 5) {
    const tick = document.createElement('span');
    tick.className = 'tick';
    tick.style.left = `${second * pixelsPerSecond}px`;
    tick.textContent = fmt(second).slice(0, 5);
    rulerCanvas.append(tick);
  }
  ruler.append(rulerCanvas);
  root.append(ruler);

  for (const [type, label] of [['video', 'V1 主视频'], ['audio', 'A1 原声'], ['captions', 'T1 字幕']]) {
    const row = document.createElement('div');
    row.className = 'track-row';
    row.innerHTML = `<div class="track-label">${label}</div>`;
    const canvas = document.createElement('div');
    canvas.className = 'track-canvas';
    canvas.style.width = `${canvasWidth}px`;
    for (const clip of state.tracks[type]) {
      if (clip.timelineStart == null) continue;
      const element = document.createElement('div');
      element.className = `timeline-clip ${type === 'captions' ? 'caption' : type}${clip.id === selectedId ? ' active' : ''}${clip.enabled === false ? ' deleted' : ''}`;
      element.style.left = `${clip.timelineStart * pixelsPerSecond}px`;
      element.style.width = `${Math.max(clipDuration(clip) * pixelsPerSecond, 28)}px`;
      element.textContent = clip.text || clip.label || clip.id;
      element.title = `${fmt(clip.timelineStart)} · ${fmt(clipDuration(clip))}`;
      element.draggable = type === 'video';
      element.onclick = () => selectTimelineItem(type, clip);
      element.ondragstart = (event) => event.dataTransfer.setData('text/plain', clip.id);
      element.ondragover = (event) => event.preventDefault();
      element.ondrop = (event) => { event.preventDefault(); reorderVideo(event.dataTransfer.getData('text/plain'), clip.id); };
      if (type === 'video') {
        for (const [start, end] of excludedRangesFor(clip)) {
          const mark = document.createElement('i');
          mark.className = 'cut-mark';
          mark.style.left = `${((start - clip.sourceStart) / (clip.sourceEnd - clip.sourceStart)) * 100}%`;
          mark.style.width = `${Math.max(((end - start) / (clip.sourceEnd - clip.sourceStart)) * 100, .5)}%`;
          element.append(mark);
        }
      }
      canvas.append(element);
    }
    row.append(canvas);
    root.append(row);
  }
}

function selectTimelineItem(type, clip) {
  if (type === 'video') {
    const index = activeVideo().findIndex((item) => item.id === clip.id);
    if (index >= 0) loadClip(index);
  } else {
    selectedId = clip.id;
    if (type === 'captions') seekSource(clip.sourceStart);
    selectedId = clip.id;
    render();
  }
}

function reorderVideo(from, to) {
  if (from === to) return;
  mutate(() => {
    const clips = state.tracks.video;
    const fromIndex = clips.findIndex((clip) => clip.id === from);
    const toIndex = clips.findIndex((clip) => clip.id === to);
    if (fromIndex < 0 || toIndex < 0) return;
    const [moved] = clips.splice(fromIndex, 1);
    clips.splice(toIndex, 0, moved);
    const audioOrder = new Map(clips.map((clip, index) => [clip.linkId, index]));
    state.tracks.audio.sort((a, b) => (audioOrder.get(a.linkId) ?? 999) - (audioOrder.get(b.linkId) ?? 999));
  });
}

function captionFor(video) {
  return state.tracks.captions.find((caption) => player.currentTime >= caption.sourceStart && player.currentTime < caption.sourceEnd) || state.tracks.captions.find((caption) => caption.sourceStart >= video.sourceStart && caption.sourceEnd <= video.sourceEnd);
}

function renderInspector() {
  const item = currentItem() || currentVideo();
  const video = currentVideo();
  const caption = item && state.tracks.captions.includes(item) ? item : video ? captionFor(video) : null;
  $('#clipName').textContent = item?.label || item?.text || item?.id || '尚未选择';
  $('#captionText').value = caption?.text || '';
  $('#captionText').disabled = !caption;
  $('#volumeInput').value = item?.volume ?? 1;
  $('#volumeInput').disabled = !item || item.volume === undefined;
  $('#speedInput').value = video?.speed ?? 1;
  $('#speedInput').disabled = !video;
  $('#toggleClipBtn').disabled = !item;
  $('#toggleClipBtn').textContent = item?.enabled === false ? '恢复到主时间线' : '移出主时间线';
  $('#splitBtn').disabled = !video;
}

function splitCurrent() {
  const clip = currentVideo();
  if (!clip) return;
  const at = player.currentTime;
  if (at <= clip.sourceStart + .08 || at >= clip.sourceEnd - .08) return toast('请在片段中间位置拆分');
  mutate(() => {
    const index = state.tracks.video.findIndex((item) => item.id === clip.id);
    const suffix = Date.now().toString(36);
    const originalLink = clip.linkId;
    const rightLink = `${originalLink}-${suffix}`;
    const right = { ...clone(clip), id: `${clip.id}-${suffix}`, sourceStart: at, label: `${clip.label} B`, linkId: rightLink };
    clip.sourceEnd = at;
    clip.label = `${clip.label} A`;
    state.tracks.video.splice(index + 1, 0, right);
    const audio = state.tracks.audio.find((item) => item.linkId === originalLink);
    if (audio) {
      const audioIndex = state.tracks.audio.indexOf(audio);
      const rightAudio = { ...clone(audio), id: `${audio.id}-${suffix}`, sourceStart: at, linkId: rightLink, label: `${audio.label} B` };
      audio.sourceEnd = at;
      audio.label = `${audio.label} A`;
      state.tracks.audio.splice(audioIndex + 1, 0, rightAudio);
    }
    selectedId = right.id;
  });
}

function toggleWords(deleted) {
  if (!selectedWords.size) return toast('请先选择文字');
  mutate(() => { for (const word of allWords()) if (selectedWords.has(word.id)) word.deleted = deleted; });
}

function undo() { if (!history.length) return; future.push(clone(state)); state = history.pop(); updateTimelinePositions(); render(); scheduleSave(); }
function redo() { if (!future.length) return; history.push(clone(state)); state = future.pop(); updateTimelinePositions(); render(); scheduleSave(); }

player.addEventListener('loadedmetadata', () => { player.currentTime = Number(player.dataset.pendingTime || 0); player.play().catch(() => {}); });
player.addEventListener('timeupdate', () => {
  const clip = currentVideo();
  $('#timeReadout').textContent = `${fmt(player.currentTime)} / ${fmt(sequenceDuration())}`;
  const deletedSegment = state.transcript.segments.find((segment) => segment.deleted && player.currentTime >= segment.start && player.currentTime < segment.end);
  const deletedWord = allWords().find((word) => word.deleted && player.currentTime >= word.start && player.currentTime < word.end);
  const appliedCut = state.cuts.find((cut) => cut.assetId === clip?.assetId && player.currentTime >= cut.start && player.currentTime < cut.end);
  if (deletedSegment) { player.currentTime = deletedSegment.end; return; }
  if (deletedWord) { player.currentTime = deletedWord.end; return; }
  if (appliedCut) { player.currentTime = appliedCut.end; return; }
  if (clip && player.currentTime >= clip.sourceEnd - .03) loadClip(currentIndex + 1);
  document.querySelectorAll('.word.playing').forEach((element) => element.classList.remove('playing'));
  const playing = allWords().find((word) => !word.deleted && player.currentTime >= word.start && player.currentTime < word.end);
  if (playing) document.querySelector(`[data-word-id="${CSS.escape(playing.id)}"]`)?.classList.add('playing');
});

$('#prevClip').onclick = () => loadClip(currentIndex - 1);
$('#nextClip').onclick = () => loadClip(currentIndex + 1);
$('#splitBtn').onclick = splitCurrent;
$('#deleteWordsBtn').onclick = () => toggleWords(true);
$('#restoreWordsBtn').onclick = () => toggleWords(false);
$('#selectAllBtn').onclick = () => { const segment = state.transcript.segments.find((item) => player.currentTime >= item.start && player.currentTime < item.end); if (!segment) return toast('请先播放或定位到一句话'); selectedWords = new Set(segment.words.map((word) => word.id)); renderTranscript(); };
$('#zoomInput').oninput = (event) => { pixelsPerSecond = Number(event.target.value); renderTimeline(); };
$('#undoBtn').onclick = undo;
$('#redoBtn').onclick = redo;
$('#toggleClipBtn').onclick = () => { const item = currentItem() || currentVideo(); if (!item) return; const next = item.enabled === false; mutate(() => { item.enabled = next; if (state.tracks.video.includes(item)) { const audio = state.tracks.audio.find((candidate) => candidate.linkId === item.linkId); if (audio) audio.enabled = next; } }); };
$('#captionText').onchange = (event) => { const item = currentItem(); const video = currentVideo(); const caption = item && state.tracks.captions.includes(item) ? item : video ? captionFor(video) : null; if (caption) mutate(() => { caption.text = event.target.value; }); };
$('#volumeInput').onchange = (event) => { const item = currentItem() || currentVideo(); if (item?.volume !== undefined) mutate(() => { item.volume = Math.max(0, Math.min(2, Number(event.target.value) || 0)); }); };
$('#speedInput').onchange = (event) => { const video = currentVideo(); if (video) mutate(() => { video.speed = Math.max(.25, Math.min(4, Number(event.target.value) || 1)); }); };
$('#confirmBtn').onclick = () => mutate(() => { state.status = 'confirmed'; state.confirmedAt = new Date().toISOString(); });
$('#exportBtn').onclick = async () => { await save(); const button = $('#exportBtn'); button.disabled = true; button.textContent = '导出中…'; const response = await fetch('/api/export-review', { method: 'POST' }); const output = await response.json().catch(() => ({ error: '导出失败' })); button.disabled = false; button.textContent = '导出审片'; toast(response.ok ? `已导出：${output.file}` : output.error); };
$('#jianyingBtn').onclick = async () => { await save(); const button = $('#jianyingBtn'); button.disabled = true; button.textContent = '准备中…'; const response = await fetch('/api/export-jianying', { method: 'POST' }); const output = await response.json().catch(() => ({ error: '剪映工程导出失败' })); button.disabled = false; button.textContent = '导出剪映工程'; $('#exportDialogText').textContent = response.ok ? `工程包已生成：${output.path}` : output.error || '暂时无法导出'; $('#exportDialog').hidden = false; };
$('#closeDialog').onclick = () => { $('#exportDialog').hidden = true; };

load().catch((error) => { $('#saveState').textContent = '载入失败'; toast(error.message); });
