"""Throwaway CPU MobileSAM test: semantic samples+labels, official checkpoint, output.

Whole-image and four overlapping crop prompts; model masks ranked only by seeds.
"""
import argparse, hashlib, json, sys, time
from pathlib import Path
import cv2
import numpy as np
import torch


def run(args):
    sys.path.insert(0,args.repo)
    from mobile_sam import sam_model_registry, SamPredictor
    torch.set_num_threads(4)
    start=time.perf_counter()
    model=sam_model_registry['vit_t'](checkpoint=args.checkpoint).to('cpu').eval()
    predictor=SamPredictor(model)
    samples=json.loads(Path(args.samples).read_text());labels=json.loads(Path(args.labels).read_text())['labels']
    im=cv2.imread(samples['image']);assert im is not None
    h,w=im.shape[:2]
    points=np.array([[s['x'],s['y']] for s in samples['samples'] if labels[s['id']] in ('floor','solid')],np.float32)
    targets=np.array([labels[s['id']]=='floor' for s in samples['samples'] if labels[s['id']] in ('floor','solid')],np.int32)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    records=[]
    def predict(box):
        x0,y0,x1,y1=box
        inside=(points[:,0]>=x0)&(points[:,0]<x1)&(points[:,1]>=y0)&(points[:,1]<y1)
        xy=points[inside]-[x0,y0];truth=targets[inside]
        if len(np.unique(truth))<2:return None
        t=time.perf_counter();predictor.set_image(cv2.cvtColor(im[y0:y1,x0:x1],cv2.COLOR_BGR2RGB))
        masks,quality,_=predictor.predict(point_coords=xy,point_labels=truth,multimask_output=True)
        values=masks[:,xy[:,1].astype(int),xy[:,0].astype(int)]
        agreement=(values==truth).mean(axis=1)
        # Seed score is primary; model's own predicted IoU breaks exact ties.
        best=max(range(len(masks)),key=lambda j:(agreement[j],quality[j]))
        records.append({'box':box,'seeds':int(len(truth)),'seed_agreements':agreement.tolist(),'predicted_iou':quality.tolist(),'selected':best,'seconds':time.perf_counter()-t})
        return masks[best].astype(np.float32)
    with torch.inference_mode():
        full=predict((0,0,w,h));assert full is not None
        cv2.imwrite(str(out/'whole-mask.png'),(full*255).astype(np.uint8))
        accum=full.copy();count=np.ones((h,w),np.float32)
        # 20% overlap; each crop enlarges narrow structures in encoder coordinates.
        cw,ch=int(w*.6),int(h*.6)
        for y in (0,h-ch):
            for x in (0,w-cw):
                crop=predict((x,y,x+cw,y+ch))
                if crop is not None:accum[y:y+ch,x:x+cw]+=crop;count[y:y+ch,x:x+cw]+=1
    mask=(accum/count>=.5).astype(np.uint8)
    inference_seconds=time.perf_counter()-start
    segment_counts={}
    for variant, export_mask, export_out in [('tiled', mask, out), ('whole', full.astype(np.uint8), Path(str(out)+'-whole'))]:
        export_out.mkdir(parents=True,exist_ok=True)
        # Deterministic quarter-resolution export, with all islands/holes retained.
        small=cv2.resize(export_mask,(w//4,h//4),interpolation=cv2.INTER_NEAREST)
        contours,_=cv2.findContours(small,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        overlay=im.copy();walls=[]
        for c in contours:
            p=cv2.approxPolyDP(c,.75,True).reshape(-1,2)*4
            if len(p)<3:continue
            for a,b in zip(p,np.roll(p,-1,axis=0)):
                if any(a[j]==b[j] and a[j] in (0,(small.shape[1-j]-1)*4) for j in (0,1)):continue
                walls.append([int(a[0]),int(a[1]),int(b[0]),int(b[1])]);cv2.line(overlay,tuple(a),tuple(b),(0,0,255),3)
        cv2.imwrite(str(export_out/'mask.png'),small*255)
        cv2.imwrite(str(export_out/'overlay.jpg'),cv2.resize(overlay,(w//4,h//4)))
        (export_out/'walls.json').write_text(json.dumps({'walls':walls}))
        segment_counts[variant]=len(walls)
    agreement=float((mask[points[:,1].astype(int),points[:,0].astype(int)]==targets).mean())
    report={'image':samples['image'],'reference_read':False,'inference_inputs':['image','image-only semantic seeds','pretrained MobileSAM checkpoint'],'checkpoint_sha256':hashlib.sha256(Path(args.checkpoint).read_bytes()).hexdigest(),'license':'Apache-2.0','official_source':'https://github.com/ChaoningZhang/MobileSAM','repo_commit':args.commit,'torch':torch.__version__,'device':'cpu','seconds_model_load_and_inference':inference_seconds,'segments':segment_counts['tiled'],'segments_by_variant':segment_counts,'seed_agreement':agreement,'known_seeds':len(points),'floor_fraction':float(mask.mean()),'strategy':'whole + four 60%-size overlapping crops; majority mask; candidate chosen by seed agreement then model IoU','predictions':records,'warning':'Seed agreement is prompt consistency, not held-out accuracy. Open internal cliff lines cannot be represented by binary regions.'}
    (out/'inference.json').write_text(json.dumps(report,indent=2))
    whole_report={**report,'strategy':'whole-image multimask selected using semantic seed consistency','segments':segment_counts['whole'],'seed_agreement':float((full[points[:,1].astype(int),points[:,0].astype(int)]==targets).mean()),'floor_fraction':float(full.mean())}
    (Path(str(out)+'-whole')/'inference.json').write_text(json.dumps(whole_report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='predictions'}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('repo','checkpoint','samples','labels','out','commit'):p.add_argument('--'+name,required=True)
    run(p.parse_args())
