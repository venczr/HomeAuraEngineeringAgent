from __future__ import annotations
import concurrent.futures,json,os
from mcp.server.fastmcp import FastMCP
from tools.tokenwave_mcp import router
mcp=FastMCP("HomeAura TokenWave Router")
@mcp.tool()
def delegate_task(task:str,context:str="",task_type:str="ANALYSIS",complexity:str="MEDIUM",preferred_model:str|None=None,max_output_tokens:int=1200,task_id:str|None=None)->dict:return router.call(task,context,task_type,complexity,preferred_model,max_output_tokens,task_id)
@mcp.tool()
def review_solution(task:str,context:str,proposed_solution:str,preferred_model:str|None=None,task_id:str|None=None)->dict:return router.call("Review independently: "+task,context+"\nPROPOSED:\n"+proposed_solution,"REVIEW",preferred_model=preferred_model,task_id=task_id)
@mcp.tool()
def parallel_analysis(task:str,context:str,models:list[str],max_parallel:int=2,task_id:str|None=None)->dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_parallel,router.CONFIG["budgets"]["max_parallel_calls"])) as pool:
        futures=[pool.submit(router.call,task,context,"ANALYSIS",preferred_model=m,task_id=task_id) for m in models]
        return {"results":[f.result() if not f.exception() else {"error":type(f.exception()).__name__} for f in futures]}
@mcp.tool()
def consensus(task:str,context:str,candidate_answers:list[str],task_id:str|None=None)->dict:
    normalized={" ".join(x.lower().split()) for x in candidate_answers}
    if len(normalized)<=1:return {"deterministic_consensus":True,"answer":candidate_answers[0] if candidate_answers else ""}
    return router.call("Resolve substantive conflict: "+task,context+"\nCANDIDATES:\n"+json.dumps(candidate_answers),"HARD",task_id=task_id)
@mcp.tool()
def escalate(task:str,context:str,reason:str,task_id:str|None=None)->dict:
    result=router.call(task,context+"\nESCALATION_REASON:"+reason,"ESCALATION",task_id=task_id)
    router.METRICS["escalations"]+=1
    return result
@mcp.tool()
def router_status()->dict:return router.status()
if __name__=="__main__":
    if os.getenv("HOMEAURA_TOKENWAVE_MCP_HTTP")=="1":
        mcp.settings.host="127.0.0.1";mcp.settings.port=8765
        mcp.run(transport="streamable-http")
    else:mcp.run(transport="stdio")
