export type ProjectState="RUNNING"|"IDLE"|"FAILED"|"BLOCKED"|"STALE"|"UNKNOWN";
export type EvidenceRef={source:string;artifact?:string;commitSha?:string;datasetSha256?:string;observedAt:string};
export type ProjectSnapshot={
 schema:"aureon.project.snapshot.v1"; state:ProjectState; currentTask:string|null; stage:string|null;
 progress:{completed:number;total:number;unit:string}|null;
 gold:{first:string|null;last:string|null;rows:number|null;integrity:"PASS"|"FAIL"|"UNKNOWN";timeframesValidated:number|null};
 tests:{queued:number;running:number;completed:number;rejected:number;promoted:number};
 champion:{name:string;net:number|null;profitFactor:number|null;drawdownPct:number|null;trades:number|null};
 challenger:{name:string|null;net:number|null;profitFactor:number|null;drawdownPct:number|null;trades:number|null;oosStatus:string|null;holdoutStatus:string|null};
 ctrader:{application:"SUBMITTED"|"ACTIVE"|"UNKNOWN";auth:string;demoCertification:string};
 blocker:string|null; latestCommit:string|null; deployment:string|null; updatedAt:string; evidence:EvidenceRef[];
};
