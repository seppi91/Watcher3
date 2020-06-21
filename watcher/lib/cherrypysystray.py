import sys

import cherrypy
from cherrypy.process import plugins
from infi.systray import SysTrayIcon


class SysTrayPlugin(plugins.SimplePlugin):
    """
    CherryPy plugin that creates a system tray icon for Windows.

    Because SysTrayIcon always fires off on_quit, we can't have on_quit
        execute cherrypy.engine.exit() if cherrypy.engine.exit() is what
        triggered SysTrayIcon to close. So conditions are set to only fire
        on_quit when the quit_method == 'men'.

    This way, when the menu option is called, it destroys SysTrayIcon then
        closes cherrypy. Cherrypy will try to close SysTrayIcon by calling
        stop(), so _on_quit() gets reassigned to None.

    If the app is closed by cherrypy (whether catching a kb interrupt or the GUI
        shutdown button), cherrypy stops the plugin by calling stop(). Stop()
        reassigns SysTrayIcon._on_quit to None and calls SysTrayIcon.shutdown().
        SysTrayIcon is then destroyed (twice for reasons I can't figure out),
        then cherrypy finishes up the engine.stop() and engine.exit().

    The chain is as such:

    Trigger == systray menu 'Quit':
    SysTrayIcon._destroy() >
    SysTrayIcon._on_quit() > set SysTrayPlugin.quit_method = 'men'
    cherrypy.engine.exit() >
    SysTrayPlugin.stop()   > does nothing
    sys.exit()

    Trigger == KBInterrupt or GUI Shutdown:
    cherrypy.engine.stop() >
    SysTrayPlugin.stop()   > disable SysTrayIcon._on_quit()
    SysTrayIcon.shutdown() >
    SysTrayIcon._destroy() >
    SysTrayIcon._destroy() >
    cherrypy.engine.exit() >
    sys.exit()

    """

    def __init__(self, bus, icon, name, menu_options, on_quit=lambda: None):
        if not callable(on_quit):
            raise TypeError("on_quit not a callable object.")
        self.on_quit = on_quit

        plugins.SimplePlugin.__init__(self, bus)
        self.systray = SysTrayIcon(icon, name, menu_options, on_quit=self._on_quit)
        self.quit_method = None
        return

    def start(self):
        self.systray.start()
        return

    def stop(self):
        if self.quit_method == "men":
            return
        else:
            self.systray._on_quit = None
            self.systray.shutdown()
            return

    def _on_quit(self, systray):
        self.on_quit()
        self.quit_method = "men"
        cherrypy.engine.exit()
        sys.exit(0)
