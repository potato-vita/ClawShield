import {apiGet} from "./client";
import type {DashboardMetrics} from "@/types/session";

interface CoreRuntimeStatus{tool_calls_24h:number;blocked_24h:number;high_risk_24h:number;policy_hits_24h:number}
export async function getDashboardMetrics():Promise<DashboardMetrics>{const data=await apiGet<CoreRuntimeStatus>("/v1/dashboard/runtime-status");return{toolCalls24h:data.tool_calls_24h,blocked:data.blocked_24h,highRisk:data.high_risk_24h,policyHits:data.policy_hits_24h};}
