import json,random,sys,datetime,uuid
mode,out=sys.argv[1],sys.argv[2]
random.seed(7)
t=datetime.datetime(2026,11,19,14,0,0)
lines=[];traces=[]
def rid(): return "req_"+uuid.uuid4().hex[:10]
for i in range(1200):
    t+=datetime.timedelta(seconds=3)
    r=random.random(); tid=uuid.uuid4().hex; rq=rid()
    path="/v1/chat"; status=200; ev="request"; err=None; lat=int(random.gauss(150,40))
    if mode=="auth" and i%9==0:
        path="/v1/me"; 
        if i%27==0 and i>200: status=500; ev="unhandled_exception"; err="SessionExpired: token exp=1731900000 < now (app/auth/session.py:14 raise SessionExpired, not caught)"
        else: status=200
    elif r<0.03: status=400; err="validation error: prompt missing"; ev="request"
    elif r<0.045: status=401; err="invalid api key"
    elif r<0.05: status=429; err="rate limited client key_abc"
    d={"ts":t.isoformat()+"Z","level":"ERROR" if status>=500 else "INFO","event":ev,"request_id":rq,"trace_id":tid,"path":path,"status":status,"latency_ms":max(30,lat)}
    if err:d["error"]=err
    lines.append(d)
    if status==500 and len(traces)<3:
        traces.append((tid,[{"name":"GET /v1/me","start_ms":0,"duration_ms":lat,"status":"ERROR","attributes":{"http.status_code":500}},{"name":"auth.validate_session","start_ms":2,"duration_ms":5,"status":"ERROR","attributes":{"exception.type":"SessionExpired","exception.message":"token expired","exception.stacktrace":"app/main.py:me -> app/auth/session.py:validate_session (raise SessionExpired)"}}]))
open(out+"/logs/app.jsonl","w").write("\n".join(json.dumps(x) for x in lines)+"\n")
for tid,sp in traces: json.dump(sp,open(f"{out}/traces/{tid}.json","w"),indent=1)
print(sum(1 for l in lines if l["status"]>=500),"5xx")
