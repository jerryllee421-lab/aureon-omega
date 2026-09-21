async function request(path:string,body?:unknown){
  const response=await fetch(path,{
    method:body===undefined?'GET':'POST',
    headers:{'Content-Type':'application/json'},
    body:body===undefined?undefined:JSON.stringify(body)
  });
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.error||'REQUEST_FAILED');
  return {data};
}
export const api={get:(path:string)=>request(path),post:(path:string,body:unknown)=>request(path,body)};
