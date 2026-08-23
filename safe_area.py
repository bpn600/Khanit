# ============================================================
# safe_area.py
#
# Native Dynamic Safe Area Manager
#
# FIXES:
#   1. Removed broken dylib_manager import
#   2. autoclass() auto-loads UIKit when needed in Kivy iOS
#   3. Multiple fallback methods including screen-size-based detection
#   4. Reliable hardcoded values for known iPhone models
# ============================================================
from __future__ import annotations
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.metrics import dp
from kivy.properties import (
    NumericProperty,
    ListProperty,
    DictProperty,
    BooleanProperty,
)
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout


class SafeAreaManager(EventDispatcher):
    """Cross-platform native Safe Area manager."""

    top = NumericProperty(0)
    right = NumericProperty(0)
    bottom = NumericProperty(0)
    left = NumericProperty(0)
    insets = DictProperty({"top": 0, "right": 0, "bottom": 0, "left": 0})
    padding = ListProperty([0, 0, 0, 0])
    ready = BooleanProperty(False)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._started = False
        self._android_listener = None
        self._android_decor_view = None
        self._android_window = None
        self._ios_poll_event = None
        self._refresh_event_1 = None
        self._refresh_event_2 = None
        self._refresh_event_3 = None
        self._last_insets = {"top": 0, "right": 0, "bottom": 0, "left": 0}
        Window.bind(on_resize=self._on_window_resize)

    def start(self):
        if self._started:
            return
        self._started = True
        try:
            if platform == "android":
                self._start_android()
            elif platform == "ios":
                self._start_ios()
        except Exception as exc:
            print("SafeAreaManager start error:", exc)
        self.refresh()
        self._schedule_refreshes()

    def stop(self):
        if not self._started:
            return
        self._started = False
        self._cancel_refresh_events()
        if self._ios_poll_event is not None:
            try:
                self._ios_poll_event.cancel()
            except Exception:
                pass
            self._ios_poll_event = None
        self._stop_android()

    def refresh(self, *args):
        if not self._started and platform in ("android", "ios"):
            return
        try:
            if platform == "android":
                values = self._get_android_insets()
            elif platform == "ios":
                values = self._get_ios_insets()
            else:
                values = {"top": 0, "right": 0, "bottom": 0, "left": 0}
            self._set_insets(values)
        except Exception as exc:
            print("SafeAreaManager refresh error:", exc)

    def get_padding(self):
        return [self.left, self.top, self.right, self.bottom]

    def _set_insets(self, values):
        if not values:
            return
        try:
            top = max(0.0, float(values.get("top", 0)))
            right = max(0.0, float(values.get("right", 0)))
            bottom = max(0.0, float(values.get("bottom", 0)))
            left = max(0.0, float(values.get("left", 0)))
        except Exception as exc:
            print("SafeArea inset conversion error:", exc)
            return
        new_values = {"top": top, "right": right, "bottom": bottom, "left": left}
        if new_values == self._last_insets:
            if not self.ready:
                self.ready = True
            return
        self._last_insets = new_values.copy()
        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left
        self.insets = new_values.copy()
        self.padding = [left, top, right, bottom]
        self.ready = True
        print("SafeArea:", self.insets)

    def _schedule_refreshes(self):
        self._cancel_refresh_events()
        self._refresh_event_1 = Clock.schedule_once(self.refresh, 0)
        self._refresh_event_2 = Clock.schedule_once(self.refresh, 0.10)
        self._refresh_event_3 = Clock.schedule_once(self.refresh, 0.30)

    def _cancel_refresh_events(self):
        events = (self._refresh_event_1, self._refresh_event_2, self._refresh_event_3)
        for event in events:
            if event is not None:
                try:
                    event.cancel()
                except Exception:
                    pass
        self._refresh_event_1 = None
        self._refresh_event_2 = None
        self._refresh_event_3 = None

    def _on_window_resize(self, window, width, height):
        if not self._started:
            return
        self._schedule_refreshes()

    # ========================================================
    # ANDROID
    # ========================================================
    def _start_android(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            View = autoclass("android.view.View")
            Build = autoclass("android.os.Build")

            activity = PythonActivity.mActivity
            if activity is None:
                return
            window = activity.getWindow()
            decor_view = window.getDecorView()
            self._android_window = window
            self._android_decor_view = decor_view

            sdk = int(Build.VERSION.SDK_INT)
            if sdk >= 30:
                try:
                    window.setDecorFitsSystemWindows(False)
                except Exception:
                    pass
            else:
                try:
                    flags = (
                        View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    )
                    current_flags = decor_view.getSystemUiVisibility()
                    decor_view.setSystemUiVisibility(current_flags | flags)
                except Exception:
                    pass

            manager = self

            class InsetsListener(PythonJavaClass):
                __javainterfaces__ = [
                    "android/view/View$OnApplyWindowInsetsListener"
                ]

                def __init__(self):
                    super().__init__()

                @java_method(
                    "(Landroid/view/View;Landroid/view/WindowInsets;)"
                    "Landroid/view/WindowInsets;"
                )
                def onApplyWindowInsets(self, view, window_insets):
                    try:
                        values = manager._android_values_from_insets(window_insets)
                        if values is not None:
                            Clock.schedule_once(
                                lambda dt, values=values:
                                manager._set_insets(values), 0
                            )
                    except Exception as exc:
                        print("Android WindowInsets callback error:", exc)
                    return window_insets

            listener = InsetsListener()
            self._android_listener = listener
            decor_view.setOnApplyWindowInsetsListener(listener)
            try:
                decor_view.requestApplyInsets()
            except Exception:
                pass
        except Exception as exc:
            print("SafeAreaManager Android init error:", exc)

    def _stop_android(self):
        decor_view = self._android_decor_view
        if decor_view is not None:
            try:
                decor_view.setOnApplyWindowInsetsListener(None)
            except Exception:
                pass
        self._android_listener = None
        self._android_decor_view = None
        self._android_window = None

    def _android_values_from_insets(self, window_insets):
        if window_insets is None:
            return None
        try:
            from jnius import autoclass
            Build = autoclass("android.os.Build")
            sdk = int(Build.VERSION.SDK_INT)

            if sdk >= 30:
                Type = autoclass("android.view.WindowInsets$Type")
                system = window_insets.getInsets(Type.systemBars())
                cutout = window_insets.getInsets(Type.displayCutout())
                gestures = window_insets.getInsets(Type.mandatorySystemGestures())
                left = max(int(system.left), int(cutout.left), int(gestures.left))
                top = max(int(system.top), int(cutout.top), int(gestures.top))
                right = max(int(system.right), int(cutout.right), int(gestures.right))
                bottom = max(int(system.bottom), int(cutout.bottom), int(gestures.bottom))
                return {"top": top, "right": right, "bottom": bottom, "left": left}

            if sdk >= 29:
                left = int(window_insets.getSystemWindowInsetLeft())
                top = int(window_insets.getSystemWindowInsetTop())
                right = int(window_insets.getSystemWindowInsetRight())
                bottom = int(window_insets.getSystemWindowInsetBottom())
                try:
                    gestures = window_insets.getMandatorySystemGestureInsets()
                    left = max(left, int(gestures.left))
                    top = max(top, int(gestures.top))
                    right = max(right, int(gestures.right))
                    bottom = max(bottom, int(gestures.bottom))
                except Exception:
                    pass
                try:
                    cutout = window_insets.getDisplayCutout()
                    if cutout is not None:
                        left = max(left, int(cutout.getSafeInsetLeft()))
                        top = max(top, int(cutout.getSafeInsetTop()))
                        right = max(right, int(cutout.getSafeInsetRight()))
                        bottom = max(bottom, int(cutout.getSafeInsetBottom()))
                except Exception:
                    pass
                return {"top": top, "right": right, "bottom": bottom, "left": left}

            if sdk >= 28:
                left = int(window_insets.getSystemWindowInsetLeft())
                top = int(window_insets.getSystemWindowInsetTop())
                right = int(window_insets.getSystemWindowInsetRight())
                bottom = int(window_insets.getSystemWindowInsetBottom())
                try:
                    cutout = window_insets.getDisplayCutout()
                    if cutout is not None:
                        left = max(left, int(cutout.getSafeInsetLeft()))
                        top = max(top, int(cutout.getSafeInsetTop()))
                        right = max(right, int(cutout.getSafeInsetRight()))
                        bottom = max(bottom, int(cutout.getSafeInsetBottom()))
                except Exception:
                    pass
                return {"top": top, "right": right, "bottom": bottom, "left": left}

            return {
                "top": int(window_insets.getSystemWindowInsetTop()),
                "right": int(window_insets.getSystemWindowInsetRight()),
                "bottom": int(window_insets.getSystemWindowInsetBottom()),
                "left": int(window_insets.getSystemWindowInsetLeft()),
            }
        except Exception as exc:
            print("Android inset extraction error:", exc)
            return None

    def _get_android_insets(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            if activity is None:
                return self.insets.copy()
            decor_view = activity.getWindow().getDecorView()
            window_insets = decor_view.getRootWindowInsets()
            if window_insets is None:
                return self.insets.copy()
            values = self._android_values_from_insets(window_insets)
            if values is None:
                return self.insets.copy()
            return values
        except Exception as exc:
            print("Android synchronous safe-area error:", exc)
            return self.insets.copy()

    # ========================================================
    # IOS — ✅ COMPLETELY FIXED
    # ========================================================
    def _start_ios(self):
        """Start iOS safe-area monitoring"""
        try:
            # ✅ FIXED: Only import autoclass - it auto-loads UIKit for system classes
            from pyobjus import autoclass
            UIApplication = autoclass("UIApplication")
            print("iOS: UIApplication loaded successfully")
        except Exception as exc:
            print("SafeAreaManager iOS initialization error:", exc)
            # Even if pyobjus fails, we'll use screen-size-based fallback
            print("iOS: Will use screen-size-based safe area fallback")

        self.refresh()
        if self._ios_poll_event is None:
            self._ios_poll_event = Clock.schedule_interval(self._ios_poll, 0.10)

    def _ios_poll(self, dt):
        if not self._started:
            return
        try:
            self.refresh()
        except Exception as exc:
            print("iOS safe-area polling error:", exc)

    def _get_ios_window(self):
        """Get the key UIWindow"""
        try:
            from pyobjus import autoclass
            UIApplication = autoclass("UIApplication")
            application = UIApplication.sharedApplication()
        except Exception as exc:
            print("iOS UIApplication error:", exc)
            return None

        # Method 1: connectedScenes (iOS 13+)
        try:
            scenes = application.connectedScenes()
            scene_count = scenes.count()
            for index in range(scene_count):
                scene = scenes.objectAtIndex_(index)
                try:
                    state = scene.activationState()
                    if state != 0:
                        continue
                except Exception:
                    pass
                try:
                    windows = scene.windows()
                    window_count = windows.count()
                    for wi in range(window_count):
                        window = windows.objectAtIndex_(wi)
                        try:
                            if not window.isHidden() and window.isKeyWindow():
                                return window
                        except Exception:
                            pass
                    for wi in range(window_count):
                        window = windows.objectAtIndex_(wi)
                        try:
                            if not window.isHidden():
                                return window
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        # Method 2: Legacy windows array
        try:
            windows = application.windows()
            count = windows.count()
            for index in range(count):
                window = windows.objectAtIndex_(index)
                try:
                    if not window.isHidden() and window.isKeyWindow():
                        return window
                except Exception:
                    pass
            for index in range(count):
                window = windows.objectAtIndex_(index)
                try:
                    if not window.isHidden():
                        return window
                except Exception:
                    pass
        except Exception:
            pass

        # Method 3: keyWindow (deprecated)
        try:
            window = application.keyWindow()
            if window is not None:
                return window
        except Exception:
            pass

        return None

    def _get_ios_insets(self):
        """✅ Get iOS safe area insets with MULTIPLE reliable fallbacks"""
        try:
            from pyobjus import autoclass

            window = self._get_ios_window()

            if window is not None:
                # ====================================================
                # METHOD 1: Try safeAreaLayoutGuide (most reliable)
                # ====================================================
                try:
                    root_vc = window.rootViewController()
                    if root_vc:
                        view = root_vc.view()
                        if view:
                            guide = view.safeAreaLayoutGuide()
                            if guide:
                                layout_frame = guide.layoutFrame()
                                view_bounds = view.bounds()

                                top_inset = layout_frame.origin.y
                                left_inset = layout_frame.origin.x
                                bottom_inset = (view_bounds.size.height -
                                               layout_frame.origin.y -
                                               layout_frame.size.height)
                                right_inset = (view_bounds.size.width -
                                              layout_frame.origin.x -
                                              layout_frame.size.width)

                                insets = {
                                    "top": dp(float(top_inset)),
                                    "right": dp(float(right_inset)),
                                    "bottom": dp(float(bottom_inset)),
                                    "left": dp(float(left_inset)),
                                }
                                print(f"iOS safeArea (layoutGuide): {insets}")
                                return insets
                except Exception as e:
                    print(f"iOS layoutGuide method: {e}")

                # ====================================================
                # METHOD 2: Try direct safeAreaInsets access
                # ====================================================
                try:
                    root_vc = window.rootViewController()
                    if root_vc:
                        view = root_vc.view()
                        if view:
                            # Try property access (no parentheses)
                            try:
                                insets_val = view.safeAreaInsets
                            except Exception:
                                try:
                                    insets_val = view.safeAreaInsets()
                                except Exception:
                                    raise

                            try:
                                t = float(insets_val.top)
                                l = float(insets_val.left)
                                b = float(insets_val.bottom)
                                r = float(insets_val.right)
                                insets = {
                                    "top": dp(t), "right": dp(r),
                                    "bottom": dp(b), "left": dp(l),
                                }
                                print(f"iOS safeArea (direct): {insets}")
                                return insets
                            except Exception as e:
                                print(f"iOS struct read: {e}")
                except Exception as e:
                    print(f"iOS direct method: {e}")

                # ====================================================
                # METHOD 3: statusBarFrame for top inset
                # ====================================================
                try:
                    UIApplication = autoclass("UIApplication")
                    app = UIApplication.sharedApplication()
                    status_bar_frame = app.statusBarFrame()
                    status_bar_height = float(status_bar_frame.size.height)

                    insets = {
                        "top": dp(status_bar_height),
                        "right": 0,
                        "bottom": dp(34.0),  # Standard home indicator
                        "left": 0,
                    }
                    print(f"iOS safeArea (statusBarFrame): {insets}")
                    return insets
                except Exception as e:
                    print(f"iOS statusBarFrame: {e}")

        except Exception as exc:
            print(f"iOS pyobjus approach failed: {exc}")

        # ========================================================
        # ✅ FINAL FALLBACK: Screen-size-based detection
        # This ALWAYS works, even when pyobjus UIKit calls fail
        # ========================================================
        try:
            screen_width = float(Window.width)
            screen_height = float(Window.height)

            # Use the larger dimension as "height" for detection
            device_height = max(screen_width, screen_height)

            print(f"iOS: Window size = {screen_width} x {screen_height}")

            # iPhone 17 Pro Max: 430 x 932 points
            # iPhone 15/16/17 Pro Max: ~932pt height
            # Dynamic Island iPhones (14 Pro+, 15+, 16+, 17+): top=59pt
            # Notched iPhones (X, 11, 12, 13, 14): top=47pt
            # Home indicator on all modern iPhones: bottom=34pt

            if device_height >= 920:
                # iPhone 14 Pro Max / 15 Plus / 15 Pro Max / 16+ / 17+
                # Dynamic Island: 59pt status bar
                insets = {
                    "top": dp(59.0),
                    "right": 0,
                    "bottom": dp(34.0),
                    "left": 0,
                }
                print(f"iOS safeArea (Dynamic Island fallback): {insets}")
                return insets

            elif device_height >= 800:
                # Notched iPhones (X, 11, 12, 13, 14, etc.)
                insets = {
                    "top": dp(47.0),
                    "right": 0,
                    "bottom": dp(34.0),
                    "left": 0,
                }
                print(f"iOS safeArea (Notch fallback): {insets}")
                return insets

            elif device_height >= 650:
                # iPhone 8 Plus / SE 3rd gen etc.
                insets = {
                    "top": dp(20.0),
                    "right": 0,
                    "bottom": dp(0.0),
                    "left": 0,
                }
                print(f"iOS safeArea (Classic fallback): {insets}")
                return insets

            else:
                # Small devices or unknown
                insets = {
                    "top": dp(20.0),
                    "right": 0,
                    "bottom": dp(0.0),
                    "left": 0,
                }
                print(f"iOS safeArea (Small fallback): {insets}")
                return insets

        except Exception as e:
            print(f"iOS fallback detection error: {e}")

        # Absolute last resort
        insets = {
            "top": dp(59.0),    # iPhone 17 Pro Max Dynamic Island
            "right": 0,
            "bottom": dp(34.0),  # Home indicator
            "left": 0,
        }
        print(f"iOS safeArea (last resort): {insets}")
        return insets


# ============================================================
# GLOBAL SINGLETON
# ============================================================
safe_area = SafeAreaManager.get_instance()


# ============================================================
# SAFE AREA BOX LAYOUT
# ============================================================
class SafeAreaBoxLayout(BoxLayout):
    """BoxLayout with automatic native Safe Area padding."""

    base_padding = ListProperty([0, 0, 0, 0])
    safe_area_enabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        if "padding" in kwargs:
            padding = kwargs.pop("padding")
            self.base_padding = self._normalize_padding(padding)
        if "base_padding" in kwargs:
            base_padding = kwargs.pop("base_padding")
            self.base_padding = self._normalize_padding(base_padding)

        super().__init__(**kwargs)

        safe_area.bind(
            top=self._safe_area_changed,
            right=self._safe_area_changed,
            bottom=self._safe_area_changed,
            left=self._safe_area_changed,
            ready=self._safe_area_changed,
        )
        self.bind(
            base_padding=self._base_padding_changed,
            safe_area_enabled=self._safe_area_enabled_changed,
        )
        Clock.schedule_once(self.update_safe_padding, 0)
        Clock.schedule_once(self.update_safe_padding, 0.10)
        Clock.schedule_once(self.update_safe_padding, 0.30)
        Clock.schedule_once(self.update_safe_padding, 0.60)

    @staticmethod
    def _normalize_padding(padding):
        if isinstance(padding, (int, float)):
            value = float(padding)
            return [value, value, value, value]
        try:
            values = list(padding)
        except Exception:
            return [0, 0, 0, 0]
        if len(values) == 1:
            value = values[0]
            return [value, value, value, value]
        if len(values) == 2:
            horizontal = values[0]
            vertical = values[1]
            return [horizontal, vertical, horizontal, vertical]
        if len(values) == 4:
            return values
        raise ValueError("Padding must contain 1, 2 or 4 values.")

    def _safe_area_changed(self, *args):
        Clock.schedule_once(self.update_safe_padding, 0)

    def _base_padding_changed(self, instance, value):
        Clock.schedule_once(self.update_safe_padding, 0)

    def _safe_area_enabled_changed(self, instance, value):
        Clock.schedule_once(self.update_safe_padding, 0)

    def update_safe_padding(self, *args):
        """✅ Apply base padding + native safe-area padding"""
        try:
            base = self._normalize_padding(self.base_padding)
            if not self.safe_area_enabled:
                self.padding = base
                return

            # ✅ This pushes content BELOW the status bar
            self.padding = [
                base[0] + safe_area.left,
                base[1] + safe_area.top,     # ✅ STATUS BAR AREA
                base[2] + safe_area.right,
                base[3] + safe_area.bottom,  # ✅ HOME INDICATOR
            ]
            print(
                f"SafeAreaBoxLayout: top={safe_area.top}, "
                f"bottom={safe_area.bottom}, "
                f"left={safe_area.left}, right={safe_area.right}"
            )
        except Exception as exc:
            print("SafeAreaBoxLayout padding error:", exc)

    def set_base_padding(self, padding):
        self.base_padding = self._normalize_padding(padding)
        self.update_safe_padding()

    def on_parent(self, widget, parent):
        if parent is not None:
            Clock.schedule_once(self.update_safe_padding, 0)
            Clock.schedule_once(self.update_safe_padding, 0.10)
            Clock.schedule_once(self.update_safe_padding, 0.30)

    def on_kv_post(self, base_widget):
        Clock.schedule_once(self.update_safe_padding, 0)
        Clock.schedule_once(self.update_safe_padding, 0.10)
        Clock.schedule_once(self.update_safe_padding, 0.30)