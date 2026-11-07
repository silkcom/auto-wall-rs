"""Conservative portal proposal anchoring; geometry only, no reference input."""
import argparse,json,math,collections
from pathlib import Path
import numpy as np


def anchored(walls,portals,grid):
    assert math.isfinite(grid)and grid>0
    graph={}
    def key(p):return tuple(round(float(x),4)for x in p)
    for line in walls:
        a,b=key(line[:2]),key(line[2:]);graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a)
    terminals=[]
    for start,neighbors in graph.items():
        if len(neighbors)!=1:continue
        previous=start;current=next(iter(neighbors));length=np.linalg.norm(np.subtract(current,start))
        while len(graph[current])==2 and length<grid*.5:
            next_point=next(p for p in graph[current]if p!=previous);length+=np.linalg.norm(np.subtract(next_point,current));previous,current=current,next_point
        direction=np.subtract(current,start);norm=np.linalg.norm(direction)
        if norm:terminals.append((np.asarray(start),direction/norm))
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    def obstructed(a,b):
        v=b-a;size=np.dot(v,v)
        for wall in walls:
            c,d=np.asarray(wall,float).reshape(2,2);u=d-c;den=cross(v,u)
            if abs(den)>1e-8:
                t=cross(c-a,u)/den;s=cross(c-a,v)/den
                if .05<t<.95 and 0<=s<=1:return True
            elif abs(cross(c-a,v))/np.sqrt(size)<2:
                lo,hi=sorted((np.dot(c-a,v)/size,np.dot(d-a,v)/size))
                if min(.95,hi)>max(.05,lo):return True
        return False
    accepted={}
    for proposal in portals:
        p,q=np.asarray(proposal,float).reshape(2,2);axis=q-p;norm=np.linalg.norm(axis)
        if not norm:continue
        axis/=norm;left=[(a,t)for a,t in terminals if np.linalg.norm(a-p)<=grid*.3];right=[(b,t)for b,t in terminals if np.linalg.norm(b-q)<=grid*.3];options=[]
        for a,ta in left:
            for b,tb in right:
                v=b-a;length=np.linalg.norm(v)
                if length<grid*.25 or length>grid*2:continue
                direction=v/length
                if np.dot(ta,direction)>-.8 or np.dot(tb,direction)<.8 or abs(cross(axis,direction))>.5:continue
                if obstructed(a,b):continue
                options.append((np.linalg.norm(a-p)+np.linalg.norm(b-q),a,b))
        if options:
            distance,a,b=min(options,key=lambda row:row[0]);identity=tuple(sorted((key(a),key(b))));accepted[identity]=[*a.tolist(),*b.tolist()]
    return list(accepted.values())


def gap_candidates(walls,grid):
    graph={}
    for line in walls:
        a,b=tuple(line[:2]),tuple(line[2:]);graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a)
    ends=sorted(a for a,n in graph.items()if len(n)==1);buckets=collections.defaultdict(list);candidates=[];size=grid*2
    for a in ends:
        cell=tuple(int(x//size)for x in a)
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                for b in buckets[(cell[0]+dx,cell[1]+dy)]:
                    length=np.linalg.norm(np.subtract(a,b))
                    if grid*.25<=length<=grid*2:candidates.append([*a,*b])
        buckets[cell].append(a)
    return candidates


def selfcheck():
    walls=[[0,0,40,0],[60,0,100,0]];proposal=[[44,1,56,1]]
    assert anchored(walls,proposal,49)==[[40.,0.,60.,0.]]
    assert not anchored(walls,[[20,30,35,30]],49)
    assert not anchored(walls+[[50,-10,50,10]],proposal,49)
    assert len(anchored(walls,proposal+[[56,1,44,1]],49))==1
    gaps=anchored(walls,gap_candidates(walls,49),49);assert len(gaps)==1 and set(tuple(gaps[0][i:i+2])for i in(0,2))=={(40.,0.),(60.,0.)}
    print('Portal attachment, unsupported, permanent-blocker and duplicate checks passed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',nargs='?');p.add_argument('output',nargs='?');p.add_argument('--grid',type=float);p.add_argument('--selfcheck',action='store_true');p.add_argument('--from-wall-gaps',action='store_true');a=p.parse_args()
    if a.selfcheck:selfcheck()
    else:
        assert a.input and a.output and a.grid;data=json.loads(Path(a.input).read_text());original=gap_candidates(data['walls'],a.grid)if a.from_wall_gaps else data.get('portals',[]);data['portals']=anchored(data['walls'],original,a.grid);data['portal_support']={'input_proposals':len(original),'supported_proposals':len(data['portals']),'reference_read':False,'grid_hint':a.grid,'source':'wall endpoint gaps'if a.from_wall_gaps else'portal class regions','note':'Wall-anchored proposals remain unverified door classifications.'};Path(a.output).write_text(json.dumps(data));print(json.dumps(data['portal_support']))
