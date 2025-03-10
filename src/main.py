import time
import flet as ft
import spotipy
from functools import partial

from spotipy.oauth2 import SpotifyOAuth
from apscheduler.schedulers.background import BackgroundScheduler
import credentials
from Pylette import extract_colors

import stateclass as sc
import constructor as cs

scope = "user-library-read, user-read-playback-state, user-modify-playback-state, user-read-currently-playing, user-read-playback-position, user-read-recently-played, user-read-private, user-read-email, playlist-read-private, playlist-read-collaborative"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=credentials.SPOTIPY_CLIENT_ID,
        client_secret=credentials.SPOTIPY_CLIENT_SECRET,
        redirect_uri=credentials.SPOTIPY_REDIRECT_URI,
        scope=scope,
    )
)

ss = sc.CurrentState()

scheduler = BackgroundScheduler()
scheduler.start()


class SpotifyController:
    def __init__(self):
        self.playback_state = None

        devices = sp.devices()
        ss.userdevices = cs.get_user_devices(devices)
        self.get_user_playlists()
        self.update_playback()

    def get_queue(self):
        queue = sp.queue()
        try:
            que = queue["queue"]
            return que
        except:
            return None

    def get_user_playlists(self):
        me = sp.me()
        useruri = me["uri"]
        savedplaylist = sp.current_user_saved_tracks(limit=50)
        playlistsJSON = sp.current_user_playlists(limit=25)
        tracksdict = cs.get_playlist_items(savedplaylist)
        savedtracks = sc.PlaylistItem(
            name="Liked Songs",
            image="None",
            uri=useruri + ":collection",
            tracks=tracksdict,
        )
        playlistdict: dict[str, sc.PlaylistItem] = {}
        playlistdict[useruri + ":collection"] = savedtracks
        playlistdict.update(cs.get_user_playlists(playlistsJSON))
        ss.userplaylists = playlistdict

    def update_playback(self, progress_only=False, volume_only=False):
        self.playback_state = sp.current_playback()
        if self.playback_state is not None:
            if progress_only:
                ss.playerstate = cs.get_player_state(self.playback_state)
                return
            if volume_only:
                ss.actualdevice = cs.get_current_device(
                    self.playback_state, ss.userdevices
                )
                return
            ss.actualdevice = cs.get_current_device(self.playback_state, ss.userdevices)
            ss.playerstate = cs.get_player_state(self.playback_state)
            ss.actualtrack = cs.get_current_track(self.playback_state)
            ss.actualqueue = cs.get_current_queue(self.get_queue())
        else:
            self.playback_state = sp.current_user_recently_played(limit=1)
            ss.playerstate = sc.PlayerState("")
            ss.actualtrack = cs.get_current_track(
                self.playback_state, from_history=True
            )
            for deviceid, device in ss.userdevices.items():
                ss.actualdevice = device if device.name == "SAMWIN" else None

    def update_device(self, device_name: str | None = None):
        devices = sp.devices()
        if device_name is None or device_name == ss.actualdevice.name:
            for dev in devices["devices"]:
                if dev["name"] == ss.actualdevice.name:
                    ss.actualdevice.id = dev["id"]
                    ss.actualdevice.volume = dev["volume_percent"]
                    return
        else:
            for dev in devices["devices"]:
                if dev["name"] == device_name:
                    newdev = sc.DeviceItem()
                    newdev.name = dev["name"]
                    newdev.id = dev["id"]
                    newdev.volume = dev["volume_percent"]
                    ss.userdevices[newdev.id] = newdev
                    return

    def next_track(self):
        sp.next_track()
        self.update_playback()

    def previous_track(self):
        sp.previous_track()
        self.update_playback()

    def seek_track(self, seek_ms):
        sp.seek_track(seek_ms, ss.actualdevice.id)
        self.update_playback(progress_only=True)

    def toggle_shuffle(self):
        if not ss.playerstate.shuffle:
            sp.shuffle(False, ss.actualdevice.id)
        else:
            sp.shuffle(True, ss.actualdevice.id)

    def play_pause(self):
        if ss.playerstate.isplaying == True:
            sp.pause_playback(ss.actualdevice.id)
        else:
            sp.start_playback(ss.actualdevice.id)
        self.update_playback()

    def update_volume(self, volume):
        sp.volume(volume, ss.actualdevice.id)
        self.update_playback(volume_only=True)

    def play_trackcontexturi(self, contexturi, trackuri):
        offset = {"uri": trackuri}
        sp.start_playback(ss.actualdevice.id, context_uri=contexturi, offset=offset)
        self.update_playback()

    def play_trackuri(self, trackuri: list[str]):
        sp.start_playback(ss.actualdevice.id, uris=trackuri)
        self.update_playback()


spc = SpotifyController()


def main(page: ft.Page):
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

        if ss.playerstate.isplaying == True:
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

    def timer_refresh():
        spc.update_playback()
        update_fields()

        if ss.playerstate.isplaying == False:
            stop_timer()
            long_running_poll()

    def extract_palette(image):
        palette = extract_colors(
            image=image, palette_size=5, sort_mode="frequency", mode="KM"
        )
        most_common_color = palette[0].rgb
        rgbval = (
            most_common_color[0],
            most_common_color[1],
            most_common_color[2],
        )
        least_common_color = palette[1].rgb
        collum = palette[1].luminance
        rgbval2 = (
            least_common_color[0],
            least_common_color[1],
            least_common_color[2],
        )
        rgbcol = "#60%02x%02x%02x" % (rgbval)
        rgbcol2 = "#%02x%02x%02x" % (rgbval2)
        page.views[-1].bgcolor = rgbcol
        if collum > 100:
            nexttrack.icon_color = "#000000"
            prevtrack.icon_color = "#000000"
        else:
            nexttrack.icon_color = "#ffffff"
            prevtrack.icon_color = "#ffffff"
        nexttrack.style.bgcolor = rgbcol2
        prevtrack.style.bgcolor = rgbcol2

    def is_first_item():
        try:
            for uri, i in ss.actualqueue.items():
                # this is crazy, but it just simpler that checking the queue in other places
                # rplaces ui only if the first track changes or if the check fails

                for x in bs.content.content.content.controls:
                    if i.name == x.title.value:
                        return True
                    else:
                        return False
        except:
            return False

    def make_queue():
        if ss.actualqueue is not None:
            if is_first_item():
                return
            queuelist = []
            for uri, track in ss.actualqueue.items():
                queuelist.append(
                    ft.ListTile(
                        leading=ft.Image(
                            src=track.image,
                            width=32,
                            height=32,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=ft.border_radius.all(5),
                        ),
                        title=ft.Text(track.name),
                        subtitle=ft.Text(track.artists),
                        trailing=ft.Text(
                            time.strftime("%M:%S", time.gmtime(track.duration))
                        ),
                        on_click=change_track,
                        data=[ss.playerstate.contexturi, uri, False],
                    )
                )
            bs.content.content = ft.Container(
                width=600,
                content=ft.Column(controls=queuelist, spacing=0, scroll=True),
                padding=ft.padding.symmetric(vertical=0, horizontal=0),
                margin=ft.margin.symmetric(horizontal=2, vertical=2),
            )

    def make_playlists():
        if ss.userplaylists is not None:
            queuelist = []
            for uri, playlist in ss.userplaylists.items():
                queuelist.append(
                    ft.ListTile(
                        leading=ft.Image(
                            src=playlist.image,
                            width=32,
                            height=32,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=ft.border_radius.all(5),
                        ),
                        title=ft.Text(playlist.name),
                        trailing=ft.IconButton(
                            ft.Icons.ARROW_CIRCLE_RIGHT,
                            on_click=explore_playlist,
                            data=[uri],
                        ),
                        on_click=explore_playlist,
                        data=[uri],
                    )
                )
            bs1.content.content = ft.Container(
                width=600,
                content=ft.Column(controls=queuelist, spacing=0, scroll=True),
                padding=ft.padding.symmetric(vertical=0, horizontal=0),
                margin=ft.margin.symmetric(horizontal=2, vertical=2),
            )

    def explore_playlist(e):
        playlisturi = e.control.data[0]
        if not bool(ss.userplaylists[playlisturi].tracks):
            playlistitemsJSON = sp.playlist_items(
                playlist_id=playlisturi,
                fields="items(track(name,artists(name),album(name,images),duration_ms,uri))",
            )
            ss.userplaylists[playlisturi].tracks = cs.get_playlist_items(
                playlistitemsJSON
            )
        tracklist = []
        for uri, track in ss.userplaylists[playlisturi].tracks.items():
            tracklist.append(
                ft.ListTile(
                    leading=ft.Image(
                        src=track.image,
                        width=32,
                        height=32,
                        fit=ft.ImageFit.CONTAIN,
                        border_radius=ft.border_radius.all(5),
                    ),
                    title=ft.Text(track.name),
                    subtitle=ft.Text(track.artists),
                    trailing=ft.Text(
                        time.strftime("%M:%S", time.gmtime(track.duration))
                    ),
                    on_click=change_track,
                    data=[playlisturi, uri, True],
                )
            )
        bs2.content.content = ft.Container(
            width=600,
            content=ft.Column(controls=tracklist, spacing=0, scroll=True),
            padding=ft.padding.symmetric(vertical=0, horizontal=0),
            margin=ft.margin.symmetric(horizontal=2, vertical=2),
        )
        page.open(bs2)

    def change_track(e):
        if e.control.data[0] == "" or e.control.data[0] == "none":
            spc.play_trackuri([e.control.data[1]])
        else:
            spc.play_trackcontexturi(e.control.data[0], e.control.data[1])

        if e.control.data[2] == True:
            page.close(bs2)
            page.close(bs1)
        else:
            page.close(bs)

        spc.update_playback()
        make_queue()
        update_fields()
        start_refresh()

    def play_pause(e):
        spc.play_pause()
        make_queue()
        update_fields()

        if ss.playerstate.isplaying == True:
            start_refresh()
            remove_long_poll()
        else:
            long_running_poll()
            stop_timer()

    def previous_track(e):
        spc.previous_track()
        make_queue()
        update_fields()

    def next_track(e):
        spc.next_track()
        make_queue()
        update_fields()

    def update_fields():
        if ss.playerstate.isplaying == True:
            tticonbtn.icon = ft.Icons.PAUSE
            tticonbtn.opacity = 0
            ttimg.opacity = 1
            ttimg.color = None
            ttimg.color_blend_mode = ft.BlendMode.COLOR
            ttime.content.value = ss.playerstate.progress
            t0.value = time.strftime("%M:%S", time.gmtime(ss.playerstate.progress))
            make_queue()
        else:
            ttimg.color = ft.Colors.BLACK
            ttimg.color_blend_mode = ft.BlendMode.SATURATION
            ttimg.opacity = 0.5
            tticonbtn.icon = ft.Icons.PLAY_ARROW
            tticonbtn.opacity = 0.8
        ttimg.src = ss.actualtrack.image
        tname.value = ss.actualtrack.name
        tartist.value = ss.actualtrack.artists
        talbum.value = ss.actualtrack.album

        ttime.content.max = ss.actualtrack.duration
        tdur.value = time.strftime("%M:%S", time.gmtime(ss.actualtrack.duration))

        tvolume.value = ss.actualdevice.volume
        extract_palette(ss.actualtrack.image)
        page.update()

    def seek_track(e):
        spc.seek_track(int(e.control.value * 1000))
        ttime.content.value = e.control.value
        ttime.update()

    def update_volume(e):
        spc.update_volume(int(e.control.value))
        tvolume.value = e.control.value
        tvolume.update()

    tvolume = ft.Slider(
        min=0, max=100, value=ss.actualdevice.volume, on_change_end=update_volume
    )

    ttime = ft.Container(
        content=ft.Slider(
            value=int(ss.playerstate.progress),
            min=0,
            max=int(ss.actualtrack.duration),
            on_change_end=seek_track,
            width=250,
        )
    )
    tdur = ft.Text(
        time.strftime("%M:%S", time.gmtime(ss.actualtrack.duration)),
        size=12,
        color=ft.Colors.WHITE,
    )

    t0 = ft.Text(
        time.strftime("%M:%S", time.gmtime(ss.playerstate.progress)),
        size=12,
        color=ft.Colors.WHITE,
    )
    ttimg = ft.Image(
        src=ss.actualtrack.image,
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
        ss.actualtrack.name,
        size=24,
        weight=ft.FontWeight.BOLD,
        # overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
        max_lines=2,
    )
    tartist = ft.Text(
        ss.actualtrack.artists,
        size=20,
        weight=ft.FontWeight.BOLD,
        # overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
        max_lines=1,
    )
    talbum = ft.Text(ss.actualtrack.album)

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
        icon=ft.Icons.PLAY_ARROW if not ss.playerstate.isplaying else ft.Icons.PAUSE,
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

    bs1 = ft.BottomSheet(
        enable_drag=True,
        dismissible=True,
        is_scroll_controlled=True,
        show_drag_handle=True,
        content=ft.Container(padding=20, width=780, content=None),
    )

    bs2 = ft.BottomSheet(
        enable_drag=True,
        dismissible=True,
        is_scroll_controlled=True,
        show_drag_handle=True,
        content=ft.Container(padding=20, width=780, content=None),
    )

    toprow = ft.Row(
        [
            prevtrackcol,
            trackinfocol,
            nexttrackcol,
        ],
        alignment=ft.MainAxisAlignment.SPACE_AROUND,
    )

    bottomrow = ft.Row(
        [
            ft.Container(tvolume),
            ft.Container(
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Playlists",
                            on_click=lambda _: page.open(bs1),
                            icon=ft.Icons.LIST,
                            style=ft.ButtonStyle(
                                icon_size=28,
                                text_style=ft.TextStyle(size=22),
                                padding=ft.padding.symmetric(horizontal=15),
                            ),
                            height=60,
                        ),
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
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    page.views.append(
        ft.View(
            "/",
            [
                ft.Container(
                    toprow,
                    alignment=ft.alignment.center,
                    width=800,
                ),
                ft.Container(bottomrow),
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
    make_playlists()
    if ss.playerstate.isplaying == True:
        start_refresh()
        remove_long_poll()
        spc.update_playback()
        make_queue()
        update_fields()
    else:
        long_running_poll()
        stop_timer()
        update_fields()

    page.go("/")


ft.app(main)
