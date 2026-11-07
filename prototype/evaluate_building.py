"""Evaluate building centerlines and portal instances; never imported by inference."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from cave_segmentation.evaluate import segments,normalize,score


def portal_score(predicted,reference,tolerance):
    predicted=normalize(predicted);reference=normalize(reference);adjacency=[]
    for p in predicted.reshape(-1,2,2):
        options=[]
        for i,r in enumerate(reference.reshape(-1,2,2)):
            distance=min(float(np.linalg.norm(p-r,axis=1).max()),float(np.linalg.norm(p-r[::-1],axis=1).max()))
            if distance<=tolerance:options.append((distance,i))
        adjacency.append([i for _,i in sorted(options)])
    assignments={}
    def match(candidate,seen):
        for target in adjacency[candidate]:
            if target in seen:continue
            seen.add(target)
            if target not in assignments or match(assignments[target],seen):assignments[target]=candidate;return True
        return False
    for i in range(len(predicted)):match(i,set())
    return {'proposals':len(predicted),'reference_portals':len(reference),'matched':len(assignments),'precision':len(assignments)/len(predicted)if len(predicted)else None,'recall':len(assignments)/len(reference)if len(reference)else None,'criterion':'Both corresponding endpoints within tolerance, either direction, one-to-one maximum matching','tolerance_pixels':tolerance}


def evaluate(reference,candidate,output,heldout=None):
    doc=json.loads(Path(reference).read_text());raw=json.loads(Path(candidate).read_text());g=doc['resolution']['pixels_per_grid'];w=round(doc['resolution']['map_size']['x']*g);h=round(doc['resolution']['map_size']['y']*g);wall=normalize(raw['walls']);ref=segments(doc['line_of_sight'],g);portals=normalize(raw.get('portals',[]));reference_portals=np.asarray([[a['x']*g,a['y']*g,b['x']*g,b['y']*g]for p in doc.get('portals',[])for a,b in zip(p['bounds'],p['bounds'][1:])],float).reshape(-1,4)
    mask=cv2.imread(heldout,cv2.IMREAD_GRAYSCALE)if heldout else None
    result={'reference_role':'Evaluation only','structural':score(wall,ref,w,h,g,mask),'portals':{'full_image':portal_score(portals,reference_portals,g*.2)},'warning':'Same-map spatial development validation when heldout mask supplied; no independent-map claim. Portal predictions are unverified. Structural visibility assumes all portal spans open.'}
    if mask is not None:
        def select(lines):
            points=(lines[:,:2]+lines[:,2:])/2;x=np.clip((points[:,0]*mask.shape[1]/w).astype(int),0,mask.shape[1]-1);y=np.clip((points[:,1]*mask.shape[0]/h).astype(int),0,mask.shape[0]-1);return lines[mask[y,x]>0]
        result['portals']['spatial_heldout']=portal_score(select(portals),select(reference_portals),g*.2)
    result['all_portals_closed_visibility']=score(np.concatenate((wall,portals)),np.concatenate((ref,reference_portals)),w,h,g)['visibility']
    Path(output).write_text(json.dumps(result,indent=2));print(json.dumps({'boundary_heldout':result['structural'].get('spatial_heldout'),'portals':result['portals'],'open_portals_visibility':result['structural']['visibility'],'closed_portals_visibility':result['all_portals_closed_visibility']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference',nargs='?');p.add_argument('candidate',nargs='?');p.add_argument('output',nargs='?');p.add_argument('--heldout');p.add_argument('--selfcheck',action='store_true');a=p.parse_args()
    if a.selfcheck:
        r=[[0,0,10,0],[0,0,10,0]];assert portal_score([[10,0,0,0]],r,.1)['matched']==1
        assert portal_score([],r,1)['recall']==0
        assert portal_score([[0,0,2,0]],[[0,0,10,0]],1)['matched']==0
        assert portal_score([[0,0,10,0],[0,0,10,0]],[[0,0,10,0]],1)['precision']==.5
        print('Portal direction, duplicate, missing and shortened-span checks passed')
    else:assert a.reference and a.candidate and a.output;evaluate(a.reference,a.candidate,a.output,a.heldout)
