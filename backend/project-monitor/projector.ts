import type {ProjectSnapshot} from "./schema";
export type StatusEvent={state:ProjectSnapshot["state"];stage:string;currentTask:string;progress:ProjectSnapshot["progress"];blocker?:string|null;commitSha?:string|null;observedAt:string};
export function projectStatus(base:ProjectSnapshot,e:StatusEvent):ProjectSnapshot{
 return {...base,state:e.state,stage:e.stage,currentTask:e.currentTask,progress:e.progress,blocker:e.blocker??null,latestCommit:e.commitSha??base.latestCommit,updatedAt:e.observedAt,
 evidence:[...base.evidence,{source:"research-pipeline",commitSha:e.commitSha??undefined,observedAt:e.observedAt}].slice(-50)};
}
