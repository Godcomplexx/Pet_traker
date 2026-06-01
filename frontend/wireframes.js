/* ============================================================
   petpro — wireframe interactivity + pixel pet
   ============================================================ */
(function(){
'use strict';

/* ---------------- navigation ---------------- */
let lastScreen = 'dashboard';
function go(name){
  const cur = document.querySelector('.screen.on');
  if(cur && name==='taskdetail'){ lastScreen = cur.id.replace('screen-',''); }
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('on'));
  const el = document.getElementById('screen-'+name);
  if(el) el.classList.add('on');
  const navKey = ({projdetail:'projects',artdetail:'articles',taskdetail:'mytasks',lab:null,profile:null,taskdetail:'mytasks'})[name] ?? name;
  document.querySelectorAll('#nav a').forEach(a=>a.classList.toggle('active', a.dataset.go===navKey));
  const main = document.querySelector('.main'); if(main) main.scrollTop=0;
  try{ localStorage.setItem('petpro_screen', name); }catch(e){}
}
window.go = go;

document.addEventListener('click', e=>{
  const t = e.target.closest('[data-go]');
  if(t){ e.preventDefault(); go(t.dataset.go); }
});

/* ---------------- auth ---------------- */
function enterApp(){
  document.getElementById('auth').classList.remove('on');
  document.getElementById('app').style.display='grid';
  try{ localStorage.setItem('petpro_auth','1'); }catch(e){}
}
const authGo = document.getElementById('authGo');
if(authGo) authGo.addEventListener('click', enterApp);
document.querySelectorAll('#authTabs button').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('#authTabs button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  document.querySelector('[data-reg]').style.display = b.dataset.tab==='reg'?'block':'none';
}));
const logoutBtn = document.getElementById('logoutBtn');
if(logoutBtn) logoutBtn.addEventListener('click',()=>{
  try{ localStorage.removeItem('petpro_auth'); }catch(e){}
  document.getElementById('app').style.display='none';
  document.getElementById('auth').classList.add('on');
});

/* ---------------- segmented controls + filters ---------------- */
document.addEventListener('click', e=>{
  const b = e.target.closest('.seg button');
  if(!b) return;
  b.parentElement.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  if(b.closest('#mtFilters')) applyFilters();
});
function activeVal(sel){
  const seg = document.querySelector('#mtFilters .seg[data-filter="'+sel+'"] button.on');
  return seg ? seg.dataset.val : 'all';
}
function applyFilters(){
  const scope = activeVal('scope'), status = activeVal('status'), due = activeVal('due');
  document.querySelectorAll('#mtTeam .task, #mtPersonal .task').forEach(t=>{
    let ok = true;
    if(scope!=='all' && t.dataset.scope!==scope) ok=false;
    if(status!=='all' && t.dataset.status!==status) ok=false;
    if(due==='today' && t.dataset.due!=='today') ok=false;
    if(due==='week' && !(t.dataset.due==='today'||t.dataset.due==='week')) ok=false;
    t.classList.toggle('hidden', !ok);
  });
}

/* ---------------- pet XP state ---------------- */
const pet = { xp:640, today:30, name:'Кодзи' };
function levelOf(xp){ return Math.floor(xp/100)+1; }
function renderPet(){
  const lvl = levelOf(pet.xp);
  const next = lvl*100;
  const pct = Math.min(100, pet.xp - (lvl-1)*100);
  document.querySelectorAll('[data-petfill]').forEach(el=> el.style.width = pct+'%');
  document.querySelectorAll('[data-petlevel]').forEach(el=> el.textContent = lvl);
  document.querySelectorAll('[data-petlevelnext]').forEach(el=> el.textContent = lvl+1);
  document.querySelectorAll('[data-petlabel]').forEach(el=> el.textContent = pet.xp+' / '+next+' XP');
  document.querySelectorAll('[data-petnum]').forEach(el=> el.textContent = pet.xp+'/'+next);
  document.querySelectorAll('[data-pettotal]').forEach(el=> el.textContent = pet.xp);
  document.querySelectorAll('[data-todayxp]').forEach(el=> el.textContent = pet.today);
  document.querySelectorAll('[data-petname]').forEach(el=> el.textContent = pet.name);
}
function addXp(n){
  const before = levelOf(pet.xp);
  pet.xp += n; pet.today += n;
  renderPet();
  const after = levelOf(pet.xp);
  if(after>before) setTimeout(()=>toast('⬆ Уровень '+after+'! Кодзи подрос', 'lvl'), 350);
}

/* ---------------- toasts ---------------- */
function toast(text, cls){
  const wrap = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast sk '+(cls||'xp');
  el.textContent = text;
  wrap.appendChild(el);
  setTimeout(()=>{ el.classList.add('fade'); setTimeout(()=>el.remove(),400); }, 2200);
}

/* ---------------- feed / reward helpers ---------------- */
function prependFeed(inner){
  document.querySelectorAll('[data-feed="dash"],[data-feed="team"]').forEach(f=>{
    const it = document.createElement('div');
    it.className = 'it fresh';
    it.innerHTML = '<div class="av">АП</div><div>'+inner+'<div class="when">сейчас</div></div>';
    f.insertBefore(it, f.firstChild);
  });
}
function prependReward(label, xp, priv){
  const list = document.querySelector('[data-feed="rewards"]');
  if(!list) return;
  const row = document.createElement('div');
  row.className = 'task'+(priv?' priv':'');
  row.innerHTML = '<div class="t" style="cursor:default;">✦ '+label+(priv?' <span class="lock">🔒</span>':'')+'</div>'+
                  '<span class="chip '+(priv?'priv':'xp')+'">+'+xp+' XP</span>';
  list.insertBefore(row, list.firstChild);
}

/* ---------------- task helpers ---------------- */
function taskTitle(task){
  const t = task.querySelector('.t').cloneNode(true);
  t.querySelectorAll('.tag,.mono,.lock,.chip').forEach(n=>n.remove());
  return t.textContent.trim();
}
function recount(){
  document.querySelectorAll('[data-count="open"]').forEach(el=>{
    const card = el.closest('.card');
    const n = card.querySelectorAll('.task[data-kind]:not(.done)').length;
    el.textContent = n+' открыто';
  });
}
function completeTask(task){
  if(!task || !task.dataset.kind) return;
  const chk = task.querySelector('.chk');
  task.classList.add('done'); if(chk) chk.classList.add('done');
  task.dataset.status = 'done';
  if(!task.dataset.awarded){
    task.dataset.awarded = '1';
    const xp = parseInt(task.dataset.xp||'10',10);
    const personal = task.dataset.kind==='personal';
    const title = taskTitle(task);
    addXp(xp);
    task.classList.add('flash');
    if(personal){
      toast('+'+xp+' XP · личная задача 🔒','priv');
      prependReward('Личная задача', xp, true);   /* privacy: no title */
    } else {
      toast('+'+xp+' XP · задача закрыта','xp');
      prependFeed('<span>Анна закрыла «'+title+'»</span> <span class="chip xp">+'+xp+'</span>');
      prependReward('Задача «'+title+'»', xp, false);
    }
  }
  recount();
}
/* checkbox toggle (complete / reopen) */
document.addEventListener('click', e=>{
  const chk = e.target.closest('.chk');
  if(!chk) return;
  const task = chk.closest('.task');
  if(!task || !task.dataset.kind) return;
  if(task.classList.contains('done')){      /* reopen — no XP removed (FR-GAME-6) */
    task.classList.remove('done'); chk.classList.remove('done'); task.dataset.status='open';
    recount();
  } else {
    completeTask(task);
  }
});

/* ---------------- task -> task detail ---------------- */
let tdSrc = null;
function openTaskDetail(task){
  tdSrc = task;
  const personal = task.dataset.kind==='personal';
  const title = taskTitle(task);
  const type = (task.querySelector('.tag')||{}).textContent || (personal?'PERSONAL':'OTHER');
  const ctx  = (task.querySelector('.mono')||{}).textContent || (personal?'личная':'командная');
  let scope = 'WORKSPACE', vis='WORKSPACE';
  if(personal){ scope='PERSONAL'; vis='PRIVATE'; }
  else if(/ARTICLE|МРТ/i.test(ctx)) { scope='ARTICLE'; vis='ARTICLE'; }
  else if(/PROJECT|Portal/i.test(ctx)) { scope='PROJECT'; vis='PROJECT'; }
  const prio = ((task.querySelector('.prio')||{className:''}).className.match(/\b(LOW|MEDIUM|HIGH|URGENT)\b/)||['','MEDIUM'])[1];
  const done = task.classList.contains('done');
  document.getElementById('tdScope').textContent = scope;
  document.getElementById('tdType').textContent = type.replace(/^·\s*/,'');
  document.getElementById('tdVis').textContent = 'visibility: '+vis;
  document.getElementById('tdTitle').textContent = title;
  document.getElementById('tdCtx').textContent = ctx;
  document.getElementById('tdPrio').textContent = prio;
  document.getElementById('tdStatus').firstChild ?
    (document.getElementById('tdStatus').childNodes[0].textContent = (done?'DONE':'IN_PROGRESS')+' ') :
    (document.getElementById('tdStatus').textContent = (done?'DONE':'IN_PROGRESS')+' ▾');
  document.getElementById('tdStatus').innerHTML = (done?'DONE':'IN_PROGRESS')+' ▾';
  const cbtn = document.getElementById('tdComplete');
  cbtn.style.display = done ? 'none' : '';
  go('taskdetail');
}
document.addEventListener('click', e=>{
  const t = e.target.closest('.task .t');
  if(!t) return;
  const task = t.closest('.task');
  if(!task || !task.dataset.kind) return;
  openTaskDetail(task);
});
const tdBack = document.getElementById('tdBack');
if(tdBack) tdBack.addEventListener('click', ()=> go(lastScreen));
const tdComplete = document.getElementById('tdComplete');
if(tdComplete) tdComplete.addEventListener('click', ()=>{
  if(tdSrc){ completeTask(tdSrc); }
  document.getElementById('tdStatus').innerHTML = 'DONE ▾';
  tdComplete.style.display='none';
  const tl = document.getElementById('tdTl');
  if(tl){ const ev=document.createElement('div'); ev.className='ev xp';
    ev.innerHTML='TASK_COMPLETED <span class="chip xp">+10</span><div class="mono">Анна · сейчас</div>';
    tl.insertBefore(ev, tl.firstChild); }
});

/* ---------------- status selectors ---------------- */
const STATUS = {
  article:{ list:['IDEA','PLANNING','WRITING','INTERNAL_REVIEW','REVISION','SUBMITTED','UNDER_REVIEW','ACCEPTED','PUBLISHED','ARCHIVED'],
            reward:{SUBMITTED:50,ACCEPTED:100,PUBLISHED:150} },
  project:{ list:['IDEA','PLANNING','ACTIVE','PAUSED','IN_REVIEW','DONE','ARCHIVED'], reward:{DONE:50} },
  task:{ list:['TODO','IN_PROGRESS','IN_REVIEW','DONE','CANCELLED'], reward:{DONE:10} }
};
let openMenu = null;
function closeMenu(){ if(openMenu){ openMenu.remove(); openMenu=null; } }
document.addEventListener('click', e=>{
  const chip = e.target.closest('.statussel');
  if(!chip){ if(!e.target.closest('.menu')) closeMenu(); return; }
  e.stopPropagation();
  closeMenu();
  const kind = chip.dataset.stkind;
  const cfg = STATUS[kind]; if(!cfg) return;
  const menu = document.createElement('div');
  menu.className = 'menu sk2';
  cfg.list.forEach(st=>{
    const b = document.createElement('button');
    const rw = cfg.reward[st];
    b.innerHTML = st + (rw?'<span class="rw">+'+rw+' XP</span>':'');
    b.addEventListener('click', ()=>{
      chip.innerHTML = st+' ▾';
      const screen = chip.closest('.screen');
      const tl = screen && screen.querySelector('.tl');
      if(tl){ const ev=document.createElement('div'); ev.className='ev'+(rw?' xp':'');
        ev.innerHTML = (kind==='article'?'ARTICLE':kind==='project'?'PROJECT':'TASK')+'_STATUS → '+st+
          (rw?' <span class="chip xp">+'+rw+'</span>':'')+'<div class="mono">Анна · сейчас</div>';
        tl.insertBefore(ev, tl.firstChild); }
      if(rw){
        addXp(rw);
        toast('+'+rw+' XP · статус '+st,'xp');
        if(kind!=='task') prependFeed('<span>Анна: '+(kind==='article'?'статья':'проект')+' → <b>'+st+'</b></span> <span class="chip xp">+'+rw+'</span>');
      }
      closeMenu();
    });
    menu.appendChild(b);
  });
  document.body.appendChild(menu);
  const r = chip.getBoundingClientRect();
  menu.style.left = Math.min(r.left, window.innerWidth-190)+'px';
  menu.style.top  = (r.bottom+6)+'px';
  openMenu = menu;
});

/* ---------------- notifications ---------------- */
function updateBadge(){
  const n = document.querySelectorAll('#notifList [data-notif="unread"]').length;
  const badge = document.getElementById('notifBadge');
  if(!badge) return;
  badge.textContent = n;
  badge.classList.toggle('hide', n===0);
}
function readNotif(task){
  task.dataset.notif='read';
  task.style.opacity='.55';
  const dot = task.querySelector('.statusdot'); if(dot) dot.style.background='var(--line)';
  const btn = task.querySelector('.notif-read'); if(btn) btn.remove();
  updateBadge();
}
document.addEventListener('click', e=>{
  const b = e.target.closest('.notif-read');
  if(b){ readNotif(b.closest('.task')); }
});
const markAll = document.getElementById('markAll');
if(markAll) markAll.addEventListener('click', ()=>{
  document.querySelectorAll('#notifList [data-notif="unread"]').forEach(readNotif);
});

/* ---------------- pet rename ---------------- */
const renamePet = document.getElementById('renamePet');
if(renamePet) renamePet.addEventListener('click', ()=>{
  const v = prompt('Имя питомца', pet.name);
  if(v && v.trim()){ pet.name=v.trim(); renderPet(); const i=document.getElementById('petNameInput'); if(i) i.value=pet.name; }
});
const petNameInput = document.getElementById('petNameInput');
if(petNameInput) petNameInput.addEventListener('input', ()=>{ pet.name=petNameInput.value||'Питомец'; renderPet(); });

/* ---------------- add task ---------------- */
function makeTaskRow(title, personal){
  const row = document.createElement('div');
  if(personal){
    row.className='task priv'; row.dataset.kind='personal'; row.dataset.xp='5';
    row.dataset.scope='personal'; row.dataset.status='open'; row.dataset.due='today';
    row.innerHTML='<div class="chk"></div><div class="t">'+title+' <span class="tag" style="border-color:var(--priv);color:var(--priv)">PERSONAL</span><div class="mono">личная</div></div><span class="chip priv">+5</span>';
  } else {
    row.className='task'; row.dataset.kind='team'; row.dataset.xp='10';
    row.dataset.scope='team'; row.dataset.status='open'; row.dataset.due='week';
    row.innerHTML='<div class="prio MEDIUM"></div><div class="chk"></div><div class="t">'+title+' <span class="tag">ADMIN</span><div class="mono">WORKSPACE</div></div><span class="muted sm">скоро</span>';
  }
  return row;
}
const addPersonal = document.getElementById('addPersonal');
if(addPersonal) addPersonal.addEventListener('click', ()=>{
  const v = prompt('Новая личная задача 🔒'); if(!v) return;
  document.getElementById('mtPersonal').insertBefore(makeTaskRow(v,true), document.getElementById('mtPersonal').firstChild);
  applyFilters();
});
const addTeam = document.getElementById('addTeam');
if(addTeam) addTeam.addEventListener('click', ()=>{
  const v = prompt('Новая командная задача'); if(!v) return;
  document.getElementById('mtTeam').insertBefore(makeTaskRow(v,false), document.getElementById('mtTeam').firstChild);
  recount(); applyFilters();
});

/* ============================================================
   PIXEL PET  (CSS-grid sprite, no SVG)
   ============================================================ */
const PET_ROWS = [
  "...bbbb...",
  ".bbbbbbbb.",
  "bbbbbbbbbb",
  "bbebbbbebb",
  "bbebbbbebb",
  "bbbbbbbbbb",
  "bbbbmmbbbb",
  ".bbbbbbbb.",
  "..bb..bb.."
];
function makePixelPet(pal){
  const d = document.createElement('div');
  d.className = 'pixelpet idle';
  if(pal){
    if(pal.body) d.style.setProperty('--pp-body', pal.body);
    if(pal.shade) d.style.setProperty('--pp-shade', pal.shade);
    if(pal.mouth) d.style.setProperty('--pp-mouth', pal.mouth);
  }
  const frag = document.createDocumentFragment();
  PET_ROWS.join('').split('').forEach(ch=>{
    const i = document.createElement('i');
    if(ch==='b') i.className='b';
    else if(ch==='e') i.className='e';
    else if(ch==='m') i.className='m';
    else if(ch==='s') i.className='s';
    frag.appendChild(i);
  });
  d.appendChild(frag);
  return d;
}
function mountPet(el, pal){ if(!el) return; el.appendChild(makePixelPet(pal)); }
mountPet(document.querySelector('[data-pet="mini"]'), null);
mountPet(document.querySelector('[data-pet="hero"]'), null);
mountPet(document.querySelector('[data-pet="big"]'), null);

/* ============================================================
   BOARDS + TABLES
   ============================================================ */
function avs(s){ return '<div class="avstack">'+s.split(',').map((x,i)=>'<div class="avatar '+(i%2?'hatch':'')+'">'+x+'</div>').join('')+'</div>'; }

/* projects */
const PCOLS=[['IDEA','Идея','#b5acce'],['PLANNING','План','#a8c4d4'],['ACTIVE','Активен','#c9a5ba'],
  ['PAUSED','Пауза','#c4b5a0'],['IN_REVIEW','Ревью','#a8b8c8'],['DONE','Готов','#9dbf9b'],['ARCHIVED','Архив','#b8bdb6']];
const PTYPE={RESEARCH:'#9dbf9b',SOFTWARE:'#a8c4d4',PUBLICATION:'#c9a5ba',EXPERIMENT:'#b5acce',ADMIN:'#c4b5a0',OTHER:'#b8bdb6'};
const PROJ={
  IDEA:[['Open-source датасет ЭКГ','RESEARCH','ИВ','']],
  PLANNING:[['Геном растений в засуху','RESEARCH','АП,СД','']],
  ACTIVE:[['Research Portal','SOFTWARE','АП,МК,СД','8/20'],['Диагностика МРТ','PUBLICATION','МК,СД','7/12']],
  PAUSED:[['Миграция инфраструктуры','SOFTWARE','МК','3/14']],
  IN_REVIEW:[['Климат и урожайность','RESEARCH','ИВ','10/10']],
  DONE:[['Пилот сенсоров','EXPERIMENT','ИВ','']],
  ARCHIVED:[['Релиз API v1.2','SOFTWARE','АП','']]
};
function pct(s){ const a=s.split('/'); return Math.round(parseInt(a[0])/parseInt(a[1])*100)||0; }
const pb=document.getElementById('projboard');
if(pb){
  pb.innerHTML=PCOLS.map(function(c){
    const k=c[0], label=c[1], color=c[2]; const items=PROJ[k]||[];
    const cards=items.map(function(it){
      const click = it[0]==='Research Portal' ? ' data-go="projdetail" style="cursor:pointer;"' : '';
      return '<div class="acard soft"'+click+'>'+
        '<div class="row"><span class="tag ptype" style="border-color:'+PTYPE[it[1]]+'">'+it[1]+'</span></div>'+
        '<div class="ttl">'+it[0]+'</div>'+
        (it[3]?'<div class="track"><div class="fill acc" style="width:'+pct(it[3])+'%"></div></div>':'')+
        '<div class="foot">'+avs(it[2])+'<span style="flex:1"></span>'+(it[3]?'<span class="sm muted">'+it[3]+'</span>':'')+'</div></div>';
    }).join('');
    return '<div class="colm"><div class="colhead soft"><span class="statusdot" style="background:'+color+'"></span><b>'+label+'</b><span class="cnt">'+items.length+'</span></div>'+
      (cards||'<div class="ph" style="height:54px;">пусто</div>')+'<button class="btn sm" style="opacity:.7;">+ проект</button></div>';
  }).join('');
}

/* articles */
const ACOLS=[['IDEA','Идея','#bdb4a0'],['PLANNING','План','#9bb0c4'],['WRITING','Пишем','#e07a52'],
  ['INTERNAL_REVIEW','Внутр.','#d8a24a'],['REVISION','Правки','#c98b6b'],['SUBMITTED','Сабмит','#5f9e6e'],
  ['UNDER_REVIEW','Ревью','#7a9b8a'],['ACCEPTED','Принято','#5f9e6e'],['PUBLISHED','Опубл.','#3f7d52']];
const ART={
  IDEA:[['Микробиом и иммунитет','—','ИВ']],
  PLANNING:[['Methodology paper: Portal','PLOS','АП,СД']],
  WRITING:[['Нейросети в диагностике МРТ','Nature Med','АП,МК','7/12'],['Этика ИИ в медицине','—','СД','2/9']],
  INTERNAL_REVIEW:[['Квантовые сенсоры','PRL','МК','9/9']],
  REVISION:[['Климат и урожайность пшеницы','Science','ИВ','10/10']],
  SUBMITTED:[['Полимеры для имплантов','Biomater.','СД,АП']],
  UNDER_REVIEW:[['Нейропластичность сна','—','МК']],
  ACCEPTED:[['CRISPR off-target','Cell','ИВ']],
  PUBLISHED:[['Графен в батареях','Nat.Energy','АП']]
};
const ab=document.getElementById('artboard');
if(ab){
  ab.innerHTML=ACOLS.map(function(c){
    const k=c[0],label=c[1],color=c[2]; const items=ART[k]||[];
    const cards=items.map(function(it){
      const click = it[0].indexOf('МРТ')>-1 ? ' data-go="artdetail" style="cursor:pointer;"' : '';
      return '<div class="acard soft"'+click+'><div class="ttl">'+it[0]+'</div><div class="mono">'+it[1]+'</div>'+
        '<div class="foot">'+avs(it[2])+'<span style="flex:1"></span>'+(it[3]?'<span class="sm muted">'+it[3]+'</span>':'')+'</div></div>';
    }).join('');
    return '<div class="colm"><div class="colhead soft"><span class="statusdot" style="background:'+color+'"></span><b>'+label+'</b><span class="cnt">'+items.length+'</span></div>'+
      (cards||'<div class="ph" style="height:54px;">пусто</div>')+'<button class="btn sm" style="opacity:.7;">+ статья</button></div>';
  }).join('');
}

/* team pets (pixel) */
const PETS=[
  ['Кодзи','Анна П.','капибара',7,40,{body:'#c98a52',shade:'#a66f3a',mouth:'#6e3a22'}],
  ['Тофу','Михаил К.','кот',9,30,{body:'#d8d2c4',shade:'#b4ae9e',mouth:'#8a4a4a'}],
  ['Луна','Ирина В.','лиса',12,88,{body:'#d98a6a',shade:'#b86a4a',mouth:'#6e3322'}],
  ['Пиксель','Сергей Д.','ёж',5,45,{body:'#8a9bb0',shade:'#6d7e94',mouth:'#3a4452'}],
  ['Мокко','Лена З.','панда',8,70,{body:'#e8e4da',shade:'#b6b0a6',mouth:'#5a544c'}],
  ['Бумба','Олег Р.','сова',6,20,{body:'#b89ad0',shade:'#9a7cb0',mouth:'#5a4472'}]
];
const pg=document.getElementById('petgrid');
if(pg){
  PETS.forEach(function(p){
    const card=document.createElement('div');
    card.className='acard soft col'; card.style.alignItems='center'; card.style.textAlign='center'; card.style.gap='8px';
    const screen=document.createElement('div'); screen.className='petscreen teampet';
    screen.appendChild(makePixelPet(p[5]));
    card.appendChild(screen);
    const meta=document.createElement('div');
    meta.innerHTML='<b>'+p[0]+'</b><div class="mono">'+p[2]+' · ур.'+p[3]+'</div>';
    card.appendChild(meta);
    const track=document.createElement('div'); track.className='track'; track.style.width='100%';
    track.innerHTML='<div class="fill xp" style="width:'+p[4]+'%"></div>'; card.appendChild(track);
    const who=document.createElement('div'); who.className='sm muted'; who.textContent=p[1]; card.appendChild(who);
    pg.appendChild(card);
  });
}

/* members table */
const MEMBERS=[
  ['Анна Петрова','АП','anna@lab.ru','OWNER'],
  ['Михаил Климов','МК','mikhail@lab.ru','ADMIN'],
  ['Ирина Власова','ИВ','irina@lab.ru','PROJECT_LEAD'],
  ['Сергей Дёмин','СД','sergey@lab.ru','EDITOR'],
  ['Лена Зайцева','ЛЗ','lena@lab.ru','MEMBER'],
  ['Олег Рыбин','ОР','oleg@lab.ru','VIEWER']
];
const ROLES=['OWNER','ADMIN','PROJECT_LEAD','EDITOR','MEMBER','VIEWER'];
const mb=document.getElementById('memberBody');
if(mb){
  mb.innerHTML=MEMBERS.map(function(m,idx){
    const opts=ROLES.map(function(r){return '<option'+(r===m[3]?' selected':'')+'>'+r+'</option>';}).join('');
    return '<tr><td><div class="row"><div class="avatar '+(idx%2?'hatch':'')+'" style="width:30px;height:30px;font-size:10px;">'+m[1]+'</div>'+m[0]+'</div></td>'+
      '<td class="mono">'+m[2]+'</td>'+
      '<td><select class="rolepick">'+opts+'</select></td>'+
      '<td><button class="btn sm" title="убрать">×</button></td></tr>';
  }).join('');
  const mc=document.getElementById('memberCount'); if(mc) mc.textContent=MEMBERS.length+' человек';
}

/* ---------------- boot ---------------- */
renderPet();
recount();
try{
  if(localStorage.getItem('petpro_auth')==='1'){
    document.getElementById('auth').classList.remove('on');
    document.getElementById('app').style.display='grid';
  } else { document.getElementById('auth').classList.add('on'); }
  const s=localStorage.getItem('petpro_screen'); if(s) go(s);
}catch(e){ document.getElementById('auth').classList.add('on'); }

/* ---------------- mobile sidebar toggle ---------------- */
(function(){
  const toggle  = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sideOverlay');
  if(!toggle || !sidebar || !overlay) return;

  function openSide(){
    sidebar.classList.add('open');
    overlay.classList.add('on');
    document.body.style.overflow = 'hidden';
  }
  function closeSide(){
    sidebar.classList.remove('open');
    overlay.classList.remove('on');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', () =>
    sidebar.classList.contains('open') ? closeSide() : openSide()
  );
  overlay.addEventListener('click', closeSide);

  /* закрыть при навигации */
  document.querySelectorAll('#nav a').forEach(a =>
    a.addEventListener('click', () => {
      if(window.innerWidth <= 900) closeSide();
    })
  );
})();

})();
