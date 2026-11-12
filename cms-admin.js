(()=>{'use strict';
const area=document.createElement('section');area.id='content-admin';area.hidden=true;document.querySelector('main').append(area);
const nav=document.createElement('nav');nav.className='actions';for(const [title,fn] of [['Gói dịch vụ',()=>{area.hidden=true;document.getElementById('workspace').hidden=false}],['Nội dung website',()=>showContent()],['Yêu cầu tư vấn',()=>showInbox()],['Đăng xuất',()=>document.getElementById('logout').click()]]){const b=document.createElement('button');b.textContent=title;b.onclick=()=>Promise.resolve(fn()).catch(e=>status(e.message,true));nav.append(b)}
document.getElementById('workspace').prepend(nav);const nav2=nav.cloneNode(true);[...nav2.children].forEach((b,i)=>b.onclick=()=>nav.children[i].click());area.append(nav2);const body=document.createElement('div');area.append(body);
function label(title,value,type='text'){const l=document.createElement('label');l.textContent=title;const input=document.createElement(type==='textarea'?'textarea':'input');if(type!=='textarea')input.type=type;input.value=value??'';l.append(input);return [l,input]}
function button(title,fn){const b=document.createElement('button');b.type='button';b.textContent=title;b.onclick=()=>Promise.resolve(fn()).catch(e=>status(e.message,true));return b}
function activate(){area.hidden=false;document.getElementById('workspace').hidden=true;body.replaceChildren()}
async function showContent(){const result=await api('content');activate();const data=result.content;
 const [hl,hotline]=label('Hotline',data.hotline);body.append(hl);
 const [fl,footer]=label('Footer',data.footer||'','textarea');body.append(fl);
 const select=document.createElement('select');data.sections.forEach((s,i)=>select.append(option(i,s.title)));body.append(select);const list=document.createElement('div');body.append(list);
 function render(){list.replaceChildren();const section=data.sections[Number(select.value)];const [sl,title]=label('Tên mục quản trị',section.title);title.oninput=()=>section.title=title.value;list.append(sl);
 for(const field of [...section.fields].sort((a,b)=>a.order-b.order)){const box=document.createElement('fieldset');const [tl,text]=label(field.tag==='IMG'?'Ảnh':'Nội dung',field.text,'textarea');text.oninput=()=>{field.text=text.value;if(field.tag==='IMG'){delete field.mobile;delete field.desktop;preview.src=field.text}};box.append(tl);let preview;
 if(field.tag==='SUMMARY'){const [l,answer]=label('Câu trả lời',field.answer||'','textarea');answer.oninput=()=>field.answer=answer.value;box.append(l)}
 if(field.href!==null){const [l,input]=label('Liên kết',field.href);input.oninput=()=>field.href=input.value;box.append(l)}
 const [al,active]=label('Hiển thị',null,'checkbox');active.checked=field.active;active.onchange=()=>field.active=active.checked;box.append(al);
 const [ol,order]=label('Thứ tự trong cùng nhóm',field.order,'number');order.oninput=()=>field.order=Number(order.value);box.append(ol);
 if(field.tag==='IMG'){preview=document.createElement('img');preview.src=field.desktop||field.text;preview.alt=field.alt||'Ảnh banner';preview.style.cssText='display:block;max-width:100%;max-height:220px;object-fit:contain;margin:12px 0';box.append(preview);const upload=document.createElement('input');upload.type='file';upload.accept='image/png,image/jpeg,image/webp';upload.onchange=async()=>{try{const file=upload.files[0];if(!file)return;if(file.size>2100000)throw Error('Ảnh tối đa 2 MB.');upload.disabled=true;const image=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(file)});const urls=await api('upload',{image});const latest=await api('content');
if(latest.version!==result.version)throw Error('Ảnh đã tải lên Blob nhưng nội dung đã được sửa ở phiên khác. Tải lại trang quản trị trước khi áp dụng ảnh.');
const target=latest.content.sections.find(s=>s.id===section.id)?.fields.find(f=>f.id===field.id);
Object.assign(field,urls);text.value=field.text=urls.desktop;preview.src=urls.desktop;
if(!target){status('Ảnh đã tải lên. Đây là mục mới: bấm Lưu nội dung để thêm mục và áp dụng ảnh.');return}
Object.assign(target,{mobile:urls.mobile,desktop:urls.desktop,text:urls.desktop});
await api('content',{content:latest.content,version:latest.version});
result.version=latest.version+1;
try{localStorage.setItem('website-content-changed',crypto.randomUUID())}catch{}
status('Đã lưu và áp dụng ảnh banner. Trang khách sẽ tự cập nhật.')}catch(e){status(e.message,true)}finally{upload.disabled=false}};box.append(upload)}
 box.append(button('Nhân bản',()=>{section.fields.push({...field,templateId:field.templateId??field.id,id:Math.max(-1,...section.fields.map(f=>f.id))+1,order:field.order+1});render()}),button('Ẩn',()=>{field.active=false;render()}));list.append(box)}
 }
 select.onchange=render;render();body.append(button('Lưu nội dung',async()=>{data.hotline=hotline.value;data.footer=footer.value;await api('content',{content:data,version:result.version});status('Đã lưu nội dung. Tải lại trang khách để đối chiếu.');await showContent()}));
}
async function showInbox(){const result=await api('consultations');activate();const title=document.createElement('h2');title.textContent='Yêu cầu tư vấn';body.append(title);for(const row of result.requests){const box=document.createElement('article');const text=document.createElement('p');text.style.whiteSpace='pre-wrap';text.textContent=[row.id,new Date(row.created*1000).toLocaleString('vi'),row.data.name,row.data.email,row.data.phone,row.data.planId||row.data.products?.join(', '),'Email: '+row.emailStatus,row.emailId].filter(Boolean).join('\n');const select=document.createElement('select');for(const value of ['Mới','Đang xử lý','Hoàn tất','Hủy'])select.append(option(value,value));select.value=row.status;box.append(text,select,button('Cập nhật trạng thái',async()=>{await api('consultations',{id:row.id,status:select.value});status('Đã cập nhật trạng thái.')}));body.append(box)}}
// Hide private panels immediately when the session view returns to login.
new MutationObserver(()=>{if(!document.getElementById('login').hidden){area.hidden=true;body.replaceChildren()}}).observe(document.getElementById('login'),{attributes:true,attributeFilter:['hidden']});
})();
