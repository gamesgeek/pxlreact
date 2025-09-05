import pxl_guiconst as pgc


class PxlGui:
    """
    PxlGui is responsible for the creation and updating of the PxlReact GUI window,
    which displays data about pixels being monitored, including a "mouse preview" area for the pixel under the cursor.
    """

    def __init__( self ):
        """
        Initialize the PxlGui class by calculating the layout configuration dynamically.
        """
        self._layout_config = self._calculate_layout()

    @property
    def layout_config( self ):
        """
        Return the layout configuration for the GUI.
        """
        return self._layout_config

    @property
    def pixel_areas( self ):
        """
        Return the layout configuration for the pixel areas.
        """
        return self._layout_config[ "pixel_areas" ]

    def _calculate_layout( self ):
        """
        Dynamically calculate the layout configuration for pixel areas and return all relevant layout data.
        """
        # Calculate pixel area dimensions
        area_width = ( pgc.DRAWABLE_W - pgc.TOTAL_HPAD ) // pgc.PX_GRID_COLS
        area_height = ( pgc.DRAWABLE_H - pgc.TOTAL_VPAD ) // pgc.PX_GRID_ROWS

        layout = {
            "window": {
                "width": pgc.WIN_W, "height": pgc.WIN_H
            },
            "pixel_areas": [],
            "padding": pgc.PAD,
        }

        # Populate layout with all pixel areas and the mouse preview
        for row in range( pgc.PX_GRID_ROWS ):
            for col in range( pgc.PX_GRID_COLS ):
                x1 = pgc.PX_GRID_L + col * ( area_width + pgc.PAD )
                y1 = pgc.PX_GRID_T + row * ( area_height + pgc.PAD )
                x2 = x1 + area_width
                y2 = y1 + area_height

                if row == 0: # Mouse preview row
                    layout[ "mouse_preview" ] = {
                        "x1": pgc.PX_GRID_L, "y1": pgc.PX_GRID_T, "x2": pgc.PX_GRID_R, "y2": y2
                    }
                    break
                else: # Normal grid pixel area
                    layout[ "pixel_areas" ].append( { "x1": x1, "y1": y1, "x2": x2, "y2": y2 } )

        return layout
