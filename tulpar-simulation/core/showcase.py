"""Visible walkthrough of report scenarios; it does not create trial results."""

class Showcase:
    def __init__(self, controller):
        self.c = controller
        self.stage = -1
        self.since = 0.0
        self.recording = False
        self.pending_capture = None
        self.motion_ended_at = None
        self.title = 'READY  |  Press B to start the walkthrough'
        self.detail = 'Four report scenarios + tabletop greeting + expression preview'

    def reset_floor(self):
        c = self.c
        c.tracks(0, 0)
        c.action = None
        c.target = None
        c.pending_stop_time = None
        c.pending_movement_response_start = None
        c.mode = 'floor'
        c.translation_field.setSFVec3f([-1.7, -1.1, 0.07])
        c.rotation_field.setSFRotation([0, 0, 1, 0])
        c.self_node.resetPhysics()
        c.set_camera_view('side')

    def start(self, record=False):
        if self.c.trial_recorder.current is not None:
            self.c.say('Finish the active trial before starting the walkthrough.')
            return
        self.reset_floor()
        self.c.emergency_stop = False
        self.c.range_fault_injected = False
        self.stage = 0
        self.since = self.c.robot.getTime()
        self.title = '01 / 04   APPROACH THE OPERATOR'
        self.detail = 'Scripted command: Come to me.  |  Watch speech, face and drive.'
        self.c.set_emotion('neutral')
        if record and not self.recording:
            from pathlib import Path
            destination = Path(__file__).resolve().parents[1] / 'outputs'
            destination.mkdir(exist_ok=True)
            self.c.robot.movieStartRecording(str(destination / 'TULPAR-walkthrough.mp4'), 1280, 720, 0, 90, 1, False)
            self.recording = True

    def advance(self, stage, title, detail):
        self.stage, self.title, self.detail = stage, title, detail
        self.since = self.c.robot.getTime()
        self.pending_capture = ('showcase_' + str(stage), self.since + 0.35)
        self.motion_ended_at = None

    def update(self):
        c = self.c
        t = c.robot.getTime() - self.since
        if self.pending_capture and c.robot.getTime() >= self.pending_capture[1]:
            c.capture_scene(self.pending_capture[0])
            self.pending_capture = None
        if self.stage in (1, 3) and c.action is None and self.motion_ended_at is None:
            self.motion_ended_at = c.robot.getTime()
        settled = self.motion_ended_at is not None and c.robot.getTime() - self.motion_ended_at > 2
        if self.stage == 0 and t > 2:
            c.dispatch_spoken_text('come to me')
            self.advance(1, self.title, self.detail)
        elif self.stage == 1 and ((t > 3 and settled) or t > 45):
            if c.action is not None:
                c.stop('demo_timeout')
            self.advance(2, '02 / 04   OPERATOR-INDICATED TARGET', 'Reset between scenarios. Amber = target A; purple = target B.')
            self.reset_floor()
            c.set_simulated_pointing_target('target-A')
        elif self.stage == 2 and t > 2.5:
            c.dispatch_spoken_text('go to marker')
            self.advance(3, self.title, 'Scripted command: Go to marker.  |  Select A, turn, approach.')
        elif self.stage == 3 and ((t > 3 and settled) or t > 50):
            if c.action is not None:
                c.stop('demo_timeout')
            self.reset_floor()
            self.advance(4, '03 / 04   STOP WHILE MOVING', 'First start movement; then send the stop command.')
        elif self.stage == 4 and t > 2:
            c.dispatch_spoken_text('come to me')
            self.advance(5, self.title, 'Moving now. The stop command follows in four seconds.')
        elif self.stage == 5 and t > 4:
            c.dispatch_spoken_text('stop')
            self.advance(6, self.title, 'STOP received. Wheel sensors determine when rotation ceases.')
        elif self.stage == 6 and t > 3:
            c.set_camera_view('robot')
            c.dispatch_spoken_text('say hello')
            self.advance(7, '04 / 04   GREETING ON THE FLOOR', 'Voice + happy face + non-contact arm wave. Tracks stay stopped.')
        elif self.stage == 7 and t > 5:
            c.command('mode')
            self.advance(8, '04 / 04   GREETING ON THE TABLE', 'Placement change between trials. Same robot; drive inhibited.')
        elif self.stage == 8 and t > 2:
            c.dispatch_spoken_text('say hello')
            self.advance(9, self.title, 'Voice + animated face + arm wave; stationary tabletop support.')
        elif self.stage == 9 and t > 5:
            c.set_emotion('surprised')
            c.say('Oh! That is surprising.')
            self.advance(10, 'EXPRESSION PREVIEW', 'Additional visual demonstration; separate from the 40-trial protocol.')
        elif self.stage == 10 and t > 3.5:
            c.set_emotion('sad')
            c.say('I am sorry to hear that.')
            self.advance(11, self.title, 'Sad expression and lowered arm pose.')
        elif self.stage == 11 and t > 3.5:
            c.set_emotion('happy')
            c.say('Thank you for watching. I am ready to talk.')
            self.advance(12, 'WALKTHROUGH COMPLETE', 'B replay   |   C camera   |   T placement   |   G greeting')
        elif self.stage == 12 and t > 4:
            self.stage = -1
            c.log('showcase', 'completed')
            if self.recording:
                c.robot.movieStopRecording()
                self.recording = False
            import os
            if os.environ.get('TULPAR_DEMO_EXIT') == '1':
                c.robot.simulationQuit(0)

    def overlay(self):
        c = self.c
        labels = [
            (0, 'T U L P A R   /   MULTIMODAL ROBOT', .025, .025, .085, 0x80E6EF),
            (1, self.title, .025, .095, .075, 0xFFFFFF),
            (2, self.detail, .025, .145, .055, 0xBBD0DE),
            (3, 'TULPAR: ' + getattr(c, 'last_utterance', ''), .025, .83, .07, 0xFFFFFF),
            (4, f'{c.mode.upper()}  |  {c.emotion.upper()}  |  {c.action or "stationary"}  |  t = {c.robot.getTime():.1f} s', .025, .895, .055, 0x80E6EF),
            (5, 'B replay   R record   C view   1 approach   3 point A   2 target   S stop   G wave   T table/floor', .025, .95, .045, 0xBBD0DE),
            (6, 'SIMULATION  /  Scripted inputs in walkthrough; no trial results generated', .025, .195, .04, 0xE5BA79),
        ]
        for args in labels:
            c.robot.setLabel(*args, 0.0, 'Arial')
