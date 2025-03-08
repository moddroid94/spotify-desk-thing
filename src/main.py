import time
import flet as ft
import spotipy
from functools import partial

from spotipy.oauth2 import SpotifyOAuth
from apscheduler.schedulers.background import BackgroundScheduler
import credentials
from Pylette import extract_colors


scope = "user-library-read, user-read-playback-state, user-modify-playback-state, user-read-currently-playing, user-read-playback-position, user-read-recently-played"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=credentials.SPOTIPY_CLIENT_ID,
        client_secret=credentials.SPOTIPY_CLIENT_SECRET,
        redirect_uri=credentials.SPOTIPY_REDIRECT_URI,
        scope=scope,
    )
)


class SpotifyController:
    def __init__(self):
        devices = sp.devices()
        for device in devices["devices"]:
            if device["name"] == "SAMWIN":
                self.deviceid = device["id"]
                self.volume = device["volume_percent"]

        self.playback_state = sp.current_playback()
        self.currently_playing = sp.currently_playing()
        self.queue = None

        if self.playback_state is not None:
            self.trackimage = self.playback_state["item"]["album"]["images"][1]["url"]
            self.trackartist = ""
            for i in self.playback_state["item"]["artists"]:
                self.trackartist = self.trackartist + i["name"] + ", "
            self.trackartist = self.trackartist[0:-2]
            self.trackname = self.playback_state["item"]["name"]
            self.trackalbum = self.playback_state["item"]["album"]["name"]
            self.is_playing = self.playback_state["is_playing"]
            self.duration = self.playback_state["item"]["duration_ms"] / 1000
            if self.currently_playing is not None:
                self.progress = self.currently_playing["progress_ms"] / 1000
            else:
                self.progress = 0
        else:
            self.playback_state = sp.current_user_recently_played(limit=1)
            self.trackimage = self.playback_state["items"][0]["track"]["album"][
                "images"
            ][1]["url"]
            self.trackartist = ""
            for i in self.playback_state["items"][0]["track"]["artists"]:
                self.trackartist = self.trackartist + i["name"] + ", "
            self.trackartist = self.trackartist[0:-2]
            self.trackname = self.playback_state["items"][0]["track"]["name"]
            self.trackalbum = self.playback_state["items"][0]["track"]["album"]["name"]
            self.duration = (
                self.playback_state["items"][0]["track"]["duration_ms"] / 1000
            )
            self.progress = 0
            self.is_playing = False

    def update_playback(self):
        self.playback_state = sp.current_playback()
        # print(self.playback_state)
        if self.playback_state is not None:
            self.trackimage = self.playback_state["item"]["album"]["images"][1]["url"]
            self.trackartist = ""
            for i in self.playback_state["item"]["artists"]:
                self.trackartist = self.trackartist + i["name"] + ", "
            self.trackartist = self.trackartist[0:-2]
            self.trackname = self.playback_state["item"]["name"]
            self.trackalbum = self.playback_state["item"]["album"]["name"]
            self.is_playing = self.playback_state["is_playing"]
            try:
                self.context = self.playback_state["context"]["uri"]
            except:
                self.context = None
        else:
            self.playback_state = sp.current_user_recently_played(limit=1)
            self.trackimage = self.playback_state["items"][0]["track"]["album"][
                "images"
            ][1]["url"]
            self.trackartist = ""
            for i in self.playback_state["items"][0]["track"]["artists"]:
                self.trackartist = self.trackartist + i["name"] + ", "
            self.trackartist = self.trackartist[0:-2]
            self.trackname = self.playback_state["items"][0]["track"]["name"]
            self.trackalbum = self.playback_state["items"][0]["track"]["album"]["name"]
            self.is_playing = False

    def update_state(self):
        if self.is_playing == True:
            self.currently_playing = sp.currently_playing()
            self.duration = self.currently_playing["item"]["duration_ms"] / 1000
            self.progress = self.currently_playing["progress_ms"] / 1000
            devices = sp.devices()
            for device in devices["devices"]:
                if device["name"] == "SAMWIN":
                    self.deviceid = device["id"]
                    self.volume = device["volume_percent"]

    def next_track(self):
        sp.next_track()
        time.sleep(0.4)
        self.update_playback()

    def previous_track(self):
        sp.previous_track()
        time.sleep(0.4)
        self.update_playback()

    def seek_track(self, seek_ms):
        sp.seek_track(seek_ms, self.deviceid)
        time.sleep(0.4)
        self.update_state()

    def play_pause(self):
        if self.is_playing == True:
            sp.pause_playback(self.deviceid)
        else:
            sp.start_playback(self.deviceid)
        time.sleep(0.3)
        self.update_playback()

    def update_volume(self, volume):
        sp.volume(volume, self.deviceid)

    def get_queue(self):
        try:
            sp.shuffle(False, self.deviceid)
        except Exception as e:
            print(e)
        time.sleep(0.5)
        que = sp.queue()
        time.sleep(0.2)
        self.queue = que["queue"]

    def play_trackcontexturi(self, contexturi, trackuri):
        offset = {"uri": trackuri}
        sp.start_playback(self.deviceid, context_uri=contexturi, offset=offset)
        self.update_playback()
        time.sleep(0.3)

    def play_trackuri(self, trackuri):
        sp.start_playback(self.deviceid, uris=trackuri)
        self.update_playback()
        time.sleep(0.3)


spc = SpotifyController()


def main(page: ft.Page):
    scheduler = BackgroundScheduler()
    scheduler.start()
    job = None

    def long_running_poll():
        try:
            scheduler.add_job(
                func=long_poll_check,
                trigger="interval",
                seconds=5,
                id="longpoll",
                max_instances=1,
            )
        except Exception as e:
            scheduler.resume_job(job_id="longpoll", jobstore="default")

    def remove_long_poll():
        try:
            scheduler.remove_job(job_id="longpoll", jobstore="default")
        except Exception as e:
            pass

    def long_poll_check():
        spc.update_playback()
        update_fields()
        page.update()
        if spc.is_playing == True:
            start_refresh()
            remove_long_poll()

    def start_refresh():
        try:
            scheduler.add_job(
                func=timer_refresh,
                trigger="interval",
                seconds=1,
                id="timer",
                max_instances=1,
            )

        except Exception as e:
            scheduler.resume_job(job_id="timer", jobstore="default")

    def stop_timer():
        try:
            scheduler.remove_job(job_id="timer", jobstore="default")
        except Exception as e:
            pass

    def extract_pallete():
        palette = extract_colors(
            image=spc.trackimage, palette_size=5, sort_mode="frequency", mode="KM"
        )
        most_common_color = palette[0].rgb
        rgbval = (
            most_common_color[0],
            most_common_color[1],
            most_common_color[2],
        )
        least_common_color = palette[1].rgb
        collum = palette[1].luminance
        if collum > 100:
            nexttrack.icon_color = "#000000"
            prevtrack.icon_color = "#000000"
        else:
            nexttrack.icon_color = "#ffffff"
            prevtrack.icon_color = "#ffffff"
        rgbval2 = (
            least_common_color[0],
            least_common_color[1],
            least_common_color[2],
        )
        rgbcol = "#60%02x%02x%02x" % (rgbval)
        rgbcol2 = "#%02x%02x%02x" % (rgbval2)
        page.views[-1].bgcolor = rgbcol
        nexttrack.style.bgcolor = rgbcol2
        prevtrack.style.bgcolor = rgbcol2

    def make_queue():
        spc.get_queue()
        if spc.queue is not None:
            queuelist = []
            for i in spc.queue:
                artists = ""
                for x in i["artists"]:
                    artists = artists + x["name"] + ", "
                artists = artists[0:-2]
                queuelist.append(
                    ft.ListTile(
                        leading=ft.Image(
                            src=i["album"]["images"][2]["url"],
                            width=32,
                            height=32,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=ft.border_radius.all(5),
                        ),
                        title=ft.Text(i["name"]),
                        subtitle=ft.Text(artists),
                        trailing=ft.IconButton(ft.Icons.PLAY_ARROW),
                        on_click=change_track,
                        data=[spc.context, i["uri"]],
                    )
                )
            bs.content.content = ft.Container(
                width=600,
                content=ft.Column(controls=queuelist, spacing=0, scroll=True),
                padding=ft.padding.symmetric(vertical=0, horizontal=0),
                margin=ft.margin.symmetric(horizontal=2, vertical=2),
            )

    def change_track(e):
        spc.play_trackcontexturi(e.control.data[0], e.control.data[1])
        time.sleep(0.2)
        page.close(bs)
        make_queue()
        update_fields()
        page.update()
        start_refresh()

    def timer_refresh():
        spc.update_playback()
        spc.update_state()
        update_fields()
        page.update()
        if spc.is_playing == False:
            stop_timer()
            long_running_poll()

    def play_pause(e):
        spc.play_pause()
        make_queue()
        update_fields()
        if spc.is_playing == True:
            start_refresh()
            remove_long_poll()
        else:
            long_running_poll()
            stop_timer()
        page.update()

    def previous_track(e):
        spc.previous_track()
        make_queue()
        update_fields()
        page.update()

    def next_track(e):
        spc.next_track()
        make_queue()
        update_fields()
        page.update()

    def update_fields():
        if spc.is_playing == True:
            tticonbtn.icon = ft.Icons.PAUSE
            tticonbtn.opacity = 0
            ttimg.opacity = 1
            ttimg.color = None
            ttimg.color_blend_mode = ft.BlendMode.COLOR
        else:
            ttimg.color = ft.Colors.BLACK
            ttimg.color_blend_mode = ft.BlendMode.SATURATION
            ttimg.opacity = 0.5
            tticonbtn.icon = ft.Icons.PLAY_ARROW
            tticonbtn.opacity = 0.8
        ttimg.src = spc.trackimage
        tname.value = spc.trackname
        tartist.value = "### **" + spc.trackartist + "**"
        talbum.value = spc.trackalbum
        ttime.content.value = int(spc.progress)
        ttime.content.max = int(spc.duration)
        tdur.value = time.strftime("%M:%S", time.gmtime(spc.duration))
        t0.value = time.strftime("%M:%S", time.gmtime(spc.progress))
        tvolume.value = spc.volume
        extract_pallete()

    def seek_track(e):
        spc.seek_track(int(e.control.value * 1000))
        ttime.content.value = e.control.value

    def update_volume(e):
        spc.update_volume(int(e.control.value))
        tvolume.update()

    tvolume = ft.Slider(min=0, max=100, value=spc.volume, on_change_end=update_volume)

    ttime = ft.Container(
        content=ft.Slider(
            value=int(spc.progress),
            min=0,
            max=int(spc.duration),
            on_change_end=seek_track,
            width=250,
        )
    )
    tdur = ft.Text(
        time.strftime("%M:%S", time.gmtime(spc.duration)),
        size=12,
        color=ft.Colors.WHITE,
    )

    t0 = ft.Text(
        time.strftime("%M:%S", time.gmtime(spc.progress)),
        size=12,
        color=ft.Colors.WHITE,
    )
    ttimg = ft.Image(
        src=spc.trackimage,
        width=200,
        height=200,
        fit=ft.ImageFit.CONTAIN,
        border_radius=ft.border_radius.all(8),
    )
    tticonbtn = ft.IconButton(
        ft.Icons.PLAY_ARROW,
        icon_size=128,
        icon_color=ft.Colors.WHITE,
        opacity=0.8,
        on_click=play_pause,
    )
    timg = ft.Container(
        content=ft.Stack(
            [
                ttimg,
                ft.Container(
                    content=tticonbtn,
                    alignment=ft.alignment.center,
                    width=200,
                    height=200,
                    on_click=play_pause,
                ),
            ],
            alignment=ft.alignment.center,
        ),
    )
    tname = ft.Text(
        spc.trackname,
        size=24,
        weight=ft.FontWeight.BOLD,
        # overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
        max_lines=2,
    )
    tartist = ft.Markdown("### **" + spc.trackartist + "**")
    talbum = ft.Text(spc.trackalbum)

    prevtrack = ft.IconButton(
        icon=ft.Icons.SKIP_PREVIOUS_ROUNDED,
        icon_size=64,
        icon_color=ft.Colors.WHITE,
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLACK),
        on_click=previous_track,
    )
    nexttrack = ft.IconButton(
        icon=ft.Icons.SKIP_NEXT_ROUNDED,
        icon_size=64,
        icon_color=ft.Colors.WHITE,
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLACK),
        on_click=next_track,
    )
    play_fab = ft.FloatingActionButton(
        icon=ft.Icons.PLAY_ARROW if not spc.is_playing else ft.Icons.PAUSE,
        on_click=play_pause,
        scale=2,
    )
    trackinfocol = ft.Container(
        ft.Column(
            [
                ft.Container(timg, alignment=ft.alignment.center),
                ft.Container(
                    ft.Row(
                        [t0, ttime, tdur],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    alignment=ft.alignment.center,
                ),
                ft.Container(tname),
                ft.Container(tartist),
                ft.Container(talbum),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=2,
    )
    prevtrackcol = ft.Container(
        ft.Column([ft.Container(prevtrack)]),
        alignment=ft.alignment.center,
        expand=1,
    )
    nexttrackcol = ft.Container(
        ft.Column([ft.Container(nexttrack)]),
        alignment=ft.alignment.center,
        expand=1,
    )

    bs = ft.BottomSheet(
        enable_drag=True,
        dismissible=True,
        is_scroll_controlled=True,
        show_drag_handle=True,
        content=ft.Container(padding=20, width=780, content=None),
    )
    page.views.append(
        ft.View(
            "/",
            [
                ft.Container(
                    content=ft.Row(
                        [
                            prevtrackcol,
                            trackinfocol,
                            nexttrackcol,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    ),
                    alignment=ft.alignment.center,
                    width=800,
                ),
                ft.Container(
                    ft.Row(
                        [
                            ft.Container(tvolume),
                            ft.ElevatedButton(
                                "Queue",
                                on_click=lambda _: page.open(bs),
                                icon=ft.Icons.ARROW_UPWARD,
                                style=ft.ButtonStyle(
                                    icon_size=28,
                                    text_style=ft.TextStyle(size=24),
                                    padding=ft.padding.symmetric(horizontal=15),
                                ),
                                height=60,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ),
            ],
            bgcolor="#000000",
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        )
    )

    page.window.max_height = 480
    page.window.max_width = 800
    page.window.resizable = False
    page.window.maximized = True
    page.window.full_screen = True
    page.window.title_bar_hidden = True
    page.theme = ft.Theme(
        page_transitions=ft.PageTransitionsTheme(windows=ft.PageTransitionTheme.NONE),
        use_material3=True,
    )
    if spc.is_playing == True:
        start_refresh()
        make_queue()
    page.go("/")


ft.app(main)
