export const coreBaseUrl=(import.meta.env.VITE_TRACESHIELD_CORE_BASE_URL||"http://127.0.0.1:8787").replace(/\/$/,"");
export const useMockData=import.meta.env.VITE_USE_MOCK_DATA!=="false";

export class ApiError extends Error {
  constructor(public status:number,public path:string,message:string){super(message);this.name="ApiError";}
}

export async function apiRequest<T>(path:string,init:RequestInit={}):Promise<T>{
  let response:Response;
  try{
    response=await fetch(`${coreBaseUrl}${path}`,{...init,headers:{Accept:"application/json",...(init.body?{"Content-Type":"application/json"}:{}),...init.headers},signal:init.signal??AbortSignal.timeout(5000)});
  }catch(error){throw new ApiError(0,path,error instanceof Error?error.message:"Core is unreachable");}
  if(!response.ok){let detail=`Core returned ${response.status}`;try{const body=await response.json() as {error?:string};detail=body.error??detail;}catch{/* non-JSON error */}throw new ApiError(response.status,path,detail);}
  try{return await response.json() as T;}catch{throw new ApiError(response.status,path,"Core returned invalid JSON");}
}

export const apiGet=<T>(path:string)=>apiRequest<T>(path);
export const apiPatch=<T>(path:string,body:unknown)=>apiRequest<T>(path,{method:"PATCH",body:JSON.stringify(body)});
export const apiPost=<T>(path:string,body:unknown)=>apiRequest<T>(path,{method:"POST",body:JSON.stringify(body)});
