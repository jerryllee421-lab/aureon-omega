type Session={accessToken:string;refreshToken:string|null;supabaseUrl:string;publishableKey:string};
let session:Session|null=null;

export function setSession(value:Session){session=value;}
export function clearSession(){session=null;}
export function setAccessToken(value:string|null){
  if(!value){session=null;return;}
  if(session)session={...session,accessToken:value};
}

async function refreshSession(){
  if(!session?.refreshToken)return false;
  const response=await fetch(session.supabaseUrl+'/auth/v1/token?grant_type=refresh_token',{
    method:'POST',headers:{apikey:session.publishableKey,'Content-Type':'application/json'},
    body:JSON.stringify({refresh_token:session.refreshToken})
  });
  const data=await response.json().catch(()=>({}));
  if(!response.ok||!data.access_token){session=null;return false;}
  session={...session,accessToken:data.access_token,refreshToken:data.refresh_token||session.refreshToken};
  return true;
}

async function request(path:string,body?:unknown,retry=true){
  const response=await fetch(path,{
    method:body===undefined?'GET':'POST',
    headers:{'Content-Type':'application/json',...(session?.accessToken?{Authorization:'Bearer '+session.accessToken}:{})},
    body:body===undefined?undefined:JSON.stringify(body)
  });
  const data=await response.json().catch(()=>({}));
  if(response.status===401&&retry&&session?.refreshToken&&await refreshSession())return request(path,body,false);
  if(!response.ok)throw new Error(data.error||'REQUEST_FAILED');
  return {data};
}
export const api={get:(path:string)=>request(path),post:(path:string,body:unknown)=>request(path,body)};
