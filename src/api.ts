function xhrRequest(path:string,body?:unknown):Promise<{data:any}>{
  return new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest();
    xhr.open(body===undefined?'GET':'POST',path,true);
    xhr.setRequestHeader('Content-Type','application/json');
    xhr.timeout=125000;
    xhr.onload=()=>{
      let data:any={};
      try{data=xhr.responseText?JSON.parse(xhr.responseText):{};}catch{}
      if(xhr.status>=200&&xhr.status<300)return resolve({data});
      reject(new Error(data?.error?`HTTP_${xhr.status}_${data.error}`:`HTTP_${xhr.status}_REQUEST_FAILED`));
    };
    xhr.onerror=()=>reject(new Error('NETWORK_REQUEST_FAILED'));
    xhr.ontimeout=()=>reject(new Error('REQUEST_TIMEOUT'));
    xhr.send(body===undefined?null:JSON.stringify(body));
  });
}
async function request(path:string,body?:unknown){
  const payload=body===undefined?undefined:JSON.stringify(body);
  try{
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),125000);
    try{
      const response=await fetch(path,{
        method:body===undefined?'GET':'POST',
        headers:{'Content-Type':'application/json'},
        body:payload,
        signal:controller.signal
      });
      const text=await response.text();
      let data:any={};
      try{data=text?JSON.parse(text):{};}catch{}
      if(!response.ok)throw new Error(data?.error?`HTTP_${response.status}_${data.error}`:`HTTP_${response.status}_REQUEST_FAILED`);
      return {data};
    }finally{clearTimeout(timer);}
  }catch(error){
    if(body===undefined)throw error;
    return xhrRequest(path,body);
  }
}
export const api={get:(path:string)=>request(path),post:(path:string,body:unknown)=>request(path,body)};
