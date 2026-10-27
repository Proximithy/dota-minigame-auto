import unittest
from auto_launch import AutoLaunch, double_space


class LaunchTests(unittest.TestCase):
    def sample(self,guard,t,x=190,y=380,valid=True,enabled=True):
        return guard.update(t,valid,(x,y,30,30),(160,420,90,22),enabled)

    def test_wait_then_exactly_one_request(self):
        guard=AutoLaunch()
        events=[self.sample(guard,i*.05) for i in range(150)]
        self.assertEqual(sum(events),1)
        self.assertGreaterEqual(events.index(True)*.05,2)

    def test_normal_moving_ball_never_launches(self):
        guard=AutoLaunch()
        events=[self.sample(guard,i*.04,190+(i%30)*3) for i in range(200)]
        self.assertFalse(any(events))

    def test_ball_attached_to_moving_cart_is_launch_ready(self):
        guard=AutoLaunch()
        events=[guard.update(i*.05,True,(190+i,380,30,30),(160+i,420,90,22)) for i in range(100)]
        self.assertEqual(sum(events),1)

    def test_loss_pause_and_observation_do_not_launch(self):
        for disabled in ('valid','enabled'):
            guard=AutoLaunch()
            for i in range(100):
                options={disabled:False} if i%12==0 else {}
                self.assertFalse(self.sample(guard,i*.05,**options))
        guard=AutoLaunch()
        self.assertFalse(any(self.sample(guard,i*.05,enabled=False) for i in range(100)))

    def test_stationary_away_from_cart_does_not_launch(self):
        guard=AutoLaunch()
        self.assertFalse(any(self.sample(guard,i*.05,y=100) for i in range(100)))

    def test_focus_loss_does_not_repeat_and_movement_rearms(self):
        guard=AutoLaunch()
        self.assertEqual(sum(self.sample(guard,i*.05) for i in range(60)),1)
        guard.reset_observation()
        self.assertFalse(any(self.sample(guard,4+i*.05) for i in range(60)))
        for i in range(10):self.sample(guard,8+i*.05,x=250,y=200)
        self.assertEqual(sum(self.sample(guard,9+i*.05) for i in range(60)),1)

    def test_sparse_frames_cannot_accumulate_stationary_time(self):
        guard=AutoLaunch()
        self.assertFalse(any(self.sample(guard,i*.5) for i in range(20)))

    def test_double_press_order_and_focus_cancel_release(self):
        clock=[0.];events=[]
        def wait(dt):clock[0]+=dt
        def down():events.append(('down',clock[0]))
        def up():events.append(('up',clock[0]))
        self.assertTrue(double_space(down,up,lambda:True,wait,lambda:clock[0]))
        self.assertEqual([v[0] for v in events],['down','up','down','up'])
        self.assertGreaterEqual(events[2][1]-events[1][1],.19)
        clock[0]=0;events.clear()
        self.assertFalse(double_space(down,up,lambda:clock[0]<.03,wait,lambda:clock[0]))
        self.assertEqual([v[0] for v in events],['down','up'])


if __name__=='__main__':unittest.main()
