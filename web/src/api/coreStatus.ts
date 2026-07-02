import {apiGet} from "./client";
import type {RuntimeStatus} from "@/types/session";
interface Health{ok:boolean;version:string;db_connected:boolean}
export async function getCoreStatus():Promise<RuntimeStatus>{const data=await apiGet<Health>("/v1/health");return{coreOnline:data.ok,databaseConnected:data.db_connected,pluginLastSeen:"event stream pending",eventsIngested:0,queueSize:0,coreVersion:data.version,policyVersion:"Core managed"};}
