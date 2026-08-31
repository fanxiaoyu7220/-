const form = document.querySelector('#job-form');
const urlInput = document.querySelector('#url');
const accessWrap = document.querySelector('#access-wrap');
const accessCode = document.querySelector('#access-code');
const submitButton = document.querySelector('#submit-button');
const jobCard = document.querySelector('#job-card');
const platformLabel = document.querySelector('#platform');
const statusTitle = document.querySelector('#status-title');
const progressBar = document.querySelector('#progress-bar');
const progressTrack = document.querySelector('.progress-track');
const progressPercent = document.querySelector('#progress-percent');
const progressDetail = document.querySelector('#progress-detail');
const errorMessage = document.querySelector('#error-message');
const downloadList = document.querySelector('#download-list');
const cancelButton = document.querySelector('#cancel-button');

let activeJobId = null;
let pollTimer = null;

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || '服务器暂时不可用，请稍后再试。');
  return body;
}

function setProgress(value) {
  const safe = Math.max(0, Math.min(Number(value) || 0, 100));
  progressBar.style.width = `${safe}%`;
  progressTrack.setAttribute('aria-valuenow', String(Math.round(safe)));
  progressPercent.textContent = `${Math.round(safe)}%`;
}

function resetJobCard() {
  jobCard.hidden = false;
  errorMessage.hidden = true;
  errorMessage.textContent = '';
  downloadList.replaceChildren();
  cancelButton.hidden = false;
  setProgress(0);
  jobCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showDownloads(job) {
  downloadList.replaceChildren();
  for (const filename of job.files || []) {
    const link = document.createElement('a');
    link.className = 'download-link';
    link.href = `/api/jobs/${encodeURIComponent(job.id)}/files/${encodeURIComponent(filename)}`;
    const name = document.createElement('span');
    name.textContent = filename;
    const action = document.createElement('span');
    action.textContent = '下载文件 ↓';
    link.append(name, action);
    downloadList.append(link);
  }
}

function renderJob(job) {
  platformLabel.textContent = job.platform || '网页任务';
  statusTitle.textContent = job.message || '正在处理';
  setProgress(job.progress);
  const details = [job.speed ? `速度 ${job.speed}` : '', job.eta ? `剩余 ${job.eta}` : ''].filter(Boolean);
  progressDetail.textContent = details.join(' · ') || (job.status === 'queued' ? '正在排队' : '请保持页面打开');

  const finished = ['completed', 'failed', 'cancelled'].includes(job.status);
  cancelButton.hidden = finished;
  submitButton.disabled = !finished;
  if (job.status === 'completed') {
    setProgress(100);
    progressDetail.textContent = '结果默认保留两小时，请及时下载';
    showDownloads(job);
  } else if (job.status === 'failed') {
    errorMessage.textContent = job.error || '任务失败，请稍后重试。';
    errorMessage.hidden = false;
  } else if (job.status === 'cancelled') {
    progressDetail.textContent = '任务已取消';
  }
  return finished;
}

async function pollJob() {
  if (!activeJobId) return;
  try {
    const job = await api(`/api/jobs/${encodeURIComponent(activeJobId)}`);
    if (renderJob(job)) {
      activeJobId = null;
      pollTimer = null;
      return;
    }
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
    submitButton.disabled = false;
    activeJobId = null;
    return;
  }
  pollTimer = window.setTimeout(pollJob, 1200);
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (pollTimer) window.clearTimeout(pollTimer);
  resetJobCard();
  submitButton.disabled = true;
  platformLabel.textContent = '准备中';
  statusTitle.textContent = '正在创建任务';
  progressDetail.textContent = '正在连接 ACAN 后台服务';
  try {
    const job = await api('/api/jobs', {
      method: 'POST',
      body: JSON.stringify({ url: urlInput.value, accessCode: accessCode.value }),
    });
    activeJobId = job.id;
    renderJob(job);
    pollJob();
  } catch (error) {
    submitButton.disabled = false;
    cancelButton.hidden = true;
    statusTitle.textContent = '无法创建任务';
    progressDetail.textContent = '请修改链接后重新尝试';
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  }
});

cancelButton.addEventListener('click', async () => {
  if (!activeJobId) return;
  cancelButton.disabled = true;
  try {
    await api(`/api/jobs/${encodeURIComponent(activeJobId)}`, { method: 'DELETE' });
    statusTitle.textContent = '任务已取消';
    progressDetail.textContent = '可以粘贴新的链接重新开始';
    submitButton.disabled = false;
    activeJobId = null;
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    cancelButton.disabled = false;
  }
});

api('/api/health').then((health) => {
  accessWrap.hidden = !health.requiresAccessCode;
}).catch(() => {
  accessWrap.hidden = true;
});
