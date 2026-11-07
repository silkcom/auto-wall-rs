"""Geometry-first building proposal experiment: grayscale wall pairs and enclosures."""
import argparse,hashlib,json,time,collections
from pathlib import Path
import cv2,numpy as np

RULES={'working_grid_pixels':32,'working_cap':2800,'unpaired_discovery_length_grid':1.2,'minimum_face_length_grid':.4,'wall_width_grid':[.05,.45],'parallel_degrees':4,'proposal_gap_grid':1.0,'minimum_region_area_grid2':3,'minimum_region_width_grid':.9,'proposal_close_grid':1.5,'minimum_supported_box_sides':3,'minimum_axis_fraction':.65,'minimum_texture_axis_fraction':.55,'interior_inset_grid':.5,'inset_short_side_fraction':.25}

def dot(a,b):
    a=np.asarray(a);return a[...,0]*b[0]+a[...,1]*b[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def combine(lines,g):
    groups=[]
    for row in sorted(lines,key=lambda a:-np.linalg.norm(a[2:]-a[:2])):
        a,b=row.reshape(2,2);u=b-a;length=np.linalg.norm(u)
        if length==0:continue
        u/=length
        if u[0]<0:u=-u
        center=(a+b)/2
        for group in groups:
            v=group['u'];n=np.array([-v[1],v[0]]);values=np.array([dot(a,v),dot(b,v)]);lo,hi=min(values),max(values)
            if abs(dot(u,v))>np.cos(np.deg2rad(4)) and abs(dot(center-group['center'],n))<g*.18 and max(group['lo'],lo)<=min(group['hi'],hi)+g*.5:
                group['center']=(group['center']*group['weight']+center*length)/(group['weight']+length);group['weight']+=length;group['lo']=min(group['lo'],lo);group['hi']=max(group['hi'],hi);break
        else:groups.append({'u':u,'center':center,'weight':length,'lo':min(dot(a,u),dot(b,u)),'hi':max(dot(a,u),dot(b,u))})
    result=[]
    for group in groups:
        u=group['u'];n=np.array([-u[1],u[0]]);offset=dot(n,group['center']);result.append(np.r_[u*group['lo']+n*offset,u*group['hi']+n*offset])
    return result


def detect(image,grid):
    cv2.setRNGSeed(42)
    factor=min(1,32/grid,2800/max(image.shape[:2]));small=cv2.resize(image,None,fx=factor,fy=factor,interpolation=cv2.INTER_AREA);h,w=small.shape[:2];sx=image.shape[1]/w;sy=image.shape[0]/h;g=grid*factor
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);gray=cv2.createCLAHE(2,(8,8)).apply(gray);gray=cv2.GaussianBlur(gray,(3,3),.6)
    found=cv2.createLineSegmentDetector().detect(gray)[0];lines=np.empty((0,4))if found is None else found.reshape(-1,4).astype(float);lengths=np.linalg.norm(lines[:,2:]-lines[:,:2],axis=1);lines=lines[lengths>=g*.4];lengths=lengths[lengths>=g*.4]
    vectors=lines[:,2:]-lines[:,:2];units=vectors/lengths[:,None];centers=(lines[:,:2]+lines[:,2:])/2;pairs=[]
    for i,(a,u)in enumerate(zip(lines,units)):
        n=np.array([-u[1],u[0]]);separation=np.abs(dot(centers-centers[i],n));eligible=np.flatnonzero((np.abs(dot(units,u))>=np.cos(np.deg2rad(4)))&(separation>=g*.05)&(separation<=g*.45)&(np.arange(len(lines))>i))
        own=np.sort(dot(a.reshape(2,2),u))
        for j in eligible:
            other=np.sort(dot(lines[j].reshape(2,2),u));lo=max(own[0],other[0]);hi=min(own[1],other[1])
            if hi-lo<g*.3 or(hi-lo)/min(lengths[i],lengths[j])<.5:continue
            offset=dot((centers[i]+centers[j])/2,n);pairs.append(np.r_[u*lo+n*offset,u*hi+n*offset])
    pairmask=np.zeros((h,w),np.uint8)
    for x,y,z,t in pairs:cv2.line(pairmask,(round(x),round(y)),(round(z),round(t)),255,1)
    discovery=pairmask.copy()
    for x,y,z,t in lines[lengths>=g*1.2]:cv2.line(discovery,(round(x),round(y)),(round(z),round(t)),255,1)
    joined=cv2.HoughLinesP(discovery,1,np.pi/360,max(12,round(g*.6)),minLineLength=max(12,g*.8),maxLineGap=g);joined=np.empty((0,4))if joined is None else joined.reshape(-1,4).astype(float)
    barrier=np.zeros_like(pairmask)
    for x,y,z,t in joined:cv2.line(barrier,(round(x),round(y)),(round(z),round(t)),255,3)
    k=max(3,round(g*1.5)|1);padded=np.pad(barrier,k);padded=cv2.morphologyEx(padded,cv2.MORPH_CLOSE,np.ones((k,k),np.uint8));padded=cv2.morphologyEx(padded,cv2.MORPH_OPEN,np.ones((3,3),np.uint8));barrier=padded[k:-k,k:-k];shape_distance=cv2.distanceTransform(255-discovery,cv2.DIST_L2,cv2.DIST_MASK_PRECISE);contours,hierarchy=cv2.findContours(barrier,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE);boundary=np.zeros_like(barrier);regions=[];rejected=collections.Counter()
    if hierarchy is not None:
        for i,c in enumerate(contours):
            if hierarchy[0,i,3]<0:c=cv2.convexHull(c)
            area=cv2.contourArea(c)
            if area<3*g*g or area>600*g*g:rejected['area']+=1;continue
            rect=cv2.minAreaRect(c);sizes=sorted(rect[1])
            if sizes[0]<g*.9 or sizes[1]/sizes[0]>10 or area/(sizes[0]*sizes[1])<.5:rejected['extent']+=1;continue
            parent=hierarchy[0,i,3]
            if parent<0:
                box=cv2.boxPoints(rect);sides=0
                for a,b in zip(box,np.roll(box,-1,axis=0)):
                    samples=a+(b-a)*np.linspace(0,1,max(2,round(np.linalg.norm(b-a))))[:,None];xx=np.clip(np.rint(samples[:,0]).astype(int),0,w-1);yy=np.clip(np.rint(samples[:,1]).astype(int),0,h-1)
                    sides+=float(np.mean(shape_distance[yy,xx]<=g*.2))>=.2
                if sides<3:rejected['unsupported_shape']+=1;continue
            poly=cv2.approxPolyDP(c,g*.2,True).reshape(-1,2)
            if len(poly)<4 or len(poly)>24:rejected['corners']+=1;continue
            box=cv2.boxPoints(rect);axis=box[1]-box[0];axis=axis/np.linalg.norm(axis);other=np.array([-axis[1],axis[0]]);edge=np.roll(poly,-1,0)-poly;edge_length=np.linalg.norm(edge,axis=1);directions=edge/np.maximum(edge_length[:,None],1e-6);aligned=np.maximum(np.abs(dot(directions,axis)),np.abs(dot(directions,other)))>=np.cos(np.deg2rad(12));axis_fraction=float(edge_length[aligned].sum()/edge_length.sum())
            if axis_fraction<.65:rejected['axes']+=1;continue
            inset=min(g*.5,sizes[0]*.25);inside=np.array([cv2.pointPolygonTest(c,tuple(map(float,p)),True)>inset for p in centers]);texture=lengths[inside];directions=units[inside];total=texture.sum();good=np.maximum(np.abs(dot(directions,axis)),np.abs(dot(directions,other)))>=np.cos(np.deg2rad(12));aligned_length=texture[good].sum();texture_fraction=float(aligned_length/total)if total else 0
            if aligned_length<g or texture_fraction<.55:rejected['interior_texture']+=1;continue
            cv2.polylines(boundary,[poly],True,255,1);regions.append({'polygon':[[float(x*sx),float(y*sy)]for x,y in poly],'area_source_pixels':float(area*sx*sy),'axis_fraction':axis_fraction,'interior_alignment':texture_fraction})
    distance=cv2.distanceTransform(255-boundary,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)if regions else np.full((h,w),np.inf);evidence=cv2.distanceTransform(255-pairmask,cv2.DIST_L2,cv2.DIST_MASK_PRECISE);walls=[];openings=[]
    observed=cv2.HoughLinesP(pairmask,1,np.pi/360,max(12,round(g*.6)),minLineLength=max(12,g*.8),maxLineGap=g);observed=np.empty((0,4))if observed is None else observed.reshape(-1,4).astype(float)
    for row in combine(observed,g):
        a,b=row.reshape(2,2);length=np.linalg.norm(b-a);count=max(2,int(np.ceil(length)));points=a+(b-a)*np.linspace(0,1,count)[:,None];xx=np.clip(np.rint(points[:,0]).astype(int),0,w-1);yy=np.clip(np.rint(points[:,1]).astype(int),0,h-1);near=distance[yy,xx]<=g*.25;supported=near&(evidence[yy,xx]<=g*.10)
        cuts=np.r_[0,np.flatnonzero(supported[1:]!=supported[:-1])+1,count]
        for lo,hi in zip(cuts,cuts[1:]):
            if hi-lo<2:continue
            p,q=points[lo],points[hi-1];span=np.linalg.norm(q-p);result=[float(p[0]*sx),float(p[1]*sy),float(q[0]*sx),float(q[1]*sy)]
            if supported[lo]and span>=g*.4:walls.append(result)
            elif not supported[lo]and lo>0 and hi<count and np.all(near[lo:hi])and g*.2<=span<=g:openings.append(result)
    return {'walls':walls,'portals':openings,'regions':regions},dict(working=[w,h],long_edges=len(lines),paired_edges=len(pairs),proposal_lines=len(joined),regions=len(regions),rejected=dict(rejected)),pairmask,barrier,boundary


def run(image_path,out,grid):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);manifest={'image_sha256':sha(image_path),'code_sha256':sha(__file__),'rules':RULES,'grid_hint':grid,'reference_input':False,'trained_model':False};(out/'frozen-config.json').write_text(json.dumps(manifest,indent=2));start=time.perf_counter();im=cv2.imread(str(image_path));assert im is not None and grid>0;result,detail,pairs,barrier,boundary=detect(im,grid);seconds=time.perf_counter()-start
    (out/'walls.json').write_text(json.dumps(result));overlay=im.copy()
    for key,color in [('walls',(50,245,60)),('portals',(66,174,255))]:
        for x,y,z,t in result[key]:cv2.line(overlay,(round(x),round(y)),(round(z),round(t)),color,3)
    cv2.imwrite(str(out/'overlay.jpg'),overlay)
    for name,data in [('pairs',pairs),('closures',barrier),('regions',boundary)]:cv2.imwrite(str(out/f'{name}.png'),data)
    report={'seconds':seconds,'reference_read':False,'paid_vision_calls':0,'uses_learned_colors':False,'inputs':['source image converted to grayscale','fixed grid hint'],'wall_segments':len(result['walls']),'opening_proposals':len(result['portals']),**detail,'limitations':'Enclosure/texture proposals are not recognized buildings or doors. Virtual closures are not exported as permanent walls.'};(out/'inference.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


def selfcheck():
    room=np.full((260,300,3),70,np.uint8);cv2.rectangle(room,(50,40),(250,220),(185,185,185),-1)
    for y in range(52,215,12):cv2.line(room,(55,y),(245,y),(140,140,140),1)
    cv2.rectangle(room,(50,40),(250,220),(15,15,15),10)
    rotated=cv2.warpAffine(room,cv2.getRotationMatrix2D((150,130),23,1),(300,260),borderValue=(70,70,70))
    for image in (room,255-room,rotated):
        result,detail,*_=detect(image,40);assert detail['regions']>=1 and len(result['walls'])>=4
    first=detect(room,40)[0];assert first==detect(room,40)[0]
    blank=np.full_like(room,70);fence=blank.copy();cv2.line(fence,(30,130),(270,130),(15,15,15),8)
    yard=blank.copy();cv2.rectangle(yard,(50,40),(250,220),(15,15,15),10)
    for image in (blank,fence,yard):assert not detect(image,40)[0]['regions']
    print('Closed building, contrast inversion, rotation, blank, open/closed fence and repeatability checks passed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image',nargs='?');p.add_argument('out',nargs='?');p.add_argument('--grid',type=float,default=49.00020730856938);p.add_argument('--selfcheck',action='store_true');a=p.parse_args()
    if a.selfcheck:selfcheck()
    else:assert a.image and a.out;run(a.image,a.out,a.grid)
