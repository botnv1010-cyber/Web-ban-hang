/* Notify only after a successful server mutation; no credentials or content in messages. */
(()=>{'use strict';
const key='site-invalidation-v1';let channel;try{channel=new BroadcastChannel(key)}catch{}
const seen=new Set();
function receive(message){if(message?.id){if(seen.has(message.id))return;seen.add(message.id);if(seen.size>100)seen.delete(seen.values().next().value)}if(!message||!['content','plans','consultations'].includes(message.resource))return;if(message.resource==='plans'){try{localStorage.removeItem('catalog-cache-v1')}catch{}}window.dispatchEvent(new CustomEvent('site:invalidate',{detail:message}))}
window.notifySiteChange=(resource)=>{const message={resource,id:crypto.randomUUID()};receive(message);try{localStorage.setItem(key,JSON.stringify(message));channel?.postMessage(message)}catch{}};
if(channel)channel.onmessage=e=>receive(e.data);
window.addEventListener('storage',e=>{if(e.key===key){try{receive(JSON.parse(e.newValue))}catch{}}});
// Other devices discover committed database revisions without downloading whole catalogs.
let running=false,previous;
async function check(){if(running||document.hidden)return;running=true;try{const r=await fetch('/api/revisions',{cache:'no-store',signal:AbortSignal.timeout(8000)});if(!r.ok)return;const next=await r.json();for(const resource of ['content','plans'])if(!previous||previous[resource]!==next[resource])receive({resource,revision:next[resource]});previous=next}catch{}finally{running=false}}
if(!location.pathname.startsWith('/admin')){check();setInterval(check,5000);window.addEventListener('focus',check);document.addEventListener('visibilitychange',check)}
})();
