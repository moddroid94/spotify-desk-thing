import time
import flet as ft
import spotipy
from functools import partial

from spotipy.oauth2 import SpotifyOAuth
from apscheduler.schedulers.background import BackgroundScheduler
import credentials
from Pylette import extract_colors

import interfaces

scope = "user-library-read, user-read-playback-state, user-modify-playback-state, user-read-currently-playing, user-read-playback-position, user-read-recently-played"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=credentials.SPOTIPY_CLIENT_ID,
        client_secret=credentials.SPOTIPY_CLIENT_SECRET,
        redirect_uri=credentials.SPOTIPY_REDIRECT_URI,
        scope=scope,
    )
)

pstate = interfaces.CurrentState()


class SpotifyController:
    def __init__(self):
        devices = sp.devices()
        for device in devices["devices"]:
            dev = interfaces.DeviceItem()
            dev.name = device["name"]
            dev.id = device["id"]
            dev.volume = device["volume_percent"]
            pstate.statedevices[dev.id] = dev

        self.update_playback()

    def update_playback(self):
        self.playback_state = sp.current_playback()

        if self.playback_state is not None:
            pstate.stateisplaying = self.playback_state["is_playing"]
            pstate.trackimage = self.playback_state["item"]["album"]["images"][1]["url"]
            pstate.trackartists = ""
            for i in self.playback_state["item"]["artists"]:
                pstate.trackartists = pstate.trackartists + i["name"] + ", "
            pstate.trackartists = pstate.trackartists[0:-2]
            pstate.trackname = self.playback_state["item"]["name"]
            pstate.trackalbum = self.playback_state["item"]["album"]["name"]
            pstate.trackduration = int(
                self.playback_state["item"]["duration_ms"] / 1000
            )
            pstate.stateisplaying = self.playback_state["is_playing"]
            if pstate.stateisplaying == True:
                pstate.playercontexturi = self.playback_state["context"]["uri"]
                pstate.stateprogress = int(self.playback_state["progress_ms"] / 1000)
                self.get_queue()
                pstate.stateshuffle = self.playback_state["shuffle_state"]
                self.update_device()
                self.update_progress()
        else:
            self.playback_state = sp.current_user_recently_played(limit=1)
            pstate.trackimage = self.playback_state["items"][0]["track"]["album"][
                "images"
            ][1]["url"]
            pstate.trackartists = ""
            for i in self.playback_state["items"][0]["track"]["artists"]:
                pstate.trackartists = pstate.trackartists + i["name"] + ", "
            pstate.trackartists = pstate.trackartists[0:-2]
            pstate.trackname = self.playback_state["items"][0]["track"]["name"]
            pstate.trackalbum = self.playback_state["items"][0]["track"]["album"][
                "name"
            ]
            pstate.trackduration = int(
                self.playback_state["items"][0]["track"]["duration_ms"] / 1000
            )
            pstate.stateprogress = 0
            pstate.stateisplaying = False
            for deviceid, device in pstate.statedevices.items():
                if device["name"] == "SAMWIN":
                    pstate.playerdeviceid = device.id

    def update_progress(self):
        if pstate.stateisplaying == True:
            self.currently_playing = sp.currently_playing()
            self.progress = self.currently_playing["progress_ms"] / 1000

    def update_device(self):
        devices = sp.devices()

        for device in devices["devices"]:
            if device["name"] == "SAMWIN":
                pstate.playerdeviceid = device["id"]
                pstate.statevolume = device["volume_percent"]

    def next_track(self):
        sp.next_track()

        self.update_playback()

    def previous_track(self):
        sp.previous_track()

        self.update_playback()

    def seek_track(self, seek_ms):
        sp.seek_track(seek_ms, pstate.playerdeviceid)

        self.update_progress()

    def play_pause(self):
        if pstate.stateisplaying == True:
            sp.pause_playback(pstate.playerdeviceid)
        else:
            sp.start_playback(pstate.playerdeviceid)

        self.update_playback()

    def update_volume(self, volume):
        sp.volume(volume, pstate.playerdeviceid)

    def get_queue(self):
        if pstate.stateshuffle != True:
            sp.shuffle(False, pstate.playerdeviceid)
        else:
            sp.shuffle(True, pstate.playerdeviceid)

        que = sp.queue()

        pstate.playerqueue = que["queue"]

    def play_trackcontexturi(self, contexturi, trackuri):
        offset = {"uri": trackuri}
        sp.start_playback(pstate.playerdeviceid, context_uri=contexturi, offset=offset)
        self.update_playback()

    def play_trackuri(self, trackuri):
        sp.start_playback(pstate.playerdeviceid, uris=trackuri)
        self.update_playback()


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
        if pstate.stateisplaying == True:
            start_refresh()
            remove_long_poll()

    def start_refresh():
        job = scheduler.get_job("timer")
        if job is None:
            scheduler.add_job(
                func=timer_refresh,
                trigger="interval",
                seconds=1,
                id="timer",
                max_instances=1,
            )
        else:
            if job.next_run_time is None:
                scheduler.resume_job(job_id="timer", jobstore="default")

    def stop_timer():
        job = scheduler.get_job("timer")
        if job is not None:
            scheduler.remove_job(job_id="timer", jobstore="default")

    def extract_pallete():
        palette = extract_colors(
            image=pstate.trackimage, palette_size=5, sort_mode="frequency", mode="KM"
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
        context = (
            pstate.playercontexturi if pstate.playercontexturi is not None else False
        )
        if pstate.playerqueue is not None:
            queuelist = []
            for i in pstate.playerqueue:
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
                        data=[context, i["uri"]],
                    )
                )
            bs.content.content = ft.Container(
                width=600,
                content=ft.Column(controls=queuelist, spacing=0, scroll=True),
                padding=ft.padding.symmetric(vertical=0, horizontal=0),
                margin=ft.margin.symmetric(horizontal=2, vertical=2),
            )

    def change_track(e):
        if e.control.data[0] == False:
            spc.play_trackuri([e.control.data[1]])
        spc.play_trackcontexturi(e.control.data[0], e.control.data[1])
        time.sleep(0.2)
        page.close(bs)
        make_queue()
        update_fields()
        page.update()
        start_refresh()

    def timer_refresh():
        spc.update_playback()
        update_fields()
        page.update()
        if pstate.stateisplaying == False:
            stop_timer()
            long_running_poll()

    def play_pause(e):
        spc.play_pause()
        make_queue()
        update_fields()
        page.update()
        if pstate.stateisplaying == True:
            start_refresh()
            remove_long_poll()
        else:
            long_running_poll()
            stop_timer()

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
        if pstate.stateisplaying == True:
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
        ttimg.src = pstate.trackimage
        tname.value = pstate.trackname
        tartist.value = "### **" + pstate.trackartists + "**"
        talbum.value = pstate.trackalbum
        ttime.content.value = int(pstate.stateprogress)
        ttime.content.max = int(pstate.trackduration)
        tdur.value = time.strftime("%M:%S", time.gmtime(pstate.trackduration))
        t0.value = time.strftime("%M:%S", time.gmtime(pstate.stateprogress))
        tvolume.value = pstate.statevolume
        extract_pallete()

    def seek_track(e):
        spc.seek_track(int(e.control.value * 1000))
        ttime.content.value = e.control.value

    def update_volume(e):
        spc.update_volume(int(e.control.value))
        tvolume.value = e.control.data

    tvolume = ft.Slider(
        min=0, max=100, value=pstate.statevolume, on_change_end=update_volume
    )

    ttime = ft.Container(
        content=ft.Slider(
            value=int(pstate.stateprogress),
            min=0,
            max=int(pstate.trackduration),
            on_change_end=seek_track,
            width=250,
        )
    )
    tdur = ft.Text(
        time.strftime("%M:%S", time.gmtime(pstate.trackduration)),
        size=12,
        color=ft.Colors.WHITE,
    )

    t0 = ft.Text(
        time.strftime("%M:%S", time.gmtime(pstate.stateprogress)),
        size=12,
        color=ft.Colors.WHITE,
    )
    ttimg = ft.Image(
        src=pstate.trackimage,
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
        pstate.trackname,
        size=24,
        weight=ft.FontWeight.BOLD,
        # overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
        max_lines=2,
    )
    tartist = ft.Markdown("### **" + pstate.trackartists + "**")
    talbum = ft.Text(pstate.trackalbum)

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
        icon=ft.Icons.PLAY_ARROW if not pstate.stateisplaying else ft.Icons.PAUSE,
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
    if pstate.stateisplaying == True:
        start_refresh()
        remove_long_poll()
        make_queue()
    else:
        long_running_poll()
        stop_timer()
        update_fields()

    page.go("/")


ft.app(main)
