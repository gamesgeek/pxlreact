"""
pxl_statusbar.py renders the in-process runtime status bar: a small always-on-top DearPyGui window
that replaces the terminal crawl during gameplay.

Layout (top to bottom):
- headline bar: a framed strip showing the most recently fired ability with a right-side timestamp;
  the frame flashes red briefly when a press arrives during a cast and is dropped
- context line: ACTIVE/INACTIVE and live CASTING state
- rotations: one header per rotation with live per-action readiness rows (cooldown + color checks)
- reactions: last-fire swatch/timing rows, at the bottom

The bar runs its own render loop on a daemon thread (DPG 2.x is thread-safe) and reads StatusHub
snapshots each frame; the 40 Hz poll loop on the main thread is untouched. Live rotation cooldowns
are computed from shared Action state (no pixel reads); rotation color checks DO read pixels, so
they refresh at the lower `color_check_hz` rate and only while the app context is active, keeping
GDI contention with the poll loop negligible.

This module is imported only when gui.statusbar_enabled is true, so headless runs never touch
dearpygui. Closing the status bar window kills only the bar; the core keeps running.
"""

import threading
import time

import dearpygui.dearpygui as dpg

GREEN_C = ( 120, 220, 120, 255 )
YELLOW_C = ( 230, 200, 90, 255 )
RED_C = ( 235, 110, 110, 255 )
GREY_C = ( 150, 150, 150, 255 )
WHITE_C = ( 230, 230, 230, 255 )

HEADLINE_HEIGHT = 44


class StatusBar:

    def __init__( self, hub, gui_cfg ):
        self.hub = hub
        self.fps = gui_cfg[ 'fps' ]
        self.color_interval = 1.0 / gui_cfg[ 'color_check_hz' ]
        self.pos = gui_cfg[ 'pos' ]
        self.size = gui_cfg[ 'size' ]

        self._stop = threading.Event()
        self._thread = None

        # Cached row signatures; a change (profile reload) triggers a row rebuild
        self._reaction_sig = None
        self._rotation_sig = None

        # id(ColorCondition) -> last passes() result, refreshed at color_check_hz while active
        self._color_cache = {}
        self._last_color_refresh = 0.0

        self._flash_theme = None
        self._flash_bound = False

    def start( self ):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread( target = self._run, name = 'StatusBar', daemon = True )
        self._thread.start()

    def stop( self ):
        self._stop.set()
        if self._thread:
            self._thread.join( timeout = 2.0 )

    # ------------------------------------------------------------------ render

    def _run( self, max_frames = None ):
        try:
            dpg.create_context()
            dpg.create_viewport( title = 'pxlreact', width = self.size[ 0 ], height = self.size[ 1 ],
                                 x_pos = self.pos[ 0 ], y_pos = self.pos[ 1 ],
                                 always_on_top = True, resizable = True )

            # Red border theme, bound to the headline bar while a dropped-press flash is active
            with dpg.theme() as self._flash_theme:
                with dpg.theme_component( dpg.mvChildWindow ):
                    dpg.add_theme_color( dpg.mvThemeCol_Border, RED_C )

            with dpg.window( tag = 'sb_root' ):
                # Headline: most recently fired ability, timestamp hugging the right edge
                with dpg.child_window( tag = 'sb_headline', height = HEADLINE_HEIGHT, border = True ):
                    with dpg.table( header_row = False, policy = dpg.mvTable_SizingStretchProp ):
                        dpg.add_table_column( init_width_or_weight = 1.0 )
                        dpg.add_table_column( init_width_or_weight = 70, width_fixed = True )
                        with dpg.table_row():
                            dpg.add_text( '--', tag = 'sb_ability', color = WHITE_C )
                            dpg.add_text( '', tag = 'sb_ability_t', color = GREY_C )

                with dpg.group( horizontal = True ):
                    dpg.add_text( 'INACTIVE', tag = 'sb_active', color = GREY_C )
                    dpg.add_text( '', tag = 'sb_cast', color = RED_C )
                dpg.add_separator()
                dpg.add_text( 'rotations', color = GREY_C )
                dpg.add_group( tag = 'sb_rotations' )
                dpg.add_separator()
                dpg.add_text( 'reactions', color = GREY_C )
                dpg.add_group( tag = 'sb_reactions' )

            dpg.set_primary_window( 'sb_root', True )
            dpg.setup_dearpygui()
            dpg.show_viewport()

            frame = 0
            interval = 1.0 / self.fps
            while dpg.is_dearpygui_running() and not self._stop.is_set():
                started = time.perf_counter()
                self._refresh()
                dpg.render_dearpygui_frame()
                frame += 1
                if max_frames is not None and frame >= max_frames:
                    break
                elapsed = time.perf_counter() - started
                if elapsed < interval:
                    time.sleep( interval - elapsed )
        finally:
            try:
                dpg.destroy_context()
            except Exception:
                pass

    def _refresh( self ):
        snap = self.hub.snapshot()

        self._refresh_headline( snap )

        if snap[ 'active' ]:
            dpg.set_value( 'sb_active', 'ACTIVE' )
            dpg.configure_item( 'sb_active', color = GREEN_C )
        else:
            dpg.set_value( 'sb_active', 'INACTIVE' )
            dpg.configure_item( 'sb_active', color = GREY_C )
        dpg.set_value( 'sb_cast', 'CASTING' if snap[ 'casting' ] else '' )

        self._refresh_rotations( snap )
        self._refresh_reactions( snap )

    # ---------------------------------------------------------------- headline

    def _refresh_headline( self, snap ):
        last = snap[ 'last_ability' ]
        if last is not None:
            name, stamp = last
            dpg.set_value( 'sb_ability', name )
            dpg.set_value( 'sb_ability_t', stamp )

        # Bind/unbind the red-border theme only on transitions (theme binding is not free per frame)
        flash = snap[ 'flash' ]
        if flash != self._flash_bound:
            dpg.bind_item_theme( 'sb_headline', self._flash_theme if flash else 0 )
            self._flash_bound = flash

    # ---------------------------------------------------------------- rotations

    def _refresh_rotations( self, snap ):
        view = snap[ 'rotation_view' ]
        sig = tuple( rname for rname, _ in view )
        if sig != self._rotation_sig:
            self._rotation_sig = sig
            self._color_cache = {}
            dpg.delete_item( 'sb_rotations', children_only = True )
            for rname, rotation in view:
                dpg.add_text( rname, parent = 'sb_rotations', color = WHITE_C )
                for i, _action in enumerate( rotation.actions ):
                    dpg.add_text( '', tag = f'sb_rot_{rname}_{i}', parent = 'sb_rotations',
                                  color = GREY_C, indent = 12 )

        # Rotation color checks read live pixels, so refresh them at the (slower) configured rate
        # and only while the game context is active
        now = time.perf_counter()
        refresh_colors = snap[ 'active' ] and ( now - self._last_color_refresh ) >= self.color_interval
        if refresh_colors:
            self._last_color_refresh = now

        for rname, rotation in view:
            for i, action in enumerate( rotation.actions ):
                remaining = action.cooldown_remaining()
                cd = 'rdy' if remaining == 0.0 else f'{remaining:4.1f}s'

                glyphs = ''
                colors_ok = True
                for cond in action.color_checks:
                    if refresh_colors:
                        self._color_cache[ id( cond ) ] = cond.passes()
                    ok = self._color_cache.get( id( cond ) )
                    if ok is None:
                        glyphs += '?'
                        colors_ok = False
                    else:
                        glyphs += '+' if ok else 'x'
                        colors_ok = colors_ok and ok

                tag = f'sb_rot_{rname}_{i}'
                dpg.set_value( tag, f"{action.name:<20} {cd:>6}  {glyphs}" )
                if remaining == 0.0 and colors_ok:
                    dpg.configure_item( tag, color = GREEN_C )
                elif remaining > 0.0:
                    dpg.configure_item( tag, color = YELLOW_C )
                else:
                    dpg.configure_item( tag, color = GREY_C )

    # --------------------------------------------------------------- reactions

    def _refresh_reactions( self, snap ):
        reactions = snap[ 'reactions' ]
        sig = tuple( reactions )
        if sig != self._reaction_sig:
            self._reaction_sig = sig
            dpg.delete_item( 'sb_reactions', children_only = True )
            for name in reactions:
                with dpg.group( horizontal = True, parent = 'sb_reactions' ):
                    dpg.add_color_button( default_value = ( 40, 40, 40, 255 ), tag = f'sb_rx_{name}_c',
                                          width = 18, height = 18, no_border = True )
                    dpg.add_text( f'{name:<6}', color = WHITE_C )
                    dpg.add_text( '', tag = f'sb_rx_{name}_t', color = GREY_C )

        for name, row in reactions.items():
            if row[ 'time' ]:
                dpg.set_value( f'sb_rx_{name}_t', f"{row['time']}  dt {row['delta']}" )
                dpg.configure_item( f'sb_rx_{name}_t', color = WHITE_C )
            else:
                dpg.set_value( f'sb_rx_{name}_t', 'no triggers yet' )
            if row[ 'color' ] is not None:
                r, g, b = row[ 'color' ]
                dpg.set_value( f'sb_rx_{name}_c', ( r, g, b, 255 ) )
