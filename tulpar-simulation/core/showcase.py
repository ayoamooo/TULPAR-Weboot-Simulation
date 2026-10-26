"""Visible walkthrough of report scenarios; it does not create trial results."""

import os
from pathlib import Path

class Showcase:
    def __init__(self, controller):
        self.c = controller
        self.stage = -1
        self.since = 0.0
        self.recording = False
        self.animation_recording = False
        self.animation_capture_enabled = os.environ.get('TULPAR_RECORD_WEB_ANIMATION', '1') != '0'
        self.movie_waiting = False
        self.movie_started_at = None
        self.movie_stopped_at = None
        self.movie_staging = None
        self.movie_destination = None
        self.animation_destination = None
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
            destination = Path(__file__).resolve().parents[1] / 'outputs'
            destination.mkdir(exist_ok=True)
            self.movie_destination = destination / 'TULPAR-walkthrough.mp4'
            self.movie_staging = destination / 'TULPAR-walkthrough.pending.mp4'
            self.movie_staging.unlink(missing_ok=True)
            if not self.c.robot.movieIsReady():
                self.c.log('showcase_video', 'start_rejected', reason='movie_encoder_busy')
                return
            self.c.robot.movieStartRecording(str(self.movie_staging), 1280, 720, 0, 90, 1, False)
            self.recording = True
            self.movie_started_at = self.c.robot.getTime()
            self.c.log('showcase_video', 'recording_started', path=str(self.movie_staging))
            if self.animation_capture_enabled:
                self.animation_destination = destination / 'TULPAR-walkthrough-interactive.html'
                animation_started = self.c.robot.animationStartRecording(str(self.animation_destination))
                self.animation_recording = bool(animation_started)
                self.c.log(
                    'showcase_animation',
                    'recording_started' if self.animation_recording else 'start_rejected',
                    path=str(self.animation_destination),
                )

    def advance(self, stage, title, detail):
        self.stage, self.title, self.detail = stage, title, detail
        self.since = self.c.robot.getTime()
        self.pending_capture = ('showcase_' + str(stage), self.since + 0.35)
        self.motion_ended_at = None

    def update(self):
        c = self.c
        if self.movie_waiting:
            if c.robot.movieIsReady():
                failed = c.robot.movieFailed()
                size = self.movie_staging.stat().st_size if self.movie_staging.exists() else 0
                if not failed and size > 1_000_000:
                    os.replace(self.movie_staging, self.movie_destination)
                    c.log(
                        'showcase_video', 'recording_completed',
                        path=str(self.movie_destination), bytes=size,
                        duration_s=round(c.robot.getTime() - self.movie_started_at, 2),
                    )
                else:
                    c.log(
                        'showcase_video', 'recording_failed',
                        encoder_failed=failed, bytes=size,
                    )
                self.movie_waiting = False
                if os.environ.get('TULPAR_DEMO_EXIT') == '1':
                    c.robot.simulationQuit(0)
            elif c.robot.getTime() - self.movie_stopped_at > 90:
                c.log('showcase_video', 'encoding_timeout', timeout_s=90)
                self.movie_waiting = False
                if os.environ.get('TULPAR_DEMO_EXIT') == '1':
                    c.robot.simulationQuit(1)
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
            # The robot-follow view is useful while it moves on the floor, but
            # becomes a poor movie composition after relocating it onto the
            # tabletop support. Return to the wide side view for the stationary
            # greeting and emotion sequence so the robot and set stay visible.
            c.set_camera_view('side')
            self.advance(8, '04 / 04   GREETING ON THE TABLE', 'Placement change between trials. Same robot; drive inhibited.')
        elif self.stage == 8 and t > 2:
            c.dispatch_spoken_text('say hello')
            self.advance(9, self.title, 'Voice + animated face + arm wave; stationary tabletop support.')
        elif self.stage == 9 and t > 5:
            c.set_emotion('surprised')
            c.say('Oh! That is surprising.')
            self.advance(10, 'EMOTION PREVIEW  /  SURPRISED', 'Face and arm pose change together; tracks remain disabled.')
        elif self.stage == 10 and t > 2.5:
            c.set_emotion('sad')
            c.say('I am sorry to hear that.')
            self.advance(11, 'EMOTION PREVIEW  /  SAD', 'Face and arm pose change together; tracks remain disabled.')
        elif self.stage == 11 and t > 2.5:
            c.set_emotion('angry')
            c.say('That sounds frustrating.')
            self.advance(12, 'EMOTION PREVIEW  /  ANGRY', 'Face and arm pose change together; tracks remain disabled.')
        elif self.stage == 12 and t > 2.5:
            c.set_emotion('sleepy')
            c.say('I am getting sleepy.')
            self.advance(13, 'EMOTION PREVIEW  /  SLEEPY', 'Face and arm pose change together; tracks remain disabled.')
        elif self.stage == 13 and t > 2.5:
            c.set_emotion('wink')
            c.say('Here is a quick wink.')
            self.advance(14, 'EMOTION PREVIEW  /  WINK', 'Animated eye and arm pose; tracks remain disabled.')
        elif self.stage == 14 and t > 2.5:
            c.set_emotion('love')
            c.say('That is very kind.')
            self.advance(15, 'EMOTION PREVIEW  /  AFFECTION', 'Face and arm pose change together; tracks remain disabled.')
        elif self.stage == 15 and t > 2.5:
            c.set_emotion('thinking')
            c.say('Let me think about that.')
            self.advance(16, 'EMOTION PREVIEW  /  THINKING', 'Face and arm pose change together; tracks remain disabled.')
        elif self.stage == 16 and t > 2.5:
            c.set_emotion('happy')
            c.say('Thank you for watching. I am ready to talk.')
            self.advance(17, 'EMOTION PREVIEW  /  HAPPY', 'Coordinated face and arm pose; tracks remain disabled.')
        elif self.stage == 17 and t > 3:
            self.stage = -1
            self.title = 'WALKTHROUGH COMPLETE'
            self.detail = 'B replay   |   C camera   |   T placement   |   G greeting'
            c.log('showcase', 'completed')
            if self.recording:
                c.robot.movieStopRecording()
                self.recording = False
                self.movie_waiting = True
                self.movie_stopped_at = c.robot.getTime()
                c.log('showcase_video', 'encoding_started')
            if self.animation_recording:
                completed = c.robot.animationStopRecording()
                html_exists = self.animation_destination.exists()
                companions = [
                    path for path in self.animation_destination.parent.glob(
                        self.animation_destination.stem + '.*'
                    ) if path.is_file()
                ]
                size = sum(path.stat().st_size for path in companions)
                c.log(
                    'showcase_animation',
                    'recording_completed' if completed and html_exists and size > 0 else 'recording_failed',
                    path=str(self.animation_destination),
                    exported=completed,
                    html_exists=html_exists,
                    companion_files=len(companions),
                    total_bytes=size,
                )
                self.animation_recording = False
            elif os.environ.get('TULPAR_DEMO_EXIT') == '1':
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
