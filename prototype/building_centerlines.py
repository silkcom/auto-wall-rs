"""Thin predicted building material into centerlines; no reference input."""
import argparse,json,time
from pathlib import Path
import cv2
import numpy as np


def thin(mask):
    image=np.pad((mask>0).astype(np.uint8),1)
    while True:
        changed=False
        for step in (0,1):
            p=[image[:-2,1:-1],image[:-2,2:],image[1:-1,2:],image[2:,2:],image[2:,1:-1],image[2:,:-2],image[1:-1,:-2],image[:-2,:-2]]
            count=sum(p);transitions=sum((a==0)&(b==1) for a,b in zip(p,p[1:]+p[:1]))
            center=image[1:-1,1:-1]
            remove=(center==1)&(count>=2)&(count<=6)&(transitions==1)
            if step==0:remove&=(p[0]*p[2]*p[4]==0)&(p[2]*p[4]*p[6]==0)
            else:remove&=(p[0]*p[2]*p[6]==0)&(p[0]*p[4]*p[6]==0)
            if remove.any():center[remove]=0;changed=True
        if not changed:return image[1:-1,1:-1]


def paths(mask):
    pixels=set(map(tuple,np.column_stack(np.nonzero(mask))))
    def neighbors(p):
        y,x=p;result=[]
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                q=(y+dy,x+dx)
                if not(dx or dy)or q not in pixels:continue
                # Do not count a diagonal shortcut through an existing right-angle step.
                if dx and dy and ((y+dy,x)in pixels or(y,x+dx)in pixels):continue
                result.append(q)
        return sorted(result)
    graph={p:neighbors(p)for p in pixels};nodes={p for p in pixels if len(graph[p])!=2};seen=set();result=[]
    def edge(a,b):return tuple(sorted((a,b)))
    def trace(start,next_point):
        line=[start];previous=start;current=next_point;seen.add(edge(previous,current))
        while True:
            line.append(current)
            if current in nodes or current==start:break
            follow=[q for q in graph[current]if q!=previous]
            if not follow:break
            q=follow[0]
            if edge(current,q)in seen:break
            seen.add(edge(current,q));previous,current=current,q
        return line
    for start in sorted(nodes):
        for neighbor in graph[start]:
            if edge(start,neighbor)not in seen:result.append(trace(start,neighbor))
    for start in sorted(pixels):
        for neighbor in graph[start]:
            if edge(start,neighbor)not in seen:result.append(trace(start,neighbor))
    return result


def extract(classes,image_shape,straight_grid=None):
    h,w=classes.shape;sy=image_shape[0]/h;sx=image_shape[1]/w
    epsilon=.5 if straight_grid is None else straight_grid*.12/max(sx,sy)
    assert epsilon>0 and np.isfinite(epsilon)
    def source(p):return [(float(p[0])+.5)*sx-.5,(float(p[1])+.5)*sy-.5]
    # Keep permanent centerlines out of predicted door spans; proposals remain unverified.
    door=classes==2;wall=(classes==1)&(cv2.dilate(door.astype(np.uint8),np.ones((3,3),np.uint8))==0)
    skeleton=thin(wall);walls=[]
    for line in paths(skeleton):
        points=np.asarray([(x,y)for y,x in line],np.float32)
        if len(points)<2:continue
        closed=np.array_equal(points[0],points[-1]);points=cv2.approxPolyDP(points,epsilon,closed).reshape(-1,2)
        pairs=list(zip(points,points[1:]))
        if closed and len(points)>2:pairs.append((points[-1],points[0]))
        for a,b in pairs:
            if not np.array_equal(a,b):walls.append([*source(a),*source(b)])
    portals=[];n,components,stats,_=cv2.connectedComponentsWithStats(door.astype(np.uint8),8)
    for i in range(1,n):
        if stats[i,cv2.CC_STAT_AREA]<3:continue
        yy,xx=np.nonzero(components==i);points=np.column_stack((xx,yy)).astype(np.float64);center=points.mean(axis=0);delta=points-center
        angle=.5*np.arctan2(2*np.sum(delta[:,0]*delta[:,1]),np.sum(delta[:,0]**2-delta[:,1]**2));axis=np.array([np.cos(angle),np.sin(angle)]);along=delta[:,0]*axis[0]+delta[:,1]*axis[1]
        length=float(np.max(along)-np.min(along))
        if length<2:continue
        a=center+axis*np.min(along);b=center+axis*np.max(along);portals.append([*source(a),*source(b)])
    assert np.isfinite(np.asarray(walls+portals)).all()
    return {'walls':walls,'portals':portals},skeleton


def selfcheck():
    # A two-faced wall must yield one central blocker; the doorway must remain open.
    c=np.zeros((40,60),np.uint8);c[4:36,28:33]=1;c[17:23,28:33]=2
    result,skeleton=extract(c,c.shape);assert np.count_nonzero(skeleton[10])==1
    assert abs(float(np.flatnonzero(skeleton[10])[0])-30)<=1
    assert not skeleton[20].any() and len(result['portals'])==1
    assert all(not(min(s[1],s[3])<20<max(s[1],s[3]))for s in result['walls'])
    # Closed rooms stay connected single rings, rather than two material-edge loops.
    room=np.zeros((40,50),np.uint8);cv2.rectangle(room,(5,5),(44,34),1,5);lines=paths(thin(room));assert len(lines)==1 and lines[0][0]==lines[0][-1]
    empty,_=extract(np.zeros((20,30),np.uint8),(81,121));assert empty=={'walls':[],'portals':[]}
    jitter=np.zeros((60,160),np.uint8);points=np.array([(x,20+(i%2)*3)for i,x in enumerate(range(5,155,8))],np.int32);cv2.polylines(jitter,[points],False,1,1)
    raw,_=extract(jitter,jitter.shape);straight,_=extract(jitter,jitter.shape,49);assert len(straight['walls'])<len(raw['walls'])/2
    diagonal=np.zeros((100,130),np.uint8);cv2.line(diagonal,(15,15),(110,75),1,5);result,_=extract(diagonal,diagonal.shape,49);assert len(result['walls'])<=3
    longest=max(result['walls'],key=lambda l:(l[2]-l[0])**2+(l[3]-l[1])**2);v=np.array([longest[2]-longest[0],longest[3]-longest[1]]);target=np.array([95,60]);assert abs(np.dot(v,target))/(np.linalg.norm(v)*np.linalg.norm(target))>np.cos(.06)
    opened,_=extract(c,c.shape,49);assert all(not(min(l[1],l[3])<20<max(l[1],l[3]))for l in opened['walls'])
    print('Centerline, doorway, room, blank, straightening and diagonal checks passed')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('classes',nargs='?');p.add_argument('image',nargs='?');p.add_argument('output',nargs='?');p.add_argument('--selfcheck',action='store_true');p.add_argument('--straight-grid',type=float);a=p.parse_args()
    if a.selfcheck:selfcheck();return
    assert a.classes and a.image and a.output
    start=time.perf_counter();classes=cv2.imread(a.classes,cv2.IMREAD_GRAYSCALE);im=cv2.imread(a.image);assert classes is not None and im is not None;assert set(np.unique(classes)).issubset({0,1,2})
    result,skeleton=extract(classes,im.shape,a.straight_grid);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);(out/'walls.json').write_text(json.dumps(result));cv2.imwrite(str(out/'skeleton.png'),skeleton*255)
    overlay=im.copy()
    for key,color in [('walls',(50,245,60)),('portals',(66,174,255))]:
        for x,y,u,v in result[key]:cv2.line(overlay,(round(x),round(y)),(round(u),round(v)),color,3)
    cv2.imwrite(str(out/'overlay.jpg'),overlay);report={'seconds':time.perf_counter()-start,'reference_read':False,'inputs':['predicted class raster','source image dimensions'],'centerline_method':'Zhang-Suen thinning and pixel graph tracing','straight_grid_hint':a.straight_grid,'simplification_source_pixels':a.straight_grid*.12 if a.straight_grid else None,'wall_segments':len(result['walls']),'portal_proposals':len(result['portals']),'limitations':'Geometry follows the predicted mask. Portal spans are unverified; missed or false semantic labels remain errors.'};(out/'inference.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
