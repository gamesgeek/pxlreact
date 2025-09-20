import tkinter as tk
import time
import threading
import argparse
from pynput import keyboard
from ansi import *


class Stopwatch:
    
    def __init__( self, hold_timer_mode=False ):
        # Store the mode
        self.hold_timer_mode = hold_timer_mode
        
        # Keybinding configuration dictionary
        if hold_timer_mode:
            self.keybinds = {
                'start_stop': keyboard.Key.space,  # Press to start, release to stop
                'reset': keyboard.Key.f10,
                'exit': keyboard.Key.f11
            }
        else:
            self.keybinds = {
                'toggle': keyboard.Key.f9,         # Toggle start/pause
                'reset': keyboard.Key.f10,
                'exit': keyboard.Key.f11
            }
        
        # Configuration dictionary for easy customization
        self.config = {
            'window_width': 160,
            'window_height': 40,
            'initial_x': 100,
            'initial_y': 100,
            'background_color': 'black',
            'text_color': 'lime',
            'text_color_threshold': 'magenta',
            'color_threshold': 0.45,
            'font_family': 'Consolas',
            'font_size': 16,
            'transparency': 0.8,
            'update_interval_ms': 10
        }
        
        self.root = tk.Tk()
        self.root.title( "Stopwatch" )
        self.root.geometry( f"{self.config['window_width']}x{self.config['window_height']}+{self.config['initial_x']}+{self.config['initial_y']}" )
        self.root.configure( bg=self.config['background_color'] )
        self.root.attributes( '-topmost', True )  # Stay on top
        self.root.attributes( '-alpha', self.config['transparency'] )     # Semi-transparent
        self.root.overrideredirect( True )        # Remove window decorations
        
        # Timing variables
        self.start_time = None
        self.elapsed_time = 0.0
        self.running = False
        
        # Display label
        self.time_label = tk.Label(
            self.root,
            text="00:00.000",
            font=( self.config['font_family'], self.config['font_size'], "bold" ),
            fg=self.config['text_color'],
            bg=self.config['background_color']
        )
        self.time_label.pack( expand=True )
        
        # Make window draggable
        self.root.bind( '<Button-1>', self.start_drag )
        self.root.bind( '<B1-Motion>', self.drag_window )
        self.time_label.bind( '<Button-1>', self.start_drag )
        self.time_label.bind( '<B1-Motion>', self.drag_window )
        
        # Setup global hotkey listener
        self.setup_global_hotkeys()
        
        # Start the update loop
        self.update_display()
        
        # Print instructions to console
        print( f"{GREEN}Stopwatch initialized and ready!{RESET}" )
        print( f"{CYAN}Controls:{RESET}" )
        if self.hold_timer_mode:
            print( f"  {YELLOW}SPACE{RESET} - Hold to time (press to start, release to stop)" )
            print( f"  {YELLOW}F10{RESET}   - Reset" )
            print( f"  {YELLOW}F11{RESET}   - Exit" )
        else:
            print( f"  {YELLOW}F9{RESET}  - Toggle Start/Pause" )
            print( f"  {YELLOW}F10{RESET} - Reset" )
            print( f"  {YELLOW}F11{RESET} - Exit" )
    
    def start_drag( self, event ):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def drag_window( self, event ):
        x = self.root.winfo_x() + event.x - self.drag_start_x
        y = self.root.winfo_y() + event.y - self.drag_start_y
        self.root.geometry( f"+{x}+{y}" )
    
    def setup_global_hotkeys( self ):
        """Setup global hotkey listener using pynput"""
        def on_key_press( key ):
            try:
                if self.hold_timer_mode:
                    # Hold timer mode: space starts timer
                    if key == self.keybinds['start_stop']:
                        self.start_timer()
                    elif key == self.keybinds['reset']:
                        self.reset()
                    elif key == self.keybinds['exit']:
                        self.exit_app()
                else:
                    # Normal mode: existing toggle behavior
                    if key == self.keybinds['toggle']:
                        self.toggle_start_pause()
                    elif key == self.keybinds['reset']:
                        self.reset()
                    elif key == self.keybinds['exit']:
                        self.exit_app()
            except AttributeError:
                # Handle special keys that don't have a char attribute
                pass
        
        def on_key_release( key ):
            try:
                if self.hold_timer_mode:
                    # Hold timer mode: space release stops timer
                    if key == self.keybinds['start_stop']:
                        self.stop_timer()
                        # Reset the timer 1s after release
                        self.root.after( 1000, self.reset )
            except AttributeError:
                # Handle special keys that don't have a char attribute
                pass
        
        # Start the global listener in a separate thread
        if self.hold_timer_mode:
            self.listener = keyboard.Listener( on_press=on_key_press, on_release=on_key_release )
        else:
            self.listener = keyboard.Listener( on_press=on_key_press )
        self.listener.daemon = True
        self.listener.start()
    
    def toggle_start_pause( self ):
        """Toggle between start/resume and pause with a single key"""
        if self.running:
            # Currently running, so pause
            self.running = False
            print( f"{YELLOW}Stopwatch paused{RESET}" )
        else:
            # Currently paused or stopped, so start/resume
            self.start_time = time.perf_counter() - self.elapsed_time
            self.running = True
            print( f"{GREEN}Stopwatch started/resumed{RESET}" )
    
    def start_timer( self ):
        """Start the timer (for hold mode)"""
        if not self.running:
            self.start_time = time.perf_counter() - self.elapsed_time
            self.running = True
            print( f"{GREEN}Timer started{RESET}" )
    
    def stop_timer( self ):
        """Stop the timer (for hold mode)"""
        if self.running:
            self.running = False
            print( f"{YELLOW}Timer stopped{RESET}" )
    
    def reset( self ):
        self.running = False
        self.elapsed_time = 0.0
        self.start_time = None
        print( f"{CYAN}Stopwatch reset{RESET}" )
    
    def exit_app( self ):
        print( f"{RED}Stopwatch exiting{RESET}" )
        self.listener.stop()  # Stop the global hotkey listener
        self.root.quit()
        self.root.destroy()
    
    def update_display( self ):
        if self.running and self.start_time is not None:
            self.elapsed_time = time.perf_counter() - self.start_time
        
        # Format time as MM:SS.mmm (minutes:seconds.milliseconds)
        total_seconds = self.elapsed_time
        minutes = int( total_seconds // 60 )
        seconds = total_seconds % 60
        
        # Display with millisecond precision
        time_str = f"{minutes:02d}:{seconds:06.3f}"
        
        # Determine text color based on elapsed time threshold
        if self.elapsed_time > self.config['color_threshold']:
            text_color = self.config['text_color_threshold']
        else:
            text_color = self.config['text_color']
        
        self.time_label.config( text=time_str, fg=text_color )
        
        # Schedule next update using configured interval
        self.root.after( self.config['update_interval_ms'], self.update_display )
    
    def run( self ):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.exit_app()


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Lightweight stopwatch overlay')
    parser.add_argument('--holdtimer', action='store_true', 
                       help='Enable hold timer mode (press space to start, release to stop)')
    args = parser.parse_args()
    
    print( f"{CYAN}Starting lightweight stopwatch overlay...{RESET}" )
    if args.holdtimer:
        print( f"{MAGENTA}Hold timer mode enabled{RESET}" )
    
    stopwatch = Stopwatch(hold_timer_mode=args.holdtimer)
    stopwatch.run()


if __name__ == "__main__":
    main()
