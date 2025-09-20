# Use ANSI colors to highlight any console output
from ansi import *

sharex_root = r"C:/dev/sharex"
subdir_pattern = r"\d{4}-\d{2}"
capture_format = "mp4"
clip_dst = r"C:/Users/games/Videos"

ffmpeg_config = {
    # Video settings
    "video_codec": "libx264",
    "preset": "fast",
    "crf": 23,
    "fps": 60,
    "scale_height": 1080,  # Maintain aspect ratio with width = -2
    "pixel_format": "yuv420p",

    # Audio settings - suitable for clear speech and general gameplay audio
    "audio_codec": "aac",
    "audio_bitrate": "160k",
    "audio_channels": 2,
    "audio_sample_rate": 48000,

    # Extra args if you want to tweak encoding (e.g., ["-movflags", "+faststart"])
    "extra_args": []
}

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Tuple, Dict

# Delete any source clip shorter than this many seconds (treated as canceled/misclick)
MIN_KEEP_SECONDS = 5.0


def find_capture_files( root: Path, pattern: str, extension: str ) -> List[ Path ]:
    regex = re.compile( pattern )
    target_ext = "." + extension.lstrip( "." ).lower()
    results: List[ Path ] = []

    if not root.exists():
        print( f"{YELLOW}Warning: sharex_root does not exist: {CYAN}{root}{RE}" )
        return results

    for path in root.iterdir():
        if not path.is_dir():
            continue
        if not regex.fullmatch( path.name ):
            continue
        for file in path.rglob( "*" ):
            if file.is_file() and file.suffix.lower() == target_ext:
                results.append( file )
    return results


def run_ffprobe_duration_seconds( src: Path ) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        str( src )
    ]
    try:
        out = subprocess.check_output( cmd, stderr = subprocess.STDOUT )
        txt = out.decode( "utf-8", errors = "ignore" ).strip()
        return float( txt ) if txt else 0.0
    except Exception:
        return 0.0


def human_time( seconds: float ) -> str:
    seconds = max( 0, int( round( seconds ) ) )
    h = seconds // 3600
    m = ( seconds % 3600 ) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def build_ffmpeg_cmd( src: Path, dst: Path, cfg: dict ) -> List[ str ]:
    fps = int( cfg.get( "fps", 30 ) )
    scale_h = int( cfg.get( "scale_height", 1080 ) )
    vf = f"fps={fps},scale=-2:{scale_h}"

    cmd: List[ str ] = [
        "ffmpeg",
        # Overwrite behavior (-y/-n) is injected by caller based on flags
        "-i", str( src ),

        # Video
        "-c:v", cfg.get( "video_codec", "libx264" ),
        "-preset", cfg.get( "preset", "veryfast" ),
        "-crf", str( cfg.get( "crf", 23 ) ),
        "-pix_fmt", cfg.get( "pixel_format", "yuv420p" ),
        "-vf", vf,

        # Audio
        "-c:a", cfg.get( "audio_codec", "aac" ),
        "-b:a", cfg.get( "audio_bitrate", "160k" ),
        "-ac", str( cfg.get( "audio_channels", 2 ) ),
        "-ar", str( cfg.get( "audio_sample_rate", 48000 ) ),
    ]

    extra = cfg.get( "extra_args", [] ) or []
    if isinstance( extra, ( list, tuple ) ):
        cmd.extend( [ str( x ) for x in extra ] )

    cmd.append( str( dst ) )
    return cmd


def convert_one( src: Path, dst: Path, cfg: dict, overwrite: bool ) -> Tuple[ bool, int ]:
    if not overwrite and dst.exists():
        return ( True, 0 )

    if overwrite and dst.exists():
        try:
            dst.unlink()
        except Exception as e:
            print( f"{RED}Error removing existing file: {CYAN}{dst}{RE} — {e}" )
            return ( False, 1 )

    cmd = build_ffmpeg_cmd( src, dst, cfg )
    # Replace -y depending on overwrite
    if overwrite:
        if "-y" not in cmd:
            cmd.insert( 1, "-y" )
    else:
        # Use -n to avoid overwriting
        if "-n" not in cmd:
            cmd.insert( 1, "-n" )

    try:
        proc = subprocess.run( cmd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT )
        success = proc.returncode == 0 and dst.exists() and dst.stat().st_size > 0
        if not success:
            print( f"{RED}ffmpeg failed for {CYAN}{src.name}{RE}\n{proc.stdout.decode('utf-8', errors='ignore')}" )
            return ( False, proc.returncode )
        return ( True, 0 )
    except FileNotFoundError:
        print( f"{RED}ffmpeg not found in PATH.{RE}" )
        return ( False, 2 )
    except Exception as e:
        print( f"{RED}Unexpected error converting {CYAN}{src}{RE}: {e}" )
        return ( False, 3 )


def main():
    parser = argparse.ArgumentParser( description = "Convert ShareX clips to standardized MP4 with ffmpeg." )
    parser.add_argument( "--root", default = sharex_root, help = "ShareX root directory" )
    parser.add_argument( "--pattern", default = subdir_pattern, help = "Subdirectory regex pattern (full match)" )
    parser.add_argument( "--format", default = capture_format, help = "Capture format/extension (e.g., mp4)" )
    parser.add_argument( "--dst", default = clip_dst, help = "Destination directory for converted clips" )
    parser.add_argument( "--delete-original", action = "store_true", help = "Delete source file after successful conversion" )
    parser.add_argument( "--overwrite", action = "store_true", help = "Overwrite existing destination files" )
    parser.add_argument( "--no-metrics", action = "store_true", help = "Skip duration probing/metrics" )

    # Optional overrides for common config values
    parser.add_argument( "--fps", type = int, help = "Target frames per second (default 30)" )
    parser.add_argument( "--height", type = int, help = "Target output height (default 1080)" )
    parser.add_argument( "--crf", type = int, help = "x264 CRF (lower is higher quality, default 23)" )
    parser.add_argument( "--preset", type = str, help = "x264 preset (ultrafast..placebo, default veryfast)" )
    parser.add_argument( "--audio-bitrate", type = str, help = "Audio bitrate (e.g., 160k)" )

    args = parser.parse_args()

    root = Path( args.root )
    dst_dir = Path( args.dst )
    dst_dir.mkdir( parents = True, exist_ok = True )

    # Local cfg copy for overrides
    cfg = dict( ffmpeg_config )
    if args.fps is not None:
        cfg[ "fps" ] = args.fps
    if args.height is not None:
        cfg[ "scale_height" ] = args.height
    if args.crf is not None:
        cfg[ "crf" ] = args.crf
    if args.preset is not None:
        cfg[ "preset" ] = args.preset
    if args.audio_bitrate is not None:
        cfg[ "audio_bitrate" ] = args.audio_bitrate

    print( f"{CYAN}ShareX root{RE}: {root}" )
    print( f"{CYAN}Pattern{RE}: {args.pattern}    {CYAN}Format{RE}: .{args.format}" )
    print( f"{CYAN}Destination{RE}: {dst_dir}" )
    print( f"{CYAN}Config{RE}: fps={MAGENTA}{cfg['fps']}{RE}, height={MAGENTA}{cfg['scale_height']}{RE}, crf={MAGENTA}{cfg['crf']}{RE}, preset={MAGENTA}{cfg['preset']}{RE}, a_bitrate={MAGENTA}{cfg['audio_bitrate']}{RE}" )

    files = find_capture_files( root, args.pattern, args.format )
    if not files:
        print( f"{YELLOW}No matching files found.{RE}" )
        sys.exit( 0 )

    # Map to destination paths
    plan: List[ Tuple[ Path, Path ] ] = []
    for src in files:
        plan.append( ( src, dst_dir / src.name ) )

    # Pre-probe durations for files that need conversion
    total_seconds = 0.0
    durations: Dict[ Path, float ] = {}
    if not args.no_metrics:
        for src, dst in plan:
            if args.overwrite or not dst.exists():
                dur = run_ffprobe_duration_seconds( src )
                durations[ src ] = dur
                total_seconds += dur

    if total_seconds > 0:
        print( f"{CYAN}Total duration to convert{RE}: {MAGENTA}{human_time(total_seconds)}{RE} (~{MAGENTA}{total_seconds:.1f}{RE}s)" )

    converted = 0
    skipped = 0
    failed = 0
    deleted_short = 0

    t0 = time.perf_counter()
    for idx, ( src, dst ) in enumerate( plan, start = 1 ):
        # Always determine duration to enforce short-clip deletion
        dur = durations.get( src ) if src in durations else run_ffprobe_duration_seconds( src )
        if dur > 0.0 and dur < MIN_KEEP_SECONDS:
            try:
                src.unlink()
                deleted_short += 1
                print( f"[{idx}/{len(plan)}] {YELLOW}Delete short{RE} ({MAGENTA}{human_time(dur)}{RE}) → {CYAN}{src.name}{RE}" )
            except Exception as e:
                print( f"[{idx}/{len(plan)}] {YELLOW}Warning could not delete short clip{RE}: {CYAN}{src}{RE} — {e}" )
            continue

        if not args.overwrite and dst.exists():
            skipped += 1
            print( f"[{idx}/{len(plan)}] {YELLOW}Skip exists{RE} → {CYAN}{dst.name}{RE}" )
            continue

        print( f"[{idx}/{len(plan)}] {GREEN}Converting{RE} → {CYAN}{src.name}{RE}" )
        ok, _ = convert_one( src, dst, cfg, overwrite = args.overwrite )
        if ok:
            converted += 1
            if args.delete_original:
                try:
                    src.unlink()
                    print( f"    {GREEN}Deleted original{RE}: {CYAN}{src}{RE}" )
                except Exception as e:
                    print( f"    {YELLOW}Warning could not delete{RE}: {CYAN}{src}{RE} — {e}" )
        else:
            failed += 1

    elapsed = time.perf_counter() - t0

    # Report
    print()
    print( f"{B_CYAN}Summary{RE}: converted={MAGENTA}{converted}{RE}, skipped={MAGENTA}{skipped}{RE}, failed={MAGENTA}{failed}{RE}, deleted<5s={MAGENTA}{deleted_short}{RE}" )
    if not args.no_metrics:
        rt = ( total_seconds / elapsed ) if elapsed > 0 else 0.0
        print( f"{CYAN}Encoding time{RE}: {MAGENTA}{human_time(elapsed)}{RE} ({elapsed:.1f}s)  |  speed≈{MAGENTA}{rt:.2f}x realtime{RE}" )


if __name__ == "__main__":
    main()
