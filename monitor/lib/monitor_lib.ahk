; Basic output function to write data to stdout; comment these out in production for optimal performance
debug( str ) {
  ; Specifying asterisk redirects to stdout instead of writing to a file
  FileAppend( str "`n", "*" )
}

; Function to convert HEX colors returned by PixelGetColor into a tuple of RGB values
hexToRGB( hexColor ) {
  return [ ( hexColor >> 16 ) & 0xFF, ( hexColor >> 8 ) & 0xFF, hexColor & 0xFF ]
}

; Function to convert HEX colors into a string representation of decimal values as "( R, G, B )"
hexToRGBString( hexColor ) {
  rgb := hexToRGB( hexColor )
  return "( " . rgb[ 1 ] . ", " . rgb[ 2 ] . ", " . rgb[ 3 ] . " )"
}
