'use strict';
const groups={tendoo:'Tendoo',devices:'Thiết bị Tendoo',ca:'Chữ ký số',invoice:'Hóa đơn điện tử',bh:'Kê khai BHXH',contract:'Hợp đồng điện tử'};
const $=id=>document.getElementById(id), form=$('edit-form');
let plans=[],version,csrf,editing=null,busy=false;
function option(value,text){const o=document.createElement('option');o.value=value;o.textContent=text;return o}
$('category').append(option('','Tất cả dịch vụ'));for(const [key,name] of Object.entries(groups)){$('category').append(option(key,name));form.elements.category.append(option(key,name))}
class ApiError extends Error {
  constructor(message,status){super(message);this.status=status}
}
function backendError(status){
  if(status===404||status===405)return 'Không tìm thấy API quản trị. Trang này cần chạy bằng server.py; GitHub Pages và máy chủ tĩnh không hỗ trợ đăng nhập hoặc lưu gói.';
  if(status>=500)return 'Máy chủ quản trị đang không khả dụng (HTTP '+status+'). Vui lòng kiểm tra tiến trình server.py và cấu hình chuyển tiếp /api/.';
  return 'API quản trị trả về dữ liệu không hợp lệ (HTTP '+status+'). Vui lòng kiểm tra địa chỉ máy chủ và cấu hình /api/.';
}
async function api(path,data){
  let r;
  try{
    r=await fetch(new URL('/api/'+path,location.origin),{cache:'no-store',...(data?{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||''},body:JSON.stringify(data)}:{})});
  }catch{throw new ApiError('Không kết nối được máy chủ quản trị. Kiểm tra kết nối mạng và máy chủ rồi thử lại.',0)}
  const type=r.headers.get('Content-Type')||'';
  if(!type.toLowerCase().includes('application/json'))throw new ApiError(backendError(r.status),r.status);
  let body;
  try{body=await r.json()}catch{throw new ApiError(backendError(r.status),r.status)}
  if(!body||typeof body!=='object'||Array.isArray(body))throw new ApiError(backendError(r.status),r.status);
  if(!r.ok){
    if(r.status===401&&path!=='login'){csrf=null;document.body.classList.remove('authenticated');$('admin-nav').hidden=true;$('workspace').hidden=true;$('login').hidden=false}
    throw new ApiError(typeof body.error==='string'?body.error:backendError(r.status),r.status);
  }
  if((path==='session'||path==='login')&&typeof body.csrf!=='string')throw new ApiError(backendError(r.status),r.status);
  if(path==='plans'&&!data&&(!Array.isArray(body.plans)||!Number.isInteger(body.version)))throw new ApiError(backendError(r.status),r.status);
  if(data&&['plans','content','consultations'].includes(path))window.notifySiteChange?.(path);
  return body;
}
function status(message,error=false){$('status').textContent=message;$('status').className=error?'error':''}
async function load(){const data=await api('plans');plans=data.plans;version=data.version;render()}
function render(){ $('total').textContent=plans.length;$('active').textContent=plans.filter(p=>p.active).length;$('inactive').textContent=plans.filter(p=>!p.active).length;const query=$('search').value.trim().toLocaleLowerCase('vi');const visible=plans.filter(p=>(!$('category').value||p.category===$('category').value)&&(!$('visibility').value||String(p.active)===$('visibility').value)&&(p.name+' '+p.details).toLocaleLowerCase('vi').includes(query));$('count').textContent=`${visible.length} gói dịch vụ`;$('empty').hidden=visible.length>0;$('rows').replaceChildren();for(const p of visible){const tr=document.createElement('tr');function cell(text){const td=document.createElement('td');td.textContent=text;tr.append(td);return td}const title=cell(p.name);const sub=document.createElement('small');sub.textContent=p.duration;title.append(sub);cell(groups[p.category]);cell(p.price.toLocaleString('vi-VN')+'đ');const badge=document.createElement('span');badge.className='badge'+(p.active?'':' off');badge.textContent=p.active?'Đang hiển thị':'Đang ẩn';cell('').append(badge);const actions=document.createElement('div');actions.className='actions';for(const [label,fn] of [['Sửa',()=>edit(p)],['Xóa',()=>remove(p)],['↑',()=>move(p,-1)],['↓',()=>move(p,1)]]){const b=document.createElement('button');b.type='button';b.className='secondary';b.textContent=label;b.onclick=fn;actions.append(b)}cell('').append(actions);$('rows').append(tr)}}
function edit(p){editing=p?.id||null;form.reset();$('editor-title').textContent=p?'Chỉnh sửa gói':'Thêm gói mới';for(const key of ['name','category','duration','price','details'])form.elements[key].value=p?.[key]??(key==='price'?0:key==='category'?'tendoo':'');form.elements.active.checked=p?.active??true;$('edit-error').textContent='';$('editor').showModal()}
async function persist(next){if(busy)throw Error('Đang lưu, vui lòng đợi.');busy=true;try{const result=await api('plans',{plans:next,version});version=result.version;plans=next;render();status('Đã lưu. Bảng giá trên website đã được cập nhật.')}finally{busy=false}}
async function remove(p){if(!confirm(`Xóa gói “${p.name}”? Thao tác này sẽ cập nhật website.`))return;try{await persist(plans.filter(row=>row.id!==p.id))}catch(e){status(e.message,true)}}
form.onsubmit=async e=>{e.preventDefault();const price=Number(form.elements.price.value);if(!Number.isSafeInteger(price)||price<0)return;const p={id:editing||crypto.randomUUID(),category:form.elements.category.value,name:form.elements.name.value.trim(),duration:form.elements.duration.value.trim(),price,details:form.elements.details.value.trim(),active:form.elements.active.checked};if(!p.name){$('edit-error').textContent='Vui lòng nhập tên gói.';return}$('save').disabled=true;try{await persist(editing?plans.map(row=>row.id===editing?p:row):[...plans,p]);$('editor').close()}catch(e){$('edit-error').textContent=e.message}finally{$('save').disabled=false}};
$('login-form').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{const result=await api('login',{username:$('username').value.trim(),password:$('password').value});csrf=result.csrf;$('password').value='';await enterAdmin();status('')}catch(e){status(e.message,true)}finally{button.disabled=false}};
$('logout').onclick=async()=>{try{await api('logout',{});csrf=null;plans=[];document.body.classList.remove('authenticated');$('admin-nav').hidden=true;$('editor').close();$('workspace').hidden=true;$('login').hidden=false;status('Đã đăng xuất.')}catch(e){status(e.message,true)}};
$('add').onclick=()=>edit(null);$('close').onclick=$('cancel').onclick=()=>$('editor').close();for(const id of ['search','category','visibility'])$(id).addEventListener('input',render);
(async()=>{try{csrf=(await api('session')).csrf;await enterAdmin()}catch(e){if(e.status!==401)status(e.message,true)}})();

async function move(p,direction){const index=plans.indexOf(p),next=index+direction;if(next<0||next>=plans.length)return;const ordered=[...plans];[ordered[index],ordered[next]]=[ordered[next],ordered[index]];try{await persist(ordered)}catch(e){status(e.message,true)}}

async function enterAdmin(){document.body.classList.add('authenticated');$('login').hidden=true;$('admin-nav').hidden=false;if(['/admin','/admin/','/admin.html'].includes(location.pathname)){location.replace('/admin/plans');return}window.dispatchEvent(new Event('admin:ready'));if(location.pathname==='/admin/plans'){await load();$('workspace').hidden=false}}
