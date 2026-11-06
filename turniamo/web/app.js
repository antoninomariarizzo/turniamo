'use strict';
const $ = s => document.querySelector(s);
const icons = {
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6m10-6v6M3 11h18M7 15h2m3 0h2m3 0h1M7 18h2"/>',
  doctors:'<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3M8 13v5a3 3 0 0 0 6 0v-4m3 1v3"/><circle cx="17" cy="20" r="2"/>',
  gear:'<path d="m9 3 .7-1h4.6l.7 1 .4 2 1.8 1 1.9-.7 1.5 2.6-1.4 1.6v2l1.4 1.6-1.5 2.6-1.9-.7-1.8 1-.4 2-.7 1H9l-.7-1-.4-2-1.8-1-1.9.7-1.5-2.6L4.1 12v-2L2.7 8.4l1.5-2.6 1.9.7 1.8-1z"/><circle cx="11.3" cy="10.5" r="3"/>',
  export:'<path d="M12 15V2m-4 4 4-4 4 4M7 9H4v12h16V9h-3"/>',
  left:'<path d="m14 6-6 6 6 6"/>', right:'<path d="m10 6 6 6-6 6"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
  check:'<path d="m5 12 4 4L19 6"/>', more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
};
function el(tag, cls, text) { const n=document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n; }
function icon(name) { const n=document.createElementNS('http://www.w3.org/2000/svg','svg'); n.setAttribute('viewBox','0 0 24 24'); n.setAttribute('aria-hidden','true'); n.innerHTML=icons[name]; return n; }
let bridge, state, tab='schedule', menuToken=0, toastTimer;
const t = key => state.text[key] || key;
function rpc(command, args={}) { return new Promise((resolve,reject)=>bridge.request(command,JSON.stringify(args), raw=>{
  const response=JSON.parse(raw); if(response.ok)resolve(response.result); else {notify(response.error); reject(new Error(response.error));}
})); }
function run(command,args) { return rpc(command,args).catch(()=>{}); }
function notify(text) { const n=$('#toast'); n.textContent=text; n.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>n.hidden=true,6500); }
function closeMenu() { $('#popover').hidden=true; $('#popover').onkeydown=null; menuToken++; }
function showMenu(anchor) {
  const p=$('#popover'); p.hidden=false; const rect=anchor.getBoundingClientRect();
  p.style.left=Math.min(Math.max(8,rect.left),window.innerWidth-p.offsetWidth-8)+'px';
  p.style.top=Math.min(rect.bottom+5,Math.max(8,window.innerHeight-p.offsetHeight-8))+'px';
}
function addMenuAction(text,callback) { const b=el('button','menu-action',text); b.onclick=()=>{closeMenu();callback();}; $('#popover').append(b); return b; }
function render() {
  document.documentElement.lang=state.language;
  $('#tabs').replaceChildren();
  for(const name of ['schedule','summary','monthly','festivities']) {
    const b=el('button',name===tab?'selected':'');if(name==='schedule')b.append(icon('calendar'));else b.textContent=t(name);b.title=t(name);b.setAttribute('aria-label',t(name));b.dataset.tab=name;
    b.onclick=async()=>{closeMenu();if(['monthly','festivities'].includes(name)){try{await rpc('report_reset');}catch(_){return;}}tab=name;render();}; $('#tabs').append(b);
  }
  $('#weeks').replaceChildren(...state.weeks.map(w=>{const o=el('option','',w.label);o.value=w.start;return o;}));
  $('#weeks').value=state.start;
  $('#doctors').title=t('doctors');$('#doctors').setAttribute('aria-label',t('doctors'));$('#doctors').classList.toggle('selected',tab==='doctors');
  for(const [id,key] of [['previous','previous_week'],['next','next_week'],['export','export'],['settings','settings']]) {
    $('#'+id).title=t(key); $('#'+id).setAttribute('aria-label',t(key));
  }
  const reportTab=['monthly','festivities'].includes(tab);
  $('.week-controls').hidden=reportTab;
  $('#main').replaceChildren();
  if(tab==='schedule')renderSchedule(); else if(tab==='doctors')renderDoctors(); else if(tab==='summary')renderSummary(); else renderPeriodReport();
}
function renderSchedule() {
  const table=el('table','schedule'); table.setAttribute('aria-label',t('schedule'));
  const head=el('thead'), hr=el('tr'); hr.append(el('th','',''));
  for(const col of state.columns) {
    const h=el('th',['night_off','absence','holiday','recovery'].includes(col.key)?'narrow':'');
    const lines=t(col.key).split('\n');h.append(document.createTextNode(lines[0]));
    if(lines[1])h.append(el('span','',lines[1])); hr.append(h);
  }
  head.append(hr);table.append(head);const body=el('tbody');
  for(const day of state.days) {
    const row=el('tr',day.weekday>=5?'weekend':'');row.append(el('th','',day.label));
    for(const col of state.columns) {
      const td=el('td'), cell=el('div','cell');
      const activities=col.key==='ward'?['ward']:col.activities;
      for(const activity of activities) {
        const slot=el('div','slot');slot.tabIndex=0;slot.setAttribute('role','button');
        slot.dataset.day=day.date;slot.dataset.activity=activity;
        slot.setAttribute('aria-label',`${day.label} · ${t(col.key)} ${state.sublabels[activity]||''}`);
        if(state.sublabels[activity])slot.append(el('span','slot-label',state.sublabels[activity]));
        const disabled=activity==='on_call_am'&&day.weekday!==5;
        if(disabled){slot.setAttribute('aria-disabled','true');slot.tabIndex=-1;}
        const entries=state.assignments.filter(a=>a.day===day.date&&(a.activity===activity||(activity==='ward'&&a.activity==='ward_help')));
        const collator=new Intl.Collator(state.language,{sensitivity:'base',numeric:true});
        const doctorName=id=>state.doctors.find(d=>d.id===id)?.name.normalize('NFKC')||'';
        entries.sort((a,b)=>collator.compare(doctorName(a.doctor_id),doctorName(b.doctor_id))||a.doctor_id.localeCompare(b.doctor_id));
        for(const a of entries) {
          const d=state.doctors.find(d=>d.id===a.doctor_id); if(!d)continue;
          const warning=state.issues.find(i=>i.day===a.day&&i.doctor_id===d.id&&(!i.activity||i.activity===a.activity));
          const chip=el('div','assignment'+(a.paid?' paid':'')+(warning?' warning':''));
          const name=el('span','name',d.name+(a.paid?' *':''));chip.append(name);
          let title=d.name+' · '+Math.floor(Math.abs(a.minutes)/60)+'h'+String(Math.abs(a.minutes)%60).padStart(2,'0')+'m';
          if(warning)title+=' · '+t(warning.key);
          if(!d.active)title+=' · '+t('former_doctor');
          chip.title=title;
          if(a.activity==='ward_help')chip.append(el('span','associated',t('ward_assistant')));
          if(a.associate_role)chip.append(el('span','associated',t(a.associate_role)+': '+a.associate_name));
          const details=el('button','more');details.append(icon('more'));details.title=t('assignment_note');
          details.setAttribute('aria-label',t('assignment_note')+' '+d.name);
          details.onclick=e=>{e.stopPropagation();closeMenu();assignmentDialog(a,d);};chip.append(details);slot.append(chip);
        }
        if(!entries.length&&!disabled)slot.append(el('span','slot-empty','+'));
        slot.onclick=()=>{if(!disabled)doctorMenu(slot,day.date,activity);};
        slot.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();if(!disabled)doctorMenu(slot,day.date,activity);}};
        cell.append(slot);
      }
      td.append(cell);row.append(td);
    }
    body.append(row);
  }
  table.append(body);$('#main').append(table);
  if(!window.turniamoPrintState)requestAnimationFrame(fitSchedule);
}
function fitSchedule() {
  if(window.turniamoPrintState)return;
  const table=$('.schedule');if(!table)return;
  const cells=[...table.querySelectorAll('.cell')];cells.forEach(c=>{c.style.height='auto';});
  const baseline=Math.max(88,($('#main').clientHeight-table.tHead.offsetHeight-1)/7);
  const sizes=[...table.tBodies[0].rows].map(row=>Math.ceil(Math.max(baseline,...[...row.querySelectorAll('.cell')].map(c=>c.getBoundingClientRect().height))));
  [...table.tBodies[0].rows].forEach((row,i)=>row.querySelectorAll('.cell').forEach(c=>c.style.height=sizes[i]+'px'));
}
async function doctorMenu(anchor,day,activity) {
  closeMenu();const token=menuToken;
  const choices=await rpc('choices',{day,activity}).catch(()=>null);if(!choices||token!==menuToken)return;
  const pop=$('#popover');pop.replaceChildren();
  const selected=new Set(choices.filter(d=>d.selected).map(d=>d.id));
  let saving=false;
  const search=el('input','search');search.type='search';search.placeholder=t('search_doctor');search.setAttribute('aria-label',t('search_doctor'));pop.append(search);
  const list=el('div','choices');pop.append(list);
  const populate=()=>{
    list.replaceChildren();
    for(const d of choices.filter(d=>d.name.toLocaleLowerCase().includes(search.value.toLocaleLowerCase()))) {
      const b=el('button','choice'+(d.warning?' warning':''));b.dataset.doctor=d.id;b.setAttribute('aria-pressed',String(selected.has(d.id)));b.disabled=d.disabled||saving;b.title=d.reason;
      const mark=el('span','checkmark');if(selected.has(d.id))mark.append(icon('check'));b.append(mark,el('span','',d.name));
      b.onclick=()=>{
        if(selected.has(d.id))selected.delete(d.id);else selected.add(d.id);
        b.setAttribute('aria-pressed',String(selected.has(d.id)));mark.replaceChildren();if(selected.has(d.id))mark.append(icon('check'));
      };list.append(b);
    }
    if(!list.children.length)list.append(el('div','empty',t('no_results')));
  };
  search.oninput=populate;
  search.onkeydown=e=>{if(e.key==='ArrowDown'){e.preventDefault();list.querySelector('button:not(:disabled)')?.focus();}};
  const footer=el('div','selection-actions'),cancel=el('button','selection-cancel'),confirm=el('button','selection-confirm');
  cancel.append(icon('close'),document.createTextNode(t('cancel')));cancel.title=t('cancel')+' (Esc)';
  confirm.append(icon('check'),document.createTextNode(t('confirm')));confirm.title=t('confirm')+' (↵)';
  cancel.onclick=()=>{closeMenu();anchor.focus();};
  const save=async()=>{
    if(saving)return;saving=true;confirm.disabled=true;cancel.disabled=true;search.disabled=true;populate();
    try{await rpc('set_slot_doctors',{day,activity,doctors:[...selected]});if(token===menuToken)closeMenu();}
    catch(_){saving=false;confirm.disabled=false;cancel.disabled=false;search.disabled=false;populate();search.focus();}
  };
  confirm.onclick=save;footer.append(cancel,confirm);pop.append(footer);
  pop.onkeydown=e=>{
    if(e.key==='Enter'&&!e.isComposing){e.preventDefault();e.stopPropagation();save();}
    else if(e.key==='Escape'){e.preventDefault();e.stopPropagation();if(!saving){closeMenu();anchor.focus();}}
  };
  populate();showMenu(anchor);search.focus();
}
function renderDoctors() {
  const page=el('div','doctors-page'),form=el('form','add-form'),input=el('input');
  input.type='text';input.placeholder=t('name');input.setAttribute('aria-label',t('name'));input.maxLength=80;input.required=true;
  const add=el('button','primary',t('add_doctor'));add.type='submit';form.append(input,add);
  form.onsubmit=async e=>{e.preventDefault();add.disabled=true;await run('save_doctor',{name:input.value});add.disabled=false;};page.append(form);
  for(const d of state.doctors) {
    const row=el('div','doctor-row');row.dataset.doctor=d.id;
    const name=el('button','doctor-name',d.name);name.title=t('edit');
    name.onclick=()=>{
      const edit=el('input');edit.type='text';edit.value=d.name;edit.maxLength=80;edit.setAttribute('aria-label',t('name'));
      name.replaceWith(edit);edit.focus();edit.select();let done=false;
      const save=()=>{if(done)return;done=true;if(edit.value.trim()===d.name){edit.replaceWith(name);return;}
        rpc('save_doctor',{id:d.id,name:edit.value}).catch(()=>{done=false;edit.focus();});};
      edit.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();save();}if(e.key==='Escape'){done=true;edit.replaceWith(name);}};
      edit.onblur=save;
    };
    row.append(name);
    if(!d.active){const former=el('span','former');former.title=t('former_doctor');row.append(former);}
    const trash=el('button','icon-button trash');trash.append(icon('trash'));trash.title=t('delete_doctor');trash.setAttribute('aria-label',t('delete_doctor')+' '+d.name);
    trash.onclick=()=>confirmDialog(t('delete_doctor'),
      state.language==='it'?`Rimuovere ${d.name} da questa settimana e dalle successive, inclusi i suoi incarichi? Le settimane precedenti restano conservate.`:
        `Remove ${d.name} from this week and later weeks, including their assignments? Earlier weeks will be preserved.`,
      ()=>run('remove_doctor',{id:d.id}));row.append(trash);page.append(row);
  }
  $('#main').append(page);
}
function renderSummary() {
  const table=el('table','summary'),head=el('thead'),hr=el('tr');hr.append(el('th','',''));
  for(const key of ['ordinary','paid_hours','status']){const th=el('th','',t(key));if(key==='ordinary')th.title=t('ordinary_tooltip');hr.append(th);}head.append(hr);table.append(head);
  const body=el('tbody');
  for(const d of state.doctors) {
    const values=state.totals[d.id],r=el('tr');r.append(el('th','',d.name));
    for(const category of ['ordinary','paid']) {
      const td=el('td'),amount=el('span','amount',values[category]);
      const info=el('button','info-button');info.append(icon('info'));info.title=t('calculation');info.setAttribute('aria-label',t('calculation')+' · '+d.name+' · '+t(category));
      info.dataset.doctor=d.id;info.dataset.category=category;info.onclick=()=>calculationDialog(d,category);td.append(amount,info);r.append(td);
    }
    const status=el('td');status.append(el('span',values.status==='above'?'status above':'neutral-status',t(values.status)));r.append(status);body.append(r);
  }table.append(body);$('#main').append(table);
}
function renderPeriodReport(kind=tab) {
  const report=state.reports, monthly=kind==='monthly', page=el('section','period-report');
  const controls=el('div','period-controls'),label=el('label','',t(monthly?'month':'year')),input=el('input');
  input.type=monthly?'month':'number';input.value=monthly?report.month:report.year;
  input.min=monthly?'1900-01':'1900';input.max=monthly?'9999-12':'9999';input.setAttribute('aria-label',label.textContent);
  input.onchange=()=>{if(!input.value||!input.checkValidity())return;const [year,month]=monthly?input.value.split('-'):[input.value,report.month.split('-')[1]];run('report_period',{year:Number(year),month:Number(month)});};
  label.append(input);controls.append(el('h2','',t(kind)),label);page.append(controls,el('p','report-note',t(monthly?'monthly_note':'festive_note')));
  const columns=monthly?report.columns:['festive','special','paid_clinic','paid_nights'],rows=monthly?report.monthly:report.festivities;
  const table=el('table','summary report-table'),head=el('thead'),hr=el('tr');hr.append(el('th','',t('report_person')));
  for(const key of columns){const th=el('th','',t(key));if(!monthly)th.append(reportInfo(t(key),key,()=>holidayDialog(key)));hr.append(th);}head.append(hr);table.append(head);
  const body=el('tbody');for(const row of rows){const tr=el('tr');tr.dataset.doctor=row.id;tr.append(el('th','',row.name));for(const key of columns){const td=el('td');td.append(el('span','amount',row.counts[key]));if(!monthly)td.append(reportInfo(row.name+' · '+t(key),key,()=>holidayDialog(key,row)));tr.append(td);}body.append(tr);}table.append(body);page.append(table);$('#main').append(page);
}
function reportInfo(label,key,callback) {
  const button=el('button','info-button');button.append(icon('info'));button.title=label;
  button.setAttribute('aria-label',t('calculation')+' · '+label);button.dataset.category=key;button.onclick=callback;return button;
}
function holidayDialog(key,row=null) {
  const d=dialogBase((row?row.name+' · ':'')+t(key)+' · '+state.reports.year);d.classList.add('calculation-dialog');
  const paid=key.startsWith('paid_');const entries=row?row.details[key]:(state.reports.holiday_catalog[key]||[]);if(paid)d.append(el('p','report-note',t(key+'_note')));
  const table=el('table','breakdown'),head=el('thead'),header=el('tr');
  for(const label of [t('date'),...(!paid?[t('festive')]:[]),...(row?[t('activity')]:[])])header.append(el('th','',label));head.append(header);table.append(head);
  const body=el('tbody');for(const entry of entries){const tr=el('tr');const [year,month,day]=entry.date.split('-');tr.append(el('td','',day+'/'+month+'/'+year));if(!paid)tr.append(el('td','',t(entry.holiday)));if(row)tr.append(el('td','',entry.assignments.map(a=>t(a.activity)+(a.paid?' · '+t('paid'):'')).join('; ')));body.append(tr);}table.append(body);if(row||!paid)d.append(table);
  if(row){if(!entries.length)d.append(el('p','',t('no_attendance')));const total=el('div','breakdown-total');total.append(el('span','',t('total')),el('strong','',row.counts[key]));d.append(total);if(!paid)d.append(el('p','report-note',t('attendance_note')));}
  const footer=el('div','actions'),close=el('button','primary',t('close'));close.onclick=()=>d.close();footer.append(close);d.append(footer);d.showModal();
}
function formatMinutes(value){return (value<0?'−':'')+Math.floor(Math.abs(value)/60)+'h'+String(Math.abs(value)%60).padStart(2,'0')+'m';}
function calculationDialog(doctor,category) {
  const d=dialogBase(doctor.name+' · '+t('calculation'));d.classList.add('calculation-dialog');
  const entries=state.assignments.filter(a=>a.doctor_id===doctor.id&&a.paid===(category==='paid'));
  entries.sort((a,b)=>a.day.localeCompare(b.day)||state.columns.findIndex(c=>c.activities.includes(a.activity))-state.columns.findIndex(c=>c.activities.includes(b.activity)));
  const table=el('table','breakdown');const head=el('thead'),hr=el('tr');
  for(const key of ['day','activity','counted_hours'])hr.append(el('th','',t(key)));head.append(hr);table.append(head);
  const body=el('tbody');
  for(const a of entries){const row=el('tr');row.append(el('td','',state.days.find(d=>d.date===a.day)?.label||a.day),el('td','',t(a.activity).replace('\n',' ')),el('td','',formatMinutes(a.minutes)));body.append(row);}
  table.append(body);d.append(table);
  if(!entries.length)d.append(el('p','',t('no_counted_duties')));
  const total=el('div','breakdown-total');total.append(el('span','',t('total')),el('strong','',formatMinutes(entries.reduce((sum,a)=>sum+a.minutes,0))));d.append(total);
  const footer=el('div','actions'),close=el('button','primary',t('close'));close.onclick=()=>d.close();footer.append(close);d.append(footer);d.showModal();
}
// Populate dialogs while hidden, then enter the modal top layer once complete.
function dialogBase(title) {closeMenu();const d=$('#dialog');if(d.open)d.close();d.className='';d.replaceChildren(el('h2','',title));return d;}
function actions(dialog,onSave,saveText=t('save')) {
  const footer=el('div','actions'),cancel=el('button','quiet-button',t('cancel')),save=el('button','primary',saveText);
  cancel.onclick=()=>dialog.close();save.onclick=onSave;footer.append(cancel,save);dialog.append(footer);return save;
}
function confirmDialog(title,message,callback) {const d=dialogBase(title);d.append(el('p','',message));actions(d,()=>{d.close();callback();},t('remove'));d.showModal();}
function assignmentDialog(a,doctor) {
  const d=dialogBase(doctor.name+' · '+t('assignment_note'));
  if(a.source_id){d.append(el('p','',t('error_derived')));const close=el('button','primary',t('close'));close.onclick=()=>d.close();d.append(close);d.showModal();return;}
  const paidRow=el('div','switch-row');paidRow.append(el('span','',t('paid')));
  const paid=el('button','switch');paid.setAttribute('role','switch');paid.setAttribute('aria-label',t('paid'));paid.setAttribute('aria-checked',String(a.paid));
  paid.disabled=['absence','holiday','recovery','multidisciplinary','on_call_night'].includes(a.activity);
  paid.onclick=()=>paid.setAttribute('aria-checked',String(paid.getAttribute('aria-checked')!=='true'));paidRow.append(paid);d.append(paidRow);
  const role=el('select');role.id='associate-role';for(const key of ['', 'training','reference']){const o=el('option','',t(key||'none'));o.value=key;role.append(o);}role.value=a.associate_role;
  const roleLabel=el('label','',t('associate'));roleLabel.htmlFor=role.id;d.append(roleLabel,role);
  const name=el('input');name.type='text';name.id='associate-name';name.value=a.associate_name;name.maxLength=80;name.disabled=!role.value;
  const nameLabel=el('label','',t('associate_name'));nameLabel.htmlFor=name.id;d.append(nameLabel,name);role.onchange=()=>{name.disabled=!role.value;if(role.value)name.focus();};
  actions(d,async()=>{try{await rpc('update_assignment',{id:a.id,paid:paid.getAttribute('aria-checked')==='true',role:role.value,name:role.value?name.value:''});d.close();}catch(_){}});
  d.showModal();
}
function settingsMenu(anchor) {
  closeMenu();$('#popover').replaceChildren(el('div','menu-heading',t('language')));
  for(const [code,name] of [['it','Italiano'],['en','English']]) {const b=addMenuAction(name,()=>run('language',{language:code}));if(state.language===code)b.append(icon('check'));}
  $('#popover').append(el('div','divider'));
  addMenuAction(t('export_database'),()=>run('export_database'));
  addMenuAction(t('import_database'),()=>run('import_database'));showMenu(anchor);
}
function exportMenu(anchor) {closeMenu();$('#popover').replaceChildren();addMenuAction(t('export_excel'),()=>run('export',{kind:'xlsx'}));addMenuAction(t('export_pdf'),()=>run('export',{kind:'pdf'}));showMenu(anchor);}
function offsetWeek(delta) {const d=new Date(state.start+'T12:00:00');d.setDate(d.getDate()+delta);run('week',{date:[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')});}
$('#doctors').append(icon('doctors'));$('#doctors').onclick=()=>{tab='doctors';closeMenu();render();};
$('#previous').append(icon('left'));$('#next').append(icon('right'));$('#export').append(icon('export'));$('#settings').append(icon('gear'));
$('#previous').onclick=()=>offsetWeek(-7);$('#next').onclick=()=>offsetWeek(7);
$('#weeks').onchange=e=>{closeMenu();run('week',{date:e.target.value});};
$('#settings').onclick=e=>settingsMenu(e.currentTarget);$('#export').onclick=e=>exportMenu(e.currentTarget);
document.addEventListener('pointerdown',e=>{if(!$('#popover').hidden&&!$('#popover').contains(e.target)&&!e.target.closest('.slot,.tools'))closeMenu();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMenu();});
window.addEventListener('resize',()=>{closeMenu();requestAnimationFrame(fitSchedule);});
new ResizeObserver(()=>requestAnimationFrame(fitSchedule)).observe($('#main'));
if(window.turniamoPrintState) {
  state=window.turniamoPrintState;
  document.documentElement.lang=state.language;
  document.body.classList.add('print-document');
  const main=$('#main');main.replaceChildren();
  for(const [name,draw] of [['schedule',renderSchedule],['summary',renderSummary],['monthly',()=>renderPeriodReport('monthly')],['festivities',()=>renderPeriodReport('festivities')]]) {
    draw();const table=main.lastElementChild,section=el('section','print-section '+name+'-section');
    section.append(el('h2','print-heading',t(name)+': '+(name==='monthly'?state.reports.month:name==='festivities'?state.reports.year:state.weekLabel)),table);main.append(section);
  }
  // Hidden export pages do not receive animation frames. Font readiness is
  // sufficient; printToPdf performs the final layout at the target page size.
  document.fonts.ready.then(()=>window.turniamoPrintReady=true);
} else new QWebChannel(qt.webChannelTransport,channel=>{
  bridge=channel.objects.turniamo;
  bridge.exportFinished.connect(raw=>{const result=JSON.parse(raw);if(result.message)notify(result.message);});
  bridge.updated.connect(raw=>{state=JSON.parse(raw);render();});
  rpc('state').then(s=>{state=s;render();window.turniamoReady=true;});
});
