"""Recover a cart from its narrow red roof when the animated template fails."""
import cv2
import numpy as np


def red_mask(image):
    hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    return np.uint8(((hsv[:,:,0]<13)|(hsv[:,:,0]>170))&(hsv[:,:,1]>120)&(hsv[:,:,2]>75))*255


class PaddleBand:
    def __init__(self,paddle):
        self.height,self.width=paddle.shape[:2]
        self.kernel=np.ones((3,max(9,int(self.width*.22))),np.uint8)
        self.reference=None
        mask=red_mask(paddle[:max(12,int(self.height*.35))])
        if mask.sum(axis=1).max()/255<self.width*.30:return
        peak=int(mask.sum(axis=1).argmax());start=max(0,peak-4)
        band=cv2.morphologyEx(mask[start:peak+5],cv2.MORPH_CLOSE,self.kernel)
        count,labels,stats,_=cv2.connectedComponentsWithStats(band)
        choices=[(i,stats[i]) for i in range(1,count) if stats[i,2]>self.width*.5]
        if not choices:return
        i,(x,y,w,h,_) = max(choices,key=lambda v:v[1][4])
        self.reference=band[y:y+h,x:x+w]>0
        self.offset_y=start+y+h/2
        self.expected_width=int(w)

    def match(self,frame,paddle_y):
        if self.reference is None:return None
        top=max(0,paddle_y-12);bottom=min(frame.shape[0],paddle_y+int(self.height*.35)+12)
        mask=red_mask(frame[top:bottom])
        rows=mask.sum(axis=1)
        if not len(rows) or rows.max()/255<self.width*.30:return None
        peak=int(rows.argmax());start=max(0,peak-4)
        band=cv2.morphologyEx(mask[start:peak+5],cv2.MORPH_CLOSE,self.kernel)
        count,labels,stats,_=cv2.connectedComponentsWithStats(band)
        best=None
        rh,rw=self.reference.shape
        for i in range(1,count):
            x,y,w,h,area=map(int,stats[i])
            if not self.expected_width*.75<=w<=self.expected_width*1.25 or h<3:continue
            candidate=cv2.resize(np.uint8(labels[y:y+h,x:x+w]==i),(rw,rh),interpolation=cv2.INTER_NEAREST)>0
            score=float(np.count_nonzero(candidate&self.reference)/max(1,np.count_nonzero(candidate|self.reference)))
            if best is None or score>best[0]:
                full_top=top+start+y+h/2-self.offset_y
                best=(score,x+w/2,full_top)
        return best
