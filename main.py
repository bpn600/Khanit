from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen, SwapTransition
from kivy.core.audio import SoundLoader
import sqlite3
from datetime import datetime
from kivy.clock import Clock
from kivy.uix.textinput import TextInput

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

# Window.size = (310, 600)

class KeyboardThemeStyle(Screen):
    pass

class HelpScreen(Screen):
    pass

class NoKeyboardTextInput(TextInput):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.focus = True
            return True
        return super().on_touch_down(touch)

    def _on_focus(self, instance, value):
        if value:
            self.focus = False

class LogScreen(Screen):
    delete_dialog = None

    def on_pre_enter(self):
        self.load_history()

    def load_history(self):
        try:
            import os
            from kivy.app import App

            app = App.get_running_app()
            if hasattr(app, 'user_data_dir'):
                db_path = os.path.join(app.user_data_dir, 'kirat_cal.db')
            else:
                db_path = 'kirat_cal.db'

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, expression, result, timestamp_english, timestamp_nepali, timestamp_limbu
                FROM calu_activity
                ORDER BY timestamp_english DESC, id DESC
            ''')
            records = cursor.fetchall()
            conn.close()

            if not records:
                self.ids.log_label.text = "[size=20sp][b]No history found[/b][/size]"
                self.ids.log_label.markup = True
                return

            main_screen = self.manager.get_screen('main')
            num_system = main_screen.current_num_system

            def parse_timestamp_for_header(ts_eng):
                try:
                    dt = datetime.strptime(ts_eng, '%Y-%m-%d | %H:%M:%S')
                    weekday = dt.strftime('%A')
                    date_only = dt.strftime('%d-%m-%Y')
                    time_only = dt.strftime('%H:%M:%S')
                    return weekday, date_only, time_only, dt.date()
                except Exception:
                    try:
                        parts = ts_eng.split('|')
                        left = parts[0].strip() if parts else ts_eng
                        time_part = parts[1].strip() if len(parts) > 1 else ''
                        date_only = left
                        weekday = ''
                        return weekday, date_only, time_part, None
                    except Exception:
                        return '', ts_eng, '', None

            grouped = {}
            order_of_dates = []

            for rec in records:
                rec_id, expression, result, ts_eng, ts_nep, ts_lim = rec
                weekday, date_only, time_only, _ = parse_timestamp_for_header(ts_eng or "")
                date_key = date_only or ts_eng or "Unknown Date"

                if date_key not in grouped:
                    grouped[date_key] = []
                    order_of_dates.append(date_key)

                if num_system == "limbu":
                    time_str = ts_lim.split('|')[-1].strip() if ts_lim else (time_only or '')
                elif num_system == "nepali":
                    time_str = ts_nep.split('|')[-1].strip() if ts_nep else (time_only or '')
                else:
                    time_str = ts_eng.split('|')[-1].strip() if ts_eng else (time_only or '')

                grouped[date_key].append((rec_id, expression, result, time_str, ts_eng, ts_nep, ts_lim))

            history_lines = [""]
            for date_key in order_of_dates:
                first_rec = grouped[date_key][0]
                ts_eng = first_rec[4]
                weekday, date_only, _, _ = parse_timestamp_for_header(ts_eng or "")

                display_date = date_key
                if date_only and num_system in ("nepali", "limbu"):
                    display_date = main_screen.convert_timestamp(date_only, num_system)

                header_text = f"[size=20sp][b]{weekday} | {display_date}[/b][/size]\n"
                history_lines.append(header_text)

                for rec in grouped[date_key]:
                    rec_id, expression, result, time_str, ts_eng, ts_nep, ts_lim = rec

                    if num_system == "limbu":
                        ts_display = ts_lim or ts_eng or ""
                    elif num_system == "nepali":
                        ts_display = ts_nep or ts_eng or ""
                    else:
                        ts_display = ts_eng or ts_nep or ts_lim or ""

                    if '|' in ts_display:
                        ts_parts = ts_display.split('|')
                        ts_time_part = ts_parts[-1].strip()
                    else:
                        ts_time_part = ts_display[-8:] if len(ts_display) >= 8 else ts_display

                    if num_system != "english":
                        expr_display = main_screen.convert_from_english(expression) if expression else ""
                        result_display = main_screen.convert_from_english(result) if result else ""
                    else:
                        expr_display = expression if expression else ""
                        result_display = result if result else ""

                    history_lines.append(
                        f"[size=16sp][b]{expr_display} = {result_display}[/b][/size]\n"
                        f"[size=14sp]{ts_time_part}[/size]"
                        f"              [color=ff0000][ref=del_{rec_id}][size=14sp][Delete][/size][/ref][/color]\n"
                    )

            full_text = "\n".join(history_lines)
            self.ids.log_label.text = full_text
            self.ids.log_label.markup = True

        except Exception as e:
            print(f"Error loading history: {e}")
            self.ids.log_label.text = "Error loading history"

    def show_delete_confirmation(self, record_id):
        if self.delete_dialog:
            self.delete_dialog.dismiss()

        app = MDApp.get_running_app()

        self.delete_dialog = MDDialog(
            title="Confirm Delete",
            text="Are you sure you want to delete this record?",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    theme_text_color="Custom",
                    text_color=app.theme_cls.primary_color,
                    on_release=lambda x: self.delete_dialog.dismiss()
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color=(1, 0, 0, 1),
                    on_release=lambda x: self.confirm_delete(record_id)
                ),
            ],
        )
        self.delete_dialog.open()

    def confirm_delete(self, record_id):
        try:
            if self.delete_dialog:
                self.delete_dialog.dismiss()

            import os
            from kivy.app import App

            app = App.get_running_app()
            if hasattr(app, 'user_data_dir'):
                db_path = os.path.join(app.user_data_dir, 'kirat_cal.db')
            else:
                db_path = 'kirat_cal.db'

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM calu_activity WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()

            self.show_delete_success()
            self.load_history()

        except Exception as e:
            print(f"Error deleting record: {e}")
            self.show_delete_error(str(e))

    def show_delete_success(self):
        app = MDApp.get_running_app()

        success_dialog = MDDialog(
            title="Success",
            text="Record deleted successfully!",
            buttons=[
                MDFlatButton(
                    text="OK",
                    theme_text_color="Custom",
                    text_color=app.theme_cls.primary_color,
                    on_release=lambda x: success_dialog.dismiss()
                ),
            ],
        )
        success_dialog.open()

    def show_delete_error(self, error_msg):
        app = MDApp.get_running_app()

        error_dialog = MDDialog(
            title="Error",
            text=f"Failed to delete record: {error_msg}",
            buttons=[
                MDFlatButton(
                    text="OK",
                    theme_text_color="Custom",
                    text_color=app.theme_cls.primary_color,
                    on_release=lambda x: error_dialog.dismiss()
                ),
            ],
        )
        error_dialog.open()

    def on_ref_press(self, ref):
        if ref.startswith('del_'):
            record_id = ref[4:]
            self.show_delete_confirmation(record_id)

class MainScreen(Screen):
    current_input = StringProperty("")
    current_result = StringProperty("0")
    current_num_system = StringProperty("limbu")
    font_name = StringProperty("assets/font/CODE2000.TTF")
    focused_field = StringProperty("input")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.operators = ['+', '-', '×', '÷', '%']
        self.last_was_operator = False
        self.font_name = "assets/font/CODE2000.TTF"
        self.sound = None

        self.nepali_numbers = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९']
        self.limbu_numbers = ['᥆', '᥇', '᥈', '᥉', '᥊', '᥋', '᥌', '᥍', '᥎', '᥏']

        self.init_database()
        self.init_sound()
        Clock.schedule_once(self.update_hint_colors)

    def update_hint_colors(self, dt=None):
        dark_gray = [0.3, 0.3, 0.3, 1]
        light_gray = [0.9, 0.9, 0.9, 1]

        app = MDApp.get_running_app()
        hint_color = dark_gray if app.theme_cls.theme_style == "Light" else light_gray

        self.ids.input_text.hint_text_color = hint_color
        self.ids.result_text.hint_text_color = hint_color

        self.ids.input_text.canvas.ask_update()
        self.ids.result_text.canvas.ask_update()

    def init_sound(self):
        try:
            self.sound = SoundLoader.load('assets/sound/click.mp3')
            if not self.sound:
                print("Sound file not found or couldn't be loaded")
        except Exception as e:
            print(f"Error loading sound: {e}")

    def init_database(self):
        try:
            import os
            from kivy.app import App

            app = App.get_running_app()
            if hasattr(app, 'user_data_dir'):
                db_path = os.path.join(app.user_data_dir, 'kirat_cal.db')
            else:
                db_path = 'kirat_cal.db'

            print(f"Database path: {db_path}")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calu_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expression TEXT,
                    result TEXT,
                    timestamp_english TEXT,
                    timestamp_nepali TEXT,
                    timestamp_limbu TEXT
                )
            ''')
            conn.commit()
            conn.close()
            return db_path
        except Exception as e:
            print(f"Database initialization error: {e}")
            return None

    def play_sound(self):
        if self.sound:
            try:
                self.sound.play()
            except Exception as e:
                print(f"Error playing sound: {e}")

    def convert_to_english(self, text):
        if not text:
            return text
        if self.current_num_system == "english":
            return text
        elif self.current_num_system == "nepali":
            return ''.join([str(self.nepali_numbers.index(c)) if c in self.nepali_numbers else c for c in text])
        elif self.current_num_system == "limbu":
            return ''.join([str(self.limbu_numbers.index(c)) if c in self.limbu_numbers else c for c in text])
        return text

    def convert_from_english(self, text):
        if not text:
            return text
        if self.current_num_system == "english":
            return text
        elif self.current_num_system == "nepali":
            return ''.join([self.nepali_numbers[int(c)] if c.isdigit() else c for c in text])
        elif self.current_num_system == "limbu":
            return ''.join([self.limbu_numbers[int(c)] if c.isdigit() else c for c in text])
        return text

    def nep_num_press(self, button_text):
        if button_text == "NEP_NUM" and self.current_num_system != "nepali":
            self.convert_existing_content("nepali")
            self.current_num_system = "nepali"
            self.font_name = "assets/font/CODE2000.TTF"

    def lim_num_press(self, button_text):
        if button_text == "LIM_NUM" and self.current_num_system != "limbu":
            self.convert_existing_content("limbu")
            self.current_num_system = "limbu"
            self.font_name = "assets/font/CODE2000.TTF"

    def eng_num_press(self, button_text):
        if button_text == "ENG_NUM" and self.current_num_system != "english":
            self.convert_existing_content("english")
            self.current_num_system = "english"
            self.font_name = "Roboto"

    def convert_existing_content(self, new_system):
        if self.current_input:
            english_input = self.convert_to_english(self.current_input)
            self.current_input = self.convert_from_english_system(english_input, new_system)

        if self.current_result and self.current_result != "0" and self.current_result != "Error":
            english_result = self.convert_to_english(self.current_result)
            self.current_result = self.convert_from_english_system(english_result, new_system)

    def convert_from_english_system(self, text, to_system):
        if not text or to_system == "english":
            return text

        number_map = {
            "nepali": self.nepali_numbers,
            "limbu": self.limbu_numbers
        }

        numbers = number_map[to_system]
        result = []
        for char in text:
            if char.isdigit():
                result.append(numbers[int(char)])
            else:
                result.append(char)
        return ''.join(result)

    def on_button_press(self, button_text):
        self.set_focus("input")

        if button_text == "AC":
            self.current_input = ""
            self.current_result = "0"
            self.last_was_operator = False
            return

        if button_text == "DEL":
            if self.current_input:
                self.current_input = self.current_input[1:]
            return

        if button_text == "⌫":
            if self.current_input:
                self.current_input = self.current_input[:-1]
            return

        if button_text == "=":
            self.calculate_result()
            return

        if button_text == "%":
            self.current_input += button_text
            self.calculate_percentage()
            return

        if button_text in self.operators and not self.current_input and self.current_result != "0":
            english_result = self.convert_to_english(self.current_result)
            self.current_input = english_result + button_text
            self.last_was_operator = True
            return

        if button_text in self.operators:
            if self.current_input and self.last_was_operator:
                self.current_input = self.current_input[:-1] + button_text
                return
            elif not self.current_input:
                return
            self.last_was_operator = True
        else:
            self.last_was_operator = False

        self.current_input += button_text

    def convert_timestamp(self, timestamp_str, number_system):
        if number_system == "english":
            return timestamp_str

        number_map = {
            "nepali": ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'],
            "limbu": ['᥆', '᥇', '᥈', '᥉', '᥊', '᥋', '᥌', '᥍', '᥎', '᥏']
        }

        digits = number_map[number_system]
        converted = []
        for char in timestamp_str:
            if char.isdigit():
                converted.append(digits[int(char)])
            else:
                converted.append(char)
        return ''.join(converted)

    def save_calculation(self, expression, result):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d | %H:%M:%S')

            timestamp_english = timestamp
            timestamp_nepali = self.convert_timestamp(timestamp, "nepali")
            timestamp_limbu = self.convert_timestamp(timestamp, "limbu")

            import os
            from kivy.app import App

            app = App.get_running_app()
            if hasattr(app, 'user_data_dir'):
                db_path = os.path.join(app.user_data_dir, 'kirat_cal.db')
            else:
                db_path = 'kirat_cal.db'

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO calu_activity 
                (expression, result, timestamp_english, timestamp_nepali, timestamp_limbu)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                expression,
                result,
                timestamp_english,
                timestamp_nepali,
                timestamp_limbu
            ))

            conn.commit()
            conn.close()
            print("Calculation saved successfully!")
        except Exception as e:
            print(f"Error saving calculation: {e}")

    def calculate_percentage(self):
        try:
            if not self.current_input:
                self.current_result = self.convert_from_english("0")
                return True

            english_input = self.convert_to_english(self.current_input)

            if english_input.endswith('%'):
                num_part = english_input[:-1]
                if not num_part:
                    self.current_result = self.convert_from_english("0")
                    self.current_input = ""
                    return True

                try:
                    value = float(num_part)
                    percentage = value / 100
                    result_str = "{:.2f}".format(float(percentage)).rstrip('0').rstrip(
                        '.') if percentage % 1 else "{:.0f}".format(percentage)
                    self.current_result = self.convert_from_english(result_str)
                    self.current_input = ""
                    return True
                except ValueError:
                    self.current_result = self.convert_from_english("0")
                    return True

            if '%' in english_input:
                parts = english_input.split('%')
                if len(parts) != 2 or parts[1] != '':
                    self.current_result = self.convert_from_english("0")
                    return True

                expr_part = parts[0]
                if not expr_part:
                    self.current_result = self.convert_from_english("0")
                    self.current_input = ""
                    return True

                operators = {'+', '-', '×', '÷', '*', '/'}
                last_op = None
                last_op_pos = -1
                for op in operators:
                    pos = expr_part.rfind(op)
                    if pos > last_op_pos:
                        last_op_pos = pos
                        last_op = op

                if last_op:
                    left_part = expr_part[:last_op_pos]
                    right_part = expr_part[last_op_pos + 1:]

                    try:
                        left_num = float(left_part) if left_part else 0.0
                        right_num = float(right_part) if right_part else 0.0

                        op = last_op.replace('×', '*').replace('÷', '/')

                        if op == '+':
                            result = left_num + (left_num * right_num / 100)
                        elif op == '-':
                            result = left_num - (left_num * right_num / 100)
                        elif op == '*':
                            result = left_num * (right_num / 100)
                        elif op == '/':
                            if right_num == 0:
                                self.current_result = self.convert_from_english("0")
                                return True
                            result = left_num / (right_num / 100)

                        result_str = "{:.2f}".format(float(result)).rstrip('0').rstrip(
                            '.') if result % 1 else "{:.0f}".format(result)
                        self.current_result = self.convert_from_english(result_str)
                        self.current_input = ""
                        return True
                    except (ValueError, ZeroDivisionError):
                        self.current_result = self.convert_from_english("0")
                        return True
                else:
                    try:
                        value = float(expr_part)
                        percentage = value / 100
                        result_str = "{:.2f}".format(float(percentage)).rstrip('0').rstrip(
                            '.') if percentage % 1 else "{:.0f}".format(percentage)
                        self.current_result = self.convert_from_english(result_str)
                        self.current_input = ""
                        return True
                    except ValueError:
                        self.current_result = self.convert_from_english("0")
                        return True

            return False
        except Exception as e:
            print(f"Percentage calculation error: {e}")
            self.current_result = self.convert_from_english("0")
            return True

    def calculate_result(self):
        try:
            if not self.current_input:
                self.current_result = self.convert_from_english("0")
                return

            original_input = self.current_input
            english_input = self.convert_to_english(self.current_input)

            if '%' in english_input:
                if english_input.endswith('%'):
                    value_part = english_input[:-1]
                    try:
                        value = float(value_part) if value_part else 0
                        result = value / 100
                        result_str = "{:.2f}".format(float(result)).rstrip('0').rstrip(
                            '.') if result % 1 else "{:.0f}".format(result)
                        self.current_result = self.convert_from_english(result_str)
                        self.save_calculation(original_input, self.convert_from_english(result_str))
                        self.current_input = ""
                        return
                    except ValueError:
                        pass

                parts = english_input.split('%')
                if len(parts) == 2 and parts[1] == '':
                    expr_part = parts[0]
                    operators = {'+', '-', '×', '÷', '*', '/'}
                    last_op = None
                    last_op_pos = -1
                    for op in operators:
                        pos = expr_part.rfind(op)
                        if pos > last_op_pos:
                            last_op_pos = pos
                            last_op = op

                    if last_op:
                        left_part = expr_part[:last_op_pos]
                        right_part = expr_part[last_op_pos + 1:]
                        try:
                            left_num = float(left_part) if left_part else 0
                            right_num = float(right_part) if right_part else 0

                            if last_op in ('+', '-'):
                                percentage = right_num / 100
                                if last_op == '+':
                                    result = left_num + (left_num * percentage)
                                else:
                                    result = left_num - (left_num * percentage)
                            else:
                                percentage = right_num / 100
                                if last_op in ('×', '*'):
                                    result = left_num * percentage
                                else:
                                    if percentage == 0:
                                        self.current_result = self.convert_from_english("Error")
                                        return
                                    result = left_num / percentage

                            result_str = "{:.2f}".format(float(result)).rstrip('0').rstrip(
                                '.') if result % 1 else "{:.0f}".format(result)
                            self.current_result = self.convert_from_english(result_str)
                            self.save_calculation(original_input, self.convert_from_english(result_str))
                            self.current_input = ""
                            return
                        except (ValueError, ZeroDivisionError):
                            pass

            while english_input and english_input[-1] in ['+', '-', '×', '÷', '*', '/']:
                english_input = english_input[:-1]

            if not english_input:
                self.current_result = self.convert_from_english("0")
                self.current_input = ""
                return

            expression = english_input.replace('×', '*').replace('÷', '/')

            try:
                result = eval(expression)
                result_str = "{:.2f}".format(float(result)).rstrip('0').rstrip('.') if result % 1 else "{:.0f}".format(
                    result)

                self.save_calculation(original_input, self.convert_from_english(result_str))
                self.current_result = self.convert_from_english(result_str)
                self.current_input = ""

            except (SyntaxError, ZeroDivisionError, TypeError, NameError):
                self.current_result = self.convert_from_english("Error")
                self.current_input = ""

        except Exception as e:
            print(f"Calculation error: {e}")
            self.current_result = self.convert_from_english("Error")
            self.current_input = ""

    def set_focus(self, field_name):
        self.focused_field = field_name
        if field_name == "input":
            self.ids.input_text.focus = True
            self.ids.result_text.focus = False
        else:
            self.ids.input_text.focus = False
            self.ids.result_text.focus = True

class CalculatorApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"

        sm = ScreenManager(transition=SwapTransition())
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(HelpScreen(name='help_screen'))
        sm.add_widget(LogScreen(name='log_screen'))
        sm.add_widget(KeyboardThemeStyle(name='keyboard_theme_style'))

        Builder.load_file("calculator.kv")
        return sm

    def on_start(self):
        main_screen = self.root.get_screen('main')
        main_screen.update_hint_colors()

    def theme_changer(self):
        self.theme_cls.theme_style = 'Dark' if self.theme_cls.theme_style == 'Light' else 'Light'
        main_screen = self.root.get_screen('main')
        main_screen.update_hint_colors()

    def open_keyboard_theme(self):
        self.root.current = "keyboard_theme_style"

    def play_sound(self):
        sound = SoundLoader.load('assets/sound/click.mp3')
        if sound:
            sound.play()

    def open_help(self):
        self.root.current = "help_screen"

    def return_to_HomeScreen(self):
        self.root.current = "main"
        self.play_sound()

    def open_log(self):
        self.root.current = "log_screen"

if __name__ == "__main__":
    CalculatorApp().run()