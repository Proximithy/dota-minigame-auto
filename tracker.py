import cv2
import numpy as np
from physics import intercept, direction
from paddle_band import PaddleBand


def largest_component(mask):
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if count < 2:
        return mask
    chosen = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.uint8(labels == chosen)*255


class Tracker:
    def __init__(self, config, ball, paddle):
        self.config = config
        self.h, self.w = ball.shape[:2]
        self.paddle_full_shape = paddle.shape[:2]
        self.band_detector=PaddleBand(paddle)
        self.paddle_offset = 0
        self.paddle = paddle.copy()
        # Use the stable red roof instead of the animated cart body.
        hsv = cv2.cvtColor(paddle, cv2.COLOR_BGR2HSV)
        red = ((hsv[:, :, 0] < 13) | (hsv[:, :, 0] > 170)) & (hsv[:, :, 1] > 120) & (hsv[:, :, 2] > 75)
        rows = np.sum(red, axis=1)
        if rows.max() >= paddle.shape[1]*.4:
            peak = int(np.argmax(rows))
            top = bottom = peak
            while top > 0 and rows[top-1] > rows[peak]*.45:
                top -= 1
            while bottom+1 < len(rows) and rows[bottom+1] > rows[peak]*.45:
                bottom += 1
            if bottom-top >= 3:
                top, bottom = max(0, top-2), min(len(rows), bottom+3)
                self.paddle = paddle[top:bottom].copy()
                self.paddle_offset = top
        hsv = cv2.cvtColor(ball, cv2.COLOR_BGR2HSV)
        warm = np.uint8((hsv[:, :, 0] < 50) & (hsv[:, :, 1] > 40) & (hsv[:, :, 2] > 35))*255
        mask = largest_component(warm)
        self.warm_ball = np.count_nonzero(mask) >= ball.shape[0]*ball.shape[1]*.12
        color_mask = np.uint8((hsv[:, :, 0] < 40) & (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 40))*255
        self.color_area = max(1, np.count_nonzero(color_mask))
        self.color_histogram = self.histogram(hsv, color_mask)
        if np.count_nonzero(mask) < ball.shape[0]*ball.shape[1]*.12:
            edge = np.concatenate((ball[0], ball[-1], ball[:, 0], ball[:, -1]))
            background = np.median(edge, axis=0)
            mask = largest_component(np.uint8(np.linalg.norm(ball.astype(float)-background, axis=2) > 28)*255)
        if np.count_nonzero(mask) < 12:
            mask = np.full(ball.shape[:2], 255, np.uint8)
        size = int(np.ceil(np.hypot(self.h, self.w)))+4
        canvas = np.zeros((size, size, 3), np.uint8)
        alpha = np.zeros((size, size), np.uint8)
        y, x = (size-self.h)//2, (size-self.w)//2
        canvas[y:y+self.h, x:x+self.w] = ball
        alpha[y:y+self.h, x:x+self.w] = mask
        self.variants = []
        for angle in range(0, 360, 30):
            matrix = cv2.getRotationMatrix2D((size/2, size/2), angle, 1)
            rotated = cv2.warpAffine(canvas, matrix, (size, size))
            rotated_mask = cv2.warpAffine(alpha, matrix, (size, size), flags=cv2.INTER_NEAREST)
            rx, ry, rw, rh = cv2.boundingRect(rotated_mask)
            self.variants.append((cv2.cvtColor(rotated[ry:ry+rh, rx:rx+rw], cv2.COLOR_BGR2GRAY), rotated_mask[ry:ry+rh, rx:rx+rw].copy()))
        self.ball_box = self.paddle_box = None
        self.paddle_method='template'
        self.tracking_reason='acquiring'
        self.last_target=None
        self.last_command=0
        self.excluded_paddle = None
        self.reset_motion()
        if min(self.paddle.shape[:2]) < 4 or np.std(self.paddle) < 2 or np.std(ball) < 2:
            raise ValueError('Recorte sem detalhe. Marque novamente a bola e a raquete.')

    def reset_motion(self):
        self.previous = self.last_ball = self.last_frame = self.last_time = None
        self.velocity = (0, 0)

    @staticmethod
    def histogram(hsv, mask):
        histogram = cv2.calcHist([hsv], [0, 1, 2], mask, [6, 2, 4], [0, 180, 0, 256, 0, 256])
        return cv2.normalize(histogram, None, 1, 0, cv2.NORM_L1)

    def find_colored_boot(self, frame, bounds, motion):
        """Color distribution survives the boot's different animation poses."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = np.uint8((hsv[:, :, 0] < 40) & (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 40))*255
        joined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(joined)
        best = (-1., 0., 0., 0, 0)
        left, top, right, bottom = bounds
        for i in range(1, count):
            x, y, w, h, area = map(int, stats[i])
            cx, cy = x+w/2, y+h/2
            if not (left <= cx <= right and top <= cy <= bottom):
                continue
            if min(w, h) < max(4, min(self.w, self.h)*.20) or max(w, h) > np.hypot(self.w, self.h)*1.3:
                continue
            if not self.color_area*.30 <= area <= self.color_area*2.8:
                continue
            if self.excluded_paddle is not None:
                ex, ey, ew, eh = self.excluded_paddle
                if ex-4 <= cx <= ex+ew+4 and ey-4 <= cy <= ey+eh+4:
                    continue
            if motion is not None and motion[min(int(cy), frame.shape[0]-1), min(int(cx), frame.shape[1]-1)] <= .025:
                if self.last_ball is None or np.hypot(cx-self.last_ball[0], cy-self.last_ball[1]) > max(self.w, self.h):
                    continue
            component_mask = np.uint8(labels[y:y+h, x:x+w] == i)*mask[y:y+h, x:x+w]
            score = 1-cv2.compareHist(self.color_histogram, self.histogram(hsv[y:y+h, x:x+w], component_mask), cv2.HISTCMP_BHATTACHARYYA)
            if score >= .78 and score > best[0]:
                best = score, cx, cy, w, h
        return best

    @staticmethod
    def match(frame, template):
        if any(a < b for a, b in zip(frame.shape[:2], template.shape[:2])):
            raise ValueError('O recorte não cabe na arena. Refaça a calibração.')
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, (x, y) = cv2.minMaxLoc(result)
        return score, x+template.shape[1]/2, y+template.shape[0]/2

    def find_ball(self, frame, now):
        height, width = frame.shape[:2]
        left, top, right, bottom = 0, 0, width, height
        if self.last_ball is not None and now-self.last_ball[2] < .30:
            x, y, then = self.last_ball
            dt = now-then
            vx, vy = self.velocity
            radius = max(45, self.w*2, self.h*2, np.hypot(vx, vy)*dt*1.5+25)
            cx, cy = x+vx*dt, y+vy*dt
            cx, cy = np.clip(cx, 0, width), np.clip(cy, 0, height)
            left, top = max(0, int(cx-radius)), max(0, int(cy-radius))
            right, bottom = min(width, int(cx+radius)), min(height, int(cy+radius))
        view = cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2GRAY)
        scale = .5 if view.shape[1] > 300 and min(self.h, self.w) >= 24 and not self.config.get('full_resolution', False) else 1.
        if scale != 1:
            view = cv2.resize(view, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        warm_view = None
        if self.warm_ball:
            hsv = cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2HSV)
            warm_view = ((hsv[:, :, 0] < 50) & (hsv[:, :, 1] > 40) & (hsv[:, :, 2] > 45)).astype(np.float32)
            if scale != 1:
                warm_view = cv2.resize(warm_view, (view.shape[1], view.shape[0]), interpolation=cv2.INTER_AREA)
        motion = None
        if self.last_frame is not None and self.last_time is not None and 0 < now-self.last_time < .20:
            diff = cv2.absdiff(frame, self.last_frame)
            moving = np.uint8(np.max(diff, axis=2) > 18)
            motion = cv2.boxFilter(moving.astype(np.float32), -1, (max(5, self.w), max(5, self.h)))
        if self.warm_ball:
            return self.find_colored_boot(frame, (left, top, right, bottom), motion)
        best = (-1., 0., 0., 0, 0)
        for original, original_mask in self.variants:
            template, mask = original, original_mask
            if scale != 1:
                template = cv2.resize(original, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                mask = cv2.resize(original_mask, (template.shape[1], template.shape[0]), interpolation=cv2.INTER_NEAREST)
            th, tw = template.shape[:2]
            if view.shape[0] < th or view.shape[1] < tw:
                continue
            scores = cv2.matchTemplate(view, template, cv2.TM_CCOEFF_NORMED, mask=mask)
            scores = np.clip(np.nan_to_num(scores, nan=-1, posinf=-1, neginf=-1), -1, 1)
            # Masked correlation is unstable over almost uniform dark scenery.
            # Require actual contrast and the boot's foreground color as well.
            values = view.astype(np.float32)
            mean = cv2.boxFilter(values, -1, (tw, th))
            variance = np.maximum(0, cv2.boxFilter(values*values, -1, (tw, th))-mean*mean)
            contrast = variance[th//2:th//2+scores.shape[0], tw//2:tw//2+scores.shape[1]]
            scores = np.where(contrast >= max(6., float(np.std(template[mask > 0]))*.20)**2, scores, -1.)
            if warm_view is not None:
                fraction = cv2.boxFilter(warm_view, -1, (tw, th))
                fraction = fraction[th//2:th//2+scores.shape[0], tw//2:tw//2+scores.shape[1]]
                scores = np.where(fraction >= .10, scores, -1.)
            if self.excluded_paddle is not None:
                ex, ey, ew, eh = self.excluded_paddle
                yy, xx = np.ogrid[:scores.shape[0], :scores.shape[1]]
                cx, cy = (xx+tw/2)/scale+left, (yy+th/2)/scale+top
                scores = np.where((cx >= ex) & (cx <= ex+ew) & (cy >= ey) & (cy <= ey+eh), -1., scores)
            if motion is not None:
                motion_view = motion[top:bottom, left:right]
                if scale != 1:
                    motion_view = cv2.resize(motion_view, (view.shape[1], view.shape[0]), interpolation=cv2.INTER_AREA)
                moving = motion_view[th//2:th//2+scores.shape[0], tw//2:tw//2+scores.shape[1]] > .025
                if self.last_ball is not None:
                    yy, xx = np.ogrid[:scores.shape[0], :scores.shape[1]]
                    close = ((xx+tw/2)/scale+left-self.last_ball[0])**2+((yy+th/2)/scale+top-self.last_ball[1])**2 < max(self.w, self.h)**2
                    moving |= close
                scores = np.where(moving, scores, -1.)
            _, score, _, (x, y) = cv2.minMaxLoc(scores)
            if score > best[0]:
                best = score, (x+tw/2)/scale+left, (y+th/2)/scale+top, tw/scale, th/scale
        return best

    def step(self, frame, now):
        c = self.config
        expected_y = c['paddle_y']+self.paddle_offset
        margin = max(10, self.paddle.shape[0]//2)
        top = max(0, expected_y-margin)
        bottom = min(frame.shape[0], expected_y+self.paddle.shape[0]+margin)
        ps, px, py_core = self.match(frame[top:bottom], self.paddle)
        py_core += top
        self.paddle_method='template'
        # Keep the working template path unchanged. Recover only rejected carts.
        if ps < c['threshold_paddle']:
            recovered=self.band_detector.match(frame,c['paddle_y'])
            if recovered is not None and recovered[0]>=c['threshold_paddle']:
                ps,px,full_top=recovered
                py_core=full_top+self.paddle_offset+self.paddle.shape[0]/2
                self.paddle_method='red-band'
        paddle_top = py_core-self.paddle.shape[0]/2-self.paddle_offset
        py = paddle_top+self.paddle_full_shape[0]/2
        # The boot can be beside/below the red roof. Search the whole arena,
        # excluding the actual cart, rather than cutting away its entire row.
        self.excluded_paddle = (px-self.paddle_full_shape[1]/2, paddle_top,
                                self.paddle_full_shape[1], self.paddle_full_shape[0])
        playfield = frame
        if self.last_frame is not None and self.last_frame.shape != playfield.shape:
            self.last_frame = None
        bs, bx, by, bw, bh = self.find_ball(playfield, now)
        valid = ps >= c['threshold_paddle'] and bs >= max(.67, c['threshold_ball'])
        self.tracking_reason=('paddle-lost' if ps<c['threshold_paddle'] else
                              'boot-lost' if bs<max(.67,c['threshold_ball']) else 'acquiring-velocity')
        vx = vy = 0
        ready = False
        if valid and self.previous:
            ox, oy, ot = self.previous
            dt = now-ot
            if 0 < dt < .20:
                vx, vy = (bx-ox)/dt, (by-oy)/dt
                valid = abs(vx) < frame.shape[1]*5 and abs(vy) < frame.shape[0]*5
                ready = valid
                self.tracking_reason='tracking' if valid else 'jump-rejected'
        target = intercept(bx, by, vx, vy, paddle_top-self.h/2,
                           self.w/2, frame.shape[1]-self.w/2)
        command = direction(target, px, c['deadzone']) if valid and ready else 0
        self.last_target=target
        self.last_command=command
        self.previous = (bx, by, now) if valid else None
        if valid:
            self.last_ball = (bx, by, now)
            if ready:
                self.velocity = (vx, vy)
        self.last_frame = playfield.copy()
        self.last_time = now
        self.ball_box = (bx-bw/2, by-bh/2, bw, bh)
        self.paddle_box = (px-self.paddle.shape[1]/2, py_core-self.paddle.shape[0]/2, self.paddle.shape[1], self.paddle.shape[0])
        preview = frame.copy()
        for box, okay in [(self.ball_box, bs >= max(.67, c['threshold_ball'])), (self.paddle_box, ps >= c['threshold_paddle'])]:
            x, y, w, h = map(int, box)
            cv2.rectangle(preview, (x, y), (x+w, y+h), (80, 210, 100) if okay else (50, 80, 240), 2)
        cv2.circle(preview, (int(target), int(py)), 6, (255, 180, 40), 2)
        return preview, command, valid, bs, ps
