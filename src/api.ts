export async function api<T>(path:string, options:RequestInit={}):Promise<T>{
  const token=localStorage.getItem('aureon_access_token')
  const headers=new Headers(options.headers)
  headers.set('Content-Type','application/json')
  if(token)headers.set('Authorization',`Bearer ${token}`)
  const response=await fetch('/api/'+path.replace(/^\//,''),{...options,headers})
  const data=await response.json().catch(()=>({}))
  if(!response.ok)throw new Error(data.error||'REQUEST_FAILED')
  return data as T
}
