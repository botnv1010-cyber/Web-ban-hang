/* Accept source files below 10 MiB; keep the actual API payload within Vercel limits. */
window.prepareAdminImage=async function(file){
 if(!file||file.size>=10*1024*1024)throw Error('Ảnh phải có dung lượng dưới 10 MB.');
 if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw Error('Chọn ảnh PNG, JPEG hoặc WebP.');
 const url=URL.createObjectURL(file);const image=new Image();
 try{
 image.src=url;await image.decode();if(!image.naturalWidth||!image.naturalHeight)throw Error();
 const scale=Math.min(1,2560/Math.max(image.naturalWidth,image.naturalHeight));
 const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));canvas.height=Math.max(1,Math.round(image.naturalHeight*scale));const context=canvas.getContext('2d');if(!context)throw Error();context.fillStyle='#fff';context.fillRect(0,0,canvas.width,canvas.height);context.drawImage(image,0,0,canvas.width,canvas.height);
 let blob;
 for(const maxSide of [2560,1920,1440]){
  const ratio=Math.min(1,maxSide/Math.max(image.naturalWidth,image.naturalHeight));canvas.width=Math.max(1,Math.round(image.naturalWidth*ratio));canvas.height=Math.max(1,Math.round(image.naturalHeight*ratio));context.fillStyle='#fff';context.fillRect(0,0,canvas.width,canvas.height);context.drawImage(image,0,0,canvas.width,canvas.height);
  for(const quality of [.9,.8,.7,.6,.5]){blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/webp',quality));if(blob&&blob.size<=2300000)break}
  if(blob&&blob.size<=2300000)break;
 }
 if(!blob||blob.size>2300000)throw Error('Không tối ưu được ảnh này. Hãy chọn ảnh có kích thước nhỏ hơn.');
 return await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(blob)});
 }catch(error){if(error.message?.includes('tối ưu'))throw error;throw Error('Không đọc được ảnh. Vui lòng chọn tệp ảnh PNG, JPEG hoặc WebP hợp lệ.')}finally{URL.revokeObjectURL(url)}
};
