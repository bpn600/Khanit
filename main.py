from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
from khanit_db import KhanitDatabase
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivy.metrics import dp, sp
from kivy.uix.label import Label
from kivy.core.text import LabelBase
from kivy.utils import platform
from kivy.uix.accordion import Accordion
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget
import webbrowser
from urllib.parse import quote
from random import randint, sample
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from random import randint
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.properties import (
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
    BooleanProperty,
    DictProperty,
)
from kivy.metrics import dp
from kivy.clock import Clock
from math import sqrt
from kivy.graphics import Ellipse, Line, Color
import os
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle
from kivy.properties import StringProperty
from kivy.core.image import Image as CoreImage
from safe_area import (
    SafeAreaManager,
    SafeAreaBoxLayout,
    safe_area,
)

FONT_PATH = os.path.join(
    os.path.dirname(__file__),
    "assets", "font", "CODE2000.TTF"
)
if os.path.exists(FONT_PATH):
    LabelBase.register(name="CODE2000", fn_regular=FONT_PATH)
else:
    print(f"CODE2000 font not found: {FONT_PATH}")


class LimbuTracePad(Widget):
    trace_background_color = ListProperty([1, 1, 1, 1])
    image_padding = NumericProperty(dp(12))
    image_padding = NumericProperty(dp(10))
    _background_texture = None
    background_image_rect = None
    line_color = ListProperty([0, 0, 0, 1])
    guide_color = ListProperty([0.35, 0.55, 0.90, 0.55])
    correct_color = ListProperty([0.15, 0.70, 0.30, 1])
    incorrect_color = ListProperty([0.85, 0.20, 0.20, 1])
    line_width = NumericProperty(dp(4))
    guide_width = NumericProperty(dp(3))
    current_number = NumericProperty(0)
    accuracy = NumericProperty(0)
    current_stroke = NumericProperty(0)
    total_strokes = NumericProperty(1)
    feedback = StringProperty("")
    feedback_color = ListProperty([0.1, 0.1, 0.1, 1])
    tracing_enabled = BooleanProperty(True)

    LIMBU_STROKE_COUNTS = {
        0: 1,  # ᥆
        1: 1,  # ᥇
        2: 2,  # ᥈
        3: 1,  # ᥉
        4: 2,  # ᥊
        5: 1,  # ᥋
        6: 1,  # ᥌
        7: 1,  # ᥍
        8: 2,  # ᥎
        9: 2,  # ᥏
    }

    background_image = StringProperty("assets/images/0.png")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.guide_paths = []
        self.guide_lines = []
        self.user_strokes = []
        self.current_points = []
        self.stroke_start_time = None
        self._guide_event = None
        self._guide_animation = None
        self._background_texture = None
        self.background_image_rect = None
        self.bind(
            pos=self._redraw_background,
            size=self._redraw_background,
            background_image=self._redraw_background,
            image_padding=self._redraw_background,
        )
        self._create_background()

    def _create_background(self):
        self.canvas.before.clear()
        self.background_image_rect = None
        with self.canvas.before:
            Color(*self.trace_background_color)
            self.background = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(15)]
            )
        try:
            image_path = self.background_image
            if not image_path:
                return
            if not os.path.exists(image_path):
                print(
                    f"Trace background image not found: "
                    f"{image_path}"
                )
                return
            self._background_texture = (
                CoreImage(
                    image_path,
                    keep_data=False
                ).texture
            )
            texture_width = (self._background_texture.width)
            texture_height = (self._background_texture.height)
            if texture_width <= 0 or texture_height <= 0:
                return
            padding = self.image_padding
            available_width = max(0, self.width - (padding * 2))
            available_height = max(0, self.height - (padding * 2))
            if (available_width <= 0 or available_height <= 0):
                return
            texture_ratio = (texture_width / texture_height)
            available_ratio = (available_width / available_height)
            if texture_ratio > available_ratio:
                image_width = available_width
                image_height = (image_width / texture_ratio)
            else:
                image_height = available_height
                image_width = (image_height * texture_ratio)
            image_x = (self.x + (self.width - image_width) / 2)
            image_y = (self.y + (self.height - image_height) / 2)
            with self.canvas.before:
                Color(1, 1, 1, 1)
                self.background_image_rect = Rectangle(texture=self._background_texture, pos=(image_x, image_y), size=(image_width, image_height))
        except Exception as e:
            self._background_texture = None
            self.background_image_rect = None
            print(f"Trace background image error: {e}")

    def _redraw_background(self, *args):
        try:
            self._create_background()
        except Exception as e:
            print(f"Trace background update error: {e}")

    def set_background_image(self, number):
        try:
            number = int(number)
            if number < 0:
                number = 0
            if number > 9:
                number = 9
            image_path = os.path.join(
                os.path.dirname(__file__),
                "assets",
                "images",
                f"{number}.png"
            )
            self.background_image = image_path
        except Exception as e:
            print(f"Background image selection error: {e}")

    def set_number(self, number):
        if number not in self.LIMBU_STROKE_COUNTS:
            number = 0
        self.current_number = number
        self.set_background_image(number)
        self._stop_guide_animation()
        self.total_strokes = self.LIMBU_STROKE_COUNTS[number]
        self.clear_all()
        self.guide_paths = []
        self.guide_lines = []
        self.current_stroke = 0
        self.accuracy = 0
        self.feedback = ""
        self._notify_trace_progress()

    def _stop_guide_animation(self):
        if self._guide_event is not None:
            try:
                self._guide_event.cancel()
            except Exception:
                pass
            self._guide_event = None
        self._guide_animation = None

    def draw_guides(self):
        self.canvas.after.clear()
        self.guide_lines = []

    def animate_guides(self):
        self._stop_guide_animation()
        self.canvas.after.clear()
        self.guide_lines = []

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if not self.tracing_enabled:
            return True
        self.current_points = [touch.pos]
        self.stroke_start_time = Clock.get_time()
        return True

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        if not self.current_points:
            return True
        self.current_points.append(touch.pos)
        if len(self.current_points) >= 2:
            p1 = self.current_points[-2]
            p2 = self.current_points[-1]
            with self.canvas:
                Color(*self.line_color)
                Line(points=[p1[0], p1[1], p2[0], p2[1]], width=self.line_width, cap="round")
        return True

    def on_touch_up(self, touch):
        if not self.current_points:
            return super().on_touch_up(touch)
        if len(self.current_points) < 3:
            self.current_points = []
            return True
        stroke = list(self.current_points)
        self.current_points = []
        self.user_strokes.append(stroke)
        completed_strokes = len(self.user_strokes)
        self.current_stroke = min(
            completed_strokes,
            self.total_strokes
        )
        accuracy = self.calculate_stroke_accuracy(stroke, self.current_stroke - 1)
        self.accuracy = accuracy
        self.update_feedback(accuracy)
        self._notify_trace_progress()
        return True

    def calculate_stroke_accuracy(
            self,
            user_points,
            stroke_index
    ):
        if not user_points:
            return 0
        return 100

    # DISTANCE
    @staticmethod
    def distance_to_segment(
        point,
        start,
        end
    ):
        px, py = point
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return sqrt(
                (px - x1) ** 2 +
                (py - y1) ** 2
            )
        t = (
            (px - x1) * dx +
            (py - y1) * dy
        ) / (
            dx * dx +
            dy * dy
        )
        t = max(
            0,
            min(1, t)
        )
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        return sqrt(
            (px - nearest_x) ** 2 +
            (py - nearest_y) ** 2
        )

    def update_feedback(self, accuracy):
        if accuracy >= 80:
            self.feedback = (f"✓ Excellent! {accuracy:.0f}%")
            self.feedback_color = (self.correct_color)
        elif accuracy >= 55:
            self.feedback = (f"✓ Good! {accuracy:.0f}%")
            self.feedback_color = (self.correct_color)
        else:
            self.feedback = (f"Try again • {accuracy:.0f}%")
            self.feedback_color = (self.incorrect_color)

    def clear_all(self):
        self._stop_guide_animation()
        self.canvas.clear()
        self._create_background()
        self.user_strokes = []
        self.current_points = []
        self.current_stroke = 0
        self.accuracy = 0
        self.feedback = ""
        Clock.schedule_once(lambda dt: self.draw_guides(), 0)

    def undo(self):
        if not self.user_strokes:
            return
        self.user_strokes.pop()
        self.current_stroke = min(
            len(self.user_strokes),
            self.total_strokes
        )
        self.redraw_user_strokes()
        self.accuracy = 0
        self.update_feedback(0)
        self.feedback = "↶ Last stroke removed"
        self._notify_trace_progress()

    def redraw_user_strokes(self):
        self._stop_guide_animation()
        self.canvas.clear()
        self._create_background()
        Clock.schedule_once(lambda dt: self.draw_guides(), 0)
        for stroke in self.user_strokes:
            if len(stroke) < 2:
                continue
            with self.canvas:
                Color(*self.line_color)
                points = []
                for x, y in stroke:
                    points.extend([
                        x, y
                    ])
                Line(points=points, width=self.line_width, cap='round', joint='round')

    def get_theme_background(self):
        app = MDApp.get_running_app()
        return app.theme_surface

    def _notify_trace_progress(self):
        parent = self.parent
        while parent is not None:
            if isinstance(parent, LimbuNumberTrace):
                parent.update_trace_progress()
                return
            parent = parent.parent


class LimbuNumberTrace(Screen):
    limbu_numbers = {
        0: '᥆',
        1: '᥇',
        2: '᥈',
        3: '᥉',
        4: '᥊',
        5: '᥋',
        6: '᥌',
        7: '᥍',
        8: '᥎',
        9: '᥏'
    }
    nepali_numbers = {
        0: '०',
        1: '१',
        2: '२',
        3: '३',
        4: '४',
        5: '५',
        6: '६',
        7: '७',
        8: '८',
        9: '९'
    }
    number_words = {
        0: '- ᤜᤥᤵ (hop)',
        1: '- ᤌᤡᤰ (thik)',
        2: '- ᤏᤧᤳᤇᤡ (netchhi)',
        3: '- ᤛᤢᤶᤛᤡ (sumsi)',
        4: '- ᤗᤡᤛᤡ (lisi)',
        5: '- ᤅᤠᤛᤡ (ngasi)',
        6: '- ᤋᤢᤰᤛᤡ (tuksi)',
        7: '- ᤏᤢᤛᤡ (nusi)',
        8: '- ᤕᤧᤳᤇᤡ (yetchhi)',
        9: '- ᤑᤠᤱᤛᤡ (fangsi)'
    }
    number_names = {
        0: "Hop (Zero)",
        1: "Thik (One)",
        2: "Netchhi (Two)",
        3: "Sumsi (Three)",
        4: "Lisi (Four)",
        5: "Ngasi (Five)",
        6: "Tuksi (Six)",
        7: "Nusi (Seven)",
        8: "Yetchhi (Eight)",
        9: "Fangsi (Nine)"
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_number = 0
        self.quiz_number = 0
        self.quiz_score = 0
        self.quiz_total = 0
        self.completed_numbers = set()
        self.audio_files = {
            0: "assets/audio/0.mp3",
            1: "assets/audio/1.mp3",
            2: "assets/audio/2.mp3",
            3: "assets/audio/3.mp3",
            4: "assets/audio/4.mp3",
            5: "assets/audio/5.mp3",
            6: "assets/audio/6.mp3",
            7: "assets/audio/7.mp3",
            8: "assets/audio/8.mp3",
            9: "assets/audio/9.mp3",
        }

    def close_screen(self, *args):
        if self.manager:
            self.manager.current = "help"

    def select_number(self, number):
        if number not in range(10):
            return
        self.current_number = number
        try:
            self.ids.trace_number.text = (self.limbu_numbers[number])
            self.ids.trace_number_english.text = (str(number))
            self.ids.trace_number_nepali.text = (self.nepali_numbers[number])
            self.ids.trace_word.text = (self.number_words[number])
        except Exception as e:
            print(f"Sirijanga display error: {e}")
        self.update_trace_progress()
        try:
            self.ids.show_number_sirijanga.text = (self.limbu_numbers[number])
            self.ids.num_name.text = (self.number_names[number])
            trace_pad = self.ids.trace_pad
            trace_pad.set_number(number)
            self.update_trace_progress()
        except Exception as e:
            print(f"Write tab update error: {e}")

    def next_number(self):
        self.current_number += 1
        if self.current_number > 9:
            self.current_number = 0
        self.select_number(self.current_number)

    def previous_number(self):
        self.current_number -= 1
        if self.current_number < 0:
            self.current_number = 9
        self.select_number(self.current_number)

    def prev_number(self):
        self.previous_number()

    def clear_trace(self):
        try:
            pad = self.ids.trace_pad
            pad.clear_all()
            pad.current_stroke = 0
            pad.accuracy = 0
            pad.feedback = ""
            self.update_trace_progress()
            self.ids.progress_bar.value = 0
        except Exception as e:
            print(f"Trace clear error: {e}")

    def undo_trace(self):
        try:
            self.ids.trace_pad.undo()
        except Exception as e:
            print(f"Undo error: {e}")

    def play_audio(self):
        try:
            from kivy.core.audio import SoundLoader
            import os
            path = self.audio_files.get(self.current_number)
            if not path:
                print("No audio configured.")
                return
            if not os.path.exists(path):
                print(f"Audio file not found: {path}")
                return
            sound = SoundLoader.load(path)
            if sound:
                sound.stop()
                sound.play()
        except Exception as e:
            print(f"Audio error: {e}")

    def on_write_tab(self):
        self.select_number(self.current_number)

    def on_enter(self, *args):
        Clock.schedule_once(lambda dt: self.select_number(self.current_number), 0.1)
        Clock.schedule_once(lambda dt: self.start_quiz(), 0.2)

    def update_trace_progress(self):
        try:
            pad = self.ids.trace_pad
            total = max(1, int(pad.total_strokes))
            completed = min(len(pad.user_strokes), total)
            pad.current_stroke = completed
            progress = (completed / total) * 100
            self.ids.progress_bar.value = progress
            self.ids.stroke_info.text = (f"Strokes: {completed}/{total}")
            if completed >= total:
                self.ids.progress_label.text = (f"Completed • {total}/{total}")
            else:
                self.ids.progress_label.text = (f"Stroke {completed}/{total}")
            if completed >= total:
                self.check_trace_completion()
        except Exception as e:
            print(f"Progress update error: {e}")

    def check_trace_completion(self):
        try:
            pad = self.ids.trace_pad
            completed = len(pad.user_strokes)
            total = max(1, pad.total_strokes)
            if completed < total:
                return
            if pad.accuracy >= 80:
                self.completed_numbers.add(self.current_number)
                self.ids.trace_feedback.text = (
                    f"✓ Number {self.current_number} "
                    f"completed!"
                )
                self.ids.progress_bar.value = 100
                self.ids.progress_label.text = (f"Completed • {total}/{total}")
            else:
                self.ids.trace_feedback.text = ("Try the number again")
        except Exception as e:
            print(f"Completion error: {e}")

    # QUIZ
    def start_quiz(self):
        self.quiz_score = 0
        self.quiz_total = 0
        self.ids.quiz_score_label.text = "Score: 0"
        self.next_quiz_question()

    def next_quiz_question(self):
        self.quiz_number = randint(0, 9)
        self.quiz_total += 1
        self.ids.quiz_question.text = (f"What is {self.quiz_number} in Sirijanga?")
        self.ids.quiz_result.text = ""
        incorrect_numbers = [
            number
            for number in range(10)
            if number != self.quiz_number
        ]
        choices = sample(incorrect_numbers, 3)
        choices.append(self.quiz_number)
        choices = sample(choices, len(choices))
        answer_grid = self.ids.answer_grid
        answer_grid.clear_widgets()
        for number in choices:
            button = MDRaisedButton(
                text=self.limbu_numbers[number],
                font_size=sp(24),
                font_name="assets/font/CODE2000.TTF",
                size_hint=(1, None),
                height=dp(70),
            )
            button.bind(on_release=lambda instance, answer=number: self.answer_quiz(answer))
            answer_grid.add_widget(button)

    def answer_quiz(self, answer):
        correct_limbu = self.limbu_numbers[self.quiz_number]
        if answer == self.quiz_number:
            self.quiz_score += 1
            self.ids.quiz_result.text = (f"Right! {correct_limbu} is {self.quiz_number}.")
        else:
            self.ids.quiz_result.text = (f"Wrong! Correct answer: {correct_limbu}")
        self.ids.quiz_score_label.text = (f"Score: {self.quiz_score}")

    def quit_quiz(self):
        dialog = MDDialog(
            title="Quiz Finished",
            text=(
                "Thank you for practicing Sirijanga numbers!\n\n"
                f"Your score: "
                f"{self.quiz_score}/{self.quiz_total}"
            ),
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())], )
        dialog.open()


class CustomAccordionItem(Accordion):
    header_color = ListProperty([0.15, 0.45, 0.90, 1])
    content_color = ListProperty([1, 1, 1, 1])


class UnicodeLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = 'CODE2000'
        self.font_size = sp(16)
        self.halign = 'left'
        self.valign = 'top'
        self.text_size = (None, None)
        self.markup = True
        self.size_hint_y = None
        self.bind(texture_size=self.setter('height'))
        self.update_theme()
        app = MDApp.get_running_app()
        if app:
            app.theme_cls.bind(theme_style=self._theme_changed)

    def _theme_changed(self, *args):
        self.update_theme()

    def update_theme(self):
        app = MDApp.get_running_app()
        if app:
            self.color = app.theme_text


class HelpScreen(Screen):
    def get_bottom_sheet_items(self):
        app = MDApp.get_running_app()
        if app.theme_cls.theme_style == "Light":
            theme_text = "Dark Mode"
            theme_icon = "weather-night"
        else:
            theme_text = "Light Mode"
            theme_icon = "white-balance-sunny"
        return [
            {"text": "Home", "icon": "home"},
            {"text": "Learn Sirijanga Numbers", "icon": "read"},
            {"text": "Update", "icon": "upload-outline"},
            {"text": "Rate Us", "icon": "star-circle-outline"},
            {"text": "Share the App", "icon": "share-variant-outline"},
            {"text": "Feedback", "icon": "email-outline"},
        ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_font()

    def register_font(self):
        import os
        font_path = 'assets/font/CODE2000.TTF'
        if os.path.exists(font_path):
            try:
                LabelBase.register(name='CODE2000', fn_regular=font_path)
            except Exception as e:
                print(f"Error registering font: {e}")
        else:
            print(f"Font file NOT found at: {os.path.abspath(font_path)}")

    def on_enter(self, *args):
        Clock.schedule_once(self.populate_bottom_sheet, 0)

    def on_leave(self, *args):
        try:
            bottom_sheet = self.ids.bottom_sheet
            if bottom_sheet.state != "close":
                bottom_sheet.dismiss()
        except Exception as e:
            (print(f"Bottom sheet close warning: {e}"))

    def go_back(self, *args):
        try:
            bottom_sheet = self.ids.bottom_sheet
            if bottom_sheet.state != "close":
                bottom_sheet.dismiss()
        except Exception:
            pass
        if self.manager:
            self.manager.current = "main"

    def open_bottom_sheet(self, *args):
        try:
            bottom_sheet = self.ids.bottom_sheet
            if bottom_sheet.state == "close":
                bottom_sheet.open()
        except Exception as e:
            print(f"ERROR opening bottom sheet: {e}")

    def close_bottom_sheet(self, *args):
        try:
            bottom_sheet = self.ids.bottom_sheet
            if bottom_sheet.state != "close":
                bottom_sheet.dismiss()
        except Exception as e:
            print(f"ERROR closing bottom sheet: {e}")

    def populate_bottom_sheet(self, *args):
        try:
            sheet_list = self.ids.sheet_list
        except Exception as e:
            print(f"Cannot access sheet_list: {e}")
            return
        sheet_list.clear_widgets()
        menu_items = self.get_bottom_sheet_items()
        for menu_item in menu_items:
            text = menu_item["text"]
            icon_name = menu_item["icon"]
            item = OneLineIconListItem(text=text)
            icon = IconLeftWidget(icon=icon_name)
            item.add_widget(icon)
            item.bind(on_release=lambda instance, selected=text: self.sheet_action(selected))
            sheet_list.add_widget(item)

    def sheet_action(self, action):
        self.close_bottom_sheet()
        if action == "Feedback":
            Clock.schedule_once(lambda dt: self.open_feedback_email(), 0.15)
        elif action == "Share the App":
            Clock.schedule_once(lambda dt: self.share_khanit(), 0.15)
        elif action == "Rate Us":
            Clock.schedule_once(lambda dt: self.rate_khanit(), 0.15)
        elif action == "Update":
            Clock.schedule_once(lambda dt: self.update_khanit(), 0.15)
        elif action == "Learn Sirijanga Numbers":
            self.open_limbu_number_trace()
        elif action == "Home":
            self.go_back()
        elif action == "Theme":
            app = MDApp.get_running_app()
            app.switch_theme_style()
            Clock.schedule_once(self.populate_bottom_sheet, 0.05)

    def share_khanit(self, *args):
        share_title = "Share Khanit"
        share_text = (
            "Khanit — Tri-Language Smart Calculator\n\n"
            "Android:\n"
            "https://play.google.com/store/apps/details?id=org.khanit&pcampaignid=web_share\n\n"
            "iOS:\n"
            "https://apps.apple.com/us/app/khanit/id6755106550"
        )
        try:
            # ANDROID — Native Share Sheet
            if platform == "android":
                try:
                    from jnius import autoclass
                    Intent = autoclass("android.content.Intent")
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    current_activity = PythonActivity.mActivity
                    send_intent = Intent(Intent.ACTION_SEND)
                    send_intent.setType("text/plain")
                    send_intent.putExtra(Intent.EXTRA_SUBJECT, share_title)
                    send_intent.putExtra(Intent.EXTRA_TEXT, share_text)
                    send_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    chooser = Intent.createChooser(send_intent, share_title)
                    chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    current_activity.startActivity(chooser)
                    return
                except Exception as e:
                    print(f"Android native share error: {e}")
            # iOS — Native Share Sheet
            elif platform == "ios":
                try:
                    from pyobjus import autoclass
                    UIApplication = autoclass("UIApplication")
                    UIActivityViewController = autoclass("UIActivityViewController")
                    application = UIApplication.sharedApplication()
                    window = application.keyWindow()
                    root_vc = window.rootViewController()
                    items = [share_title, share_text]
                    activity_vc = UIActivityViewController.alloc().initWithActivityItems_applicationActivities_(
                        items, None
                    )
                    try:
                        popover = activity_vc.popoverPresentationController()
                        if popover:
                            popover.sourceView = root_vc.view
                            popover.sourceRect = ((root_vc.view.bounds().size.width / 2),
                                                  (root_vc.view.bounds().size.height - 100), 1, 1)
                    except Exception:
                        pass
                    root_vc.presentViewController_animated_completion_(activity_vc, True, None)
                    return
                except Exception as e:
                    print(f"iOS native share error: {e}")
            # DESKTOP / FALLBACK
            webbrowser.open("https://play.google.com/store/apps/details?id=org.khanit&pcampaignid=web_share")
        except Exception as e:
            print(f"General sharing error: {e}")

    def rate_khanit(self, *args):
        android_url = ("https://play.google.com/store/apps/details?id=org.khanit")
        ios_url = ("https://apps.apple.com/us/app/khanit/id6755106550")
        try:
            if platform == "android":
                try:
                    from jnius import autoclass
                    Intent = autoclass("android.content.Intent")
                    Uri = autoclass("android.net.Uri")
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    market_uri = Uri.parse("market://details?id=org.khanit")
                    intent = Intent(Intent.ACTION_VIEW, market_uri)
                    current_activity = (PythonActivity.mActivity)
                    current_activity.startActivity(intent)
                except Exception as e:
                    print(f"Play Store app unavailable: {e}")
                    webbrowser.open(android_url)
                return
            elif platform == "ios":
                try:
                    webbrowser.open(ios_url)
                except Exception as e:
                    print(f"iOS App Store error: {e}")
                return
            else:
                webbrowser.open(android_url)
        except Exception as e:
            print(f"ERROR opening rating page: {e}")

    def update_khanit(self, *args):
        android_url = ("https://play.google.com/store/apps/details?id=org.khanit")
        ios_url = ("https://apps.apple.com/us/app/khanit/id6755106550")
        try:
            if platform == "android":
                try:
                    from jnius import autoclass
                    Intent = autoclass("android.content.Intent")
                    Uri = autoclass("android.net.Uri")
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    uri = Uri.parse("market://details?id=org.khanit")
                    intent = Intent(Intent.ACTION_VIEW, uri)
                    current_activity = (PythonActivity.mActivity)
                    current_activity.startActivity(intent)
                except Exception as e:
                    print(f"Could not open Play Store: {e}")
                    webbrowser.open(android_url)
                return
            elif platform == "ios":
                try:
                    webbrowser.open(ios_url)
                except Exception as e:
                    print(f"Could not open App Store: {e}")
                return
            else:
                webbrowser.open(android_url)
        except Exception as e:
            print(f"ERROR opening update page: {e}")

    def open_limbu_number_trace(self, *args):
        try:
            self.close_bottom_sheet()
            Clock.schedule_once(
                lambda dt: self._navigate_to_limbu_trace(),
                0.15
            )
        except Exception as e:
            print(f"Error opening Limbu Number Trace: {e}")

    def _navigate_to_limbu_trace(self):
        try:
            if self.manager:
                self.manager.current = "limbu_trace"
        except Exception as e:
            print(f"Navigation error: {e}")

    def on_start(self):
        Clock.schedule_once(self.populate_bottom_sheet, 0)

    def open_feedback_email(self, *args):
        recipient = "bestdialing17@gmail.com"
        subject = "Khanit App Feedback"
        body = (
            "Hello Khanit Team,\n\n"
            "I would like to provide the following feedback:\n\n\n"
            "Device:\n"
            "Platform:\n"
            "App Version:\n\n"
            "Thank you."
        )
        try:
            platform_name = platform
            if platform_name == "android":
                try:
                    from jnius import autoclass
                    Intent = autoclass("android.content.Intent")
                    Uri = autoclass("android.net.Uri")
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    intent = Intent(
                        Intent.ACTION_SENDTO,
                        Uri.parse(
                            "mailto:" + recipient +
                            "?subject=" + quote(subject) +
                            "&body=" + quote(body)
                        )
                    )
                    current_activity = (PythonActivity.mActivity)
                    current_activity.startActivity(intent)
                    return
                except Exception as e:
                    print(f"Android email intent failed: {e}")
                    mailto_url = ("mailto:" + recipient + "?subject=" + quote(subject) + "&body=" + quote(body))
                    webbrowser.open(mailto_url)
                    return
            elif platform_name == "ios":
                mailto_url = ("mailto:" + recipient + "?subject=" + quote(subject) + "&body=" + quote(body))
                webbrowser.open(mailto_url)
                return
            else:
                mailto_url = ("mailto:" + recipient + "?subject=" + quote(subject) + "&body=" + quote(body))
                webbrowser.open(mailto_url)
                return
        except Exception as e:
            print(f"ERROR opening feedback email: {e}")

    def open_limbu_number_trace(self, *args):
        if self.manager:
            self.manager.current = "limbu_trace"

    def toggle_theme(self, *args):
        app = MDApp.get_running_app()
        app.switch_theme_style()
        self.update_theme_ui()

    def get_theme_description(self):
        app = MDApp.get_running_app()
        if app.theme_cls.theme_style == "Light":
            return "Choose light or dark mode."
        return "Choose light or dark mode."

    def get_theme_icon(self):
        app = MDApp.get_running_app()
        if app.theme_cls.theme_style == "Light":
            return "weather-night"
        return "white-balance-sunny"

    def update_theme_ui(self, *args):
        try:
            if hasattr(self, "ids"):
                tabs = self.ids.get("number_tabs")
                if tabs:
                    for tab in tabs.tab_list:
                        tab.color = (1, 1, 1, 1)
            if "trace_number" in self.ids:
                self.ids.trace_number.theme_text_color = "Custom"
                self.ids.trace_number.text_color = (1, 1, 1, 1)
            if "progress_label" in self.ids:
                self.ids.progress_label.theme_text_color = "Custom"
                self.ids.progress_label.text_color = (1, 1, 1, 1)
            if "show_number_sirijanga" in self.ids:
                self.ids.show_number_sirijanga.theme_text_color = "Custom"
                self.ids.show_number_sirijanga.text_color = (1, 1, 1, 1)
            if "num_name" in self.ids:
                self.ids.num_name.theme_text_color = "Custom"
                self.ids.num_name.text_color = (1, 1, 1, 1)
            if "stroke_info" in self.ids:
                self.ids.stroke_info.theme_text_color = "Custom"
                self.ids.stroke_info.text_color = (1, 1, 1, 1)
            if "quiz_question" in self.ids:
                self.ids.quiz_question.theme_text_color = "Custom"
                self.ids.quiz_question.text_color = (1, 1, 1, 1)
            if "quiz_result" in self.ids:
                self.ids.quiz_result.theme_text_color = "Custom"
                self.ids.quiz_result.text_color = (1, 1, 1, 1)
            if "quiz_score_label" in self.ids:
                self.ids.quiz_score_label.theme_text_color = "Custom"
                self.ids.quiz_score_label.text_color = (1, 1, 1, 1)
            if "progress_bar" in self.ids:
                self.ids.progress_bar.color = (1, 1, 1, 1)
        except Exception as e:
            print(f"LimbuNumberTrace theme UI refresh warning: {e}")

    def open_labauk_link(self):
        webbrowser.open("https://labanepal.co.uk/services/")

    def open_cube_link(self):
        webbrowser.open("https://cube.com.np/services")

    def open_laba_link(self):
        webbrowser.open("https://www.labanepal.com/course_catalog?select=brands")

    def open_labauk_AIlink(self):
        webbrowser.open("https://labanepal.co.uk/services/artificial-intelligence-solutions/")


class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = None
        self.build_ui()
        Clock.schedule_once(self.update_theme_ui, 0)

    def set_database(self, db):
        self.db = db

    def get_top_bar_height(self):
        if platform == 'ios':
            return dp(60)
        elif platform == 'android':
            return dp(56)
        else:
            return dp(50)

    def update_theme_ui(self, *args):
        try:
            app = MDApp.get_running_app()
            if not app:
                return
            if app.theme_cls.theme_style == "Dark":
                icon_color = (1, 1, 1, 1)
                title_color = (1, 1, 1, 1)
            else:
                icon_color = (0.10, 0.10, 0.10, 1)
                title_color = (0.10, 0.10, 0.10, 1)
            if hasattr(self, "back_btn"):
                self.back_btn.theme_icon_color = "Custom"
                self.back_btn.icon_color = icon_color
            if hasattr(self, "clear_btn"):
                self.clear_btn.theme_icon_color = "Custom"
                self.clear_btn.icon_color = icon_color
            if hasattr(self, "history_title"):
                self.history_title.theme_text_color = "Custom"
                self.history_title.text_color = title_color
        except Exception as e:
            print(f"History theme UI update warning: {e}")

    def build_ui(self):
        main_layout = SafeAreaBoxLayout(
            orientation="vertical",
            base_padding=[
                dp(10),
                dp(10),
                dp(10),
                dp(10),
            ],
            safe_area_enabled=True,
        )
        top_bar = BoxLayout(
            size_hint_y=None,
            height=self.get_top_bar_height(),
            spacing=dp(10),
            padding=dp(2)
        )
        self.back_btn = MDIconButton(
            icon='arrow-left',
            on_release=self.go_back,
            size_hint_x=0.2,
            size_hint_y=None,
            height=dp(40),
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 1),
            background_color=(0, 0, 0, 0),
            background_normal=''
        )
        self.history_title = MDLabel(
            text='\nCalculation History',
            font_style="Caption",
            size_hint_x=0.6,
            halign='center',
            valign='middle',
            padding=dp(1),
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1)
        )
        self.clear_btn = MDIconButton(
            icon='delete-forever-outline',
            on_release=self.clear_history,
            size_hint_x=0.2,
            size_hint_y=None,
            height=dp(40),
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 1),
            background_color=(0, 0, 0, 0),
            background_normal=''
        )
        top_bar.add_widget(self.back_btn)
        top_bar.add_widget(self.history_title)
        top_bar.add_widget(self.clear_btn)
        main_layout.add_widget(top_bar)
        self.scroll_view = MDScrollView(size_hint_y=0.9)
        self.history_grid = MDGridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=dp(10))
        self.history_grid.bind(minimum_height=self.history_grid.setter('height'))
        self.scroll_view.add_widget(self.history_grid)
        main_layout.add_widget(self.scroll_view)
        self.add_widget(main_layout)
        try:
            LabelBase.register(name='CustomFont', fn_regular='assets/font/CODE2000.TTF')
        except:
            pass

    def on_enter(self):
        self.load_history()

    def load_history(self):
        if not self.db:
            return
        self.history_grid.clear_widgets()
        history = self.db.get_all_history()
        if not history:
            empty_label = MDLabel(
                text='No calculation history yet!',
                halign='center',
                size_hint_y=None,
                height=dp(50),
                theme_text_color='Secondary'
            )
            self.history_grid.add_widget(empty_label)
            return
        grouped_history = {}
        for record in history:
            timestamp = record[7]
            if ' | ' in timestamp:
                date_str = timestamp.split(' | ')[0]
            elif ' ' in timestamp:
                date_str = timestamp.split(' ')[0]
            else:
                date_str = timestamp
            if date_str not in grouped_history:
                grouped_history[date_str] = []
            grouped_history[date_str].append(record)

        def get_sortable_date(date_str):
            try:
                day, month, year = date_str.split('-')
                return f"{year}-{month}-{day}"
            except:
                return date_str

        sorted_dates = sorted(
            grouped_history.keys(),
            key=get_sortable_date,
            reverse=True
        )
        for date_str in sorted_dates:
            date_header = MDLabel(
                text=f"Date: {date_str}",
                font_name='assets/font/CODE2000.TTF',
                halign='left',
                size_hint_y=None,
                height=dp(40),
                theme_text_color='Primary',
                font_style='H6'
            )
            self.history_grid.add_widget(date_header)
            for record in grouped_history[date_str]:
                self.add_history_record(record)

    def delete_record(self, record_id, card_widget):
        if self.db:
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton
            dialog = MDDialog(
                title="Delete Record",
                text="Are you sure you want to delete this record?",
                buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: dialog.dismiss()),
                         MDFlatButton(text="DELETE", on_release=lambda x: self.confirm_delete(record_id, card_widget, dialog)), ], )
            dialog.open()

    def confirm_delete(self, record_id, card_widget, dialog):
        try:
            if self.db:
                self.db.ensure_connection()
                success = self.db.delete_record(record_id)
                if success:
                    if card_widget in self.history_grid.children:
                        self.history_grid.remove_widget(card_widget)
                    self.cleanup_empty_dates()
                    if len(self.history_grid.children) == 0:
                        empty_label = MDLabel(
                            text='No calculation history yet!',
                            halign='center',
                            size_hint_y=None,
                            height=dp(50),
                            theme_text_color='Secondary'
                        )
                        self.history_grid.add_widget(empty_label)
                    from kivymd.uix.dialog import MDDialog
                    from kivymd.uix.button import MDFlatButton
                    notification = MDDialog(
                        title="Success",
                        text="Record deleted successfully.",
                        buttons=[MDFlatButton(text="OK", on_release=lambda x: notification.dismiss()), ], )
                    notification.open()
                else:
                    from kivymd.uix.dialog import MDDialog
                    from kivymd.uix.button import MDFlatButton
                    notification = MDDialog(
                        title="Error",
                        text="Failed to delete record. Please try again.",
                        buttons=[MDFlatButton(text="OK", on_release=lambda x: notification.dismiss()), ], )
                    notification.open()
        except Exception as e:
            print(f"Error deleting record: {e}")
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton
            notification = MDDialog(
                title="Error",
                text="An error occurred while deleting.",
                buttons=[MDFlatButton(text="OK", on_release=lambda x: notification.dismiss()), ], )
            notification.open()
        dialog.dismiss()

    def cleanup_empty_dates(self):
        widgets_to_remove = []
        children_list = list(self.history_grid.children)
        for i, widget in enumerate(children_list):
            if isinstance(widget, MDLabel) and widget.text.startswith("Date:"):
                has_cards = False
                for j in range(i - 1, -1, -1):
                    if j < len(children_list) and not isinstance(children_list[j], MDLabel):
                        has_cards = True
                        break
                if not has_cards:
                    widgets_to_remove.append(widget)
        for widget in widgets_to_remove:
            if widget in self.history_grid.children:
                self.history_grid.remove_widget(widget)

    def add_history_record(self, record):
        record_id = record[0]
        app = MDApp.get_running_app()
        card = MDGridLayout(
            cols=1,
            size_hint_y=None,
            height=dp(200),
            spacing=dp(5),
            padding=dp(5)
        )
        with card.canvas.before:
            Color(*app.theme_surface)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[10])

        def update_card_background(instance, value):
            app = MDApp.get_running_app()
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(*app.theme_surface)
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[10])

        card.bind(pos=update_card_background, size=update_card_background)
        top_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(35),
            spacing=dp(5)
        )
        timestamp = record[7] if len(record) > 7 else ''
        if timestamp:
            if '|' in timestamp:
                time_str = timestamp.split('|')[1].strip()
            elif ' ' in timestamp:
                parts = timestamp.split(' ')
                time_str = parts[1] if len(parts) > 1 else ''
            else:
                time_str = timestamp
        else:
            time_str = ''
        time_label = MDLabel(
            text=(
                f"Time: {time_str}"
                if time_str
                else "Time not available"
            ),
            halign='left',
            size_hint_x=0.7,
            theme_text_color='Primary',
            font_style='Caption'
        )
        try:
            time_label.font_name = 'assets/font/CODE2000.TTF'
        except Exception:
            pass
        top_row.add_widget(time_label)
        spacer = BoxLayout(size_hint_x=0.1)
        top_row.add_widget(spacer)
        delete_btn = MDIconButton(
            icon='delete',
            pos_hint={'center_y': 0.5},
            theme_icon_color='Custom',
            icon_color=(0.7, 0.1, 0.1, 1),
            background_color=(0, 0, 0, 0),
            background_normal='',
            on_release=lambda x, rid=record_id, c=card:
            self.delete_record(rid, c))
        top_row.add_widget(delete_btn)
        card.add_widget(top_row)
        limbu_numbers = {
            '0': '᥆', '1': '᥇', '2': '᥈', '3': '᥉', '4': '᥊',
            '5': '᥋', '6': '᥌', '7': '᥍', '8': '᥎', '9': '᥏'
        }
        nepali_numbers = {
            '0': '०', '1': '१', '2': '२', '3': '३', '4': '४',
            '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'
        }

        def convert_to_limbu(text):
            if not text:
                return ''
            result = ''
            for char in text:
                if char in limbu_numbers:
                    result += limbu_numbers[char]
                else:
                    result += char
            return result

        def convert_to_nepali(text):
            if not text:
                return ''
            result = ''
            for char in text:
                if char in nepali_numbers:
                    result += nepali_numbers[char]
                else:
                    result += char
            return result

        if record[1] or record[2]:
            lim_expression_display = convert_to_limbu(record[1] or '')
            lim_result_display = convert_to_limbu(record[2] or '')
            lim_text = (f"Kirat:  {lim_expression_display} = {lim_result_display}")
            lim_label = MDLabel(
                text=lim_text,
                halign='left',
                size_hint_y=None,
                height=dp(35),
                theme_text_color='Primary'
            )
            try:
                lim_label.font_name = ('assets/font/CODE2000.TTF')
            except Exception:
                pass
            card.add_widget(lim_label)
        if record[3] or record[4]:
            nep_expression_display = convert_to_nepali(record[3] or '')
            nep_result_display = convert_to_nepali(record[4] or '')
            nep_text = (f"Nepali: {nep_expression_display} = {nep_result_display}")
            nep_label = MDLabel(
                text=nep_text,
                halign='left',
                size_hint_y=None,
                height=dp(35),
                theme_text_color='Primary',
                font_size=dp(14)
            )
            try:
                nep_label.font_name = ('assets/font/CODE2000.TTF')
            except Exception:
                pass
            card.add_widget(nep_label)
        if record[5] or record[6]:
            eng_text = (f"English: {record[5] or ''} = {record[6] or ''}")
            eng_label = MDLabel(
                text=eng_text,
                halign='left',
                size_hint_y=None,
                height=dp(35),
                theme_text_color='Primary'
            )
            card.add_widget(eng_label)
        separator = BoxLayout(size_hint_y=None, height=dp(1))
        with separator.canvas:
            Color(*app.theme_secondary_text)
            Rectangle(pos=separator.pos, size=separator.size)

        def update_separator(instance, value):
            app = MDApp.get_running_app()
            instance.canvas.clear()
            with instance.canvas:
                Color(*app.theme_secondary_text)
                Rectangle(pos=instance.pos, size=instance.size)

        separator.bind(pos=update_separator, size=update_separator)
        card.add_widget(separator)
        self.history_grid.add_widget(card)

    def go_back(self, instance):
        self.manager.current = 'main'

    def clear_history(self, instance):
        if self.db:
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton
            dialog = MDDialog(
                title="Clear All History",
                text="Are you sure you want to delete all history records?",
                buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: dialog.dismiss()),
                         MDFlatButton(text="DELETE ALL", on_release=lambda x: self.confirm_clear_all(dialog)), ], )
            dialog.open()

    def confirm_clear_all(self, dialog):
        if self.db:
            self.db.clear_history()
            self.history_grid.clear_widgets()
            empty_label = MDLabel(
                text='No calculation history yet',
                halign='center',
                size_hint_y=None,
                height=dp(50),
                theme_text_color='Secondary'
            )
            self.history_grid.add_widget(empty_label)
            dialog.dismiss()
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton
            success_dialog = MDDialog(
                title="Success!",
                text="All history has been cleared successfully.",
                buttons=[MDFlatButton(text="OK", on_release=lambda x: success_dialog.dismiss()), ], )
            success_dialog.open()


class NumberPadContainer(SafeAreaBoxLayout):
    western_display = ObjectProperty(None)
    limbu_display = ObjectProperty(None)
    nepali_display = ObjectProperty(None)
    limbu_numbers = {
        '0': '᥆', '1': '᥇', '2': '᥈', '3': '᥉', '4': '᥊',
        '5': '᥋', '6': '᥌', '7': '᥍', '8': '᥎', '9': '᥏'
    }
    nepali_numbers = {
        '0': '०', '1': '१', '2': '२', '3': '३', '4': '४',
        '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (0.98, 0.98, 0.98, 1)
        self.db = KhanitDatabase()

    def update_rect(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*instance.background_color)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[10])

    def add_number(self, number):
        current = self.western_display.text
        self.western_display.text = current + str(number)
        self.update_limbu_display()
        self.update_nepali_display()

    def add_operator(self, operator):
        current = self.western_display.text
        if current and current[-1] not in '+-×÷.':
            self.western_display.text = current + operator
            self.update_limbu_display()
            self.update_nepali_display()

    def add_decimal(self):
        current = self.western_display.text
        if current:
            last_number = ''
            for char in reversed(current):
                if char in '+-×÷.%':
                    break
                last_number = char + last_number
            if '.' not in last_number:
                self.western_display.text = current + '.'
                self.update_limbu_display()
                self.update_nepali_display()
        else:
            self.western_display.text = '0.'
            self.update_limbu_display()
            self.update_nepali_display()

    def add_percent(self):
        current = self.western_display.text
        if current and current[-1] not in '+-×÷.%':
            self.western_display.text = current + '%'
            self.update_limbu_display()
            self.update_nepali_display()

    def calculate_result(self):
        try:
            current = self.western_display.text
            if current:
                eng_expression = current
                lim_expression = self.limbu_display.text.replace('Kirat: ', '') if self.limbu_display.text else ''
                nep_expression = self.nepali_display.text.replace('Nepali: ', '') if self.nepali_display.text else ''
                expression = current.replace('×', '*').replace('÷', '/')
                import re

                def replace_percent(match):
                    num = match.group(1)
                    return str(float(num) / 100)

                expression = re.sub(r'(\d+\.?\d*)%', replace_percent, expression)
                result = eval(expression)
                if isinstance(result, (int, float)):
                    result = round(result, 2)
                    if isinstance(result, int) or (isinstance(result, float) and result.is_integer()):
                        result = int(result)
                eng_result = str(result)
                self.western_display.text = eng_result
                self.update_limbu_display()
                self.update_nepali_display()
                lim_result = self.limbu_display.text.replace('Kirat: ', '') if self.limbu_display.text else ''
                nep_result = self.nepali_display.text.replace('Nepali: ', '') if self.nepali_display.text else ''
                self.db.insert_history(
                    (lim_expression, lim_result),
                    (nep_expression, nep_result),
                    (eng_expression, eng_result)
                )
        except Exception as e:
            self.western_display.text = 'Error'
            self.update_limbu_display()
            self.update_nepali_display()
            print(f"Calculation error: {e}")

    def update_limbu_display(self):
        western_text = self.western_display.text
        limbu_text = "Kirat: "
        for char in western_text:
            if char in self.limbu_numbers:
                limbu_text += self.limbu_numbers[char]
            else:
                limbu_text += char
        self.limbu_display.text = limbu_text

    def update_nepali_display(self):
        western_text = self.western_display.text
        nepali_text = "Nepali: "
        for char in western_text:
            if char in self.nepali_numbers:
                nepali_text += self.nepali_numbers[char]
            else:
                nepali_text += char
        self.nepali_display.text = nepali_text

    def backspace(self, instance):
        current = self.western_display.text
        if current:
            self.western_display.text = current[:-1]
            self.update_limbu_display()
            self.update_nepali_display()

    def delete(self, instance):
        current = self.western_display.text
        if current:
            self.western_display.text = current[1:]
            self.update_limbu_display()
            self.update_nepali_display()

    def clear_all(self, instance):
        self.western_display.text = ''
        self.limbu_display.text = ''
        self.nepali_display.text = ''

    def show_history(self):
        try:
            app = MDApp.get_running_app()
            screen_manager = app.sm
            history_screen = screen_manager.get_screen("history")
            history_screen.set_database(self.db)
            screen_manager.current = "history"
        except Exception as e:
            print(f"Error opening History screen: {e}")

    def show_help(self):
        try:
            app = MDApp.get_running_app()
            screen_manager = app.sm
            screen_manager.current = "help"
        except Exception as e:
            print(f"Error opening Help screen: {e}")


class NumberButton(Button):
    number_value = NumericProperty(0)
    bg_color = ListProperty([0, 0, 0, 0])
    border_color = ListProperty([0.4, 0.6, 0.8, 1])
    limbu_numbers = DictProperty(NumberPadContainer.limbu_numbers)
    nepali_numbers = DictProperty(NumberPadContainer.nepali_numbers)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = ('assets/font/CODE2000.TTF')
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.halign = 'center'
        self.valign = 'middle'
        self.text_size = self.size
        self.update_background()

    def on_pos(self, instance, value):
        self.update_background()

    def on_size(self, instance, value):
        self.update_background()
        self.text_size = self.size

    def update_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.border_color)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 10), width=1.01)


class CalculatorApp(MDApp):
    theme_background = ListProperty([1, 1, 1, 1])
    theme_surface = ListProperty([1, 1, 1, 1])
    theme_text = ListProperty([0, 0, 0, 1])
    theme_secondary_text = ListProperty([0.45, 0.45, 0.45, 1])
    theme_border = ListProperty([0.4, 0.6, 0.8, 1])
    theme_input_background = ListProperty([1, 1, 1, 1])
    theme_input_text = ListProperty([0.2, 0.4, 0.6, 1])
    theme_accent = ListProperty([0.4, 0.6, 0.8, 1])

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.update_theme_colors()
        self.theme_cls.bind(theme_style=self._on_theme_style_changed)

        if platform in ['win', 'linux', 'macosx']:
            Window.size = (400, 700)

        # ============================================================
        # ✅ STATUS BAR — iOS configuration
        # ============================================================
        if platform == "ios":
            self._configure_ios_status_bar()

        Window.clearcolor = (self.theme_background)

        # SAFE AREA
        self.safe_area = SafeAreaManager.get_instance()
        self.safe_area.start()

        # SCREEN MANAGER
        self.sm = ScreenManager()
        main_screen = Screen(name='main')
        self.calculator = NumberPadContainer()
        main_screen.add_widget(self.calculator)
        history_screen = HistoryScreen(name='history')
        help_screen = HelpScreen(name='help')
        limbu_trace_screen = LimbuNumberTrace(name='limbu_trace')
        self.sm.add_widget(main_screen)
        self.sm.add_widget(history_screen)
        self.sm.add_widget(help_screen)
        self.sm.add_widget(limbu_trace_screen)
        history_screen.set_database(self.calculator.db)
        self.sm.current = "main"
        return self.sm

    def _configure_ios_status_bar(self):
        """✅ Configure iOS status bar to be visible"""
        try:
            # ✅ FIXED: Only import autoclass, no broken dylib_manager import
            from pyobjus import autoclass

            UIApplication = autoclass("UIApplication")
            app = UIApplication.sharedApplication()

            # Try to unhide status bar via UIApplication
            try:
                # setStatusBarHidden:NO animated:YES
                app.setStatusBarHidden_animated_(False, True)
                print("iOS: setStatusBarHidden_animated_ called")
            except Exception as e:
                print(f"iOS setStatusBarHidden: {e}")

            # Set status bar text style
            self._update_ios_status_bar_style()

            # Try to force VC to update status bar appearance
            try:
                windows = app.windows()
                if windows and windows.count() > 0:
                    window = windows.objectAtIndex_(0)
                    if window:
                        root_vc = window.rootViewController()
                        if root_vc:
                            root_vc.setNeedsStatusBarAppearanceUpdate()
                            print("iOS: setNeedsStatusBarAppearanceUpdate called")
            except Exception as e:
                print(f"iOS VC status bar update: {e}")

            print("iOS status bar: configuration applied")

        except Exception as e:
            print(f"iOS Status Bar configuration error: {e}")

    def _update_ios_status_bar_style(self):
        """Update iOS status bar text color based on theme"""
        if platform != "ios":
            return
        try:
            from pyobjus import autoclass
            UIApplication = autoclass("UIApplication")
            app = UIApplication.sharedApplication()

            # UIStatusBarStyleDefault = 0 (dark text for light backgrounds)
            # UIStatusBarStyleLightContent = 1 (light text for dark backgrounds)
            if self.theme_cls.theme_style == "Dark":
                style_value = 1  # Light/white text
            else:
                style_value = 0  # Dark/black text

            try:
                app.setStatusBarStyle_(style_value)
                print(f"iOS: setStatusBarStyle_({style_value}) called")
            except Exception as e:
                print(f"iOS setStatusBarStyle: {e}")

            try:
                windows = app.windows()
                if windows and windows.count() > 0:
                    window = windows.objectAtIndex_(0)
                    if window:
                        root_vc = window.rootViewController()
                        if root_vc:
                            root_vc.setNeedsStatusBarAppearanceUpdate()
            except Exception as e:
                print(f"iOS VC appearance update: {e}")

        except Exception as e:
            print(f"iOS status bar style error: {e}")

    def on_start(self):
        Clock.schedule_once(self._refresh_safe_area, 0)
        Clock.schedule_once(self._refresh_safe_area, 0.20)
        # Re-apply status bar config after window is fully ready
        if platform == "ios":
            Clock.schedule_once(lambda dt: self._configure_ios_status_bar(), 0.30)
            Clock.schedule_once(lambda dt: self._configure_ios_status_bar(), 0.60)
            Clock.schedule_once(lambda dt: self._configure_ios_status_bar(), 1.0)

    def _refresh_safe_area(self, *args):
        try:
            self.safe_area.refresh()
        except Exception as exc:
            print("Safe area startup error:", exc)

    def on_resume(self):
        try:
            self.safe_area.refresh()
            Clock.schedule_once(self.safe_area.refresh, 0.10)
            Clock.schedule_once(self.safe_area.refresh, 0.30)
        except Exception as exc:
            print("Safe area resume error:", exc)

    def on_pause(self):
        return True

    def on_stop(self):
        try:
            if hasattr(self, "safe_area"):
                self.safe_area.stop()
        except Exception as exc:
            print("Safe area stop error:", exc)
        try:
            if hasattr(self, "calculator") and self.calculator.db:
                self.calculator.db.close()
        except Exception as exc:
            print("Database close error:", exc)

    def _on_theme_style_changed(self, instance, theme_style):
        self.update_theme_colors()
        Window.clearcolor = self.theme_background

        if platform == "ios":
            self._update_ios_status_bar_style()

        try:
            help_screen = self.sm.get_screen("help")
            help_screen.update_theme_ui()
        except Exception as e:
            print(f"Help theme UI refresh warning: {e}")
        try:
            history_screen = self.sm.get_screen("history")
            history_screen.update_theme_ui()
        except Exception as e:
            print(f"History theme UI refresh warning: {e}")
        try:
            limbu_screen = self.sm.get_screen("limbu_trace")
            limbu_screen.update_theme_ui()
        except Exception as e:
            print(f"Limbu theme UI refresh warning: {e}")

    def update_theme_colors(self):
        if self.theme_cls.theme_style == "Dark":
            self.theme_background = [0.08, 0.08, 0.08, 1]
            self.theme_surface = [0.13, 0.13, 0.13, 1]
            self.theme_text = [1, 1, 1, 1]
            self.theme_secondary_text = [0.72, 0.72, 0.72, 1]
            self.theme_border = [0.35, 0.65, 0.85, 1]
            self.theme_input_background = [0.16, 0.16, 0.16, 1]
            self.theme_input_text = [0.75, 0.85, 1, 1]
        else:
            self.theme_background = [0.98, 0.98, 0.98, 1]
            self.theme_surface = [1, 1, 1, 1]
            self.theme_text = [0.10, 0.10, 0.10, 1]
            self.theme_secondary_text = [0.40, 0.40, 0.40, 1]
            self.theme_border = [0.40, 0.60, 0.80, 1]
            self.theme_input_background = [1, 1, 1, 1]
            self.theme_input_text = [0.20, 0.40, 0.60, 1]

    def switch_theme_style(self, *args):
        if self.theme_cls.theme_style == "Light":
            self.theme_cls.theme_style = "Dark"
        else:
            self.theme_cls.theme_style = "Light"


if __name__ == '__main__':
    CalculatorApp().run()