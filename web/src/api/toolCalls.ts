import {apiGet} from "./client";
export const getToolCallDecision=(toolCallId:string)=>apiGet<Record<string,unknown>>(`/v1/tool-calls/${encodeURIComponent(toolCallId)}/decision`);
