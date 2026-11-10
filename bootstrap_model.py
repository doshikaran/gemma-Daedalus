"""Download and hash-check the pinned official primary Gemma CPU runtime."""
import concurrent.futures,hashlib,json,pathlib,tarfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
ITEMS=[('gemma-4-E4B_q4_0-it.gguf','https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf/resolve/4b4a2c1d584be7264f87aac328a1bc739ce81b6c/gemma-4-E4B_q4_0-it.gguf','676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee',False),('llama-b12020-bin-ubuntu-x64.tar.gz','https://github.com/ggml-org/llama.cpp/releases/download/b12020/llama-b12020-bin-ubuntu-x64.tar.gz','1b69032f9ab60dc6aa909689fda941fa1b9162f6ab46b863582d5649d96ac6be',True)]
def run(item):
    name,url,expected,unpack=item;p=ROOT/'runtime'/name;p.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();n=0
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Daedalus-Research'}),timeout=90)as r,p.open('wb')as out:
        while chunk:=r.read(8*1024*1024):out.write(chunk);h.update(chunk);n+=len(chunk)
    assert h.hexdigest()==expected,(name,h.hexdigest())
    if unpack:
        with tarfile.open(p)as t:t.extractall(ROOT/'runtime',filter='data')
    row={'name':name,'url':url,'bytes':n,'sha256':expected};print(json.dumps(row),flush=True);return row
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,ITEMS))
    (ROOT/'results/primary_model_restored.json').write_text(json.dumps(rows,indent=2)+'\n')
