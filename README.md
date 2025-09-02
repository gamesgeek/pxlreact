# Project Overview
PxlReact seeks to enhance and automate tasks in various applications including games by:
- Monitoring the state of pixels on the screen, primarily observing for color fluctuations
- Triggering predefined "reactions" when monitored pixels change; reactions will usually involve
sending one or more key events via PxlIntercept, but may include other actions such as playing sounds

# PxlReact Structure

## Hardware Interception, Keyboard Handling
The classes PxlIntercept and PxlKbd are responsible for dispatching key events via pyinterception
and, defining and managing keybinds (remappings), and capturing keys from the user's physical keyboard
in order to enforce defined mappings.

PxlIntercept is a wrapper-wrapper around pyinterception, which is itself a wrapper for the Interception library.

- [pyinterception](https://github.com/kennyhml/pyinterception)
- [Interception library](https://github.com/oblitum/Interception?tab=readme-ov-file#readme)

To avoid running afoul of various automation detection algorithms, PxlIntercept adds pseudo-random
delays before key press events and between press and release events. 

## Class PxlReactApp
The "main entry point" of the utility; an instance of PxlReactApp creates a GUI for displaying pixel
information, and a PxlWatcher for collecting it.

### The PxlReactApp GUI

#### Simple, Minimally Viable Design
PxlReact implements a simple, barebones GUI window whose purpose is to provide visual feedback to the user related to the
pixels currently being monitored. The guiding principle behind the design of the PxlReact GUI is `minimum viability`; it
will serve primarily as a status window with little to no interactive elements.

#### Dynamic Construction, Static Operation
The PxlReact GUI will not support resizing or any changes to its layout during operation, but the dimensions and position
of its components are calculated when the script is run and can be adapted to support the monitoring of different numbers of
pixels within its `pixel display area.`

The current implementation focuses on watching four pixels (five with mouse preview), but however possible when implementing
new functionality, support should be included for the possibility of expanding to larger grid sizes (probably safe to
assume an upper-limit of 16 pixels in a 4x4 grid if such an estimate is valuable in any context).
  
#### Main Window Layout
The main window of PxlReact comprises a number of pixel display areas, each containing data related to a specific
pixel location. These areas are arranged in a grid-like pattern where the top row is reserved for reporting on
the pixel currently under the mouse cursor. This `mouse preview area` will always be the only information in the top row
to help distinguish it visually from the other pixel data.

The rows below the mouse preview row are designated for displaying data related to the pixels which have been assigned
for monitoring. For the purposes of design & development, we will focus on a layout that allows for the monitoring of
4 pixels simultaneously arranged in a 2x2 grid. We can refer to these pixel display areas as the `pixel grid` which
will be shorthand for "all pixel display areas except the mouse preview area."

Here is a textual representation of the layout; as indicated, the mouse preview area is offset to account for the fact that
it is the only area on that "row" of the GUI window. Apart from this, the internal contents of all areas are identical
and arranged with the same configuration, alignment, etc.

```
+-------------------------+
|      [Mouse Area]       |
+-------------------------+
|  [Pixel 1] | [Pixel 2]  |
+-------------------------+
|  [Pixel 3] | [Pixel 4]  |
+-------------------------+
```

#### Pixel Display Area Layouts
Each pixel display area contains two primary components: 
  1. a `data text` area responsible for displaying information about the pixel such as its location or the hexidecimal
  value of its current color
  2. a `big pixel` representation which is a framed rectangle filled using the color of the pixel (the last time
  it was polled); another way to think of this is that it shows a "zoomed in" version of the monitored pixel
  
Here is a visual representation of the pixel display area layout, showing the top-left alignment of the data text, and
top-right alignment of the big pixel:

```
+--------------------------+
| Data row 1          [BP] |
| Data row 2               |
| ...                      |
+--------------------------+
```

As indicated, while the pixel data currently contains only two rows, PxlReact should be designed to accommodate the addition
of new data for each pixel area. 'BP' represents the big pixel rectangle.

#### Pixel Data Text
One of the two components of each individual pixel display area, pixel data text relays information related to each
pixel using basic text output.

#### Current Pixel Data Text
Pixel data currently includes two pieces of data separated into rows with a newline:

```
(sx, sy)
0x######
```

`sx`, and `sy` represent the pixel's screen coordinates, while `0x######` is the current HEX color (or the one which
was seen by the last poll cycle).

One possible enhancement opportunity for PxlReact will be to add additional data to the set of pixel data, which may
eventually suggest the need for a companion class that encapsulates a pixel object to manage this data more effectively.

## Class Pxl
Pxl's represent a location on the screen, their most recently-observed color, and any PxlReactions associated with them.

Each Pxl object observes its own screen position each tick, alerting the GUI to redraw its display area if its color changes
from that currently being displayed in the GUI window.

## Class PxlReaction
PxlReactions are the heart of PxlReact; when a Pxl is assigned a PxlReaction it means that the user wants to invoke
some method in response to changes in color of that pixel. Some generic examples that demonstrate this concept:

- If the pixel at sx, sy turns red, I want to immediately press the "r" key (react_if_color)
- If the pixel at sx, sy ever stops being green, I want to immediately press the 'g' key (react_if_not_color)

## Class PxlReactionRegistry
Instead of maintaining an external file format for loading predefined reactions, this provides a class for this purpose.

The PxlReacitonRegistry is a way of storing pixel locations and their associated reactions for later use so they do not
have to be recreated each time the application is run (i.e., for a common applications, the same pixels will be monitored
and reacted to similarly across sessions).

In the future, it may be desirable to create an external file format for this purpose that can be loaded into PxlReact
at runtime.

# Core PxlReact Functional Components
PxlReact is a small utility with relatively limited functionality by design; below are the main functional components that
comprise the project.

## Pixel Assignment
Function keys are used to set or "assign" the pixel currently under the mouse to one of the pixel display areas. Once
set, each pixel can be replaced if the same function key is pressed again, but no mechanism will (yet) be implemented for 
un-assignment. PxlReact is lightweight and simple enough to rely on simply starting a new instance to perform new assignments.

## Pixel Polling Loop (or "Pixel Watcher")
At a globally preset interval, PxlReact reads or "polls" each of the currently assigned pixel locations to retrieve their
current color, then updates the information within the corresponding pixel display area.

For efficiency, PxlReact should always strive to limit updating information about a pixel to cases where a change has
occurred (i.e., do not redraw or refresh details for a pixel whose color is the same as it was on the last polling pass).

## Keyboard Events w/ Interception
The `PxlIntercept` class implemented in `pxl_intercept.py` imports [pyinterception](https://github.com/kennyhml/pyinterception),
which is a Python wrapper for [Interception](https://github.com/oblitum/Interception?tab=readme-ov-file).

With an instance of `PxlIntercept`, the PxlReact utility can `press_key` to send key events immediately, or `react_key`
to include a reasonable amount of human-like reaction time.

`PxlIntercept` introduces an added layer of variability in event timing by dynamically adjusting the KEY_PRESS_DELAY property
of pyinterception.

## React to Pixel Color Change
The next priority for PxlReact is implementation of the "reaction" component. This will involve the creation of a more
robust dictionary to keep track of data related to the pixels being monitored. Most importantly, this dictionary will define:

  - The type of reaction associated with this pixel
  - The function (and parameters) to use when this reaction is triggered
  - The color to use to decide when to trigger a reaction
  - A tolerance value to suppress reactions in response to very small changes in color when necessary

## Pause Polling (Future - Not Implemented)
In certain instances, it may be useful for the user to "hold" a particular pixel state within the GUI and temporarily pause
refreshes. This is currently achieved by holding down CTRL during operation.

## Log Pixel Data (Future - Not Implemented)
A necessary planned enhancement is the ability for PxlWin to "record" pixel data over time with the eventual goal of
writing this data to an external data file for further analysis. Similar to the efficiency measures described in the polling
section, the pixel data log should only log events related to a change in the pixel being monitored.

Each "log entry" would include a timestamp in milliseconds-since-application-run along with the state of the pixel at
the time of the poll (it will not be necessary to repeatedly log the pixel's location since that will be static, instead
location can be used in order to create uniquely-keyed entries if multiple pixels are being logged simultaneously).

## Analyze Pixel Log (Future - Not Implemented)
Once logging is implemented, an immediate need arises for a method to perform some basic analysis on the pixel data logs.
Two analysis tasks of immediate benefit would be:

1. `total colors`: For a given pixel, show all possible unique color values (i.e., every color that pixel was at any point
   within the logging period). For pixels with a very large set of possible unique values, it may be helpful to allow for
   some "grouping" of color values so the data set becomes managemeable while still providing relevant details about
   how a pixel's color changed.

2. `average color`: For a given pixel over a set period of time it will be useful to be able to calculate an average of
   all color values seen.

3. `color frequency`: Analysis that can probably be done when finding `total colors`, it might also be useful to know
   how often each individual color appears in the log for a given pixel (i.e., it was 0xFF00FF 3,764 times and 0xFF99FF
   537 times, etc.).

4. `largest deltas`: Since many reaction events will be based on a pixel undergoing a "significant" change in color, being
   able to see the greatest changes in color value for a given pixel over a period of logging will be helpful to know what
   constitutes significance for any given pixel. When implementing this analysis it will not be sufficient to report only
   on the minimum and maximum deltas, because these will almost always represent some anomalous state such as the screen
   going black during application loading or white because a word document was accidentally opened momentarily.

# Enhancement Opportunities
In addition to the enhanced functionality suggested in the above 'Future - Not Implemented' sections, here are some other
opportunities to enhance or improve PxlWin project:

## Consider Alternatives to tkinter
While the `tkinter` library fulfills an early development requirement to "minimize complexity" and get up-and-running
with as little overhead as possible, it does strike me as perhaps a relatively dated solution even for a simple project
like PxlReact; if my hunch is correct I could use help identifying alternatives and assessing the level of effort that
might be necessary to transition to a different library without necessitating a full "rebuild" of the project.

# Additional Reference
Below sections are dedicated to "additional information" that provide additional support or contextual details for the
various components of PxlReact.

## Local Directory Structure
Following are absolute paths showing where the components of PxlReact reside on my local system.

`C:/dev/pxlreact` is the primary working directory and home to all scripts

## PxlReact Technology Stack

- [Microsoft Windows 11](https://www.microsoft.com/en-us/windows/windows-11?r=1)
- [Cursor](https://docs.cursor.com/)
- [Python 3.12.10](https://www.python.org/downloads/release/python-3128/)
- [Github](https://github.com/gamesgeek/pxlreact)
- [tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI/window
- [pyinterception](https://github.com/kennyhml/pyinterception)
- [Interception](https://github.com/oblitum/Interception?tab=readme-ov-file)
