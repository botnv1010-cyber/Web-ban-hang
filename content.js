/* Stable DOM bindings preserve the approved storefront layout. */
(()=>{'use strict';
const sections=[...document.querySelectorAll('header, main > :not(dialog), footer')];
const bindings=sections.map(section=>[...section.querySelectorAll('h1,h2,h3,p,a,summary,details > div,img,button,li,span,iframe')].filter(el=>el.id!=='poster-count'&&!el.closest('form,dialog')&&(['IMG','IFRAME','A'].includes(el.tagName)||!el.children.length)));
let version=0;
async function load(){try{const response=await fetch('api/content',{cache:'no-store'});if(!response.ok)return;const result=await response.json();if(result.version===version)return;version=result.version;
 for(const section of result.content.sections){const index=Number(section.id.replace('section-',''));const nodes=bindings[index];if(!nodes)continue;
 for(const field of section.fields){let node=nodes[field.id];if(!node){const template=nodes[field.templateId]||nodes.find(n=>n.tagName===field.tag);if(!template)continue;if(template.closest('.poster-slide')&&field.tag==='IMG'){const slide=template.closest('.poster-slide').cloneNode(true);template.closest('.poster-slide').parentNode.append(slide);node=slide.querySelector('img')}else if(field.tag==='SUMMARY'){const item=template.parentNode.cloneNode(true);template.parentNode.parentNode.append(item);node=item.querySelector('summary')}else{node=template.cloneNode(true);template.parentNode.append(node)}nodes[field.id]=node}
 node.hidden=!field.active;
 if(field.tag==='SUMMARY'){node.parentNode.hidden=!field.active;const answer=node.parentNode.querySelector('textarea');if(answer){answer.value=field.answer||'';answer.readOnly=true}}
 if(node.classList.contains('poster-slide')||field.tag==='IMG'&&node.closest('.poster-slide')){const slide=node.closest('.poster-slide');slide.dataset.disabled=String(!field.active);if(field.tag==='IMG')slide.dataset.cmsOrder=field.order;}
 if(field.tag==='IMG'){node.src=field.desktop||field.text;node.alt=field.alt||'';if(field.mobile) {node.srcset=field.mobile+' 768w, '+(field.desktop||field.text)+' 1920w';node.sizes='(max-width: 768px) 100vw, 100vw'}}else if(field.tag==='IFRAME'){if(node.getAttribute('src')!==field.text)node.src=field.text}else if(!field.preserveChildren)node.textContent=field.text;
 if(field.href!==null&&field.href!==undefined&&node.tagName==='A')node.setAttribute('href',field.href);
 node.dataset.cmsOrder=field.order;
 }
 // Reorder only siblings, preserving structural wrappers and CSS classes.
 const parents=new Set(nodes.map(n=>n.parentNode));for(const parent of parents){const children=[...parent.children].filter(n=>n.dataset.cmsOrder!==undefined);const sorted=[...children].sort((a,b)=>Number(a.dataset.cmsOrder)-Number(b.dataset.cmsOrder));const slots=children.map(n=>{const marker=document.createComment('cms');n.replaceWith(marker);return marker});slots.forEach((slot,i)=>slot.replaceWith(sorted[i]))}
 }
 for(const link of document.querySelectorAll('a[href^="tel:"]')){link.href='tel:'+result.content.hotline;for(const text of [...link.childNodes])if(text.nodeType===Node.TEXT_NODE&&/\d{3}/.test(text.textContent))text.textContent=result.content.hotline;for(const el of link.querySelectorAll('strong,span'))if(!el.children.length&&/\d{3}/.test(el.textContent))el.textContent=result.content.hotline}
 document.dispatchEvent(new Event('cms-updated'));
 document.querySelector('footer').textContent=result.content.footer||document.querySelector('footer').textContent;
}catch{}}
load();window.addEventListener('focus',load);setInterval(()=>{if(!document.hidden)load()},15000);
})();
