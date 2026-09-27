export interface SymbolMeta{id:number;symbolName:string;minVolume:number;maxVolume:number;stepVolume:number;digits:number}
export function normalizeVolume(requested:number,s:SymbolMeta){
 const v=Math.max(s.minVolume,Math.min(requested,s.maxVolume));
 return Math.floor((v-s.minVolume)/s.stepVolume)*s.stepVolume+s.minVolume;
}
export function selectSymbol(symbols:SymbolMeta[],wanted:string){
 const key=wanted.replace(/[^A-Z0-9]/gi,'').toUpperCase();
 const exact=symbols.filter(s=>s.symbolName.replace(/[^A-Z0-9]/gi,'').toUpperCase()===key);
 if(exact.length!==1)throw new Error(exact.length?'AMBIGUOUS_SYMBOL':'SYMBOL_NOT_FOUND');
 return exact[0];
}
