const SECRET_KEYS=/client.?secret|access.?token|refresh.?token|password/i;
export function assertNoSecrets(value:unknown,path='root'):void{
 if(!value||typeof value!=='object')return;
 for(const [k,v] of Object.entries(value as Record<string,unknown>)){
  if(SECRET_KEYS.test(k)&&typeof v==='string'&&v.length>0)throw new Error('SECRET_MATERIAL_BLOCKED:'+path+'.'+k);
  assertNoSecrets(v,path+'.'+k);
 }
}
