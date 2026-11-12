/* One catalog powers pricing, registration details and administration. */
(()=>{
'use strict';
let groups={tendoo:'Tendoo',devices:'Thiết bị Tendoo',ca:'Chữ ký số Viettel-CA',invoice:'Hóa đơn điện tử',bh:'Kê khai BHXH',contract:'Hợp đồng điện tử vContract'};
const dialog=document.createElement('dialog');dialog.id='catalog-pricing';dialog.style.maxWidth='1100px';dialog.innerHTML='<button type="button" class="close" aria-label="Đóng">×</button><h2></h2><div class="catalog-tools"><input type="search" aria-label="Tìm gói dịch vụ" placeholder="Tìm gói dịch vụ…"><select aria-label="Nhóm dịch vụ"><option value="tendoo">Gói Tendoo</option><option value="devices">Thiết bị Tendoo</option></select></div><p class="catalog-status" role="status"></p><div class="catalog-grid"></div>';
document.body.append(dialog);
let category='tendoo',rows=[],groupRows=null;
const search=dialog.querySelector('input'),select=dialog.querySelector('select'),grid=dialog.querySelector('.catalog-grid'),status=dialog.querySelector('.catalog-status');
dialog.querySelector('.close').onclick=()=>dialog.close();
function render(){grid.replaceChildren();const filtered=rows.filter(p=>p.active&&(!groupRows||groupRows.some(g=>g.id===p.category&&g.active))&&p.category===category&&(p.name+' '+p.details).toLocaleLowerCase('vi').includes(search.value.toLocaleLowerCase('vi').trim()));status.textContent=filtered.length?`${filtered.length} gói dịch vụ`:'Chưa có gói phù hợp.';for(const p of filtered){const card=document.createElement('article');card.className='invoice-price-card';const title=document.createElement('h3');title.textContent=p.name;const duration=document.createElement('p');duration.textContent=p.duration;const price=document.createElement('p');price.className='invoice-price';price.textContent=p.price.toLocaleString('vi-VN')+'đ';const details=document.createElement('p');details.style.whiteSpace='pre-line';details.textContent=p.details;const button=document.createElement('button');button.type='button';button.textContent='Đăng ký ngay';button.onclick=()=>register(p);card.append(title,duration,price,details,button);grid.append(card)}}
const cacheKey='catalog-cache-v1', changeKey='catalog-changed-v1';
let cached=null,inflight=null,generation=0;
function applyGroups(data){if(!Array.isArray(data.groups))return;groupRows=data.groups;groups=Object.fromEntries(groupRows.map(g=>[g.id,g.name]));select.replaceChildren();for(const g of groupRows.filter(g=>g.active)){const o=document.createElement('option');o.value=g.id;o.textContent=g.name;select.append(o)}if(!groupRows.some(g=>g.id===category&&g.active))category=groupRows.find(g=>g.active)?.id||'';select.value=category;select.hidden=false;
const cards=document.getElementById('cards');if(!cards)return;const legacy=['tendoo','ca','contract','invoice','bh'];for(const id of legacy){const card=cards.querySelector(`[data-${id}-pricing]`)?.closest('.card');const group=groupRows.find(g=>g.id===id);if(card){card.hidden=!group?.active;card.style.order=groupRows.findIndex(g=>g.id===id);const title=card.querySelector('h3 a')||card.querySelector('h3');if(group&&title)title.textContent=group.name;if(group?.description){const description=card.querySelector('p');if(description)description.textContent=group.description}}}
for(const card of cards.querySelectorAll('[data-managed-group]'))card.remove();
for(const [index,g] of groupRows.entries()){if(legacy.includes(g.id)||!g.active)continue;const card=document.createElement('article');card.className='card';card.dataset.managedGroup=g.id;card.style.order=index;const title=document.createElement('h3');title.textContent=g.name;const p=document.createElement('p');p.textContent=g.description;const button=document.createElement('button');button.type='button';button.className='product-detail-link';button.textContent='Xem chi tiết';button.onclick=()=>open(g.id);card.append(title,p,button);cards.append(card)}const special=cards.querySelector('.special');if(special)special.style.order=1000;
const choices=document.getElementById('choices');if(choices){const checked=new Set([...choices.querySelectorAll('[data-managed-choice] input:checked')].map(i=>i.value));for(const label of choices.querySelectorAll('[data-managed-choice]'))label.remove();const inputs=[...choices.querySelectorAll('input')];legacy.forEach((id,index)=>{const group=groupRows.find(g=>g.id===id),input=inputs[index];if(!input)return;input.closest('label').hidden=!group?.active;input.disabled=!group?.active;if(!group?.active)input.checked=false;if(group){input.value=group.name;const text=[...input.closest('label').childNodes].find(n=>n.nodeType===Node.TEXT_NODE);if(text)text.textContent=group.name}});for(const g of groupRows.filter(g=>g.active&&!legacy.includes(g.id))){const label=document.createElement('label');label.className='checks';label.dataset.managedChoice=g.id;const input=document.createElement('input');input.type='checkbox';input.name='products';input.value=g.name;input.checked=checked.has(g.name);label.append(input,document.createTextNode(g.name));choices.append(label)}}
}
function valid(data){return data&&Array.isArray(data.plans)&&data.plans.every(p=>p&&typeof p.id==='string'&&typeof p.name==='string'&&typeof p.details==='string'&&typeof p.category==='string'&&typeof p.duration==='string'&&Number.isSafeInteger(p.price)&&typeof p.active==='boolean')}
try{const saved=JSON.parse(localStorage.getItem(cacheKey));if(valid(saved)&&Date.now()-saved.savedAt<86400000)cached=saved}catch{}
function clearCache(){generation++;cached=null;rows=[];try{localStorage.removeItem(cacheKey)}catch{}}
async function refresh(){
 if(inflight)return inflight;
 const epoch=generation;
 inflight=(async()=>{
  const headers=cached?.etag?{'If-None-Match':cached.etag}:{};
  let response=await fetch(new URL('api/plans',location.href),{cache:'no-cache',headers,signal:AbortSignal.timeout(10000)});
  if(response.status===304&&cached)return cached;
  if(response.status===404||(response.ok&&!(response.headers.get('Content-Type')||'').includes('application/json')))response=await fetch('data/plans.json',{cache:'no-cache',signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw Error('catalog');
  const body=await response.json(),data=Array.isArray(body)?{plans:body}:body;
  if(!valid(data))throw Error('catalog');
  if(epoch!==generation)return null;
  cached={plans:data.plans,groups:data.groups,version:data.version,etag:response.headers.get('ETag'),savedAt:Date.now()};
  try{localStorage.setItem(cacheKey,JSON.stringify(cached))}catch{}
  return cached;
 })().finally(()=>{inflight=null});
 return inflight;
}
async function update(){try{const data=await refresh();if(data){rows=data.plans;applyGroups(data);if(dialog.open){dialog.querySelector('h2').textContent='Bảng giá '+(groups[category]||'dịch vụ');render()}}}catch{if(dialog.open)status.textContent=rows.length?'Đang hiển thị dữ liệu đã lưu. Chưa kiểm tra được cập nhật; vui lòng thử lại.':'Không tải được bảng giá. Vui lòng đóng và thử lại.'}}
function open(kind){category=kind;search.value='';select.value=kind;select.hidden=false;dialog.querySelector('h2').textContent='Bảng giá '+groups[kind];rows=cached?.plans||[];if(cached)applyGroups(cached);grid.replaceChildren();if(cached)render();else status.textContent='Đang tải bảng giá…';if(!dialog.open)dialog.showModal();update()}
document.addEventListener('site-content-applied',()=>{if(cached)applyGroups(cached)});
// Warm the catalog before the first click; share one request across dialogs.
update();
window.addEventListener('storage',event=>{if(event.key===changeKey){clearCache();if(dialog.open){grid.replaceChildren();status.textContent='Đang cập nhật bảng giá…'}Promise.resolve(inflight).catch(()=>{}).then(update)}});
window.addEventListener('focus',()=>update());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)update()});
window.addEventListener('site:invalidate',event=>{if(event.detail.resource!=='plans')return;clearCache();if(dialog.open){grid.replaceChildren();status.textContent='Đang cập nhật bảng giá…'}Promise.resolve(inflight).catch(()=>{}).then(update)});
async function register(p){try{const data=await refresh();const current=data?.plans.find(item=>item.id===p.id&&item.active);if(!current||(data.groups&&!data.groups.some(g=>g.id===current.category&&g.active))){rows=data?.plans||[];render();status.textContent='Gói này đã thay đổi hoặc ngừng hiển thị. Vui lòng chọn lại.';return}p=current}catch{status.textContent='Chưa xác nhận được giá mới nhất. Vui lòng thử lại.';return}dialog.close();const $=id=>document.getElementById(id),form=$('td-registration-form'),modal=$('td-registration');modal.dataset.sourceDialog='catalog-pricing';let planInput=form.elements.selectedPlanId;if(!planInput){planInput=document.createElement('input');planInput.type='hidden';planInput.name='selectedPlanId';form.append(planInput)}planInput.value=p.id;$('td-registration-title').textContent='Đăng ký tư vấn '+groups[p.category];form.elements.products.value=groups[p.category];const selected=form.querySelector('[name$="Plan"]');selected.name=({tendoo:'tendooPlan',devices:'tendooPlan',ca:'caPlan',invoice:'invoicePlan',bh:'bhPlan',contract:'contractPlan'})[p.category]||'servicePlan';const price=p.price.toLocaleString('vi-VN')+'đ';selected.value=[p.name,p.duration,price].filter(Boolean).join(' — ');let details=form.elements.selectedPlanDetails;if(!details){details=document.createElement('input');details.type='hidden';details.name='selectedPlanDetails';form.append(details)}details.value=p.details; $('td-reg-package-title').textContent=p.name;$('td-reg-price').textContent=price;$('td-reg-duration-label').textContent='Thời hạn / Bảo hành';$('td-reg-duration').textContent=p.duration||'Theo gói dịch vụ';$('td-reg-vat').textContent='';const text=document.createElement('p');text.style.whiteSpace='pre-line';text.textContent=p.details;$('selected-plan-details').replaceChildren(text);$('td-registration-status').textContent='';modal.showModal()}
search.oninput=render;select.onchange=()=>{category=select.value;dialog.querySelector('h2').textContent='Bảng giá '+groups[category];render()};
// Capture prevents legacy hard-coded pricing handlers from opening a second dialog.
document.addEventListener('click',event=>{for(const kind of ['tendoo','ca','invoice','bh','contract']){if(event.target.closest(`[data-${kind}-pricing]`)){event.preventDefault();event.stopImmediatePropagation();open(kind);return}}},true);
})();
