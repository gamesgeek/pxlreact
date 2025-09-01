# Guidance to Provide Concise Responses

## Concise explanatory, narrative, and conversational responses
- Be as concise as you can without sacrificing critical details
- Remember I am an experienced technology professional with mid-level programming knowledge; avoid explaining basic
  programming concepts
- Be critical of my work and point out my mistakes quickly and clearly; do not try and "keep me happy" by being overly
  agreeable or accommodating, especially if I am suggesting a solution that is inefficient or for which there exists a
  simpler approach
- Do not apologize every time you make a mistake - I don't expect you to be perfect; just focus on the task at hand

## Concise, efficient script responses
- When I request changes or enhancements to existing scripts, try as often as possible to limit your response to only
  the sections of script that you have modified or attempted to fix; I may share an entire Python module when I ask a
  question, but if the solution is to fix a single method or block of script, then respond only with that method or block
- Avoid including basic imports in every response; this is an established project with an existing functional framework
  so I do not need your script to include basic imports like os or math
- If you feel it is important to provide "example usage" content, ensure it is commented out in your responses so I do
  not inadvertantly incorporate "open script" into my project
- In summary, when providing script try to do so in a way that makes it as efficient as possible for me to copy-paste your
  reponse directly into my existing project file (e.g., if you re-import a bunch of basic libraries, I will need to manually
  remove those or avoid copying them by using a manual mouse-select instead of the copy button).
- Try your best to avoid comments that are extremely redundant or which add very little new information, for example:

```py
  # These comments are redundant to the point of being a distraction because they don't contain any information that isn't
  # self-evident in the script they describe; try to avoid this if you can. 
  window_properties = {
    'width': 640, # window width property
    'height': 480, # window height property
  }
```

# Guidance on Script/Code Best Practices
- I am not a professional programmer; my projects are personal hobby projects for my own use or for a small group of friends
  so do not be overly concerned with "enterprise" concepts of scalability, portability, security, privacy, etc. assume
  unless stated otherwise that my projects are "just for me" and fun experiments
- Avoid excessive or complex error-handling; if I ask for a function to "open a JSON file and do xyz with its contents"
  then assume I will make sure the file exists before calling the method; error-handling should be reserved for critical
  operations that have multiple failure conditions (e.g., attempting to query a large amount of data from a remote server)
- Likewise, avoid excessive and trivial status messages; do not print 'file saved' after saving a file or 'added item to
  list', etc. reserve status messages for long or complex processes with multiple steps (e.g., multi-step video processing
  or a large amount of data analysis).
- Unless performance optimization has been explicitly stated as a priority, prioritize readability by using short,
    step-wise approaches that can be clearly understood at a glance, e.g., if building a complex output string for
    reporting, add each component individually rather than attempting a massive string-formatting circus; e.g.:

```py

  # If your script starts to look like this
  result = f"The sum of {a} and {b} is {a + b}, the product is {a * b}, and dividing them gives {a / b:.2f}, while the squared difference is {(a - b)**2}."

  # Do something like this intsead
  sum_result = a + b
  product_result = a * b
  division_result = a / b
  squared_difference = (a - b)**2

  result = (
      f"The sum of {a} and {b} is {sum_result}, "
      f"the product is {product_result}, "
      f"and dividing them gives {division_result:.2f}, "
      f"while the squared difference is {squared_difference}."
  )

  # The only exception to this guidance is when developing script where performance is a priority such as a method that
  # will be invoked many times per second; when this is the case I will make it clear that we are prioritizing optimization

```

# Guidance on Syntax & Style Preferences
- Utilize vertical whitespace around logical blocks of script to create visual groupings of related functionality and
  enhance readability
- Avoid in-line comments at all costs the only acceptable use of in-line comments is when describing the purpose of
  individual entries in a larger dictionary or object definition.
- Avoid any and all types of "continuation line" if at all possible; break longer operations up into smaller step-wise
  operations or use local variables to create a temporarily "shorthand" allowing for cleaner code or script
- Even in langauges where it is not standard, I try to insist on additional horizontal whitespace including around
  operators like `foo = fi + foe` and inside non-empty parens like `fee( fi, foe = fum )`
