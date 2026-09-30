/* War of the Gods: campaign site. Data comes from data/site.json, built by tools/build.py. */
(() => {
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4.5v15l13-7.5z"/></svg>';
const PAUSE = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 4h4.5v16H6zM13.5 4H18v16h-4.5z"/></svg>';
const SPEAK = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4z"/></svg>';
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const fmtDate = iso => { if (!iso) return ''; const [y, m, d] = iso.slice(0, 10).split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };
const fmtT = t => { t = Math.floor(t); const h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60; return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s).padStart(2, '0'); };
const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };

let D = null;               // site data
const S = {};               // sessions by number
const H = {};               // heroes by id
let order = [];             // session numbers in order
const rendered = {};

/* ---------- audio ---------- */
const audio = new Audio(); audio.preload = 'none';
let playingBtn = null;
function setBtn(btn, on) {
  if (!btn) return;
  btn.classList.toggle('on', on);
  if (btn.classList.contains('play')) btn.innerHTML = (on ? PAUSE : PLAY) + '<span class="ring"></span>';
  btn.setAttribute('aria-label', on ? 'Pause' : 'Play');
  if (!on) btn.style.setProperty('--p', 0);
}
function playClip(src, btn) {
  if (playingBtn === btn && !audio.paused) { audio.pause(); return; }
  if (playingBtn && playingBtn !== btn) setBtn(playingBtn, false);
  document.querySelectorAll('video').forEach(v => v.pause());
  playingBtn = btn;
  if (!audio.src.endsWith(src)) audio.src = src;
  audio.currentTime = 0;
  audio.play().then(() => setBtn(btn, true)).catch(() => setBtn(btn, false));
}
audio.addEventListener('pause', () => setBtn(playingBtn, false));
audio.addEventListener('ended', () => setBtn(playingBtn, false));
audio.addEventListener('timeupdate', () => { if (playingBtn && audio.duration) playingBtn.style.setProperty('--p', audio.currentTime / audio.duration); });
document.addEventListener('click', e => {
  const b = e.target.closest('[data-audio]');
  if (b) { e.preventDefault(); playClip(b.dataset.audio, b.matches('.quote') ? b : (b.querySelector('.play') || b)); }
});

// quote cards are buttons: play them from the keyboard too
document.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches?.('.quote[data-audio]')) { e.preventDefault(); e.target.click(); } });

/* ---------- lightbox ---------- */
let lbList = [], lbI = 0;
function lbShow() {
  const it = lbList[lbI]; if (!it) return;
  $('#lb-stage').innerHTML = it.k === 'vid'
    ? `<video src="${esc(it.src)}" controls autoplay playsinline ${it.poster ? `poster="${esc(it.poster)}"` : ''}></video>`
    : `<img src="${esc(it.full || it.src)}" alt="${esc(it.alt || '')}">`;
  $('#lb-cap').innerHTML = it.cap || '';
  $('#lb-pv').hidden = $('#lb-nx').hidden = lbList.length < 2;
}
function lbOpen(list, i) { lbList = list; lbI = i; $('#lb').hidden = false; lbShow(); $('#lb-x').focus(); document.body.style.overflow = 'hidden'; }
function lbClose() { $('#lb').hidden = true; $('#lb-stage').innerHTML = ''; document.body.style.overflow = ''; }
$('#lb-x').addEventListener('click', lbClose);
$('#lb-pv').addEventListener('click', () => { lbI = (lbI - 1 + lbList.length) % lbList.length; lbShow(); });
$('#lb-nx').addEventListener('click', () => { lbI = (lbI + 1) % lbList.length; lbShow(); });
$('#lb').addEventListener('click', e => { if (e.target.id === 'lb' || e.target.id === 'lb-stage') lbClose(); });
document.addEventListener('keydown', e => {
  if ($('#lb').hidden) return;
  if (e.key === 'Escape') lbClose();
  if (e.key === 'ArrowLeft') $('#lb-pv').click();
  if (e.key === 'ArrowRight') $('#lb-nx').click();
});
// any element with data-lb="groupKey" data-i opens its group
const lbGroups = {};
document.addEventListener('click', e => {
  const el = e.target.closest('[data-lb]');
  if (!el) return;
  e.preventDefault();
  lbOpen(lbGroups[el.dataset.lb] || [], +el.dataset.i || 0);
});
// static gallery images (fallen page)
function wireStaticGallery() {
  const figs = $$('#v-fallen .gallery img');
  lbGroups.fallen = figs.map(img => ({ src: img.getAttribute('src'), alt: img.alt, cap: esc(img.closest('figure')?.querySelector('figcaption')?.textContent || '') }));
  figs.forEach((img, i) => { img.dataset.lb = 'fallen'; img.dataset.i = i; });
}

/* ---------- shared bits ---------- */
function ytUrl(n, t) { const v = S[n]?.video; if (!v) return ''; return `https://www.youtube.com/watch?v=${v.id}${t ? `&t=${Math.floor(t)}s` : ''}`; }
function dayHtml(s) { return `<b>Day ${esc(s.day)}</b>${esc(s.reckoned)}${s.real ? `<span class="real">Played ${fmtDate(s.real)}${s.realApprox ? ' (ish)' : ''}</span>` : ''}`; }
function thumbHtml(s, link = true) {
  if (!s.thumb) return '<span class="thumb none">No video</span>';
  const img = `<img loading="lazy" src="${esc(s.thumb)}" alt="Session ${s.n} thumbnail">`;
  return link ? `<a class="thumb" href="#/session/${s.n}">${img}</a>` : `<span class="thumb">${img}</span>`;
}
function tagsHtml(s) {
  const t = [];
  for (const g of s.gods) t.push(`<span class="tag gd">${esc(g)}</span>`);
  for (const x of s.plain) t.push(`<span class="tag">${esc(x)}</span>`);
  for (const d of s.dead) t.push(`<span class="tag death">† ${esc(d)}</span>`);
  if (s.moments.length) t.push(`<a class="tag fun" href="#/session/${s.n}">★ ${s.moments.length} best moment${s.moments.length > 1 ? 's' : ''}</a>`);
  if (s.posts.length) t.push(`<a class="tag dc" href="#/session/${s.n}#dc">💬 ${s.posts.length} Discord post${s.posts.length > 1 ? 's' : ''}</a>`);
  return `<div class="tags">${t.join('')}</div>`;
}
const KINDS = { funny: '😂 Funny', epic: '⚔️ Epic' };
// best first: the hand-given stars decide, the laugh detector breaks ties
const rank = m => (m.stars || 0) * 10 + (m.score || 0);
const byRank = (a, b) => rank(b) - rank(a) || a.s - b.s || (a.t || 0) - (b.t || 0);
function heroChips(m) {
  return (m.pcs || []).filter(id => H[id]).map(id => `<a class="hchip c-${esc(H[id].c)}" href="#/hero/${esc(id)}"><img src="${esc(H[id].img)}" alt="">${esc(H[id].name.split(' ')[0])}</a>`).join('');
}
// painted moments from the art queue: a small copy in the page, the larger one in the lightbox
function artFig(m, sizes) {
  const a = m.art, set = a.thumb && a.web ? ` srcset="${esc(a.thumb)} 640w, ${esc(a.web)} 1600w" sizes="${sizes}"` : '';
  return `<button type="button" class="art-img" data-lb="art" data-i="${D.art.indexOf(m)}" aria-label="View the painting: ${esc(m.title)}"><img loading="lazy" decoding="async" src="${esc(a.thumb || a.web || a.src)}"${set}${a.w ? ` width="${a.w}" height="${a.h}"` : ''} alt="${esc(a.alt)}"></button>`;
}
// absolute, because a url() in a custom property resolves against the stylesheet that uses it
const cssUrl = src => `url("${new URL(src, location.href).href}")`;
function artCap(m) {
  const s = S[m.s];
  return `<b>${esc(m.title)}</b> · <a href="#/session/${m.s}">Session ${m.s}${s ? ` · ${esc(s.title)}` : ''}</a>${m.blurb ? `<br>${esc(m.blurb)}` : ''}
    <span class="lb-acts">${m.audio ? `<button type="button" class="mini" data-audio="${esc(m.audio)}"><span class="play" aria-hidden="true">${PLAY}<span class="ring"></span></span><span>Hear it at the table</span></button>` : ''}<a href="${esc(m.art.src)}" target="_blank" rel="noopener">Full size ↗</a></span>`;
}
function laughMeter(score) {
  const n = Math.max(1, Math.round((score || 0) * 5));
  return `<span class="laughs" title="How hard the table laughed">${[4, 7, 10, 13, 14].map((h, i) => `<i style="height:${h}px;opacity:${i < n ? .9 : .2}"></i>`).join('')}</span>`;
}
function momentCard(m, withSession = true) {
  const s = S[m.s];
  const lines = (m.lines || []).map(l => `<li class="${l.w === 'DM' ? 'dm' : ''}">${l.w ? `<b>${esc(l.w)}</b>` : ''}${esc(l.x)}</li>`).join('');
  const yt = ytUrl(m.s, m.t);
  return `<article class="moment" id="m-${esc(m.id)}">
    <div class="mh">
      ${m.audio && !m.video ? `<button class="play" data-audio="${esc(m.audio)}" aria-label="Play">${PLAY}<span class="ring"></span></button>` : ''}
      <div><h4>${esc(m.title)}</h4>
      <div class="ms">${m.kind && KINDS[m.kind] ? `<span class="kind k-${esc(m.kind)}">${KINDS[m.kind]}</span> ` : ''}${withSession ? `<a href="#/session/${m.s}">Session ${m.s}${s ? ` · ${esc(s.title)}` : ''}</a> · ` : ''}${fmtT(m.t)}</div></div>
    </div>
    ${m.video ? `<button type="button" class="clip" data-video="${esc(m.video)}" aria-label="Play the clip: ${esc(m.title)}"><img loading="lazy" decoding="async" src="${esc(m.poster)}" alt="" width="640" height="360"><span class="play" aria-hidden="true">${PLAY}</span><span class="dur">${fmtT(m.d)}</span></button>` : ''}
    ${m.blurb ? `<p class="blurb">${esc(m.blurb)}</p>` : ''}
    ${m.art ? artFig(m, '(max-width: 700px) 100vw, 420px') : ''}
    ${lines ? `<ul class="lines">${lines}</ul>` : ''}
    ${m.pcs && m.pcs.length ? `<div class="hchips">${heroChips(m)}</div>` : ''}
    <div class="foot">${laughMeter(m.score)}${yt ? `<a href="${yt}" target="_blank" rel="noopener">Watch it at ${fmtT(m.t)} ↗</a>` : ''}</div>
  </article>`;
}
// a highlight Short from the channel, playable in place
function shortCard(c) {
  const s = S[c.s];
  return `<article class="moment short-card">
    <div class="mh"><div><h4>${esc(c.title)}</h4>
      <div class="ms">${KINDS[c.mood] ? `<span class="kind k-${esc(c.mood)}">${KINDS[c.mood]}</span> ` : ''}${s ? `<a href="#/session/${s.n}">Session ${s.n} · ${esc(s.title)}</a> · ` : ''}channel Short</div></div></div>
    <button type="button" class="yt-short" data-yt="${esc(c.id)}" aria-label="Play ${esc(c.title)}"><img loading="lazy" src="https://i.ytimg.com/vi/${esc(c.id)}/hqdefault.jpg" alt="" onerror="this.style.visibility='hidden'"><span class="play" aria-hidden="true">${PLAY}</span></button>
    ${c.pcs && c.pcs.length ? `<div class="hchips">${heroChips(c)}</div>` : ''}
    <div class="foot"><a href="https://www.youtube.com/shorts/${esc(c.id)}" target="_blank" rel="noopener">Watch on YouTube ↗</a></div>
  </article>`;
}
// moment clips play in place; only one at a time
document.addEventListener('click', e => {
  const b = e.target.closest('.clip[data-video]');
  if (!b) return;
  audio.pause();
  $$('video.clip-v').forEach(v => v.pause());
  b.outerHTML = `<video class="clip-v" src="${esc(b.dataset.video)}" controls autoplay playsinline preload="auto"></video>`;
});
document.addEventListener('play', e => { if (e.target.matches?.('video')) { audio.pause(); $$('video').forEach(v => { if (v !== e.target) v.pause(); }); } }, true);
document.addEventListener('click', e => {
  const b = e.target.closest('.yt-short');
  if (!b) return;
  audio.pause();
  b.outerHTML = `<div class="yt-embed"><iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(b.dataset.yt)}?autoplay=1&rel=0" title="YouTube Short" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe></div>`;
});
function postCard(p, group, i) {
  const media = (p.m || []).map((x, j) => x.k === 'vid'
    ? `<video src="${esc(x.src)}" ${x.poster ? `poster="${esc(x.poster)}"` : ''} preload="none" muted playsinline data-lb="${group}" data-i="${i + j}"></video>`
    : `<img loading="lazy" src="${esc(x.src)}" width="${x.w || ''}" height="${x.h || ''}" alt="${esc(x.alt || 'Posted by ' + p.a)}" data-lb="${group}" data-i="${i + j}">`).join('');
  return `<figure class="post">${media}<figcaption class="pc2"><b>${esc(p.a)}</b><span class="d">${fmtDate(p.t)}</span>${p.x ? `<p>${esc(p.x)}</p>` : ''}</figcaption></figure>`;
}
function postsHtml(posts, group) {
  const items = []; let html = '';
  for (const p of posts) { html += postCard(p, group, items.length); for (const x of p.m || []) items.push({ ...x, cap: `<b>${esc(p.a)}</b> · ${fmtDate(p.t)}${p.x ? '<br>' + esc(p.x) : ''}` }); }
  lbGroups[group] = items;
  return `<div class="masonry">${html}</div>`;
}

/* ---------- timeline ---------- */
function renderTimeline() {
  const out = [];
  for (const c of D.chapters) {
    const ss = c.sessions.map(n => S[n]);
    const lo = ss[0].dayLo, hi = ss[ss.length - 1].dayHi;
    const rng = ss.length > 1 ? `Sessions ${ss[0].n}–${ss[ss.length - 1].n}` : `Session ${ss[0].n}`;
    out.push(`<section class="chapter" id="ch-${esc(c.num)}"><div class="ch-head"><div class="ch-num">${esc(c.num)}</div><h3>${esc(c.title)}</h3><div class="ch-meta">${esc(c.place)} · ${rng} · Days ${lo}–${hi}</div></div><p class="ch-blurb">${c.blurb}</p>`);
    for (const s of ss) {
      const strip = s.posts.flatMap(p => (p.m || []).filter(x => x.k !== 'vid').map(x => ({ ...x, p }))).slice(0, 10);
      const g = `tl${s.n}`;
      const art = s.moments.filter(m => m.art).sort(byRank)[0];
      lbGroups[g] = strip.map(x => ({ ...x, cap: `<b>${esc(x.p.a)}</b> · ${fmtDate(x.p.t)}${x.p.x ? '<br>' + esc(x.p.x) : ''}` }));
      out.push(`<article class="sess" data-cats="${esc(s.cats.join(' '))}">
        <div class="day">${dayHtml(s)}</div>
        ${thumbHtml(s)}
        <div class="s-body"><div class="s-title"><span class="no">Session ${s.n}</span><h4><a href="#/session/${s.n}">${esc(s.title)}</a></h4></div>
        <p>${s.text}</p>${tagsHtml(s)}
        ${art ? `<figure class="s-art">${artFig(art, '(max-width: 760px) 100vw, 460px')}<figcaption>🎨 ${esc(art.title)}</figcaption></figure>` : ''}
        ${s.moments.length ? `<div class="minis">${s.moments.slice().sort(byRank).slice(0, 3).map(m => `<button type="button" class="mini" data-audio="${esc(m.audio)}"><span class="play" aria-hidden="true">${PLAY}<span class="ring"></span></span><span>${esc(m.title)}</span></button>`).join('')}</div>` : ''}
        ${strip.length ? `<div class="strip">${strip.map((x, i) => `<img loading="lazy" src="${esc(x.thumb || x.src)}" alt="Discord post by ${esc(x.p.a)}" data-lb="${g}" data-i="${i}">`).join('')}</div>` : ''}
        </div></article>`);
    }
    out.push('</section>');
  }
  const lastN = order[order.length - 1];
  out.push(`<section class="chapter"><div class="ch-head"><div class="ch-num">…</div><h3>To be continued</h3><div class="ch-meta">Session ${lastN + 1} · Day ${S[lastN].dayHi}+</div></div>
    <p class="ch-blurb">The Scales have been given a name, and their verdict is still to come. Nogratis air patrols are closing in, and the Skycrest has a crown to deliver to the Ashen Brotherhood in Muttonham, where it all began.</p></section>`);
  $('#timeline').innerHTML = out.join('');
  const fb = $$('#tl-filters button');
  fb.forEach(b => b.addEventListener('click', () => {
    const f = b.dataset.f;
    fb.forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    $$('#timeline .sess').forEach(el => { el.hidden = !(f === 'all' || el.dataset.cats.split(' ').includes(f)); });
    $$('#timeline .chapter').forEach(c => { c.hidden = !$$('.sess', c).some(el => !el.hidden); });
  }));
}

/* ---------- session page ---------- */
function renderSession(n) {
  const s = S[n];
  if (!s) { location.hash = '#/'; return; }
  const i = order.indexOf(n), prev = order[i - 1], next = order[i + 1];
  const ch = D.chapters.find(c => c.sessions.includes(n));
  const loc = D.locations.find(l => l.id === s.loc);
  const v = s.video;
  const video = v ? `<div class="embed" id="emb"><img class="poster" src="${esc(s.thumb || '')}" alt=""><button class="play" id="emb-play" aria-label="Play Session ${n} here">${PLAY}</button></div>
      <div class="s-links"><a href="${ytUrl(n)}" target="_blank" rel="noopener">Watch Session ${n} on YouTube ↗</a>${s.clips.map(c => `<a href="https://www.youtube.com/shorts/${c.id}" target="_blank" rel="noopener">▸ ${esc(c.title)}</a>`).join('')}</div>`
    : (n <= 13 ? `${thumbHtml(s, false)}<div class="s-links"><a href="https://www.youtube.com/watch?v=${D.videos.summary}&t=${s.sumt || 0}s" target="_blank" rel="noopener">Watch it in the Sessions 1–13 summary ↗</a></div>` : thumbHtml(s, false));
  const el = $('#v-session');
  el.innerHTML = `<div class="sp-nav">
      <a class="btn" href="#/">← Timeline</a>
      <span>${prev ? `<a class="btn" href="#/session/${prev}">‹ Session ${prev}</a> ` : ''}${next ? `<a class="btn" href="#/session/${next}">Session ${next} ›</a>` : ''}</span>
    </div>
    <div class="sp-head">
      <div>
        <div class="kicker">Chapter ${esc(ch.num)} · ${esc(ch.title)}</div>
        <h2>${esc(s.title)}</h2>
        <div class="sp-meta"><span>Session <b>${n}</b></span><span>Day <b>${esc(s.day)}</b> · ${esc(s.reckoned)}</span>${s.real ? `<span>Played <b>${fmtDate(s.real)}</b>${s.realApprox ? ' (ish)' : ''}</span>` : ''}${loc ? `<span><a href="#/map/${n}">📍 ${esc(loc.name)}</a></span>` : ''}</div>
        <p class="sp-text">${s.text}</p>
        ${tagsHtml(s)}
      </div>
      <div>${video}</div>
    </div>
    <h3 class="sec">Best moments</h3>
    ${s.moments.length ? `<div class="moments">${s.moments.map(m => momentCard(m, false)).join('')}</div>` : `<p class="empty">${n <= 13 ? 'Sessions 1–13 were never recorded in full, so their moments live on only in the summary video and in legend.' : n === 21 ? 'The recording for this one has no sound. Whatever happened, happened.' : 'No moments picked for this session yet.'}</p>`}
    <h3 class="sec" id="dc">Meanwhile, in the Discord</h3>
    ${s.posts.length ? `<p class="note">Posted between this session and the next.</p>${postsHtml(s.posts, 'sp' + n)}` : '<p class="empty">Nothing posted in the Discord around this session.</p>'}`;
  const b = $('#emb-play');
  if (b) b.addEventListener('click', () => {
    audio.pause();
    $('#emb').innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${v.id}?autoplay=1&rel=0" title="Session ${n}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>`;
  });
  if (location.hash.endsWith('#dc')) setTimeout(() => $('#dc')?.scrollIntoView(), 50);
}

/* ---------- moments ---------- */
function renderMoments() {
  const sel = $('#mo-ch');
  sel.innerHTML += D.chapters.map(c => `<option value="${esc(c.num)}">${esc(c.num)} · ${esc(c.title)}</option>`).join('');
  const hs = $('#mo-hero');
  hs.innerHTML += D.heroes.filter(h => D.moments.some(m => (m.pcs || []).includes(h.id))).map(h => `<option value="${esc(h.id)}">${esc(h.name)}</option>`).join('');
  const all = D.moments.slice().sort((a, b) => a.s - b.s || a.t - b.t);
  const chOf = n => D.chapters.find(c => c.sessions.includes(n))?.num;
  let kind = '';
  $('#mo-kinds').innerHTML = [['', 'Everything'], ...Object.entries(KINDS), ['art', '🎨 Painted']].map(([k, l]) => `<button type="button" data-k="${k}" aria-pressed="${k === ''}">${l}</button>`).join('');
  $$('#mo-kinds button').forEach(b => b.addEventListener('click', () => { kind = b.dataset.k; $$('#mo-kinds button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(); }));
  function draw() {
    const q = $('#mo-q').value.trim().toLowerCase(), ch = sel.value, hero = hs.value;
    const hay = m => [m.title, m.blurb, m.quote?.x, ...(m.lines || []).map(l => l.w + ' ' + l.x), S[m.s]?.title, ...(m.pcs || []).map(id => H[id]?.name)].join(' ').toLowerCase();
    const list = all.filter(m => (!ch || chOf(m.s) === ch) && (!kind || (kind === 'art' ? m.art : m.kind === kind)) && (!hero || (m.pcs || []).includes(hero)) && (!q || hay(m).includes(q)));
    if (kind || hero) list.sort(byRank);
    $('#moments').innerHTML = list.length ? list.map(m => momentCard(m)).join('') : `<p class="empty">${D.moments.length ? 'Nothing matches that.' : 'The moments are still being dug out of the recordings. Check back soon.'}</p>`;
  }
  $('#mo-q').addEventListener('input', draw);
  sel.addEventListener('change', draw);
  hs.addEventListener('change', draw);
  $('#mo-rand').addEventListener('click', () => {
    if (!all.length) return;
    $('#mo-q').value = ''; sel.value = ''; hs.value = ''; kind = ''; $$('#mo-kinds button').forEach(x => x.setAttribute('aria-pressed', String(!x.dataset.k))); draw();
    const m = all[Math.floor(Math.random() * all.length)];
    const card = $('#m-' + CSS.escape(m.id));
    card.scrollIntoView({ block: 'center' });
    const clip = $('.clip', card);
    if (clip) clip.click();
    else { const btn = $('.play', card); if (btn) playClip(m.audio, btn); }
  });
  draw();
}

/* ---------- heroes ---------- */
const GROUPS = [['party', 'The party today'], ['companion', 'Companions'], ['fallen', 'The fallen']];
function heroStats(h) {
  const ms = D.moments.filter(m => (m.pcs || []).includes(h.id));
  const sh = D.shorts.filter(c => (c.pcs || []).includes(h.id));
  // audio moments and channel Shorts compete for the top three
  const pool = k => [...ms.filter(m => m.kind === k), ...sh.filter(c => c.mood === k)];
  return { ms, sh, funny: pool('funny'), epic: pool('epic') };
}
const card = x => x.mood ? shortCard(x) : momentCard(x);
function renderHeroes() {
  $('#heroes-list').innerHTML = GROUPS.map(([g, label]) => {
    const hs = D.heroes.filter(h => h.group === g);
    return `<h3 class="group">${label}</h3><div class="heroes">${hs.map(h => {
      const st = heroStats(h);
      return `<a class="pc ${g === 'fallen' ? 'gone' : ''} c-${esc(h.c)}" href="#/hero/${esc(h.id)}"><img src="${esc(h.img)}" alt="Portrait of ${esc(h.name)}"><div><h3>${esc(h.name)}</h3><div class="who">${esc(h.who)}</div></div>
        <p>${esc(h.bio)}</p>${h.tag ? `<p class="q">${esc(h.tag)}</p>` : ''}
        <div class="pc-foot">${st.ms.length + st.sh.length ? `<span>★ ${st.ms.length + st.sh.length} moments &amp; clips</span>` : ''}${h.arc.length ? `<span>${h.arc.length} session${h.arc.length > 1 ? 's' : ''} in the chronicle</span>` : ''}<span class="go">Open →</span></div></a>`;
    }).join('')}</div>`;
  }).join('');
}
function renderHero(id) {
  const h = H[id];
  if (!h) { location.hash = '#/heroes'; return; }
  const st = heroStats(h);
  const top = list => list.slice().sort(byRank).slice(0, 3);
  const quotes = D.moments.filter(m => m.quote && m.quote.w === h.name.split(' ')[0]);
  const i = D.heroes.indexOf(h), prev = D.heroes[i - 1], next = D.heroes[i + 1];
  const span = h.to ? `Sessions ${h.from}–${h.to}` : `Session ${h.from} onwards`;
  const first = h.name.split(' ')[0];
  const painted = D.art.filter(m => (m.pcs || []).includes(h.id));
  const cover = painted.slice().sort(byRank)[0];
  const none = k => h.to && h.to < 14 ? `Sessions 1–13 were never recorded in full, so ${esc(first)}'s ${k} moments live on only in legend.` : `No ${k} moments with ${esc(first)} have been clipped yet.`;
  const block = (title, list, empty) => `<h3 class="sec">${title}</h3>${list.length ? `<div class="moments">${list.map(card).join('')}</div>` : `<p class="empty">${empty}</p>`}`;
  const shown = [...top(st.epic), ...top(st.funny)];
  const others = [...st.ms, ...st.sh].filter(m => !shown.includes(m)).sort((a, b) => a.s - b.s || (a.t || 0) - (b.t || 0));
  const el = $('#v-hero');
  el.innerHTML = `<div class="sp-nav">
      <a class="btn" href="#/heroes">← All heroes</a>
      <span>${prev ? `<a class="btn" href="#/hero/${esc(prev.id)}">‹ ${esc(prev.name.split(' ')[0])}</a> ` : ''}${next ? `<a class="btn" href="#/hero/${esc(next.id)}">${esc(next.name.split(' ')[0])} ›</a>` : ''}</span>
    </div>
    <div class="hp-head c-${esc(h.c)}${cover ? ' has-art' : ''}">
      <img src="${esc(h.img)}" alt="Portrait of ${esc(h.name)}" class="${h.group === 'fallen' ? 'gone' : ''}">
      <div>
        <div class="kicker">${esc(GROUPS.find(g => g[0] === h.group)[1])} · ${span}</div>
        <h2>${esc(h.name)}${h.group === 'fallen' ? ' <span class="dagger">†</span>' : ''}</h2>
        <div class="sp-meta"><span>${esc(h.who)}</span></div>
        <p class="sp-text">${esc(h.bio)}</p>
        ${h.tag ? `<p class="hp-tag">${esc(h.tag)}</p>` : ''}
        <div class="hp-stats"><div class="stat"><b>${st.ms.length + st.sh.length}</b><span>moments &amp; clips</span></div><div class="stat"><b>${st.epic.length}</b><span>epic</span></div><div class="stat"><b>${st.funny.length}</b><span>funny</span></div><div class="stat"><b>${h.arc.length}</b><span>sessions in the chronicle</span></div></div>
      </div>
    </div>
    ${block('Top 3 epic moments', top(st.epic), none('epic'))}
    ${block('Top 3 funny moments', top(st.funny), none('funny'))}
    ${quotes.length ? `<h3 class="sec">Said at the table</h3><div class="quotes">${quotes.map(m => `<figure class="quote" data-audio="${esc(m.audio)}" role="button" tabindex="0" aria-label="Play quote"><span class="ic">${SPEAK}</span><blockquote>${esc(m.quote.x)}</blockquote><figcaption><span class="who">${esc(m.quote.w)}</span> <span class="ctx">· Session ${m.s}, ${fmtT(m.t)}</span></figcaption></figure>`).join('')}</div>` : ''}
    ${painted.length ? `<h3 class="sec">Painted moments</h3><div class="art-row">${painted.map(m => `<figure>${artFig(m, '(max-width: 700px) 100vw, 340px')}<figcaption>${esc(m.title)} · <a href="#/session/${m.s}">S${m.s}</a></figcaption></figure>`).join('')}</div>` : ''}
    ${h.arc.length ? `<h3 class="sec">The story so far</h3><ol class="arc">${h.arc.map(a => `<li><a class="arc-n" href="#/session/${a.n}">S${a.n}</a><div><a class="arc-t" href="#/session/${a.n}">${esc(S[a.n].title)}</a><p>${a.x}</p></div></li>`).join('')}</ol>` : ''}
    ${others.length ? block(`More with ${esc(h.name.split(' ')[0])}`, others, '') : ''}`;
  if (cover) $('.hp-head', el).style.setProperty('--art', cssUrl(cover.art.web || cover.art.src));
}

/* ---------- painted moments ---------- */
function renderArt() {
  $('#art-grid').innerHTML = D.art.length ? D.art.map(m => `<figure class="art-card">${artFig(m, '(max-width: 700px) 100vw, 520px')}
    <figcaption><div class="mh">${m.audio ? `<button class="play" data-audio="${esc(m.audio)}" aria-label="Play">${PLAY}<span class="ring"></span></button>` : ''}
      <div><h4>${esc(m.title)}</h4><div class="ms"><a href="#/session/${m.s}">Session ${m.s} · ${esc(S[m.s]?.title || '')}</a></div></div></div>
      ${m.pcs && m.pcs.length ? `<div class="hchips">${heroChips(m)}</div>` : ''}</figcaption></figure>`).join('')
    : '<p class="empty">The first paintings are still drying. Check back soon.</p>';
}

/* ---------- quotes ---------- */
function renderQuotes() {
  const qs = D.moments.filter(m => m.quote).map(m => ({ ...m.quote, m }));
  const who = [...new Set(qs.map(q => q.w))].sort();
  $('#q-filters').innerHTML = ['Everyone', ...who].map((w, i) => `<button type="button" data-w="${i ? esc(w) : ''}" aria-pressed="${i === 0}">${esc(w)}</button>`).join('');
  function draw(w) {
    const list = qs.filter(q => !w || q.w === w);
    $('#quotes').innerHTML = list.length ? list.map(q => `<figure class="quote" ${q.m.audio ? `data-audio="${esc(q.m.audio)}" role="button" tabindex="0" aria-label="Play quote"` : ''}>
      ${q.m.audio ? `<span class="ic">${SPEAK}</span>` : ''}
      <blockquote>${esc(q.x)}</blockquote>
      <figcaption><span class="who">${esc(q.w)}</span> <span class="ctx">· Session ${q.m.s}, ${fmtT(q.m.t)}</span></figcaption></figure>`).join('') : '<p class="empty">Quotes are still being transcribed. Check back soon.</p>';
  }
  $$('#q-filters button').forEach(b => b.addEventListener('click', () => { $$('#q-filters button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(b.dataset.w); }));
  draw('');
}

/* ---------- discord ---------- */
function renderDiscord() {
  const box = $('#discord');
  if (!D.posts.length) { box.innerHTML = '<p class="empty">The Discord archive is still being sorted. Check back soon.</p>'; return; }
  const groups = D.chapters.map(c => ({ c, posts: c.sessions.flatMap(n => S[n].posts) })).filter(g => g.posts.length);
  if (D.prePosts.length) groups.unshift({ c: { num: '0', title: 'Before it all began', place: 'Ballers & Bandits' }, posts: D.prePosts });
  $('#dc-filters').innerHTML = [`<button type="button" data-g="" aria-pressed="true">All arcs</button>`, ...groups.map(g => `<button type="button" data-g="${esc(g.c.num)}" aria-pressed="false">${esc(g.c.num === '0' ? 'Before' : g.c.num)} · ${esc(g.c.title)}</button>`)].join('');
  box.innerHTML = groups.map(g => {
    const first = g.posts[0].t, last = g.posts[g.posts.length - 1].t;
    return `<section class="dgroup" data-g="${esc(g.c.num)}"><h3>${g.c.num === '0' ? '' : esc(g.c.num) + ' · '}${esc(g.c.title)}</h3><div class="ch-meta">${g.posts.length} posts · ${fmtDate(first)} – ${fmtDate(last)}</div>${postsHtml(g.posts, 'dg' + g.c.num)}</section>`;
  }).join('');
  $$('#dc-filters button').forEach(b => b.addEventListener('click', () => {
    $$('#dc-filters button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    $$('#discord .dgroup').forEach(sct => { sct.hidden = !!b.dataset.g && sct.dataset.g !== b.dataset.g; });
  }));
}

/* ---------- watch ---------- */
function renderWatch() {
  const V = D.videos;
  const link = (u, t, k) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}<span class="k">${esc(k || '')}</span></a>`;
  const yt = id => 'https://www.youtube.com/watch?v=' + id;
  const shorts = Object.entries(V.clips).filter(([id, c]) => c.kind === 'short' && id !== V.intro);
  $('#watch').innerHTML = `
    <h3 class="mh">Remembering the fallen</h3><div class="media">${link(yt(V.tribute), 'Lyrial & Nate Tribute', 'tribute')}${link('https://www.youtube.com/shorts/' + V.intro, 'War of the Gods: Intro', 'short')}${link(yt(V.summary), 'An AI Summary of Sessions 1–13', 'summary')}</div>
    <h3 class="mh">The gods reveal themselves</h3><div class="media">${V.reveals.map(r => link(yt(r.id), r.title, 'reveal')).join('')}</div>
    <h3 class="mh">Hymns</h3><div class="media">${V.hymns.map(r => link(yt(r.id), r.title, 'hymn')).join('')}</div>
    <h3 class="mh">Every session</h3><div class="media">${order.filter(n => S[n].video).map(n => link(yt(S[n].video.id), `${n} · ${S[n].video.title}`, 'session')).join('')}</div>
    <h3 class="mh">Short clips</h3><div class="media">${shorts.map(([id, c]) => link('https://www.youtube.com/shorts/' + id, c.title, 'short')).join('')}</div>`;
}

/* ---------- map ---------- */
let MAP = null;
function initMap() {
  const H = D.map.h, W = D.map.w, xy = (x, y) => L.latLng(H - y, x);
  const map = L.map('leaf', { crs: L.CRS.Simple, minZoom: -2, maxZoom: 2, zoomSnap: .25, attributionControl: false, zoomControl: true });
  const bounds = [[0, 0], [H, W]];
  L.imageOverlay(D.map.src, bounds).addTo(map);
  map.setView([H / 2, W / 2], map.getBoundsZoom(bounds, true));
  map.setMaxBounds([[-H * .15, -W * .15], [H * 1.15, W * 1.15]]);
  const locs = Object.fromEntries(D.locations.map(l => [l.id, l]));
  const path = order.filter(n => S[n].loc).map(n => ({ n, l: locs[S[n].loc] }));
  const pins = {};
  for (const l of D.locations) {
    const at = path.filter(p => p.l.id === l.id).map(p => p.n);
    if (!at.length) continue;
    const html = l.id === 'anomaly' ? '<div class="anomaly"></div>' : `<div class="lpin">${at.length}</div>`;
    const m = L.marker(xy(l.x, l.y), { icon: L.divIcon({ className: '', html, iconSize: l.id === 'anomaly' ? [46, 46] : [30, 30] }), title: l.name, riseOnHover: true }).addTo(map);
    m.bindPopup(`<h5>${esc(l.name)}</h5>${l.blurb ? `<p style="margin:0 0 6px">${esc(l.blurb)}</p>` : ''}${at.map(n => `<a href="#/map/${n}">S${n} · ${esc(S[n].title)}</a>`).join('<br>')}`);
    pins[l.id] = { m, first: at[0] };
  }
  const trail = L.polyline([], { color: '#F0904A', weight: 3.5, opacity: .9, dashArray: '9 9' }).addTo(map);
  const ahead = L.polyline(path.map(p => xy(p.l.x, p.l.y)), { color: '#8193A4', weight: 2, opacity: .25, dashArray: '2 8' }).addTo(map);
  ahead.bringToBack();
  const party = L.marker(xy(path[0].l.x, path[0].l.y), { icon: L.divIcon({ className: '', html: '<div class="party"></div>', iconSize: [22, 22] }), interactive: false, zIndexOffset: 1000 }).addTo(map);
  const range = $('#mp-range');
  range.max = order[order.length - 1]; $('#mp-last').textContent = 'S' + range.max;
  let timer = null;
  function go(n, pan = true) {
    n = Math.max(1, Math.min(+range.max, n)); range.value = n;
    const upto = path.filter(p => p.n <= n);
    const pts = []; upto.forEach(p => { const q = xy(p.l.x, p.l.y); if (!pts.length || !pts[pts.length - 1].equals(q)) pts.push(q); });
    trail.setLatLngs(pts);
    const cur = upto[upto.length - 1] || path[0];
    party.setLatLng(xy(cur.l.x, cur.l.y));
    for (const [id, p] of Object.entries(pins)) {
      const el = p.m.getElement()?.firstChild; if (!el) continue;
      if (el.classList.contains('anomaly')) { el.style.display = p.first > n ? 'none' : ''; continue; }
      el.classList.toggle('future', p.first > n); el.classList.toggle('here', id === cur.l.id);
    }
    if (pan) map.panTo(xy(cur.l.x, cur.l.y), { animate: true, duration: .6 });
    const s = S[n];
    $('#mp-body').innerHTML = `<div class="day">${dayHtml(s)}</div><div class="s-title"><span class="no">Session ${n} · ${esc(cur.l.name)}</span></div><h4><a href="#/session/${n}">${esc(s.title)}</a></h4><p>${s.text}</p>${tagsHtml(s)}
      ${s.moments.slice(0, 3).map(m => `<div class="mh" style="display:flex;gap:10px;align-items:center;margin-top:10px">${m.audio ? `<button class="play" data-audio="${esc(m.audio)}" aria-label="Play">${PLAY}<span class="ring"></span></button>` : ''}<span style="font-size:14.5px">${esc(m.title)}</span></div>`).join('')}
      <p style="margin-top:12px"><a href="#/session/${n}">Open Session ${n} →</a></p>`;
    try { history.replaceState(null, '', '#/map/' + n); } catch (e) {}
  }
  range.addEventListener('input', () => { stop(); go(+range.value); });
  $('#mp-prev').addEventListener('click', () => { stop(); go(+range.value - 1); });
  $('#mp-next').addEventListener('click', () => { stop(); go(+range.value + 1); });
  function stop() { clearInterval(timer); timer = null; $('#mp-play').textContent = '▶ Play the journey'; }
  $('#mp-play').addEventListener('click', () => {
    if (timer) return stop();
    if (+range.value >= +range.max) go(1);
    $('#mp-play').textContent = '❚❚ Pause';
    timer = setInterval(() => { if (+range.value >= +range.max) return stop(); go(+range.value + 1); }, 2200);
  });
  MAP = { map, go, stop };
}

/* ---------- router ---------- */
const hero = $('#hero');
function route() {
  const h = location.hash.replace(/^#\/?/, '');
  const [v0, arg] = h.split(/[/#]/);
  let v = v0 || 'timeline';
  const known = ['timeline', 'session', 'hero', 'map', 'moments', 'quotes', 'discord', 'fallen', 'heroes', 'gods', 'people', 'watch', 'art'];
  if (!known.includes(v)) v = ['chronicle'].includes(v) ? 'timeline' : 'timeline';
  $$('section.view').forEach(s => { s.hidden = s.dataset.view !== v; });
  $$('#tabs a').forEach(a => a.setAttribute('aria-current', a.dataset.v === v || (v === 'session' && a.dataset.v === 'timeline') || (v === 'hero' && a.dataset.v === 'heroes') ? 'page' : 'false'));
  hero.classList.toggle('slim', v !== 'timeline');
  if (MAP && v !== 'map') MAP.stop();
  if (v === 'session') { renderSession(+arg); window.scrollTo(0, 0); return; }
  if (v === 'hero') { renderHero(arg); window.scrollTo(0, 0); $('#tabs a[data-v="heroes"]').scrollIntoView({ block: 'nearest', inline: 'nearest' }); return; }
  if (!rendered[v]) {
    rendered[v] = true;
    ({ timeline: renderTimeline, moments: renderMoments, quotes: renderQuotes, discord: renderDiscord, watch: renderWatch, map: initMap, heroes: renderHeroes, art: renderArt }[v] || (() => {}))();
  }
  if (v === 'map') { MAP.map.invalidateSize(); MAP.go(+arg || +store.get('wotg-map') || 1); }
  if (v === 'map' && arg) store.set('wotg-map', arg);
  const a = $(`#tabs a[data-v="${v}"]`); if (a) a.scrollIntoView({ block: 'nearest', inline: 'nearest' });
}
window.addEventListener('hashchange', () => { if (!$('#lb').hidden) lbClose(); route(); if (!location.hash.startsWith('#/map')) window.scrollTo({ top: 0 }); });

/* ---------- boot ---------- */
fetch('data/site.json?v=' + (document.currentScript?.src.split('v=')[1] || '')).then(r => r.json()).then(data => {
  D = data;
  for (const s of D.sessions) { S[s.n] = s; order.push(s.n); s.moments = []; s.posts = []; }
  D.heroes = D.heroes || [];
  for (const h of D.heroes) H[h.id] = h;
  // the channel's highlight Shorts, each placed in its session
  D.shorts = [];
  for (const s of D.sessions) for (const c of s.clips) { const v = D.videos.clips[c.id]; if (v && v.kind === 'short') D.shorts.push({ ...v, id: c.id, s: s.n }); }
  for (const m of D.moments) S[m.s]?.moments.push(m);
  D.prePosts = [];
  for (const p of D.posts) (S[p.s] ? S[p.s].posts : D.prePosts).push(p);
  for (const s of D.sessions) s.moments.sort((a, b) => a.t - b.t);
  D.art = D.moments.filter(m => m.art).sort((a, b) => a.s - b.s || a.t - b.t);
  lbGroups.art = D.art.map(m => ({ src: m.art.web || m.art.src, alt: m.art.alt, cap: artCap(m) }));
  if (D.art.length) {
    // a different painting behind the title on every visit
    const m = D.art[Math.floor(Math.random() * D.art.length)];
    hero.classList.add('has-art');
    hero.style.setProperty('--art', cssUrl(m.art.web || m.art.src));
    $('#hero-cap').innerHTML = `<a href="#/art">🎨 ${esc(m.title)} · Session ${m.s}</a>`;
  }
  if (D.trailer && $('#hero-acts')) {
    lbGroups.trailer = [{ k: 'vid', src: D.trailer.src, poster: D.trailer.poster, cap: '<b>War of the Gods</b> · the trailer' }];
    $('#hero-acts').innerHTML = `<button type="button" class="btn primary trailer-btn" data-lb="trailer" data-i="0">${PLAY}<span>Watch the trailer</span></button>`;
  }
  $('#stats').innerHTML = [
    [order.length, 'sessions played'], ['~' + D.stats.days, 'days in Aurilia'], [D.chapters.length, 'chapters'],
    [D.moments.length || '…', 'best moments'], [D.posts.length || '…', 'Discord posts'], ...(D.art.length ? [[D.art.length, 'painted moments']] : []), ['300+', 'Frost Wardens over a waterfall']
  ].map(([b, s]) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join('');
  $('#hstrip').innerHTML = D.heroes.filter(h => h.group !== 'fallen' || heroStats(h).ms.length).map(h =>
    `<a href="#/hero/${esc(h.id)}" class="c-${esc(h.c)}${h.group === 'fallen' ? ' gone' : ''}" title="${esc(h.name)}"><img src="${esc(h.img)}" alt=""><span>${esc(h.name.split(' ')[0])}</span></a>`).join('');
  wireStaticGallery();
  route();
}).catch(err => { $('main').innerHTML = `<p class="empty">Couldn't load the chronicle (${esc(err.message)}).</p>`; });
})();
