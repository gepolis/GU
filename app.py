import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

# Если запущено на Android — импортируем Android-специфичные модули
if platform == 'android':
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

class MainApp(App):
    def build(self):
        return BoxLayout()  # Пустой макет (WebView запустится в on_start)

    def on_start(self):
        if platform == 'android':
            self.setup_android_webview()
        else:
            self.setup_pc_webview()

    # WebView для Android (работает только на Android)
    if platform == 'android':
        @run_on_ui_thread
        def setup_android_webview(self):
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity

            webview = WebView(activity)
            webview.getSettings().setJavaScriptEnabled(True)
            webview.setWebViewClient(WebViewClient())
            webview.loadUrl("http://127.0.0.1:5000/")
            activity.setContentView(webview)

    # WebView для ПК (Windows/Linux/macOS)
    def setup_pc_webview(self):
        import webview
        webview.create_window(
            "Мои Госуслуги",
            "http://127.0.0.1:5000/",
            width=1024,
            height=768,
            resizable=True
        )
        webview.start()

if __name__ == '__main__':
    MainApp().run()