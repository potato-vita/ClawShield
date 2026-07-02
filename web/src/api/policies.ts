import {apiGet,apiPatch,apiPost} from "./client";
import type {Policy} from "@/types/policy";
export const getPolicies=()=>apiGet<{policies:Policy[]}>("/v1/policies").then(data=>data.policies);
export const updatePolicy=(policyId:string,patch:Partial<Policy>)=>apiPatch<Policy>(`/v1/policies/${encodeURIComponent(policyId)}`,patch);
export const createPolicy=(policy:Omit<Policy,"id"|"hitCount"|"lastHitTime">)=>apiPost<Policy>("/v1/policies",policy);
